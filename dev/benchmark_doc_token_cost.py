#!/usr/bin/env python3
"""Mede custo em tokens de queries-benchmark sobre docs/. Gate de regressão para ADR-182."""
# Aproximação: tokens ≈ ceil(chars/4) (OpenAI/Anthropic, sem tiktoken). Drift ±15%
# absorvido pelo threshold de 5%. Modos: --init|--update|--check|--print.

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
BENCHMARK_FILE = ROOT / "tests" / "benchmarks" / "doc_token_cost.json"
REGRESSION_THRESHOLD_PCT = 5.0


@dataclass
class QueryResult:
    tokens: int
    chars: int
    files_read: list[str]


def chars_to_tokens(chars: int) -> int:
    """Aproxima 1 token ≈ 4 chars (heurística OpenAI/Anthropic, sem tiktoken)."""
    return math.ceil(chars / 4)


def _read_text(rel_path: str) -> str:
    p = DOCS / rel_path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def measure_q1() -> QueryResult:
    """Q1: adicionar lane no BACKLOG → lê BACKLOG.md inteiro."""
    text = _read_text("BACKLOG.md")
    return QueryResult(chars_to_tokens(len(text)), len(text), ["docs/BACKLOG.md"])


def measure_q2() -> QueryResult:
    """Q2: atualizar status de lane → lê BACKLOG inteiro (achar seção + editar)."""
    return measure_q1()


def measure_q3() -> QueryResult:
    """Q3: adicionar entrada CHANGELOG → lê CHANGELOG inteiro."""
    text = _read_text("CHANGELOG.md")
    return QueryResult(chars_to_tokens(len(text)), len(text), ["docs/CHANGELOG.md"])


def measure_q4() -> QueryResult:
    """Q4: atualizar entrada CHANGELOG → lê CHANGELOG inteiro (achar entrada)."""
    return measure_q3()


def measure_q5() -> QueryResult:
    """Q5: descobrir lanes prontas → BACKLOG completo + últimas 100 linhas CHANGELOG."""
    backlog = _read_text("BACKLOG.md")
    tail = "\n".join(_read_text("CHANGELOG.md").splitlines()[-100:])
    chars = len(backlog) + len(tail)
    return QueryResult(
        chars_to_tokens(chars),
        chars,
        ["docs/BACKLOG.md", "docs/CHANGELOG.md (last 100 lines)"],
    )


def measure_q6() -> QueryResult:
    """Q6: planos não finalizados → legacy *PLAN.md ou _MOC/PLANS-active.md pós-F3."""
    plans_legacy = sorted(DOCS.glob("*PLAN.md"))
    if plans_legacy:
        chars = sum(len(p.read_text(encoding="utf-8")) for p in plans_legacy)
        files = [str(p.relative_to(ROOT)) for p in plans_legacy]
    else:
        moc = DOCS / "_MOC" / "PLANS-active.md"
        chars = len(moc.read_text(encoding="utf-8")) if moc.exists() else 0
        files = ["docs/_MOC/PLANS-active.md"] if chars else []
    return QueryResult(chars_to_tokens(chars), chars, files)


def _measure_context_pack(pack_name: str) -> QueryResult:
    """Mede orientação por área: CONTEXT_INDEX + 1 pack específico."""
    files = ["_MOC/_generated/CONTEXT_INDEX.md", f"_MOC/_generated/{pack_name}.md"]
    chars = sum(len(_read_text(path)) for path in files)
    return QueryResult(chars_to_tokens(chars), chars, [f"docs/{path}" for path in files])


def measure_q7() -> QueryResult:
    """Q7: orientar investigação backend/API/pipeline via context pack."""
    return _measure_context_pack("CONTEXT_BACKEND")


def measure_q8() -> QueryResult:
    """Q8: orientar investigação frontend/relatório via context pack."""
    return _measure_context_pack("CONTEXT_FRONTEND")


def measure_q9() -> QueryResult:
    """Q9: orientar investigação produto/domínio via context pack."""
    return _measure_context_pack("CONTEXT_PRODUCT")


def measure_q10() -> QueryResult:
    """Q10: orientar edição de documentação/vault via context pack."""
    return _measure_context_pack("CONTEXT_DOCS")


MEASURERS: dict[str, Callable[[], QueryResult]] = {
    "Q1": measure_q1,
    "Q2": measure_q2,
    "Q3": measure_q3,
    "Q4": measure_q4,
    "Q5": measure_q5,
    "Q6": measure_q6,
    "Q7": measure_q7,
    "Q8": measure_q8,
    "Q9": measure_q9,
    "Q10": measure_q10,
}

QUERY_DESCRIPTIONS = {
    "Q1": {
        "name": "Adicionar lane no BACKLOG",
        "files_read": ["docs/BACKLOG.md"],
        "operation": "leitura completa para inserir 1 lane",
    },
    "Q2": {
        "name": "Atualizar status de lane",
        "files_read": ["docs/BACKLOG.md"],
        "operation": "leitura completa para achar seção e editar",
    },
    "Q3": {
        "name": "Adicionar entrada no CHANGELOG",
        "files_read": ["docs/CHANGELOG.md"],
        "operation": "leitura completa para inserir bullet do dia",
    },
    "Q4": {
        "name": "Atualizar entrada do CHANGELOG",
        "files_read": ["docs/CHANGELOG.md"],
        "operation": "leitura completa para achar entrada e editar",
    },
    "Q5": {
        "name": "Descobrir lanes prontas para pickup",
        "files_read": ["docs/BACKLOG.md", "docs/CHANGELOG.md (last 100 lines)"],
        "operation": "cross-check estado entre BACKLOG e CHANGELOG recente",
    },
    "Q6": {
        "name": "Listar planos não finalizados",
        "files_read": ["docs/*PLAN.md"],
        "operation": "leitura de todos os planos para descobrir status",
    },
    "Q7": {
        "name": "Orientar investigação backend/API/pipeline",
        "files_read": [
            "docs/_MOC/_generated/CONTEXT_INDEX.md",
            "docs/_MOC/_generated/CONTEXT_BACKEND.md",
        ],
        "operation": "escolher pack e ler contexto mínimo antes de buscar por bucket",
    },
    "Q8": {
        "name": "Orientar investigação frontend/relatório",
        "files_read": [
            "docs/_MOC/_generated/CONTEXT_INDEX.md",
            "docs/_MOC/_generated/CONTEXT_FRONTEND.md",
        ],
        "operation": "escolher pack e ler contexto mínimo antes de buscar por bucket",
    },
    "Q9": {
        "name": "Orientar investigação produto/domínio",
        "files_read": [
            "docs/_MOC/_generated/CONTEXT_INDEX.md",
            "docs/_MOC/_generated/CONTEXT_PRODUCT.md",
        ],
        "operation": "escolher pack e ler contexto mínimo antes de buscar por bucket",
    },
    "Q10": {
        "name": "Orientar edição de documentação/vault",
        "files_read": [
            "docs/_MOC/_generated/CONTEXT_INDEX.md",
            "docs/_MOC/_generated/CONTEXT_DOCS.md",
        ],
        "operation": "escolher pack e ler contexto mínimo antes de buscar por bucket",
    },
}

TARGETS = {
    "Q1": {
        "tokens": 3000,
        "reduction_pct": 94,
        "rationale": "lê só sprint/<X>/_README.md + cria nova lane atômica",
    },
    "Q2": {"tokens": 1000, "reduction_pct": 99, "rationale": "lê só sprint/<X>/lanes/<id>.md"},
    "Q3": {"tokens": 1000, "reduction_pct": 99, "rationale": "cria changelog/<id>.md atômico"},
    "Q4": {"tokens": 500, "reduction_pct": 99.6, "rationale": "edita entrada atômica"},
    "Q5": {
        "tokens": 1000,
        "reduction_pct": 98,
        "rationale": "lê _MOC/_generated/SPRINT_CURRENT.md filtrado",
    },
    "Q6": {
        "tokens": 1000,
        "reduction_pct": 80,
        "rationale": "lê _MOC/PLANS-active.md (status sem expandir)",
    },
    "Q7": {
        "tokens": 1000,
        "rationale": "lê CONTEXT_INDEX + CONTEXT_BACKEND antes de abrir fontes longas",
    },
    "Q8": {
        "tokens": 1000,
        "rationale": "lê CONTEXT_INDEX + CONTEXT_FRONTEND antes de abrir fontes longas",
    },
    "Q9": {
        "tokens": 1000,
        "rationale": "lê CONTEXT_INDEX + CONTEXT_PRODUCT antes de abrir fontes longas",
    },
    "Q10": {
        "tokens": 1000,
        "rationale": "lê CONTEXT_INDEX + CONTEXT_DOCS antes de abrir fontes longas",
    },
}


def measure_all() -> dict[str, QueryResult]:
    return {qid: fn() for qid, fn in MEASURERS.items()}


def load_benchmark() -> dict | None:
    if not BENCHMARK_FILE.exists():
        return None
    return json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))


def write_benchmark(data: dict) -> None:
    BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    BENCHMARK_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _baseline_block(results: dict[str, QueryResult]) -> dict:
    return {
        qid: {"tokens": r.tokens, "chars": r.chars, "approximation": "ceil(chars/4)"}
        for qid, r in results.items()
    }


def _latest_block(results: dict[str, QueryResult], date_iso: str, phase: str) -> dict:
    return {
        qid: {"tokens": r.tokens, "measured_at": date_iso, "phase": phase}
        for qid, r in results.items()
    }


def init_benchmark(results: dict[str, QueryResult], date_iso: str) -> dict:
    """Estrutura inicial: queries + baseline_<data> + target + latest=baseline."""
    return {
        "$schema": "doc-token-cost-benchmark/v1",
        "description": "Custo em tokens de queries-benchmark sobre docs/ (ADR-182). tokens = ceil(chars/4).",
        "queries": QUERY_DESCRIPTIONS,
        f"baseline_{date_iso.replace('-', '_')}": _baseline_block(results),
        "target": TARGETS,
        "latest": _latest_block(results, date_iso, "F1"),
    }


def update_latest(
    results: dict[str, QueryResult], existing: dict, date_iso: str, phase: str
) -> dict:
    """Atualiza só latest, preservando baseline + target."""
    out = dict(existing)
    out["latest"] = _latest_block(results, date_iso, phase)
    return out


def check_regression(results: dict[str, QueryResult], existing: dict) -> list[str]:
    """Retorna lista de queries com regressão > REGRESSION_THRESHOLD_PCT vs latest."""
    latest = existing.get("latest", {})
    offenders = []
    for qid, r in results.items():
        prev = latest.get(qid, {}).get("tokens", 0)
        if prev == 0:
            continue
        diff_pct = (r.tokens - prev) / prev * 100
        if diff_pct > REGRESSION_THRESHOLD_PCT:
            offenders.append(f"  {qid}: {prev} → {r.tokens} (+{diff_pct:.1f}%)")
    return offenders


def check_targets(results: dict[str, QueryResult]) -> list[str]:
    """Retorna queries cujo custo atual passou do budget alvo."""
    offenders = []
    for qid, r in results.items():
        target = TARGETS.get(qid, {}).get("tokens")
        if isinstance(target, int) and r.tokens > target:
            offenders.append(f"  {qid}: {r.tokens} > target {target} (+{r.tokens - target})")
    return offenders


def find_baseline(existing: dict) -> dict[str, dict] | None:
    for k, v in existing.items():
        if k.startswith("baseline_"):
            return v
    return None


def print_table(results: dict[str, QueryResult], existing: dict | None) -> None:
    print(f"{'Query':<6}{'Files':<46}{'Tokens hoje':>12}  {'Target':>8}  {'Redução':>9}")
    print("-" * 84)
    for qid, r in results.items():
        files_str = ", ".join(r.files_read)[:43]
        target = TARGETS.get(qid, {}).get("tokens", "—")
        reduction = TARGETS.get(qid, {}).get("reduction_pct", "—")
        red_str = f"{reduction}%" if isinstance(reduction, (int, float)) else str(reduction)
        print(f"{qid:<6}{files_str:<46}{r.tokens:>12}  {target:>8}  {red_str:>9}")


def _today_iso() -> str:
    from datetime import date

    return date.today().isoformat()


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", action="store_true", help="cria baseline (1x na F1)")
    g.add_argument("--update", action="store_true", help="atualiza latest")
    g.add_argument("--check", action="store_true", help="falha se regressão >5%%")
    g.add_argument(
        "--print", dest="print_table", action="store_true", help="mostra current sem escrever"
    )
    ap.add_argument("--phase", default="F1", help="rótulo de fase para latest")
    return ap.parse_args()


def _handle_init(results: dict[str, QueryResult], existing: dict | None) -> int:
    if existing is not None:
        print(f"erro: {BENCHMARK_FILE} já existe. Use --update.", file=sys.stderr)
        return 1
    data = init_benchmark(results, _today_iso())
    write_benchmark(data)
    print(f"baseline criado em {BENCHMARK_FILE.relative_to(ROOT)}.")
    print_table(results, data)
    return 0


def _handle_update(results: dict[str, QueryResult], existing: dict | None, phase: str) -> int:
    if existing is None:
        print(f"erro: {BENCHMARK_FILE} não existe. Rode --init primeiro.", file=sys.stderr)
        return 1
    data = update_latest(results, existing, _today_iso(), phase)
    write_benchmark(data)
    print(f"latest atualizado (fase: {phase}).")
    return 0


def _print_targets() -> None:
    print("\nMeta de redução por query (target):", file=sys.stderr)
    for qid, t in TARGETS.items():
        reduction = t.get("reduction_pct")
        suffix = f" (-{reduction}%)" if reduction is not None else ""
        print(f"  {qid}: alvo {t['tokens']} tokens{suffix}", file=sys.stderr)


def _print_offenders(title: str, offenders: list[str]) -> None:
    if not offenders:
        return
    print(title, file=sys.stderr)
    for line in offenders:
        print(line, file=sys.stderr)


def _handle_check(results: dict[str, QueryResult], existing: dict | None) -> int:
    if existing is None:
        print(f"erro: {BENCHMARK_FILE} não existe. Rode --init primeiro.", file=sys.stderr)
        return 1
    regression_offenders = check_regression(results, existing)
    target_offenders = check_targets(results)
    if not regression_offenders and not target_offenders:
        print("ok: nenhuma regressão detectada (>5%).")
        return 0
    _print_offenders("REGRESSÃO detectada (>5% vs latest):", regression_offenders)
    _print_offenders("BUDGET de tokens excedido:", target_offenders)
    _print_targets()
    return 1


def main() -> int:
    args = _parse_args()
    results = measure_all()
    existing = load_benchmark()
    if args.print_table:
        print_table(results, existing)
        return 0
    if args.init:
        return _handle_init(results, existing)
    if args.update:
        return _handle_update(results, existing, args.phase)
    if args.check:
        return _handle_check(results, existing)
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
