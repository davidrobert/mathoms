#!/usr/bin/env python3
"""Núcleo puro da ledger-certify: vereditos por grupo/balde + drift + relatório.

Sem I/O, sem backend — recebe os artefatos E2/E3/E4 (dicts) + o
``CategorizationResult`` já re-derivados e computa os 5 vereditos da rubrica, o
sumário de drift fresco↔persistido e o texto PII-safe. A leitura do DB e a
re-derivação in-process ficam em ``dev.certify_ledger_local`` (o harness);
importar este módulo não exige env/DB. Reusa o ledger de conservação em cents
(``dev.ledger_conservation``, tol-zero ADR-090).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import to_cents
from dev.ledger_collapse_layer import (
    CollapseLayerSummary,
    collapse_layer_summary,
    detector_digests,
    fmt_collapse_layer,
)
from dev.ledger_conservation import (
    NAO_VERIFICAVEL,
    CrossGroupSummary,
    cross_group_summary,
    declared_removed_count,
    e2_to_e3,
    e3_to_e4,
    fmt_cross_group,
    investment_double_count,
)
from dev.ledger_cross_group_render import _KR_B_LABEL, _SOMBRA_LABEL, _TITLE

# Re-export: a rubrica saiu para `ledger_unit_verdicts` em A42.l19 (o núcleo
# cruzou as 500 linhas); os call-sites que importavam daqui seguem valendo.
from dev.ledger_unit_verdicts import e3_group_verdict, e4_bucket_verdict  # noqa: F401


@dataclass(frozen=True)
class UnitVerdict:
    """Veredito de um grupo E3 ou balde E4 (grão de reporte da rubrica)."""

    unit: str
    verdict: str
    detail: str
    metrics: dict


@dataclass
class DriftSummary:
    """Sumário do cross-check fresco↔persistido (drift, não perda)."""

    matched: int
    count_diff: list
    fresh_only: list
    persisted_only: list


@dataclass
class LedgerReport:
    workspace_id: str
    run_id: str | None
    e2_seeded: int
    e2_tx: int
    e3_exec: dict
    conservation: list
    e3_groups: list
    e4_buckets: list
    investment_collisions: list
    natural_key: dict
    drift: DriftSummary
    counts_before: dict = field(default_factory=dict)
    counts_after: dict = field(default_factory=dict)
    cross_group: CrossGroupSummary = field(default_factory=CrossGroupSummary)
    # A40.l2 PR1b — camada E3 do colapso, ao lado do numerador E4: o gate do enforce
    # não pode ser lido só pelo detector (populações distintas por construção).
    collapse_layer: CollapseLayerSummary = field(default_factory=CollapseLayerSummary)
    blast_radius: dict = field(default_factory=dict)
    # Modo entregue (KR-B): detector sobre E3 persistido do run pinado.
    # Vazio = relatório só-sombra; a sombra NÃO pontua a KR.
    cross_group_entregue: CrossGroupSummary | None = None
    entregue: dict = field(default_factory=dict)
    # Censo de proveniência do E2 (ADR-421 D3) — vazio = NÃO MEDIDO, nunca "tudo do run".
    e2_provenance: dict = field(default_factory=dict)
    # Substrato do eixo E4: "entregue" (E4 publicado pelo run) ou "sombra" (re-derivação).
    e4_subject: str = "sombra"

    @property
    def zero_write_ok(self) -> bool:
        return self.counts_before == self.counts_after


# ─────────────────────────── drift + cobertura ───────────────────────────


# A42.l20 — somar só `transacoes_duplicadas_removidas` lia apenas o canal
# `cross_file_dedup`: um canal declarado (o colapso cross-documento) saía como *count
# divergente*. `declared_removed_count` é o mesmo normalizador da conservação E2→E3, e
# degrada ao campo legado quando o artefato não tem `remocoes`.
def _e3_count(payload) -> int:
    """População que o grupo PRESTA CONTA: sobreviventes + remoções declaradas."""
    if not isinstance(payload, dict):
        return -1
    return int(payload.get("transacoes_total", 0)) + declared_removed_count(payload)


def _count_diffs(fresh_e3: dict, persisted_e3: dict) -> tuple[int, list[str]]:
    matched, diffs = 0, []
    for key, fresh in fresh_e3.items():
        pers = persisted_e3.get(key)
        if pers is None:
            continue
        f_n, p_n = _e3_count(fresh), _e3_count(pers)
        (diffs.append(f"{key}: n_tx fresco {f_n} != persistido {p_n}") if f_n != p_n else None)
        matched += int(f_n == p_n)
    return matched, diffs


def _drift(fresh_e3: dict, persisted_e3: dict) -> DriftSummary:
    """Cross-check fresco↔persistido por grupo — divergência = drift (reporta, não falha)."""
    # O count vem normalizado pelos canais de `remocoes` (ver `_e3_count`), então remoção
    # DECLARADA dos dois lados não é divergência. O que sobra tem TRÊS causas: keying/dedup
    # mudou pós-run, artefato de run parcial, OU a config do harness diverge da do run
    # (ex.: `collapse_enforce`) num eixo que nenhum canal declara. Atribuir só as duas
    # primeiras foi o defeito da A42.l20.
    matched, count_diff = _count_diffs(fresh_e3, persisted_e3)
    return DriftSummary(
        matched=matched,
        count_diff=count_diff,
        fresh_only=sorted(set(fresh_e3) - set(persisted_e3)),
        persisted_only=sorted(set(persisted_e3) - set(fresh_e3)),
    )


def _natural_key_coverage(result) -> dict:
    """Cobertura de ``natural_key`` (% de tx classificadas com chave) — KR embrião."""
    txns = result.classified
    total = len(txns)
    present = sum(1 for t in txns if t.natural_key is not None)
    pct = round(100.0 * present / total, 1) if total else 0.0
    return {"total": total, "present": present, "pct": pct}


# ─────────────────────────── montagem do report ───────────────────────────


def _conservation(e2_payloads: list, fresh_e3: dict, e4: dict, result) -> list:
    e3_list = list(fresh_e3.values())
    return [
        e2_to_e3(e2_payloads, e3_list),
        # O lado-saída vem dos sinais que o E4 DECLARA no artefato ([[ADR-426]]); somar
        # `result.classified` aqui era comparar a origem consigo mesma.
        e3_to_e4(
            e3_list,
            e4.get("despesas", {}),
            e4.get("receitas", {}),
            result.cash_flow.transferencias_count,
        ),
    ]


def _e3_verdicts(fresh_e3: dict) -> list:
    out = []
    for key in sorted(fresh_e3):
        verdict, detail = e3_group_verdict(fresh_e3[key])
        out.append(UnitVerdict(key, verdict, detail, {"n_tx": _e3_count(fresh_e3[key])}))
    return out


def _bucket_metrics(payload) -> dict:
    if not isinstance(payload, dict):
        return {}
    dados = payload.get("dados")
    n = len(dados) if isinstance(dados, (list, dict)) else 0
    return {"n": n, "n_tx": int(payload.get("total_transacoes", 0))}


def _expected_buckets(e4: dict) -> list[str]:
    """Baldes canônicos do E4 + qualquer key inesperada — a UNIÃO, nunca só o presente."""
    from pipeline.domain.services.e4_serialization import ARTIFACT_KEYS

    return list(ARTIFACT_KEYS) + sorted(set(e4) - set(ARTIFACT_KEYS))


def _bucket_verdict(key: str, e4: dict, collisions: list) -> UnitVerdict:
    """Veredito de um balde — ausente vira linha `não-verificável`, nunca silêncio (D6)."""
    if key not in e4:
        return UnitVerdict(key, NAO_VERIFICAVEL, "balde ausente no sujeito", {})
    verdict, detail = e4_bucket_verdict(key, e4[key], collisions)
    return UnitVerdict(key, verdict, detail, _bucket_metrics(e4[key]))


def _e4_verdicts(e4: dict, collisions: list) -> list:
    """Um veredito por balde ESPERADO — `sorted(e4)` omitia o ausente (ADR-421 D6)."""
    return [_bucket_verdict(k, e4, collisions) for k in _expected_buckets(e4)]


def _e3_exec_dict(e3_result) -> dict:
    excl: dict[str, int] = {}  # ADR-347 PR2 — tx contadas por canal de exclusão
    for e in getattr(e3_result, "exclusions", ()):
        excl[e.canal] = excl.get(e.canal, 0) + e.count
    return {
        "statements_loaded": e3_result.statements_loaded,
        "statements_reconciled": e3_result.statements_reconciled,
        "skipped_inputs": e3_result.skipped_inputs,
        "artifacts_written": e3_result.artifacts_written,
        "exclusions": excl,
    }


def _collapse_layer(e3_result, cross_group) -> CollapseLayerSummary:
    """Camada E3 medida contra o numerador do detector — vazia se o colapsador não
    foi injetado (``default None`` no adapter mantém o stage inerte)."""
    return collapse_layer_summary(
        getattr(e3_result, "collapse_candidates", ()), detector_digests(cross_group)
    )


def _e4_subject(e4: dict, e4_persisted) -> tuple[dict, str]:
    """Sujeito do eixo E4 + rótulo do substrato ([[ADR-421]] D4)."""
    # Balde e colisão de investimento vêm do E4 PUBLICADO. Sem ele o eixo cai para a
    # re-derivação — e o RÓTULO diz isso, em vez de herdar em silêncio (D6).
    return (e4_persisted, "entregue") if e4_persisted else (e4, "sombra")


def _subject_axes(e4: dict, e4_persisted) -> dict:
    """Os três eixos que descrevem o SUJEITO: rótulo, baldes e colisões de investimento."""
    subject, label = _e4_subject(e4, e4_persisted)
    collisions = investment_double_count(subject.get("investimentos", {}))
    return {
        "e4_subject": label,
        "e4_buckets": _e4_verdicts(subject, collisions),
        "investment_collisions": collisions,
    }


def build_report(
    ws, run_id, seeds, e3_result, result, e4, fresh_e3, persisted_e3, *, e4_persisted=None
) -> LedgerReport:
    """Monta o ``LedgerReport``; o eixo E4 descreve o artefato ENTREGUE quando ele existe."""
    cross_group = cross_group_summary(e4, result.cash_flow.transferencias_count)
    return LedgerReport(
        **_subject_axes(e4, e4_persisted),
        workspace_id=ws,
        run_id=run_id,
        e2_seeded=len(seeds),
        e2_tx=sum(len(p.get("transacoes", [])) for p in seeds),
        e3_exec=_e3_exec_dict(e3_result),
        conservation=_conservation(seeds, fresh_e3, e4, result),
        e3_groups=_e3_verdicts(fresh_e3),
        natural_key=_natural_key_coverage(result),
        drift=_drift(fresh_e3, persisted_e3),
        cross_group=cross_group,
        collapse_layer=_collapse_layer(e3_result, cross_group),
    )


# ─────────────────────────── relatório (PII-safe) ───────────────────────────


def _delta_cents(a, b) -> str:
    if a is None or b is None:
        return "n/d"
    return str(b - a)


def _fmt_conservation(results: list) -> list[str]:
    lines = ["## Conservação (workspace, cents tol-zero)"]
    for r in results:
        delta = _delta_cents(r.value_in_cents, r.value_out_cents)
        lines.append(
            f"- {r.transition}: count {r.count_in}->{r.count_out} dups={r.dups} "
            f"Δvalor={delta} cents · **{r.verdict}** — {r.detail}"
        )
    return lines


_E2_PROV_TITLE = "## Substrato E2 (proveniência)"


def _fmt_e2_provenance(cen: dict) -> list[str]:
    """Censo do substrato E2 — `do run` / `herdado` / `descartado pós-run` ([[ADR-421]] D3)."""
    if not cen:
        return [_E2_PROV_TITLE, "- não medido — leia o bloco como não-verificável [entregue]"]
    return [
        _E2_PROV_TITLE,
        f"- do run={cen['do_run']} · herdado={cen['herdado']} · "
        f"descartado pós-run={cen['descartado_pos_run']} · corte temporal: {cen['corte']}",
        "- E2 é workspace-scoped POR DECISÃO ([[ADR-241]]): `herdado` é o regime normal, "
        "não anomalia — run-escopá-lo seria regressão",
    ]


def _fmt_exec(report: LedgerReport) -> list[str]:
    e = report.e3_exec
    excl = e.get("exclusions") or {}
    excl_txt = ", ".join(f"{k}={v}" for k, v in sorted(excl.items())) if excl else "nenhuma"
    return [
        "## E3 execução (contexto do gap E2→E3)",
        f"- statements: carregados={e['statements_loaded']} reconciliados={e['statements_reconciled']} "
        f"skipped={e['skipped_inputs']} artefatos={e['artifacts_written']}",
        f"- exclusões de statement no load (tx por canal, ADR-347 PR2): {excl_txt}",
        "- gap de count E2→E3 = remoções por artefato (remocoes) + exclusões acima; "
        "o ledger que fecha por grupo prova a conservação, resíduo = perda",
    ]


def _fmt_units(title: str, units: list) -> list[str]:
    lines = [title]
    for u in units:
        metrics = " ".join(f"{k}={v}" for k, v in u.metrics.items())
        lines.append(f"- {u.unit} [{metrics}] · **{u.verdict}** — {u.detail}")
    return lines


def _fmt_tail(report: LedgerReport) -> list[str]:
    nk = report.natural_key
    zw = "OK (inalterado)" if report.zero_write_ok else "VIOLADO"
    return [
        "## natural_key",
        f"- cobertura: {nk['present']}/{nk['total']} ({nk['pct']}%)",
        "## Zero-write",
        f"- pipeline_artifacts/transaction_overrides antes={report.counts_before} "
        f"depois={report.counts_after} · **{zw}**",
    ]


def _fmt_drift(d: DriftSummary) -> list[str]:
    lines = [
        "## Drift fresco↔persistido (reporta, não falha)",
        f"- grupos casados (mesmo count): {d.matched}",
        f"- count divergente: {len(d.count_diff)}",
    ]
    lines += [f"  · {c}" for c in d.count_diff[:20]]
    lines.append(f"- só no fresco (re-derivação re-chaveou / grupo novo): {len(d.fresh_only)}")
    lines += [f"  · {k}" for k in d.fresh_only[:8]]
    # A glosa antiga dizia "keying antigo não reproduzido" — ATRIBUIÇÃO FALSA DE CAUSA.
    # Medido (ADR-421 M1): os 31 grupos eram 31/31 sobra de 7 OUTROS runs, e o run pinado
    # escreveu zero deles. Nada na re-chaveação estava implicado. Com o substrato agora
    # run-scoped, a sobra cross-run não pode mais aparecer aqui — o que sobrar é do run.
    lines.append(
        f"- só no persistido do run (publicado e não reproduzido): {len(d.persisted_only)}"
    )
    lines += [f"  · {k}" for k in d.persisted_only[:8]]
    return lines


def _ancora_identity(br: dict) -> str:
    """ADR-282: ``as_columns()`` escreve ``natural_key_hash`` e o snapshot juntos, logo os
    dois contadores DEVEM coincidir — comparação derivada, não prosa estática."""
    if br["sem_ancora_v2"] == br["sem_snapshot"]:
        return "=="
    return "!= (writer contornou as_columns)"


def _fmt_blast_radius(br: dict) -> list[str]:
    """Blast radius da A40.l2 — lado-override do mesmo titular vazio; inertes em linha separada."""
    if not br:
        return [
            "## Blast radius A40.l2",
            "- não medido (sem sessão DB **ou** schema divergente — ver stderr)",
        ]
    return [
        "## Blast radius A40.l2 (overrides ancorados em row de titular vazio)",
        f"- numerador: titular_vazio={br['titular_vazio']} de "
        f"ativos_com_snapshot={br['ativos_com_snapshot']} (população julgável) · "
        f"ativos={br['ativos']} · sem_snapshot={br['sem_snapshot']} não julgáveis",
        f"- contexto legado (não toca o numerador): sem_ancora_v2={br['sem_ancora_v2']} "
        f"{_ancora_identity(br)} sem_snapshot={br['sem_snapshot']} (ADR-282)",
        f"- inertes hoje (fora do numerador): quarentenados={br['quarentenados']} "
        f"soft_deleted={br['soft_deleted']}",
    ]


def _fmt_entregue_meta(meta: dict) -> list[str]:
    if not meta:
        return []
    rev = meta.get("executor_revision") or "n/d"
    return [
        "## KR-B · prova no E3 persistido",
        f"- run_id={meta['run_id']} executor_revision={rev} "
        f"cortadas={meta['cortadas']} retido_por_override={meta['retido_por_override']}",
        "- este bloco pontua KR-B; a sombra (enforce omitido) não pontua",
    ]


def _cross_group_blocks(report: LedgerReport) -> list:
    sombra = fmt_cross_group(report.cross_group, numerator_label=_SOMBRA_LABEL, title=_TITLE)
    if report.cross_group_entregue is None:
        return [sombra]
    run8 = (report.entregue.get("run_id") or report.run_id or "n/d")[:8]
    label = f"{_KR_B_LABEL} · E3 persistido run {run8}"
    title = "## Duplicação cross-grupo — entregue (E3 persistido do run)"
    return [
        sombra,
        _fmt_entregue_meta(report.entregue),
        fmt_cross_group(report.cross_group_entregue, numerator_label=label, title=title),
    ]


def _report_blocks(report: LedgerReport) -> list:
    return [
        _fmt_conservation(report.conservation),
        _fmt_e2_provenance(report.e2_provenance),
        _fmt_exec(report),
        _fmt_units("## Eixo E3 (por grupo)", report.e3_groups),
        _fmt_units(f"## Eixo E4 (por balde) [{report.e4_subject}]", report.e4_buckets),
        *_cross_group_blocks(report),
        fmt_collapse_layer(report.collapse_layer),
        _fmt_tail(report),
        _fmt_drift(report.drift),
        _fmt_blast_radius(report.blast_radius),
    ]


def format_report(report: LedgerReport) -> str:
    """Texto PII-safe do LedgerReport (2 tabelas de veredito + conservação + drift)."""
    header = [
        f"# ledger-certify — ws {report.workspace_id[:8]} run {(report.run_id or 'n/d')[:8]}",
        f"E2 semeado: {report.e2_seeded} artefatos, {report.e2_tx} tx · "
        f"colisões de investimento: {len(report.investment_collisions)}",
        "",
    ]
    body = "\n\n".join("\n".join(b) for b in _report_blocks(report))
    return "\n".join(header) + body + "\n"
