"""Invariante ADR-306 — rótulo de janela em toda métrica mensalizada do E5.

Todo dict do payload que contém campo ``*mensal*``/``*mensais*`` derivado de
série temporal DEVE carregar a chave irmã ``janela`` (vocabulário fechado:
``12m`` | ``full`` | ``irpf[_<ano>]``). Campos "valor mensal por natureza"
(parcela contratual, aporte de meta) são isentos — cada isenção justificada
inline; assert anti-órfã impede a lista de acumular nomes mortos (ADR-210).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import (
    load_fixture,
    run_dogfood_pipeline,
    run_e3_e4_e5,
    write_e5_config,
)

_REPO = Path(__file__).resolve().parents[1]
_FIX = _REPO / "tests" / "fixtures" / "pipeline_golden"
_E3_MIXED = _FIX / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
_BASELINE = _FIX / "e2" / "minimal-baseline-1.5_consolidated.json"
_DOGFOOD = _FIX / "dogfood"

_JANELA_VOCAB = re.compile(r"^(12m|full|irpf(_\d{4})?)$")

# Valores mensais por natureza — quantia mensal contratual/planejada, não
# mensalização de série temporal (ADR-306 §D1 família iv).
_EXEMPT_FIELDS = frozenset(
    {
        "parcela_mensal",  # parcela contratual de dívida
        "aporte_mensal",  # meta/plano de aporte (goals + previdência + cenários)
        "aporte_mensal_usado",  # input do Monte Carlo IF, ecoa a meta
        "aporte_meta_mensal",  # meta de aporte (goals)
        "receita_despesa_mensal_detalhado",  # dataset de chart (série por mês)
        "renda_pj_mensal",  # input direto de config/goals
    }
)


def _mensal_fields(node: dict) -> set[str]:
    return {
        k
        for k in node
        if ("mensal" in k.split("_") or "mensais" in k.split("_")) and k not in _EXEMPT_FIELDS
    }


def _children(node, path):
    if isinstance(node, dict):
        return [(f"{path}.{k}", v) for k, v in node.items()]
    if isinstance(node, list):
        return [(f"{path}[{i}]", v) for i, v in enumerate(node)]
    return []


def _walk(node, path=""):
    if isinstance(node, dict):
        yield path, node
    for child_path, child in _children(node, path):
        yield from _walk(child, child_path)


def _walk_all(payloads):
    for payload in payloads:
        yield from _walk(payload)


@pytest.fixture(scope="module")
def payloads(tmp_path_factory) -> list[dict]:
    minimal_root = tmp_path_factory.mktemp("janela_minimal")
    write_e5_config(minimal_root, expense_keywords={"lazer": ["CINEMA"]})
    minimal = run_e3_e4_e5(
        minimal_root,
        e3_payloads={"minimal-conta-com-despesa": load_fixture(_E3_MIXED)},
        baseline=load_fixture(_BASELINE),
    )
    dogfood_root = tmp_path_factory.mktemp("janela_dogfood")
    write_e5_config(dogfood_root)
    dogfood = run_dogfood_pipeline(
        dogfood_root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "extrato-a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "extrato-b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )
    return [minimal, dogfood]


def test_todo_campo_mensal_tem_rotulo_de_janela(payloads: list[dict]):
    violations = [
        f"{path or '<root>'}: {sorted(fields)} sem chave 'janela'"
        for path, node in _walk_all(payloads)
        if (fields := _mensal_fields(node)) and "janela" not in node
    ]
    assert not violations, "campos mensalizados sem rótulo de janela (ADR-306):\n" + "\n".join(
        violations
    )


def test_rotulo_de_janela_usa_vocabulario_fechado(payloads: list[dict]):
    rotulados = [
        (path, node) for path, node in _walk_all(payloads) if isinstance(node.get("janela"), str)
    ]
    assert rotulados, "nenhum bloco rotulado encontrado — pipeline mudou shape?"
    for path, node in rotulados:
        assert _JANELA_VOCAB.match(
            node["janela"]
        ), f"{path}: janela={node['janela']!r} fora do vocabulário ADR-306"
        assert isinstance(
            node.get("janela_meses"), int
        ), f"{path}: bloco rotulado sem 'janela_meses' int"


def test_isencao_sem_orfaos(payloads: list[dict]):
    """Toda isenção deve existir em ≥1 payload — impede lixão de nomes mortos."""
    seen: set[str] = set()
    for _, node in _walk_all(payloads):
        seen.update(k for k in node if k in _EXEMPT_FIELDS)
    orfaos = _EXEMPT_FIELDS - seen
    # `renda_pj_mensal` só aparece em snapshots com goals de renda PJ —
    # tolerada como isenção documental (consumida em suggestion_rules).
    tolerados = {"renda_pj_mensal", "aporte_meta_mensal"}
    assert orfaos <= tolerados, f"isenções órfãs (remova da lista): {sorted(orfaos - tolerados)}"


def test_base_canonica_da_reserva_vem_da_janela_12m(payloads: list[dict]):
    """A28.l1 — denominador da reserva é o custo essencial da janela canônica;
    sem categoria essencial documentada, fallback rotulado à despesa total."""
    for payload in payloads:
        reserva = payload["reserva_emergencia"]
        j12m = payload["fluxo_caixa"]["janela_12m"]
        assert reserva["janela"] == "12m"
        essencial = j12m["despesa_mensal_essencial"]
        if essencial > 0:
            assert reserva["base_denominador"] == "custo_essencial"
            assert reserva["despesas_mensais"] == pytest.approx(essencial)
        else:
            assert reserva["base_denominador"] == "despesa_total"
            assert reserva["despesas_mensais"] == pytest.approx(j12m["despesa_mensal_media"])


def test_folga_mensal_reconcilia_com_base_canonica(payloads: list[dict]):
    """ADR-306 §D6 — folga derivável algebricamente da janela 12m."""
    for payload in payloads:
        consumo = payload["consumo_consciente"]
        j12m = payload["fluxo_caixa"]["janela_12m"]
        n = j12m["n_meses"]
        esperado = (
            j12m["receita_recorrente_mensal"]
            - j12m["despesa_mensal_media"]
            + (consumo["total_pontuais_janela"] / n if n else 0.0)
        )
        assert consumo["folga_mensal"] == pytest.approx(esperado, abs=0.02)
