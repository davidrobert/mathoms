"""Golden de execução E1.5c (`consolidate_baseline`): run canônico + contrato.

Distinto da suíte INV-1..9 (propriedades) e do golden anotado de l2 (fn/fp
rates): este golden roda um baseline sintético **realista** (imóvel + série
cross-year + conta conjunta + dívida + zero-PII) pelo caminho real
`main_with_store` e afirma o **contrato de saída** que o E5 consome. Fixture
mínima — l2 endurece com o golden multi-ano anotado.

Plano: [[PLAN-launch-trust]] §F1-O0. Lane A21.l1.
"""

from __future__ import annotations

import copy
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext

# Chaves que o E5 (`analyze_finances`) lê do artifact E1.5c — o contrato.
_E5_CONSUMED_KEYS = (
    "imoveis_consolidados",
    "veiculos_consolidados",
    "investimentos_consolidados",
    "dividas",
    "patrimonio_por_ano",
)

_BALDES_ATIVO = ("imoveis_consolidados", "veiculos_consolidados", "investimentos_consolidados")

# A lane que desmarca cada xfail abaixo. L1 fecha o seam (roteamento por fato +
# conservação por eixo + review_reason); L2 fecha o contrato de schema.
_L1 = "A40.l66 (seam extração/consolidação — itens 1a/1b/1c do PLAN-deterministic-authority)"
_L2 = "A40.l67 (guarda de publicação E5 — item 1e do PLAN-deterministic-authority)"


def _canonical_baseline() -> dict:
    return {
        "itens": [
            {
                "codigo": "11",
                "descricao": "APT RUA EXEMPLO 100, SAO PAULO/SP",
                "categoria": "imovel",
                "valor_brl": 600000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "TESOURO SELIC 2029",
                "instituicao": "tesouro",
                "categoria": "investimento",
                "valor_brl": 80000.0,
                "membro": "david_robert",
                "ano": 2023,
            },
            {
                "codigo": "04",
                "descricao": "TESOURO SELIC 2029",
                "instituicao": "tesouro",
                "categoria": "investimento",
                "valor_brl": 100000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "CDB BANCO EXEMPLO",
                "instituicao": "banco_exemplo",
                "categoria": "investimento",
                "valor_brl": 50000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
            {
                "codigo": "04",
                "descricao": "CDB BANCO EXEMPLO",
                "instituicao": "banco_exemplo",
                "categoria": "investimento",
                "valor_brl": 50000.0,
                "membro": "mariana_silva",
                "ano": 2024,
            },
            {
                "codigo": "00",
                "descricao": "FINANCIAMENTO IMOVEL",
                "categoria": "outros",
                "valor_brl": -200000.0,
                "membro": "david_robert",
                "ano": 2024,
            },
        ],
        "resumo": {
            "total_ativos": 0.0,
            "total_passivos": 0.0,
            "patrimonio_liquido": 0.0,
            "ano_referencia": 2024,
        },
    }


# Payload da pipeline-review r6: a re-extração flipou o rótulo do financiamento.
# O item de dívida chega com `categoria` de ATIVO e o MESMO código RFB do imóvel
# legítimo — só o sinal do valor denuncia o fato. O `resumo` do próprio artefato
# contabiliza o montante no lado do passivo: o detector já vem dentro do payload,
# e `consolidate_from_itens` o descarta (adota o total do `resumo` quando
# `pj_skipped == 0`). O item de 2023 dá dente ao eixo do ano — soma ano-cega dá
# 480k e ano-fatiada dá 400k, e nenhuma das duas é o 600k declarado.
_R6_PAYLOAD = {
    "itens": [
        {
            "codigo": "11",
            "descricao": "Rua Exemplo, 100",
            "categoria": "imovel",
            "valor_brl": 600000.0,
            "membro": "david_robert",
            "ano": 2024,
        },
        {
            "codigo": "11",
            "descricao": "FINANCIAMENTO IMOVEL EXEMPLO",
            "categoria": "imovel",
            "valor_brl": -200000.0,
            "membro": "david_robert",
            "ano": 2024,
        },
        {
            "codigo": "04",
            "descricao": "TESOURO SELIC 2029",
            "instituicao": "tesouro",
            "categoria": "investimento",
            "valor_brl": 80000.0,
            "membro": "david_robert",
            "ano": 2023,
        },
    ],
    "resumo": {
        "total_ativos": 600000.0,
        "total_passivos": 200000.0,
        "patrimonio_liquido": 400000.0,
        "ano_referencia": 2024,
    },
}


def _r6_baseline() -> dict:
    """Cópia funda — `consolidate_from_itens` grava os baldes no dict de entrada."""
    return copy.deepcopy(_R6_PAYLOAD)


def _cents(value) -> int:
    """ADR-090: comparação monetária é int de centavos, nunca float."""
    return int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _soma_ativos_cents(out: dict, ano: str) -> int:
    return sum(
        _cents((entry.get("valores_31_12") or {}).get(ano, 0))
        for balde in _BALDES_ATIVO
        for entry in (out.get(balde) or [])
    )


def _soma_passivos_cents(out: dict, ano: str) -> int:
    return sum(
        _cents((entry.get("saldo_31_12") or {}).get(ano, 0)) for entry in (out.get("dividas") or [])
    )


def _run(tmp_path: Path, baseline: dict | None = None) -> dict:
    from scripts.consolidate_baseline import main_with_store

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "pipeline.json").write_text("{}")
    (tmp_path / "config" / "family_members.json").write_text("{}")
    store = InMemoryArtifactStore()
    store.write("E1.5", "baseline_patrimonial", baseline or _canonical_baseline())
    ctx = WorkspaceContext(
        root=tmp_path,
        artifact_store=store,
        workspace_id="test-ws-golden",
        property_identity_resolver=InMemoryPropertyIdentityResolver(),
    )
    result = main_with_store(ctx)
    assert result["success"] is True
    return store.read("E1.5c", "baseline_patrimonial")


def test_e15c_golden_output_contract(tmp_path: Path) -> None:
    """Run canônico produz todas as chaves que o E5 consome, com tipos certos."""
    out = _run(tmp_path)
    for key in _E5_CONSUMED_KEYS:
        assert key in out, f"contrato E5 quebrado: falta {key!r}"
    assert isinstance(out["investimentos_consolidados"], list)
    assert isinstance(out["dividas"], list)
    assert isinstance(out["patrimonio_por_ano"], dict)


def test_e15c_golden_dedup_e_serie(tmp_path: Path) -> None:
    """Conta conjunta funde (1), série cross-year preserva 2 anos, dívida fica."""
    out = _run(tmp_path)
    invs = out["investimentos_consolidados"]
    # CDB conjunto idêntico → 1; Tesouro série cross-year → 1: total 2.
    assert len(invs) == 2
    serie = [e for e in invs if e["descricao"] == "TESOURO SELIC 2029"]
    assert len(serie) == 1
    assert set(serie[0]["valores_31_12"]) == {"2023", "2024"}
    assert len(out["dividas"]) == 1
    assert out["dividas"][0]["saldo_31_12"]["2024"] == 200000.0


# ---------------------------------------------------------------------------
# Golden r6 — o rótulo do LLM decidindo ativo/passivo (PLAN-deterministic-authority
# §Onda 0 · item 0a). Cada assert é um teste próprio: com um único teste, o
# primeiro assert a falhar esconde os outros quatro e a lane perde o sinal de
# progresso parcial. `strict=True` obriga o desmarque explícito no PR que corrige.
# ---------------------------------------------------------------------------

_ANO_REF = "2024"


def test_e15c_r6_nenhum_balde_de_ativo_publica_valor_negativo(tmp_path: Path) -> None:
    """Item com rótulo de ativo e valor negativo não pode aterrissar em balde de ativo."""
    out = _run(tmp_path, _r6_baseline())
    negativos = [
        (balde, entry.get("descricao"), ano, valor)
        for balde in _BALDES_ATIVO
        for entry in (out.get(balde) or [])
        for ano, valor in (entry.get("valores_31_12") or {}).items()
        if _cents(valor) < 0
    ]
    assert negativos == [], f"balde de ativo com valor negativo: {negativos}"


# Hoje só o ramo de imóvel carimba proveniência; o ramo de dívida devolve
# `descricao`/`proprietario`/`saldo_31_12` e nada mais (item 1a).
def test_e15c_r6_item_negativo_vira_divida_carimbada(tmp_path: Path) -> None:
    """O fato (sinal) roteia para `dividas[]`, com `fonte`/`ano_referencia`/`tipo`."""
    out = _run(tmp_path, _r6_baseline())
    dividas = out.get("dividas") or []
    alvo = [d for d in dividas if "FINANCIAMENTO" in (d.get("descricao") or "")]
    assert alvo, f"financiamento ausente de dividas[]: {dividas}"
    divida = alvo[0]
    assert _cents(divida["saldo_31_12"][_ANO_REF]) == 20_000_000
    for campo in ("fonte", "ano_referencia", "tipo"):
        assert campo in divida, f"dívida sem {campo!r} carimbado: {divida}"


# Por EIXO e por ANO, cents int, tolerância zero. Só o eixo denuncia: a dívida foi
# SUBTRAÍDA do lado do ativo em vez de somada ao do passivo, então os dois
# somatórios ficam devendo o mesmo montante — e o líquido, sendo a diferença entre
# eles, não acusa nada (ver o teste irmão logo abaixo).
def test_e15c_r6_conservacao_por_eixo_e_por_ano(tmp_path: Path) -> None:
    """Σ ativos ≡ `resumo.total_ativos` E Σ passivos ≡ `resumo.total_passivos`."""
    base = _r6_baseline()
    out = _run(tmp_path, base)
    resumo = base["resumo"]
    assert _soma_ativos_cents(out, _ANO_REF) == _cents(resumo["total_ativos"])
    assert _soma_passivos_cents(out, _ANO_REF) == _cents(resumo["total_passivos"])


# O contrato de `review_reasons` no artefato E1.5c é o item 1c — hoje só
# `extract_baseline` projeta o bloco. O `code` fica a cargo da L1 (membro novo no
# enum ADR-272); aqui só se exige o namespace `domain.` e a forma do schema.
def test_e15c_r6_divergencia_fato_rotulo_emite_review_reason(tmp_path: Path) -> None:
    """A divergência entre o fato (sinal/código) e o rótulo do LLM vira razão tipada."""
    out = _run(tmp_path, _r6_baseline())
    reasons = ((out.get("validation") or {}).get("review_reasons")) or []
    assert reasons, "E1.5c não projeta `validation.review_reasons` (ADR-272)"
    do_stage = [r for r in reasons if r.get("stage") == "consolidate_baseline"]
    assert do_stage, f"nenhuma razão carimbada com o stage: {reasons}"
    assert any(
        str(r.get("code", "")).startswith("domain.") for r in do_stage
    ), f"divergência fato×rótulo sem code no namespace `domain.`: {do_stage}"
    for reason in do_stage:
        assert _schema_errors(reason, "review_reason") == [], reason


# Mede `iter_errors` direto, não `validate_dict`: o retorno de `validate_dict`
# depende do modo (warn devolve `True` mesmo inválido), e um assert mode-dependente
# seria verde local e vermelho só no CI.
@pytest.mark.xfail(strict=True, reason=f"RED até {_L2} — schema aceita ativo negativo")
# Afirma o erro DO BALDE, não "existe algum erro": com o helper resolvendo o
# schema, o payload da fixture já reprova por `pipeline_stage`/`data_processamento`
# ausentes — genérico demais, e o teste passaria sem que o `minimum: 0` da
# A40.l67 existisse (medido no §Ataque II da A40.l66).
def test_e15c_r6_payload_reprova_no_schema(tmp_path: Path) -> None:
    """`baseline_patrimonial` deve recusar valor negativo nos 3 baldes de ativo (item 1e)."""
    negativo = copy.deepcopy(_R6_PAYLOAD)
    out = _run(tmp_path, negativo)
    out["imoveis_consolidados"] = [
        {
            "descricao": "forçado",
            "proprietario": "x",
            "tipo": "imovel",
            "valores_31_12": {_ANO_REF: -1.0},
        }
    ]
    erros = [e for e in _schema_errors(out, "baseline_patrimonial") if "imoveis" in e or "-1" in e]
    assert erros, "schema aceitou balde de ativo com valor negativo"


def _schema_errors(payload: dict, schema_name: str) -> list[str]:
    """Erros de schema independentes do modo warn/strict (ADR-212 PR3a)."""
    from scripts.pipeline_common import _build_schema_validator, _schema_to_validate

    # `_schema_to_validate` resolve por FILENAME (`CONFIG_DIR/schemas/<nome>`):
    # com o nome nu ele devolve `None` e o assert abaixo mata o teste por um
    # motivo que não é o mecanismo sob prova (medido no §Ataque II da A40.l66).
    schema, _ = _schema_to_validate(f"{schema_name}.schema.json")
    assert schema is not None, f"schema {schema_name!r} não encontrado em config/schemas/"
    return [e.message for e in _build_schema_validator(schema).iter_errors(payload)]


# ---------------------------------------------------------------------------
# 0b — o teste-irmão. Sem ele, quem for consertar o seam vê a conservação
# LÍQUIDA verde sobre o payload defeituoso e conclui que o invariante certo já
# existe. O cancelamento exato dos dois lados É a assinatura do bug, então este
# teste passa HOJE e precisa continuar passando: é controle, não alvo.
# ---------------------------------------------------------------------------


# Controle PERMANENTE: verde hoje (seam quebrado) e verde depois (seam corrigido).
# Um gate que não distingue os dois mundos não é gate. Fica ao lado do
# `..._conservacao_por_eixo_e_por_ano` para que a diferença entre as duas
# identidades seja visível no mesmo arquivo.
def test_e15c_r6_conservacao_liquida_nasce_verde_sobre_o_payload_defeituoso(
    tmp_path: Path,
) -> None:
    """O líquido fecha no payload r6 — e é exatamente por isso que não serve de gate."""
    base = _r6_baseline()
    out = _run(tmp_path, base)
    resumo = base["resumo"]
    liquido_observado = _soma_ativos_cents(out, _ANO_REF) - _soma_passivos_cents(out, _ANO_REF)
    liquido_declarado = _cents(resumo["total_ativos"]) - _cents(resumo["total_passivos"])
    assert liquido_observado == liquido_declarado
