#!/usr/bin/env python3
"""Ledger de conservação E2→E3→E4 em cents — núcleo puro da skill ledger-certify (ADR-343/302).

Funções puras (testáveis sem DB): recebem os artefatos E2/E3/E4 como dicts e
computam as igualdades de conservação em **int cents** (tol-zero, ADR-090) +
detectam dupla-contagem de investimento (ADR-271) + atribuem o veredito (5
estados fail-closed da rubrica). Reusa `dev.golden_diff.to_cents` (não reimplementa
aritmética de cents).

**Conservação é o piso, não o teto:** os piores erros são sum-preserving. Este
módulo cobre a **camada A** (conservação objetiva por transição de stage) + o
detector de dupla-contagem (**camada B**, o check que falha num cenário
sum-preserving). A camada B de fronteira de categoria (natureza/consumo) é
julgamento de domínio delegado ao financial-planner, não codificável aqui.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents

# Vereditos fail-closed (rubrica ledger-certify).
CONSERVADO = "conservado"
COBERTO_SEM_VALOR = "coberto-sem-verificação-de-valor"
DEDUP_LEGITIMO = "dedup/transfer-legítimo"
PERDA_SILENCIOSA = "perda/dupla-contagem-silenciosa"  # P0
NAO_VERIFICAVEL = "não-verificável"


@dataclass(frozen=True)
class ConservationResult:
    transition: str  # "E2->E3" | "E3->E4"
    count_in: int
    count_out: int
    value_in_cents: int | None
    value_out_cents: int | None
    dups: int
    verdict: str
    detail: str


# ─────────────────────────── E2 → E3 ───────────────────────────

# Doc-types que carregam posição/informe (não transação bancária): passam pelo
# reconciliador mas não produzem tx reconciliada — não podem inflar o denominador
# E2→E3 (LC-07). Espelha a distinção do E4 (``e4_categorizer_adapter``:
# ``tipo_documento in ("investment_report", "informe_rendimentos")``). Os tipos já
# normalizados (``investimentosposicao``, ``informerendimentos``…) saem via
# ``AccountGrouper.should_skip``; este set cobre as formas LLM com underscore.
_NON_TX_DOC_TYPES = frozenset({"investment_report", "informe_rendimentos"})


def _tx_cents(tx: dict) -> int:
    """Cents de uma transação. O pipeline move ``valor`` (float); ``amount``
    (decimal-string, ADR-278) é preferido quando presente por precisão."""
    raw = tx.get("amount")
    if raw in (None, ""):
        raw = tx.get("valor", 0)
    return to_cents(raw)


def _sum_cents(txns: list[dict]) -> int:
    return sum(_tx_cents(t) for t in txns)


def _skips_reconcile(artifact: dict) -> bool:
    """True se o reconciliador não produziria tx a partir deste artefato E2 — tipo
    pulado (``AccountGrouper.should_skip``: IRPF, posição, informe, fatura não-
    suportada) ou doc-type de posição/informe (``_NON_TX_DOC_TYPES``). Filtra o
    denominador E2→E3 para não contar tx que nunca entram no reconcile (LC-07)."""
    from pipeline.domain.services.account_grouper import AccountGrouper

    if not isinstance(artifact, dict):
        return True
    doc_type = str(artifact.get("tipo") or artifact.get("tipo_documento") or "").strip()
    if doc_type in _NON_TX_DOC_TYPES:
        return True
    return AccountGrouper().should_skip(artifact)


def e2_to_e3(e2_artifacts: list[dict], e3_artifacts: list[dict]) -> ConservationResult:
    """Conservação E2→E3 (workspace-wide). Count HARD; valor HARD só se dups==0.
    O denominador exclui artefatos não-reconciliáveis (posição/informe/IRPF): suas
    tx nunca entram no reconcile e inflariam a perda aparente (LC-07)."""
    reconcilable = [a for a in e2_artifacts if not _skips_reconcile(a)]
    e2_tx = [t for a in reconcilable for t in a.get("transacoes", [])]
    count_in = len(e2_tx)
    survivors = sum(a.get("transacoes_total", 0) for a in e3_artifacts)
    dups = sum(a.get("transacoes_duplicadas_removidas", 0) for a in e3_artifacts)
    count_out = survivors + dups
    e3_tx = [t for a in e3_artifacts for t in a.get("transacoes", [])]
    val_in, val_out = _sum_cents(e2_tx), _sum_cents(e3_tx)
    return _e2e3_verdict(count_in, count_out, survivors, dups, val_in, val_out)


def _e2e3_verdict(
    count_in: int, count_out: int, survivors: int, dups: int, val_in: int, val_out: int
) -> ConservationResult:
    """Veredito E2→E3 fail-closed. A ORDEM importa: queda de count COM dedup
    declarado (dups>0) é sub-declaração de dedup ⇒ coberto, não perda (LC-07). Só é
    perda quando a queda vem sem nenhum dedup declarado. (count/dups vão no report.)"""
    checks = [
        (count_out < count_in and dups == 0, PERDA_SILENCIOSA, "count caiu sem dedup declarado"),
        (count_out < count_in, COBERTO_SEM_VALOR, "sub-declaração de dedup; valor não-provável"),
        (dups > 0, COBERTO_SEM_VALOR, "dups>0; valor removido não declarado no artefato"),
        (val_out != val_in, PERDA_SILENCIOSA, "Σ valor diverge sem dedup (dups=0)"),
    ]
    v, d = next(
        ((vv, dd) for cond, vv, dd in checks if cond), (CONSERVADO, "count e valor conservam")
    )
    return ConservationResult("E2->E3", count_in, count_out, val_in, val_out, dups, v, d)


# ─────────────────────────── E3 → E4 ───────────────────────────


def _bucket_value_ok(bucket: dict) -> bool:
    """Σ totais_por_categoria == total_geral (cents)."""
    total = to_cents(bucket.get("total_geral", 0))
    parts = sum(to_cents(v) for v in bucket.get("totais_por_categoria", {}).values())
    return total == parts


def e3_to_e4(
    e3_artifacts: list[dict], despesas: dict, receitas: dict, transferencias_count: int
) -> ConservationResult:
    """Conservação E3→E4: todo classificado tem destino; baldes fecham."""
    e3_total = sum(a.get("transacoes_total", 0) for a in e3_artifacts)
    signals = despesas.get("_lineage", {}).get("signals", {})
    tx_total = int(signals.get("tx_total", 0))
    dedup_collapsed = int(signals.get("dedup_collapsed", 0))
    destino = (
        receitas.get("total_transacoes", 0)
        + despesas.get("total_transacoes", 0)
        + transferencias_count
        + dedup_collapsed
    )
    return _e3e4_verdict(e3_total, tx_total, destino, despesas, receitas)


def _e3e4_verdict(
    e3_total: int, tx_total: int, destino: int, despesas: dict, receitas: dict
) -> ConservationResult:
    buckets_ok = _bucket_value_ok(despesas) and _bucket_value_ok(receitas)
    checks = [
        (
            e3_total != tx_total,
            PERDA_SILENCIOSA,
            f"E3 {e3_total} -> E4 tx_total {tx_total} (dropou)",
        ),
        (tx_total != destino, PERDA_SILENCIOSA, f"tx_total {tx_total} != destino {destino}"),
        (not buckets_ok, PERDA_SILENCIOSA, "Σ categorias != total_geral num balde"),
    ]
    v, d = next(
        ((vv, dd) for cond, vv, dd in checks if cond), (CONSERVADO, "count e baldes fecham")
    )
    val = to_cents(despesas.get("total_geral", 0)) + to_cents(receitas.get("total_geral", 0))
    return ConservationResult("E3->E4", tx_total, destino, val, val, 0, v, d)


# ─────────────────── dedup de investimento (camada B, P0) ───────────────────


def _norm(text: str) -> str:
    """Normaliza texto para chave de identidade de posição (ADR-271)."""
    stripped = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def _pos_descriptor(pos: dict) -> str:
    """Descritor estável e time-invariante de uma posição: ticker quando houver,
    senão nome+vencimento. É o que separa DOIS produtos distintos de UMA mesma
    posição re-snapshotada — a descrição sozinha vem vazia neste corpus, e keyar só
    por (tipo|instituição) funde produtos distintos do mesmo snapshot (LC-06)."""
    ticker = _norm(pos.get("ticker_norm") or pos.get("ticker") or pos.get("codigo") or "")
    if ticker:
        return ticker
    nome = _norm(pos.get("nome") or pos.get("descricao") or pos.get("name") or "")
    venc = _norm(pos.get("vencimento") or "")
    return f"{nome}@{venc}" if venc else nome


def _pos_value_cents(pos: dict) -> int:
    for k in ("valor_atual", "valor_total", "current_value", "valor_brl", "valor"):
        raw = pos.get(k)
        if raw not in (None, ""):
            return to_cents(raw)
    return 0


def _pos_data_ref(pos: dict) -> str:
    return _norm(pos.get("data_referencia") or pos.get("data_posicao") or pos.get("periodo") or "")


def _pos_identity(pos: dict) -> tuple[str, str, str]:
    """Identidade de posição SEM membro nem tempo. Membro fora da chave de propósito:
    o vetor real (snapshot stale via escape membro-vazio) exige que a identidade não
    dependa de atribuição de membro (frágil, ADR-287); o tempo entra à parte."""
    return (_norm(pos.get("tipo", "")), _norm(pos.get("instituicao", "")), _pos_descriptor(pos))


def _identity_label(identity: tuple[str, str, str], reason: str) -> str:
    tipo, inst, desc = identity
    return f"{tipo}|{inst}|{desc or '<sem-descrição>'} [{reason}]"


def _exact_dups(positions: list[dict]) -> set[tuple[str, str, str]]:
    """Identidades cuja linha COMPLETA (identidade + data_ref + valor + membro)
    aparece 2×: duplicata literal dentro de um snapshot."""
    seen: dict[tuple, int] = {}
    for pos in positions:
        full = _pos_identity(pos) + (
            _pos_data_ref(pos),
            _pos_value_cents(pos),
            _norm(pos.get("membro", "")),
        )
        seen[full] = seen.get(full, 0) + 1
    return {full[:3] for full, n in seen.items() if n > 1}


def _cross_period(positions: list[dict]) -> set[tuple[str, str, str]]:
    """Identidades presentes em ≥2 ``data_referencia`` distintas: somar dois
    snapshots da MESMA posição infla o patrimônio (o vetor real — ex.: binance
    stale). Só conta ``data_ref`` não-vazia (fail-safe: sem data não afirma nada)."""
    refs: dict[tuple[str, str, str], set[str]] = {}
    for pos in positions:
        dr = _pos_data_ref(pos)
        if dr:
            refs.setdefault(_pos_identity(pos), set()).add(dr)
    return {ident for ident, drs in refs.items() if len(drs) > 1}


def investment_double_count(investimentos: dict) -> list[str]:
    """Posições dupla-contadas (ADR-271) — falha num cenário sum-preserving. Dois
    vetores: duplicata literal num snapshot + mesma posição em ≥2 ``data_referencia``.
    NÃO alerta em N produtos distintos do mesmo tipo/instituição no mesmo snapshot
    (valor/descritor diferentes ⇒ somar é correto) — o falso-positivo do LC-06."""
    positions = [p for p in investimentos.get("dados", []) if isinstance(p, dict)]
    hits: dict[tuple[str, str, str], str] = {}
    for ident in _exact_dups(positions):
        hits[ident] = "duplicata-exata"
    for ident in _cross_period(positions):
        hits.setdefault(ident, "snapshot-stale-cross-período")
    return [_identity_label(ident, reason) for ident, reason in hits.items()]
