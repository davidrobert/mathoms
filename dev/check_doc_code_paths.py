#!/usr/bin/env python3
"""Gate: mover ou deletar código não deixa citação órfã em ADR/reference.

Fecha a classe reaberta pela auditoria r10 (F21 · [[ADR-302]]): nenhum gate lê
path de código escrito em prosa. `check_doc_links` resolve wikilink,
`check_doc_markdown_links` resolve link relativo — um
``backend/app/services/vault.py`` em backtick é invisível aos dois, e toda
movimentação de pacote reabre a classe em silêncio (o cluster ADR-285 nasceu
assim e sobreviveu a duas auditorias).

POLARIDADE — a decisão que este arquivo existe para registrar
==============================================================
O gate dispara no commit que **move ou deleta o código**, não no que escreve o
doc. Isso não é gosto; é o que a medição mostrou, depois de dois desenhos
errados:

1. **Corpus inteiro** (`docs/**` varrido): **1123 ocorrências**. O topo são
   paths mortos POR DESENHO citados como história correta — `scripts/e5_analyze.py`
   (renomeado na F9.4), `scripts/e6_render.py` (deletado pela ADR-129),
   `config/goals.json` (migrado na A10). Gatear exigiria allowlist do tamanho
   do problema, e "corrigir" as citações seria revisionismo. Descartado.

2. **Diff-based no lado do doc** (só linha adicionada, escopo `adr`+`reference`):
   replay sobre 600 commits deu **18 disparos, ~10 falsos**. Estreitando para
   linhas que AFIRMAM existência ("entregue em #429", "vive em X"), caiu para
   **3 disparos — e os 3 eram falsos** (doc commitado antes do código no mesmo
   PR; fixture temporária homônima; negação verbal). Zero verdadeiro.
   Descartado, e a razão é estrutural: **quando o doc é escrito, ele está
   certo.** A citação morre depois, no commit que move o código — e nesse
   commit a linha do doc não é tocada. Gate diff-based no doc não pode ver.

3. **Lado do código** (este): replay sobre 400 commits deu **2 disparos em 1
   commit, zero falso** — a remoção de dois cards do relatório que a ADR-196
   citava. Dispara no instante em que a citação morre, e para a pessoa que tem
   o contexto para decidir se o doc corrige o path ou passa a marcá-lo como
   histórico.

Escopo `docs/adr/` + `docs/reference/` — a superfície "agente lê isto para
decidir", e onde estavam os 20 DOC-BLOCK da r10 sem exceção. Lane e plano
citam arquivo que a própria lane vai criar; ali path não-resolvido é o estado
normal.

O BACKTICK É A AFIRMAÇÃO
========================
`_docs_citing` casa ``` `path` ```, com backtick, e é isso que dá a saída
histórica: backtick diz "existe hoje"; menção sem backtick é história e o gate
não a lê. A instrução impressa até 2026-08-27 mandava "marque a linha como
histórico" sem dizer isso — e marcar sem tirar o backtick não suprimia nada,
o que deixava a saída anunciada inexequível (a linha da ADR-196 já dizia
"removido pela ADR-375" e seguia sendo acusada). Pinado em
`test_citacao_fora_do_backtick_e_a_saida_historica`.

Consequência: link markdown sem backtick também é invisível — declarado como
não-coberto na lane A40.l78, pinado em
`test_link_markdown_sem_backtick_nao_e_visto`.

Uso:
    python3 dev/check_doc_code_paths.py                 # pre-commit (staged)
    python3 dev/check_doc_code_paths.py --since HEAD~5  # range
    python3 dev/check_doc_code_paths.py --all           # auditoria; reporta, não gateia
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_SCOPE = ("docs/adr/", "docs/reference/")

CODE_FILE = re.compile(
    r"^(?:backend|frontend|pipeline|scripts|dev|config|tests|design-tokens)/"
    r".*\.(?:py|ts|tsx|js|jsx|json|yaml|yml|go|css|sql|sh)$"
)

# Arquivo real de runtime que o git não versiona por desenho.
GITIGNORED_BY_DESIGN = frozenset({"config/internal_operators.yaml"})


def _run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, check=False).stdout


def _parse_status_line(line: str) -> tuple[str, str | None] | None:
    """(path_que_sumiu, destino_ou_None) de uma linha de `--name-status -M`."""
    parts = line.split("\t")
    if len(parts) < 2 or not CODE_FILE.match(parts[1]):
        return None
    if parts[0].startswith("D") and len(parts) == 2:
        return (parts[1], None)
    if parts[0].startswith("R") and len(parts) == 3:
        return (parts[1], parts[2])
    return None


def _gone_paths(name_status: str) -> list[tuple[str, str | None]]:
    """Paths de código que este diff removeu do lugar onde estavam."""
    parsed = (_parse_status_line(line) for line in name_status.splitlines())
    return [row for row in parsed if row is not None]


def _docs_citing(path: str) -> list[str]:
    """Docs em escopo que citam ``path`` em backtick. Ignora archive."""
    out = _run("git", "grep", "-l", "-F", f"`{path}`", "--", *DOC_SCOPE)
    return [d for d in out.splitlines() if "/archive/" not in d]


def _still_missing(path: str) -> bool:
    if path in GITIGNORED_BY_DESIGN:
        return False
    return not (REPO_ROOT / path).exists()


def _scoped_docs() -> list[tuple[str, str]]:
    """[(path_relativo, conteúdo)] das notas em escopo, fora de archive."""
    docs = [md for prefix in DOC_SCOPE for md in sorted((REPO_ROOT / prefix).rglob("*.md"))]
    rels = [(md, md.relative_to(REPO_ROOT).as_posix()) for md in docs]
    return [(rel, md.read_text(encoding="utf-8")) for md, rel in rels if "/archive/" not in rel]


def _audit_all() -> list[tuple[str, str]]:
    """Modo auditoria: toda citação em escopo que não resolve hoje."""
    token = re.compile(
        r"`((?:backend|frontend|pipeline|scripts|dev|config|tests|design-tokens)"
        r"/[A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|jsx|json|yaml|yml|go|css|sql|sh))(?::\d+)?`"
    )
    return [
        (rel, m.group(1))
        for rel, text in _scoped_docs()
        for m in token.finditer(text)
        if _still_missing(m.group(1))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Citação de código em ADR/reference")
    parser.add_argument("--since", help="compara contra este ref em vez do índice")
    parser.add_argument("--all", action="store_true", help="auditoria; reporta, não gateia")
    parser.add_argument("files", nargs="*", help="ignorado (compat pre-commit)")
    args = parser.parse_args(argv)

    if args.all:
        rows = _audit_all()
        for doc, path in rows:
            print(f"{doc}: cita `{path}`, que não existe")
        print(f"\n{len(rows)} citação(ões) sem alvo no acervo de ADR/reference.")
        print("[--all é auditoria — exit 0. O gate só cobre movimentação nova.]")
        return 0

    if args.since:
        name_status = _run("git", "diff", "--name-status", "-M", args.since)
    else:
        name_status = _run("git", "diff", "--cached", "--name-status", "-M")

    orphans = [
        (path, dest, docs)
        for path, dest in _gone_paths(name_status)
        if _still_missing(path) and (docs := _docs_citing(path))
    ]

    if not orphans:
        print("✓ nenhuma citação órfã em docs/adr ou docs/reference.")
        return 0

    for path, dest, docs in orphans:
        destino = f"movido para `{dest}`" if dest else "deletado"
        print(f"\n`{path}` foi {destino}, mas é citado em:")
        for d in docs:
            print(f"    {d}")
    print(f"\n{len(orphans)} path(s) de código com citação órfã em ADR/reference.")
    print("Escolha por citação — as duas saídas são legítimas:")
    print("  · atualize o path, se o doc descreve onde a coisa mora HOJE;")
    print("  · vire menção histórica: TIRE o backtick e mantenha o nome (ex.:")
    print('    "vivia em backend/app/x.py, removido pela ADR-129"). O backtick é')
    print("    a afirmação de que o path existe hoje; sem ele o gate não lê a")
    print("    linha como citação. Apagar o nome seria revisionismo — não é isso.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
