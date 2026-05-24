"""IrpfDeclarationDeduplicator — colapsa fragmentos do mesmo (cpf, ano, natureza)."""

# Resposta ao bug operacional (workspace 1b9f2cf5...): usuário sobe N PDFs
# distintos de IRPF do mesmo titular/ano (original, retificadora, recibo,
# screenshot) e o analyzer soma todos. Política (data-engineer):
# - Chave: (cpf_masked, ano_base, natureza).
# - Score: blocos de renda + pagamentos + min(bens, 4) × 0.5.
# - Tie-break: maior tie_break_key (caller passa created_at ISO ou index).
# - Levenshtein normalizado > 0.3 sobre nome → warning (não bloqueia).
# - Mesmo nome canônico em CPFs distintos → warning de OCR.
# Idempotência upstream no upload é A-condicional (lane futura).

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

# Threshold padrão para divergência de nomes (Levenshtein normalizado).
# 0.3 = ~30% dos caracteres diferentes. Ex.: "FERREIRA CAMPOS" vs "DE CAMPOS"
# em "DAVID ROBERT CAMARGO {X} CAMPOS" → distance ~0.19, abaixo do threshold.
_DEFAULT_NAME_DIVERGENCE_THRESHOLD = 0.3

# Cap de bens no score: IRPF pré-preenchida traz bens herdados; sem cap,
# fragmento com 18 bens + 0 PJ domina fragmento com 1 PJ + 2 isentos.
_BENS_SCORE_CAP = 4


@dataclass(frozen=True)
class IrpfFragment:
    """Wrapper de uma declaração IRPF candidata + chave de desempate."""

    declaration: IRPFFullOutput
    tie_break_key: str = ""


@dataclass(frozen=True)
class DiscardedFragment:
    """Fragmento descartado pelo dedup — preservado para auditoria."""

    declaration: IRPFFullOutput
    tie_break_key: str
    score: float
    reason: str  # "lower_score" | "lost_tie_break" | "shell_declaration"


@dataclass(frozen=True)
class CollisionWarning:
    """Sinal de ambiguidade que merece revisão humana — não bloqueia dedup."""

    cpf_masked: str
    ano_base: int
    natureza: str
    kind: str  # "name_divergence" | "cross_cpf_same_name"
    details: str


@dataclass(frozen=True)
class DeduplicatedIRPFSet:
    """Resultado canônico do dedup — winners + auditoria + colisões."""

    winners: list[IRPFFullOutput] = field(default_factory=list)
    discarded: list[DiscardedFragment] = field(default_factory=list)
    collisions: list[CollisionWarning] = field(default_factory=list)


def deduplicate_irpf_declarations(
    fragments: Iterable[IrpfFragment],
    *,
    name_divergence_threshold: float = _DEFAULT_NAME_DIVERGENCE_THRESHOLD,
) -> DeduplicatedIRPFSet:
    """Aplica dedup score-based + detecção de colisões. Pure function."""
    items = list(fragments)
    if not items:
        return DeduplicatedIRPFSet()

    winners, discarded, collisions = _resolve_all_groups(
        _group_by_identity(items), name_divergence_threshold
    )
    collisions.extend(_detect_cross_cpf_collisions(winners))
    return DeduplicatedIRPFSet(winners, discarded, collisions)


def _resolve_all_groups(
    groups: dict[tuple[str, int, str], list[IrpfFragment]],
    threshold: float,
) -> tuple[list[IRPFFullOutput], list[DiscardedFragment], list[CollisionWarning]]:
    """Loop sobre grupos, agregando winners/discarded/collisions intra-grupo."""
    winners: list[IRPFFullOutput] = []
    discarded: list[DiscardedFragment] = []
    collisions: list[CollisionWarning] = []
    for (cpf, ano, natureza), group in groups.items():
        w, d, c = _resolve_group(cpf, ano, natureza, group, threshold)
        if w is not None:
            winners.append(w.declaration)
        discarded.extend(d)
        collisions.extend(c)
    return winners, discarded, collisions


def _group_by_identity(
    fragments: list[IrpfFragment],
) -> dict[tuple[str, int, str], list[IrpfFragment]]:
    """Agrupa fragmentos por (cpf_masked, ano_base, natureza)."""
    groups: dict[tuple[str, int, str], list[IrpfFragment]] = {}
    for frag in fragments:
        c = frag.declaration.contribuinte
        key = (c.cpf_masked, c.ano_base, c.natureza.value)
        groups.setdefault(key, []).append(frag)
    return groups


def _resolve_group(
    cpf: str,
    ano: int,
    natureza: str,
    group: list[IrpfFragment],
    threshold: float,
) -> tuple[IrpfFragment | None, list[DiscardedFragment], list[CollisionWarning]]:
    """Escolhe winner do grupo + lista descartados e colisões intra-grupo."""
    if not group:
        return None, [], []
    scored = _sort_by_score(group)
    winner_frag, winner_score = scored[0]
    discarded = [_make_discarded(f, s, winner_score) for f, s in scored[1:]]
    collisions = _detect_name_divergence(cpf, ano, natureza, group, threshold)
    return winner_frag, discarded, collisions


def _sort_by_score(group: list[IrpfFragment]) -> list[tuple[IrpfFragment, float]]:
    """Sort por (score desc, tie_break_key desc) — maior vence em ambas as dimensões."""
    scored = [(frag, _score(frag.declaration)) for frag in group]
    scored.sort(key=lambda x: (x[1], x[0].tie_break_key), reverse=True)
    return scored


def _make_discarded(frag: IrpfFragment, score: float, winner_score: float) -> DiscardedFragment:
    return DiscardedFragment(
        declaration=frag.declaration,
        tie_break_key=frag.tie_break_key,
        score=score,
        reason=_discard_reason(frag, score, winner_score),
    )


def _score(decl: IRPFFullOutput) -> float:
    """Completude (renda > patrimônio): blocos de renda + min(bens, 4) × 0.5."""
    bens_score = min(len(decl.bens_direitos), _BENS_SCORE_CAP) * 0.5
    return (
        len(decl.rendimentos_pj)
        + len(decl.rendimentos_pf)
        + len(decl.rendimentos_isentos)
        + len(decl.rendimentos_tributacao_exclusiva)
        + len(decl.pagamentos_efetuados)
        + bens_score
    )


def _discard_reason(frag: IrpfFragment, score: float, winner_score: float) -> str:
    if score == 0 and _is_shell(frag.declaration):
        return "shell_declaration"
    if score < winner_score:
        return "lower_score"
    return "lost_tie_break"


def _is_shell(decl: IRPFFullOutput) -> bool:
    """Declaração-fantasma: todos os blocos de renda+pagamento+bens vazios."""
    return (
        not decl.rendimentos_pj
        and not decl.rendimentos_pf
        and not decl.rendimentos_isentos
        and not decl.rendimentos_tributacao_exclusiva
        and not decl.pagamentos_efetuados
        and not decl.bens_direitos
    )


def _detect_name_divergence(
    cpf: str,
    ano: int,
    natureza: str,
    group: list[IrpfFragment],
    threshold: float,
) -> list[CollisionWarning]:
    """Emite warning se 2+ fragmentos no grupo têm nomes divergentes."""
    if len(group) < 2:
        return []
    names = [_normalize_nome(f.declaration.contribuinte.nome) for f in group]
    max_dist, worst = _max_pairwise_distance(names)
    if max_dist <= threshold:
        return []
    details = f'distance={max_dist:.2f} between "{worst[0]}" and "{worst[1]}"'
    return [CollisionWarning(cpf, ano, natureza, "name_divergence", details)]


def _max_pairwise_distance(names: list[str]) -> tuple[float, tuple[str, str]]:
    """Maior Levenshtein normalizado entre qualquer par; nome do par junto."""
    pairs = ((a, b) for i, a in enumerate(names) for b in names[i + 1 :])
    best_dist = 0.0
    best_pair: tuple[str, str] = ("", "")
    for a, b in pairs:
        d = _levenshtein_normalized(a, b)
        if d > best_dist:
            best_dist, best_pair = d, (a, b)
    return best_dist, best_pair


def _detect_cross_cpf_collisions(
    winners: list[IRPFFullOutput],
) -> list[CollisionWarning]:
    """Mesmo nome canônico em CPFs distintos no mesmo (ano, natureza)."""
    # Caso real: -36 e -87 com mesmo nome (OCR ruim no último dígito). Não
    # fundimos; só sinalizamos para revisão humana.
    by_identity = _group_winners_by_canonical_name(winners)
    return [_emit_cross_cpf(k, cpfs) for k, cpfs in by_identity.items() if len(set(cpfs)) >= 2]


def _group_winners_by_canonical_name(
    winners: list[IRPFFullOutput],
) -> dict[tuple[str, int, str], list[str]]:
    by_identity: dict[tuple[str, int, str], list[str]] = {}
    for decl in winners:
        c = decl.contribuinte
        key = (_normalize_nome(c.nome), c.ano_base, c.natureza.value)
        by_identity.setdefault(key, []).append(c.cpf_masked)
    return by_identity


def _emit_cross_cpf(key: tuple[str, int, str], cpfs: list[str]) -> CollisionWarning:
    nome, ano, natureza = key
    unique = sorted(set(cpfs))
    return CollisionWarning(
        cpf_masked=", ".join(unique),
        ano_base=ano,
        natureza=natureza,
        kind="cross_cpf_same_name",
        details=f'nome canônico "{nome}" aparece em {len(unique)} CPFs distintos',
    )


def _normalize_nome(nome: str) -> str:
    """Lower + strip acentos + collapse spaces — comparação tolerante a OCR."""
    decomposed = unicodedata.normalize("NFD", nome)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(ascii_only.lower().split())


def _levenshtein_normalized(a: str, b: str) -> float:
    """Distância Levenshtein normalizada por max(len) — em [0.0, 1.0]."""
    if a == b:
        return 0.0
    if not a or not b:
        return 1.0
    return _levenshtein(a, b) / max(len(a), len(b))


def _levenshtein(a: str, b: str) -> int:
    """Distância de edição clássica (DP O(n×m), suficiente para nomes curtos)."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = _levenshtein_row(ca, b, previous, i)
        previous = current
    return previous[-1]


def _levenshtein_row(ca: str, b: str, previous: list[int], i: int) -> list[int]:
    """Uma linha do DP — extraída para reduzir profundidade de nesting."""
    current = [i] + [0] * len(b)
    for j, cb in enumerate(b, start=1):
        insert_cost = current[j - 1] + 1
        delete_cost = previous[j] + 1
        replace_cost = previous[j - 1] + (0 if ca == cb else 1)
        current[j] = min(insert_cost, delete_cost, replace_cost)
    return current
