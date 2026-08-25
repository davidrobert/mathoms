"""Base do PGBL da S8 sai do ano-base fiscal eleito, não do `created_at` (A40.l65 §Escopo 1).

Antes desta lane `_load_irpf_renda_tributavel` lia a row mais recentemente criada.
Com dois declarantes — ou com o mesmo declarante re-extraído — o ano publicado
passava a depender de quem foi processado por último, enquanto o Card B publicava
o ano que `resolve_ano_base_fiscal` elege (ADR-305 D1/D2). Dois resolvedores do
mesmo corpus no mesmo documento.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.app.services.tributario_input_builder import build_cascata_input_sync
from backend.tests import factories

_HOJE = datetime.now(timezone.utc)


def _contribuinte(*, ano_base: int, cpf_final: str) -> dict:
    return {
        "cpf_masked": f"***.***.***-{cpf_final}",
        "nome": f"Declarante {cpf_final}",
        "ano_base": ano_base,
        "exercicio": ano_base + 1,
        "modelo": "completo",
        "natureza": "titular",
    }


def _fonte_pj(tributavel: str) -> dict:
    return {
        "cnpj": "12.345.678/0001-90",
        "nome": "Fonte",
        "rendimentos_tributaveis_brl": tributavel,
        "contrib_previdenciaria_brl": "0",
        "ir_retido_brl": "0",
        "decimo_terceiro_bruto_brl": "0",
        "decimo_terceiro_ir_retido_brl": "0",
    }


def _declaracao(
    *, ano_base: int, cpf_final: str, tributavel: str, dependentes: list[str] | None = None
) -> dict:
    return {
        "contribuinte": _contribuinte(ano_base=ano_base, cpf_final=cpf_final),
        "dependentes": [
            {"cpf_masked": f"***.***.***-{d}", "nome": f"Dep {d}", "relacao": "conjuge"}
            for d in (dependentes or [])
        ],
        "rendimentos_pj": [_fonte_pj(tributavel)],
        "rendimentos_pf": [],
        "imposto_apurado": {
            "base_calculo_brl": tributavel,
            "ir_devido_brl": "0",
            "deducoes_totais_brl": "0",
            "ir_pago_brl": "0",
        },
        "confidence": 0.95,
    }


# ADR-371: `pipeline_run_id` é NOT NULL — a fixture materializa o pai da FK em vez
# de fabricar id sintético.
async def _run_do_workspace(db, ws_id: str) -> str:
    from backend.app.models.pipeline_run import PipelineRun, PipelineRunStatus

    run = PipelineRun(
        id=str(uuid4()),
        workspace_id=ws_id,
        status=PipelineRunStatus.completed,
        started_at=_HOJE - timedelta(days=1),
    )
    db.add(run)
    await db.flush()
    return run.id


def _ano_do(content: dict) -> str:
    """Tolerante de propósito: o teste do ramo de degradação usa payload sem ficha."""
    return str((content.get("contribuinte") or {}).get("ano_base", "malformado"))


def _artifact(ws_id: str, run_id: str, content: dict, *, created_at: datetime):
    from backend.app.models.pipeline_artifact import PipelineArtifact

    return PipelineArtifact(
        workspace_id=ws_id,
        pipeline_run_id=run_id,
        stage="extract_irpf_full",
        artifact_key=f"irpfdeclaracao_{_ano_do(content)}_{uuid4().hex[:6]}",
        content_json=content,
        created_at=created_at,
    )


async def _ws_com_perfil(db):
    from backend.app.models.workspace import Workspace

    ws = await factories.make_workspace(db)
    row = await db.get(Workspace, ws.id)
    row.business_profile_json = {"regime": "simples", "anexo_simples": "III"}
    await db.commit()
    return ws


def _cascata(ws_id: str):
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as sync_db:
        return build_cascata_input_sync(ws_id, db=sync_db)


def _base_pgbl(ws_id: str) -> Decimal:
    from backend.app.core.database import SyncSessionLocal

    with SyncSessionLocal() as sync_db:
        return build_cascata_input_sync(ws_id, db=sync_db).renda_tributavel_pf_irpf_anual.amount


#: (ano_base, tributável) das duas declarações; 2024 é o ano completo eleito.
_DE_2024 = (2024, "200000")
_DE_2023 = (2023, "90000")


async def _seed(db, ws_id: str, *, primeiro, segundo):
    """Semeia as duas declarações; `primeiro` é o criado há mais tempo."""
    run_id = await _run_do_workspace(db, ws_id)
    for (ano, valor), quando in ((primeiro, _HOJE - timedelta(hours=2)), (segundo, _HOJE)):
        payload = _declaracao(ano_base=ano, cpf_final="11", tributavel=valor)
        db.add(_artifact(ws_id, run_id, payload, created_at=quando))
    await db.commit()


@pytest.mark.asyncio
async def test_ano_base_nao_segue_a_ordem_de_processamento(db):
    """A row de 2023 foi criada DEPOIS e não vence: o ano eleito é 2024."""
    ws = await _ws_com_perfil(db)
    await _seed(db, ws.id, primeiro=_DE_2024, segundo=_DE_2023)

    assert _base_pgbl(ws.id) == Decimal("200000")


@pytest.mark.asyncio
async def test_falsificavel_a_ordem_inversa_devolve_o_mesmo_ano(db):
    """Braço de controle: invertidos os `created_at`, o resultado NÃO muda — sem
    este par o teste acima passaria por coincidência de ordenação, que é
    exatamente a leitura por `created_at` que ele existe para falsificar."""
    ws = await _ws_com_perfil(db)
    await _seed(db, ws.id, primeiro=_DE_2023, segundo=_DE_2024)

    assert _base_pgbl(ws.id) == Decimal("200000")


@pytest.mark.asyncio
async def test_sem_irpf_a_base_e_zero(db):
    """Workspace sem declaração: o caminho não estoura e a base não é inventada."""
    ws = await _ws_com_perfil(db)

    assert _base_pgbl(ws.id) == Decimal("0")


# =============================================================================
# A40.l65 §Escopo 3 — o lado S8 publica o ano que SOMOU (proveniência)
#
# Sem isto o §Critério 3 compara duas ausências: `RendaTributavelPF` não tinha
# campo de ano nenhum. Publicar o ano ELEITO não serviria — o ramo de fallback
# (ano eleito sem declaração) continuaria mudo, que é justamente o que precisa
# ficar visível. Decisão: `senior-cto` (D6-a1, co-design 2026-08-24).
# =============================================================================


@pytest.mark.asyncio
async def test_a_cascata_publica_o_ano_que_somou(db):
    ws = await _ws_com_perfil(db)
    await _seed(db, ws.id, primeiro=_DE_2024, segundo=_DE_2023)

    inp = _cascata(ws.id)

    assert inp.renda_tributavel_pf_ano_base == 2024
    # Falsificável: sem o par, o ano poderia vir de qualquer lugar.
    assert inp.renda_tributavel_pf_irpf_anual.amount == Decimal("200000")


@pytest.mark.asyncio
async def test_sem_irpf_o_ano_e_ausente_nao_zero(db):
    """Ausência declarada — `0` seria um ano, e ano nenhum é o fato."""
    ws = await _ws_com_perfil(db)

    assert _cascata(ws.id).renda_tributavel_pf_ano_base is None


class _RecordingLogger:
    """Recorder imune a `propagate=False` do namespace mathoms.* — caplog não vê."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, dict]] = []

    def warning(self, msg: str, *args, extra=None, **kwargs) -> None:
        self.warnings.append((msg, extra or {}))


@pytest.mark.asyncio
async def test_o_ramo_de_degradacao_deixa_de_ser_mudo(db, monkeypatch):
    """Payload que não parseia: a S8 volta ao artifact mais recente — declarando.

    Antes era silencioso: nenhum gate podia distinguir "resolveu o ano" de
    "desistiu e pegou o último". O `ano_base` do VO fica `None` junto, porque o
    payload malformado não tem `contribuinte.ano_base` legível.
    """
    # O logger mudou de módulo na extração do reader — patch segue o produtor.
    import backend.app.services.tributario_irpf_reader as mod

    recorder = _RecordingLogger()
    monkeypatch.setattr(mod, "logger", recorder)

    ws = await _ws_com_perfil(db)
    run_id = await _run_do_workspace(db, ws.id)
    db.add(_artifact(ws.id, run_id, {"lixo": True}, created_at=_HOJE))
    await db.commit()

    _cascata(ws.id)

    eventos = [m for m, _ in recorder.warnings]
    assert "tributario_irpf_ano_base_nao_resolvido" in eventos


# =============================================================================
# A40.l65 §Escopo 2 — a base é a do TITULAR, nunca a de quem sobrou
#
# Decisão de escopo (2026-08-25): a âncora vai para a S8, onde a lane a coloca.
# A variante do card do E5 (motivos `titular_nao_identificado` /
# `titular_sem_declaracao_no_ano` do D5 do `financial-planner`) exigiria mover o
# Card B para agregação por titular — que o §Fora de escopo desta lane VEDA.
# =============================================================================


async def _titular_com_cpf(db, ws_id: str, cpf: str = "123.456.789-11"):
    from backend.app.models.family_member import FamilyMember
    from backend.app.services.security.vault import get_vault

    db.add(
        FamilyMember(
            workspace_id=ws_id,
            key="titular",
            full_name="Titular",
            short_name="Tit",
            role="titular",
            cpf_encrypted=get_vault().encrypt(cpf),
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_com_dois_declarantes_a_base_e_a_do_titular(db):
    """O caso que dá nome à lane: sem âncora a base era de quem foi processado
    por último — aqui, o cônjuge, cuja declaração é a mais recente."""
    ws = await _ws_com_perfil(db)
    await _titular_com_cpf(db, ws.id)
    run_id = await _run_do_workspace(db, ws.id)
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="11", tributavel="200000"),
            created_at=_HOJE - timedelta(hours=2),
        )
    )
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="22", tributavel="90000"),
            created_at=_HOJE,
        )
    )
    await db.commit()

    assert _base_pgbl(ws.id) == Decimal("200000")


@pytest.mark.asyncio
async def test_titular_como_dependente_da_conjunta(db):
    """Declaração conjunta com o titular como dependente: a base sai, é a dela."""
    ws = await _ws_com_perfil(db)
    await _titular_com_cpf(db, ws.id)
    run_id = await _run_do_workspace(db, ws.id)
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="22", tributavel="150000", dependentes=["11"]),
            created_at=_HOJE,
        )
    )
    await db.commit()

    assert _base_pgbl(ws.id) == Decimal("150000")


@pytest.mark.asyncio
async def test_sem_cadastro_e_dois_declarantes_a_base_e_ausente(db):
    """Base de OUTRO CPF é pior que base nenhuma — erro de identidade, não de
    aritmética. Sem cadastro do titular, escolher seria cara-ou-coroa."""
    ws = await _ws_com_perfil(db)
    run_id = await _run_do_workspace(db, ws.id)
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="11", tributavel="200000"),
            created_at=_HOJE - timedelta(hours=2),
        )
    )
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="22", tributavel="90000"),
            created_at=_HOJE,
        )
    )
    await db.commit()

    assert _base_pgbl(ws.id) == Decimal("0")


@pytest.mark.asyncio
async def test_sem_cadastro_e_UM_declarante_a_base_sai(db):
    """Braço de controle: suprimir aqui tiraria a base de todo declarante único
    para prevenir um erro que exige dois declarantes para existir."""
    ws = await _ws_com_perfil(db)
    run_id = await _run_do_workspace(db, ws.id)
    db.add(
        _artifact(
            ws.id,
            run_id,
            _declaracao(ano_base=2024, cpf_final="11", tributavel="200000"),
            created_at=_HOJE,
        )
    )
    await db.commit()

    assert _base_pgbl(ws.id) == Decimal("200000")
