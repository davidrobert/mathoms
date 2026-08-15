"""Tests para fiscal_parsers — DB row ↔ FiscalParameters (A7.2b · ADR-135)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.adapters.fiscal_parsers import (  # noqa: E402
    TabelaProgressivaMalformada,
    fiscal_payload_to_dataclass,
    fiscal_row_to_payload,
)
from pipeline.domain.types.config import (  # noqa: E402
    FiscalParameters,
    IRPFBracket,
    TabelaProgressiva,
)


@dataclass
class _StubRow:
    year: int
    ir_brackets_anual: dict
    ir_brackets_mensal: dict
    regime_completo: bool
    componentes_ausentes: list
    pgbl_limit_brl_cents: int
    inss_ceiling_brl_cents: int
    lucro_presumido_aliquota: Decimal
    effective_from: date | None
    effective_to: date | None
    source: str


_ANUAL_STUB = {
    "faixas": [
        {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
        {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0},
    ],
    "vigencia_ref": "Exercício de 2026, ano-calendário de 2025",
    "source": "test-source",
    "motivo_divergencia_x12": "",
}

_MENSAL_STUB = {
    "faixas": [
        {"upper_brl_cents": 242880, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
        {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 90873},
    ],
    "vigencia_ref": "maio/2025 em diante",
    "source": "test-source",
    "motivo_divergencia_x12": "",
}


def _stub_row() -> _StubRow:
    return _StubRow(
        year=2025,
        ir_brackets_anual=_ANUAL_STUB,
        ir_brackets_mensal=_MENSAL_STUB,
        regime_completo=True,
        componentes_ausentes=[],
        pgbl_limit_brl_cents=0,
        inss_ceiling_brl_cents=0,
        lucro_presumido_aliquota=Decimal("0.32"),
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
        source="test-source",
    )


# ---------------------------------------------------------------------------
# fiscal_row_to_payload
# ---------------------------------------------------------------------------


class TestRowToPayload:
    def test_serializes_to_json_safe_dict(self):
        payload = fiscal_row_to_payload(_stub_row())
        assert payload["year"] == 2025
        # Decimal vira string (JSON-safe)
        assert payload["lucro_presumido_aliquota"] == "0.32"
        # Datas vão como ISO
        assert payload["effective_from"] == "2025-01-01"
        assert payload["effective_to"] == "2025-12-31"

    def test_handles_open_ended_effective_to(self):
        row = _stub_row()
        row.effective_to = None
        payload = fiscal_row_to_payload(row)
        assert payload["effective_to"] is None


# ---------------------------------------------------------------------------
# fiscal_payload_to_dataclass
# ---------------------------------------------------------------------------


class TestPayloadToDataclass:
    def test_roundtrip(self):
        row = _stub_row()
        payload = fiscal_row_to_payload(row)
        fp = fiscal_payload_to_dataclass(payload)
        assert isinstance(fp, FiscalParameters)
        assert fp.year == row.year
        assert fp.lucro_presumido_aliquota == row.lucro_presumido_aliquota
        assert fp.effective_from == row.effective_from
        assert fp.effective_to == row.effective_to

    def test_brackets_are_typed(self):
        fp = fiscal_payload_to_dataclass(fiscal_row_to_payload(_stub_row()))
        faixas = fp.ir_brackets_anual.faixas
        assert all(isinstance(b, IRPFBracket) for b in faixas)
        assert faixas[-1].upper_brl_cents is None
        assert faixas[-1].aliquota_pct == Decimal("27.5")
        # A proveniência viaja com a tabela, não com a row (ADR-389 D2).
        assert fp.ir_brackets_anual.vigencia_ref.startswith("Exercício de 2026")
        assert fp.ir_brackets_mensal.faixas[-1].deducao_brl_cents == 90873

    def test_handles_missing_optional_fields(self):
        fp = fiscal_payload_to_dataclass({"year": 2030})
        assert fp.year == 2030
        assert fp.ir_brackets_anual == TabelaProgressiva()
        assert fp.ir_brackets_mensal == TabelaProgressiva()
        assert fp.regime_completo is True
        assert fp.lucro_presumido_aliquota == Decimal("0")


class TestFailClosed:
    """A40.l56 · ADR-389: chave ausente levanta, em vez de virar zero ou terminal."""

    def _tabela(self, faixas):
        return {"faixas": faixas}

    def test_deducao_ausente_levanta(self):
        with pytest.raises(TabelaProgressivaMalformada, match="deducao_brl_cents"):
            fiscal_payload_to_dataclass(
                {"ir_brackets_anual": self._tabela([{"upper_brl_cents": 1, "aliquota_pct": "7.5"}])}
            )

    # O pior fail-open do bloco, e não era o `or 0`: `upper_brl_cents` ausente
    # virava ``None``, que é a faixa TERMINAL — `resolve_faixa_marginal` retornava
    # na primeira, truncando a tabela e aplicando alíquota errada a toda renda.
    def test_upper_ausente_levanta_e_nao_vira_faixa_terminal(self):
        """Chave ausente levanta em vez de promover a faixa a terminal."""
        with pytest.raises(TabelaProgressivaMalformada, match="upper_brl_cents"):
            fiscal_payload_to_dataclass(
                {
                    "ir_brackets_anual": self._tabela(
                        [{"aliquota_pct": "7.5", "deducao_brl_cents": 0}]
                    )
                }
            )

    def test_faixa_que_nao_e_objeto_levanta_em_vez_de_ser_pulada(self):
        with pytest.raises(TabelaProgressivaMalformada, match="não é objeto"):
            fiscal_payload_to_dataclass({"ir_brackets_anual": self._tabela(["7.5"])})

    def test_upper_none_explicito_continua_sendo_a_terminal(self):
        """Ausência levanta; ``None`` declarado é a faixa terminal legítima."""
        fp = fiscal_payload_to_dataclass(
            {
                "ir_brackets_anual": self._tabela(
                    [{"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 1}]
                )
            }
        )
        assert fp.ir_brackets_anual.faixas[0].upper_brl_cents is None

    def test_regime_incompleto_viaja_no_dado(self):
        """ADR-389 D4: o consumidor recusa lendo a row, não com `if year >= 2026`."""
        fp = fiscal_payload_to_dataclass(
            {"year": 2026, "regime_completo": False, "componentes_ausentes": ["irpfm"]}
        )
        assert fp.regime_completo is False
        assert fp.componentes_ausentes == ("irpfm",)
