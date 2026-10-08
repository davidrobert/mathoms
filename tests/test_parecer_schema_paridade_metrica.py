"""Todo `Literal` de `Metrica` tem a mesma extensão no JSON schema do artefato.

O schema é cópia manual do modelo e nada as ligava: `imobilizacao_patrimonial` entrou em
`METRICA_KEYS` pela [[A40.l95]] (#1924) e o enum do `$defs/metrica` ficou em 13 chaves.
Nenhum teste reprovou porque nenhum emite essa chave — o golden valida contra o schema
só o que a fixture carrega. A paridade é por IGUALDADE de conjunto, não por pertinência:
pertinência aprovaria o schema mais estreito que o modelo, que é exatamente o drift.

O que este teste NÃO pega: campo novo de `Metrica` sem `Literal` (string livre) e
`Literal` aninhado dentro de submodelo — a introspecção desce só por `Union`/`Optional`.
"""

from __future__ import annotations

import functools
import json
import typing
from pathlib import Path

import pytest

from pipeline.llm.schemas.parecer_planejador import Metrica

_SCHEMA = (
    Path(__file__).resolve().parents[1] / "config" / "schemas" / "parecer_planejador.schema.json"
)


def _membros_literal(anotacao) -> set[str]:
    if typing.get_origin(anotacao) is typing.Literal:
        return {a for a in typing.get_args(anotacao) if a is not None}
    membros: set[str] = set()
    for arg in typing.get_args(anotacao):
        membros |= _membros_literal(arg)
    return membros


@functools.lru_cache(maxsize=1)
def _campos_literal() -> dict[str, set[str]]:
    campos = {nome: _membros_literal(f.annotation) for nome, f in Metrica.model_fields.items()}
    return {nome: membros for nome, membros in campos.items() if membros}


def _enum_do_schema(no: dict, defs: dict) -> set[str]:
    if "$ref" in no:
        return _enum_do_schema(defs[no["$ref"].rsplit("/", 1)[-1]], defs)
    if "enum" in no:
        return {v for v in no["enum"] if v is not None}
    membros: set[str] = set()
    for chave in ("anyOf", "oneOf"):
        for ramo in no.get(chave, ()):
            membros |= _enum_do_schema(ramo, defs)
    return membros


@functools.lru_cache(maxsize=1)
def _schema_da_metrica() -> tuple[dict, dict]:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return schema["$defs"]["metrica"]["properties"], schema["$defs"]


# Sem este piso o gate fica verde comparando vazio com vazio: um extrator que deixe de
# enxergar o `Literal` (wrapper novo do Pydantic, `Annotated` a mais) devolve `{}`.
def test_introspeccao_enxerga_os_literais_conhecidos():
    assert {"metrica_key", "frequencia_revisao", "section_id", "tema_canonico"} <= set(
        _campos_literal()
    )


@pytest.mark.parametrize("campo", sorted(_campos_literal()))
def test_literal_da_metrica_e_o_enum_do_schema_sao_o_mesmo_conjunto(campo):
    propriedades, defs = _schema_da_metrica()
    no_schema = _enum_do_schema(propriedades[campo], defs)
    no_modelo = _campos_literal()[campo]

    assert no_modelo == no_schema, (
        f"`Metrica.{campo}` e o schema divergem — só no modelo: "
        f"{sorted(no_modelo - no_schema)}; só no schema: {sorted(no_schema - no_modelo)}"
    )
