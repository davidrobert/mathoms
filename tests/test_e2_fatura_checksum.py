"""A39.l3 — _apply_fatura_checksum é escopo-aware: soma só as tx cujo `escopo`
casa `signal.escopo` (o schema #1036 já declara `escopo` no signal; o gate
ignorava). Sem isso, fatura com pagamento/exterior/IOF false-fira contra o
`total_compras` (só despesa-Brasil)."""

from __future__ import annotations

from scripts.e2.validation import _apply_fatura_checksum


def _fatura(transacoes, valor_cents, escopo="despesa_brasil"):
    return {
        "transacoes": transacoes,
        "total_lancamentos_conferivel": {"valor_cents": valor_cents, "escopo": escopo},
    }


def test_soma_so_o_subconjunto_do_escopo() -> None:
    # despesa_brasil = 150,00; pagamento/exterior/iof excluídos → fecha em 15000 cents.
    r = _fatura(
        [
            {"valor": 100.0, "escopo": "despesa_brasil"},
            {"valor": 50.0, "escopo": "despesa_brasil"},
            {"valor": -200.0, "escopo": "pagamento"},
            {"valor": 300.0, "escopo": "exterior"},
            {"valor": 5.0, "escopo": "iof_exterior"},
        ],
        valor_cents=15000,
    )
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert issues == []
    assert "review_reasons" not in r or not r.get("review_reasons")


def test_mismatch_no_escopo_dispara_warn() -> None:
    r = _fatura([{"valor": 100.0, "escopo": "despesa_brasil"}], valor_cents=20000)
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert any("Σ lançamentos" in i for i in issues)


def test_sem_signal_nao_faz_nada() -> None:
    r = {"transacoes": [{"valor": 100.0, "escopo": "despesa_brasil"}]}
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert issues == []


def test_soma_todas_tx_do_escopo_ignora_nao_taggeadas() -> None:
    # tx sem escopo (parser não taggeou) não entra na soma do escopo → mismatch honesto.
    r = _fatura([{"valor": 100.0}, {"valor": 50.0, "escopo": "despesa_brasil"}], valor_cents=15000)
    issues: list[str] = []
    _apply_fatura_checksum(r, issues)
    assert any("Σ lançamentos" in i for i in issues)  # só 50,00 casa o escopo ≠ 150,00
