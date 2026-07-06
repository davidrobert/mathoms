#!/usr/bin/env python3
"""Deriva o snapshot OpenAPI 3.0 do 3.1 para o oapi-codegen (F1 GO_SHELL).

O oapi-codegen não suporta 3.1 (issue #373): `anyOf: [T, {type: null}]`
quebra a geração. Este conversor é determinístico e cobre APENAS os padrões
que o FastAPI emite no snapshot do pipeline-service: rebaixa `openapi` para
3.0.3 e reescreve `anyOf` com `{type: "null"}` como `nullable: true`.
O 3.0 é artefato DERIVADO — fonte de verdade continua o 3.1 (#747);
`tests/test_openapi_30_derived_sync.py` falha se dessincronizar.

Uso: python3 dev/convert_openapi_31_to_30.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "docs" / "reference" / "api" / "v1" / "pipeline-service.openapi.json"
DST = REPO_ROOT / "docs" / "reference" / "api" / "v1" / "pipeline-service.openapi.3_0.json"


def _convert_anyof_null(schema: dict) -> dict:
    any_of = schema.get("anyOf")
    if not any_of:
        return schema
    non_null = [s for s in any_of if s != {"type": "null"}]
    if len(non_null) == len(any_of):
        return schema
    if len(non_null) == 1:
        merged = {k: v for k, v in schema.items() if k != "anyOf"}
        merged.update(non_null[0])
        merged["nullable"] = True
        return merged
    schema = dict(schema)
    schema["anyOf"] = non_null
    schema["nullable"] = True
    return schema


def _walk(node):
    if isinstance(node, dict):
        node = _convert_anyof_null(node)
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    return node


def convert() -> str:
    spec = json.loads(SRC.read_text(encoding="utf-8"))
    spec = _walk(spec)
    spec["openapi"] = "3.0.3"
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Falha se DST está dessincronizado.")
    args = parser.parse_args()
    rendered = convert()
    if args.check:
        if not DST.exists() or DST.read_text(encoding="utf-8") != rendered:
            print(f"✗ {DST.name} dessincronizado — rode python3 dev/convert_openapi_31_to_30.py")
            return 1
        print(f"✓ {DST.name} em sync")
        return 0
    DST.write_text(rendered, encoding="utf-8")
    print(f"✓ escrito {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
