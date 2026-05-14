"""Smoke tests para a correção de ir_brackets.deducao_brl_cents (ADR-197 §5)."""

from __future__ import annotations

import importlib
import json

import pytest

# `migration` marker: ver pyproject.toml + ci.yml — opt-in só quando
# backend/alembic/versions/ é tocado.
pytestmark = pytest.mark.migration

correction_module = importlib.import_module(
    "backend.alembic.versions.e1f2a3b4c5d6_correct_ir_brackets_deducao_2024_2026"
)


class TestDeducaoTableCanonical:
    def test_aliquota_0_maps_to_zero(self):
        assert correction_module._DEDUCAO_BY_ALIQUOTA["0.0"] == 0

    def test_aliquota_7_5_maps_to_169_44_brl(self):
        assert correction_module._DEDUCAO_BY_ALIQUOTA["7.5"] == 16944

    def test_aliquota_15_maps_to_381_44_brl(self):
        assert correction_module._DEDUCAO_BY_ALIQUOTA["15.0"] == 38144

    def test_aliquota_22_5_maps_to_662_77_brl(self):
        assert correction_module._DEDUCAO_BY_ALIQUOTA["22.5"] == 66277

    def test_aliquota_27_5_maps_to_896_brl(self):
        assert correction_module._DEDUCAO_BY_ALIQUOTA["27.5"] == 89600

    def test_table_covers_all_five_brackets(self):
        assert set(correction_module._DEDUCAO_BY_ALIQUOTA.keys()) == {
            "0.0",
            "7.5",
            "15.0",
            "22.5",
            "27.5",
        }

    def test_affected_years_are_2024_2025_2026(self):
        assert correction_module._AFFECTED_YEARS == (2024, 2025, 2026)


class TestCorrectBrackets:
    def _seed_brackets_zeroed(self) -> list[dict]:
        return [
            {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": 3391980, "aliquota_pct": "7.5", "deducao_brl_cents": 0},
            {"upper_brl_cents": 4501260, "aliquota_pct": "15.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": 5597616, "aliquota_pct": "22.5", "deducao_brl_cents": 0},
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0},
        ]

    def test_corrects_all_deductions_from_seed_state(self):
        corrected = correction_module._correct_brackets(self._seed_brackets_zeroed())
        assert corrected is not None
        deductions = [b["deducao_brl_cents"] for b in corrected]
        assert deductions == [0, 16944, 38144, 66277, 89600]

    def test_preserves_upper_brl_cents(self):
        corrected = correction_module._correct_brackets(self._seed_brackets_zeroed())
        assert corrected is not None
        uppers = [b["upper_brl_cents"] for b in corrected]
        assert uppers == [2696320, 3391980, 4501260, 5597616, None]

    def test_preserves_aliquota_pct(self):
        corrected = correction_module._correct_brackets(self._seed_brackets_zeroed())
        assert corrected is not None
        aliquotas = [b["aliquota_pct"] for b in corrected]
        assert aliquotas == ["0.0", "7.5", "15.0", "22.5", "27.5"]

    def test_returns_none_when_already_corrected(self):
        already_correct = [
            {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": 3391980, "aliquota_pct": "7.5", "deducao_brl_cents": 16944},
            {"upper_brl_cents": 4501260, "aliquota_pct": "15.0", "deducao_brl_cents": 38144},
            {"upper_brl_cents": 5597616, "aliquota_pct": "22.5", "deducao_brl_cents": 66277},
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 89600},
        ]
        assert correction_module._correct_brackets(already_correct) is None

    def test_accepts_json_string_input(self):
        # SQLite legado pode retornar JSON como str — aceitar ambos.
        raw = json.dumps(self._seed_brackets_zeroed())
        corrected = correction_module._correct_brackets(raw)
        assert corrected is not None
        assert [b["deducao_brl_cents"] for b in corrected] == [0, 16944, 38144, 66277, 89600]

    def test_skips_unknown_aliquota(self):
        # Faixa exótica (ex.: pós-Lei 15.270 com 10% sobretaxa) não é tocada.
        exotic = [
            {"upper_brl_cents": None, "aliquota_pct": "10.0", "deducao_brl_cents": 12345},
        ]
        result = correction_module._correct_brackets(exotic)
        assert result is None

    def test_partial_update_when_only_some_brackets_wrong(self):
        partial = [
            {"upper_brl_cents": 2696320, "aliquota_pct": "0.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": 3391980, "aliquota_pct": "7.5", "deducao_brl_cents": 16944},
            {"upper_brl_cents": 4501260, "aliquota_pct": "15.0", "deducao_brl_cents": 0},
            {"upper_brl_cents": 5597616, "aliquota_pct": "22.5", "deducao_brl_cents": 66277},
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 89600},
        ]
        corrected = correction_module._correct_brackets(partial)
        assert corrected is not None
        assert [b["deducao_brl_cents"] for b in corrected] == [0, 16944, 38144, 66277, 89600]

    def test_returns_none_for_invalid_input(self):
        assert correction_module._correct_brackets(None) is None
        assert correction_module._correct_brackets("not-json") is None
        assert correction_module._correct_brackets(42) is None

    def test_does_not_mutate_input_list(self):
        original = self._seed_brackets_zeroed()
        original_copy = [dict(b) for b in original]
        correction_module._correct_brackets(original)
        assert original == original_copy


class TestZeroDeducoes:
    def test_zeros_corrected_state(self):
        corrected = [
            {"upper_brl_cents": 3391980, "aliquota_pct": "7.5", "deducao_brl_cents": 16944},
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 89600},
        ]
        zeroed = correction_module._zero_deducoes(corrected)
        assert zeroed is not None
        assert all(b["deducao_brl_cents"] == 0 for b in zeroed)

    def test_returns_none_when_already_zero(self):
        zeroed_already = [
            {"upper_brl_cents": None, "aliquota_pct": "27.5", "deducao_brl_cents": 0},
        ]
        assert correction_module._zero_deducoes(zeroed_already) is None


class TestSeedConsistencyWithCorrection:
    """Editar o seed sem revisitar a correção quebra este teste (coordenação forçada)."""

    def test_seed_aliquotas_estao_cobertas_pela_correcao(self):
        seed_module = importlib.import_module(
            "backend.alembic.versions.y3z4a5b6c7d8_seed_fiscal_2024_2026"
        )
        seed_aliquotas = {str(b["aliquota_pct"]) for b in seed_module._IR_BRACKETS_PRE_LEI_15270}
        assert seed_aliquotas == set(correction_module._DEDUCAO_BY_ALIQUOTA.keys())
