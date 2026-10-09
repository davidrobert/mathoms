#!/usr/bin/env python3
"""Rebaseline do golden mensal do parecer: valida a candidata, escreve a baseline e monta o link de PR."""

# Roda no job `baseline-branch` de `planner-golden-monthly.yml`, o único com
# `contents: write`. A candidata vem do job que executou deps de terceiros e a
# chamada LLM — entrada NÃO confiável: shape fechado, teto de tamanho, e o path
# é derivado aqui, nunca do payload. Stdlib only, roda com `python3 -I` do
# sistema: venv nenhum entra no job que escreve no repo.
#
# O PR é aberto pelo humano que despachou, pelo link do summary: o GITHUB_TOKEN
# não cria PR neste repo (`can_approve_pull_request_reviews: false`), e PR de
# bot não dispara o CI (ADR-322) — `All checks green` nunca reportaria. PAT
# ficou de fora por decisão do sre-devops (2026-10-08): credencial de Admin,
# vencida, e o CI_TRUST §Onda 2 cortou "planner-golden via PR" desta janela.

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlencode

MAX_BYTES = 8 * 1024
MAX_METRICS = 32
_YYYY_MM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_METRIC_KEY = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
# O valor vira célula de tabela no summary e no corpo do PR: sem `|`, crase,
# colchete ou tag, a amostra do LLM não reescreve a tabela nem injeta link.
_SAFE_STR = re.compile(r"^[^`|<>\[\]\x00-\x1f]{0,80}$")
_TOP_KEYS = {"generated_at", "yyyy_mm", "metrics"}


def baseline_path(base_dir: Path, yyyy_mm: str) -> Path:
    return base_dir / f"parecer_monthly_{yyyy_mm}.json"


def pr_title(yyyy_mm: str) -> str:
    return f"chore(test): bump planner monthly golden baseline ({yyyy_mm})"


def decode_candidate(b64: str, yyyy_mm: str) -> dict:
    """Payload base64 do job não confiável → dict validado; ValueError nomeia o ofensor."""
    if not _YYYY_MM.match(yyyy_mm):
        raise ValueError(f"expected yyyy_mm YYYY-MM, got {yyyy_mm!r}")
    try:
        raw = base64.b64decode(b64, validate=True)
    except ValueError as exc:  # binascii.Error e str não-ASCII
        raise ValueError(f"expected base64, got {len(b64)} chars: {exc}") from exc
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError(f"expected 1..{MAX_BYTES} bytes, got {len(raw)}")
    payload = json.loads(raw.decode("utf-8"))
    _validate_envelope(payload, yyyy_mm)
    _validate_metrics(payload["metrics"])
    return payload


def _validate_envelope(payload: object, yyyy_mm: str) -> None:
    if not isinstance(payload, dict) or set(payload) != _TOP_KEYS:
        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        raise ValueError(f"expected keys {sorted(_TOP_KEYS)}, got {got!r}")
    if payload["yyyy_mm"] != yyyy_mm:
        raise ValueError(f"expected yyyy_mm={yyyy_mm!r}, got {payload['yyyy_mm']!r}")
    generated_at = payload["generated_at"]
    if not isinstance(generated_at, str) or not _SAFE_STR.match(generated_at):
        raise ValueError(f"expected generated_at ISO str, got {generated_at!r}")


def _validate_metrics(metrics: object) -> None:
    if not isinstance(metrics, dict) or not 0 < len(metrics) <= MAX_METRICS:
        raise ValueError(f"expected 1..{MAX_METRICS} metrics as object, got {metrics!r}")
    for key, value in metrics.items():
        if not _METRIC_KEY.match(key):
            raise ValueError(f"expected snake_case metric key, got {key!r}")
        if value is None or type(value) is int:
            continue
        if type(value) is not str or not _SAFE_STR.match(value):
            raise ValueError(f"expected int|null|safe str in {key}, got {value!r}")


def latest_baseline(base_dir: Path) -> Path | None:
    """Mesma regra do teste: ordem lexical do filename = cronológica."""
    files = sorted(base_dir.glob("parecer_monthly_*.json"))
    return files[-1] if files else None


def write_baseline(payload: dict, base_dir: Path) -> Path:
    """Mesmo formato de `_write_baseline` em tests/test_parecer_golden_monthly_real.py."""
    path = baseline_path(base_dir, payload["yyyy_mm"])
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _cell(value: object) -> str:
    return "—" if value is None else f"`{value}`"


def metrics_table(prev: dict | None, new: dict) -> str:
    """Anterior × nova — o diff do PR não mostra o drift, porque cada mês é arquivo novo."""
    rows = ["| métrica | anterior | nova | mudou |", "|---|---|---|---|"]
    for key in sorted(set(new) | set(prev or {})):
        before = None if prev is None else prev.get(key)
        changed = "—" if prev is None else ("sim" if before != new.get(key) else "não")
        rows.append(f"| `{key}` | {_cell(before)} | {_cell(new.get(key))} | {changed} |")
    return "\n".join(rows)


def pr_body(table: str, prev_name: str | None, run_url: str) -> str:
    reference = f"`{prev_name}`" if prev_name else "nenhuma — este PR semeia a primeira"
    return "\n".join(
        [
            "## Sumário",
            f"- Rebaseline do golden mensal do parecer gerada pelo run {run_url}.",
            f"- Baseline de referência anterior: {reference}.",
            "",
            table,
            "",
            "## Revisão humana (sem auto-merge)",
            "Esta é uma amostra NOVA do LLM, não a que falhou no run de drift.",
            "Confira a tabela antes de mergear.",
            "Runbook: `docs/reference/runbooks/planner_golden_rebaseline.md`.",
        ]
    )


def compare_url(server_url: str, repo: str, branch: str, title: str, body: str) -> str:
    query = urlencode({"quick_pull": "1", "title": title, "body": body}, quote_via=quote)
    return f"{server_url}/{repo}/compare/main...{quote(branch, safe='/')}?{query}"


def step_summary(url: str, branch: str, body: str) -> str:
    return "\n".join(
        [
            "## Rebaseline pronta — abra o PR",
            f"Branch `{branch}`. **[Abrir o PR pré-preenchido]({url})** (sem auto-merge).",
            "",
            body,
            "",
        ]
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--yyyy-mm", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--server-url", required=True)
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--summary-out", type=Path, required=True)
    ap.add_argument("--baseline-dir", type=Path, default=Path("tests/golden_baselines"))
    return ap.parse_args(argv)


def _read_metrics(path: Path | None) -> dict | None:
    return None if path is None else json.loads(path.read_text(encoding="utf-8"))["metrics"]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = decode_candidate(os.environ.get("BASELINE_B64", ""), args.yyyy_mm)
    except ValueError as exc:
        print(f"::error::baseline candidata rejeitada: {exc}", file=sys.stderr)
        return 1
    prev_path = latest_baseline(args.baseline_dir)
    table = metrics_table(_read_metrics(prev_path), payload["metrics"])
    write_baseline(payload, args.baseline_dir)
    body = pr_body(table, prev_path.name if prev_path else None, args.run_url)
    url = compare_url(args.server_url, args.repo, args.branch, pr_title(args.yyyy_mm), body)
    args.summary_out.write_text(step_summary(url, args.branch, body), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
