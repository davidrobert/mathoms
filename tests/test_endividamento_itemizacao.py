"""Itemização de ``endividamento.dividas[]`` a partir do baseline (RV6-15 · PR2).

O item deixa de ser "um membro que tem dívida" e passa a ser a **dívida**:
fonte é ``baseline["dividas"][]``, itemizado desde a [[ADR-301]]. Cobre o
rótulo derivado, a atribuição de dono por token, o fallback agregado e a
conservação ``Σ saldo_devedor == total_dividas``.

O gate de conservação do golden (``tests/test_e5_conservation_invariants.py``)
só roda no caso ``baseline``; os testes daqui são alimentados pelo produtor e
**não pulam** — teste que se auto-pula não é gate.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.endividamento_analyzer import (  # noqa: E402
    _DESC_SEM_TIPO,
    TIPO_LABEL,
    EndividamentoAnalyzer,
)
from tests.test_endividamento_fontes_bijecao import (  # noqa: E402
    _SCHEMA_PATH,
    _validate,
    assert_fontes_bijecao,
)


@pytest.fixture(autouse=True)
def _strict(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


# ──────────────────────────────────────────────────────────────────────
# PR2 — o item é a DÍVIDA, não "um membro que tem dívida" (ADR-401 D4)
# ──────────────────────────────────────────────────────────────────────


def test_tipo_label_e_total_sobre_o_enum_do_schema():
    """Gate de TOTALIDADE: tipo novo no schema sem rótulo falha aqui, não em prod."""
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    enum = _dividas_item_schema(schema)["properties"]["tipo"]["enum"]
    do_schema = {v for v in enum if v is not None}
    assert set(TIPO_LABEL) == do_schema, (
        f"faltam rótulos: {do_schema - set(TIPO_LABEL)}; " f"sobram: {set(TIPO_LABEL) - do_schema}"
    )


def _dividas_item_schema(schema: dict) -> dict:
    return schema["properties"]["endividamento"]["properties"]["dividas"]["items"]


class _Ident:
    titular_key = "alfa"
    conjuge_key = "beta"
    titular_nome = "Alfa"
    conjuge_nome = "Beta"


# Instância única: identidade é imutável e o construtor dentro de teste
# parametrizado dispara o gate de recomputo do ADR-210.
_IDENT = _Ident()


def _divida(desc, saldo, **kw):
    return {"descricao": desc, "saldo_31_12": {"2024": saldo}, **kw}


def test_saldo_objeto_por_ano_nao_vira_zero():
    """`saldo_31_12` é objeto por ano no schema; lê-lo como escalar some com a dívida."""
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 100_000},
        [],
        dividas_baseline=[_divida("x", 100_000.0, tipo="financiamento_imobiliario")],
        ano_ref="2024",
    )
    assert [d.saldo_devedor for d in r.dividas] == [100_000.0]


def test_um_item_por_divida_nao_por_membro():
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 140_000},
        [{"nome": "Alfa", "data": {"total_dividas": 140_000}}],
        dividas_baseline=[
            _divida("a", 100_000.0, tipo="financiamento_imobiliario", proprietario="Alfa"),
            _divida("b", 40_000.0, tipo="financiamento_veiculo", proprietario="Beta"),
        ],
        ano_ref="2024",
        identity=_IDENT,
    )
    assert len(r.dividas) == 2
    assert [d.descricao for d in r.dividas] == [
        "Financiamento imobiliário",
        "Financiamento de veículo",
    ]
    assert [d.membro for d in r.dividas] == ["Alfa", "Beta"]


def test_nome_de_pessoa_nao_entra_na_descricao():
    """PII/ADR-129: `descricao` é artefato exportado no PDF — nome vai em `membro`."""
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 100_000},
        [],
        dividas_baseline=[
            _divida("x", 100_000.0, tipo="financiamento_imobiliario", proprietario="Alfa")
        ],
        ano_ref="2024",
        identity=_IDENT,
    )
    item = r.dividas[0]
    assert "Alfa" not in item.descricao
    assert item.membro == "Alfa"


def test_desambigua_por_ordinal_so_quando_o_tipo_repete():
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 300_000},
        [],
        dividas_baseline=[
            _divida("a", 100_000.0, tipo="financiamento_imobiliario"),
            _divida("b", 150_000.0, tipo="financiamento_imobiliario"),
            _divida("c", 50_000.0, tipo="consignado"),
        ],
        ano_ref="2024",
    )
    descs = [d.descricao for d in r.dividas]
    assert descs == [
        "Financiamento imobiliário #1",
        "Financiamento imobiliário #2",
        "Empréstimo consignado",
    ]


def test_desambigua_por_codigo_canonico_quando_o_catalogo_resolve():
    r = EndividamentoAnalyzer(resolve_credor_code=lambda c: "itau" if "ita" in c.lower() else None)
    out = r.analyze(
        {"bruto": 1_000_000, "dividas": 250_000},
        [],
        dividas_baseline=[
            _divida("a", 100_000.0, tipo="financiamento_imobiliario", credor="Banco Itau SA"),
            _divida("b", 150_000.0, tipo="financiamento_imobiliario", credor="Outro"),
        ],
        ano_ref="2024",
    )
    assert [d.descricao for d in out.dividas] == [
        "Financiamento imobiliário — itau",
        "Financiamento imobiliário #2",
    ]


def test_divida_conjunta_conta_uma_vez_e_nao_reivindica_dono():
    """`_total_dividas_for` credita a conjunta aos DOIS membros; aqui ela é uma linha."""
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 40_000},
        [],
        dividas_baseline=[
            _divida("x", 40_000.0, tipo="financiamento_veiculo", proprietario="Alfa e Beta")
        ],
        ano_ref="2024",
        identity=_IDENT,
    )
    assert len(r.dividas) == 1
    assert r.dividas[0].saldo_devedor == 40_000.0
    assert r.dividas[0].membro is None


def test_fallback_quando_baseline_nao_e_itemizado():
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 200_000},
        [{"nome": "Alfa", "data": {"total_dividas": 200_000}}],
        dividas_baseline=None,
    )
    item = r.dividas[0]
    assert item.descricao == "Dívida (origem: declaração patrimonial)"
    assert item.tipo is None and item.divida_id is None
    assert item.to_dict()["fontes"] == {"saldo_devedor": "baseline_irpf"}


def test_item_itemizado_valida_em_strict(tmp_path):
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 100_000},
        [],
        dividas_baseline=[
            _divida(
                "x",
                100_000.0,
                tipo="consignado",
                proprietario="Alfa",
                divida_id="h1",
                credor="Banco",
            )
        ],
        ano_ref="2024",
        identity=_IDENT,
    )
    for item in r.to_legacy_dict()["dividas"]:
        assert_fontes_bijecao(item)
        assert _validate(tmp_path, item) is True


# ──────────────────────────────────────────────────────────────────────
# Conservação — o gate do golden pula em corpus sem dívida; aqui não pula
# ──────────────────────────────────────────────────────────────────────


def _cents(v) -> int:
    return int(round(float(v) * 100))


@pytest.mark.parametrize(
    "baseline_dividas,total",
    [
        pytest.param(
            [_divida("a", 100_000.0, tipo="financiamento_imobiliario", proprietario="Alfa")],
            100_000.0,
            id="uma-divida",
        ),
        pytest.param(
            [
                _divida("a", 100_000.0, tipo="financiamento_imobiliario", proprietario="Alfa"),
                _divida("b", 40_000.5, tipo="financiamento_veiculo", proprietario="Beta"),
            ],
            140_000.5,
            id="duas-de-donos-diferentes",
        ),
        pytest.param(
            [_divida("x", 40_000.0, tipo="consignado", proprietario="Alfa e Beta")],
            40_000.0,
            id="conjunta-conta-uma-vez",
        ),
    ],
)
def test_soma_dos_itens_fecha_com_total_dividas(baseline_dividas, total):
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": total},
        [],
        dividas_baseline=baseline_dividas,
        ano_ref="2024",
        identity=_IDENT,
    )
    legacy = r.to_legacy_dict()
    soma = sum(_cents(d["saldo_devedor"]) for d in legacy["dividas"])
    assert soma == _cents(legacy["total_dividas"])


def test_conservacao_pega_dupla_contagem_de_conjunta():
    """Mutação: creditar a conjunta aos DOIS membros — o defeito vivo de
    `patrimonio_resolvers._total_dividas_for` — quebra o invariante."""
    conjunta = _divida("x", 40_000.0, tipo="consignado", proprietario="Alfa e Beta")
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 40_000.0},
        [],
        dividas_baseline=[conjunta, dict(conjunta)],  # a mesma dívida, duas vezes
        ano_ref="2024",
        identity=_IDENT,
    )
    legacy = r.to_legacy_dict()
    soma = sum(_cents(d["saldo_devedor"]) for d in legacy["dividas"])
    assert soma != _cents(legacy["total_dividas"]), "invariante cego à dupla contagem"


def test_conservacao_pega_saldo_lido_como_escalar():
    """Mutação: ler `saldo_31_12` (objeto por ano) como escalar zera o item."""
    r = EndividamentoAnalyzer().analyze(
        {"bruto": 1_000_000, "dividas": 100_000.0},
        [],
        dividas_baseline=[_divida("a", 100_000.0, tipo="consignado")],
        ano_ref="1999",  # ano ausente força o fallback de maior ano disponível
    )
    assert [d.saldo_devedor for d in r.dividas] == [100_000.0]


# ──────────────────────────────────────────────────────────────────────
# `descricao` é PII-free POR CONSTRUÇÃO — independente de redação a jusante
# ──────────────────────────────────────────────────────────────────────

# Vocabulário fechado: 8 rótulos de tipo + o de origem desconhecida, com
# sufixo opcional de código canônico ou ordinal. Nada mais pode sair daqui.
_DESCRICAO_PERMITIDA = re.compile(
    r"^(?:"
    + "|".join(re.escape(v) for v in [*TIPO_LABEL.values(), _DESC_SEM_TIPO])
    + r")(?: — [a-z0-9_]{2,32}| #\d+)?$"
)


def _descricoes(dividas_baseline, **kw):
    r = EndividamentoAnalyzer(**kw).analyze(
        {"bruto": 1_000_000, "dividas": 1.0},
        [],
        dividas_baseline=dividas_baseline,
        ano_ref="2024",
        identity=_IDENT,
    )
    return [d.descricao for d in r.dividas]


# Independente de redação a jusante: se o #1569 aplicar `redact_cartorial` por
# cima, ele vira cinto-e-suspensório. Se este teste só passasse COM a redação,
# o fix teria virado dependente dela.
def test_descricao_sai_do_vocabulario_fechado_mesmo_com_baseline_sujo():
    """Texto livre do baseline NÃO alcança `descricao` — ela é reconstruída."""
    sujo = [
        _divida(
            "Financiamento c/ FULANO DE TAL, CPF 000.000.000-00, matr. 12.345 do 2º CRI",
            100_000.0,
            tipo="financiamento_imobiliario",
            proprietario="Alfa",
            credor="Banco Fulano de Tal S.A. — Agência 1234",
            numero_contrato="8899-77/2021",
        )
    ]
    for desc in _descricoes(sujo):
        assert _DESCRICAO_PERMITIDA.match(desc), f"vocabulário violado: {desc!r}"
        for vazado in ("FULANO", "Fulano", "000.000.000", "12.345", "8899", "Agência"):
            assert vazado not in desc


def test_resolver_de_credor_que_devolve_texto_livre_e_rejeitado():
    """A única porta de dado externo na `descricao` é peneirada na origem."""
    duas = [
        _divida("a", 100_000.0, tipo="consignado", credor="Banco Fulano de Tal S.A."),
        _divida("b", 50_000.0, tipo="consignado", credor="Outro"),
    ]
    # Resolver hostil: devolve razão social por extenso em vez de código.
    descs = _descricoes(duas, resolve_credor_code=lambda c: c)
    assert descs == ["Empréstimo consignado #1", "Empréstimo consignado #2"]
    for d in descs:
        assert _DESCRICAO_PERMITIDA.match(d)
    # Resolver bem-comportado continua desambiguando pelo código canônico.
    ok = _descricoes(duas, resolve_credor_code=lambda c: "c6bank" if "Fulano" in c else None)
    assert ok == ["Empréstimo consignado — c6bank", "Empréstimo consignado #2"]
