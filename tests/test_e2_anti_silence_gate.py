"""A38.l3 (ADR-342) — gate anti-silêncio no E2 + contrato de read-path.

Cobre: escalação de 0-tx/fatura-vazia, gate de conservação HARD (allowlist)
vs WARN, exceção de conta sem movimentação, stub inerte no dedup do E3,
pickup do E2-llm tratando stub como não-processado e key unificada.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.services.e3_reconciler_adapter import E3ReconcilerAdapter
from pipeline.domain.services.reconciliation_service import ReconciliationConfig
from pipeline.stages.extract_with_llm import _e2_extract_stem, _find_unprocessed_docs
from scripts.e2.validation import (
    conservation_gap_cents,
    validate_extrato_result,
    validate_fatura_result,
)
from scripts.extract_bank_documents import _artifact_key_for_file


def _extrato_result(n_tx: int = 2, **overrides) -> dict:
    result = {
        "banco": "BancoSintetico",
        "tipo": "extratoconta",
        "tipo_conta": "corrente",
        "moeda": "BRL",
        "periodo": {"inicio": "2026-01-01", "fim": "2026-01-31"},
        "transacoes": [
            {"data": f"2026-01-{5 + i:02d}", "descricao": f"TX SINTETICA {i}", "valor": 10.0}
            for i in range(n_tx)
        ],
        "notas": [],
    }
    result.update(overrides)
    return result


def _substantial_csv(tmp_path: Path) -> Path:
    path = tmp_path / "banco_extratoconta_202601-0_original.csv"
    path.write_text("data,lancamento,valor\n" + "x" * 2000)
    return path


# ---------------------------------------------------------------------------
# Escalação — extrato
# ---------------------------------------------------------------------------


def test_extrato_0tx_com_texto_substancial_escala(tmp_path: Path) -> None:
    result = _extrato_result(n_tx=0)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.empty_result"


def test_extrato_sem_movimentacao_nao_escala(tmp_path: Path) -> None:
    result = _extrato_result(n_tx=0, notas=["Conta sem movimentação no período (saldo estável)"])
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result


# ---------------------------------------------------------------------------
# Gate de conservação — HARD allowlist vs WARN
# ---------------------------------------------------------------------------


def test_conservacao_quebrada_com_semantica_verificada_escala(tmp_path: Path) -> None:
    result = _extrato_result(saldo_inicial=100.0, saldo_final=999.0, conservacao_verificavel=True)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.incomplete_conservation"


def test_conservacao_quebrada_sem_opt_in_do_parser_so_warn(tmp_path: Path) -> None:
    """Layout antigo do Itaú / saldo derivado (Wise/Rico): WARN, nunca escala."""
    result = _extrato_result(saldo_inicial=100.0, saldo_final=999.0)
    issues = validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result
    assert result["warn_reasons"][0]["code"] == "extract.incomplete_conservation"
    assert any(i.startswith("WARN: conservação") for i in issues)


def test_conservacao_fechada_nao_flagga(tmp_path: Path) -> None:
    result = _extrato_result(
        n_tx=2, saldo_inicial=100.0, saldo_final=120.0, conservacao_verificavel=True
    )
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result
    assert "warn_reasons" not in result


def test_conservacao_noop_sem_saldos(tmp_path: Path) -> None:
    assert conservation_gap_cents(_extrato_result()) is None
    result = _extrato_result(conservacao_verificavel=True)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result


# ---------------------------------------------------------------------------
# Escalação — fatura (contrato único)
# ---------------------------------------------------------------------------


def test_fatura_vazia_escala() -> None:
    result = {"transacoes": [], "itens": [], "notas": []}
    validate_fatura_result(result, "banco_fatura_202601.pdf")
    assert result["parse_quality"] == "empty_result"
    assert result["requires_llm_fallback"] is True


def test_fatura_com_saldo_sem_lancamentos_escala() -> None:
    result = {"saldo_atual": 150.0, "transacoes": [], "itens": [], "notas": []}
    validate_fatura_result(result, "banco_fatura_202601.pdf")
    assert result["parse_quality"] == "missing_transactions"
    assert result["requires_llm_fallback"] is True


def test_fatura_ok_nao_escala() -> None:
    result = {
        "saldo_atual": 150.0,
        "transacoes": [{"data": "2026-01-05", "descricao": "X", "valor": 150.0}],
        "itens": [],
        "notas": [],
        "data_vencimento": "2026-02-06",
    }
    validate_fatura_result(result, "banco_fatura_202601.pdf")
    assert result["parse_quality"] == "ok"
    assert "requires_llm_fallback" not in result


# ---------------------------------------------------------------------------
# Read-path — stub inerte no E3, pickup do E2-llm, key unificada
# ---------------------------------------------------------------------------

_KEY = "bancosintetico_extratoconta_202601"


def test_stub_nao_reivindica_key_e_e3_le_o_full_do_llm() -> None:
    """Aceite (a)+(b) da lane: parcial escalado (stub) em extract_statements
    não bloqueia o artefato full do extract_with_llm; zero duplicata."""
    store = InMemoryArtifactStore()
    stub = _extrato_result(n_tx=1, requires_llm_fallback=True)
    store.seed("extract_statements", _KEY, stub)
    store.seed("extract_with_llm", _KEY, _extrato_result(n_tx=3))

    adapter = E3ReconcilerAdapter(ReconciliationConfig())
    statements, _, _, skipped = adapter.load_bank_statements_with_warnings(store)

    assert len(statements) == 1
    assert len(statements[0].transactions) == 3
    assert skipped == 1


def test_artefato_full_continua_com_precedencia_de_stage() -> None:
    store = InMemoryArtifactStore()
    store.seed("extract_statements", _KEY, _extrato_result(n_tx=2))
    store.seed("extract_with_llm", _KEY, _extrato_result(n_tx=5))

    statements = E3ReconcilerAdapter(ReconciliationConfig()).load_bank_statements(store)

    assert len(statements) == 1
    assert len(statements[0].transactions) == 2


def test_pickup_e2llm_trata_stub_como_nao_processado(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    (data_dir / "financial_statements").mkdir(parents=True)
    doc = data_dir / "financial_statements" / f"{_KEY}-0_original.pdf"
    doc.write_bytes(b"%PDF-1.4 sintetico")
    ctx = SimpleNamespace(data_dir=data_dir, e2_dir=tmp_path / "e2")

    store = InMemoryArtifactStore()
    store.seed("extract_statements", _KEY, _extrato_result(requires_llm_fallback=True))
    assert _find_unprocessed_docs(ctx, store) == [doc]

    store.seed("extract_statements", _KEY, _extrato_result(n_tx=2))
    assert _find_unprocessed_docs(ctx, store) == []


def test_key_unificada_entre_writers_deterministico_e_llm() -> None:
    for name in (
        "banco_extratoconta_202601-0_original.pdf",
        "nome com espaço-0_original.pdf",
        ("x" * 95) + "-0_original.pdf",
    ):
        path = Path(name)
        assert _e2_extract_stem(path) == _artifact_key_for_file(path)
