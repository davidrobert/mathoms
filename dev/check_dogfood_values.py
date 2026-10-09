#!/usr/bin/env python3
"""Gate: valor monetário do workspace de dogfood não entra no repositório (ADR-442).

Lê só linhas ADICIONADAS e compara cada forma monetária, normalizada em centavos,
contra a denylist HMAC local (`dev/build_dogfood_denylist.py`). A saída é
`path:linha: VALOR_DOGFOOD` — nunca o número.

Uso:
    python3 dev/check_dogfood_values.py --staged          # pre-commit
    python3 dev/check_dogfood_values.py --commit-msg ARQ  # commit-msg
    python3 dev/check_dogfood_values.py --pre-push        # pre-push, commit a commit
    python3 dev/check_dogfood_values.py --tree            # inventário local da árvore
    python3 dev/check_dogfood_values.py --self-test       # canário num repo temporário
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dogfood_values import (  # noqa: E402
    MANIFEST_MAX_AGE_DAYS,
    MANIFEST_NAME,
    Denylist,
    DenylistIndisponivel,
    carregar_denylist,
    centavos_da_linha,
    diretorio_da_denylist,
    e_tier_a,
)

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_ZEROS = re.compile(r"^0+$")
_ORIENTACAO = (
    "Use ponteiro (run · stage · campo) + relação (sinal, razão, Δ%), ou valor sintético. "
    "Arredondar não sanea. Constante pública: dev/dogfood_public_constants.json + regerar."
)

Linha = tuple[str, int, str]


def _git(*args: str, cwd: Path | None = None) -> str:
    # Dentro de hook o git exporta GIT_DIR/GIT_INDEX_FILE: um repo temporário com `cwd`
    # explícito herdaria o índice do repo real.
    env = None if cwd is None else {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    resultado = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"git {args[0]} saiu com {resultado.returncode}")
    return resultado.stdout


def linhas_adicionadas(diff: str) -> Iterator[Linha]:
    """(path, número da linha no destino, texto) de cada `+` de um diff `-U0`."""
    leitor = _LeitorDeDiff()
    for bruta in diff.splitlines():
        if (linha := leitor.avancar(bruta)) is not None:
            yield linha


@dataclass
class _LeitorDeDiff:
    """Estado da leitura de um diff: arquivo, linha no destino e se está no cabeçalho."""

    path: str = ""
    numero: int = 0
    no_cabecalho: bool = False

    def avancar(self, bruta: str) -> Linha | None:
        # `+++` só é cabeçalho antes do 1º `@@`: conteúdo que começa com `++` também vira `+++`.
        if bruta.startswith("diff --git "):
            self.path, self.no_cabecalho = "", True
            return None
        if self.no_cabecalho and bruta.startswith("+++ "):
            self.path = bruta[6:] if bruta.startswith("+++ b/") else ""
            return None
        if (m := _HUNK.match(bruta)) is not None:
            self.numero, self.no_cabecalho = int(m.group(1)), False
            return None
        if self.no_cabecalho or not self.path or not bruta.startswith("+"):
            return None
        self.numero += 1
        return self.path, self.numero - 1, bruta[1:]


def ocorrencias(linhas: Iterable[Linha], denylist: Denylist) -> list[tuple[str, int]]:
    """(path, linha) de cada linha com ao menos um valor da denylist."""
    achados = []
    for path, numero, texto in linhas:
        if any(e_tier_a(c) and denylist.contem(c) for c in centavos_da_linha(texto)):
            achados.append((path, numero))
    return achados


def linhas_staged() -> Iterator[Linha]:
    yield from linhas_adicionadas(_git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff"))


def linhas_da_mensagem(arquivo: Path) -> Iterator[Linha]:
    for numero, texto in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
        if not texto.startswith("#"):
            yield "COMMIT_EDITMSG", numero, texto


def commits_do_push(de: str, para: str) -> list[str]:
    """Commits que o push publica — a lista inteira, não o diff líquido."""
    if not para or _ZEROS.match(para):
        return []
    # Commit já em algum remoto já foi publicado: após rebase, `de..para` reabria a main inteira.
    ja_publicados = ["--remotes"] if not de or _ZEROS.match(de) else ["--remotes", de]
    return _git("rev-list", "--reverse", para, "--not", *ja_publicados).split()


def linhas_do_commit(sha: str) -> Iterator[Linha]:
    yield from linhas_adicionadas(
        _git("show", "-U0", "--no-color", "--no-ext-diff", "--format=", sha)
    )
    mensagem = _git("log", "-1", "--format=%B", sha)
    for numero, texto in enumerate(mensagem.splitlines(), 1):
        yield f"{sha[:12]}:mensagem", numero, texto


def linhas_do_pre_push() -> Iterator[Linha]:
    de = os.environ.get("PRE_COMMIT_FROM_REF", "")
    para = os.environ.get("PRE_COMMIT_TO_REF", "")
    for sha in commits_do_push(de, para):
        yield from (
            (f"{sha[:12]}:{path}", numero, texto) for path, numero, texto in linhas_do_commit(sha)
        )


def linhas_da_arvore() -> Iterator[Linha]:
    for path in _git("ls-files", "-z").split("\0"):
        try:
            texto = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for numero, linha in enumerate(texto.splitlines(), 1):
            yield path, numero, linha


def _reportar(achados: list[tuple[str, int]]) -> int:
    for path, numero in achados:
        print(f"{path}:{numero}: VALOR_DOGFOOD", file=sys.stderr)
    if achados:
        print(
            f"\n✗ {len(achados)} linha(s) com valor do dogfood (ADR-442). {_ORIENTACAO}",
            file=sys.stderr,
        )
    return 1 if achados else 0


def _avisar_se_velha(denylist: Denylist) -> None:
    idade = denylist.idade_dias(datetime.now(timezone.utc))
    if idade > MANIFEST_MAX_AGE_DAYS:
        print(
            f"⚠ denylist com {idade:.0f} dias — rode `python3 dev/build_dogfood_denylist.py` "
            "para cobrir os runs novos.",
            file=sys.stderr,
        )


def _carregar_ou_sair() -> Denylist | int:
    diretorio = diretorio_da_denylist()
    if not diretorio.is_dir():
        print(
            f"ℹ dogfood-values: sem {diretorio} — gate inativo nesta máquina (CI/cloud).",
            file=sys.stderr,
        )
        return 0
    try:
        denylist = carregar_denylist(diretorio)
    except DenylistIndisponivel as exc:
        print(
            f"✗ dogfood-values: {diretorio} existe mas a denylist está indisponível ({exc}).",
            file=sys.stderr,
        )
        return 1
    _avisar_se_velha(denylist)
    return denylist


def _self_test(denylist: Denylist) -> int:
    """Planta o canário do manifesto num repo temporário e exige o hit."""
    canario = json.loads((diretorio_da_denylist() / MANIFEST_NAME).read_text())["canary_cents"]
    reais, cents = divmod(int(canario), 100)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _git("init", "-q", cwd=repo)
        (repo / "canario.md").write_text(f"valor: {reais:,}.{cents:02d}\n".replace(",", "_"))
        _git("add", "canario.md", cwd=repo)
        diff = _git("diff", "--cached", "-U0", "--no-color", cwd=repo)
    achou = bool(ocorrencias(linhas_adicionadas(diff), denylist))
    print("✓ canário detectado" if achou else "✗ canário NÃO detectado", file=sys.stderr)
    return 0 if achou else 1


def _linhas_do_modo(args: argparse.Namespace) -> Iterable[Linha]:
    if args.commit_msg:
        return linhas_da_mensagem(Path(args.commit_msg))
    if args.pre_push:
        return linhas_do_pre_push()
    if args.tree:
        return linhas_da_arvore()
    return linhas_staged()


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Gate de valor do dogfood (ADR-442)")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--staged", action="store_true", help="linhas adicionadas no diff staged")
    modo.add_argument("--commit-msg", metavar="ARQ", help="mensagem de commit")
    modo.add_argument("--pre-push", action="store_true", help="cada commit do push")
    modo.add_argument("--tree", action="store_true", help="todos os arquivos versionados")
    modo.add_argument("--self-test", action="store_true", help="canário num repo temporário")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    denylist = _carregar_ou_sair()
    if isinstance(denylist, int):
        return denylist
    if args.self_test:
        return _self_test(denylist)
    return _reportar(ocorrencias(_linhas_do_modo(args), denylist))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — a mensagem pode conter o token; só o tipo sai
        print(f"✗ dogfood-values: erro interno ({type(exc).__name__})", file=sys.stderr)
        sys.exit(2)
