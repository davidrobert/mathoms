#!/usr/bin/env python3
"""Coleta determinística de candidatos a julgamento LLM para a skill audit-vault (ADR-302).

Candidatos = gate-fail ∪ git-diff(--since) ∪ amostra estratificada dos limpos.
Não manda os ~956 markdown ao LLM; só o residual. `archive/` e sprint fechada
ficam fora (gates ainda rodam via pre-commit; aqui é a lista de julgamento).

Uso:
  python3 collect_candidates.py --scope all
  python3 collect_candidates.py --scope reference --since origin/main
  python3 collect_candidates.py --self-test        # roda 2× e prova determinismo
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DOCS = REPO_ROOT / "docs"

SAMPLE_STRIDE = 20  # ~5% determinístico (todo N-ésimo arquivo ordenado)

GATES = [
    "dev/validate_frontmatter.py",
    "dev/check_doc_links.py",
    "dev/check_adr_anchors.py",
    "dev/check_doc_filename_id.py",
    "dev/validate_adr_format.py",
]

# Buckets sob julgamento. archive/ e sprint fechada são resolvidos em runtime.
BUCKET_GLOBS: dict[str, list[str]] = {
    "reference": ["docs/reference/**/*.md"],
    "adr": ["docs/adr/*.md"],
    "plan": ["docs/plan/**/*.md"],
    "claude": ["CLAUDE.md", ".claude/agents/*.md"],
    "prompt": ["config/prompts/*.yaml", "config/prompts/*.yml"],
    "root": ["README.md"],
}

PATH_IN_OUTPUT_RE = re.compile(r"(?:docs|config|\.claude)/[\w./-]+\.(?:md|yaml|yml)")


def current_sprint_dir() -> Path | None:
    """Dir da sprint com sprint_status: current (única auditável em docs/sprint/)."""
    for readme in sorted((DOCS / "sprint").glob("*/_README.md")):
        head = readme.read_text(encoding="utf-8")[:600]
        if re.search(r"^sprint_status:\s*current\s*$", head, re.MULTILINE):
            return readme.parent
    return None


def bucket_files(scope: str) -> dict[str, list[Path]]:
    """Resolve globs → arquivos por bucket, excluindo archive/ e sprint fechada."""
    buckets = dict(BUCKET_GLOBS)
    sprint = current_sprint_dir()
    if sprint is not None:
        buckets["sprint"] = [f"docs/sprint/{sprint.name}/**/*.md"]
    selected = buckets if scope == "all" else {scope: buckets.get(scope, [])}
    out: dict[str, list[Path]] = {}
    for name, globs in selected.items():
        files = sorted({p for g in globs for p in REPO_ROOT.glob(g) if p.is_file()})
        out[name] = [p for p in files if "archive/" not in p.as_posix()]
    return out


def gate_flagged() -> set[str]:
    """Roda os gates e extrai paths sinalizados (best-effort sobre a saída)."""
    flagged: set[str] = set()
    for gate in GATES:
        proc = subprocess.run(
            [sys.executable, gate],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            blob = proc.stdout + proc.stderr
            flagged.update(m.group(0) for m in PATH_IN_OUTPUT_RE.finditer(blob))
    return flagged


def changed_since(ref: str | None) -> set[str]:
    """Paths de doc alterados desde `ref` (git diff --name-only)."""
    if not ref:
        return set()
    proc = subprocess.run(
        ["git", "diff", "--name-only", ref, "--", "docs", "config", "CLAUDE.md", ".claude/agents"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def stratified_sample(files: list[Path], already: set[str]) -> list[Path]:
    """Todo N-ésimo arquivo limpo (determinístico), pulando os já candidatos."""
    clean = [p for p in files if rel(p) not in already]
    return clean[::SAMPLE_STRIDE]


def rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def collect(scope: str, since: str | None) -> dict:
    flagged = gate_flagged()
    changed = changed_since(since)
    hot = flagged | changed
    candidates: list[dict] = []
    for name, files in bucket_files(scope).items():
        for p in files:
            r = rel(p)
            reasons = [k for k, s in (("gate-fail", flagged), ("changed", changed)) if r in s]
            if reasons:
                candidates.append({"path": r, "bucket": name, "reason": reasons})
        for p in stratified_sample(files, hot):
            candidates.append({"path": rel(p), "bucket": name, "reason": ["sample"]})
    candidates.sort(key=lambda c: (c["bucket"], c["path"]))
    return {
        "scope": scope,
        "since": since,
        "gate_flagged_count": len(flagged),
        "changed_count": len(changed),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def self_test(scope: str) -> int:
    """Prova determinismo: 2 coletas idênticas sem mudança no vault → OK."""
    a = collect(scope, since=None)["candidates"]
    b = collect(scope, since=None)["candidates"]
    if a == b:
        print(f"self-test OK — {len(a)} candidatos estáveis em 2 runs (scope={scope})")
        return 0
    print("self-test FALHOU — coleta não-determinística", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", default="all", choices=[*BUCKET_GLOBS, "sprint", "all"])
    ap.add_argument("--since", default=None, help="git ref p/ diff (ex.: origin/main)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default=None, help="grava JSON no path (default: stdout)")
    args = ap.parse_args()
    if args.self_test:
        return self_test(args.scope)
    result = collect(args.scope, args.since)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
