"""Trava a leniência top-level dos schemas LLM ADR-238/157/239 (design, não bug).

`extra="allow"` no TOP-LEVEL é intencional: o payload precisa sobreviver a
shape novo de PDF sem hard-fail (campo extra é ignorado, não derruba a
extração). Sub-models permanecem `extra="forbid"` para pegar drift de campo
renomeado. Flip top-level para `forbid` só via track W6-T01 sub-PR 3
(PLATFORM_REVIEW) — se este teste quebrou, ou é esse flip deliberado, ou é
regressão acidental de leniência.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import BaseModel

from pipeline.llm.schemas import apolice as apolice_mod
from pipeline.llm.schemas import e16_irpf_full as e16_mod
from pipeline.llm.schemas.apolice import ApolicePayload
from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput
from pipeline.llm.schemas.informe_base import InformeRendimentosBase
from pipeline.llm.schemas.informe_pf import InformeFinanceiroPFPayload
from pipeline.llm.schemas.informe_pj import InformeFinanceiroPJPayload
from pipeline.llm.schemas.informe_previdencia import InformePrevidenciaPayload
from pipeline.llm.schemas.informe_proventos import InformeProventosPayload

_TOP_LEVEL_LENIENT = (IRPFFullOutput, InformeRendimentosBase, ApolicePayload)

_INFORME_SUB_PAYLOADS = (
    InformePrevidenciaPayload,
    InformeFinanceiroPJPayload,
    InformeFinanceiroPFPayload,
    InformeProventosPayload,
)


def _sub_models(module, top_level: type[BaseModel]) -> list[type[BaseModel]]:
    """Modelos Pydantic do módulo que não são o top-level lenient."""
    models = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, BaseModel) or obj is BaseModel:
            continue
        if obj is top_level or issubclass(top_level, obj):
            continue  # exclui o top-level e suas bases (_TopModel)
        models.append(obj)
    return models


@pytest.mark.parametrize("model", _TOP_LEVEL_LENIENT, ids=lambda m: m.__name__)
def test_top_level_schema_is_lenient(model: type[BaseModel]) -> None:
    """Top-level de schema LLM mantém extra='allow' (leniência é design)."""
    assert model.model_config.get("extra") == "allow", (
        f"{model.__name__} deixou de ser lenient no top-level — "
        "flip p/ forbid só via W6-T01 sub-PR 3"
    )


@pytest.mark.parametrize(
    "model",
    _sub_models(e16_mod, IRPFFullOutput) + _sub_models(apolice_mod, ApolicePayload),
    ids=lambda m: m.__name__,
)
def test_e16_and_apolice_sub_models_are_strict(model: type[BaseModel]) -> None:
    """Todo sub-model de e16_irpf_full/apolice mantém extra='forbid'."""
    assert model.model_config.get("extra") == "forbid", (
        f"{model.__name__} deveria ser strict (extra='forbid') — "
        "leniência é privilégio do top-level"
    )


@pytest.mark.parametrize("model", _INFORME_SUB_PAYLOADS, ids=lambda m: m.__name__)
def test_informe_sub_payloads_are_strict(model: type[BaseModel]) -> None:
    """Sub-payloads polimórficos do InformeRendimentosBase mantêm extra='forbid'."""
    assert model.model_config.get("extra") == "forbid"
