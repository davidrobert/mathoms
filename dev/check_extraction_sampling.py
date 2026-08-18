#!/usr/bin/env python3
"""Call-site de extração declara `temperature` e `seed` (A40.l66 · ADR-394 cauda).

Fecha **sintaxe**, não determinismo: em `anthropic/*` o `seed` é descartado por
`litellm.drop_params` (medido — `get_supported_openai_params` não o lista para
`claude-sonnet-4-6`). O gate existe para que um call-site novo não nasça herdando
`temperature=0.1` do `LLMConfig` sem que alguém tenha decidido.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALVO = "pipeline/stages"
PREFIXO = "extract_"
EXIGIDOS = ("temperature", "seed")


def _chamadas_de_call(arvore: ast.AST) -> list[ast.Call]:
    return [
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.Call)
        and isinstance(no.func, ast.Attribute)
        and no.func.attr == "call"
        and isinstance(no.func.value, ast.Name)
        and no.func.value.id == "service"
    ]


def _faltantes(chamada: ast.Call) -> list[str]:
    nomeados = {kw.arg for kw in chamada.keywords if kw.arg}
    return [k for k in EXIGIDOS if k not in nomeados]


def main() -> int:
    achados: list[str] = []
    for arquivo in sorted((REPO_ROOT / ALVO).glob(f"{PREFIXO}*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for chamada in _chamadas_de_call(arvore):
            faltam = _faltantes(chamada)
            if faltam:
                rel = arquivo.relative_to(REPO_ROOT)
                achados.append(f"{rel}:{chamada.lineno}: `service.call` sem {', '.join(faltam)}")
    if achados:
        print("\n".join(achados))
        print(
            f"\n✗ {len(achados)} call-site(s) de extração sem amostragem declarada.\n"
            "  Use `temperature=EXTRACTION_TEMPERATURE, seed=EXTRACTION_SEED` de\n"
            "  pipeline/llm/deterministic_extraction.py — sem eles o call-site herda\n"
            "  temperature=0.1 do LLMConfig por omissão, não por decisão."
        )
        return 1
    print("✓ todo `service.call` em pipeline/stages/extract_*.py declara temperature + seed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
