#!/usr/bin/env python3
"""Coleta determinística de candidatos a julgamento LLM para a skill audit-vault (ADR-302).

Candidatos = gate-fail ∪ git-diff(--since) ∪ amostra rotativa dos limpos
∪ linhas de registro. A amostra dá a cada arquivo uma classe permanente
(`sha1(path) % stride`, imune a inserções no vault) e rotaciona a classe-alvo
com `--run N` (o rN do AUDITS-active): em `stride` runs, 100% do bucket é
julgado. `--full` (ou `--stride 1`) = sweep completo, modo de evento
(baseline, pré-beta) — nunca cadência recorrente. Não manda os ~956 markdown
ao LLM; só o residual. `archive/` e sprint fechada ficam fora (gates ainda
rodam via pre-commit).

O bucket `moc` tem dois grãos (emenda 2026-08-21 da ADR-302): os registros
com máquina de estado (ADR-343) entram como LINHA de seção viva — emissor
puro de fatos locais (disposição + status de lane resolvido do frontmatter,
sem rede); quem decide "é zumbi" é a camada 3. Seção com 0 linhas vivas é
histórico congelado e fica fora até de `--full`. MOCs navegacionais/fila
entram no grão-arquivo normal. Fora do universo julgado: AUDITS-active
(a camada 5 escreve nele todo run — auto-referência deixaria o hot set
permanentemente sujo) e SPRINTS-active (sobrepõe o bucket `sprint` e a
camada 2 da lane-closeout).

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
    "moc": 5,
    "adr": 20,
    "claude": 20,
    "prompt": 20,
}
DEFAULT_SAMPLE_STRIDE = 20

MOC = DOCS / "_MOC"

# Registros com máquina de estado de skills pares (ADR-343), auditados no
# grão de LINHA de seção viva — arquivo inteiro custa ~95k tokens/run e o
# residual real são as linhas.
MOC_REGISTRY_FILES = (
    "LEDGER-CERTIFY-active.md",
    "PARSE-CERTIFY-active.md",
    "PIPELINE-REVIEWS-active.md",
    "REPORT-REVIEWS-active.md",
)

RUN_SECTION_RE = re.compile(r"^r\d+\b")
VIVA_DISPO_RE = re.compile(
    r"procede-aberto|\bparcial\b|remediado|fechado com ressalva|em observação",
    re.IGNORECASE,
)
LANE_REF_RE = re.compile(r"\[\[(A\d+\.l\d+)\]\]")
PR_REF_RE = re.compile(r"#(\d{3,5})\b")

GATES = [
    "dev/validate_frontmatter.py",
    "dev/check_doc_links.py",
    "dev/check_adr_anchors.py",
    "dev/check_doc_filename_id.py",
    "dev/validate_adr_format.py",
]

# Buckets sob julgamento. archive/ e sprint fechada são resolvidos em runtime.
# `moc` (grão-arquivo) = navegacionais/fila, sem tabela de disposição; os
# registros com máquina de estado entram via `registry_row_candidates`.
BUCKET_GLOBS: dict[str, list[str]] = {
    "reference": ["docs/reference/**/*.md"],
    "adr": ["docs/adr/*.md"],
    "plan": ["docs/plan/**/*.md"],
    "claude": [
        "CLAUDE.md",
        ".claude/agents/*.md",
        ".claude/skills/*/SKILL.md",
        ".claude/skills/*/references/*.md",
    ],
    "prompt": ["config/prompts/*.yaml", "config/prompts/*.yml"],
    "root": ["README.md"],
    "moc": [
        "docs/_MOC/00-INDEX.md",
        "docs/_MOC/OWNER-GATED-active.md",
        "docs/_MOC/PLANS-active.md",
    ],
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


def split_run_sections(text: str) -> list[tuple[str, str]]:
    """(id, corpo) das seções `## rN — …` — só seção de run carrega tabela de achado."""
    parts = re.split(r"^## +(.+?)\s*$", text, flags=re.MULTILINE)
    pairs = zip(parts[1::2], parts[2::2])
    return [(t.split()[0], body) for t, body in pairs if RUN_SECTION_RE.match(t)]


def parse_rows(body: str) -> list[dict[str, str]]:
    """Linhas de tabela como dict coluna→célula (header com `Código` nomeia colunas)."""
    rows: list[dict[str, str]] = []
    cols: list[str] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].lower().startswith("código"):
            cols = [c.lower() for c in cells]
        elif cols and set(line) - {"|", "-", " ", ":"}:
            rows.append(dict(zip(cols, cells)))
    return rows


def _lane_status(lane_id: str) -> dict | None:
    """`status:`/`ship_pr:` lidos localmente do frontmatter da lane (sem rede)."""
    sprint, lane = lane_id.split(".", 1)
    lanes_dir = DOCS / "sprint" / sprint / "lanes"
    hits = sorted(lanes_dir.glob(f"{sprint}-{lane}-*.md")) or sorted(
        lanes_dir.glob(f"{sprint}-{lane}.md")
    )
    if not hits:
        return None
    head = hits[0].read_text(encoding="utf-8")[:800]
    status = re.search(r"^status:\s*(\S+)", head, re.MULTILINE)
    ship = re.search(r'^ship_pr:\s*"?#?(\d+)', head, re.MULTILINE)
    return {
        "status": status.group(1) if status else None,
        "ship_pr": int(ship.group(1)) if ship else None,
    }


def _row_candidate(path_rel: str, section: str, row: dict[str, str]) -> dict:
    """Candidato no grão de linha: fatos locais, zero veredito — zumbi é a camada 3."""
    text = " | ".join(row.values())
    dispo = row.get("disposição", "")
    return {
        "path": path_rel,
        "bucket": "moc",
        "reason": ["registry-row"],
        "anchor": f"{section}/{row['código'].split(' — ')[0].strip(' *`~')}",
        "disposicao": dispo.strip(" *"),
        "viva": bool(VIVA_DISPO_RE.search(dispo)),
        "lanes": {m: _lane_status(m) for m in dict.fromkeys(LANE_REF_RE.findall(text))},
        "prs": sorted({int(n) for n in PR_REF_RE.findall(text)}),
    }


# Seção 0-viva é histórico congelado — fora, inclusive de `--full` (ADR-302
# §Riscos: auditar snapshot congelado gera falso-drift). Linha terminal de
# seção viva ENTRA, marcada `viva: false` — atestação barata do ponteiro na
# camada 3, nunca re-adjudicação de mérito.
def rows_from_text(path_rel: str, text: str) -> list[dict]:
    """Linhas em seção de run viva (≥1 disposição viva)."""
    out: list[dict] = []
    for section, body in split_run_sections(text):
        rows = [r for r in parse_rows(body) if r.get("código")]
        if any(VIVA_DISPO_RE.search(r.get("disposição", "")) for r in rows):
            out.extend(_row_candidate(path_rel, section, r) for r in rows)
    return out


def registry_row_candidates() -> list[dict]:
    """Grão de linha dos registros com máquina de estado (ADR-343) — emissor puro."""
    out: list[dict] = []
    for name in MOC_REGISTRY_FILES:
        path = MOC / name
        if path.is_file():
            out.extend(rows_from_text(rel(path), path.read_text(encoding="utf-8")))
    return out


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
    if scope in ("moc", "all"):
        row_cands = registry_row_candidates()
        candidates.extend(row_cands)
        buckets_meta["moc-linhas"] = {
            "universe": len(row_cands),
            "sampled": len(row_cands),
            "stride": 1,
        }
    candidates.sort(key=lambda c: (c["bucket"], c["path"], c.get("anchor", "")))
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


# Fixture do self-test: a seção `Convenção` (tabela-template) e a `r0` (0
# linhas vivas) têm de ficar FORA; `r1` entra inteira, com a terminal marcada.
_SELF_TEST_REGISTRY = """## Convenção
| Código | Disposição | Trilha |
|---|---|---|
| RV01 — <template> | procede-aberto | <lane> |

## r1 — run vivo
| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV1-01 — defeito A | correção | Alto | P1 | procede | procede-aberto | [[A40.l7]] · #1375 |
| RV1-02 — defeito B | clareza | Médio | P2 | procede | procede-fechado | #1234 |

## r0 — run congelado
| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
| RV0-01 — defeito C | correção | Alto | P1 | procede | procede-fechado | #1000 |
"""


def _self_test_rows() -> str | None:
    """Prova o parser de linha sobre a fixture (a vault viva muda toda sprint)."""
    got = rows_from_text("fixture.md", _SELF_TEST_REGISTRY)
    anchors = [(c["anchor"], c["viva"]) for c in got]
    if anchors != [("r1/RV1-01", True), ("r1/RV1-02", False)]:
        return f"esperado r1 vivo+terminal e r0/Convenção fora; veio {anchors}"
    if list(got[0]["lanes"]) != ["A40.l7"] or got[0]["prs"] != [1375]:
        return f"refs da linha não extraídas: {got[0]['lanes']} {got[0]['prs']}"
    return None


def self_test(scope: str) -> int:
    """Prova determinismo (mesmo --run → mesmo conjunto) + cobertura 100% em stride runs."""
    a = collect(scope, since=None, run=1)["candidates"]
    b = collect(scope, since=None, run=1)["candidates"]
    if a != b:
        print("self-test FALHOU — coleta não-determinística", file=sys.stderr)
        return 1
    if (err := _self_test_rows()) is not None:
        print(f"self-test FALHOU — grão de linha do bucket moc: {err}", file=sys.stderr)
        return 1
    if registry_row_candidates() != registry_row_candidates():
        print("self-test FALHOU — linhas de registro não-determinísticas", file=sys.stderr)
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
        help="atalho p/ --stride 1: sweep 100%% (modo de evento, não recorrente)",
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
