"""Contrato producer-backed da raiz `tributario` do E5 ([[ADR-236]] §D3/§D4/§D6, [[ADR-238]] D5).

A raiz era emitida em 52/54 artefatos do corpus local e não era declarada — passava
pelo `additionalProperties: true` da raiz do schema. O corpus, porém, é degenerado:
todos os artefatos estão no ramo `regime_nao_suportado`, com `regime`, `fator_r_*` e
`financeiro_pj_snapshot` nulos em 52/52. Derivar o contrato dele declararia
`"type": "null"` em campos que só são nulos NESTE corpus.

Por isso o conjunto declarado é comparado por IGUALDADE DE CONJUNTO contra o que sai
de RODAR o produtor, nos 4 ramos de `compute` — nunca contra lista à mão nem contra o
corpus.
"""

from __future__ import annotations

import dataclasses
from copy import deepcopy
from decimal import Decimal
from typing import Any

import pytest

from pipeline.domain.goals_bundle import TributarioBundleSection
from pipeline.domain.models.transaction import Money
from pipeline.domain.services.tributario.cascata_calculator import (
    CascataInput,
    CascataOutput,
    FinanceiroPJSnapshot,
    PrevidenciaSnapshot,
    compute,
)
from pipeline.domain.services.tributario.cascata_serialization import cascata_to_dict
from scripts.pipeline_common import _schema_to_validate, validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO

SCHEMA = "e5_analysis.schema.json"


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


def _previdencia() -> PrevidenciaSnapshot:
    return PrevidenciaSnapshot(
        planos_pgbl_count=2,
        planos_vgbl_count=1,
        aporte_pgbl_realizado_anual=Money.brl("10000"),
        saldo_total_31_12=Money.brl("350000"),
    )


def _financeiro_pj() -> FinanceiroPJSnapshot:
    # `regime_declarado` vem da extração de informes e usa OUTRO vocabulário
    # (`simples_nacional`), não o de `tributario.regime` (`simples`).
    return FinanceiroPJSnapshot(
        informes_count=3,
        receita_bruta_total_anual=Money.brl("580000"),
        retencoes_totais_anuais=Money.brl("21000"),
        regime_declarado="simples_nacional",
        ano_base_coberto=2024,
    )


def _completo(regime: str, anexo: str | None = None) -> CascataInput:
    return CascataInput(
        regime=regime,
        anexo_simples=anexo,
        iss_aliquota_pct=Decimal("0.05"),
        tipo_declaracao_ir="completa",
        receita_pj_anual=Money.brl("600000"),
        pro_labore_mensal=Money.brl("8000"),
        lucros_distribuidos_mensal=Money.brl("20000"),
        folha_pj_mensal=Money.brl("9000"),
        renda_tributavel_pf_irpf_anual=Money.brl("250000"),
        renda_tributavel_pf_ano_base=2024,
        previdencia_snapshot=_previdencia(),
        financeiro_pj_snapshot=_financeiro_pj(),
    )


#: Os 4 ramos de `compute` + os regimes suportados. O corpus só exercita o 1º.
RAMOS: dict[str, CascataInput] = {
    "perfil_incompleto": CascataInput(),
    "lucro_real": CascataInput(regime="lucro_real", receita_pj_anual=Money.brl("900000")),
    "anexo_simples_pendente": CascataInput(regime="simples", receita_pj_anual=Money.brl("300000")),
    "simples_iii": _completo("simples", "III"),
    "simples_v": _completo("simples", "V"),
    "lucro_presumido": _completo("lucro_presumido"),
    "mei": _completo("mei"),
    # T4 é o ÚNICO caminho que emite `int` cru em `triggers[].params`.
    "t4_holding": dataclasses.replace(
        _completo("simples", "V"),
        imoveis_alugados_count=4,
        receita_aluguel_anual=Money.brl("120000"),
    ),
}


def _tributario(inp: CascataInput) -> dict[str, Any]:
    """Espelha `_assemble_tributario_section` (pipeline_adapter) sem importar backend."""
    cascata = cascata_to_dict(compute(inp))
    return {
        "regime": cascata["regime"],
        "regime_label": cascata["regime_label"],
        "cascata": cascata,
        "contador_nome": None,
        "holding_prazo_meses": None,
        "_source": "db:business_profile_json + e3/e4/e1.6 derived",
    }


def _payload(inp: CascataInput) -> dict[str, Any]:
    return {
        "score": {"valor": 7, "classificacao": "Bom"},
        "patrimonio": {"bruto": 1_000, "liquido": 900},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "tributario": _tributario(inp),
    }


def _schema() -> dict[str, Any]:
    schema, _ = _schema_to_validate(SCHEMA)
    assert (
        schema is not None
    ), f"schema {SCHEMA} nao resolveu — nome errado short-circuita validate_dict"
    return schema


def _declarado(*path: str) -> set[str]:
    node = _schema()["properties"]["tributario"]
    for part in path:
        node = node["properties"][part]
        if "$ref" in node:  # pragma: no cover - defensivo
            raise AssertionError("resolva o $ref antes de comparar")
    return set(node["properties"])


def _defs(name: str) -> dict[str, Any]:
    return _schema()["$defs"][name]


# ─────────────────────────── igualdade de conjunto ───────────────────────────


def test_cascata_declarada_e_o_que_o_produtor_emite() -> None:
    """Igualdade nos DOIS sentidos: campo novo no produtor e campo fantasma no schema."""
    assert _declarado("cascata") == {f.name for f in dataclasses.fields(CascataOutput)}


def test_raiz_declarada_e_o_que_o_bundle_declara() -> None:
    assert _declarado() == set(TributarioBundleSection.__annotations__)


@pytest.mark.parametrize(
    ("nome", "dataclass"),
    [("PrevidenciaSnapshot", PrevidenciaSnapshot), ("FinanceiroPJSnapshot", FinanceiroPJSnapshot)],
)
def test_snapshot_declarado_casa_com_a_dataclass(nome: str, dataclass: type) -> None:
    declarado = set(_defs(nome)["properties"])
    assert declarado == {f.name for f in dataclasses.fields(dataclass)}
    assert set(_defs(nome)["required"]) == declarado


def test_uniao_dos_ramos_nao_emite_chave_fora_do_schema() -> None:
    """O corpus só exercita `perfil_incompleto`; a união dos 4 ramos é o universo real."""
    emitidas: set[str] = set()
    for inp in RAMOS.values():
        emitidas |= set(cascata_to_dict(compute(inp)))
    assert emitidas == _declarado("cascata")


# ──────────────────────────────── positivo ───────────────────────────────────


@pytest.mark.parametrize("ramo", sorted(RAMOS))
def test_todo_ramo_do_produtor_valida(ramo: str) -> None:
    assert validate_dict(_payload(RAMOS[ramo]), SCHEMA) is True


def test_ramo_completo_publica_os_campos_que_o_corpus_tem_nulos() -> None:
    """Guarda contra derivar o contrato do corpus degenerado."""
    cascata = _payload(RAMOS["simples_v"])["tributario"]["cascata"]
    assert cascata["regime"] == "simples"
    assert cascata["fator_r_faixa"] in {"anexo_iii", "anexo_v"}
    assert isinstance(cascata["fator_r_pct"], float)
    assert cascata["financeiro_pj_snapshot"] is not None


def test_t4_emite_int_em_params_e_o_contrato_aceita() -> None:
    """`params` mistura string e int; declarar `string` reprovaria este caminho."""
    triggers = _payload(RAMOS["t4_holding"])["tributario"]["cascata"]["triggers"]
    t4 = next(t for t in triggers if t["code"] == "T4")
    assert isinstance(t4["params"]["imoveis_alugados_count"], int)
    assert isinstance(t4["params"]["receita_aluguel_anual_brl"], str)


def test_canais_deliberadamente_abertos_seguem_abertos() -> None:
    """`signals` e `regime_declarado` são abertos por decisão do produtor."""
    payload = _payload(RAMOS["simples_v"])
    payload["tributario"]["cascata"]["signals"] = ["sinal_de_dominio_novo"]
    assert validate_dict(payload, SCHEMA) is True


# ──────────────────────────────── negativo ───────────────────────────────────


def _mutado(ramo: str, mutacao) -> dict[str, Any]:
    payload = deepcopy(_payload(RAMOS[ramo]))
    mutacao(payload["tributario"])
    return payload


@pytest.mark.parametrize(
    ("rotulo", "mutacao"),
    [
        ("money virou string", lambda t: t["cascata"].__setitem__("receita_bruta", "1.234,56")),
        ("bool virou string", lambda t: t["cascata"].__setitem__("pgbl_aplicavel", "sim")),
        (
            "Money nao normalizado",
            lambda t: t["cascata"].__setitem__(
                "pgbl_base_anual", {"amount": "1", "currency": "BRL"}
            ),
        ),
        ("faixa com vocab do input", lambda t: t["cascata"].__setitem__("fator_r_faixa", "III")),
        ("regime fora do enum", lambda t: t.__setitem__("regime", "lucro_arbitrado")),
        (
            "motivo fora do enum",
            lambda t: t["cascata"].__setitem__("motivo_nao_suportado", "motivo_novo"),
        ),
        ("trigger como string", lambda t: t["cascata"].__setitem__("triggers", ["T1"])),
        (
            "severity fora do enum",
            lambda t: t["cascata"].__setitem__(
                "triggers", [{"code": "T1", "severity": "urgente", "title": "x", "params": {}}]
            ),
        ),
        ("holding_prazo_meses string", lambda t: t.__setitem__("holding_prazo_meses", "24 meses")),
        ("regime_label nulo", lambda t: t.__setitem__("regime_label", None)),
        ("chave fantasma na cascata", lambda t: t["cascata"].__setitem__("campo_fantasma", 1)),
        ("chave fantasma na raiz", lambda t: t.__setitem__("campo_fantasma", 1)),
        ("campo removido da cascata", lambda t: t["cascata"].pop("carga_total_pct")),
        ("campo removido da raiz", lambda t: t.pop("contador_nome")),
        (
            "snapshot com chave fantasma",
            lambda t: t["cascata"]["previdencia_snapshot"].__setitem__("fantasma", 1),
        ),
    ],
)
def test_mutacao_plausivel_reprova(rotulo: str, mutacao) -> None:
    assert validate_dict(_mutado("simples_v", mutacao), SCHEMA) is False


def test_tributario_ausente_continua_valido() -> None:
    """`analyze_finances` escreve o artefato ANTES de `generate_narratives` mergear o bloco."""
    payload = _payload(RAMOS["simples_v"])
    del payload["tributario"]
    assert validate_dict(payload, SCHEMA) is True


def test_source_e_opcional() -> None:
    payload = _payload(RAMOS["simples_v"])
    del payload["tributario"]["_source"]
    assert validate_dict(payload, SCHEMA) is True
