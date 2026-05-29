"""INV-1..9 — invariantes do output agregado de E1.5c (`consolidate_baseline`).

Os dedups por entidade (`imoveis_dedup`, `investimentos_dedup`) têm testes
unitários próprios; esta suíte valida o **resultado agregado** de E1.5c — a rede
de segurança que prova que um mecanismo de dedup novo (ou refactor — A21.l3) não
quebra a conservação. Cada teste roda o caminho real `main_with_store`
(consolidate → dedup imóveis → dedup investimentos) sobre baseline sintético
zero-PII e afirma uma propriedade do dict consolidado.

Plano: [[PLAN-launch-trust]] §F1-O0. Lane A21.l1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.domain.services.investimentos_dedup import dedup_investimentos_consolidados
from pipeline.llm.schemas.e16_irpf_full import detect_pj_suffix


def _item(
    *,
    categoria: str,
    descricao: str,
    valor_brl,  # money → float no wire-JSON do pipeline (ADR-090 é p/ produção)
    membro: str,
    codigo: str = "",
    instituicao: str | None = None,
    ano: int = 2024,
) -> dict:
    entry = {
        "codigo": codigo,
        "descricao": descricao,
        "categoria": categoria,
        "valor_brl": valor_brl,
        "membro": membro,
        "ano": ano,
    }
    if instituicao is not None:
        entry["instituicao"] = instituicao
    return entry


def _baseline(itens: list[dict], total_ativos=0.0) -> dict:
    # total_ativos = 0 (default) → consolidate usa a soma dos itens (não
    # sobrescreve). Passar > 0 exercita o override do `resumo` do LLM — usado
    # por INV-9 para provar que o agregado não vaza valor PJ.
    return {
        "itens": itens,
        "resumo": {
            "total_ativos": total_ativos,
            "total_passivos": 0.0,
            "patrimonio_liquido": 0.0,
            "ano_referencia": 2024,
        },
    }


def _consolidate(tmp_path: Path, itens: list[dict], total_ativos=0.0) -> dict:
    """Roda E1.5c (`main_with_store`) e devolve o dict consolidado."""
    from scripts.e15_consolidate import main_with_store

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", _baseline(itens, total_ativos))
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-inv",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )
    result = main_with_store(ctx)
    assert result["success"] is True
    return store.read("E1.5c", "baseline_patrimonial")


def _latest(entry: dict) -> float:
    valores = entry.get("valores_31_12") or {}
    if not valores:
        return 0.0
    return float(valores[max(valores)])


# Cenário-base reusado por vários invariantes: conta conjunta (idêntica ao
# centavo, 2 declarantes) + série cross-year (mesmo dono, 2 anos) + ativo único.
_JOINT_DESC = "CDB BANCO EXEMPLO 123"
_SERIES_DESC = "TESOURO SELIC 2029"
_SOLO_DESC = "FUNDO MULTIMERCADO XPTO"


def _mixed_itens() -> list[dict]:
    return [
        # conta conjunta — idêntica ao centavo nos 2 declarantes (funde em 1)
        _item(
            categoria="investimento",
            codigo="04",
            descricao=_JOINT_DESC,
            instituicao="banco_exemplo",
            valor_brl=50000.00,
            membro="david_robert",
        ),
        _item(
            categoria="investimento",
            codigo="04",
            descricao=_JOINT_DESC,
            instituicao="banco_exemplo",
            valor_brl=50000.00,
            membro="mariana_silva",
        ),
        # série cross-year — mesmo dono, 2023 → 2024 (funde em 1, mantém 2 anos)
        _item(
            categoria="investimento",
            codigo="04",
            descricao=_SERIES_DESC,
            instituicao="tesouro",
            valor_brl=80000.00,
            membro="david_robert",
            ano=2023,
        ),
        _item(
            categoria="investimento",
            codigo="04",
            descricao=_SERIES_DESC,
            instituicao="tesouro",
            valor_brl=100000.00,
            membro="david_robert",
            ano=2024,
        ),
        # ativo único — não funde com nada
        _item(
            categoria="investimento",
            codigo="07",
            descricao=_SOLO_DESC,
            instituicao="xpto",
            valor_brl=30000.00,
            membro="mariana_silva",
        ),
    ]


def test_inv1_conservacao_nunca_cria_patrimonio(tmp_path: Path) -> None:
    """INV-1: a soma dos valores representativos pós-dedup ≤ soma pré-dedup."""
    itens = _mixed_itens()
    raw_sum = sum(it["valor_brl"] for it in itens)  # 310000
    out = _consolidate(tmp_path, itens)
    dedup_sum = sum(_latest(e) for e in out["investimentos_consolidados"])
    assert dedup_sum <= raw_sum
    # conta conjunta não dobra: o representativo é 50k, não 100k.
    joint = [e for e in out["investimentos_consolidados"] if e["descricao"] == _JOINT_DESC]
    assert len(joint) == 1
    assert _latest(joint[0]) == 50000.00


def test_inv2_nao_double_count(tmp_path: Path) -> None:
    """INV-2: nenhuma identidade (investment_id) aparece 2× no output."""
    out = _consolidate(tmp_path, _mixed_itens())
    ids = [e["investment_id"] for e in out["investimentos_consolidados"] if "investment_id" in e]
    assert len(ids) == len(set(ids))
    # 3 entidades distintas (conjunta, série, solo) a partir de 5 itens.
    assert len(out["investimentos_consolidados"]) == 3


def test_inv3_idempotencia(tmp_path: Path) -> None:
    """INV-3: rodar o dedup de novo sobre o output não muda nada."""
    out = _consolidate(tmp_path, _mixed_itens())
    investimentos = out["investimentos_consolidados"]
    again = dedup_investimentos_consolidados(investimentos)
    assert again.count_after == len(investimentos)
    assert again.count_before == again.count_after


def test_inv4_cobertura_de_id(tmp_path: Path) -> None:
    """INV-4: todo item identificável de saída tem `<entity>_id` estampado."""
    out = _consolidate(
        tmp_path,
        _mixed_itens()
        + [
            _item(
                categoria="imovel",
                codigo="11",
                descricao="APT RUA EXEMPLO 100",
                valor_brl=600000.0,
                membro="david_robert",
            ),
        ],
    )
    for inv in out["investimentos_consolidados"]:
        if inv.get("descricao"):
            assert inv.get("investment_id"), f"sem investment_id: {inv['descricao']}"
    for im in out["imoveis_consolidados"]:
        assert im.get("property_id"), f"sem property_id: {im['descricao']}"


def test_inv5_preservacao_cross_declarante_casal(tmp_path: Path) -> None:
    """INV-5: imóvel co-declarado por 2 cônjuges vira 1 item 'casal', não some."""
    desc = "APARTAMENTO EDIFICIO EXEMPLO APT 50 - RUA TESTE 200, SAO PAULO/SP"
    out = _consolidate(
        tmp_path,
        [
            _item(
                categoria="imovel",
                codigo="11",
                descricao=desc,
                valor_brl=500000.0,
                membro="david_robert",
            ),
            _item(
                categoria="imovel",
                codigo="11",
                descricao=desc,
                valor_brl=480000.0,
                membro="mariana_silva",
            ),
        ],
    )
    imoveis = out["imoveis_consolidados"]
    assert len(imoveis) == 1
    assert imoveis[0]["proprietario"] == "casal"
    assert set(imoveis[0]["proprietarios"]) == {"david_robert", "mariana_silva"}
    # maior valor vence (ADR-246).
    assert _latest(imoveis[0]) == 500000.0


def test_inv6_tie_break_deterministico(tmp_path: Path) -> None:
    """INV-6: mesmo input → mesmo output (sem flakiness de ordem/vencedor)."""
    itens = _mixed_itens()
    a = _consolidate(tmp_path / "a", itens)
    b = _consolidate(tmp_path / "b", itens)
    assert a["investimentos_consolidados"] == b["investimentos_consolidados"]
    assert a["imoveis_consolidados"] == b["imoveis_consolidados"]


def test_inv7_warning_nao_silencioso(tmp_path: Path) -> None:
    """INV-7: fusão com divergência >10% emite `_dedup_warning` tipado."""
    desc = "APARTAMENTO RUA DIVERGENTE 300 APT 7, SAO PAULO/SP"
    out = _consolidate(
        tmp_path,
        [
            _item(
                categoria="imovel",
                codigo="11",
                descricao=desc,
                valor_brl=400000.0,
                membro="david_robert",
            ),
            _item(
                categoria="imovel",
                codigo="11",
                descricao=desc,
                valor_brl=600000.0,
                membro="mariana_silva",
            ),
        ],
    )
    merged = out["imoveis_consolidados"][0]
    assert merged["_dedup_warning"]["type"] == "valor_divergente"
    assert merged["_dedup_warning"]["diff_pct"] > 10.0


def test_inv8_monotonicidade_serie_queda_nao_e_erro(tmp_path: Path) -> None:
    """INV-8: série cross-year com queda de valor funde sem erro; usa max(ano)."""
    out = _consolidate(
        tmp_path,
        [
            _item(
                categoria="investimento",
                codigo="04",
                descricao=_SERIES_DESC,
                instituicao="tesouro",
                valor_brl=100000.0,
                membro="david_robert",
                ano=2023,
            ),
            _item(
                categoria="investimento",
                codigo="04",
                descricao=_SERIES_DESC,
                instituicao="tesouro",
                valor_brl=80000.0,
                membro="david_robert",
                ano=2024,
            ),
        ],
    )
    serie = [e for e in out["investimentos_consolidados"] if e["descricao"] == _SERIES_DESC]
    assert len(serie) == 1
    valores = serie[0]["valores_31_12"]
    assert set(valores) == {"2023", "2024"}
    # representativo = max(ano), mesmo com queda.
    assert _latest(serie[0]) == 80000.0


def test_inv9_contribuinte_pj_nao_e_pessoa(tmp_path: Path) -> None:
    """INV-9: contribuinte PJ (razão social) não vira membro nem soma ao PL (ADR-268).

    O read-filter `partition_irpf_payloads` (ADR-268 rev) cobre E5, não E1.5c.
    Este invariante fecha o boundary de consolidação — itens **e** agregado.
    """
    itens = [
        _item(
            categoria="investimento",
            codigo="04",
            descricao="CDB PF LEGITIMO",
            instituicao="banco",
            valor_brl=20000.0,
            membro="david_robert",
        ),
        # contribuinte PJ — razão social com sufixo LTDA não é PF.
        _item(
            categoria="investimento",
            codigo="04",
            descricao="PARTICIPACAO SOCIETARIA",
            instituicao="empresa",
            valor_brl=4000000.0,
            membro="DAVID ROBERT CAMARGO DE CAMPOS LTDA",
        ),
    ]
    # `total_ativos` do LLM somou o PJ (20k + 4M = 4.02M) — o agregado não pode
    # herdar essa contaminação após o filtro (bug do override de `resumo`).
    out = _consolidate(tmp_path, itens, total_ativos=4_020_000.0)
    todos = (
        out["investimentos_consolidados"]
        + out["imoveis_consolidados"]
        + out["veiculos_consolidados"]
        + out["dividas"]
    )
    for entry in todos:
        owner = entry.get("proprietario") or ""
        assert detect_pj_suffix(owner) is None, f"contribuinte PJ vazou: {owner!r}"
    # o ativo PF legítimo sobrevive.
    assert any(e["descricao"] == "CDB PF LEGITIMO" for e in out["investimentos_consolidados"])
    # o agregado também não vaza o PJ: total_bens = 20k (PF), não 4.02M.
    total_bens = out["patrimonio_por_ano"]["2024"]["total_bens"]
    assert total_bens == 20000.0, f"agregado contaminado por PJ: {total_bens}"
