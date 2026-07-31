#!/usr/bin/env python3
"""Render do detector cross-grupo ([[ADR-354]]) — boundary de PII do bloco do relatório."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # anotação sem import em runtime: a detecção NÃO depende do render
    from dev.ledger_cross_group import CrossGroupSummary

# Rótulo PRÓPRIO: ``DEDUP_LEGITIMO`` é um dos 5 vereditos da rubrica, e emprestar a
# autoridade de veredito a uma decisão de whitelist contamina o eixo de julgamento.
_EXPLAINED_LABEL = "shape declarado explicado"


def _sum_excess(hits: list) -> int:
    return sum(c.excess_cents for c in hits)


def _intra_prov_extra_rows(hits: list) -> int:
    """Rows além de 1 por proveniência: repetição legítima OU miss do dedup K4 (achado distinto)."""
    return sum(c.n_rows - c.n_provenances for c in hits)


def _fmt_coverage(cov: dict) -> list[str]:
    """Veredito grepável de cobertura + os denominadores que o tornam falsificável."""
    if not cov:
        return ["- **cobertura=CEGA — não medida (sem payload E4)**"]
    head = (
        "- cobertura=OK"
        if cov["coverage_ok"]
        else "- **cobertura=CEGA — bloco NÃO-VERIFICÁVEL, não leia como 0**"
    )
    return [
        f"{head} · {cov['rows_scanned']} rows varridas · {cov['rows_keyed']} chaveadas · "
        f"{cov['keys_distinct']} chaves distintas",
        f"- cobertura (falsificabilidade): declaradas={cov['declared_tx']} (total_transacoes, "
        f"campo que o detector NÃO lê) · multi-row={cov['keys_multirow']} · "
        f"triplas no corpus={cov['provenance_triples']} (<2 ⇒ critério vacuoso) · "
        f"baldes ilegíveis={'+'.join(cov['buckets_ilegiveis']) or 'nenhum'}",
        f"- 3ª identidade (nenhum filtro silencioso entre detector e numerador): "
        f"multi-proveniência={cov['keys_multiprov']} vs numerador+explicadas="
        f"{cov['particionadas']} ⇒ {'fecha' if cov['particao_fecha'] else 'NÃO FECHA'}",
    ]


def _fmt_unscanned(nao_varrido: dict, cov: dict) -> list[str]:
    """Massa que estruturalmente não passa pelos 2 baldes varridos + exclusões."""
    unkeyable = cov.get("unkeyable") or {}
    skip = " ".join(f"{k}={v}" for k, v in sorted(unkeyable.items())) or "n/d"
    massa = " ".join(f"{k}={v}" for k, v in sorted(nao_varrido.items())) or "n/d"
    return [
        f"- massa não-varrida (kind transferencia não vai a balde; queda de numerador "
        f"com esta massa subindo NÃO é progresso): {massa}",
        f"- rows não-chaveáveis (unidade: rows · declarado, anti-silêncio ADR-342): {skip} · "
        f"rows chaveadas com descrição normalizada vazia (unidade: rows, NÃO excluídas): "
        f"{cov.get('keyed_sem_descricao', 0)}",
    ]


_CARRIER_GLOSS = (
    "- carrier-shaped = assinatura de carrier [[ADR-354]] — a MESMA definição que a "
    "whitelist rejeita: `<campo>:c2` = campo de proveniência PARCIAL (vazio numa perna, "
    "preenchido na outra) · `tipo_conta:c1` = QUALQUER divergência de tipo_conta entre as "
    "pernas, mais largo que o par variante que motivou a ADR ('extrato' vs "
    "'extratoconta'): par de tipos de conta genuinamente distintos também sai "
    "carrier-shaped e fica IN-WHITELISTÁVEL até o alias-map versionado da [[A40.l2]] "
    "(sobre-detecção rotulada > sub-detecção silenciosa, [[ADR-342]])"
)


def _fmt_partition(hits: list) -> list[str]:
    """Partição carrier × coincidência — linha de RELATÓRIO, nunca predicado de entrada."""
    carrier = sum(1 for c in hits if c.defect_shaped)
    return [
        f"- partição do numerador (unidade: ocorrências): carrier-shaped={carrier} · "
        f"coincidence-shaped={len(hits) - carrier} · ocorrências com descrição normalizada "
        f"vazia={sum(1 for c in hits if c.descricao_vazia)} · rows além de 1 por "
        f"proveniência={_intra_prov_extra_rows(hits)} (repetição legítima OU miss de dedup "
        f"K4 — achado distinto, fora do numerador)",
        _CARRIER_GLOSS,
    ]


def _fmt_histogram(title: str, hits: list, key: Callable, cap: int) -> list[str]:
    """Histograma por classe: UM fix mata a classe inteira, então a triagem é por classe."""
    counts: dict[str, int] = {}
    for c in hits:
        counts[key(c)] = counts.get(key(c), 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [f"- {title}: {len(ranked)} classe(s)"] + [
        f"  · {shape} → {n} ocorrência(s)" for shape, n in ranked[:cap]
    ]


def _fmt_occurrences(hits: list, cap: int) -> list[str]:
    """Detalhe PII-safe: digest + mês + moeda + direction + contagens + tags de nome de campo."""
    if not hits:
        return []
    return [f"- ocorrências (cap {cap}; digest + tags de campo, sem valor exato):"] + [
        f"  · {c.key_digest} mes={c.mes} moeda={c.moeda} dir={c.direction} "
        f"rows={c.n_rows} provs={c.n_provenances} div={c.divergence or 'nenhum'} "
        f"parciais={c.parciais or 'nenhum'} vazio-total={c.vazios_totais or 'nenhum'} "
        f"carriers={'+'.join(c.carriers) or 'nenhum'} desc_vazia={int(c.descricao_vazia)}"
        for c in hits[:cap]
    ]


def _fmt_numerator(hits: list) -> list[str]:
    """Linha do numerador do KR-B + partição + 2 histogramas + ocorrências (``[off-git]``: ADR-343)."""
    head = (
        f"- não-explicada: {len(hits)} ocorrência(s) · "
        f"Σ excesso {_sum_excess(hits)} cents [off-git] · [numerador KR-B]"
    )
    return (
        [head]
        + _fmt_partition(hits)
        + _fmt_histogram("histograma diagnóstico (nomes de campo)", hits, lambda c: c.shape, 12)
        + _fmt_histogram(
            "histograma por shape de whitelist (valores de vocabulário fechado + fill-state de "
            "titular — o ÚNICO eixo que `explained` aceita)",
            hits,
            lambda c: c.explained_shape,
            12,
        )
        + _fmt_occurrences(hits, 20)
    )


def _fmt_explained(hits: list, shapes: tuple[str, ...]) -> list[str]:
    """Linha da whitelist APLICADA — separada por construção, nunca somada."""
    head = (
        f"- {_EXPLAINED_LABEL} (linha separada; NUNCA somada ao numerador): "
        f"{len(hits)} ocorrência(s) · Σ excesso {_sum_excess(hits)} cents [off-git]"
    )
    tail = f"- shapes declarados explicados (aplicados): {', '.join(shapes) or 'nenhum'}"
    return [head] + _fmt_occurrences(hits, 8) + [tail]


_TITLE = "## Duplicação cross-grupo — divergência CONFINADA à proveniência (reporta, não dedupa)"


def fmt_cross_group(cg: CrossGroupSummary) -> list[str]:
    """Bloco do relatório: cobertura primeiro, numerador e whitelisted em linhas SEPARADAS."""
    return (
        [_TITLE]
        + _fmt_coverage(cg.coverage)
        + _fmt_unscanned(cg.nao_varrido, cg.coverage)
        + _fmt_numerator(cg.numerador)
        + _fmt_explained(cg.explicadas, cg.explained_shapes)
    )
