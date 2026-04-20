"""Tests — Fase 3.2 Caminho B: E2 via ArtifactStore + BankStatement adapter."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.models import BankStatement, Money  # noqa: E402


class TestBankStatementFromE2Dict:
    def test_round_trip_minimal(self):
        d = {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extrato",
            "moeda": "BRL",
            "periodo_inicio": "2026-01-01",
            "periodo_fim": "2026-01-31",
            "transacoes": [
                {"data": "2026-01-05", "descricao": "Salario", "valor": 5000.0},
                {"data": "2026-01-10", "descricao": "Mercado", "valor": -300.5},
            ],
        }
        stmt = BankStatement.from_e2_dict(d)
        assert stmt.institution == "itau"
        assert stmt.currency == "BRL"
        assert stmt.period_start == date(2026, 1, 1)
        assert stmt.period_end == date(2026, 1, 31)
        assert len(stmt.transactions) == 2
        assert stmt.transactions[0].amount == Money.brl("5000")
        assert stmt.transactions[1].amount == Money.brl("-300.50")

    def test_preserves_opening_closing_balance(self):
        d = {
            "banco": "bradesco", "tipo": "extrato", "moeda": "BRL",
            "periodo_inicio": "2026-01-01", "periodo_fim": "2026-01-31",
            "saldo_inicial": 1000.0, "saldo_final": 2500.0,
            "transacoes": [],
        }
        stmt = BankStatement.from_e2_dict(d)
        assert stmt.opening_balance == Money.brl("1000")
        assert stmt.closing_balance == Money.brl("2500")

    def test_transfers_notes(self):
        d = {
            "banco": "santander", "tipo": "extrato", "moeda": "BRL",
            "periodo_inicio": "2026-01-01", "periodo_fim": "2026-01-31",
            "transacoes": [],
            "notas": ["WARN: saldo inconsistente", "INFO: extracted from CSV"],
        }
        stmt = BankStatement.from_e2_dict(d)
        assert stmt.notes == ["WARN: saldo inconsistente", "INFO: extracted from CSV"]

    def test_round_trip_via_to_e2_dict(self):
        d1 = {
            "banco": "c6bank", "tipo": "extrato", "moeda": "BRL",
            "periodo_inicio": "2026-02-01", "periodo_fim": "2026-02-28",
            "saldo_inicial": 500.0, "saldo_final": 600.0,
            "transacoes": [
                {"data": "2026-02-10", "descricao": "X", "valor": 100.0},
            ],
        }
        stmt = BankStatement.from_e2_dict(d1)
        d2 = stmt.to_e2_dict()
        # Round-trip preserva campos essenciais
        assert d2["banco"] == d1["banco"]
        assert d2["moeda"] == d1["moeda"]
        assert d2["periodo_inicio"] == d1["periodo_inicio"]
        assert d2["periodo_fim"] == d1["periodo_fim"]
        assert d2["saldo_inicial"] == d1["saldo_inicial"]
        assert d2["saldo_final"] == d1["saldo_final"]
        assert len(d2["transacoes"]) == 1
        assert d2["transacoes"][0]["valor"] == 100.0


class TestRunWithStoreNoFiles:
    """Smoke: ``run_with_store`` não quebra em diretório vazio e não toca disco."""

    def test_no_files_returns_empty_stats(self, tmp_path, monkeypatch):
        # Configurar pipeline_common apontando para tmp_path vazio
        monkeypatch.setenv("MATHOMS_WORKSPACE_ROOT", str(tmp_path))
        data_dir = tmp_path / "data" / "financial_statements"
        data_dir.mkdir(parents=True)

        # Reinit paths
        import scripts.pipeline_common as _pc
        _pc.init_workspace_paths_from_env(strict=False)
        from scripts.e2.common import _init_config as _e2_init
        _e2_init(tmp_path)

        from scripts.e2_extract import run_with_store

        store = InMemoryArtifactStore()
        stats = run_with_store(store=store, extratos_only=True)

        assert stats["processados"] == 0
        assert stats["transacoes_total"] == 0
        assert store.list_keys("E2-extratos") == []
        assert store.list_keys("E2-faturas") == []


class TestArtifactKey:
    def test_strips_0_original_suffix(self):
        from scripts.e2_extract import _artifact_key_for_file

        p = Path("/x/itau_extratoconta_202601_202602-0_original.pdf")
        assert _artifact_key_for_file(p) == "itau_extratoconta_202601_202602"

    def test_no_original_kept_as_is(self):
        from scripts.e2_extract import _artifact_key_for_file

        p = Path("/x/some_file.csv")
        assert _artifact_key_for_file(p) == "some_file"


class TestTargetStageSelection:
    def test_faturas_only_forces_e2_faturas(self):
        from scripts.e2_extract import _target_stage_for_file

        p = Path("/x/c6bank_extratoconta_202601-0_original.pdf")
        assert _target_stage_for_file(p, extratos_only=False, faturas_only=True) == "E2-faturas"

    def test_extratos_only_forces_e2_extratos(self):
        from scripts.e2_extract import _target_stage_for_file

        p = Path("/x/c6bank_fatura_202601-0_original.pdf")
        assert _target_stage_for_file(p, extratos_only=True, faturas_only=False) == "E2-extratos"

    def test_unified_mode_decides_by_filename(self):
        from scripts.e2_extract import _target_stage_for_file

        fatura = Path("/x/c6bank_fatura_202601-0_original.pdf")
        extrato = Path("/x/c6bank_extratoconta_202601-0_original.pdf")
        assert _target_stage_for_file(fatura, extratos_only=False, faturas_only=False) == "E2-faturas"
        assert _target_stage_for_file(extrato, extratos_only=False, faturas_only=False) == "E2-extratos"
