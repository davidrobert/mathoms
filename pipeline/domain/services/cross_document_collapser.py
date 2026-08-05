"""Colapsador cross-documento por transação ([[ADR-354]] §Emenda) — measure-only.

Duas pernas legítimas da mesma conta — uma parseada nativamente, outra escalada ao
LLM porque o parser nativo emitiu stub — entregam o mesmo evento 2× ao razão. É
**sum-preserving**, então atravessa toda conservação por grupo (105/105 em tol-zero)
e infla o fluxo 1:1 no E5.

Este service identifica os candidatos **antes** do agrupamento de artefato do E3, no
grão transação. **Não remove** (measure-only, padrão [[ADR-347]]/[[ADR-350]] PR1): o
enforce e a re-ancoragem de override são PRs próprios, porque remover row órfãna
override ancorado no ``transaction_hash`` dela.

O predicado é **mais forte** que a chave do detector da [[A40.l1]] — um detector pode
sobre-detectar rotulado ([[ADR-342]]), um mutador que sobre-colapsa apaga dado
legítimo. Medido em 2026-08-05, porém, a força vem só de ``banco`` e da allow-list de
``tipo_conta``: ``titular`` é satisfeito por vacuidade em 331/331 (perna LLM sem
titular) e ``account_number_norm`` está vazio em 117/117 statements.

**Duas premissas que este módulo NÃO verifica**, contra a leitura intuitiva:
sobreposição de período (o metadado declarado é lixo na perna LLM — 85,2% das rows
caem fora do próprio período — então não sustenta cláusula) e distinção entre "1
evento visto 2×" e "2 eventos vistos 1× cada" dentro de uma proveniência (os campos
que distinguiriam não estão na chave nem no hash). Ver [[ADR-354]] §Emenda.
Puro, sem I/O.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from pipeline.domain.models.document import BankStatement
from pipeline.domain.models.transaction import Transaction
from pipeline.domain.services._tx_identity import (
    build_hash_inputs,
    compute_natural_key,
    decimal_cents,
    derive_direction,
    normalize_banco,
    normalize_descricao,
    normalize_tipo_conta,
    normalize_titular,
)

_LLM, _NATIVE = "llm", "native"

# Grupos de variante de vocabulário de ``tipo_conta`` que nomeiam o MESMO tipo de
# conta (decisão do dono, 2026-08-05): apenas este par. Vocabulário fora daqui NÃO
# colapsa — não é fail-closed (que apagaria ~252 rows de fonte única, LEDGER §r4).
_DEFAULT_ALIAS_GROUPS: tuple[frozenset[str], ...] = (frozenset({"extrato", "extratoconta"}),)

# Deny-list: sufixo de moeda é IDENTIDADE de conta, não variante de rótulo — C6
# Global USD/EUR e Wise BRL/USD são contas distintas. Alias group que junte dois
# tipos divergindo só por um destes sufixos é erro de config, não de dado.
_DEFAULT_IDENTITY_SUFFIXES: frozenset[str] = frozenset({"brl", "usd", "eur", "gbp", "chf"})

_PROVENANCE_FIELDS: tuple[str, str, str] = ("banco", "titular", "tipo_conta")


@dataclass(frozen=True)
class CrossDocumentCollapseConfig:
    """Config tipada (ISP, [[ADR-089]]) — allow-list de variante + deny-list de identidade."""

    alias_groups: tuple[frozenset[str], ...] = _DEFAULT_ALIAS_GROUPS
    identity_suffixes: frozenset[str] = _DEFAULT_IDENTITY_SUFFIXES

    def __post_init__(self) -> None:
        for group in self.alias_groups:
            offender = _identity_collision(group, self.identity_suffixes)
            if offender is not None:
                raise ValueError(
                    "alias group junta tipos que diferem só por sufixo de moeda "
                    f"(identidade de conta, ADR-354 §Emenda): {sorted(group)} via {offender!r}"
                )

    def is_variant_pair(self, values: frozenset[str]) -> bool:
        """``True`` se todos os valores não-vazios nomeiam o mesmo tipo de conta."""
        filled = frozenset(v for v in values if v)
        if len(filled) <= 1:
            return True
        return any(filled <= group for group in self.alias_groups)


def _strip_identity_suffix(value: str, suffixes: frozenset[str]) -> str:
    """Remove o sufixo de moeda do fim do tipo; nunca reduz o tipo a string vazia."""
    for suffix in sorted(suffixes):
        if value.endswith(suffix) and len(value) > len(suffix):
            return value[: -len(suffix)]
    return value


def _identity_collision(group: frozenset[str], suffixes: frozenset[str]) -> str | None:
    """Tipo cujo sufixo de moeda é o ÚNICO discriminante contra outro membro do grupo."""
    # Cada membro perde o SEU sufixo antes da comparação: strip de um sufixo só
    # sobre o grupo inteiro não vê `...globalusd` vs `...globaleur` (stems ficam
    # distintos em qualquer passada única).
    by_stem: dict[str, str] = {}
    for value in sorted(group):
        stem = _strip_identity_suffix(value, suffixes)
        if stem in by_stem:
            return value
        by_stem[stem] = value
    return None


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


def _provenance(stmt: BankStatement) -> tuple[str, str, str]:
    """Tripla normalizada — MESMOS normalizadores do hash K4 e do detector da l1."""
    return (
        normalize_banco(stmt.institution),
        normalize_titular(stmt.member_key),
        normalize_tipo_conta(stmt.account_type),
    )


def _direction(tx: Transaction, stmt: BankStatement) -> str:
    return derive_direction(
        tipo=None, valor=float(tx.amount.amount), tipo_conta=stmt.account_type or ""
    )


def _collapse_key(tx: Transaction, stmt: BankStatement) -> tuple:
    """Chave provenance-free day-exact — idêntica à do detector da [[A40.l1]]."""
    return (
        tx.date.isoformat(),
        decimal_cents(tx.amount.amount),
        (tx.amount.currency or "").strip().upper(),
        _direction(tx, stmt),
        normalize_descricao(tx.description),
    )


def _key_digest(key: tuple) -> str:
    return hashlib.sha256("|".join(str(p) for p in key).encode("utf-8")).hexdigest()[:12]


def _row_hash(tx: Transaction, stmt: BankStatement) -> str:
    """``_hash_v2`` da row — a chave de re-ancoragem de ``transaction_overrides``."""
    inputs = build_hash_inputs(
        data=tx.date.isoformat(),
        banco=stmt.institution,
        titular=stmt.member_key,
        tipo_conta=stmt.account_type,
        valor=tx.amount.amount,
        moeda=tx.amount.currency,
        descricao=tx.description,
    )
    return compute_natural_key(inputs).hash


def _field_values(provenances: Iterable[tuple[str, str, str]], name: str) -> frozenset[str]:
    """Valores de um campo de proveniência entre as pernas — nomes, nunca PII no trace."""
    idx = _PROVENANCE_FIELDS.index(name)
    return frozenset(p[idx] for p in provenances)


def _unifiable(values: frozenset[str]) -> bool:
    """Um lado preenchido não conflita com o outro: ≤1 valor não-vazio distinto."""
    return len({v for v in values if v}) <= 1


def _is_partial(values: frozenset[str]) -> bool:
    """Carrier 2 da [[ADR-354]]: vazio em ≥1 perna E preenchido em ≥1 — nunca vazio em todas."""
    return any(not v for v in values) and any(v for v in values)


def _extraction_split(stmts: Iterable[BankStatement]) -> tuple[int, int, int]:
    """``(n_llm, n_native, n_indeterminado)`` entre as pernas do candidato."""
    methods = [s.extraction_method for s in stmts]
    return (
        sum(1 for m in methods if m == _LLM),
        sum(1 for m in methods if m == _NATIVE),
        sum(1 for m in methods if m not in (_LLM, _NATIVE)),
    )


_Row = tuple[BankStatement, Transaction]


@dataclass(frozen=True)
class _KeyGroup:
    """Rows que colidem numa chave, já particionadas por proveniência."""

    key: tuple
    by_provenance: dict[tuple[str, str, str], list[_Row]]

    @property
    def rows(self) -> list[_Row]:
        return [row for group in self.by_provenance.values() for row in group]

    @property
    def survivor_cardinality(self) -> int:
        """Multiset: o evento ocorreu tantas vezes quanto a perna que mais o viu."""
        return max(len(group) for group in self.by_provenance.values())

    @property
    def llm_rows(self) -> list[_Row]:
        return [row for row in self.rows if row[0].extraction_method == _LLM]

    def field_values(self, name: str) -> frozenset[str]:
        return _field_values(self.by_provenance, name)

    @property
    def divergence(self) -> str:
        """Campos com >1 valor entre as pernas — forma idêntica à tag do detector."""
        return "+".join(n for n in _PROVENANCE_FIELDS if len(self.field_values(n)) > 1)

    @property
    def parciais(self) -> str:
        """Campos vazios numa perna e cheios na outra — a assimetria de fill (carrier 2)."""
        return "+".join(n for n in _PROVENANCE_FIELDS if _is_partial(self.field_values(n)))


def _group_by_key(statements: Iterable[BankStatement]) -> list[_KeyGroup]:
    """Índice chave → rows, mantendo só chaves vivas em ≥2 proveniências."""
    index: dict[tuple, dict[tuple[str, str, str], list[_Row]]] = {}
    for stmt in statements:
        for tx in stmt.transactions:
            buckets = index.setdefault(_collapse_key(tx, stmt), {})
            buckets.setdefault(_provenance(stmt), []).append((stmt, tx))
    return [_KeyGroup(key, buckets) for key, buckets in index.items() if len(buckets) > 1]


class CrossDocumentCollapser:
    """Mede duplicação cross-documento no grão transação, pré-agrupamento."""

    def __init__(self, config: CrossDocumentCollapseConfig | None = None) -> None:
        self._config = config or CrossDocumentCollapseConfig()

    def measure(self, statements: Iterable[BankStatement]) -> tuple[CollapseCandidate, ...]:
        """Candidatos com ≥2 proveniências na mesma chave — ordem estável por digest."""
        candidates = [self._candidate(group) for group in _group_by_key(statements)]
        return tuple(sorted(candidates, key=lambda c: c.key_digest))

    def _targets(self, group: _KeyGroup, removable: int) -> tuple[RemovalTarget, ...]:
        """Alvo por BUCKET com multiplicidade — nunca uma row por hash (ver RemovalTarget)."""
        if not removable:
            return ()
        # `llm_rows` é um único bucket de proveniência (o predicado exige exatamente
        # 1 perna nativa + 1 LLM), logo há no máximo um alvo. `min` impede declarar
        # remoção maior que o bucket, que a fatia antiga silenciava.
        stmt, tx = group.llm_rows[0]
        return (
            RemovalTarget(
                hash=_row_hash(tx, stmt),
                remover=min(removable, len(group.llm_rows)),
                no_bucket=len(group.llm_rows),
            ),
        )

    def _candidate(self, group: _KeyGroup) -> CollapseCandidate:
        reason = self._blocked_reason(group)
        removable = 0 if reason else len(group.rows) - group.survivor_cardinality
        targets = self._targets(group, removable)
        return CollapseCandidate(
            key_digest=_key_digest(group.key),
            mes=str(group.key[0])[:7],
            valor_cents=int(group.key[1]),
            moeda=str(group.key[2]),
            direction=str(group.key[3]),
            n_rows=len(group.rows),
            n_provenances=len(group.by_provenance),
            survivor_cardinality=group.survivor_cardinality,
            removable_rows=sum(t.remover for t in targets),
            removal_targets=targets,
            blocked_reason=reason,
            divergence=group.divergence,
            parciais=group.parciais,
        )

    def _blocked_reason(self, group: _KeyGroup) -> str | None:
        """Primeira cláusula do predicado que reprova — ``None`` quando colapsável."""
        if not str(group.key[4]):
            return "descricao_vazia"
        if len(group.by_provenance) != 2:
            return "proveniencias_diferente_de_duas"
        for name in ("banco", "titular"):
            if not _unifiable(group.field_values(name)):
                return f"{name}_conflitante"
        if not self._config.is_variant_pair(group.field_values("tipo_conta")):
            return "tipo_conta_fora_da_allow_list"
        return self._extraction_reason(group)

    def _extraction_reason(self, group: _KeyGroup) -> str | None:
        """Exatamente uma perna LLM e uma nativa; indeterminado nunca colapsa (fail-open)."""
        n_llm, n_native, n_indef = _extraction_split(stmt for stmt, _ in group.rows)
        if n_indef or not (n_llm and n_native):
            return "par_nao_e_nativo_mais_llm"
        return None
