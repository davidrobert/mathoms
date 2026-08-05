"""5º canal do ledger + `intra` autoritativo ([[A40.l2]] D3 · [[ADR-347]] §Emenda).

A inferência por diferença (`tx_loaded − len(transactions)`) era o mecanismo que
convertia remoção não-declarada em ABSORÇÃO SILENCIOSA: colapso de 3 rows aparecia
como `intra_statement_dedup` count=3/cents=0 e o invariante fechava. Com `intra`
autoritativo, canal não-instrumentado produz resíduo ≠ 0 e o invariante quebra alto.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.models.document import BankStatement  # noqa: E402
from pipeline.domain.models.transaction import Money, Transaction  # noqa: E402
from pipeline.domain.services.cross_document_collapser import CollapseRemoval  # noqa: E402
from pipeline.domain.services.e3_load_report import (  # noqa: E402
    LoadStat,
    build_artifact_ledger,
)
from pipeline.domain.services.reconciliation_service import DedupRemoval  # noqa: E402


def _stmt(n_tx: int, arquivo: str = "a.pdf") -> BankStatement:
    s = BankStatement(
        institution="banco exemplo",
        member_key="titular exemplo",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        currency="BRL",
        transactions=[
            Transaction(
                date=date(2026, 3, 30), description="compra", amount=Money.of("-10.00", "BRL")
            )
            for _ in range(n_tx)
        ],
        account_type="extratoconta",
    )
    s.source_document = arquivo
    return s


def _identidade(ledger: dict, transacoes_total: int) -> tuple[int, int]:
    """(lado esquerdo, lado direito) de tx_carregadas == total + Σ remocoes[*].count."""
    declarado = sum(r["count"] for r in ledger["remocoes"].values())
    return ledger["tx_carregadas"], transacoes_total + declarado


def test_canal_collapse_declarado_e_identidade_fecha() -> None:
    """carregadas=10 → 1 undated + 1 anachronic + 2 intra + 1 collapse + 5 kept."""
    stats = {"a.pdf": LoadStat(tx_carregadas=10, tx_loaded=8, anachronic=1, undated=1)}
    removals = [
        DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf"),
        CollapseRemoval("cross_document_collapse", 1, -1000, 1, "a.pdf"),
    ]

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, removals)

    canais = ledger["remocoes"]
    assert canais["cross_document_collapse"] == {"count": 1, "valor_cents": -1000}
    assert canais["intra_statement_dedup"] == {"count": 2, "valor_cents": -2000}
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda == direita == 10


def test_remocao_nao_declarada_quebra_a_identidade_alto() -> None:
    """O eixo anti-absorção: 1 row removida SEM canal declarado ⇒ resíduo visível.
    Sob a inferência antiga o invariante fechava com a remoção misatribuída ao intra."""
    stats = {"a.pdf": LoadStat(tx_carregadas=10, tx_loaded=8, anachronic=1, undated=1)}
    removals = [DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf")]

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, removals)  # 8-2=6 ≠ 5 kept

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 2  # fato, não diferença
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda != direita  # 10 ≠ 9 — a row não-declarada aparece como resíduo


def test_mesmo_source_em_dois_removals_soma_nao_sobrescreve() -> None:
    """Bug do co-design: dict-comprehension keyed por source perdia entradas."""
    stats = {"a.pdf": LoadStat(tx_carregadas=6, tx_loaded=6, anachronic=0, undated=0)}
    removals = [
        DedupRemoval("intra_statement_dedup", 1, -1000, 0, "a.pdf"),
        DedupRemoval("intra_statement_dedup", 2, -2000, 0, "a.pdf"),
    ]

    ledger = build_artifact_ledger([_stmt(3)], stats, 0, 0, removals)

    assert ledger["remocoes"]["intra_statement_dedup"] == {"count": 3, "valor_cents": -3000}


def test_dois_statements_do_mesmo_arquivo_nao_recontam_o_canal() -> None:
    """A soma do canal é por SOURCE distinto do grupo, não por statement."""
    stats = {"a.pdf": LoadStat(tx_carregadas=4, tx_loaded=4, anachronic=0, undated=0)}
    removals = [DedupRemoval("intra_statement_dedup", 1, -1000, 0, "a.pdf")]

    ledger = build_artifact_ledger([_stmt(2), _stmt(1)], stats, 0, 0, removals)

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 1


def test_sem_removals_mantem_inferencia_legada() -> None:
    """Compat: caller antigo (removals=None) infere intra por diferença, collapse=0."""
    stats = {"a.pdf": LoadStat(tx_carregadas=8, tx_loaded=8, anachronic=0, undated=0)}

    ledger = build_artifact_ledger([_stmt(5)], stats, 0, 0, None)

    assert ledger["remocoes"]["intra_statement_dedup"]["count"] == 3  # inferido
    assert ledger["remocoes"]["cross_document_collapse"]["count"] == 0
    esquerda, direita = _identidade(ledger, transacoes_total=5)
    assert esquerda == direita


def test_e2_to_e3_ve_a_particao_completa_no_count_out() -> None:
    """O4 do co-design: `transacoes_duplicadas_removidas` é só cross-file; canal novo
    em `remocoes` não entrava no count_out e o check de COUNT disparava antes."""
    from dev.ledger_conservation import CONSERVADO, e2_to_e3

    e2 = [{"tipo": "extratoconta", "transacoes": [{"valor": 0}] * 10}]
    remocoes = {
        "undated_drop": {"count": 1, "valor_cents": 0},
        "anachronic": {"count": 1, "valor_cents": 0},
        "intra_statement_dedup": {"count": 2, "valor_cents": 0},
        "cross_file_dedup": {"count": 0, "valor_cents": 0},
        "cross_document_collapse": {"count": 1, "valor_cents": 0},
    }
    e3 = [{"transacoes_total": 5, "transacoes": [], "remocoes": remocoes}]

    r = e2_to_e3(e2, e3)

    assert (r.count_in, r.count_out) == (10, 10)
    assert r.verdict == CONSERVADO


def test_e2_to_e3_artefato_antigo_mantem_fallback() -> None:
    """Artefato de 4 canais (ou sem remocoes) segue lido pelo campo legado."""
    from dev.ledger_conservation import e2_to_e3

    e2 = [{"tipo": "extratoconta", "transacoes": [{"valor": 0}] * 6}]
    e3 = [{"transacoes_total": 5, "transacoes": [], "transacoes_duplicadas_removidas": 1}]

    r = e2_to_e3(e2, e3)

    assert (r.count_in, r.count_out) == (6, 6)
