"""DTOs do colapso cross-documento ([[ADR-354]] §Emenda · [[A40.l2]]).

Extraído de ``cross_document_collapser`` (SRP + limite de 500 linhas): o alvo de
remoção, a remoção declarada por canal e o candidato PII-safe. Sem I/O, sem lógica de
predicado — o service importa daqui e re-exporta para não quebrar call-site.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RemovalTarget:
    """Alvo de remoção com **multiplicidade** — hash NÃO endereça row."""

    # As 8 partes de `_hash_v2` são a união da 5-tupla da chave de colapso com a tripla
    # de proveniência, então TODAS as rows de um bucket compartilham o mesmo hash por
    # construção. Emitir lista de hashes fazia 1 hash endereçar N rows: medido em
    # 2026-08-05, alvo declarando 411 rows resolvia 453 — e o excesso eram exatamente
    # os sobreviventes eleitos pela cardinalidade multiset.

    hash: str
    remover: int
    no_bucket: int

    @property
    def hash_desaparece(self) -> bool:
        """``True`` ⇒ nenhuma row com esse hash sobra: override ancorado nele órfãna."""
        return self.remover >= self.no_bucket

    def to_trace_dict(self) -> dict:
        return {"hash": self.hash, "remover": self.remover, "no_bucket": self.no_bucket}


@dataclass(frozen=True)
class CollapseRemoval:
    """Remoção declarada por statement — canal ``cross_document_collapse`` ([[ADR-347]])."""

    # `valor_cents` é ASSINADO (débito negativo), como o resto do ledger. NÃO reusar
    # `CollapseCandidate.valor_cents`, que é magnitude (`decimal_cents` faz `abs()`):
    # `_declared_dedup_cents` nunca fecharia contra `val_in − val_out`.
    canal: str
    count: int
    valor_cents: int
    cross_source_count: int
    source: str | None = None


@dataclass(frozen=True)
class CollapseMeasurement:
    """Candidatos **+** o corpus contra o qual o gate de override se cruza ([[ADR-364]])."""

    # O corpus é sempre PRÉ-poda, nos dois modos. Derivá-lo depois da remoção perderia
    # exatamente as rows removidas — onde os overrides em risco ancoram —, e a garantia
    # anti-vácuo degradaria no único momento em que ela é load-bearing.

    candidates: tuple = ()
    corpus_gate_digests: frozenset[str] = frozenset()
    corpus_row_hashes: frozenset[str] = frozenset()


def shadow_counts(candidates) -> dict[str, int]:
    """Agregado PII-safe da sombra (ADR-364) — só contagens e cents, nunca texto."""
    todos = list(candidates)  # materializa ANTES: generator consumido daria candidatos=0
    colapsaveis = [c for c in todos if c.collapsible]
    return {
        "candidatos": len(todos),
        "colapsaveis": len(colapsaveis),
        "rows_removiveis": sum(c.removable_rows for c in colapsaveis),
        "cents_removiveis": sum(c.valor_cents * c.removable_rows for c in colapsaveis),
        "alvo_ambiguo": sum(1 for c in colapsaveis if c.alvo_ambiguo),
    }


@dataclass(frozen=True)
class CollapseCandidate:
    """Ocorrência cross-proveniência, PII-safe (digest + cents + códigos, nunca texto)."""

    key_digest: str
    mes: str
    valor_cents: int
    moeda: str
    direction: str
    n_rows: int
    n_provenances: int
    survivor_cardinality: int
    removable_rows: int
    removal_targets: tuple[RemovalTarget, ...]
    blocked_reason: str | None
    # Digest direction-free para o gate de override (D1) — ver `gate_key_digest`.
    gate_digest: str = ""
    # `_hash_v2` da row que SOBREVIVE ao colapso — alvo da re-ancoragem ([[ADR-364]] §2).
    # Vive no candidato e não no `RemovalTarget` porque é propriedade do GRUPO: sob a D5 há
    # no máximo 1 alvo por candidato, e todas as rows de um bucket compartilham um hash.
    survivor_hash: str = ""
    # Tags em NOMES de campo (nunca valores — PII), na mesma forma que o detector da
    # [[A40.l1]] emite: permitem afirmar a equivalência "colapsável ⇒ carrier-shaped"
    # sem que o pipeline importe `dev/`.
    divergence: str = ""
    parciais: str = ""

    @property
    def collapsible(self) -> bool:
        return self.blocked_reason is None and self.removable_rows > 0

    @property
    def rows_alcancadas_por_hash(self) -> int:
        """Rows que um consumidor que apaga por CONJUNTO de hash atingiria."""
        return sum(t.no_bucket for t in self.removal_targets)

    @property
    def alvo_ambiguo(self) -> bool:
        """Alvo pede remoção PARCIAL de um bucket — apagar por hash removeria a mais."""
        return self.rows_alcancadas_por_hash != self.removable_rows

    def to_trace_dict(self) -> dict:
        return {
            "key_digest": self.key_digest,
            "gate_digest": self.gate_digest,
            "mes": self.mes,
            "valor_cents": self.valor_cents,
            "moeda": self.moeda,
            "direction": self.direction,
            "n_rows": self.n_rows,
            "n_provenances": self.n_provenances,
            "survivor_cardinality": self.survivor_cardinality,
            "removable_rows": self.removable_rows,
            "removal_targets": [t.to_trace_dict() for t in self.removal_targets],
            "alvo_ambiguo": self.alvo_ambiguo,
            "blocked_reason": self.blocked_reason,
            "divergence": self.divergence,
            "parciais": self.parciais,
        }
