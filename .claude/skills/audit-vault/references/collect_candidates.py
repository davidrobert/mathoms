#!/usr/bin/env python3
"""Coleta determinística de candidatos a julgamento LLM para a skill audit-vault (ADR-302).

Candidatos = gate-fail ∪ git-diff(--since) ∪ amostra rotativa dos limpos.
A amostra dá a cada arquivo uma classe permanente (`sha1(path) % stride`,
imune a inserções no vault) e rotaciona a classe-alvo com `--run N` (o rN do
AUDITS-active): em `stride` runs, 100% do bucket é julgado. `--full` (ou
`--stride 1`) = sweep completo, modo de evento (baseline, pré-beta) — nunca
cadência recorrente. Não manda os ~956 markdown ao LLM; só o residual.
`archive/` e sprint fechada ficam fora (gates ainda rodam via pre-commit).

Uso:
  python3 collect_candidates.py --scope all --run 6
  python3 collect_candidates.py --scope reference --since origin/main --run 6
  python3 collect_candidates.py --scope reference --full   # sweep 100% do bucket
  python3 collect_candidates.py --self-test   # determinismo + cobertura em stride runs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DOCS = REPO_ROOT / "docs"

# Stride por bucket = nº de runs para varrer 100% dele. Denso onde o sentido
# muda toda sprint (risco fiduciário: agentes decidem lendo reference/plan);
# esparso no long tail estável (ADR Decidido antiga rota devagar).
SAMPLE_STRIDE_BY_BUCKET = {
    "reference": 5,
    "plan": 5,
    "sprint": 5,
    "root": 5,
    "adr": 20,
    "claude": 20,
    "prompt": 20,
}
DEFAULT_SAMPLE_STRIDE = 20

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


def bucket_stride(name: str, override: int | None) -> int:
    """Stride efetivo do bucket (override global de --stride/--full vence)."""
    return override if override else SAMPLE_STRIDE_BY_BUCKET.get(name, DEFAULT_SAMPLE_STRIDE)


def path_class(path_rel: str, stride: int) -> int:
    """Classe permanente do arquivo — estável sob inserção/remoção no vault."""
    return int(hashlib.sha1(path_rel.encode("utf-8")).hexdigest(), 16) % stride


def stratified_sample(files: list[Path], already: set[str], stride: int, run: int) -> list[Path]:
    """Arquivos limpos cuja classe casa com o run (rotação cobre 100% em stride runs)."""
    clean = [p for p in files if rel(p) not in already]
    if stride <= 1:
        return clean
    return [p for p in clean if path_class(rel(p), stride) == run % stride]


def hot_candidates(
    name: str, files: list[Path], flagged: set[str], changed: set[str]
) -> list[dict]:
    """Candidatos gate-fail/changed do bucket (sempre entram, fora da rotação)."""
    out: list[dict] = []
    for p in files:
        r = rel(p)
        reasons = [k for k, s in (("gate-fail", flagged), ("changed", changed)) if r in s]
        if reasons:
            out.append({"path": r, "bucket": name, "reason": reasons})
    return out


def rel(p: Path) -> str:
    return p.relative_to(REPO_ROOT).as_posix()


def collect(
    scope: str, since: str | None, run: int = 0, stride_override: int | None = None
) -> dict:
    flagged = gate_flagged()
    changed = changed_since(since)
    hot = flagged | changed
    candidates: list[dict] = []
    buckets_meta: dict[str, dict] = {}
    for name, files in bucket_files(scope).items():
        stride = bucket_stride(name, stride_override)
        candidates.extend(hot_candidates(name, files, flagged, changed))
        sampled = stratified_sample(files, hot, stride, run)
        candidates.extend({"path": rel(p), "bucket": name, "reason": ["sample"]} for p in sampled)
        buckets_meta[name] = {"universe": len(files), "sampled": len(sampled), "stride": stride}
    candidates.sort(key=lambda c: (c["bucket"], c["path"]))
    return {
        "scope": scope,
        "since": since,
        "run": run,
        "gate_flagged_count": len(flagged),
        "changed_count": len(changed),
        "candidate_count": len(candidates),
        "buckets": buckets_meta,
        "candidates": candidates,
    }


def self_test(scope: str) -> int:
    """Prova determinismo (mesmo --run → mesmo conjunto) + cobertura 100% em stride runs."""
    a = collect(scope, since=None, run=1)["candidates"]
    b = collect(scope, since=None, run=1)["candidates"]
    if a != b:
        print("self-test FALHOU — coleta não-determinística", file=sys.stderr)
        return 1
    for name, files in bucket_files(scope).items():
        stride = bucket_stride(name, None)
        seen = {rel(p) for r in range(stride) for p in stratified_sample(files, set(), stride, r)}
        missing = {rel(p) for p in files} - seen
        if missing:
            print(
                f"self-test FALHOU — rotação não cobre {name}: {sorted(missing)[:3]}",
                file=sys.stderr,
            )
            return 1
    print(
        f"self-test OK — {len(a)} candidatos estáveis (run=1) + rotação cobre 100% por bucket (scope={scope})"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", default="all", choices=[*BUCKET_GLOBS, "sprint", "all"])
    ap.add_argument("--since", default=None, help="git ref p/ diff (ex.: origin/main)")
    ap.add_argument(
        "--run",
        type=int,
        default=0,
        help="nº do run (rN do AUDITS-active) — rotaciona a classe amostrada",
    )
    ap.add_argument(
        "--stride",
        type=int,
        default=None,
        help="override global do stride por bucket (1 = universo inteiro)",
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="atalho p/ --stride 1: sweep 100% (modo de evento, não recorrente)",
    )
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default=None, help="grava JSON no path (default: stdout)")
    args = ap.parse_args()
    if args.self_test:
        return self_test(args.scope)
    stride_override = 1 if args.full else args.stride
    result = collect(args.scope, args.since, run=args.run, stride_override=stride_override)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
