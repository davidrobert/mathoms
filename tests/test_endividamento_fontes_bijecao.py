"""Bijeção ``fontes`` ↔ valor em ``endividamento.dividas[]`` (RV6-15 · PR1).

O item do E5 declara **de onde veio cada campo**. O invariante do produtor é
bijetivo e o schema sozinho não o expressa:

    ∀ c ∈ CAMPOS_COM_FONTE:  item[c] is not None  ⟺  c ∈ item["fontes"]

Metade dele (``fontes`` sem valor) até dá para escrever em JSON Schema com
``dependentRequired``; a outra metade (valor sem ``fontes``) exigiria
``dependentSchemas`` por campo e o dialeto do codegen não interpreta nenhum
dos dois. Então o schema trava a **forma** (enum por chave,
``additionalProperties: false``, ``exclusiveMinimum`` no observado) e este
gate trava a **correspondência** — inclusive sobre o payload real do produtor.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import is_monetary  # noqa: E402
from pipeline.domain.services.endividamento_analyzer import (  # noqa: E402
    DividaItem,
    EndividamentoAnalyzer,
)
from scripts.pipeline_common import validate_artifact  # noqa: E402
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO as _FLUXO_MIN  # noqa: E402

# Campos cuja presença obriga declaração de fonte (e vice-versa).
CAMPOS_COM_FONTE = (
    "saldo_devedor",
    "parcela_mensal",
    "taxa_juros_aa",
    "desembolso_mensal_observado_brl",
)

_ITEM_MINIMO = {
    "divida_id": None,
    "descricao": "Financiamento imobiliário",
    "membro": None,
    "tipo": "financiamento_imobiliario",
    "saldo_devedor": 500000.0,
    "saldo_ano_referencia": 2024,
    "parcela_mensal": None,
    "taxa_juros_aa": None,
    "desembolso_mensal_observado_brl": None,
    "fontes": {"saldo_devedor": "baseline_irpf"},
}


def assert_fontes_bijecao(item: dict) -> None:
    """Levanta ``AssertionError`` quando valor e fonte discordam."""
    fontes = item.get("fontes") or {}
    for campo in CAMPOS_COM_FONTE:
        tem_valor = item.get(campo) is not None
        tem_fonte = campo in fontes
        assert (
            tem_valor == tem_fonte
        ), f"bijeção quebrada em {campo!r}: valor={item.get(campo)!r} fontes={sorted(fontes)!r}"


def _e5_with_item(item: dict) -> dict:
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4500000},
        "fluxo_caixa": _FLUXO_MIN,
        "endividamento": {
            "total_dividas": 500000.0,
            "percentual_patrimonio": 10.0,
            "dividas": [item],
            "detalhe": "Financiamento imobiliário",
        },
    }


_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config/schemas/e5_analysis.schema.json"


def _validate(tmp_path: Path, item: dict) -> bool:
    path = tmp_path / "e5.json"
    path.write_text(json.dumps(_e5_with_item(item)))
    return validate_artifact(path, "e5_analysis.schema.json")


@pytest.fixture(autouse=True)
def _strict(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


# ──────────────────────────────────────────────────────────────────────
# Forma — travada pelo schema
# ──────────────────────────────────────────────────────────────────────


def test_item_minimo_do_produtor_valida(tmp_path):
    assert _validate(tmp_path, _ITEM_MINIMO) is True


def test_item_sem_fontes_falha(tmp_path):
    item = {k: v for k, v in _ITEM_MINIMO.items() if k != "fontes"}
    assert _validate(tmp_path, item) is False


def test_chave_extra_no_item_falha(tmp_path):
    """``additionalProperties: false`` no item — apelido inventado não passa."""
    assert _validate(tmp_path, {**_ITEM_MINIMO, "valor": 500000.0}) is False


def test_chave_extra_em_fontes_falha(tmp_path):
    item = {**_ITEM_MINIMO, "fontes": {"saldo_devedor": "baseline_irpf", "valor": "declarado"}}
    assert _validate(tmp_path, item) is False


@pytest.mark.parametrize(
    "fontes",
    [
        {"saldo_devedor": "observado_e4"},
        {"saldo_devedor": "baseline_irpf", "parcela_mensal": "baseline_irpf"},
        {"saldo_devedor": "baseline_irpf", "taxa_juros_aa": "observado_e4"},
        {"saldo_devedor": "baseline_irpf", "desembolso_mensal_observado_brl": "declarado"},
    ],
)
def test_enum_errado_por_chave_falha(tmp_path, fontes):
    """Cada chave de ``fontes`` tem enum próprio — fonte ilegítima ali falha."""
    item = {
        **_ITEM_MINIMO,
        "parcela_mensal": 1234.56,
        "taxa_juros_aa": 9.5,
        "desembolso_mensal_observado_brl": 1234.56,
        "fontes": fontes,
    }
    assert _validate(tmp_path, item) is False


def test_desembolso_zero_falha(tmp_path):
    """``0.0`` observado no item é indistinguível de 'não medi' — exclusiveMinimum."""
    item = {
        **_ITEM_MINIMO,
        "desembolso_mensal_observado_brl": 0.0,
        "fontes": {
            "saldo_devedor": "baseline_irpf",
            "desembolso_mensal_observado_brl": "observado_e4",
        },
    }
    assert _validate(tmp_path, item) is False


def test_taxa_juros_legado_nao_e_mais_aceito(tmp_path):
    """O apelido antigo ``taxa_juros`` cai no ``additionalProperties: false``."""
    item = {k: v for k, v in _ITEM_MINIMO.items() if k != "taxa_juros_aa"}
    assert _validate(tmp_path, {**item, "taxa_juros": 9.5}) is False


def test_descricao_vazia_falha(tmp_path):
    assert _validate(tmp_path, {**_ITEM_MINIMO, "descricao": ""}) is False


@pytest.mark.parametrize("ano", [1999, 2101])
def test_ano_referencia_fora_da_faixa_falha(tmp_path, ano):
    assert _validate(tmp_path, {**_ITEM_MINIMO, "saldo_ano_referencia": ano}) is False


def test_tipo_fora_do_enum_falha(tmp_path):
    assert _validate(tmp_path, {**_ITEM_MINIMO, "tipo": "financiamento_barco"}) is False


# ──────────────────────────────────────────────────────────────────────
# Correspondência — travada por este gate, não pelo schema
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "item",
    [
        pytest.param(
            {**_ITEM_MINIMO, "parcela_mensal": 1234.56},
            id="valor-sem-fonte",
        ),
        pytest.param(
            {
                **_ITEM_MINIMO,
                "fontes": {"saldo_devedor": "baseline_irpf", "parcela_mensal": "declarado"},
            },
            id="fonte-sem-valor",
        ),
    ],
)
def test_bijecao_detecta_discordancia(item):
    with pytest.raises(AssertionError):
        assert_fontes_bijecao(item)


def test_produtor_real_respeita_bijecao():
    """O payload que ``EndividamentoAnalyzer`` emite hoje satisfaz o invariante."""
    analysis = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 200_000},
        [{"nome": "Titular", "data": {"total_dividas": 200_000}}],
    )
    legacy = analysis.to_legacy_dict()
    assert legacy["dividas"], "esperado ≥1 item para o invariante ter o que medir"
    for item in legacy["dividas"]:
        assert_fontes_bijecao(item)


def test_produtor_real_valida_em_strict(tmp_path):
    """Fecha o loop: o item do produtor passa pelo schema v2 sem remendo no teste."""
    analysis = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 200_000},
        [{"nome": "Titular", "data": {"total_dividas": 200_000}}],
    )
    for item in analysis.to_legacy_dict()["dividas"]:
        assert _validate(tmp_path, item) is True


# ──────────────────────────────────────────────────────────────────────
# Unidade — o sufixo `_aa` é semântica, não decoração
# ──────────────────────────────────────────────────────────────────────


def test_taxa_publicada_e_percentual_ao_ano_sem_conversao():
    """Round-trip de UNIDADE: 12,50% a.a. entra e sai 12.5, não 1250 nem 1,04."""
    item = DividaItem(
        descricao="Financiamento imobiliário",
        saldo_devedor=200_000.0,
        taxa_juros_aa=float(Decimal("12.50")),
    )
    assert item.to_dict()["taxa_juros_aa"] == 12.5
    # A RL2 lê a mesma chave e deriva o equivalente mensal — 12,5% a.a. é
    # ~0,99% a.m., abaixo do corte de 1,5% a.m. de "dívida cara".
    mensal = ((1 + 12.5 / 100) ** (1 / 12) - 1) * 100
    assert mensal == pytest.approx(0.986, abs=0.01)


# O classificador é monetário-por-default: com o nome antigo, 12.5 viraria 1250
# cents no snapshot do view-model. O sufixo `_aa` já está em
# `_NON_MONETARY_SUFFIXES` — é ele, e não uma entrada de allowlist, que conserta
# a classe por construção. `saldo_ano_referencia` não tem sufixo reconhecido e
# por isso precisou da entrada nominal.
def test_taxa_nao_e_normalizada_para_centavos_no_snapshot():
    """O nome do campo decide se o snapshot o lê como dinheiro."""
    assert is_monetary("endividamento.dividas[0].taxa_juros") is True
    assert is_monetary("endividamento.dividas[0].taxa_juros_aa") is False
    # Ano-base é inteiro: sem allowlist viraria R$ 20,24 no snapshot.
    assert is_monetary("endividamento.dividas[0].saldo_ano_referencia") is False


def _property_paths(node, nome: str, path: str = "") -> list[str]:
    """Todo ponto do schema que declara uma property chamada ``nome``."""
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in _property_paths(v, nome, f"{path}/{i}")]
    if not isinstance(node, dict):
        return []
    achados = [f"{path}/properties/{nome}"] if nome in (node.get("properties") or {}) else []
    for key, value in node.items():
        achados += _property_paths(value, nome, f"{path}/{key}")
    return achados


def test_contrato_nao_tem_mais_a_chave_legada():
    """Fecha a CLASSE: nenhuma propriedade `taxa_juros` sobrou no schema E5."""
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert _property_paths(schema, "taxa_juros") == []
    assert _property_paths(schema, "taxa_juros_aa"), "esperado o nome novo no contrato"


def test_produtor_nao_emite_a_chave_legada():
    item = DividaItem(descricao="Financiamento imobiliário", saldo_devedor=1.0).to_dict()
    assert "taxa_juros" not in item
    assert "taxa_juros_aa" in item
