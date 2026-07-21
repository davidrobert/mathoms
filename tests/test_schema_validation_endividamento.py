"""A37.l4 (DE-07): contrato tipado de ``endividamento.dividas[]`` no schema E5.

Ausência de parcela/taxa é ``null`` — sentinela "N/D" string em campo numérico
falha a validação; payload real do produtor (EndividamentoAnalyzer) valida.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline_common import validate_artifact  # noqa: E402

_DIVIDA_NULLS = {
    "descricao": "Financiamento imobiliário",
    "saldo_devedor": 500000.0,
    "parcela_mensal": None,
    "taxa_juros": None,
}


def _e5_with_endividamento(divida: dict) -> dict:
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": {"janela": "full", "janela_meses": 0},
        "endividamento": {
            "total_dividas": 500000.0,
            "percentual_patrimonio": 10.0,
            "dividas": [divida],
            "detalhe": "Financiamento imobiliário",
        },
    }


def _validate(tmp_path: Path, divida: dict) -> bool:
    path = tmp_path / "e5.json"
    path.write_text(json.dumps(_e5_with_endividamento(divida)))
    return validate_artifact(path, "e5_analysis.schema.json")


class TestEndividamentoDividasContract:
    def test_null_sentinels_valid(self, tmp_path, monkeypatch):
        """Produtor emite null para parcela/taxa desconhecidas — payload real valida."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        assert _validate(tmp_path, _DIVIDA_NULLS) is True

    def test_rejects_taxa_juros_nd_string(self, tmp_path, monkeypatch):
        """Sentinela "N/D" string em campo numérico falha o contrato."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        assert _validate(tmp_path, {**_DIVIDA_NULLS, "taxa_juros": "N/D"}) is False

    def test_rejects_parcela_mensal_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        assert _validate(tmp_path, {**_DIVIDA_NULLS, "parcela_mensal": "N/D"}) is False

    def test_rejects_divida_sem_required(self, tmp_path, monkeypatch):
        """dividas[] exige descricao + saldo_devedor em strict."""
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        assert _validate(tmp_path, {"descricao": "Financiamento imobiliário"}) is False

    def test_taxa_juros_numerica_valida(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")
        divida = {**_DIVIDA_NULLS, "parcela_mensal": 1234.57, "taxa_juros": 9.5}
        assert _validate(tmp_path, divida) is True
