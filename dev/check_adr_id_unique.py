#!/usr/bin/env python3
"""Gate: dois arquivos em docs/adr/ nunca declaram o mesmo `id:`.

Anti-recorrência de 2026-08-19 (§r7): quatro sessões paralelas alocaram o
mesmo id de ADR na escrita, duas vezes no mesmo dia (ADR-396 por três
frentes, ADR-399 por duas). Nada barrava — `check_adr_anchors` valida
anchor, `validate_frontmatter` valida shape, e `check_doc_filename_id`
casa filename com id **por nota**, nunca entre notas. Filenames distintos
(`396-amostragem-...` vs `396-eixo-...`) satisfazem os três, não conflitam
no merge, e chegariam em main como dois ADR-396 vivos — com todo
`[[ADR-396]]` ambíguo e o índice listando o id duas vezes.

O id é recurso global monotônico alocado na escrita (CLAUDE.md §ADRs); o
que faltava era o gate que torna a alocação verificável. Roda sobre o
repo inteiro (não sobre o diff): duplicata é propriedade do conjunto, e
gate diff-based não a enxerga quando os dois lados chegam por PRs
distintos.

Stdlib puro — roda no job Lint sem venv completo.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"

_ID_RE = re.compile(r"^id:\s*['\"]?(?P<id>[A-Za-z0-9._-]+)['\"]?\s*$", re.MULTILINE)


def _declared_id(path: Path) -> str | None:
    """`id:` do frontmatter, lido só do bloco YAML de abertura."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    match = _ID_RE.search(text[: end if end != -1 else len(text)])
    return match.group("id") if match else None


def _collect() -> dict[str, list[Path]]:
    by_id: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(ADR_DIR.glob("*.md")):
        note_id = _declared_id(path)
        if note_id:
            by_id[note_id].append(path)
    return by_id


def _display(path: Path) -> str:
    """Path relativo ao repo quando possível — o gate roda sobre tmp_path em teste."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    duplicates = {i: p for i, p in _collect().items() if len(p) > 1}
    if not duplicates:
        return 0
    print("ADR com id duplicado — o id é recurso global, alocado na escrita:\n")
    for note_id, paths in sorted(duplicates.items()):
        print(f"  {note_id} declarado por {len(paths)} arquivos:")
        for path in paths:
            print(f"    - {_display(path)}")
    print(
        "\nQuem chegou depois realoca: `ls docs/adr/ | tail` para o próximo livre,\n"
        "e confira `gh pr list --state open` — id reivindicado por PR em voo não\n"
        "aparece em main. Renomeie o arquivo, corrija `id:` no frontmatter e todo\n"
        "`[[ADR-NNN]]`, e regenere com `dev/build_doc_index.py --inline`."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
