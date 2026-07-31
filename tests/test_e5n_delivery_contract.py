"""Contrato de ENTREGA das narrativas E5.N (A40.l4 · ADR-356).

Este teste é o lado Python de um par sobre **uma fixture compartilhada**:

    tests/fixtures/narrativas/e5n_delivery.json

O lado TS (`frontend/tests/components/report/sectionSummaryDelivery.test.tsx`)
lê o MESMO arquivo e assere no DOM a string exata de cada seção. Se o produtor
mudar chave, shape ou copy, este teste falha (fixture desatualizada) **e** o TS
falha (texto ausente) — um arquivo, dois leitores.

A fixture é GERADA pelo produtor, nunca escrita à mão: fixture escrita à mão
pode descrever um mundo que o produtor não emite (lição da A40.l3). Para
regravar após mudança legítima de copy::

    MATHOMS_UPDATE_NARRATIVAS_FIXTURE=1 \\
      .venv/bin/python -m pytest tests/test_e5n_delivery_contract.py -q

Família sintética (Alex/Bia): o produtor interpola **primeiro nome** em ``s3`` e
em ``perfil_familia`` — a fixture não pode carregar PII. Nome completo, CPF e
endereço não chegam a texto entregue nenhum (ADR-356 §D9, guarda em
``tests/test_e5n_pii_guard.py``).

O substrato é a fixture sintética PII-zero do dogfood (``run_dogfood_pipeline_ctx``,
A23.l2) — com valores não-triviais. A primeira versão rodava sobre o E3 mínimo de
1 transação de R$ 100 e a fixture nascia financeiramente vazia: sentinela de
FORMA, não de CONTEÚDO (com todo monetário em zero, trocar a fonte de um número
por outra não move a string).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.test_e5n_golden_execution import _build_e5_workspace

_REPO = Path(__file__).resolve().parents[1]
_FIXTURE = _REPO / "tests" / "fixtures" / "narrativas" / "e5n_delivery.json"
_DESTINATIONS = _REPO / "tests" / "fixtures" / "narrativas" / "e5n_destinations.json"
_LAYOUT_YAML = _REPO / "config" / "report_layout.yaml"
_UPDATE_ENV = "MATHOMS_UPDATE_NARRATIVAS_FIXTURE"

_FAMILY: dict[str, Any] = {
    "titular": "alex",
    "endereco": {},
    "membros": {
        "alex": {
            "papel": "titular",
            "nome_curto": "Alex",
            "data_nascimento": "1985-06-15",
            "regime": "PJ Simples",
        },
        "bia": {
            "papel": "conjuge",
            "nome_curto": "Bia",
            "data_nascimento": "1987-03-20",
            "regime": "CLT",
        },
    },
}

# GoalsBundle sintético: cobre os 7 destinos declarados no layout (riscos para
# o s9 sair do empty-state, tributário para o s8 citar regime, metas para
# s6/s7/s10 citarem parâmetro).
_GOALS: dict[str, Any] = {
    "independencia_financeira": {
        "if_meta": 5_000_000.0,
        "trs_pct": 4.0,
        "taxa_retirada_segura_pct": 4.0,
        "renda_passiva_meta_mensal": 16_000.0,
    },
    "aportes": {"meta_aporte_mensal": 20_000.0},
    "dolarizacao": {"meta_usd": 100_000.0, "aporte_mensal_brl": 2_000.0},
    "seguros": {"vida_term_minimo": 2_000_000, "vida_term_maximo": 4_000_000},
    # Shape REAL de `bundle["tributario"]` (pipeline_adapter `_assemble_tributario_section`):
    # `regime` + `regime_label` + `contador_nome` + `holding_prazo_meses`. Não
    # tem `contador_mensal` — o `get(..., 0)` legado publicava "R$ 0,00/mês".
    "tributario": {
        "regime": "simples",
        "regime_label": "Simples Nacional — Anexo III",
        "contador_nome": "Escritório contábil da PJ",
        "holding_prazo_meses": 12,
    },
    "risks_projection": [
        {
            "name": "Cobertura de vida abaixo do recomendado",
            "probability": "média",
            "impact_level": "alto",
        },
        {
            "name": "Sucessão sem inventário planejado",
            "probability": "baixa",
            "impact_level": "alto",
        },
    ],
    "top5_decisoes_projection": [
        {"title": "Iniciar aporte mensal recorrente"},
        {"title": "Contratar seguro de vida term"},
        {"title": "Consolidar reserva de emergência"},
        {"title": "Revisar alocação em renda variável"},
    ],
}


def _write_goals(root: Path) -> None:
    (root / "config" / "goals.json").write_text(
        json.dumps(_GOALS, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# Substrato = fixture sintética PII-zero do dogfood (A23.l2), não o E3 mínimo de
# 1 transação de R$ 100. Com o E3 mínimo a fixture saía financeiramente VAZIA
# (`s1` com quatro `R$ 0,00`, `s2` com "0 meses", `s3`/`s5` zerados): sentinela de
# FORMA funcionava, de CONTEÚDO não — copy podia trocar `patrimonio_bruto` por
# `patrimonio_liquido` e a string exata continuava batendo, porque os dois eram
# zero. O dogfood traz imóvel, CDB em dois anos, financiamento e dois extratos,
# então os números impressos são distintos entre si.
def _run_dogfood(root: Path):
    """E1.5c→E3→E4→E5 sobre a fixture sintética do dogfood; devolve o ctx."""
    from tests.pipeline_golden_substrate import load_fixture, run_dogfood_pipeline_ctx

    dogfood = _REPO / "tests" / "fixtures" / "pipeline_golden" / "dogfood"
    return run_dogfood_pipeline_ctx(
        root,
        raw_baseline=load_fixture(dogfood / "baseline-1.5.json"),
        e2_extracts={
            key: load_fixture(dogfood / f"{key}-2_extract.json")
            for key in ("extrato-a", "extrato-b")
        },
    )


def _run_e5n(root: Path) -> dict[str, Any]:
    """E1.5c→E3→E4→E5→E5.N reais (sem LLM, sem API key) e devolve ``narrativas``."""
    from scripts.generate_narratives import _init_config as e5n_init
    from scripts.generate_narratives import main_with_store as e5n_mws

    ctx = _run_dogfood(root)
    e5n_init(root)
    e5n_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")
    assert payload is not None, "E5.N não persistiu o payload"
    narrativas = payload.get("narrativas")
    assert isinstance(narrativas, dict), "payload E5 sem bloco `narrativas`"
    return narrativas


def _serialize(narrativas: dict[str, Any]) -> str:
    return json.dumps(narrativas, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


# ``summary: true`` faz parte do predicado: destino declarado numa seção que não
# monta ``<SectionSummary>`` é texto gerado e nunca exibido. A correspondência
# flag ⟺ render site é enforçada pela regra 6 de
# ``dev/check_chart_conclusion_parity.py``.
def _layout_destinations() -> dict[str, str]:
    """``{section_id: summary_source}`` das entradas que renderizam parágrafo."""
    layout = yaml.safe_load(_LAYOUT_YAML.read_text(encoding="utf-8"))
    estrategico = layout["estrategico"]
    entries = [*estrategico["sections"], *estrategico.get("appendices", [])]
    return {
        e["id"]: e["summary_source"]
        for e in entries
        if e.get("enabled") and e.get("summary") and e.get("summary_source")
    }


def _expected_destinations() -> dict[str, str]:
    """Mapa ESPERADO, declarado fora do layout (ver `e5n_destinations.json`)."""
    decl = json.loads(_DESTINATIONS.read_text(encoding="utf-8"))
    return {sid: spec["key"] for sid, spec in decl["destinations"].items()}


def _expected_orphans() -> dict[str, str]:
    return dict(json.loads(_DESTINATIONS.read_text(encoding="utf-8"))["orphans"])


@pytest.fixture(scope="module")
def narrativas(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Narrativas geradas na CONDIÇÃO DE PRODUÇÃO (sem ``parametros_fiscais.json``)."""
    # `_build_e5_workspace` copia o arquivo fiscal legado; em produção ele não
    # existe (migrou para a tabela `fiscal_parameters` em A7.2b e é path
    # proibido no git). Gerar a fixture com ele fazia a guarda testar um ramo
    # que produção nunca toma — o falso-verde de escopo da A40.l3.
    root = _build_e5_workspace(tmp_path_factory.mktemp("e5n_delivery"), _FAMILY)
    (root / "config" / "parametros_fiscais.json").unlink(missing_ok=True)
    _write_goals(root)
    return _run_e5n(root)


def test_fixture_matches_producer(narrativas: dict[str, Any]) -> None:
    """A fixture compartilhada é byte-a-byte o que o produtor emite."""
    if os.getenv(_UPDATE_ENV) == "1":
        _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        _FIXTURE.write_text(_serialize(narrativas), encoding="utf-8")
        pytest.skip(f"fixture regravada em {_FIXTURE.relative_to(_REPO)}")
    assert (
        _FIXTURE.exists()
    ), f"fixture ausente — gere com {_UPDATE_ENV}=1 pytest {Path(__file__).name}"
    assert narrativas == json.loads(_FIXTURE.read_text(encoding="utf-8")), (
        "produtor divergiu da fixture compartilhada. Se a mudança de copy é "
        f"intencional, regrave com {_UPDATE_ENV}=1 e rode o teste TS "
        "(sectionSummaryDelivery) no mesmo PR — ele assere as mesmas strings "
        "no DOM."
    )


# A fixture só é sentinela de CONTEÚDO se tiver conteúdo. Com todo monetário em
# R$ 0,00 (o que o E3 mínimo produzia), trocar a fonte de um número por outra
# mantém a string idêntica e o par TS+Python fica verde sobre nada. Este teste
# impede a volta silenciosa a um substrato pobre.
_VALOR_RE = re.compile(r"R\$ [\d.,]+[kM]?")
_MINIMO_VALORES_DISTINTOS = 6


def test_fixture_tem_conteudo_financeiro_nao_trivial(narrativas: dict[str, Any]) -> None:
    """Os destinos entregues citam valores monetários distintos e não-zero."""
    entregues = " ".join(narrativas["summaries"][key] for key in _layout_destinations().values())
    valores = {v for v in _VALOR_RE.findall(entregues) if v != "R$ 0,00"}
    assert len(valores) >= _MINIMO_VALORES_DISTINTOS, (
        f"fixture com só {len(valores)} valores monetários distintos "
        f"({sorted(valores)}) — substrato pobre devolve a guarda ao regime de "
        "FORMA. Gere com `run_dogfood_pipeline_ctx`, não com o E3 mínimo."
    )


# Shape nomeado para a divergência ter nome: se alguém emitir
# ``{context, conclusion}`` aqui, `validate_narrativas` PASSA (``not {...}`` é
# ``False``) e o renderer cai para o derivado silenciosamente.
def test_summaries_shape_is_flat_strings(narrativas: dict[str, Any]) -> None:
    """``summaries`` são 10 chaves ``s1..s10`` para ``str`` não-vazia."""
    summaries = narrativas["summaries"]
    assert set(summaries) == {f"s{i}" for i in range(1, 11)}
    nao_str = {k: type(v).__name__ for k, v in summaries.items() if not isinstance(v, str)}
    assert not nao_str, f"summaries com shape não-str: {nao_str}"
    vazias = [k for k, v in summaries.items() if not v.strip()]
    assert not vazias, f"summaries vazias: {vazias}"


def test_charts_shape_is_context_conclusion(narrativas: dict[str, Any]) -> None:
    """``charts[*]`` mantém o par ``{context, conclusion}`` que o TS lê."""
    charts = narrativas["charts"]
    assert charts, "nenhum chart emitido"
    faltando = {
        cid: sorted({"context", "conclusion"} - set(c))
        for cid, c in charts.items()
        if not {"context", "conclusion"} <= set(c)
    }
    assert not faltando, f"charts sem o par context/conclusion: {faltando}"


# Direção que nenhum gate cobria: layout declarando `s11` (ou produtor
# renomeando chave) produzia parágrafo vazio em silêncio.
def test_every_declared_destination_is_resolvable(narrativas: dict[str, Any]) -> None:
    """Todo ``summary_source`` do layout resolve numa chave emitida."""
    summaries = narrativas["summaries"]
    orfaos = {
        section_id: key
        for section_id, key in _layout_destinations().items()
        if key not in summaries
    }
    assert not orfaos, f"destino declarado no layout sem chave em narrativas.summaries: {orfaos}"


def test_no_orphan_summary_key_without_reason(narrativas: dict[str, Any]) -> None:
    """Chave emitida sem destino tem de estar na allowlist COM razão escrita."""
    from pipeline.domain.services.narrativas import ORPHAN_SUMMARY_KEYS

    destinos = set(_layout_destinations().values())
    orfas = set(narrativas["summaries"]) - destinos - set(ORPHAN_SUMMARY_KEYS)
    assert not orfas, (
        f"chaves de summary sem destino e sem allowlist: {sorted(orfas)} — "
        "declare `summary_source` na seção ou registre a razão em "
        "ORPHAN_SUMMARY_KEYS (summaries_narrator.py)"
    )


# ── Destino SEMÂNTICO (A40.l4 · P7) ──────────────────────────────────────
#
# As pernas acima leem o destino DO layout e o conferem CONTRA o layout: um
# mapeamento semanticamente errado (`summary_source: "s2"` na S2, que é Fluxo
# de Caixa, quando `s2` é o parágrafo de SCORE) passava 30/30. A expectativa
# vive fora do runtime, em `tests/fixtures/narrativas/e5n_destinations.json`,
# com a razão semântica escrita por entrada — e o lado TS lê o MESMO arquivo.


def test_layout_matches_declared_destinations() -> None:
    """O layout entrega exatamente os destinos declarados — nem mais, nem outros."""
    assert _layout_destinations() == _expected_destinations(), (
        "`summary_source` do layout divergiu do mapa declarado em "
        f"{_DESTINATIONS.name}. Isso é decisão de produto: atualize o mapa E a "
        "razão semântica da entrada, não só o YAML."
    )


def test_orphan_allowlist_matches_declaration() -> None:
    """`ORPHAN_SUMMARY_KEYS` do produtor == órfãs declaradas, chave a chave."""
    from pipeline.domain.services.narrativas import ORPHAN_SUMMARY_KEYS

    assert set(ORPHAN_SUMMARY_KEYS) == set(_expected_orphans()), (
        "allowlist de órfãs do produtor divergiu da declarada em "
        f"{_DESTINATIONS.name} — chave nova sem destino precisa de razão nos dois."
    )
