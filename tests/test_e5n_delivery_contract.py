"""Contrato de ENTREGA das narrativas E5.N (A40.l4 · ADR-355).

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

Família sintética (Alex/Bia) e ``endereco`` vazio: o produtor interpola nome
curto em ``s3`` e rua em ``s4`` — a fixture não pode carregar PII.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.test_e5n_golden_execution import _build_e5_workspace, _new_e5n_ctx

_REPO = Path(__file__).resolve().parents[1]
_FIXTURE = _REPO / "tests" / "fixtures" / "narrativas" / "e5n_delivery.json"
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
    "tributario": {
        "regime_label": "Simples Nacional (Anexo III)",
        "contador_mensal": 350.0,
        "contador_nome": "Escritório Contábil",
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


def _run_e5n(root: Path) -> dict[str, Any]:
    """E4→E5→E5.N reais (sem LLM, sem API key) e devolve ``narrativas``."""
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.generate_narratives import _init_config as e5n_init
    from scripts.generate_narratives import main_with_store as e5n_mws

    ctx = _new_e5n_ctx(root)
    e4_mws(ctx)
    e5_mws(ctx)
    e5n_init(root)
    e5n_mws(ctx)
    payload = ctx.artifact_store.read("E5", "analise_financeira")
    assert payload is not None, "E5.N não persistiu o payload"
    narrativas = payload.get("narrativas")
    assert isinstance(narrativas, dict), "payload E5 sem bloco `narrativas`"
    return narrativas


def _serialize(narrativas: dict[str, Any]) -> str:
    return json.dumps(narrativas, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _layout_destinations() -> dict[str, str]:
    """``{section_id: summary_source}`` das entradas enabled do layout."""
    layout = yaml.safe_load(_LAYOUT_YAML.read_text(encoding="utf-8"))
    estrategico = layout["estrategico"]
    entries = [*estrategico["sections"], *estrategico.get("appendices", [])]
    return {
        e["id"]: e["summary_source"]
        for e in entries
        if e.get("enabled") and e.get("summary_source")
    }


@pytest.fixture(scope="module")
def narrativas(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = _build_e5_workspace(tmp_path_factory.mktemp("e5n_delivery"), _FAMILY)
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
