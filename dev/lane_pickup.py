#!/usr/bin/env python3
"""Responde 'posso pegar esta lane?' cruzando frontmatter com ocupação viva."""
# Por que existe: o SPRINT_CURRENT.md deriva do frontmatter, e `status` NÃO TEM
# ESCRITOR no pickup. Uma sessão que abre worktree e ainda não commitou é
# invisível a `git for-each-ref`, a `gh pr list` e ao SPRINT_CURRENT — os três
# lugares onde o protocolo do CLAUDE.md manda olhar.
#
# Caso de origem, medido em 2026-08-13: a A40.l35 estava `open` no frontmatter e
# no SPRINT_CURRENT enquanto uma sessão viva trabalhava nela há 2h num worktree,
# com 20+ arquivos modificados, DUAS lanes novas (l61, l62) e uma ADR nova (387)
# — nada commitado, nada pushado, zero PR. Quem lesse a superfície canônica
# pegaria a lane e colidiria; quem alocasse "próximo id de ADR livre" tomaria o
# 387. Só `git worktree list` + leitura DENTRO de cada worktree revela.
#
# Barato de propósito (~80 tokens de saída, precedente ADR-281): a alternativa é
# reler o _README da sprint e os arquivos de lane, ~40k tokens que respondem pior.
#
# 2026-08-27 — o 2º degrau: ENTREGA. Squash-merge nunca deixa a branch ancestral
# de `main`, então branch de lane já entregue citava a lane para sempre. Medido:
# 897 branches `agent/`/`claude/` locais, 522 não-ancestrais; a A40.l80 (P0)
# respondia OCUPADA com 12 sinais, 11 deles branch entregue, e o único sinal vivo
# (worktree com 2 arquivos sujos) ficava soterrado. No `--sprint A40`: 263 linhas
# de `ocupação [branch]` → 2, e 2m34s → 47s.
#
# O predicado é HERMÉTICO — zero rede, e nenhum `git fetch` (buscar dentro de uma
# sonda é como o `check_scheduled_workflows` travou todo merge do repo em
# 2026-08-24). Fecha a condição de retomada que a A40.l59 §Deferimento declarava
# inexistente: o patch-id do diff agregado `merge-base..tip` casa o do commit de
# squash em `main`.
#
# LIMITES DECLARADOS:
#  · `origin/main` defasado só produz falso-OCUPADA (conservador). Nunca o inverso.
#  · Rebase/conflito muda o patch-id ⇒ branch entregue pode seguir contada como
#    viva. Conservador também.
#  · Branch com commit único porém SUPERADO (o caso da A40.l36) sai como viva, de
#    propósito: julgar "superado" é julgar mérito, e isso é do humano.
#  · O filtro de token continua cego a branch que não nomeia a lane —
#    `_mentions("a40-l39", "claude/finalize-lanes-l33-l39-l41-…")` é falso. Uma
#    saída limpa convence mais que a de antes; isto NÃO ficou melhor.

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, NamedTuple

import yaml

try:  # script direto vs. import como `dev.*` (padrão de dev/check_lane_transition.py)
    import _lane_branch_delivery as _delivery  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    from dev import _lane_branch_delivery as _delivery  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
TERMINAL_STATUS: frozenset[str] = frozenset({"shipped", "cancelled"})
WIKILINK_TARGET_RE = re.compile(r"^\[\[([^\]|#]+)")


class Occupancy(NamedTuple):
    """Sinal de ocupação com a fonte que o produziu — sinal sem fonte não é acionável."""

    source: str
    detail: str


# O crash é ruidoso, logo seguro. O perigo é a variante muda: sonda que falha em
# silêncio devolve zero sinais, e zero sinais viram LIVRE — exatamente a colisão
# que este tool existe para evitar. Por isso degradação é dado de primeira classe
# e contamina o veredito, em vez de virar `except: pass`.
class Degradacao(NamedTuple):
    """Sonda que NÃO pôde rodar, com o motivo que a impediu."""

    probe: str
    motivo: str

    def format(self) -> str:
        return f"sonda cega [{self.probe}]: {self.motivo}"


# `subprocess.run(cwd=<inexistente>)` levanta no Popen, ANTES de rodar o git —
# `check=False` não protege. Vale para diretório removido, path que virou
# arquivo e permissão negada; os três aparecem quando um worktree registrado
# sai do disco sem `git worktree prune`.
def _git_probe(*args: str, cwd: Path | None = None) -> tuple[str, str | None]:
    """Devolve ``(stdout, motivo_da_falha)``; nunca levanta."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return "", f"{type(exc).__name__}: {exc.strerror or exc}"
    if result.returncode != 0:
        erro = (result.stderr or "").strip().splitlines()
        return "", erro[0] if erro else f"git {args[0]} saiu {result.returncode}"
    return result.stdout, None


def _git(*args: str, cwd: Path | None = None) -> str:
    return _git_probe(*args, cwd=cwd)[0]


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return {}


def _lane_files(docs_root: Path) -> Iterable[Path]:
    return sorted(docs_root.glob("sprint/*/lanes/*.md"))


def collect_lanes(docs_root: Path) -> dict[str, dict[str, Any]]:
    """Mapa id → frontmatter de toda nota `type: lane`."""
    lanes: dict[str, dict[str, Any]] = {}
    for path in _lane_files(docs_root):
        front = _frontmatter(path)
        if front.get("type") == "lane" and front.get("id"):
            front["_path"] = path
            lanes[str(front["id"])] = front
    return lanes


_WORKTREES: list[Path] | None = None


def _worktree_paths() -> list[Path]:
    """Worktrees do clone — inclui os que nenhuma branch remota revela."""
    global _WORKTREES
    if _WORKTREES is None:
        out = _git("worktree", "list", "--porcelain")
        _WORKTREES = [Path(line[9:]) for line in out.splitlines() if line.startswith("worktree ")]
    return _WORKTREES


def _slug_of(lane_id: str, front: dict[str, Any]) -> str:
    declared = front.get("branch_slug")
    if declared:
        return str(declared)
    return lane_id.lower().replace(".", "-")


def _short_id(lane_id: str) -> str:
    """`A40.l35` → `a40-l35` — o prefixo que branches e arquivos de lane usam."""
    return lane_id.lower().replace(".", "-")


# O id de lane é sequencial e sem padding: `l5` é prefixo textual de `l50`.
# Com `in`, a A40.l5 casava 8 branches de l50/l53/l56 e as 34 lanes `shipped`
# da A40 respondiam OCUPADA. Falso-positivo em sonda de pickup custa igual ao
# falso-negativo: manda o agente para outra lane, e a lane certa fica parada.
# Fronteira = qualquer char não-alfanumérico (o naming é kebab: `-`, `/`, fim).
def _mentions(token: str, text: str) -> bool:
    """`a40-l5` casa `a40-l5-slug` e `agent/a40-l5/ts`, nunca `a40-l50`."""
    return re.search(rf"(?<![0-9a-z]){re.escape(token)}(?![0-9a-z])", text.lower()) is not None


# Só ADICIONA linhas. Não existe flag que desligue a classificação: um
# `--sem-fantasma` recriaria o estado de hoje e viraria default em máquina lenta.
_MOSTRAR_ENTREGUES = False

ENTREGUE = "branch-entregue"
# Lane terminal não paga o pré-computo: o veredito já é TERMINAL. As refs dela
# ficam contadas, não listadas — 251 linhas mortas num `--sprint` afogam o sinal.
NAO_CLASSIFICADA = "branch-nao-classificada"


# 2º degrau, irmão do TERMINAL: o predicado mora em `_lane_branch_delivery`
# (responsabilidade própria, e o gate futuro importa de lá em vez de gemear).
def _classificar(refs: list[str]) -> tuple[list[Occupancy], list[Degradacao]]:
    """Rotula cada ref como ocupação viva ou branch já entregue em `main`."""
    vivas, entregues, motivos = _delivery.classificar(refs)
    signals = [Occupancy("branch", r) for r in vivas]
    signals += [Occupancy(ENTREGUE, r) for r in entregues]
    return signals, [Degradacao("entrega", m) for m in motivos]


def _refs_mentioning(
    tokens: Iterable[str], *, classificar: bool = True
) -> tuple[list[Occupancy], list[Degradacao]]:
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    hits = [ref for ref in out.splitlines() if any(_mentions(t, ref) for t in tokens)]
    if not hits:
        return [], []
    # Lane terminal já responde TERMINAL pelo 1º degrau: classificar não muda o
    # veredito e custa o pré-computo inteiro. Medido: era 90% do tempo do
    # `--sprint A40`, e as branches antigas estouravam a janela, virando sonda
    # cega em lane que ninguém vai pegar.
    if not classificar:
        return [Occupancy(NAO_CLASSIFICADA, ref) for ref in hits], []
    return _classificar(hits)


# O HEAD de um worktree não depende do token da lane, e a varredura pergunta
# 2 tokens × N lanes. Sem memo, `--sprint A40` fazia ~3.780 `rev-parse` para
# 21 worktrees. O cache vive um processo — não há estado entre execuções.
_HEAD_DE_WORKTREE: dict[str, tuple[str, str | None]] = {}


def _head_de(path: Path) -> tuple[str, str | None]:
    chave = str(path)
    if chave not in _HEAD_DE_WORKTREE:
        _HEAD_DE_WORKTREE[chave] = _git_probe("rev-parse", "--abbrev-ref", "HEAD", cwd=path)
    return _HEAD_DE_WORKTREE[chave]


def _sonda_worktree(path: Path, token: str) -> tuple[Occupancy | None, Degradacao | None]:
    """Um worktree: sinal, degradação, ou nenhum dos dois (não cita a lane)."""
    branch, erro = _head_de(path)
    cita_pelo_path = _mentions(token, path.name)
    if erro is not None:
        # Path pode citar a lane e o git ter falhado: reportar mesmo assim, senão
        # um worktree quebrado esconde ocupação real.
        return None, Degradacao("worktree", f"{path.name}: {erro}")
    branch = branch.strip()
    if not (cita_pelo_path or _mentions(token, branch)):
        return None, None
    sujos = len([ln for ln in _git("status", "--short", cwd=path).splitlines() if ln])
    return Occupancy("worktree", f"{path.name} [{branch}] · {sujos} arq. sujos"), None


def _worktrees_mentioning(token: str) -> tuple[list[Occupancy], list[Degradacao]]:
    """Worktree cujo path OU branch cita a lane — pega sessão sem nenhum commit."""
    signals: list[Occupancy] = []
    degradacoes: list[Degradacao] = []
    for path in _worktree_paths():
        sinal, degradacao = _sonda_worktree(path, token)
        if sinal is not None:
            signals.append(sinal)
        if degradacao is not None:
            degradacoes.append(degradacao)
    return signals, degradacoes


# Sinal que nenhum comando do protocolo vigente enxerga: a sessão da A40.l35
# criou A40.l61 e A40.l62 como arquivos não-commitados dentro do próprio
# worktree, e as duas eram invisíveis ao vault inteiro.
def _uncommitted_lane_files(lane_id: str) -> list[Occupancy]:
    """Arquivo de lane que existe só dentro de outro worktree, sem commit."""
    signals: list[Occupancy] = []
    token = _short_id(lane_id)
    for path in _worktree_paths():
        lanes_dir = path / "docs" / "sprint"
        if not lanes_dir.exists():
            continue
        untracked = _git("ls-files", "--others", "--exclude-standard", "docs/sprint", cwd=path)
        hits = [ln for ln in untracked.splitlines() if _mentions(token, ln)]
        signals.extend(Occupancy("arquivo não-commitado", f"{path.name}: {h}") for h in hits)
    return signals


def _pending_deps(front: dict[str, Any], lanes: dict[str, dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for raw in front.get("depends_on") or []:
        match = WIKILINK_TARGET_RE.match(str(raw))
        if not match:
            continue
        dep_id = match.group(1).strip()
        dep = lanes.get(dep_id)
        if dep is not None and dep.get("status") not in TERMINAL_STATUS:
            pending.append(f"{dep_id} ({dep.get('status')})")
    return pending


def occupancy_signals(
    lane_id: str, front: dict[str, Any]
) -> tuple[list[Occupancy], list[Degradacao]]:
    """Todos os sinais de que alguém já está na lane, do mais barato ao mais fundo."""
    tokens = {_short_id(lane_id), _slug_of(lane_id, front).lower()}
    signals: list[Occupancy] = []
    degradacoes: list[Degradacao] = []
    terminal = front.get("status") in TERMINAL_STATUS
    sinais_ref, cegas_ref = _refs_mentioning(sorted(tokens), classificar=not terminal)
    signals.extend(sinais_ref)
    degradacoes.extend(cegas_ref)
    for token in sorted(tokens):
        sinais_wt, cegas = _worktrees_mentioning(token)
        signals.extend(sinais_wt)
        degradacoes.extend(cegas)
    signals.extend(_uncommitted_lane_files(lane_id))
    return list(dict.fromkeys(signals)), list(dict.fromkeys(degradacoes))


# Ordem deliberada, em dois degraus.
#
# 1º TERMINAL, antes de ocupação. Lane entregue não tem o que pegar, e a branch
#    que sobrou é o fim NORMAL dela — não um vizinho trabalhando. Dizer "não
#    pegue sem falar com quem está nela" manda procurar interlocutor que não
#    existe. Medido em 2026-08-17: as 34 lanes `shipped` da A40 respondiam
#    OCUPADA por causa das próprias branches mergeadas. O sinal continua
#    impresso pelo `report` — muda o rótulo, não a evidência.
# 2º Ocupação MEDIDA vence o resto, inclusive degradação: a ressalva não pode
#    diluir sinal real. Já a ausência de sinal só vale como LIVRE se todas as
#    sondas rodaram; senão o veredito diz que não sabe.
def _verdict(
    front: dict[str, Any],
    pending: list[str],
    signals: list[Occupancy],
    degradacoes: list[Degradacao] | None = None,
) -> str:
    if front.get("status") in TERMINAL_STATUS:
        return f"TERMINAL ({front.get('status')}) — nada a pegar"
    if [s for s in signals if s.source not in _RESUMOS]:
        return "OCUPADA — não pegue sem falar com quem está nela"
    if front.get("status") == "planned":
        return "NÃO LIBERADA — `planned` é liberação por-lane, decisão do dono"
    if pending and front.get("partial_delivery") is not True:
        return f"BLOQUEADA — dep pendente: {', '.join(pending)}"
    if pending:
        return f"PEGÁVEL COM AMARRA PARCIAL — dep pendente: {', '.join(pending)}"
    return _livre(degradacoes)


def _livre(degradacoes: list[Degradacao] | None) -> str:
    """Ausência de sinal só é prova de lane livre se TODAS as sondas rodaram."""
    if not degradacoes:
        return "LIVRE"
    return (
        f"LIVRE (RESSALVA: {len(degradacoes)} sonda(s) de ocupação não rodaram — "
        "ausência de sinal aqui não é prova de lane livre)"
    )


# §Pendência 13 da A40 (8 renumerações de id numa sessão): `ls` local mede o
# teto errado enquanto alguém segura o id numa branch ou num worktree.
# Diagnóstico read-only: prescreve o conserto, não o executa. Uma sonda de
# pickup que muta estado do git como efeito colateral é surpresa cara — e
# `prune` não é reversível por quem não sabia que rodou.
_REMEDIO_REGISTRO_ORFAO = (
    "  → registro de worktree órfão: `git worktree prune -v` "
    "(remove só registro cujo diretório sumiu; não apaga nada no disco)"
)


def _linhas_de_degradacao(degradacoes: list[Degradacao]) -> list[str]:
    if not degradacoes:
        return []
    linhas = [f"  {d.format()}" for d in degradacoes]
    if any("No such file" in d.motivo or "NotADirectory" in d.motivo for d in degradacoes):
        linhas.append(_REMEDIO_REGISTRO_ORFAO)
    return linhas


def _report_unknown(lane_id: str) -> tuple[str, int]:
    """Id ausente da vault local ainda pode estar TOMADO por outra sessão."""
    signals, degradacoes = occupancy_signals(lane_id, {})
    signals = [s for s in signals if s.source not in _RESUMOS]
    if not signals:
        cabeca = f"{lane_id}: não existe no vault e nenhum sinal de ocupação — id livre."
        if degradacoes:
            cabeca = f"{lane_id}: não existe no vault, mas {len(degradacoes)} sonda(s) não rodaram."
        return ("\n".join([cabeca, *_linhas_de_degradacao(degradacoes)]), 2)
    out = [f"{lane_id}: NÃO existe na vault local, mas o id está TOMADO — não realoque."]
    out.extend(f"  ocupação [{s.source}]: {s.detail}" for s in signals)
    out.extend(_linhas_de_degradacao(degradacoes))
    return ("\n".join(out), 1)


def report(lane_id: str, lanes: dict[str, dict[str, Any]]) -> tuple[str, int]:
    """Linhas do parecer + exit code (0 = livre/parcial, 1 = não pegável)."""
    front = lanes.get(lane_id)
    if front is None:
        return _report_unknown(lane_id)
    pending = _pending_deps(front, lanes)
    signals, degradacoes = occupancy_signals(lane_id, front)
    verdict = _verdict(front, pending, signals, degradacoes)
    out = [
        f"{lane_id} · status `{front.get('status')}` · {front.get('priority', 's/ prioridade')}",
        f"  {front.get('title', '')}",
        f"  veredito: {verdict}",
    ]
    out.extend(f"  ocupação [{s.source}]: {s.detail}" for s in signals if s.source not in _RESUMOS)
    out.extend(_linhas_resumidas(signals))
    out.extend(_linhas_de_degradacao(degradacoes))
    return ("\n".join(out), 0 if verdict.startswith(("LIVRE", "PEGÁVEL")) else 1)


# A evidência não some — some o RUÍDO. Listar 11 refs entregues empurra o sinal
# vivo (o worktree sujo) para fora da primeira tela, que foi o dano medido na
# A40.l80. Quem quiser os nomes tem `--todas-as-branches`, que só ADICIONA linhas.
_RESUMOS = {
    ENTREGUE: "branch(es) já entregue(s) em `main`, ignorada(s)",
    NAO_CLASSIFICADA: "branch(es) citando a lane — terminal, não classificadas",
}


def _linhas_resumidas(signals: list[Occupancy]) -> list[str]:
    linhas = []
    for source, texto in _RESUMOS.items():
        refs = [s for s in signals if s.source == source]
        if not refs:
            continue
        if _MOSTRAR_ENTREGUES:
            linhas.extend(f"  [{source}] {s.detail}" for s in refs)
        else:
            linhas.append(f"  ({len(refs)} {texto} — `--todas-as-branches` lista)")
    return linhas


def _sprint_of(front: dict[str, Any]) -> str:
    return str(front.get("sprint") or "")


def _scan(lanes: dict[str, dict[str, Any]], sprint: str) -> tuple[str, int]:
    """Varre uma sprint inteira e lista só o que é acionável."""
    rows = [lid for lid, f in sorted(lanes.items()) if _sprint_of(f) == sprint]
    if not rows:
        return (f"Nenhuma lane com sprint `{sprint}`.", 2)
    blocks = [report(lid, lanes)[0] for lid in rows]
    return ("\n\n".join(blocks), 0)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane", nargs="?", help="id da lane, ex.: A40.l35")
    parser.add_argument("--sprint", help="varre todas as lanes de uma sprint, ex.: A40")
    parser.add_argument(
        "--todas-as-branches",
        action="store_true",
        help="lista as branches já entregues em vez de resumi-las (não muda o veredito)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    global _MOSTRAR_ENTREGUES
    _MOSTRAR_ENTREGUES = args.todas_as_branches
    lanes = collect_lanes(DOCS)
    if args.sprint:
        text, code = _scan(lanes, args.sprint)
    elif args.lane:
        text, code = report(args.lane, lanes)
    else:
        parser.error("informe uma lane ou --sprint")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
