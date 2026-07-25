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


def test_extrato_0tx_sem_observacao_escala_failsafe(tmp_path: Path) -> None:
    """Parser não reporta raw_rows_detected (None) ⇒ fail-safe: escala (ADR-342 §Emenda l14)."""
    result = _extrato_result(n_tx=0)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.empty_result"


def test_extrato_dormante_observado_nao_escala(tmp_path: Path) -> None:
    """0 tx + raw_rows_detected==0 (parser viu 0 candidatas) ⇒ dormência, não escala."""
    result = _extrato_result(n_tx=0, raw_rows_detected=0)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result


def test_extrato_0tx_com_linhas_candidatas_escala(tmp_path: Path) -> None:
    """Fingerprint C6 Global: parser viu linhas (raw_rows_detected>0) e converteu
    zero ⇒ escala MESMO com nota parcial de mês vazio (o incidente A38.l14)."""
    result = _extrato_result(
        n_tx=0,
        raw_rows_detected=57,
        notas=["Sem lançamentos no período (2 mês(es) sem movimentação)"],
    )
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.empty_result"


def test_nota_parcial_nao_e_mais_predicado_de_dormencia(tmp_path: Path) -> None:
    """A nota "sem movimentação" sozinha (sem raw_rows_detected==0) não silencia:
    o gate parou de fazer substring-match em notas."""
    result = _extrato_result(
        n_tx=0, notas=["Sem lançamentos no período (3 mês(es) sem movimentação)"]
    )
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True


# ---------------------------------------------------------------------------
# Gate de conservação — HARD allowlist vs WARN
# ---------------------------------------------------------------------------


def test_conservacao_quebrada_com_semantica_verificada_escala(tmp_path: Path) -> None:
    result = _extrato_result(saldo_inicial=100.0, saldo_final=999.0, conservacao_verificavel=True)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.incomplete_conservation"


def test_conservacao_nao_certificada_acima_do_piso_escala(tmp_path: Path) -> None:
    """ADR-344: gap > piso (R$100) no caminho NÃO-certificado escala com code
    transitório próprio (gap aqui = |100+20−999| = R$879)."""
    result = _extrato_result(saldo_inicial=100.0, saldo_final=999.0)
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.conservation_above_piso"


def test_conservacao_nao_certificada_abaixo_do_piso_so_warn(tmp_path: Path) -> None:
    """ADR-344: gap ≤ piso (R$100) segue WARN como antes (drop pequeno tolerado
    por design até o parser certificar). Gap aqui = |100+20−150| = R$30."""
    result = _extrato_result(saldo_inicial=100.0, saldo_final=150.0)
    issues = validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert "requires_llm_fallback" not in result
    assert result["warn_reasons"][0]["code"] == "extract.incomplete_conservation"
    assert any(i.startswith("WARN: conservação") for i in issues)


def test_conservacao_certificada_1_cent_ainda_hard_escala(tmp_path: Path) -> None:
    """ADR-344: o piso NÃO afeta o caminho certificado — gap de 1 cent (< piso)
    ainda escala HARD (cents-zero, ADR-342 intocado). Gap = |100+20−120.01| = R$0,01."""
    result = _extrato_result(
        n_tx=2, saldo_inicial=100.0, saldo_final=120.01, conservacao_verificavel=True
    )
    validate_extrato_result(result, _substantial_csv(tmp_path), is_csv=True)
    assert result["requires_llm_fallback"] is True
    assert result["escalation_reason"]["code"] == "extract.incomplete_conservation"


def test_piso_e_constante_global_unica_nao_per_banco() -> None:
    """ADR-344: piso é constante global única (veto data-engineer contra per-banco).
    Grep-gate: nenhum override de piso indexado por banco em scripts/e2/."""
    import re
    from pathlib import Path as _P

    from scripts.e2 import validation as _v

    assert isinstance(_v._CONSERVATION_MATERIALITY_PISO_CENTS, int)
    e2_dir = _P(_v.__file__).parent
    per_bank = re.compile(r"piso.*\[.*banco|PISO_POR_BANCO|piso_por_banco", re.I)
    offenders = [p.name for p in e2_dir.rglob("*.py") if per_bank.search(p.read_text())]
    assert offenders == [], f"piso per-banco proibido (ADR-344): {offenders}"


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


# ---------------------------------------------------------------------------
# count_candidate_rows (observação de dormência) + grep-gate
# ---------------------------------------------------------------------------


def test_count_candidate_rows_conta_linhas_de_tx_excluindo_saldo() -> None:
    from scripts.e2.common import count_candidate_rows

    texto = (
        "05/02/2026 SABESP -60,00\n"
        "03/01 Compra US$ 1,234.56\n"  # formato US também conta
        "Saldo do dia 22/07/26 1.500,00\n"  # linha de saldo NÃO conta
        "cabeçalho sem data nem valor\n"
    )
    assert count_candidate_rows(texto) == 2
    assert count_candidate_rows("") == 0


def test_grep_gate_validation_nao_usa_nota_como_predicado_de_dormencia() -> None:
    """Regressão do buraco A38.l14: nenhuma leitura de 'sem movimentação'/'sem
    lançamentos' como controle de fluxo em validation.py."""
    from pathlib import Path as _P

    import scripts.e2.validation as _v

    src = _P(_v.__file__).read_text(encoding="utf-8")
    assert "sem movimenta" not in src.lower()
    assert "sem lançament" not in src.lower() and "sem lancament" not in src.lower()
