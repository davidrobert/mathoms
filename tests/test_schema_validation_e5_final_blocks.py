"""A40.l5 PR4: contratos producer-backed dos blocos finais do E5."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from pipeline.domain.services.e5_lineage import despesa_total_field
from pipeline.domain.services.equilibrio_cerbasi_analyzer import EquilibrioCerbasiAnalyzer
from pipeline.domain.services.irpf_pgbl_capacidade import CapacidadePgbl, PgblStatus
from pipeline.domain.services.lineage_fields import lineage_block
from pipeline.domain.services.orcamento_calculator import OrcamentoProspectivoCalculator
from pipeline.domain.services.previdencia_analyzer import (
    CapacidadePgblIRPF,
    PrevidenciaAnalyzer,
)
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO


def _orcamento() -> dict:
    return (
        OrcamentoProspectivoCalculator()
        .calculate({"alimentacao": 1_200, "saude": 600}, num_months=12)
        .to_legacy_dict()
    )


def _previdencia(*, calculada: bool = False) -> dict:
    capacidade = None
    if calculada:
        capacidade = CapacidadePgblIRPF(
            capacidade=CapacidadePgbl(
                teto=Decimal("12000"),
                aportado=Decimal("0"),
                restante=Decimal("12000"),
                status=PgblStatus.capacidade_disponivel,
                excedente_nao_dedutivel=Decimal("0"),
            ),
            renda_tributavel_anual=Decimal("100000"),
            ano_base=2025,
            fonte="irpf",
        )
    return PrevidenciaAnalyzer().analyze({}, capacidade).to_legacy_dict()


def _equilibrio() -> dict:
    fluxo = {
        "janela_12m": {
            "despesas_por_categoria": {"moradia": 6_000, "aportes": 2_000},
            "receita_recorrente": 10_000,
            "despesa_total": 8_000,
            "n_meses": 12,
        }
    }
    return EquilibrioCerbasiAnalyzer().analyze(fluxo).to_legacy_dict()


def _lineage() -> dict:
    field = despesa_total_field(
        {"despesa_total": 100, "despesas_por_categoria": {"lazer": 100}},
        {
            "dados": {"lazer": []},
            "_lineage": {"signals": {"tx_total": "1", "dedup_collapsed": "0", "dedup_review": "0"}},
        },
    )
    return lineage_block({"fluxo_caixa.despesa_total": field})


def _payload() -> dict:
    return {
        "score": {"valor": 7, "classificacao": "Bom"},
        "patrimonio": {"bruto": 1_000, "liquido": 900},
        "fluxo_caixa": FLUXO_CAIXA_MINIMO,
        "_lineage": _lineage(),
        "orcamento_prospectivo": _orcamento(),
        "previdencia_pgbl": _previdencia(),
        "equilibrio_cerbasi": _equilibrio(),
        "programa_milhas": {},
    }


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


def test_payload_dos_produtores_reais_valida() -> None:
    assert validate_dict(_payload(), "e5_analysis.schema.json") is True


def test_previdencia_aceita_ausencia_e_valores_calculados() -> None:
    payload = _payload()
    assert payload["previdencia_pgbl"]["renda_tributavel_anual"] is None
    assert validate_dict(payload, "e5_analysis.schema.json") is True

    payload["previdencia_pgbl"] = _previdencia(calculada=True)
    assert payload["previdencia_pgbl"]["renda_tributavel_anual"] == 100_000.0
    assert validate_dict(payload, "e5_analysis.schema.json") is True


@pytest.mark.parametrize(
    ("path", "orphan_key"),
    [
        (("orcamento_prospectivo",), "periodo_meses"),
        (("previdencia_pgbl",), "aporte_mensal_atual"),
        (("equilibrio_cerbasi",), "taxa_poupanca_pct"),
        (("equilibrio_cerbasi", "componentes"), "outros"),
    ],
)
def test_chave_que_produtor_nao_emite_falha(path: tuple[str, ...], orphan_key: str) -> None:
    payload = deepcopy(_payload())
    target = payload
    for part in path:
        target = target[part]
    target[orphan_key] = "fantasma"

    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_lineage_signals_exige_valores_string() -> None:
    payload = _payload()
    field = payload["_lineage"]["fields"]["fluxo_caixa.despesa_total"]
    field["signals"]["tx_total"] = 1

    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_campos_fixos_continuam_opcionais() -> None:
    payload = _payload()
    del payload["orcamento_prospectivo"]["legenda"]
    del payload["previdencia_pgbl"]["nota_degradacao"]
    del payload["equilibrio_cerbasi"]["componentes"]

    assert validate_dict(payload, "e5_analysis.schema.json") is True
