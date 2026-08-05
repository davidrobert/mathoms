#!/usr/bin/env python3
"""Resolve a revisão do executor para pinar no launch (ADR-362 · ADR-363).

O `git` vive AQUI, nunca em `backend/app/**`: resolver em runtime pinaria o HEAD
do momento do run em vez do bytecode carregado — medido num worker que servia
código 45 min mais velho que o HEAD.

Uso (os dois ambientes que existem — dev local e CI):
    MATHOMS_BUILD_SHA=$(dev/build_info.py) uvicorn ...     # launch nativo
    dev/build_info.py --check-roots                        # aviso de raiz divergente
    dev/build_info.py --preflight _dev_pids/worker.log     # processo vivo vs HEAD

Sempre exit 0 no modo default: isto roda em substituição de comando no Makefile,
e falhar aqui derrubaria o launch por causa de um campo de observabilidade.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.app.core.executor_revision import normalize_executor_revision  # noqa: E402

_DIRTY_SUFFIX = "-dirty"
_LOG_KEY = "executor_revision"


def _git(*args: str, cwd: Path | None = None) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd or _ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    return out.stdout.strip()


def resolve_revision(cwd: Path | None = None) -> str | None:
    """Revisão do worktree: `<sha12>` ou `<sha12>-dirty`. None se não houver git."""
    sha = _git("rev-parse", "HEAD", cwd=cwd)
    if not sha:
        return None
    # `status --porcelain` e não `diff-index`: arquivo untracked é módulo
    # importável (o `diff-index` mente por omissão), e `update-index --refresh`
    # MUTA `.git/index` — inaceitável num clone com dezenas de worktrees.
    dirty = bool(_git("status", "--porcelain", cwd=cwd))
    return normalize_executor_revision(f"{sha}{_DIRTY_SUFFIX}" if dirty else sha)


def git_root_of(module_file: str | None) -> str | None:
    """Raiz git que contém o arquivo de um módulo importado (ou None)."""
    if not module_file:
        return None
    return _git("rev-parse", "--show-toplevel", cwd=Path(module_file).resolve().parent)


def divergent_roots_warning(pipeline_root: str | None, backend_root: str | None) -> str | None:
    """Aviso quando `pipeline` e `backend` vêm de checkouts diferentes."""
    # Modo de falha real: PYTHONPATH de um worktree vencendo o editable install,
    # com o worker rodando metade do código de cada árvore.
    if not pipeline_root or not backend_root or pipeline_root == backend_root:
        return None
    return (
        "AVISO: `pipeline` e `backend` resolvem para raízes git DIFERENTES — "
        f"pipeline={pipeline_root} backend={backend_root}. "
        "O processo roda metade do código de cada árvore; a revisão pinada "
        "descreve apenas o launch."
    )


def _divergence_counts(base: str, head: str) -> tuple[str, str] | None:
    """(atrás, à frente) entre duas revisões, ou None se a base é inalcançável."""
    # `unreachable` é obrigatório: branches `agent/*` são squash-merged e
    # auto-deletadas, e `git rev-list A..B` com A órfão devolve VAZIO — sem este
    # estado o leitor concluiria, errado, que nada mudou. Ausência nunca vira zero.
    if _git("cat-file", "-e", f"{base}^{{commit}}") is None:
        return None
    counts = _git("rev-list", "--left-right", "--count", f"{base}...{head}")
    if counts is None:
        return None
    behind, ahead = (counts.split() + ["0", "0"])[:2]
    return behind, ahead


def ancestry(revision: str | None, head: str | None = None) -> str:
    """Relação entre a revisão de um run e o HEAD atual — 6 estados."""
    if not revision:
        return "desconhecido"
    base = revision.split(_DIRTY_SUFFIX)[0]
    dirty = _DIRTY_SUFFIX in revision
    head = head or _git("rev-parse", "HEAD")
    if not head:
        return "desconhecido"
    if head.startswith(base) or base.startswith(head[: len(base)]):
        # `identical-dirty` existe porque com árvore suja o sha não identifica o
        # código: dizer `identical` devolveria a garantia que o sufixo tira.
        return "identical-dirty" if dirty else "identical"
    counts = _divergence_counts(base, head)
    if counts is None:
        return "unreachable"
    behind, ahead = counts
    if behind == "0" and ahead != "0":
        return "ancestor"
    return "descendant" if ahead == "0" and behind != "0" else "divergent"


def commits_ahead_of(revision: str | None, head: str | None = None) -> int | None:
    """Quantos commits o HEAD tem à frente da revisão do run (None se indecidível)."""
    if not revision:
        return None
    base = revision.split(_DIRTY_SUFFIX)[0]
    head = head or _git("rev-parse", "HEAD")
    if not head or _git("cat-file", "-e", f"{base}^{{commit}}") is None:
        return None
    counts = _git("rev-list", "--left-right", "--count", f"{base}...{head}")
    if counts is None:
        return None
    parts = counts.split()
    return int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else None


def boot_revision_from_log(text: str) -> str | None:
    """Última revisão anunciada no log de boot (JSON estruturado)."""
    found = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{") or _LOG_KEY not in line:
            continue
        try:
            value = json.loads(line).get(_LOG_KEY)
        except (ValueError, AttributeError):
            continue
        if isinstance(value, str) and value:
            found = value
    return found


_UNKNOWN_REVISION_LITERAL = "desconhecido"


def _inconclusive_warning(live: str, head: str) -> str:
    return (
        f"AVISO: comparação INCONCLUSIVA — worker `{live}` vs HEAD `{head}`, "
        "com árvore suja. Código não commitado não é identificado pelo sha; "
        "o worker pode estar rodando outra coisa. Reinicie para garantir."
    )


_NO_REVISION_ANNOUNCED = (
    "AVISO: nenhum processo anunciou revisão no log — não é possível saber qual "
    "código vai executar este run. Suba o worker via `make dev-worker-up` para "
    "pinar a revisão."
)


def preflight_warning(live: str | None, head: str | None) -> str | None:
    """Aviso quando o processo vivo não roda a revisão do HEAD atual."""
    if live is None or live == _UNKNOWN_REVISION_LITERAL:
        return _NO_REVISION_ANNOUNCED
    if head is None:
        return None
    # Árvore suja ⇒ o sha NÃO identifica o código, então igualdade não prova nada:
    # é o laço dominante do dogfood ("corrijo → reinicio → rodo → ajusto → rodo
    # sem reiniciar"), e silenciar aqui é o falso-verde mais fácil de cometer.
    if _DIRTY_SUFFIX in live or _DIRTY_SUFFIX in head:
        return _inconclusive_warning(live, head)
    if live == head:
        return None
    return (
        f"AVISO: o worker vivo roda `{live}` e o HEAD é `{head}`. O run vai "
        "executar código VELHO; o relatório não refletirá a árvore atual. "
        "Reinicie o worker antes de disparar."
    )


def _cmd_preflight(log_path: Path) -> int:
    text = log_path.read_text(errors="replace") if log_path.exists() else ""
    warning = preflight_warning(boot_revision_from_log(text), resolve_revision())
    if warning:
        print(warning, file=sys.stderr)
        return 0
    # Imprime a revisão: linha verde sem valor esconde `-dirty` e outras surpresas.
    print(f"preflight: worker vivo em `{boot_revision_from_log(text)}` == HEAD")
    return 0


def _cmd_check_roots() -> int:
    import backend.app as backend_pkg
    import pipeline

    warning = divergent_roots_warning(
        git_root_of(getattr(pipeline, "__file__", None)),
        git_root_of(getattr(backend_pkg, "__file__", None)),
    )
    if warning:
        print(warning, file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-roots", action="store_true", help="avisa se as raízes divergem")
    parser.add_argument("--preflight", type=Path, metavar="LOG", help="processo vivo vs HEAD")
    args = parser.parse_args(argv)

    if args.preflight is not None:
        return _cmd_preflight(args.preflight)
    if args.check_roots:
        return _cmd_check_roots()
    print(resolve_revision() or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
