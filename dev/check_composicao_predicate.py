#!/usr/bin/env python3
"""A40.l71 (RV6-23) — a composição patrimonial tem UM predicado, e o rótulo da
residência não pode ser renomeado só de um lado.

Dois checks, mesma classe de bug (duas fontes de verdade sobre um fato):

1. **Leitor único** — só `visibleCompositionRows.ts` LÊ `composicao` /
   `tabela_categorias`. Foi a duplicação que produziu o desacordo do r6: donut
   com `valor > 0`, tabela com exceção de residência, e o balde negativo
   respondendo diferente na mesma tela.

   O check é sobre a **leitura**, não sobre o `.filter(`: a primeira versão
   deste gate casava `composicao` e `.filter(` na mesma linha e passou verde
   sobre a mutação que reintroduzia o bug em duas linhas — que é a forma do
   código original. Gate que não pega o bug que motivou o gate mede sintaxe,
   não a classe.

2. **Paridade Py↔TS** — o payload transmite o RÓTULO da categoria, não o
   `template_key` da ADR-145 (`patrimonio_calculator.py` monta
   `{"categoria": "Residência", ...}`). Logo o filtro da ADR-215 P5 casa por
   string, e um rename no produtor o desligaria em silêncio. Este check faz o
   rename falhar no commit.

Sem `files:` de propósito — o par vive nos dois stacks, e um PR que só toca
`pipeline/` não roda Vitest (precedente: `check_probabilidade_parity.py`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PREDICATE_TS = REPO / "frontend/src/components/report/utils/visibleCompositionRows.ts"
PRODUCER_PY = REPO / "pipeline/domain/services/patrimonio_calculator.py"
FRONTEND_SRC = REPO / "frontend/src"

_TS_LABEL = re.compile(r'CATEGORIA_RESIDENCIA_LABEL\s*=\s*"([^"]+)"')
_PY_LABEL = re.compile(r'\{\s*"categoria":\s*"([^"]+)",\s*"valor":\s*residencia\s*\}')
_RAW_READ = re.compile(r"\.composicao\b|\btabela_categorias\b|patrimonio\.composicao")

# Leitores declarados. Entrada nova aqui é decisão consciente: cada uma é uma
# segunda resposta possível para "quais linhas da composição valem".
_ALLOWED_READERS = {
    "frontend/src/components/report/utils/visibleCompositionRows.ts": "o predicado único (A40.l71)",
    "frontend/src/types/report-analysis.ts": "declaração de tipo, não leitura de valor",
    # 2026-08-17 — responde "qual categoria domina", não "quais linhas são
    # visíveis"; não filtra e não renderiza a tabela. Roteá-lo pelo predicado
    # mudaria copy de conclusão, que é escopo da A40.l72 (7a).
    "frontend/src/components/report/utils/conclusionUtils.ts": "escolhe a categoria dominante",
}


def _is_comment(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("*") or stripped.startswith("//")


def _reads_in_file(path: Path, rel: str) -> list[str]:
    """Linhas de código (não comentário) que leem a composição crua."""
    lines = enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    return [
        f"{rel}:{n}: {line.strip()}"
        for n, line in lines
        if not _is_comment(line) and _RAW_READ.search(line)
    ]


def _rogue_readers() -> list[str]:
    """Call-sites que leem a composição crua fora do predicado único."""
    out: list[str] = []
    for path in sorted(FRONTEND_SRC.rglob("*.ts*")):
        rel = path.relative_to(REPO).as_posix()
        if rel not in _ALLOWED_READERS:
            out.extend(_reads_in_file(path, rel))
    return out


def _label_mismatch() -> str | None:
    """Rótulo da residência divergente entre produtor e predicado."""
    ts = _TS_LABEL.search(PREDICATE_TS.read_text(encoding="utf-8"))
    py = _PY_LABEL.search(PRODUCER_PY.read_text(encoding="utf-8"))
    if ts is None:
        return f"{PREDICATE_TS.relative_to(REPO)}: CATEGORIA_RESIDENCIA_LABEL não encontrado"
    if py is None:
        return (
            f"{PRODUCER_PY.relative_to(REPO)}: entrada de residência não encontrada em composicao"
        )
    if ts.group(1) != py.group(1):
        return (
            f"rótulo da residência divergente: produtor emite {py.group(1)!r}, "
            f"predicado casa {ts.group(1)!r} — o filtro da ADR-215 P5 está desligado"
        )
    return None


def main() -> int:
    failures: list[str] = []

    rogue = _rogue_readers()
    if rogue:
        failures.append(
            "leitura crua da composição fora do predicado único (A40.l71):\n  "
            + "\n  ".join(rogue)
            + f"\n  → use visibleCompositionRows() de {PREDICATE_TS.relative_to(REPO)}"
        )

    mismatch = _label_mismatch()
    if mismatch:
        failures.append(mismatch)

    if failures:
        print("\n".join(f"✗ {f}" for f in failures), file=sys.stderr)
        return 1
    print("✓ composição patrimonial: predicado único + rótulo em paridade Py↔TS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
