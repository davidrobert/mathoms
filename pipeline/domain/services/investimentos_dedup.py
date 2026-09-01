"""Dedup de investimentos cross-IRPF (cross-year + cross-declarante) como policy
sobre ``run_entity_dedup`` (ADR-271, ADR-276); duas divergências vs. imóveis:
cross-year une ``valores_31_12`` marcando a mercado (ano mais recente, não piso),
e cross-declarante funde APENAS com valor 31/12 idêntico ao centavo (conta
conjunta) — calibração conservadora, falso-positivo (some PL) pior que falso-negativo.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pipeline.domain.review_reason import ReviewReason, ReviewReasonCode
from pipeline.domain.services._tx_identity import cents_int, normalize_descricao
from pipeline.domain.services.ancora_cnpj import (
    CoberturaAncora,
    ancora_da_entrada,
    medir_cobertura,
)
from pipeline.domain.services.entity_dedup import (
    DedupOutcome,
    DedupWarning,
    GroupedEntries,
    log_dedup,
    run_entity_dedup,
)
from pipeline.domain.services.patrimonio_types import parse_ano_31_12

_CASAL_LABEL = "casal"


@dataclass(frozen=True)
class InvestDedupWarning:
    investment_id: str | None
    type: str  # "valor_divergente_ano" | "possivel_duplicata"
    values: tuple[float, ...]
    diff_pct: float


@dataclass(frozen=True)
class InvestDedupResult:
    investimentos: list[dict]
    warnings: tuple[InvestDedupWarning, ...]
    count_before: int
    count_after: int
    dropped_keys: tuple[str, ...]
    cobertura_ancora: CoberturaAncora = CoberturaAncora()


def dedup_investimentos_consolidados(
    investimentos: list[dict] | None,
) -> InvestDedupResult:
    """Deduplica ``investimentos_consolidados`` por identidade cross-IRPF (ADR-271)."""
    cobertura = medir_cobertura(investimentos)
    outcome = run_entity_dedup(investimentos, _InvestmentPolicy())
    log_dedup("consolidate.investimentos_dedup", outcome, dropped_key="dropped_keys")
    _anexa_recusa(outcome.items)
    return _to_result(outcome, cobertura)


# Recusar sem dizer por quê é indistinguível de esquecer: a entrada sai do dedup igual
# a uma que passou. A razão nasce DENTRO do item porque `harvest_review_reasons` a colhe
# em qualquer profundidade, com o locator da coleção.
def _anexa_recusa(entradas: list[dict]) -> None:
    """Entrada sem âncora E sem descrição sai com motivo, nunca com hash de vazio."""
    for entrada in entradas:
        if _identity_key(entrada) is not None:
            continue
        reasons = entrada.setdefault("review_reasons", [])
        # Idempotente: o dedup roda de novo sobre a própria saída (invariante testado).
        if any(r.get("code") == _CODIGO_RECUSA for r in reasons):
            continue
        reasons.append(_razao_da_recusa())


_CODIGO_RECUSA = ReviewReasonCode.dedup_identidade_sem_ancora.value


def _razao_da_recusa() -> dict:
    return ReviewReason(
        code=ReviewReasonCode.dedup_identidade_sem_ancora,
        stage="consolidate_baseline",
        artifact_key="investimentos_consolidados",
        document_id=None,
        offending_value="<sem cnpj_emissor, sem CNPJ na descricao, sem descricao>",
        expected="cnpj_emissor de 14 digitos, ou CNPJ no texto, ou descricao nao-vazia",
        message="identidade recusada: nenhum degrau da cascata alcancou a entrada",
    ).to_dict()


def _to_result(outcome: DedupOutcome, cobertura: CoberturaAncora) -> InvestDedupResult:
    return InvestDedupResult(
        investimentos=outcome.items,
        warnings=tuple(_to_invest_warning(w) for w in outcome.warnings),
        count_before=outcome.count_before,
        count_after=outcome.count_after,
        dropped_keys=outcome.dropped_ids,
        cobertura_ancora=cobertura,
    )


def _to_invest_warning(w: DedupWarning) -> InvestDedupWarning:
    return InvestDedupWarning(
        investment_id=w.entity_id, type=w.type, values=w.values, diff_pct=w.diff_pct
    )


class _InvestmentPolicy:
    """Cascata `("cnpj", raiz)` ⊳ `("desc", tipo, inst_norm, desc_norm)`; sem reagrupamento."""

    def identity_key(self, entry: dict) -> tuple | None:
        return _identity_key(entry)

    def remap_groups(self, grouped: GroupedEntries) -> GroupedEntries:
        return grouped

    def emit_group(
        self, group: list[dict]
    ) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
        inv_id = _investment_id(_identity_key(group[0]))
        if len(group) == 1:
            return [_stamp_id(group[0], inv_id)], (), ()
        warnings: list[DedupWarning] = []
        per_owner = _merge_cross_year(group, inv_id, warnings)
        if len(per_owner) == 1:
            return per_owner, tuple(warnings), _dropped(group, inv_id)
        entries, dec_warnings, dropped = _emit_cross_declarante(inv_id, per_owner, group)
        return entries, tuple(warnings) + dec_warnings, dropped


# Cascata medida ([[A42.l15]], 836 artefatos / 28 grupos, pooled |A∩B|/|A∪B|):
# `(tipo,inst,desc)` 37,68% → com a âncora na frente **61,78%**. O subconjunto
# ancorado sozinho é 91,71% estável, e a âncora cobre ~metade das entradas.
#
# `instituicao` FICA na perna fraca, contra o que a lane planejava. Tirá-la mede
# 69,20% — mais 7,4pp — mas funde "Tesouro Selic 2029" na XP com o da BTG: mesmo
# título em duas corretoras vira uma entrada e **some com patrimônio real**, que é o
# falso-positivo que a [[ADR-271]] §139 rejeita explicitamente. A medição de que sair
# custa 0 em cardinalidade é propriedade DESTE corpus (que não tem o caso), não do
# desenho — quem pegou foi `test_different_institution_does_not_merge`.
# A [[ADR-400]] §1 segue respeitada: o que entra aqui é a string crua do item, nunca o
# code do `institution_catalog` — é o status quo, não acoplamento novo (gate: PR #1916).
#
# A âncora NÃO se compõe com `tipo`: `("cnpj",raiz,tipo)` mede 63,49% contra 69,20% da
# âncora sozinha no mesmo braço, porque `tipo` ainda churna. Compor parece mais seguro
# e é menos.
def _identity_key(entry: dict) -> tuple | None:
    """Chave do ATIVO, agnóstica a ano e proprietário. ``None`` = unidentified."""
    raiz = ancora_da_entrada(entry)
    if raiz:
        return ("cnpj", raiz)
    desc = normalize_descricao(entry.get("descricao"))
    if not desc:
        return None
    tipo = (entry.get("tipo") or "").strip().lower()
    inst = normalize_descricao(entry.get("instituicao"))
    return ("desc", tipo, inst, desc)


def _investment_id(key: tuple | None) -> str:
    raw = "|".join(str(p) for p in (key or ()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _dropped(group: list[dict], inv_id: str) -> tuple[str, ...]:
    return tuple(inv_id for _ in range(max(0, len(group) - 1)))


def _merge_cross_year(
    group: list[dict],
    inv_id: str,
    warnings: list[DedupWarning],
) -> list[dict]:
    """Funde entries do mesmo proprietário (anos sucessivos) em uma por owner."""
    by_owner: dict[str, list[dict]] = {}
    order: list[str] = []
    for entry in group:
        owner = _owner(entry)
        if owner not in by_owner:
            by_owner[owner] = []
            order.append(owner)
        by_owner[owner].append(entry)
    return [_merge_owner_entries(by_owner[o], inv_id, warnings) for o in order]


def _merge_owner_entries(
    entries: list[dict],
    inv_id: str,
    warnings: list[DedupWarning],
) -> dict:
    if len(entries) == 1:
        return _stamp_id(entries[0], inv_id)
    merged = dict(entries[0])
    valores: dict[str, float] = {}
    for entry in entries:
        _union_valores(valores, entry, inv_id, warnings)
    merged["valores_31_12"] = valores
    return _stamp_id(merged, inv_id)


def _union_valores(
    acc: dict[str, float],
    entry: dict,
    inv_id: str,
    warnings: list[DedupWarning],
) -> None:
    for ano, valor in (entry.get("valores_31_12") or {}).items():
        v = _safe_float(valor)
        if ano in acc and cents_int(acc[ano]) != cents_int(v):
            warnings.append(_year_conflict_warning(inv_id, acc[ano], v))
            acc[ano] = max(acc[ano], v)
        else:
            acc[ano] = v


def _emit_cross_declarante(
    inv_id: str,
    per_owner: list[dict],
    group: list[dict],
) -> tuple[list[dict], tuple[DedupWarning, ...], tuple[str, ...]]:
    """Mesmo ativo, proprietários distintos: funde só se valor idêntico ao centavo."""
    if _is_joint_account(per_owner):
        return [_merge_joint(per_owner, inv_id)], (), _dropped(group, inv_id)
    entries: list[dict] = []
    for entry in per_owner:
        stamped = dict(entry)
        stamped["_dedup_warning"] = {"type": "possivel_duplicata"}
        entries.append(stamped)
    return entries, (_duplicata_warning(inv_id, per_owner),), ()


def _duplicata_warning(inv_id: str, per_owner: list[dict]) -> DedupWarning:
    return DedupWarning(
        entity_id=inv_id,
        type="possivel_duplicata",
        values=tuple(_latest_value(e) for e in per_owner),
        diff_pct=0.0,
    )


def _is_joint_account(per_owner: list[dict]) -> bool:
    """True quando todos os declarantes trazem o MESMO valor 31/12 (ao centavo)."""
    cents = {cents_int(_latest_value(e)) for e in per_owner}
    return len(cents) == 1 and 0 not in cents


def _merge_joint(per_owner: list[dict], inv_id: str) -> dict:
    winner = dict(per_owner[0])
    owners = sorted({_owner(e) for e in per_owner if _owner(e)})
    winner["proprietarios"] = owners
    winner["proprietario"] = _CASAL_LABEL
    return _stamp_id(winner, inv_id)


def _owner(entry: dict) -> str:
    return (entry.get("proprietario") or "").strip().lower()


def _latest_value(entry: dict) -> float:
    vals = entry.get("valores_31_12") or {}
    if isinstance(vals, dict) and vals:
        # parse_ano_31_12: max() lexicográfico faz "31_12_2024" vencer "2025" (A40.l42).
        latest = max(vals.keys(), key=lambda k: (parse_ano_31_12(k) or 0, str(k)))
        return _safe_float(vals.get(latest))
    return _safe_float(entry.get("valor", 0))


def _year_conflict_warning(inv_id: str, a: float, b: float) -> DedupWarning:
    diff_pct = abs(a - b) / max(abs(a), abs(b)) * 100 if max(abs(a), abs(b)) else 0.0
    return DedupWarning(
        entity_id=inv_id,
        type="valor_divergente_ano",
        values=(a, b),
        diff_pct=round(diff_pct, 1),
    )


def _stamp_id(entry: dict, inv_id: str) -> dict:
    if entry.get("investment_id") == inv_id:
        return entry
    out = dict(entry)
    out["investment_id"] = inv_id
    return out


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = [
    "InvestDedupResult",
    "InvestDedupWarning",
    "dedup_investimentos_consolidados",
]
