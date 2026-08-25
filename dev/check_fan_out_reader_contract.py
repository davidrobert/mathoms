#!/usr/bin/env python3
"""Stage que lê documento é classificado no denominador declarado (ADR-393 D3/D5).

Três invariantes, todos falhando FECHADO:

1. Todo consumidor do ``DocumentTextExtractor`` está em ``FAN_OUT_STAGES`` ou no
   allowlist de não-stages — stage novo não entra em silêncio.
2. Quem está em ``FAN_OUT_STAGES_TYPED_READER`` usa ``extract_result``; quem está
   no conjunto não-tipado usa ``extract``. Sair da cegueira é MOVER a linha.
3. Os dois conjuntos são disjuntos e nomeiam stages que existem.

O denominador é enumerado de propósito: descobrir por reflexão faria o gate
crescer sozinho e ficar verde no stage novo (ADR-393 D3).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.stage_spec import (  # noqa: E402
    FAN_OUT_STAGES_TYPED_READER,
    FAN_OUT_STAGES_UNTYPED_READER,
    STAGE_REGISTRY,
)

# Consome o extrator mas NÃO é stage de pipeline — não tem fan-out sobre fila de
# documentos, então o contrato de balanço não se aplica. Entrada aqui é decisão
# explícita, com o porquê (ADR-393 §D2 não enumerava este consumidor).
NAO_STAGE_ALLOWLIST: dict[str, str] = {
    "backend/app/services/family_member_pii_service.py": (
        "serviço de backend (preenche CPF a partir de documentos já roteados), "
        "não stage — sem fila de fan-out e sem contrato de retorno de stage"
    ),
}

# Uso REAL: importar a CLASSE ou construí-la. Citar o nome num comentário, ou
# importar só a constante `READABLE_SUFFIXES`, não faz de ninguém consumidor —
# gate que casa prosa fecha sintaxe, não classe.
_USA_EXTRATOR = re.compile(
    r"DocumentTextExtractor\s*\(|^\s*(?:from|import)[^\n]*\bDocumentTextExtractor\b",
    re.MULTILINE,
)

_CHAMA_TIPADO = re.compile(r"\.extract_result\s*\(")
_CHAMA_CRU = re.compile(r"\.extract\s*\(|\.extract_multiple\s*\(")


def _modulos_de_producao():
    """Todo .py sob as três árvores de produção, exceto o próprio extrator."""
    arvores = (REPO / base for base in ("pipeline", "backend/app", "scripts"))
    todos = (f for arvore in arvores for f in sorted(arvore.rglob("*.py")))
    return (f for f in todos if f.name != "text_extractor.py")


def _consumidores() -> dict[str, str]:
    """Arquivo → texto, para todo módulo de produção que USA o extrator."""
    achados: dict[str, str] = {}
    for f in _modulos_de_producao():
        texto = f.read_text(encoding="utf-8")
        if _USA_EXTRATOR.search(texto):
            achados[str(f.relative_to(REPO))] = texto
    return achados


def _erro_do_consumidor(rel: str, texto: str) -> str | None:
    """Uma linha de erro, ou ``None`` quando o módulo está bem classificado."""
    stage = Path(rel).stem
    if stage in FAN_OUT_STAGES_TYPED_READER:
        if _CHAMA_TIPADO.search(texto):
            return None
        return f"{rel}: declarado TIPADO mas não chama `extract_result`"
    if stage in FAN_OUT_STAGES_UNTYPED_READER:
        if not _CHAMA_TIPADO.search(texto) or _CHAMA_CRU.search(texto):
            return None
        return f"{rel}: já usa `extract_result` — mova para FAN_OUT_STAGES_TYPED_READER"
    return (
        f"{rel}: consome DocumentTextExtractor e NÃO está classificado — "
        f"adicione o stage `{stage}` a FAN_OUT_STAGES_TYPED_READER/UNTYPED_READER "
        f"(pipeline/stage_spec.py) ou ao NAO_STAGE_ALLOWLIST deste gate, com o motivo"
    )


def _erros_de_classificacao(consumidores: dict[str, str]) -> list[str]:
    erros = (
        _erro_do_consumidor(rel, texto)
        for rel, texto in consumidores.items()
        if rel not in NAO_STAGE_ALLOWLIST
    )
    return [e for e in erros if e]


def _erros_de_declaracao() -> list[str]:
    erros: list[str] = []
    colisao = FAN_OUT_STAGES_TYPED_READER & FAN_OUT_STAGES_UNTYPED_READER
    if colisao:
        erros.append(f"stage declarado nos DOIS conjuntos: {sorted(colisao)}")
    for stage in sorted(FAN_OUT_STAGES_TYPED_READER | FAN_OUT_STAGES_UNTYPED_READER):
        if stage not in STAGE_REGISTRY:
            erros.append(f"`{stage}` declarado como fan-out mas não existe em STAGE_REGISTRY")
    return erros


def main() -> int:
    consumidores = _consumidores()
    erros = _erros_de_declaracao() + _erros_de_classificacao(consumidores)
    if erros:
        print("Contrato de leitor do fan-out violado (ADR-393 D3):\n")
        for e in erros:
            print(f"  ✗ {e}")
        return 1
    tipados = len(FAN_OUT_STAGES_TYPED_READER)
    total = tipados + len(FAN_OUT_STAGES_UNTYPED_READER)
    print(
        f"OK {len(consumidores)} consumidores do extrator classificados "
        f"({tipados}/{total} stages com leitor tipado; "
        f"{len(NAO_STAGE_ALLOWLIST)} não-stage no allowlist)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
