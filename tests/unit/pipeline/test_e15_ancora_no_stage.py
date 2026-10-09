"""A âncora da ficha no stage E1.5a de verdade — full, incremental e idempotência ([[ADR-440]] D4)."""

# O parser tem teste próprio; aqui o que se prova é o ELO: o artefato gravado e o agregado
# que o E1.5c lê carregam a âncora, e o incremental cura o artefato antigo sem chamar o LLM.

from __future__ import annotations

import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.stages.extract_baseline import _output_to_baseline_json, run  # noqa: E402
from pipeline.stages.ficha_imovel_parser import ANCORA_VERSAO  # noqa: E402
from tests._llm_stage_fixtures import (  # noqa: E402
    make_e15_output,
    make_llm_call_result,
    make_llm_ctx,
)

_KEY = "irpfdeclaracao_2024"
_CLIENTE = "pipeline.llm.litellm_client.LLMService"
_FICHA = (
    "01 11 APARTAMENTO SAO PAULO 500.000,00 500.000,00\n105 - BRASIL\n"
    "Inscrição Municipal (IPTU): 1234567\nLogradouro: RUA ALFA Nº: 100\n"
    "Comp.: APTO 1 Bairro: CENTRO\nMatrícula: 54321 DE REGISTRO\n"
)


def _texto(*fichas: str) -> str:
    return "DECLARAÇÃO DE BENS E DIREITOS\n" + "".join(fichas) + "DÍVIDAS E ÔNUS REAIS\n"


def _ctx(tmp_path: Path, *, incremental: bool = False):
    ctx = make_llm_ctx(tmp_path)
    irpf = tmp_path / "data" / "income_tax_br"
    irpf.mkdir(parents=True)
    (irpf / f"{_KEY}.pdf").write_text("x")
    ctx.incremental = incremental
    return ctx


def _rodar(ctx, texto: str):
    """Roda o stage com leitor de texto e LLM dublados; devolve (resultado, mock da chamada)."""
    with ExitStack() as pilha:
        pilha.enter_context(
            patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract", return_value=texto)
        )
        pilha.enter_context(patch(f"{_CLIENTE}._ensure_client"))
        resultado = make_llm_call_result(make_e15_output())
        chamada = pilha.enter_context(patch(f"{_CLIENTE}.call", return_value=resultado))
        pilha.enter_context(patch("pipeline.incremental.filter_to_incremental", return_value=[]))
        return run(ctx), chamada


def _artefato_antigo(ctx) -> dict:
    payload = _output_to_baseline_json(make_e15_output())
    payload["prompt_version"] = "1.4.1"
    ctx.get_artifact_store().write("E1.5a", _KEY, payload)
    return payload


def test_full_grava_a_ancora_no_artefato_e_no_agregado(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path)
    _rodar(ctx, _texto(_FICHA))
    store = ctx.get_artifact_store()
    artefato = store.read("E1.5a", _KEY)
    agregado = store.read("extract_baseline", "baseline_patrimonial")
    assert artefato["ancora_versao"] == ANCORA_VERSAO
    assert artefato["itens"][0]["ancora_imovel"]["logradouro"] == "RUA ALFA"
    assert agregado["itens"][0]["ancora_imovel"] == artefato["itens"][0]["ancora_imovel"]


def test_full_ambiguo_vira_review_reason_no_bloco_validation(tmp_path: Path) -> None:
    resultado, _ = _rodar(_ctx(tmp_path), _texto(_FICHA, _FICHA))
    codes = [r["code"] for r in resultado["validation"]["review_reasons"]]
    assert codes == ["extract.ancora_imovel_ambigua"]


def test_incremental_sem_doc_novo_cura_o_artefato_antigo_sem_llm(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, incremental=True)
    _artefato_antigo(ctx)
    resultado, chamada = _rodar(ctx, _texto(_FICHA))
    store = ctx.get_artifact_store()
    assert (resultado["skipped"], resultado["reancorados"], chamada.call_count) == (True, 1, 0)
    assert store.read("E1.5a", _KEY)["prompt_version"] == "1.4.1"
    assert "ancora_imovel" in store.read("extract_baseline", "baseline_patrimonial")["itens"][0]


def test_segundo_run_incremental_nao_regrava_nada(tmp_path: Path) -> None:
    ctx = _ctx(tmp_path, incremental=True)
    _artefato_antigo(ctx)
    _rodar(ctx, _texto(_FICHA))
    store = ctx.get_artifact_store()
    with patch.object(store, "write", wraps=store.write) as escrita:
        resultado, _ = _rodar(ctx, _texto(_FICHA))
    assert (resultado["reancorados"], escrita.call_count) == (0, 0)


@pytest.mark.parametrize(("texto", "versao"), [("", 2), (_texto(_FICHA), 1)])
def test_texto_vazio_ou_payload_v1_nao_toca_o_artefato(tmp_path: Path, texto, versao) -> None:
    """Falha de leitura não apaga âncora boa; payload v1 só se lê, nunca se regrava."""
    ctx = _ctx(tmp_path, incremental=True)
    antigo = _artefato_antigo(ctx)
    antigo["payload_version"] = versao
    ctx.get_artifact_store().write("E1.5a", _KEY, antigo)
    resultado, _ = _rodar(ctx, texto)
    assert resultado["reancorados"] == 0
    assert "ancora_versao" not in ctx.get_artifact_store().read("E1.5a", _KEY)
