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

A40.l25 fechou dois furos medidos:

1. O payload também chega por ``<carrier>.content_json`` — atributo de um snapshot já
   decriptado —, não só por ``read_artifact_content(...)``. `recalibracao_note.py` lia
   o payload E5 assim e por isso NÃO era coberto: ``_vars_de_payload`` voltava vazio e
   ``_analisa`` retornava antes do falha-fechado, então o módulo nunca precisou
   declarar contrato. O gate acreditava cobrir o repo inteiro e não cobria.
2. Chave de BLOCO, não só de topo. A chave morta (`p50_ano_if`) vivia dentro de
   ``if_monte_carlo``, e o rastreio local não a alcança: o bloco é extraído numa função,
   devolvido, e as chaves são lidas de PARÂMETRO em outra. Módulo focado — cujo único
   dict é o bloco — declara ``ARTIFACT_CONTRACT_BLOCO`` e aí toda chave literal lida no
   módulo é checada contra as properties daquele bloco. Opt-in porque a regra é
   grosseira de propósito: só é correta onde não há outro dict para confundir.
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
CONTRACT_BLOCO = "ARTIFACT_CONTRACT_BLOCO"

# Atributo que carrega o payload já decriptado (`AnalyzeFinancesSnapshot.content_json`).
# Também é o nome da coluna crua do `PipelineArtifact`, e o AST não distingue os dois —
# tratar ambos como payload é o lado certo do erro: ler chave da coluna cifrada é um
# defeito pior, e merece o mesmo flag.
ATRIBUTO_PAYLOAD = "content_json"

# Chaves que o backend ENXERTA no payload depois de ler — não vêm do produtor, logo não
# pertencem ao schema do stage. Enxerto é escrita seguida de leitura no mesmo processo.
ENXERTOS_DO_BACKEND = frozenset({"_report_lineage", "comparisons", "changelog"})


# Lê o mapa por AST em vez de importar: o job de Lint roda em env enxuto (sem
# pydantic), e importar `db_artifact_store` puxaria a app inteira. Mesmo motivo do
# `check_run_artifact_fk_coverage.py` — gate barato, sem import.
def _schema_por_stage() -> dict[str, str]:
    """Mapa stage→schema, lido do fonte que o `DBArtifactStore` aplica no write."""
    fonte = REPO_ROOT / "backend" / "app" / "services" / "storage" / "db_artifact_store.py"
    tree = ast.parse(fonte.read_text(encoding="utf-8"))
    for node in tree.body:
        alvo = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign):
            alvo = next((t for t in node.targets if isinstance(t, ast.Name)), None)
        if isinstance(alvo, ast.Name) and alvo.id == "SCHEMA_BY_STAGE" and node.value:
            return {str(k): str(v) for k, v in ast.literal_eval(node.value).items()}
    raise SystemExit(f"SCHEMA_BY_STAGE não encontrado em {fonte}")


def _schema_json(schema_file: str) -> dict:
    path = SCHEMAS_DIR / schema_file
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _propriedades(schema_file: str) -> set[str]:
    return set(_schema_json(schema_file).get("properties", {}))


def _propriedades_do_bloco(schema_file: str, bloco: str) -> set[str]:
    """Properties de UM bloco de topo; vazio se o bloco não as declara."""
    # Bloco `object` sem `properties` devolve vazio, e o chamador degrada para só o
    # topo: checar contra conjunto vazio reprovaria toda chave e o gate viraria ruído.
    sub = _schema_json(schema_file).get("properties", {}).get(bloco) or {}
    return set(sub.get("properties", {}))


def _valor_declarado(tree: ast.Module, nome: str):
    """Valor literal de uma constante de módulo, ou ``None`` se não declarada."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if nome not in [t.id for t in node.targets if isinstance(t, ast.Name)]:
            continue
        try:
            return ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            return ""
    return None


def _contrato_declarado(tree: ast.Module) -> list[str] | None:
    """Stages declarados no módulo, ou None se não houver declaração."""
    valor = _valor_declarado(tree, CONTRACT)
    if valor is None:
        return None
    if valor == "":
        return []
    return [str(v) for v in valor] if isinstance(valor, (list, tuple)) else [str(valor)]


def _bloco_declarado(tree: ast.Module) -> str | None:
    """Bloco de topo ao qual o módulo se declara focado (modo estrito)."""
    valor = _valor_declarado(tree, CONTRACT_BLOCO)
    return str(valor) if isinstance(valor, str) and valor else None


def _desembrulha(node: ast.expr) -> ast.expr:
    """Tira `dict(...)` e `... or {}` de volta até a chamada de leitura."""
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return _desembrulha(node.values[0])
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
        return _desembrulha(node.args[0]) if node.args else node
    return node


def _le_artefato(node: ast.expr) -> bool:
    """Expressão que produz o payload: a chamada do reader, ou `<carrier>.content_json`."""
    alvo = _desembrulha(node)
    if isinstance(alvo, ast.Attribute) and alvo.attr == ATRIBUTO_PAYLOAD:
        return True
    return isinstance(alvo, ast.Call) and isinstance(alvo.func, ast.Name) and alvo.func.id == READER


def _vars_de_payload(tree: ast.Module) -> set[str]:
    """Variáveis que recebem o conteúdo decriptado de um artefato."""
    nomes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _le_artefato(node.value):
            nomes.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return nomes


def _e_alvo_de_leitura(node: ast.expr, vars_payload: set[str] | None) -> bool:
    """Alvo cujas chaves são checadas. ``None`` = modo estrito: qualquer nome."""
    if _le_artefato(node):
        return True
    # Desembrulha antes de exigir `Name`: `(bloco or {}).get("x")` é BoolOp na
    # superfície, e sem isto o gate não vê a forma mais comum de leitura defensiva
    # — foi o que deixou `p50_ano_if` passar mesmo com o módulo declarado.
    alvo = _desembrulha(node)
    if not isinstance(alvo, ast.Name):
        return False
    return vars_payload is None or alvo.id in vars_payload


def _chave_de_subscript(node: ast.AST, vars_payload: set[str] | None) -> str | None:
    """`payload["x"]` em leitura. Escrita não conta — enxertar chave é legítimo."""
    if not (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)):
        return None
    if not _e_alvo_de_leitura(node.value, vars_payload):
        return None
    alvo = node.slice
    return alvo.value if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str) else None


def _chave_de_get(node: ast.AST, vars_payload: set[str] | None) -> str | None:
    """`payload.get("x")`."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    if node.func.attr != "get" or not node.args:
        return None
    if not _e_alvo_de_leitura(node.func.value, vars_payload):
        return None
    alvo = node.args[0]
    return alvo.value if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str) else None


def _chaves_lidas(tree: ast.Module, vars_payload: set[str] | None) -> list[tuple[str, int]]:
    """Chaves literais lidas das variáveis de payload, com a linha de cada leitura."""
    achados: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        for extrator in (_chave_de_subscript, _chave_de_get):
            chave = extrator(node, vars_payload)
            if chave is not None:
                achados.append((chave, node.lineno))
    return achados


def _propriedades_do_contrato(
    stages: list[str], mapa: dict[str, str], bloco: str | None
) -> tuple[set[str], list[str]]:
    props: set[str] = set()
    desconhecidos: list[str] = []
    for stage in stages:
        schema = mapa.get(stage)
        if schema is None:
            desconhecidos.append(stage)
            continue
        props |= _propriedades(schema)
        if bloco is not None:
            props |= _propriedades_do_bloco(schema, bloco)
    return props, desconhecidos


def _erros_de_chave(
    rel: Path, tree: ast.Module, alvos: set[str] | None, stages: list[str], props: set[str]
) -> list[str]:
    erros: list[str] = []
    for chave, linha in _chaves_lidas(tree, alvos):
        if chave in props or chave in ENXERTOS_DO_BACKEND:
            continue
        erros.append(
            f"{rel}:{linha}: lê '{chave}', que o produtor de {stages} não emite.\n"
            f"    Corrija o leitor, ou declare a chave em config/schemas/ se o produtor a emite."
        )
    return erros


def _le_payload(tree: ast.Module) -> bool:
    """Módulo toca payload de artefato — por variável ou por expressão inline."""
    # A expressão inline (`(snap.content_json or {}).get("bloco")`) não passa por
    # variável, e era por isso que `recalibracao_note.py` escapava do falha-fechado.
    return bool(_vars_de_payload(tree)) or any(
        _le_artefato(n.func.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
    )


def _erro_sem_contrato(rel: Path) -> list[str]:
    return [
        f"{rel}: lê payload de artefato ({READER}() ou .{ATRIBUTO_PAYLOAD}) "
        f"e não declara {CONTRACT}.\n"
        f'    Adicione no topo do módulo: {CONTRACT} = ("<stage>",)'
    ]


def _analisa(path: Path, mapa: dict[str, str]) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    if not _le_payload(tree):
        return []
    rel = path.relative_to(REPO_ROOT)
    stages = _contrato_declarado(tree)
    if stages is None:
        return _erro_sem_contrato(rel)
    bloco = _bloco_declarado(tree)
    props, desconhecidos = _propriedades_do_contrato(stages, mapa, bloco)
    erros = [
        f"{rel}: {CONTRACT} cita stage sem schema em SCHEMA_BY_STAGE: {s}" for s in desconhecidos
    ]
    # Modo estrito: o módulo se declarou focado num bloco, então TODA chave literal
    # lida nele é checada — inclusive de parâmetro, que o rastreio por variável não vê.
    alvos = None if bloco is not None else _vars_de_payload(tree)
    return erros if not props else erros + _erros_de_chave(rel, tree, alvos, stages, props)


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
