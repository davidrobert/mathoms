#!/usr/bin/env python3
"""Checks determinísticos de fechamento de lane para a skill lane-closeout (ADR-302).

Cobre a metade ESTRUTURAL da pergunta "a doc está atualizada?" — contador,
`ship_pr`, deferimento órfão, PR invisível no sprint, rota para lane morta,
`blocked` cuja dependência já shipou. NÃO cobre corretude semântica (número
citado que virou falso, critério de aceite invertido): isso é a camada 3 da
skill, e nenhum script pega.

Escopo é sempre 1+ lane — não a vault inteira. As ~159 lanes `shipped` legadas
sem `ship_pr` são dívida histórica: fora do escopo pedido, não aparecem.

NÃO é gate de pre-commit. É insumo advisory de um procedimento de julgamento;
exit≠0 sinaliza "tem o que revisar", não "commit proibido".

Uso:
  python3 check_closure.py --lane A40.l26
  python3 check_closure.py --pr 1339 --json
  python3 check_closure.py --recent 5
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SPRINT = REPO_ROOT / "docs" / "sprint"
MOC = REPO_ROOT / "docs" / "_MOC"

CLOSED_LANE = {"shipped", "cancelled"}
OPEN_LANE = {"planned", "open", "in_progress", "blocked"}

# Heading que hospeda trabalho que a lane decidiu NÃO fazer. `§Deferimento
# datado com dono` é a forma canônica (precedente ADR-356); as variantes
# abaixo foram medidas na vault viva, não presumidas.
DEFER_HEADING_RE = re.compile(
    r"^#{2,4}\s*.*(deferi|fora de escopo|out-of-scope|pendênc|pendenc"
    r"|em aberto|o que fica|fica para|não entrou|nao entrou|next owner|follow-?up)",
    re.I,
)
# `## Dependências e follow-up` planeja a lane; não defere trabalho. Sem esta
# ressalva o check acusa toda lane da A21 (medido: 9 de 9). `## Por que existe
# uma lane e não só o §Deferimentos da ADR` argumenta SOBRE o deferimento — é
# meta, não conteúdo deferido (medido na A40.l27).
PLANNING_HEADING_RE = re.compile(
    r"(depend|pickup|dia 1|cronograma|sequência|sequencia|^#+\s*por qu[eê])", re.I
)
# Linha que roteia trabalho futuro a alguém. Sem isso, o deferimento é órfão.
ROUTE_WORD_RE = re.compile(
    r"(candidat|dono\b|owner|próxim|proxim|assumir|herda|quem pega|vem depois|rotead)",
    re.I,
)
# `Carga herdada da [[X]]` é a lane VIVA declarando de onde recebeu — sentido
# inverso do roteamento, e o desfecho correto (#1340). Sem isso o check acusa
# justamente quem arrumou o órfão.
INBOUND_RE = re.compile(
    r"(herdad|vind|recebid|absorvid|transferid|migrad|movid)\w*\s+d[aeo]s?\s+\[\[", re.I
)
# Texto riscado é declaração aposentada — a convenção de emenda datada da casa
# preserva a frase antiga e a anula. Rota morta não é rota.
STRIKETHROUGH_RE = re.compile(r"~~.+?~~", re.S)
# A palavra de rota tem de GOVERNAR o wikilink, não só coabitar a linha. Medido
# na A40: sem esta janela, `candidato colapsável` (termo técnico), `pela [[X]]`
# (proveniência) e `Precedente exato: [[X]]` acusavam — 64% de falso-positivo.
# 40 chars separa `Dono: [[X]]` (rota) de `Roteado em duas lanes …: [[X]]` (relato).
ROUTE_WINDOW = 40
# `Dono: [[X]]` ATRIBUI; `§Decisão do dono da [[X]]` CITA uma decisão como
# precedente. Medido em 2026-08-17 no closeout da A40.l64: no instante em que a
# A40.l5 virou `shipped`, esta forma acendeu 3 de 3 CLOSE-BLOCK-05 — 100% de
# falso-positivo num código de severidade ALTA, contra o teto de 20% do §Critério
# de aceite da skill. A janela sozinha não separa: a frase cabe nos 40 chars.
DECISAO_DO_DONO_RE = re.compile(r"decis(ão|ao|ões|oes)\s+d[oa]s?\s+dono", re.I)
# Parágrafo que JÁ declara o fechamento não está enganando ninguém — o doc que
# diz "Dono do arquivo é a [[X]] (`shipped`) … fora da sprint por falta de dono
# vivo" é exatamente a forma honesta que este check quer produzir.
SELF_CLOSED_RE = re.compile(
    r"(sem dono|falta de dono|`shipped`|shipou|não absorveu|nao absorveu|recusou)", re.I
)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
LANE_COUNT_RE = re.compile(r"^(#{2,3}\s*Lanes)\s*\((\d+)\)", re.M)


@dataclass
class Finding:
    code: str
    severity: str
    lane: str
    doc: str
    summary: str
    evidence: str


@dataclass
class Lane:
    id: str
    path: Path
    fm: dict[str, Any]
    text: str

    @property
    def status(self) -> str:
        return str(self.fm.get("status", "?"))

    @property
    def sprint(self) -> str:
        return str(self.fm.get("sprint", self.path.parents[1].name))

    @property
    def closed(self) -> bool:
        return self.status in CLOSED_LANE


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        data = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def index_lanes() -> dict[str, Lane]:
    """Todas as lanes da vault, por id do frontmatter."""
    lanes: dict[str, Lane] = {}
    for path in sorted(SPRINT.glob("*/lanes/*.md")):
        fm = _frontmatter(path)
        if fm.get("type") != "lane" or not isinstance(fm.get("id"), str):
            continue
        lanes[fm["id"]] = Lane(fm["id"], path, fm, path.read_text(encoding="utf-8"))
    return lanes


def _git(args: list[str]) -> str:
    done = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""


def _lane_ids_from_paths(paths: list[str], lanes: dict[str, Lane]) -> list[str]:
    by_path = {_rel(lane.path): lane.id for lane in lanes.values()}
    return sorted({by_path[p] for p in paths if p in by_path})


def _merge_sha(pr: int) -> str:
    """SHA do squash-merge do PR — casando o ASSUNTO, não o corpo.

    `--grep` varre a mensagem inteira, então um PR que cita `#1265` no corpo
    sequestrava a resolução (medido: `--pr 1265` devolvia o #1274).
    """
    needle = f"(#{pr})"
    for row in _git(["log", "--format=%H%x09%s", "--max-count=4000", "origin/main"]).splitlines():
        sha, _, subject = row.partition("\t")
        if subject.endswith(needle):
            return sha
    return ""


def resolve_from_pr(pr: int, lanes: dict[str, Lane]) -> list[str]:
    """Lanes do PR: as que declaram `ship_pr` + as cujo arquivo o merge tocou."""
    declared = [lane.id for lane in lanes.values() if lane.fm.get("ship_pr") == pr]
    sha = _merge_sha(pr)
    touched = _lane_ids_from_paths(
        _git(["show", "--name-only", "--format=", sha]).split() if sha else [], lanes
    )
    return sorted(set(declared) | set(touched))


def resolve_recent(count: int, lanes: dict[str, Lane]) -> list[str]:
    """Lanes tocadas pelos N últimos commits de `origin/main`."""
    paths = _git(["log", "--name-only", "--format=", f"-{count}", "origin/main"]).split()
    return _lane_ids_from_paths(paths, lanes)


def _sections(text: str) -> list[tuple[str, str]]:
    """Pares (heading, corpo) de cada seção `##`+ do markdown."""
    parts = re.split(r"^(#{2,4}\s.*)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def _has_open_route(body: str, lanes: dict[str, Lane]) -> bool:
    """Deferimento roteado = aponta para lane viva, plano, ADR ou dono nomeado."""
    for target in WIKILINK_RE.findall(body):
        target = target.strip()
        if target in lanes and lanes[target].status in OPEN_LANE:
            return True
        if target.startswith(("PLAN-", "ADR-")):
            return True
    return bool(re.search(r"(owner-gated|dono:|owner:|gatilho\s+`?[a-z-]+`?)", body, re.I))


def check_orphan_deferral(lane: Lane, lanes: dict[str, Lane]) -> list[Finding]:
    """CLOSE-BLOCK: lane fechada hospedando trabalho sem destino — o que some."""
    if not lane.closed:
        return []
    out = []
    for heading, body in _sections(lane.text):
        if not DEFER_HEADING_RE.match(heading) or PLANNING_HEADING_RE.search(heading):
            continue
        # Rota pode estar no próprio heading (`## Out-of-scope ([[ADR-229]] …)`).
        if _has_open_route(f"{heading}\n{body}", lanes):
            continue
        out.append(
            Finding(
                "CLOSE-BLOCK-01",
                "alta",
                lane.id,
                _rel(lane.path),
                f"lane `{lane.status}` hospeda trabalho deferido sem rota para dono vivo",
                f"{heading} — {body.strip().splitlines()[0][:110] if body.strip() else '(vazio)'}",
            )
        )
    return out


def check_ship_trace(lane: Lane) -> list[Finding]:
    """CLOSE-DRIFT: shipped sem `ship_pr`/`ship_date` — entrega sem rastro."""
    if lane.status != "shipped":
        return []
    missing = [k for k in ("ship_pr", "ship_date") if not lane.fm.get(k)]
    if not missing:
        return []
    return [
        Finding(
            "CLOSE-DRIFT-02",
            "media",
            lane.id,
            _rel(lane.path),
            f"`shipped` sem {' e sem '.join(missing)} no frontmatter",
            f"status: shipped · ship_pr: {lane.fm.get('ship_pr')} · ship_date: {lane.fm.get('ship_date')}",
        )
    ]


def check_pr_visible_in_sprint(lane: Lane) -> list[Finding]:
    """CLOSE-DRIFT: o `_README` da sprint não menciona o PR que a lane entregou."""
    pr = lane.fm.get("ship_pr")
    readme = SPRINT / lane.sprint / "_README.md"
    if not isinstance(pr, int) or not readme.exists():
        return []
    if re.search(rf"#{pr}\b", readme.read_text(encoding="utf-8")):
        return []
    return [
        Finding(
            "CLOSE-DRIFT-03",
            "media",
            lane.id,
            _rel(readme),
            f"entrega #{pr} invisível no `_README` da sprint {lane.sprint}",
            f"`{lane.id}` declara ship_pr: {pr}; o README não cita `#{pr}`",
        )
    ]


def check_lane_counter(sprint: str) -> list[Finding]:
    """CLOSE-DRIFT: `## Lanes (N)` divergindo do disco — reincidente (#1341, #1206)."""
    readme = SPRINT / sprint / "_README.md"
    lanes_dir = SPRINT / sprint / "lanes"
    if not readme.exists() or not lanes_dir.exists():
        return []
    match = LANE_COUNT_RE.search(readme.read_text(encoding="utf-8"))
    disk = len(list(lanes_dir.glob("*.md")))
    if not match or int(match.group(2)) == disk:
        return []
    return [
        Finding(
            "CLOSE-DRIFT-04",
            "media",
            f"(sprint {sprint})",
            _rel(readme),
            f"contador de lanes declara {match.group(2)}, disco tem {disk}",
            match.group(0),
        )
    ]


def _routes_to(line: str, lane_id: str) -> bool:
    """Palavra de rota governa este wikilink (janela curta antes dele)?"""
    for match in re.finditer(rf"\[\[{re.escape(lane_id)}[\]|#]", line):
        window = line[max(0, match.start() - ROUTE_WINDOW) : match.start()]
        if ROUTE_WORD_RE.search(DECISAO_DO_DONO_RE.sub(" ", window)):
            return True
    return False


def _mask_struck(text: str) -> str:
    """Neutraliza spans `~~…~~` preservando offsets — o risco pode cruzar linhas."""
    return STRIKETHROUGH_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def _paragraph_at(lines: list[str], index: int) -> str:
    start, end = index, index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return "\n".join(lines[start : end + 1])


def _dead_route_lines(doc: Path, lane_id: str) -> list[str]:
    """Linhas que roteiam trabalho para `lane_id` sem já declarar o fechamento."""
    text = doc.read_text(encoding="utf-8")
    raw_lines, masked = text.splitlines(), _mask_struck(text).splitlines()
    hits = []
    for index, line in enumerate(masked):
        # Linha de tabela lista estado; prosa roteia trabalho. Só prosa.
        if line.lstrip().startswith("|") or not _routes_to(line, lane_id):
            continue
        if INBOUND_RE.search(line) or SELF_CLOSED_RE.search(_paragraph_at(masked, index)):
            continue
        hits.append(raw_lines[index])
    return hits


def check_dead_route_to_lane(lane: Lane) -> list[Finding]:
    """CLOSE-BLOCK: doc vivo ainda manda trabalho futuro para esta lane fechada."""
    if not lane.closed:
        return []
    out = []
    for doc in sorted(SPRINT.glob("*/_README.md")) + sorted(SPRINT.glob("*/lanes/*.md")):
        if doc == lane.path:
            continue
        for raw in _dead_route_lines(doc, lane.id):
            out.append(
                Finding(
                    "CLOSE-BLOCK-05",
                    "alta",
                    lane.id,
                    _rel(doc),
                    f"rota de trabalho futuro aponta para `{lane.id}`, que está `{lane.status}`",
                    raw.strip()[:140],
                )
            )
    return out


def check_stale_blocked(lane: Lane, lanes: dict[str, Lane]) -> list[Finding]:
    """CLOSE-BLOCK: lane `blocked` cuja dependência já shipou — some do pickup."""
    if lane.status != "blocked":
        return []
    deps = lane.fm.get("depends_on") or []
    alive = [
        WIKILINK_RE.match(d).group(1).strip()
        for d in deps
        if isinstance(d, str) and WIKILINK_RE.match(d)
    ]
    shipped = [d for d in alive if d in lanes and lanes[d].status == "shipped"]
    if not shipped or len(shipped) < len(alive):
        return []
    return [
        Finding(
            "CLOSE-BLOCK-06",
            "alta",
            lane.id,
            _rel(lane.path),
            "lane `blocked` com TODAS as dependências já `shipped` — destravou e ninguém viu",
            f"depends_on: {', '.join(shipped)}",
        )
    ]


# Registros `*-active.md` entram desde 2026-08-21: os 2 CLOSE-BLOCK reais da
# revisão de método moravam em linha de achado da PIPELINE-REVIEWS-active,
# fora do universo — a linha-zumbi nasce no merge, e este é o único ponto que
# a vê com latência zero.
def citers_of(lane_id: str) -> list[str]:
    """Docs de sprint + registros `_MOC/*-active.md` que citam a lane (contexto, não falha)."""
    universe = (
        sorted(SPRINT.glob("*/*.md"))
        + sorted(SPRINT.glob("*/lanes/*.md"))
        + sorted(MOC.glob("*-active.md"))
    )
    return [_rel(doc) for doc in universe if f"[[{lane_id}]]" in doc.read_text(encoding="utf-8")]


def audit(lane_ids: list[str], lanes: dict[str, Lane]) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    context: dict[str, list[str]] = {}
    for lane_id in lane_ids:
        lane = lanes[lane_id]
        findings += check_orphan_deferral(lane, lanes)
        findings += check_ship_trace(lane)
        findings += check_pr_visible_in_sprint(lane)
        findings += check_dead_route_to_lane(lane)
        findings += check_stale_blocked(lane, lanes)
        context[lane_id] = [c for c in citers_of(lane_id) if c != _rel(lane.path)]
    for sprint in sorted({lanes[i].sprint for i in lane_ids}):
        findings += check_lane_counter(sprint)
    return findings, context


def _resolve(args: argparse.Namespace, lanes: dict[str, Lane]) -> list[str]:
    if args.lane:
        return sorted(set(args.lane))
    if args.pr:
        return resolve_from_pr(args.pr, lanes)
    return resolve_recent(args.recent, lanes)


def _render(findings: list[Finding], context: dict, lane_ids: list[str]) -> None:
    print(f"lanes no escopo: {', '.join(lane_ids) or '(nenhuma)'}\n")
    if not findings:
        print("estrutural: 0 achados. A metade SEMÂNTICA continua por verificar.\n")
    for f in findings:
        print(f"[{f.severity.upper():5s}] {f.code}  {f.lane}")
        print(f"        {f.summary}")
        print(f"        {f.doc} — {f.evidence}\n")
    for lane_id, docs in context.items():
        print(f"docs que citam {lane_id} (releia na camada 3): {len(docs)}")
        for doc in docs:
            print(f"        {doc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", action="append", help="id da lane (repetível)")
    parser.add_argument("--pr", type=int, help="resolve as lanes deste PR")
    parser.add_argument("--recent", type=int, default=5, help="lanes dos N últimos commits")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    lanes = index_lanes()
    lane_ids = [i for i in _resolve(args, lanes) if i in lanes]
    findings, context = audit(lane_ids, lanes)

    if args.json:
        print(
            json.dumps(
                {"lanes": lane_ids, "findings": [asdict(f) for f in findings], "citers": context},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _render(findings, context, lane_ids)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
