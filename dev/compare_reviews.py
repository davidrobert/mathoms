#!/usr/bin/env python3
"""Snapshot PII-safe + `--compare` anti-regressão para a skill pipeline-review (ADR-343).

Duas responsabilidades puras (testáveis sem DB):

- ``build_snapshot(...)`` — reduz os insumos de um run (report_data, CV, meta do
  run, parecer) a um ``review_snapshot.json`` **PII-safe** (zero literal
  monetário; drift de valor vem do report_data cru no compare, nunca aqui).
- ``compare_reviews(...)`` — regressão de relatório em **3 pernas** (conservação,
  drift de valor via ``golden_diff``, saúde de execução), com **suppressors**
  (tier downgrade / corpus cresceu) que evitam falso-fail. Reusa engines
  (``golden_diff.diff_golden``), nunca o gate de manifesto de CI.

CLI (espelha ``dev/certify_parse_local.py``):
``python3 dev/compare_reviews.py --current <dir> --baseline <dir> [--strict] [--band 10]``
onde cada ``<dir>`` tem ``review_snapshot.json`` (+ ``report_data.json`` p/ a perna
de valor). Exit 1 em regressão HARD, 2 se baseline ausente, 0 se limpo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dev.golden_diff import diff_golden, to_cents

SCHEMA_VERSION = "1"

# Conservação numérica (tolerância zero): estende o set de pausa da produção
# (_CONSERVATION_CHECKS = {CV1,CV2,CV3,CV6} em scripts/validate_cross.py) com os
# checks simétricos CV16/CV17. Regressão nesses é HARD, nunca suprimida.
_CONSERVATION_HARD = frozenset({"CV1", "CV2", "CV3", "CV6", "CV16", "CV17"})
# Render/narrativa: falham legítimo em run incremental que reusa narrativa
# (A36.l3) → SOFT (só com --strict), fora do gate default.
_RENDER_SOFT = frozenset({"CV9", "CV10", "CV11", "CV12", "CV13", "CV14"})

# Seções do view-model E5 cuja ausência/esvaziamento é regressão.
_SECTION_KEYS = (
    "patrimonio",
    "fluxo_caixa",
    "ratios",
    "reserva_emergencia",
    "endividamento",
    "previdencia_pgbl",
    "investimentos",
    "real_estate",
    "protecao_patrimonial",
    "passive_income",
    "exposicao_cambial",
    "programa_milhas",
    "narrativas",
)
# Seções derivadas de LLM (dependem do tier premium) — regressão suprimida em
# tier downgrade (skip_llm / hard-stop ADR-173).
_TIER_DEPENDENT_SECTIONS = frozenset({"narrativas"})

# Voláteis: mudam entre runs idênticos, nunca são regressão (espelha
# _VOLATILE_LEAVES de backend/tests/test_report_view_model_snapshot.py).
_VOLATILE_LEAVES = frozenset({"data_analise", "prob_if_ate_idade_meta"})

_BRACKET_RE = re.compile(r"\[[^\]]*\]")


# ─────────────────────────────── snapshot ───────────────────────────────


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].split("[", 1)[0]


def _sum_leaf(obj: Any, leaf: str) -> int | None:
    """Soma recursiva dos valores numéricos de todas as folhas ``leaf`` (ou None)."""
    found: list[int] = []
    _collect_leaf(obj, leaf, found)
    return sum(found) if found else None


def _collect_leaf(obj: Any, leaf: str, out: list[int]) -> None:
    if isinstance(obj, dict):
        _collect_dict(obj, leaf, out)
    elif isinstance(obj, list):
        _collect_list(obj, leaf, out)


def _collect_list(items: list, leaf: str, out: list[int]) -> None:
    for item in items:
        _collect_leaf(item, leaf, out)


def _collect_dict(obj: dict, leaf: str, out: list[int]) -> None:
    for key, value in obj.items():
        _collect_leaf_kv(key, value, leaf, out)


def _collect_leaf_kv(key: str, value: Any, leaf: str, out: list[int]) -> None:
    if key == leaf and isinstance(value, (int, float)) and not isinstance(value, bool):
        out.append(int(value))
    else:
        _collect_leaf(value, leaf, out)


def _section_state(data: dict, key: str) -> str:
    if key not in data:
        return "absent"
    return "empty" if data[key] in (None, {}, [], "") else "populated"


def _sections_map(data: dict) -> dict[str, str]:
    return {k: _section_state(data, k) for k in _SECTION_KEYS}


def _parecer_snapshot(parecer: Any) -> dict[str, Any]:
    """Sinal estrutural do parecer (não persiste o texto: PII + maior artefato)."""
    if not isinstance(parecer, dict) or not parecer:
        return {"status": "ausente", "n_secoes": 0, "schema_valid": False}
    secoes = parecer.get("secoes", parecer.get("sections"))
    n = len(secoes) if isinstance(secoes, (list, dict)) else len(parecer)
    return {"status": "ok", "n_secoes": n, "schema_valid": True}


def _cv_snapshot(cv_results: list[dict]) -> list[dict]:
    """Só check_id/severity/passed — dropa ``details`` (embute R$: PII)."""
    return [
        {"check_id": c["check_id"], "severity": c["severity"], "passed": bool(c["passed"])}
        for c in cv_results
    ]


def _needs_review_map(rows: list[dict]) -> dict[str, int]:
    return {r["doc_type"]: r["n"] for r in rows if r.get("doc_type")}


def _run_health(report_data: dict, meta: dict) -> dict:
    costs, calls = meta.get("costs", []), meta.get("calls", [])
    run = meta.get("run", {})
    return {
        "status": run.get("status"),
        "failed_at_stage": run.get("failed_at_stage"),
        "tier_at_run": run.get("tier_at_run"),
        "total_documents": run.get("total_documents"),
        "transacoes_total": _sum_leaf(report_data, "transacoes_total"),
        "duration_min": run.get("minutes"),
        "llm_cost_usd_cents": sum(int(c.get("cost_usd_cents") or 0) for c in costs) or None,
        "llm_calls": len(calls),
        "tool_iterations_total": sum(int(c.get("tool_iterations") or 0) for c in costs) or None,
    }


def build_snapshot(
    *, run_id: str, report_data: dict, cv_results: list[dict], meta: dict, parecer: Any
) -> dict:
    """Snapshot PII-safe (meta = {run, needs_review, costs, calls}, telemetria do run)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "run_health": _run_health(report_data, meta),
        "needs_review": _needs_review_map(meta.get("needs_review", [])),
        "cross_validation": _cv_snapshot(cv_results),
        "sections": _sections_map(report_data),
        "parecer": _parecer_snapshot(parecer),
    }


# ─────────────────────────────── compare ────────────────────────────────


def _suppressors(base: dict, cur: dict) -> dict[str, bool]:
    bh, ch = base.get("run_health", {}), cur.get("run_health", {})
    tier_down = bh.get("tier_at_run") == "premium" and ch.get("tier_at_run") != "premium"
    llm_off = bool(bh.get("llm_calls")) and not ch.get("llm_calls")
    bd, cd = bh.get("total_documents") or 0, ch.get("total_documents") or 0
    return {
        "tier_downgrade": tier_down or llm_off,
        "corpus_grew": cd > bd,
        "corpus_shrank": cd < bd,
    }


def _status_regression(base: dict, cur: dict) -> list[str]:
    b, c = base["run_health"].get("status"), cur["run_health"].get("status")
    if b == "completed" and c != "completed":
        stage = cur["run_health"].get("failed_at_stage") or "?"
        return [f"status {b} -> {c} (falhou em {stage})"]
    return []


def _cv_index(snap: dict) -> dict[str, dict]:
    return {c["check_id"]: c for c in snap.get("cross_validation", [])}


def _cv_regression_for(cid: str, b: dict | None, c: dict | None) -> str | None:
    if b is None:
        return None
    if c is None:
        return f"conservação {cid} presente -> ausente"
    if b["passed"] and not c["passed"]:
        return f"conservação {cid} passa -> falha"
    return None


def _cv_regressions(base: dict, cur: dict) -> list[str]:
    bi, ci = _cv_index(base), _cv_index(cur)
    out = [_cv_regression_for(cid, bi.get(cid), ci.get(cid)) for cid in _CONSERVATION_HARD]
    return [m for m in out if m]


def _tx_regression(base: dict, cur: dict, sup: dict) -> list[str]:
    b, c = base["run_health"].get("transacoes_total"), cur["run_health"].get("transacoes_total")
    if b and c is not None and c < b and not sup["corpus_shrank"]:
        return [f"transacoes_total {b} -> {c} (corpus não encolheu)"]
    return []


def _section_regression_for(key: str, b: str, c: str, sup: dict) -> str | None:
    if b != "populated" or c == "populated":
        return None
    if sup["tier_downgrade"] and key in _TIER_DEPENDENT_SECTIONS:
        return None
    return f"seção {key} populated -> {c}"


def _section_regressions(base: dict, cur: dict, sup: dict) -> list[str]:
    cur_sections = cur.get("sections", {})
    out = [
        _section_regression_for(key, b, cur_sections.get(key, "absent"), sup)
        for key, b in base.get("sections", {}).items()
    ]
    return [m for m in out if m]


def _parecer_regressions(base: dict, cur: dict, sup: dict) -> list[str]:
    if sup["tier_downgrade"]:
        return []
    b, c = base.get("parecer", {}), cur.get("parecer", {})
    out = []
    if b.get("status") == "ok" and c.get("status") != "ok":
        out.append(f"parecer ok -> {c.get('status')}")
    if b.get("schema_valid") and not c.get("schema_valid"):
        out.append("parecer schema_valid True -> False")
    if (b.get("n_secoes") or 0) > (c.get("n_secoes") or 0):
        out.append(f"parecer n_secoes {b.get('n_secoes')} -> {c.get('n_secoes')}")
    return out


def _mask_path(path: str) -> str:
    """Colapsa chaves-natural (`[Nome]`) do path — evita PII no output do compare."""
    return _BRACKET_RE.sub("[]", path)


def _pct(old_c: int, new_c: int) -> float:
    return (new_c - old_c) / abs(old_c) * 100 if old_c else float("inf")


def _drift_line(d: Any, band: float) -> tuple[str | None, str | None]:
    """Retorna (desaparecimento HARD, drift partial) para um FieldDiff monetário."""
    if not d.is_monetary_value_delta() or _leaf(d.path) in _VOLATILE_LEAVES:
        return None, None
    old_c, new_c = to_cents(d.old), to_cents(d.new)
    if old_c and new_c == 0:
        return f"{_mask_path(d.path)} -> 0 (balde zerado)", None
    p = _pct(old_c, new_c)
    if abs(p) > band or (old_c and new_c and (old_c > 0) != (new_c > 0)):
        return None, f"{_mask_path(d.path)}: {p:+.1f}%"
    return None, None


def _value_drift(base_rd: dict, cur_rd: dict, band: float) -> tuple[list[str], list[str]]:
    """Retorna (desaparecimentos HARD, drifts partial). Só monetário; volátil fora."""
    gone, drift = [], []
    for d in diff_golden(base_rd, cur_rd):
        g, dr = _drift_line(d, band)
        if g:
            gone.append(g)
        if dr:
            drift.append(dr)
    return gone, drift


def _soft_changes(base: dict, cur: dict, sup: dict) -> list[str]:
    bi, ci = _cv_index(base), _cv_index(cur)
    out = [
        f"render {cid} passa -> falha"
        for cid in _RENDER_SOFT
        if _render_regressed(bi.get(cid), ci.get(cid))
    ]
    bnr, cnr = sum(base.get("needs_review", {}).values()), sum(cur.get("needs_review", {}).values())
    if cnr > bnr and not sup["corpus_grew"]:
        out.append(f"needs_review {bnr} -> {cnr}")
    return out + _cost_changes(base, cur)


def _render_regressed(b: dict | None, c: dict | None) -> bool:
    return bool(b and c and b["passed"] and not c["passed"])


def _cost_changes(base: dict, cur: dict) -> list[str]:
    bd = base["run_health"].get("duration_min") or 0
    cd = cur["run_health"].get("duration_min") or 0
    if bd and cd > bd * 1.5:
        return [f"duração {bd} -> {cd} min (+{(cd / bd - 1) * 100:.0f}%)"]
    return []


def _hard_regressions(
    base: dict, cur: dict, base_rd: dict, cur_rd: dict, sup: dict, band: float
) -> tuple[list[str], list[str]]:
    """Retorna (hard, drift). ``drift`` vira hard ou soft conforme corpus_grew."""
    hard = _status_regression(base, cur) + _cv_regressions(base, cur)
    hard += _tx_regression(base, cur, sup) + _section_regressions(base, cur, sup)
    hard += _parecer_regressions(base, cur, sup)
    gone, drift = _value_drift(base_rd, cur_rd, band)
    return hard + gone, drift


def compare_reviews(
    base: dict, cur: dict, base_rd: dict, cur_rd: dict, *, strict: bool = False, band: float = 10.0
) -> tuple[list[str], list[str], list[str]]:
    """Retorna (hard, soft, notes). ``hard`` não-vazio ⇒ exit 1."""
    sup = _suppressors(base, cur)
    notes = [k for k, v in sup.items() if v]
    hard, drift = _hard_regressions(base, cur, base_rd, cur_rd, sup, band)
    soft = _soft_changes(base, cur, sup)
    if sup["corpus_grew"]:
        soft += [f"drift de valor (informativo, corpus cresceu): {d}" for d in drift]
    else:
        hard += [f"drift de valor: {d}" for d in drift]
    if strict:
        hard, soft = hard + soft, []
    return hard, soft, notes


# ─────────────────────────────── CLI ────────────────────────────────


def _load(dir_path: Path, name: str) -> dict:
    return json.loads((dir_path / name).read_text(encoding="utf-8"))


def _compare_dirs(
    current: Path, baseline: Path, strict: bool, band: float
) -> tuple[list[str], list[str], list[str]]:
    return compare_reviews(
        _load(baseline, "review_snapshot.json"),
        _load(current, "review_snapshot.json"),
        _load(baseline, "report_data.json"),
        _load(current, "report_data.json"),
        strict=strict,
        band=band,
    )


def _print_compare(hard: list[str], soft: list[str], notes: list[str]) -> None:
    for n in notes:
        print(f"NOTE: suppressor ativo — {n}")
    for s in soft:
        print(f"CHANGED: {s}")
    for h in hard:
        print(f"FAIL: {h}")


def _run_compare(current: Path, baseline: Path, *, strict: bool, band: float) -> int:
    if not (baseline / "review_snapshot.json").exists():
        print(
            f"baseline não encontrado: {baseline}/review_snapshot.json — rode o run baseline antes"
        )
        return 2
    hard, soft, notes = _compare_dirs(current, baseline, strict, band)
    _print_compare(hard, soft, notes)
    verdict = f"{len(hard)} regressão(ões)" if hard else "sem regressões"
    print(f"\n{verdict} vs {baseline}")
    return 1 if hard else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--current", type=Path, required=True, help="dir do run atual (coletado)")
    parser.add_argument("--baseline", type=Path, required=True, help="dir do run baseline")
    parser.add_argument("--strict", action="store_true", help="regras SOFT viram HARD")
    parser.add_argument("--band", type=float, default=10.0, help="banda %% de drift de valor")
    args = parser.parse_args(argv)
    return _run_compare(args.current, args.baseline, strict=args.strict, band=args.band)


if __name__ == "__main__":
    raise SystemExit(main())
