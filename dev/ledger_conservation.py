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


def _tx_cents(tx: dict) -> int:
    """Cents de uma transação. O pipeline move ``valor`` (float); ``amount``
    (decimal-string, ADR-278) é preferido quando presente por precisão."""
    raw = tx.get("amount")
    if raw in (None, ""):
        raw = tx.get("valor", 0)
    return to_cents(raw)


def _sum_cents(txns: list[dict]) -> int:
    return sum(_tx_cents(t) for t in txns)


def e2_to_e3(e2_artifacts: list[dict], e3_artifacts: list[dict]) -> ConservationResult:
    """Conservação E2→E3 (workspace-wide). Count HARD; valor HARD só se dups==0."""
    e2_tx = [t for a in e2_artifacts for t in a.get("transacoes", [])]
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
    checks = [
        (
            count_out < count_in,
            PERDA_SILENCIOSA,
            f"count {count_in} -> {count_out} (sobrev+dups < entrada)",
        ),
        (dups > 0, COBERTO_SEM_VALOR, f"dups={dups}; valor removido não declarado no artefato"),
        (val_out != val_in, PERDA_SILENCIOSA, f"Σ valor {val_in} -> {val_out} cents (dups=0)"),
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
    """Normaliza descrição para chave de dedup (ADR-271: descricao_norm)."""
    stripped = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(stripped.lower().split())


def _dedup_key(pos: dict) -> tuple[str, str, str]:
    return (
        _norm(pos.get("tipo", "")),
        _norm(pos.get("instituicao", "")),
        _norm(pos.get("descricao", "")),
    )


def investment_double_count(investimentos: dict) -> list[str]:
    """Posições com mesma chave (tipo|instituicao|descricao_norm) vivas 2× (ADR-271) — falha em cenário sum-preserving; retorna chaves colididas mascaradas."""
    seen: dict[tuple[str, str, str], int] = {}
    for pos in investimentos.get("dados", []):
        key = _dedup_key(pos)
        seen[key] = seen.get(key, 0) + 1
    return [f"{k[0]}|{k[1]}|<desc>" for k, n in seen.items() if n > 1]
