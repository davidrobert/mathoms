#!/usr/bin/env python3
"""Branch já entregue em `main` não é ocupação — predicado hermético, sem rede.

Squash-merge **nunca** deixa a branch como ancestral de `main`, então a branch de
uma lane entregue cita a lane para sempre. Medido em 2026-08-27: 897 branches
`agent/`/`claude/` locais, 522 não-ancestrais; a A40.l80 (P0) respondia OCUPADA
com 12 sinais, 11 deles entregues, e o único sinal vivo — worktree com 2 arquivos
sujos — ficava soterrado sob o ruído.

O predicado:

    entregue ⟺ ancestral(origin/main) ∨ patch-id(merge-base..tip) ∈ patch-ids(main)

O patch-id do diff **agregado** é o que alcança o squash: os patch-ids
por-commit (o que `git cherry` compara) não casam, porque N commits viraram 1.

Fecha a condição de retomada do §Deferimento da A40.l59, que declarava esta
fonte inexistente. Devolve `str`, nunca tipos do `lane_pickup` — é o que mantém
a dependência em um sentido só.

REGRA INEGOCIÁVEL: não-classificado é VIVO. `merge-base --is-ancestor` sai 1
para "não é ancestral" (resposta legítima) e 128 para erro; colapsar os dois
transforma falha de sonda em "entregue", que é o fail-open exato que o
`lane_pickup` existe para não ter.

Nenhum `git fetch` aqui: buscar dentro de uma sonda é como o
`check_scheduled_workflows` travou todo merge do repo em 2026-08-24.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Acima disto o pré-computo deixa de pagar. Não é constante de dias — a âncora é
# a merge-base mais velha do próprio conjunto —, mas conjunto com branch antiga
# demais varreria `main` inteira.
TETO_COMMITS = 400

# O `git log -p` da janela é o custo dominante e não varia por lane: é sempre o
# mesmo `origin/main`. Sem memo, `--sprint A40` recomputava-o ~90×. O piso só
# anda para trás, logo o memorizado é superconjunto do que vier depois.
JANELA: dict[str, object] = {"piso": None, "pids": set()}


def _git(*args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""


def _rc(*args: str) -> int | None:
    """Returncode cru; `None` quando o git nem rodou."""
    try:
        return subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
        ).returncode
    except OSError:
        return None


def ancestral_de_main(ref: str) -> bool | None:
    """`True`/`False`, ou `None` quando a sonda não pôde decidir."""
    return {0: True, 1: False}.get(_rc("merge-base", "--is-ancestor", ref, "origin/main"))


def _patch_ids(diff: str) -> list[str]:
    """patch-ids estáveis de um stream de patches; vazio se a sonda falhar."""
    if not diff.strip():
        return []
    try:
        done = subprocess.run(
            ["git", "patch-id", "--stable"],
            cwd=str(REPO_ROOT),
            input=diff,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    return [ln.split()[0] for ln in done.stdout.splitlines() if ln.strip()]


def _ancora(bases: list[str]) -> str | None:
    """Ancestral comum a todas as merge-bases — o piso do pré-computo."""
    if len(bases) == 1:
        return bases[0]
    # `merge-base A B C` sai 0 com stdout VAZIO para N > 2; só `--octopus`
    # devolve o ancestral comum a todos. Medido em 2026-08-27 sobre a A40.l80.
    return _git("merge-base", "--octopus", *bases).strip() or None


def _pids_de_main(ancora: str) -> tuple[set[str], str | None]:
    """patch-ids de `ancora..origin/main`, memorizados e monotônicos no processo."""
    piso = JANELA["piso"]
    if piso is not None and _rc("merge-base", "--is-ancestor", str(piso), ancora) == 0:
        return set(JANELA["pids"]), None  # type: ignore[arg-type]
    novo = ancora if piso is None else (_ancora(sorted({str(piso), ancora})) or ancora)
    distancia = _git("rev-list", "--count", f"{novo}..origin/main").strip()
    if not distancia.isdigit() or int(distancia) > TETO_COMMITS:
        return set(), f"{distancia or '?'} commits até a âncora — acima do teto, não classificadas"
    pids = set(_patch_ids(_git("log", "-p", f"{novo}..origin/main")))
    JANELA.update(piso=novo, pids=pids)
    return pids, None


def _entregue(ref: str, base: str, em_main: set[str]) -> bool:
    pids = _patch_ids(_git("diff", f"{base}..{ref}"))
    return bool(pids) and pids[0] in em_main


def _entregues_por_patch_id(refs: list[str]) -> tuple[set[str], str | None]:
    """Subconjunto de `refs` cujo diff agregado já está em `origin/main`."""
    bases = {ref: _git("merge-base", ref, "origin/main").strip() for ref in refs}
    if not all(bases.values()):
        return set(), "merge-base com origin/main não resolveu"
    ancora = _ancora(sorted(set(bases.values())))
    if ancora is None:
        return set(), "âncora do pré-computo não resolveu"
    em_main, cega = _pids_de_main(ancora)
    if cega is not None:
        return set(), cega
    return {r for r, b in bases.items() if _entregue(r, b, em_main)}, None


def _por_ancestralidade(refs: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Separa em `(entregues, indecisas, cegas)` pelo teste barato."""
    entregues, indecisas, cegas = [], [], []
    for ref in refs:
        veredito = ancestral_de_main(ref)
        destino = {True: entregues, False: indecisas, None: cegas}[veredito]
        destino.append(ref)
    return entregues, indecisas, cegas


def classificar(refs: list[str]) -> tuple[list[str], list[str], list[str]]:
    """`(vivas, entregues, motivos_de_sonda_cega)` — o que não classifica é vivo."""
    entregues, indecisas, cegas = _por_ancestralidade(refs)
    vivas = list(cegas)
    motivos = [f"{ref}: --is-ancestor não decidiu" for ref in cegas]
    if indecisas:
        por_patch_id, motivo = _entregues_por_patch_id(indecisas)
        entregues.extend(r for r in indecisas if r in por_patch_id)
        vivas.extend(r for r in indecisas if r not in por_patch_id)
        if motivo is not None:
            motivos.append(motivo)
    return vivas, entregues, motivos
