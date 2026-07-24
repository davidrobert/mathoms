#!/usr/bin/env python3
"""Cross-check harness↔DB do Passo 3 do parse-certify — núcleo puro (ADR-302).

A perda silenciosa vive na divergência entre o que o harness *parsearia* (dir de
originais) e o que o DB *persistiu*. Este módulo reconcilia **por content_hash,
nunca por contagem** (dedup faz o DB ter ≤ arquivos do dir) e verifica o
invariante **≤1 artefato vivo não-fallback por (stage, key)** (um parcial de run
anterior ressuscitado = falso-verde). Funções puras, testáveis sem DB; a cola de
leitura do DB (checkout principal) alimenta estes inputs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReconResult:
    ingested: int  # records do harness cujo content_hash está no DB
    deduped: int  # cópias extra no dir (mesmo content_hash) — benigno (DB ≤ dir)
    not_ingested: list[str] = field(default_factory=list)  # labels sem hash no DB — P0
    invariant_violations: list[str] = field(default_factory=list)  # "stage:key" com >1 vivo

    @property
    def clean(self) -> bool:
        return not self.not_ingested and not self.invariant_violations


def _group_by_hash(harness_records: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for rec in harness_records:
        groups[rec.get("content_hash", "")].append(rec)
    return groups


def _not_ingested_labels(groups: dict[str, list[dict]], db_hashes: set[str]) -> list[str]:
    return [recs[0].get("label", "?") for h, recs in groups.items() if h and h not in db_hashes]


def _deduped_count(groups: dict[str, list[dict]], db_hashes: set[str]) -> int:
    return sum(len(recs) - 1 for h, recs in groups.items() if h in db_hashes and len(recs) > 1)


def _invariant_violations(live_artifacts: list[tuple[str, str]]) -> list[str]:
    """(stage, key) com >1 artefato vivo não-fallback — parcial ressuscitado."""
    counts = Counter(live_artifacts)
    return [f"{stage}:{key}" for (stage, key), n in counts.items() if n > 1]


def reconcile(
    harness_records: list[dict], db_hashes: set[str], live_artifacts: list[tuple[str, str]]
) -> ReconResult:
    """Reconcilia harness↔DB por content_hash + invariante de unicidade de artefato vivo."""
    groups = _group_by_hash(harness_records)
    ingested = sum(len(recs) for h, recs in groups.items() if h in db_hashes)
    return ReconResult(
        ingested=ingested,
        deduped=_deduped_count(groups, db_hashes),
        not_ingested=_not_ingested_labels(groups, db_hashes),
        invariant_violations=_invariant_violations(live_artifacts),
    )
