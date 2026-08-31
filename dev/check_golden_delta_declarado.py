#!/usr/bin/env python3
"""Delta valor-a-valor dos goldens que o PR tocou (A40.l80 · destrava A40.l90)."""

# O hook irmão (`check_golden_rebaseline_isolation.py`) enforça ISOLAMENTO — golden em
# commit separado de produção. Ele NÃO produz delta. Sem este passo, "delta declarado"
# era prosa no corpo do PR: `dev/golden_diff.py` existia e NADA o invocava (zero hits em
# `.github/`, `Makefile` e `.pre-commit-config.yaml`).
#
# Os prefixos vêm do gate de isolamento, importados DELE: duas listas divergiriam em
# silêncio e um golden novo entraria num gate e não no outro.
#
# Falha alta, e PROVA que mediu: sem golden tocado ele diz que não achou e quais
# prefixos vigiou, em vez de sair 0 calado. Cegueira passa por conformidade; ausência
# declarada, não. Python e não shell porque `mapfile` é bash 4+ e o dev roda 3.2 —
# script que só se executa no CI é defeito que só aparece no CI.

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Importa como `dev.` (não como top-level) para haver UM módulo: duas cópias do mesmo
# arquivo têm tuplas distintas, e a asserção de fonte única em
# `tests/test_golden_delta_declarado.py` não conseguiria distinguir cópia de partilha.
sys.path.insert(0, str(REPO_ROOT))

from dev.check_golden_rebaseline_isolation import _GOLDEN_PREFIXES  # noqa: E402

MANIFESTO = "tests/fixtures/pipeline_golden/rebaseline_manifest.yaml"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True, cwd=REPO_ROOT
    ).stdout


def goldens_tocados(base_sha: str) -> list[str]:
    """Goldens `.json` alterados em `base..HEAD` — o manifesto viaja junto, não é golden."""
    saida = _git("diff", "--name-only", f"{base_sha}..HEAD", "--", *_GOLDEN_PREFIXES)
    return [
        linha
        for linha in saida.splitlines()
        if linha.endswith(".json") and "rebaseline_manifest" not in linha
    ]


def _existe_na_base(base_sha: str, path: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{base_sha}:{path}"], cwd=REPO_ROOT, capture_output=True
        ).returncode
        == 0
    )


def _diff_de(base_sha: str, path: str, tmp: Path) -> int:
    antigo = tmp / "old.json"
    antigo.write_text(_git("show", f"{base_sha}:{path}"), encoding="utf-8")
    print(f"::group::golden_diff {path}", flush=True)
    codigo = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "dev" / "golden_diff.py"),
            str(antigo),
            path,
            "--manifest",
            MANIFESTO,
            "--golden-id",
            Path(path).name,
        ],
        cwd=REPO_ROOT,
    ).returncode
    print("::endgroup::", flush=True)
    return codigo


def _medir_todos(base: str, tocados: list[str]) -> int:
    falhou = 0
    with tempfile.TemporaryDirectory() as td:
        for path in tocados:
            # Golden REMOVIDO: `git diff --name-only` o lista, e ele não existe mais
            # na árvore. Deleção não tem `value_delta` a declarar — o manifesto
            # justifica número que MUDOU, e aqui não há número novo. Sem este ramo o
            # gate morria em `FileNotFoundError`, que é falha de leitura mascarada de
            # reprovação: o PR ficava vermelho sem dizer o que estava errado.
            if not (REPO_ROOT / path).exists():
                print(f"golden_diff: {path} foi REMOVIDO neste PR — não há delta a medir.")
                continue
            if not _existe_na_base(base, path):
                print(
                    f"golden_diff: {path} é NOVO neste PR (sem versão base) — nada a diferenciar."
                )
                continue
            falhou |= 1 if _diff_de(base, path, Path(td)) else 0
    return falhou


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-sha", required=True)
    base = ap.parse_args(argv).base_sha

    tocados = goldens_tocados(base)
    if not tocados:
        print(f"golden_diff: nenhum golden .json tocado em {base}..HEAD — nada a medir.")
        print(f"  prefixos vigiados: {', '.join(_GOLDEN_PREFIXES)}")
        return 0
    return _medir_todos(base, tocados)


if __name__ == "__main__":
    sys.exit(main())
