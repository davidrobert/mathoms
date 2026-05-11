"""Render JSON + Markdown do GateReport para ``_scratch/``."""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from dev._dogfood_gate_a12.types import GateInvariant, GateReport, RuleResult


def _render_header(report: GateReport) -> list[str]:
    return [
        "# Dogfood Gate A12 — Relatório Técnico",
        "",
        f"**Veredito:** `{report.verdict}`",
        "",
        f"**Workspace:** `{report.workspace_id}`",
        f"**Transações geradas:** {report.total_transactions}",
        f"**Meses fechados:** {', '.join(report.closed_months)}",
        f"**Manual overrides seeded:** {report.manual_overrides_seeded}",
        "",
    ]


def _render_metrics(report: GateReport) -> list[str]:
    lines = ["## Métricas"]
    for k, v in report.metrics.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    return lines


def _render_rule_row(r: RuleResult) -> str:
    return (
        f"| `{r.keyword}` | {r.target_category} | "
        f"{r.preview_matches_total} | {r.preview_in_closed_months} | "
        f"{r.preview_with_manual_override} | {r.preview_blocked_internal_transfers} | "
        f"{','.join(r.preview_warnings) or '—'} | {r.create_status} | "
        f"{r.create_applied_count} |"
    )


def _render_rules_table(report: GateReport) -> list[str]:
    header = (
        "| Keyword | Target | Preview Total | Closed | Manual | "
        "Blocked Transfer | Warnings | Apply Status | Applied |"
    )
    lines = ["## Bateria de regras", "", header, "|---|---|---:|---:|---:|---:|---|---|---:|"]
    lines.extend(_render_rule_row(r) for r in report.rules)
    lines.append("")
    return lines


def _render_invariants(report: GateReport) -> list[str]:
    lines = ["## Invariantes", "", "| Status | Código | Descrição | Detalhe |", "|---|---|---|---|"]
    for inv in report.invariants:
        lines.append(f"| {inv.status} | `{inv.code}` | {inv.description} | {inv.detail} |")
    lines.append("")
    return lines


def _summary_line(invariants: list[GateInvariant]) -> str:
    pass_count = sum(1 for i in invariants if i.status == "PASS")
    fail_count = sum(1 for i in invariants if i.status == "FAIL")
    warn_count = sum(1 for i in invariants if i.status == "WARN")
    na_count = sum(1 for i in invariants if i.status == "N/A")
    return f"- PASS: {pass_count} · FAIL: {fail_count} · WARN: {warn_count} · N/A: {na_count}"


_VERDICT_MSG = {
    "PASS": "- Invariantes técnicas estão protegidas. Gate humano UX pode prosseguir.",
    "PARTIAL": "- Há regressões em invariantes pontuais — investigar FAILs antes do dogfood humano.",
    "FAIL": "- BLOQUEIO. Múltiplas invariantes quebradas. Dogfood humano deve aguardar fix.",
}


def _render_recommendation(report: GateReport) -> list[str]:
    return [
        "## Recomendação",
        "",
        _summary_line(report.invariants),
        _VERDICT_MSG.get(report.verdict, "- Veredito desconhecido."),
        "",
    ]


_OUT_OF_SCOPE = [
    "## Out-of-scope (gate humano cobre)",
    "",
    "- Sinais qualitativos: 'vou usar isso?', fadiga de dialog, expectativa metodológica.",
    "- Entrevista 3 perguntas (RUNBOOK §9.3).",
    "- Tempo de confirmação real do dialog (telemetria fora do scope).",
    "",
]


def render_markdown(report: GateReport) -> str:
    sections = [
        *_render_header(report),
        *_render_metrics(report),
        *_render_rules_table(report),
        *_render_invariants(report),
        *_render_recommendation(report),
        *_OUT_OF_SCOPE,
    ]
    return "\n".join(sections)


def _json_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return str(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    raise TypeError(f"not serializable: {type(o).__name__}")


def serialize_report(report: GateReport) -> dict:
    raw = asdict(report)
    return json.loads(json.dumps(raw, default=_json_default))


def write_outputs(report: GateReport, scratch_dir: Path) -> tuple[Path, Path]:
    json_path = scratch_dir / "dogfood_gate_a12_report.json"
    md_path = scratch_dir / "dogfood_gate_a12_report.md"
    json_path.write_text(
        json.dumps(serialize_report(report), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


__all__ = ["render_markdown", "serialize_report", "write_outputs"]
