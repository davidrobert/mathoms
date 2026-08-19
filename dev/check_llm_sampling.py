#!/usr/bin/env python3
"""Todo call-site de `LLMService.call` declara `temperature` e `seed`.

Sucede `check_extraction_sampling.py` (A40.l66 · [[ADR-394]] cauda), que casava
por path (`pipeline/stages/extract_*.py`) e por nome do receptor (`service`).
Os dois eixos vazavam: `comprovantes_bens_llm.py` é extração e não casava o glob;
`self._service.call` não casa `ast.Name`. O discriminador estável é a assinatura
— `system_prompt` + `output_schema` juntos são únicos de `LLMService.call` e
obrigatórios em toda chamada real, então call-site novo em arquivo novo é pego
por construção.

Fecha **sintaxe**, não determinismo: em `anthropic/*` o `seed` é descartado por
`litellm.drop_params` (`get_supported_openai_params` não o lista para
`claude-sonnet-4-6`), e `seed=None` satisfaz o kwarg sem valer nada. O gate
existe para que um call-site novo não nasça herdando `temperature=0.1` do
`LLMConfig` sem que alguém tenha decidido.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAIZES = ("pipeline", "backend/app")
#: Par que identifica `LLMService.call` — ver assinatura em pipeline/llm/litellm_client.py.
ASSINATURA = ("system_prompt", "output_schema")
EXIGIDOS = ("temperature", "seed")


def _e_call_do_llm_service(no: ast.AST) -> bool:
    if not (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)):
        return False
    if no.func.attr != "call":
        return False
    nomeados = {kw.arg for kw in no.keywords if kw.arg}
    return all(marcador in nomeados for marcador in ASSINATURA)


def _faltantes(chamada: ast.Call) -> list[str]:
    nomeados = {kw.arg for kw in chamada.keywords if kw.arg}
    return [k for k in EXIGIDOS if k not in nomeados]


def _arquivos(raiz: Path):
    for prefixo in RAIZES:
        base = raiz / prefixo
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


def _varre(raiz: Path) -> tuple[list[str], int]:
    achados: list[str] = []
    inspecionados = 0
    for arquivo in _arquivos(raiz):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for no in ast.walk(arvore):
            if not _e_call_do_llm_service(no):
                continue
            inspecionados += 1
            if faltam := _faltantes(no):
                rel = arquivo.relative_to(raiz)
                achados.append(f"{rel}:{no.lineno}: `LLMService.call` sem {', '.join(faltam)}")
    return achados, inspecionados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    achados, inspecionados = _varre(args.root)

    if achados:
        print("\n".join(achados))
        print(
            f"\n✗ {len(achados)} call-site(s) de LLM sem amostragem declarada.\n"
            "  Declare `temperature=` e `seed=` no call-site — sem eles a chamada\n"
            "  herda temperature=0.1 do LLMConfig por omissão, não por decisão.\n"
            "  Constantes: pipeline/llm/deterministic_extraction.py (extração),\n"
            "  pipeline/llm/prompts/parecer_planejador.py (parecer)."
        )
        return 1
    print(f"✓ {inspecionados} call-site(s) de `LLMService.call` declaram temperature + seed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
