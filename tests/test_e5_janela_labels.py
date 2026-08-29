"""Invariante ADR-306 — rótulo de janela em toda métrica mensalizada do E5.

Todo bloco do payload que contém campo ``*mensal*``/``*mensais*`` derivado de
série temporal DEVE carregar a chave irmã ``janela`` (vocabulário fechado:
``3m`` | ``6m`` | ``12m`` | ``ytd`` | ``full`` | ``irpf[_<ano>]``). Rows
table-ready herdam o rótulo do bloco que as contém. Campos "valor mensal por natureza"
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
_E3_PONTUAIS = _FIX / "e3" / "pontuais-com-aporte-3_reconciled.json"
_BASELINE = _FIX / "e2" / "minimal-baseline-1.5_consolidated.json"
_DOGFOOD = _FIX / "dogfood"

_JANELA_VOCAB = re.compile(r"^(3m|6m|12m|ytd|full|irpf(_\d{4})?)$")

_PONTUAIS_KEYWORDS = {
    "lazer_viagens": ["CINEMA"],
    "aporte_investimento": ["APORTE CDB"],
    "moradia": ["ALUGUEL"],
}

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
        return [(f"{path}.{k}", v) for k, v in node.items() if k != "_lineage"]
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


def _inherits_interactive_window(path: str) -> bool:
    return path.startswith(".fluxo_caixa.janelas.") and ".tabela_" in path


def _payload_minimal(root: Path) -> dict:
    write_e5_config(root, expense_keywords={"lazer": ["CINEMA"]})
    return run_e3_e4_e5(
        root,
        e3_payloads={"minimal-conta-com-despesa": load_fixture(_E3_MIXED)},
        baseline=load_fixture(_BASELINE),
    )


def _payload_dogfood(root: Path) -> dict:
    write_e5_config(root)
    return run_dogfood_pipeline(
        root,
        raw_baseline=load_fixture(_DOGFOOD / "baseline-1.5.json"),
        e2_extracts={
            "extrato-a": load_fixture(_DOGFOOD / "extrato-a-2_extract.json"),
            "extrato-b": load_fixture(_DOGFOOD / "extrato-b-2_extract.json"),
        },
    )


def _payload_pontuais(root: Path) -> dict:
    write_e5_config(root, expense_keywords=_PONTUAIS_KEYWORDS)
    return run_e3_e4_e5(root, e3_payloads={"pontuais-com-aporte": load_fixture(_E3_PONTUAIS)})


@pytest.fixture(scope="module")
def payloads(tmp_path_factory) -> list[dict]:
    return [
        _payload_minimal(tmp_path_factory.mktemp("janela_minimal")),
        _payload_dogfood(tmp_path_factory.mktemp("janela_dogfood")),
        _payload_pontuais(tmp_path_factory.mktemp("janela_pontuais")),
    ]


def test_todo_campo_mensal_tem_rotulo_de_janela(payloads: list[dict]):
    violations = [
        f"{path or '<root>'}: {sorted(fields)} sem chave 'janela'"
        for path, node in _walk_all(payloads)
        if (fields := _mensal_fields(node))
        and "janela" not in node
        and not _inherits_interactive_window(path)
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


# RR6-01 / ADR-420 — `folga_mensal` devolvia `pontuais_janela/n` ao numerador e
# publicava um SEGUNDO "quanto sobra" sobre o MESMO denominador da taxa de
# poupança, divergindo dela por exatamente a provisão do gasto pontual; era o
# maior dos dois que prescrevia. `teto_sugerido` era o complemento aritmético do
# mesmo erro: 37% abaixo do gasto real no dogfood.
#
# Os dois goldens anteriores têm `total_pontuais_janela == 0` e `n_meses == 1` —
# com o termo zerado, folga e poupança coincidem qualquer que seja a fórmula e o
# gate nasce verde (RR6-07). Daí `test_fixture_discrimina_folga` vir ANTES: ele
# vigia a fixture, sem a qual os três testes abaixo passam por vacuidade.
def test_fixture_discrimina_folga(payloads: list[dict]):
    """A fixture É o gate — sem um payload que separe os 4 eixos, o invariante é vácuo."""
    discriminantes = [
        p
        for p in payloads
        if p["consumo_consciente"]["total_pontuais_janela"] > 0
        and p["consumo_consciente"]["total_pontuais"]
        > p["consumo_consciente"]["total_pontuais_janela"]
        and p["fluxo_caixa"]["janela_12m"]["transferencia_patrimonial"] > 0
        and p["fluxo_caixa"]["janela_12m"]["n_meses"] > 1
    ]
    assert discriminantes, (
        "nenhum payload separa pontuais-na-janela × pontuais-full × "
        "transferência patrimonial × n_meses>1 — o invariante da folga passaria "
        "sem exercitar nenhum dos termos que ele existe para vigiar"
    )


def test_folga_mensal_nao_soma_pontual_realizado(payloads: list[dict]):
    """ADR-420 — folga é a poupança da janela, medida sobre ``despesa_consumo``."""
    for payload in payloads:
        consumo = payload["consumo_consciente"]
        j12m = payload["fluxo_caixa"]["janela_12m"]
        n = j12m["n_meses"]
        assert n > 0, "janela sem meses — payload inválido para o invariante"
        poupanca_mensal = (j12m["receita_recorrente"] - j12m["despesa_consumo"]) / n
        assert consumo["folga_mensal"] == pytest.approx(poupanca_mensal, abs=0.02)


def test_folga_pct_nao_diverge_da_taxa_de_poupanca(payloads: list[dict]):
    """O par (folga_pct, taxa_poupanca_recorrente) é UM veredito, não dois."""
    for payload in payloads:
        j12m = payload["fluxo_caixa"]["janela_12m"]
        if not j12m["receita_recorrente"]:
            continue
        assert payload["consumo_consciente"]["folga_pct"] == pytest.approx(
            j12m["taxa_poupanca_recorrente"], abs=0.1
        )


def test_teto_sugerido_nao_e_publicado(payloads: list[dict]):
    """ADR-420 — teto saía de ``despesa_recorrente × 1,15`` sobre base bruta."""
    for payload in payloads:
        assert "teto_sugerido" not in payload["consumo_consciente"]
