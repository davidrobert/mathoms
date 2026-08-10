"""[[A40.l2]] PR3c1b: contrato de ``fluxo_caixa.consolidacao_cross_documento`` no schema E5.

O payload válido vem do **produtor real** (`FluxoCaixaEnricher`), não montado à mão — teste
alimentado por dado inventado prova o schema contra si mesmo, não contra o que o pipeline
emite. As rejeições são as três formas que a lane identificou como perigosas, cada uma por um
motivo medido, não estético.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.fluxo_caixa_enricher import FluxoCaixaEnricher  # noqa: E402
from scripts.pipeline_common import validate_artifact  # noqa: E402

_MESES = ["2026-01", "2026-02"]
_CONSOLIDACAO = {
    "count": 7,
    "meses": [{"mes": "2026-01", "count": 3}, {"mes": "2026-02", "count": 4}],
}


def _fluxo_caixa_do_produtor(consolidacao: dict | None) -> dict:
    e4: dict = {
        "meses_ordenados": _MESES,
        "receitas": {"por_mes": {}},
        "despesas": {"por_mes": {}},
    }
    if consolidacao is not None:
        e4["consolidacao_cross_documento"] = consolidacao
    return FluxoCaixaEnricher().enrich(receitas={}, despesas={}, fluxo_mensal=e4).to_legacy_dict()


def _e5(fluxo_caixa: dict) -> dict:
    return {
        "score": {"valor": 6.8, "classificacao": "Bom"},
        "patrimonio": {"bruto": 5000000, "liquido": 4000000},
        "fluxo_caixa": fluxo_caixa,
    }


def _validate(tmp_path: Path, fluxo_caixa: dict) -> bool:
    path = tmp_path / "e5.json"
    path.write_text(json.dumps(_e5(fluxo_caixa)))
    return validate_artifact(path, "e5_analysis.schema.json")


@pytest.fixture(autouse=True)
def _strict(monkeypatch):
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


class TestConsolidacaoCrossDocumentoContract:
    def test_payload_do_produtor_valida(self, tmp_path):
        assert _validate(tmp_path, _fluxo_caixa_do_produtor(_CONSOLIDACAO)) is True

    def test_omissao_e_legal(self, tmp_path):
        """Ausência é o estado normal: só há campo quando o enforce removeu alguma row."""
        fluxo = _fluxo_caixa_do_produtor(None)

        assert "consolidacao_cross_documento" not in fluxo
        assert _validate(tmp_path, fluxo) is True

    def test_rejeita_mes_como_inteiro(self, tmp_path):
        """`202601` em vez de `"2026-01"` é a forma que `golden_diff.is_monetary("meses")`
        multiplicaria por 100 no snapshot — o leaf ser string é o que neutraliza."""
        fluxo = _fluxo_caixa_do_produtor(_CONSOLIDACAO)
        fluxo["consolidacao_cross_documento"] = {"count": 1, "meses": [{"mes": 202601, "count": 1}]}

        assert _validate(tmp_path, fluxo) is False

    def test_rejeita_meses_como_mapa(self, tmp_path):
        """Mapa põe o mês na CHAVE, e aí o leaf também sai monetário. Só lista sobrevive."""
        fluxo = _fluxo_caixa_do_produtor(_CONSOLIDACAO)
        fluxo["consolidacao_cross_documento"] = {"count": 1, "meses": {"2026-01": 1}}

        assert _validate(tmp_path, fluxo) is False

    def test_rejeita_count_zero(self, tmp_path):
        """`count: 0` significa que o produtor devia ter OMITIDO o campo. Presença
        incondicional muda o sha256 do E5, que é chave de cache do parecer e do section
        summary da S2 — regeraria os dois em toda a base (hard-stop da [[ADR-173]])."""
        fluxo = _fluxo_caixa_do_produtor(_CONSOLIDACAO)
        fluxo["consolidacao_cross_documento"] = {"count": 0, "meses": []}

        assert _validate(tmp_path, fluxo) is False

    def test_janela_12m_carrega_o_mesmo_contrato(self, tmp_path):
        """A projeção usa o mesmo `$def` — contrato divergente entre os dois níveis seria a
        porta para o contador do corpus e o da janela deixarem de reconciliar."""
        fluxo = _fluxo_caixa_do_produtor(_CONSOLIDACAO)
        fluxo["janela_12m"]["consolidacao_cross_documento"] = {
            "count": 1,
            "meses": [{"mes": 202601, "count": 1}],
        }

        assert _validate(tmp_path, fluxo) is False
