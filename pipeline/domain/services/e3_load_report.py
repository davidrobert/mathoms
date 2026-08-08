"""DTOs de carga do E3 + ledger de conservação de contagem por artefato (ADR-347).

Extraído de ``e3_reconciler_adapter`` (SRP + limite de 500 linhas): ``EmptyInstitutionWarning``
(warning de load), ``LoadOutcome`` (estado acumulado no load), ``LoadStat`` (fatos por
statement carregado) e a função pura ``build_artifact_ledger`` (partição de remoções
por artefato, count-balanced). Importa só módulos-folha — sem ciclo com o adapter.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pipeline.domain.models.document import BankStatement
from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services.statement_preprocessor import (
    AnachronicTransactionWarning,
    PeriodDerivationWarning,
)


@dataclass(frozen=True)
class EmptyInstitutionWarning:
    """Extrato E2 sem banco determinável — pulado para não gerar key E3 ``_...``."""

    source: str

    def format(self) -> str:
        return f"empty-institution src={self.source} skipped=1 (needs_review)"

    def to_review_reason(
        self, *, stage: str, artifact_key: str, document_id: str | None
    ) -> ReviewReason | None:
        """Projeta (ADR-272) para ReviewReason — banco vazio é campo obrigatório ausente."""
        return ReviewReason(
            code=ReviewReasonCode.extract_missing_required_field,
            stage=stage,
            artifact_key=artifact_key,
            document_id=document_id,
            offending_value="banco=''",
            expected="campo banco/institution nao-vazio no artefato E2",
            message="extrato sem banco determinavel; documento requer revisao",
        )


@dataclass(frozen=True)
class LoadStat:
    """Fatos de carga de UM statement (ADR-347), keyed por ``source_document``.
    ``tx_carregadas`` = âncora pós-period-norm, PRÉ-anachronic/undated."""

    tx_carregadas: int
    anachronic: int
    undated: int
    tx_loaded: int


@dataclass(frozen=True)
class StatementExclusion:
    """Statement inteiro excluído no load (ADR-347), por canal. O tx count entra no
    ledger de conservação **run-level** (workspace), não num artefato E3 (não há)."""

    canal: str
    count: int


@dataclass
class LoadOutcome:
    """Estado interno acumulado durante ``_load_with_outcome``."""

    statements: list[BankStatement] = field(default_factory=list)
    period_warnings: list[PeriodDerivationWarning] = field(default_factory=list)
    anachronic_warnings: list[AnachronicTransactionWarning] = field(default_factory=list)
    institution_warnings: list[EmptyInstitutionWarning] = field(default_factory=list)
    review_reasons: list[ReviewReason] = field(default_factory=list)
    skipped: int = 0
    # ADR-347 PR1b — fatos de carga por source, base do ledger de conservação.
    load_stats: dict[str, LoadStat] = field(default_factory=dict)
    # ADR-347 PR2 — statements excluídos no load (tx count por canal), ledger run-level.
    exclusions: list[StatementExclusion] = field(default_factory=list)

    def exclude(self, canal: str, count: int) -> None:
        """Registra exclusão de statement inteiro: incrementa ``skipped`` + ledger."""
        self.skipped += 1
        self.exclusions.append(StatementExclusion(canal, count))


# `meses` só neste canal, e OMITIDO quando vazio: `$defs/remocao` é compartilhado pelos 5
# canais, então declarar `meses` lá afirmaria que qualquer canal carrega mês — falso, e
# convite para o próximo preencher (A40.l2 §Co-design do 3c1).
def _canal_colapso(collapse: tuple[int, int], meses: tuple[tuple[str, int], ...]) -> dict:
    """Canal ``cross_document_collapse``, com o breakdown mensal quando houve colapso."""
    canal = {"count": collapse[0], "valor_cents": collapse[1]}
    if meses:
        canal["meses"] = [{"mes": m, "count": n} for m, n in meses]
    return canal


def _remocoes(
    undated: int,
    anachronic: int,
    intra: tuple[int, int],
    cross: tuple[int, int],
    collapse: tuple[int, int],
    collapse_meses: tuple[tuple[str, int], ...] = (),
) -> dict:
    """Partição de remoções por canal (ADR-347 + Emenda A40.l2). ``valor_cents``
    assinado; undated/anachronic ficam 0 — captura de valor é a montante do adapter
    (perda real), diferida ao PR2b (measure-then-emit)."""
    colapso = _canal_colapso(collapse, collapse_meses)
    return {
        "undated_drop": {"count": undated, "valor_cents": 0},
        "anachronic": {"count": anachronic, "valor_cents": 0},
        "intra_statement_dedup": {"count": intra[0], "valor_cents": intra[1]},
        "cross_file_dedup": {"count": cross[0], "valor_cents": cross[1]},
        "cross_document_collapse": colapso,
    }


def _channel_by_source(removals, canal: str) -> dict[str, tuple[int, int]]:
    """``{source: (count, cents)}`` SOMADOS — a dict-comprehension anterior
    sobrescrevia: dois statements com o mesmo ``source_document`` perdiam um ao outro
    e `_ledger_totals` somava o mesmo cents 2× (achado do co-design A40.l2)."""
    out: dict[str, list[int]] = {}
    for r in removals or ():
        if getattr(r, "canal", None) == canal and getattr(r, "source", None):
            bucket = out.setdefault(r.source, [0, 0])
            bucket[0] += r.count
            bucket[1] += r.valor_cents
    return {src: (c, v) for src, (c, v) in out.items()}


def _stat_sums(reconciled_stmts, load_stats) -> tuple[int, int, int, int]:
    """``(tx_carregadas, anachronic, undated, intra_inferido)`` somados por statement."""
    carregadas = anachronic = undated = inferred = 0
    for s in reconciled_stmts:
        st = load_stats.get(s.source_document or "")
        if st is None:
            continue
        carregadas += st.tx_carregadas
        anachronic += st.anachronic
        undated += st.undated
        inferred += st.tx_loaded - len(s.transactions)
    return carregadas, anachronic, undated, inferred


def _channel_sums(reconciled_stmts, chan_map: dict[str, tuple[int, int]]) -> tuple[int, int]:
    """Soma por ``source`` DISTINTO do grupo — por statement re-somaria o canal
    quando dois statements compartilham o mesmo arquivo."""
    total = cents = 0
    for src in {s.source_document for s in reconciled_stmts if s.source_document}:
        n, v = chan_map.get(src, (0, 0))
        total += n
        cents += v
    return total, cents


def _collapse_meses(reconciled_stmts, removals) -> tuple[tuple[str, int], ...]:
    """Meses do canal do colapso, mesclados pelos ``source`` DISTINTOS do grupo."""
    # Mesma dedup-por-source de `_channel_sums`: por statement re-somaria o mês quando dois
    # statements compartilham arquivo. `Counter` mescla; a ordenação torna o payload
    # determinístico, que é o que mantém a chave de cache do parecer estável entre runs.
    fontes = {s.source_document for s in reconciled_stmts if s.source_document}
    acc: Counter = Counter()
    for r in removals or ():
        if getattr(r, "canal", None) == "cross_document_collapse" and r.source in fontes:
            acc.update(dict(getattr(r, "meses", ()) or ()))
    return tuple(sorted(acc.items()))


def _authoritative_remocoes(reconciled_stmts, removals, undated, anachronic, cross) -> dict:
    """Partição com canais AUTORITATIVOS (fatos declarados, nunca diferença)."""
    intra = _channel_sums(reconciled_stmts, _channel_by_source(removals, "intra_statement_dedup"))
    collapse = _channel_sums(
        reconciled_stmts, _channel_by_source(removals, "cross_document_collapse")
    )
    meses = _collapse_meses(reconciled_stmts, removals)
    return _remocoes(undated, anachronic, intra, cross, collapse, meses)


def build_artifact_ledger(
    reconciled_stmts: list[BankStatement],
    load_stats: dict[str, LoadStat],
    cross_removed: int,
    cross_cents: int,
    removals=None,
) -> dict:
    """Ledger E3 (ADR-347): ``tx_carregadas == transacoes_total + Σ remocoes[*].count``."""
    # Com `removals` presente, `intra` é AUTORITATIVO (fatos dos DedupRemoval), não
    # inferido por diferença — a inferência convertia remoção não-declarada em
    # absorção silenciosa (colapso de 3 rows aparecia como intra count=3/cents=0 e o
    # invariante FECHAVA). Canal não-instrumentado agora produz resíduo ≠ 0 e quebra
    # alto. `removals=None` mantém a inferência legada (compat de caller antigo).
    carregadas, anachronic, undated, inferred = _stat_sums(reconciled_stmts, load_stats)
    cross = (cross_removed, cross_cents)
    if removals is None:
        remocoes = _remocoes(undated, anachronic, (inferred, 0), cross, (0, 0))
    else:
        remocoes = _authoritative_remocoes(reconciled_stmts, removals, undated, anachronic, cross)
    return {"tx_carregadas": carregadas, "remocoes": remocoes}


def attach_artifact_ledger(
    payload: dict, reconciled_stmts, load_stats, cross_removed, cross_cents, removals
) -> None:
    """Anexa (in-place) o ledger de conservação E3 (ADR-347) ao ``payload``."""
    payload |= build_artifact_ledger(
        reconciled_stmts, load_stats, cross_removed, cross_cents, removals
    )
