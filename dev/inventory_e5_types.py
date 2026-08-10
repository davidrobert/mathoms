#!/usr/bin/env python3
"""Inventário de tipos do payload E5, PRÉ-normalização (A40.l5 · PR0)."""
# Existe porque a fonte óbvia de tipo é a errada. `backend/tests/snapshots/
# dogfood_view_model.json` passa por `_normalize`, que converte monetário em
# cents `int` e float não-monetário em STRING quantizada — quem tipar lendo o
# snapshot escreve `type: "string"` onde o wire tem `number`, e cria a classe da
# l5 na dimensão TIPO em vez de NOME (co-design `data-engineer`, 2026-08-10).
#
# A fonte correta é o produtor. Este script roda `categorize_transactions` +
# `analyze_finances` sobre as fixtures sintéticas do golden e caminha o dict
# CRU, registrando o tipo Python de cada folha.
#
# PII: emite só dot-path, nome de tipo e contagem — nunca valor. As fixtures são
# sintéticas (PII-zero por construção, A23.l2). Os 55 artefatos E5 reais do DB
# local ficam FORA: `content_json` é cifrado e a chave do vault é credencial.

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA = REPO_ROOT / "config" / "schemas" / "e5_analysis.schema.json"

Folhas = dict[str, set[str]]


# `int` e `float` NÃO se colapsam: o codegen emite `number` para os dois, mas
# saber qual é decide `required` e nulabilidade no schema.
def _tipo(v: Any) -> str:
    """Nome do tipo Python da folha."""
    return type(v).__name__


# Lista de listas é TUPLA POSICIONAL (o cone é `(ano, valor)`). Colapsar as
# posições reportava "float e int" como se o produtor fosse inconsistente — o ano
# é int e o valor é float, as duas coisas certas no mesmo path.
def _walk_tupla(item: list, prefix: str, out: Folhas) -> None:
    """Cada posição do par ganha path próprio (`[][0]`, `[][1]`)."""
    for i, pos in enumerate(item):
        _walk(pos, f"{prefix}[][{i}]", out)


def _walk_lista(node: list, prefix: str, out: Folhas) -> None:
    out[f"{prefix}[]"].add("list" if not node else "")
    for item in node[:50]:
        if isinstance(item, list):
            _walk_tupla(item, prefix, out)
        else:
            _walk(item, f"{prefix}[]", out)


def _walk(node: Any, prefix: str, out: Folhas) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _walk(v, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(node, list):
        _walk_lista(node, prefix, out)
    else:
        out[prefix].add(_tipo(node))


def _blocos_opacos(schema: dict) -> tuple[set[str], set[str]]:
    """(objetos sem `properties`/`patternProperties`, arrays sem `items`)."""
    props = schema.get("properties", {})
    objetos = {
        k
        for k, v in props.items()
        if v.get("type") == "object" and not (v.get("properties") or v.get("patternProperties"))
    }
    arrays = {k for k, v in props.items() if v.get("type") == "array" and not v.get("items")}
    return objetos, arrays


def _roda_cenario(g: Any, nome: str, e3: Path, baseline: Path | None) -> dict | None:
    """Executa E4+E5 num tenant isolado e devolve o payload E5 cru."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    raiz = Path(tempfile.mkdtemp(prefix=f"e5inv-{nome}-"))
    try:
        g._write_e5_config(raiz)
        ctx = g._new_e5_ctx(raiz, e3_fixture=e3, baseline=baseline)
        e4_mws(ctx)
        e5_mws(ctx)
        return ctx.artifact_store.read("E5", "analise_financeira")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)


# Os nomes das fixtures são referenciados DIRETO, sem `getattr(..., None)`: com
# default silencioso o 2º cenário virava cópia do 1º e o relatório dizia
# "3 cenários" sobre 1 amostra. Fixture que desaparecer quebra o script.
def _cenarios() -> list[tuple[str, dict]]:
    """Payloads E5 crus, um por cenário do golden de execução."""
    import tests.test_e5_golden_execution as g

    combos = [
        ("minimal", g._E3_FIXTURE, None),
        ("baseline_min", g._E3_FIXTURE, g._BASELINE_MIN),
        ("baseline_divergente", g._E3_FIXTURE, g._BASELINE_DIVERGENT),
    ]
    saida = [(nome, _roda_cenario(g, nome, e3, base)) for nome, e3, base in combos]
    return [(nome, p) for nome, p in saida if p]


def _agrega(payloads: list[tuple[str, dict]]) -> tuple[Folhas, dict[str, int]]:
    folhas: Folhas = defaultdict(set)
    presenca: dict[str, int] = defaultdict(int)
    for _nome, p in payloads:
        _walk(p, "", folhas)
        for topo in p:
            presenca[topo] += 1
    return folhas, presenca


def _linha_bloco(bloco: str, eh_array: bool, folhas: Folhas, presenca: dict, total: int) -> str:
    sufixo = "[]" if eh_array else ""
    chaves = [k for k in folhas if k == bloco + sufixo or k.startswith(bloco + ".")]
    tipos = sorted({t for k in chaves for t in folhas[k] if t})
    rotulo = f"`{bloco}`{' (array)' if eh_array else ''}"
    return (
        f"| {rotulo} | {presenca.get(bloco, 0)}/{total} | {len(chaves)} "
        f"| {', '.join(tipos) or '—'} |"
    )


def _secao_ambiguas(folhas: Folhas) -> list[str]:
    ambiguas = sorted(k for k, ts in folhas.items() if len({t for t in ts if t}) > 1)
    cabeca = [
        "",
        "## Folhas com MAIS DE UM tipo entre cenários",
        "",
        "Cada uma é decisão de contrato: união no schema, ou produtor inconsistente.",
        "",
    ]
    corpo = [f"- `{k}` → {', '.join(sorted(t for t in folhas[k] if t))}" for k in ambiguas]
    return cabeca + (corpo or ["- (nenhuma)"])


def _relatorio(payloads: list[tuple[str, dict]], schema: dict) -> str:
    objetos, arrays = _blocos_opacos(schema)
    folhas, presenca = _agrega(payloads)
    total = len(payloads)
    linhas = [
        "# Inventário de tipos do E5 — PRÉ-normalização (A40.l5 PR0)",
        "",
        f"Cenários executados: {total} ({', '.join(n for n, _ in payloads)})",
        f"Blocos de topo observados: {len(presenca)}",
        f"Objetos opacos no schema: {len(objetos)} · arrays sem `items`: {len(arrays)}",
        "",
        "## Blocos opacos, com os tipos que o produtor de fato emite",
        "",
        "| bloco | presença | folhas | tipos observados |",
        "|---|---|---|---|",
    ]
    linhas += [
        _linha_bloco(b, b in arrays, folhas, presenca, total) for b in sorted(objetos | arrays)
    ]
    return "\n".join(linhas + _secao_ambiguas(folhas)) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, help="grava o relatório (default: stdout)")
    args = ap.parse_args()

    payloads = _cenarios()
    if not payloads:
        print("nenhum payload E5 produzido — o golden mudou de forma", file=sys.stderr)
        return 1

    texto = _relatorio(payloads, json.loads(SCHEMA.read_text(encoding="utf-8")))
    if args.out:
        args.out.write_text(texto, encoding="utf-8")
        print(f"✓ {args.out}")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
