#!/usr/bin/env python3
"""Gate: application service não lê chave que o produtor do stage não emite.

Origem: `exposicao_cambial_v2` leu `payload["patrimonio_full"]` por três meses. A chave
é nome de variável interna do domínio; o serializador emite `patrimonio`. O endpoint
devolvia zero em silêncio e o relatório afirmava o oposto da verdade ao usuário.

Nenhum gate existente pegava: o schema só é aplicado no WRITE, `additionalProperties`
é `true` (logo nem um payload com a chave fictícia seria barrado), e a fixture do teste
fabricava o mesmo shape errado — código e teste compartilhavam a crença.

Aqui o eixo é outro: o payload está certo, o LEITOR é que está errado. Mismatch estático
string↔schema, então o instrumento é AST — não depende de fixture rica nem de dogfood
ter dado no eixo medido.

O stage é DECLARADO, nunca inferido: módulo que lê artefato precisa de
``ARTIFACT_CONTRACT = ("<stage>",)`` no topo. Sem declaração, falha fechado. Inferir da
query (`stage_aliases(...)`) quebra quando o alias mora numa variável ou num helper.
Precedente: `dev/check_run_artifact_fk_coverage.py`, que também exige classificação.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIR = REPO_ROOT / "backend" / "app" / "application"
SCHEMAS_DIR = REPO_ROOT / "config" / "schemas"

READER = "read_artifact_content"
CONTRACT = "ARTIFACT_CONTRACT"

# Chaves que o backend ENXERTA no payload depois de ler — não vêm do produtor, logo não
# pertencem ao schema do stage. Enxerto é escrita seguida de leitura no mesmo processo.
ENXERTOS_DO_BACKEND = frozenset({"_report_lineage", "comparisons", "changelog"})


def _schema_por_stage() -> dict[str, str]:
    """Reusa o mapa que o `DBArtifactStore` já aplica no write."""
    sys.path.insert(0, str(REPO_ROOT))
    from backend.app.services.storage.db_artifact_store import SCHEMA_BY_STAGE

    return dict(SCHEMA_BY_STAGE)


def _propriedades(schema_file: str) -> set[str]:
    path = SCHEMAS_DIR / schema_file
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("properties", {}))


def _contrato_declarado(tree: ast.Module) -> list[str] | None:
    """Stages declarados no módulo, ou None se não houver declaração."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        alvos = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if CONTRACT not in alvos:
            continue
        try:
            valor = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            return []
        return [str(v) for v in valor] if isinstance(valor, (list, tuple)) else [str(valor)]
    return None


def _desembrulha(node: ast.expr) -> ast.expr:
    """Tira `dict(...)` e `... or {}` de volta até a chamada de leitura."""
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return _desembrulha(node.values[0])
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        return _desembrulha(node.args[0]) if node.args else node
    return node


def _le_artefato(node: ast.expr) -> bool:
    alvo = _desembrulha(node)
    return isinstance(alvo, ast.Call) and isinstance(alvo.func, ast.Name) and alvo.func.id == READER


def _vars_de_payload(tree: ast.Module) -> set[str]:
    """Variáveis que recebem o conteúdo decriptado de um artefato."""
    nomes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _le_artefato(node.value):
            nomes.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return nomes


def _chave_de_subscript(node: ast.AST, vars_payload: set[str]) -> str | None:
    """`payload["x"]` em leitura. Escrita não conta — enxertar chave é legítimo."""
    if not (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)):
        return None
    if not (isinstance(node.value, ast.Name) and node.value.id in vars_payload):
        return None
    alvo = node.slice
    return alvo.value if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str) else None


def _chave_de_get(node: ast.AST, vars_payload: set[str]) -> str | None:
    """`payload.get("x")`."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    if node.func.attr != "get" or not node.args:
        return None
    if not (isinstance(node.func.value, ast.Name) and node.func.value.id in vars_payload):
        return None
    alvo = node.args[0]
    return alvo.value if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str) else None


def _chaves_lidas(tree: ast.Module, vars_payload: set[str]) -> list[tuple[str, int]]:
    """Chaves literais lidas das variáveis de payload, com a linha de cada leitura."""
    achados: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        for extrator in (_chave_de_subscript, _chave_de_get):
            chave = extrator(node, vars_payload)
            if chave is not None:
                achados.append((chave, node.lineno))
    return achados


def _propriedades_do_contrato(
    stages: list[str], mapa: dict[str, str]
) -> tuple[set[str], list[str]]:
    props: set[str] = set()
    desconhecidos: list[str] = []
    for stage in stages:
        schema = mapa.get(stage)
        if schema is None:
            desconhecidos.append(stage)
            continue
        props |= _propriedades(schema)
    return props, desconhecidos


def _erros_de_chave(
    rel: Path, tree: ast.Module, vars_payload: set[str], stages: list[str], props: set[str]
) -> list[str]:
    erros: list[str] = []
    for chave, linha in _chaves_lidas(tree, vars_payload):
        if chave in props or chave in ENXERTOS_DO_BACKEND:
            continue
        erros.append(
            f"{rel}:{linha}: lê '{chave}', que o produtor de {stages} não emite.\n"
            f"    Corrija o leitor, ou declare a chave em config/schemas/ se o produtor a emite."
        )
    return erros


def _analisa(path: Path, mapa: dict[str, str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    vars_payload = _vars_de_payload(tree)
    if not vars_payload:
        return []
    rel = path.relative_to(REPO_ROOT)
    stages = _contrato_declarado(tree)
    if stages is None:
        return [
            f"{rel}: lê artefato com {READER}() e não declara {CONTRACT}.\n"
            f'    Adicione no topo do módulo: {CONTRACT} = ("<stage>",)'
        ]
    props, desconhecidos = _propriedades_do_contrato(stages, mapa)
    erros = [
        f"{rel}: {CONTRACT} cita stage sem schema em SCHEMA_BY_STAGE: {s}" for s in desconhecidos
    ]
    return erros if not props else erros + _erros_de_chave(rel, tree, vars_payload, stages, props)


def main() -> int:
    mapa = _schema_por_stage()
    erros: list[str] = []
    for path in sorted(SCAN_DIR.rglob("*.py")):
        erros.extend(_analisa(path, mapa))
    if erros:
        print("Chave lida de artefato que o produtor não emite:\n", file=sys.stderr)
        for e in erros:
            print(f"  {e}", file=sys.stderr)
        print(
            "\nO payload está certo; o leitor é que erra. Foi assim que o card de "
            "exposição cambial devolveu zero por três meses.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
