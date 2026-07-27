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
from dev.ledger_conservation import (
    COBERTO_SEM_VALOR,
    CONSERVADO,
    NAO_VERIFICAVEL,
    PERDA_SILENCIOSA,
    e2_to_e3,
    e3_to_e4,
    investment_double_count,
)

_TX_BUCKETS = ("despesas", "receitas")


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

    @property
    def zero_write_ok(self) -> bool:
        return self.counts_before == self.counts_after


# ─────────────────────────── vereditos (puros) ───────────────────────────


def _first_verdict(checks: list, default: tuple) -> tuple:
    return next(((v, d) for cond, v, d in checks if cond), default)


def _ledger_verdict(fresh: dict, total: int) -> tuple[str, str] | None:
    """ADR-347 — se o artefato declara o ledger (``tx_carregadas`` + ``remocoes``),
    o fechamento (int, tol-zero) PROVA a conservação de contagem; resíduo = P0."""
    remocoes = fresh.get("remocoes")
    carregadas = fresh.get("tx_carregadas")
    if not isinstance(remocoes, dict) or carregadas is None:
        return None
    declared = sum(int(r.get("count", 0)) for r in remocoes.values() if isinstance(r, dict))
    resid = int(carregadas) - total - declared
    if resid == 0:
        return (
            CONSERVADO,
            f"ledger fecha: {carregadas} == {total} + {declared} declaradas (tol-zero)",
        )
    return (
        PERDA_SILENCIOSA,
        f"ledger não fecha: resíduo {resid} não-declarado (carregadas={carregadas})",
    )


def e3_group_verdict(fresh) -> tuple[str, str]:
    """Veredito de um grupo E3: consistência interna (count) + **ledger de contagem
    declarado** (ADR-347) quando presente. 0-tx não sobe a ``conservado``; sem ledger,
    dups>0 fica ``coberto`` (valor removido não provável no artefato)."""
    if not isinstance(fresh, dict) or "transacoes" not in fresh:
        return NAO_VERIFICAVEL, "sem payload E3 legível"
    n_tx = len(fresh.get("transacoes") or [])
    total = int(fresh.get("transacoes_total", 0))
    if n_tx != total:
        return NAO_VERIFICAVEL, f"transacoes_total={total} != len(transacoes)={n_tx}"
    if n_tx == 0:
        return COBERTO_SEM_VALOR, "0 transações — sem checksum de fechamento neste grão"
    ledger = _ledger_verdict(fresh, total)
    if ledger is not None:
        return ledger
    if int(fresh.get("transacoes_duplicadas_removidas", 0)) > 0:
        return COBERTO_SEM_VALOR, "dups>0 sem ledger; valor removido não declarado no artefato"
    return CONSERVADO, "count interno fecha; dups=0 ⇒ valor provável"


def _cat_cents_ok(txns: list, amount) -> bool:
    return sum(to_cents(t.get("valor", 0)) for t in txns) == to_cents(amount)


def _dados_cents_ok(payload: dict) -> bool:
    """Σ cents(dados[cat]) == totais_por_categoria[cat] para todo cat (mirror CV16)."""
    dados = payload.get("dados", {})
    totais = payload.get("totais_por_categoria", {})
    return all(_cat_cents_ok(dados.get(cat, []), amt) for cat, amt in totais.items())


def _tx_bucket_verdict(payload: dict) -> tuple[str, str]:
    total = to_cents(payload.get("total_geral", 0))
    parts = sum(to_cents(v) for v in payload.get("totais_por_categoria", {}).values())
    checks = [
        (total != parts, PERDA_SILENCIOSA, f"Σ categorias {parts} != total_geral {total} cents"),
        (
            not _dados_cents_ok(payload),
            PERDA_SILENCIOSA,
            "Σ tx(dados[cat]) != totais_por_categoria",
        ),
    ]
    return _first_verdict(checks, (CONSERVADO, "balde fecha (categorias + tx em cents)"))


def _investimentos_verdict(payload: dict, collisions: list) -> tuple[str, str]:
    dados = payload.get("dados", [])
    if collisions:
        return PERDA_SILENCIOSA, f"dupla-contagem ADR-271: {len(collisions)} chave(s) viva(s) 2×"
    if not dados:
        return COBERTO_SEM_VALOR, "balde vazio (0 posições)"
    return CONSERVADO, f"{len(dados)} posições; sem duplicata literal nem snapshot cross-período"


def _non_ledger_verdict(key: str, payload: dict) -> tuple[str, str]:
    items = payload.get("dados") or payload.get("apolices") or payload.get("composicao") or []
    return (
        COBERTO_SEM_VALOR,
        f"{key}: origem E2/baseline (fora do grão transacional); {len(items)} itens",
    )


def e4_bucket_verdict(key: str, payload, collisions: list) -> tuple[str, str]:
    """Um dos 5 vereditos por balde E4 (dispatch por natureza do balde)."""
    if not isinstance(payload, dict):
        return NAO_VERIFICAVEL, "balde ausente/ilegível"
    if key in _TX_BUCKETS:
        return _tx_bucket_verdict(payload)
    if key == "investimentos":
        return _investimentos_verdict(payload, collisions)
    return _non_ledger_verdict(key, payload)


# ─────────────────────────── drift + cobertura ───────────────────────────


def _e3_count(payload) -> int:
    if not isinstance(payload, dict):
        return -1
    return int(payload.get("transacoes_total", 0)) + int(
        payload.get("transacoes_duplicadas_removidas", 0)
    )


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
    """Cross-check fresco↔persistido por grupo — divergência = drift (reporta,
    não falha): código mudou o keying/dedup pós-run OU artefato de run parcial."""
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


def _classified_cents(result) -> int:
    """Σ |valor| (cents) das tx classificadas (pré-dedup, mesmo conjunto que as tx
    E3 não-puladas) — lado-saída do check de VALOR E3→E4 (F1)."""
    return sum(abs(to_cents(getattr(c, "valor", 0))) for c in result.classified)


def _conservation(e2_payloads: list, fresh_e3: dict, e4: dict, result) -> list:
    e3_list = list(fresh_e3.values())
    return [
        e2_to_e3(e2_payloads, e3_list),
        e3_to_e4(
            e3_list,
            e4.get("despesas", {}),
            e4.get("receitas", {}),
            result.cash_flow.transferencias_count,
            _classified_cents(result),
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


def _e4_verdicts(e4: dict, collisions: list) -> list:
    out = []
    for key in sorted(e4):
        verdict, detail = e4_bucket_verdict(key, e4[key], collisions)
        out.append(UnitVerdict(key, verdict, detail, _bucket_metrics(e4[key])))
    return out


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


def build_report(ws, run_id, seeds, e3_result, result, e4, fresh_e3, persisted_e3) -> LedgerReport:
    """Monta o ``LedgerReport`` a partir das peças re-derivadas (puro)."""
    e2_payloads = seeds
    collisions = investment_double_count(e4.get("investimentos", {}))
    return LedgerReport(
        workspace_id=ws,
        run_id=run_id,
        e2_seeded=len(e2_payloads),
        e2_tx=sum(len(p.get("transacoes", [])) for p in e2_payloads),
        e3_exec=_e3_exec_dict(e3_result),
        conservation=_conservation(e2_payloads, fresh_e3, e4, result),
        e3_groups=_e3_verdicts(fresh_e3),
        e4_buckets=_e4_verdicts(e4, collisions),
        investment_collisions=collisions,
        natural_key=_natural_key_coverage(result),
        drift=_drift(fresh_e3, persisted_e3),
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
    lines.append(f"- só no persistido (keying antigo não reproduzido): {len(d.persisted_only)}")
    lines += [f"  · {k}" for k in d.persisted_only[:8]]
    return lines


def _report_blocks(report: LedgerReport) -> list:
    return [
        _fmt_conservation(report.conservation),
        _fmt_exec(report),
        _fmt_units("## Eixo E3 (por grupo)", report.e3_groups),
        _fmt_units("## Eixo E4 (por balde)", report.e4_buckets),
        _fmt_tail(report),
        _fmt_drift(report.drift),
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
