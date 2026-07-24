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


def _group_ingested(
    hash_: str, recs: list[dict], db_hashes: set[str], db_prefixes: set[str]
) -> bool:
    """Grupo ingerido se o content_hash bate (arquivo == original) OU o
    ``stored_prefix`` (identidade ADR-084 do nome) bate — robusto quando o
    byte-conteúdo em disco divergiu do original ingerido (re-parse)."""
    if hash_ in db_hashes:
        return True
    return any(rec.get("stored_prefix") in db_prefixes for rec in recs if rec.get("stored_prefix"))


def _not_ingested_labels(
    groups: dict[str, list[dict]], db_hashes: set[str], db_prefixes: set[str]
) -> list[str]:
    return [
        recs[0].get("label", "?")
        for h, recs in groups.items()
        if h and not _group_ingested(h, recs, db_hashes, db_prefixes)
    ]


def _deduped_count(
    groups: dict[str, list[dict]], db_hashes: set[str], db_prefixes: set[str]
) -> int:
    return sum(
        len(recs) - 1
        for h, recs in groups.items()
        if len(recs) > 1 and _group_ingested(h, recs, db_hashes, db_prefixes)
    )


def _invariant_violations(live_artifacts: list[tuple[str, str]]) -> list[str]:
    """(stage, key) com >1 artefato vivo não-fallback — parcial ressuscitado."""
    counts = Counter(live_artifacts)
    return [f"{stage}:{key}" for (stage, key), n in counts.items() if n > 1]


def is_stub(payload: dict) -> bool:
    """Artefato E2 sem conteúdo vivo: escalado ao LLM (``requires_llm_fallback``)
    ou bank statement parseado com zero transações (``transacoes == []``). Um
    artefato de investimento **não** tem a chave ``transacoes`` (tem ``posicoes``/
    ``investimentos``) → ``.get`` devolve ``None``, logo **não** é stub — o que
    impede de excluí-lo por engano do ``live_artifacts``."""
    return payload.get("requires_llm_fallback") is True or payload.get("transacoes") == []


def _ingested_count(
    groups: dict[str, list[dict]], db_hashes: set[str], db_prefixes: set[str]
) -> int:
    return sum(
        len(recs)
        for h, recs in groups.items()
        if h and _group_ingested(h, recs, db_hashes, db_prefixes)
    )


def reconcile(
    harness_records: list[dict],
    db_hashes: set[str],
    live_artifacts: list[tuple[str, str]],
    *,
    db_prefixes: set[str] | None = None,
) -> ReconResult:
    """Reconcilia harness↔DB por content_hash (+ fallback ``stored_prefix`` quando
    ``db_prefixes`` dado) + invariante de unicidade de artefato vivo."""
    prefixes = db_prefixes or set()
    groups = _group_by_hash(harness_records)
    return ReconResult(
        ingested=_ingested_count(groups, db_hashes, prefixes),
        deduped=_deduped_count(groups, db_hashes, prefixes),
        not_ingested=_not_ingested_labels(groups, db_hashes, prefixes),
        invariant_violations=_invariant_violations(live_artifacts),
    )
