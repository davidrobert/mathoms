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

Segunda verificação — **rota alternativa ao choke-point** (A42.l17). A alegação
"call-site novo em arquivo novo é pego por construção" acima era falsa para a
chamada que **não passa** por `LLMService`: o discriminador é a assinatura
`LLMService.call`, que um `client.messages.create(...)` cru nunca carrega, e
`RAIZES` não incluía `scripts/`. Os **dois** sítios de SDK cru do repo viviam
exatamente nessa dupla cegueira, e o hook nem disparava (`files:` sem `scripts/`).
Agora o SDK cru fora de `pipeline/llm/` é ofensor, com resíduo **declarado por
igualdade de conjunto** — arquivo novo falha, e sítio novo em arquivo já
declarado também (a contagem é a tripwire; o gate imprime *quais*).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAIZES = ("pipeline", "backend/app", "scripts")
#: Par que identifica `LLMService.call` — ver assinatura em pipeline/llm/litellm_client.py.
ASSINATURA = ("system_prompt", "output_schema")
EXIGIDOS = ("temperature", "seed")

#: Dono do client do provider. Chamada crua aqui é a implementação do choke-point.
RAIZ_CHOKE_POINT = "pipeline/llm"

#: Resíduo declarado: sítios de SDK cru que já existiam quando o gate nasceu, com
#: a ADR que fecha cada um. NÃO é isenção — a contagem é exata de propósito, para
#: que sítio novo em arquivo já declarado reprove igual a arquivo novo. Entrada que
#: zera (dívida paga) também reprova: registry que sobrevive à dívida apodrece.
RESIDUO_DECLARADO: dict[str, tuple[int, str]] = {
    "scripts/route_documents.py": (2, "ADR-349 Fase 1 (A41.l2)"),
    "scripts/e2/banks/caixa.py": (2, "ADR-349 Fase 2 (A41.l3) — bloco `document`"),
}


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


# Dois eixos juntos: o construtor pega quem abre o client, e `messages.create`
# pega quem o usa mesmo que o client venha de outro módulo.
def _e_sdk_cru(no: ast.AST) -> bool:
    """`anthropic.Anthropic(...)` ou `<x>.messages.create(...)` — provider sem choke-point."""
    if not isinstance(no, ast.Call):
        return False
    func = no.func
    if isinstance(func, ast.Attribute) and func.attr == "Anthropic":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "create":
        interno = func.value
        return isinstance(interno, ast.Attribute) and interno.attr == "messages"
    return False


def _arquivos(raiz: Path):
    for prefixo in RAIZES:
        base = raiz / prefixo
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


def _varre(raiz: Path) -> tuple[list[str], int, dict[str, list[str]]]:
    achados: list[str] = []
    inspecionados = 0
    sdk_cru: dict[str, list[str]] = {}
    for arquivo in _arquivos(raiz):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        rel = arquivo.relative_to(raiz).as_posix()
        for no in ast.walk(arvore):
            if _e_call_do_llm_service(no):
                inspecionados += 1
                if faltam := _faltantes(no):
                    achados.append(f"{rel}:{no.lineno}: `LLMService.call` sem {', '.join(faltam)}")
            elif _e_sdk_cru(no) and not rel.startswith(RAIZ_CHOKE_POINT):
                sdk_cru.setdefault(rel, []).append(f"{rel}:{no.lineno}")
    return achados, inspecionados, sdk_cru


# Imprime *quais* sítios, nunca só quantos: contagem que diverge sem o conjunto ao
# lado manda o próximo leitor procurar no arquivo inteiro. Arquivo declarado que
# não existe na árvore varrida não é dívida paga — é árvore parcial (o caso da
# árvore-espelho dos testes); dívida paga é arquivo presente com zero chamada crua.
def _confere_residuo(sdk_cru: dict[str, list[str]], raiz: Path) -> list[str]:
    """Conjunto medido de SDK cru vs. conjunto declarado, nos dois sentidos."""
    problemas = (
        _julga(rel, sdk_cru.get(rel, []), raiz)
        for rel in sorted(set(sdk_cru) | set(RESIDUO_DECLARADO))
    )
    return [p for p in problemas if p]


def _julga(rel: str, sitios: list[str], raiz: Path) -> str | None:
    """Uma entrada: ofensor não declarado, resíduo vencido, ou contagem divergente."""
    declarado = RESIDUO_DECLARADO.get(rel)
    if declarado is None:
        return (
            f"{rel}: {len(sitios)} chamada(s) crua(s) ao SDK fora de {RAIZ_CHOKE_POINT}/ "
            f"e fora do resíduo declarado — {', '.join(sitios)}"
        )
    esperado, dono = declarado
    if not sitios:
        if not (raiz / rel).is_file():
            return None
        return f"{rel}: resíduo declarado ({dono}) não tem mais chamada crua — dívida paga; remova a entrada de RESIDUO_DECLARADO."
    if len(sitios) != esperado:
        return f"{rel}: resíduo declarado esperava {esperado} chamada(s) crua(s) ({dono}), achou {len(sitios)} — {', '.join(sitios)}"
    return None


_REMEDIO_AMOSTRAGEM = (
    "\n✗ {n} call-site(s) de LLM sem amostragem declarada.\n"
    "  Declare `temperature=` e `seed=` no call-site — sem eles a chamada\n"
    "  herda temperature=0.1 do LLMConfig por omissão, não por decisão.\n"
    "  Constantes: pipeline/llm/deterministic_extraction.py (extração),\n"
    "  pipeline/llm/prompts/parecer_planejador.py (parecer)."
)

_REMEDIO_CHOKE_POINT = (
    "\n✗ {n} divergência(s) na rota alternativa ao choke-point.\n"
    "  Chamada ao SDK do provider mora em pipeline/llm/ — fora dali ela pula\n"
    "  budget (ADR-173), LLMCallLog, cache (ADR-307) e sanitização (ADR-175).\n"
    "  Use `LLMService.call`; se a rota crua for inevitável hoje, declare-a\n"
    "  em RESIDUO_DECLARADO com a ADR que a fecha."
)


def _relata(linhas: list[str], remedio: str) -> None:
    print("\n".join(linhas))
    print(remedio)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    achados, inspecionados, sdk_cru = _varre(args.root)
    residuo = _confere_residuo(sdk_cru, args.root)

    if achados:
        _relata(achados, _REMEDIO_AMOSTRAGEM.format(n=len(achados)))
    if residuo:
        _relata(residuo, _REMEDIO_CHOKE_POINT.format(n=len(residuo)))
    if achados or residuo:
        return 1

    declarados = sum(len(v) for v in sdk_cru.values())
    print(
        f"✓ {inspecionados} call-site(s) de `LLMService.call` declaram temperature + seed; "
        f"{declarados} chamada(s) crua(s) ao SDK, todas em resíduo declarado."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
