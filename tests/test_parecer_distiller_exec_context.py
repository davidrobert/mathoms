"""Contrato do exec context do parecer (ADR-341 · A37.l1 PR-2b) — medição
in-process do distiller sobre payload dogfood-like sintético (fallback do eval
owner-gated): 10/10 seções no budget, probes field-level nos blocos densos
re-formatados, hints fora do corpo orçado, eviction por prioridade declarada
com marcador nomeando as seções removidas. Zero PII — valores sintéticos."""

from __future__ import annotations

import dataclasses
import json

from backend.app.services.parecer_distiller import distill_exec_context, render_block
from backend.app.services.parecer_manifest import load_manifest
from tests.test_parecer_planejador_golden import make_workspace_e5

_HINTS_HEADER = "### Diretrizes de leitura por seção (hints)"
_MARKER_PREFIX = "[exec context truncado em max_exec_context_bytes"

_MESES = [f"{ano}-{mes:02d}" for ano in (2023, 2024, 2025) for mes in range(1, 13)]
_DESPESA_CATS = [
    "moradia",
    "alimentacao",
    "transporte",
    "saude",
    "educacao",
    "lazer",
    "vestuario",
    "seguros",
    "assinaturas",
    "impostos",
    "servicos_domesticos",
    "financiamentos",
    "pets",
    "viagens",
    "presentes",
    "doacoes",
    "tarifas_bancarias",
    "manutencao_veiculo",
    "combustivel",
    "farmacia",
    "aporte_investimento",
    "outros",
]


def _chart_datasets(labels: list[str], series_labels: list[str]) -> list[dict]:
    return [
        {"label": lbl, "data": [round(1000.0 + i * 13.37 + n, 2) for n in range(len(labels))]}
        for i, lbl in enumerate(series_labels)
    ]


_DESPESAS_POR_CATEGORIA = {c: round(4000.0 + i * 321.5, 2) for i, c in enumerate(_DESPESA_CATS)}

# Espelha FluxoCaixaEnriched.to_legacy_dict — o dump cru media ~15K chars no dogfood.
_DENSE_FLUXO_CAIXA = {
    "janela": "full",
    "janela_meses": 36,
    "receita_total": 2_160_000.0,
    "receita_recorrente": 1_980_000.0,
    "receita_one_time": 180_000.0,
    "receita_recorrente_mensal": 55_000.0,
    "despesa_total": 1_440_000.0,
    "despesa_mensal_media": 40_000.0,
    "despesa_mensal_essencial": 22_000.0,
    "fluxo_liquido": 720_000.0,
    "por_fonte": {"pro_labore": 1_100_000.0, "salario": 480_000.0, "aluguel": 120_000.0},
    "receita_por_natureza": {
        "receita_pj": 1_500_000.0,
        "receita_clt": 480_000.0,
        "receita_aluguel": 120_000.0,
        "receita_outras": 60_000.0,
    },
    "por_fonte_detalhado": {"pro_labore": 660_000.0, "salario": 240_000.0},
    "despesas_por_categoria": _DESPESAS_POR_CATEGORIA,
    "tabela_receitas": [
        {"categoria": "Pro Labore", "valor": 1_100_000.0, "pct": 50.9},
        {"categoria": "Salario", "valor": 480_000.0, "pct": 22.2},
    ],
    "receita_despesa_mensal_detalhado": {
        "labels": _MESES,
        "receita_datasets": _chart_datasets(_MESES, ["Pro Labore", "Salario", "Aluguel"]),
        "despesa_datasets": _chart_datasets(_MESES, _DESPESA_CATS),
        "totais_receita": [60_000.0] * len(_MESES),
        "totais_despesa": [40_000.0] * len(_MESES),
    },
    "janela_12m": {
        "periodo": "2025-01 a 2025-12",
        "n_meses": 12,
        "janela": "12m",
        "janela_meses": 12,
        "receita_total": 720_000.0,
        "receita_recorrente": 660_000.0,
        "receita_one_time": 60_000.0,
        "receita_recorrente_mensal": 55_000.0,
        "despesa_total": 480_000.0,
        "despesa_mensal_media": 40_000.0,
        "despesa_mensal_essencial": 22_000.0,
        "despesa_consumo": 396_000.0,
        "transferencia_patrimonial": 84_000.0,
        "fluxo_liquido": 240_000.0,
        "taxa_poupanca_recorrente": 33.33,
        "taxa_poupanca_total": 38.5,
        "despesas_por_categoria": {c: round(v / 3, 2) for c, v in _DESPESAS_POR_CATEGORIA.items()},
    },
}

# Espelha ConsumoConsciente.to_legacy_dict — itens levavam o dump a ~17K chars.
_DENSE_CONSUMO_CONSCIENTE = {
    "itens": [
        {
            "descricao": f"gasto pontual sintetico {i}",
            "conta_cartao": "banco_sintetico (cartao)",
            "data": f"2025-{(i % 12) + 1:02d}-15",
            "mes": f"2025-{(i % 12) + 1:02d}",
            "valor": round(2500.0 + i * 137.9, 2),
            "categoria": _DESPESA_CATS[i % len(_DESPESA_CATS)],
            "observacao": "",
        }
        for i in range(40)
    ],
    "total_pontuais": 260_000.0,
    "total_pontuais_janela": 120_000.0,
    "equivalente_meses_aporte": 8.7,
    "folga_mensal": 15_000.0,
    "folga_pct": 27.3,
    "teto_sugerido": 28_750.0,
    "analise": "Identificados 40 gastos pontuais relevantes no período analisado.",
    "janela": "12m",
    "janela_meses": 12,
}

_PROTECAO_PATRIMONIAL = {
    "apolices_vigentes": [
        {
            "seguradora": f"seguradora_sintetica_{s}",
            "tipo": tipo,
            "vigencia_inicio": inicio,
            "vigencia_fim": fim,
            "premio_total_brl": premio,
            "bens_count": bens,
        }
        for s, tipo, inicio, fim, premio, bens in (
            ("a", "auto", "2026-01-01", "2026-12-31", 4_200.0, 1),
            ("b", "residencial", "2026-03-01", "2027-02-28", 1_800.0, 1),
            ("c", "auto", "2026-05-01", "2027-04-30", 12_500.0, 2),
        )
    ],
    "apolices_vencidas": [],
    "premio_anual_total_brl": 18_500.0,
    "pct_renda_anual": 0.026,
    "corretoras_count": 2,
    "gap_qualitativo": [
        {"categoria": "vida", "flag": True},
        {"categoria": "saude", "flag": False},
    ],
    "bens_com_gap_cobertura": [],
}

_RATIOS_OVERRIDES = {
    "taxa_poupanca_recorrente_pct": 33.33,
    "taxa_poupanca_total_pct": 38.5,
    "taxa_endividamento_pct": 9.6,
    "autonomia_financeira_meses": 18.4,
    "concentracao_imobiliaria": 58.2,
    "rentabilidade_pct": "N/D",
    "janela_referencia": "2025-01 a 2025-12",
    "janela_n_meses": 12,
}

_PGBL_OVERRIDES = {
    "limite_pgbl_anual": 0,
    "pgbl_status": "teto_atingido",
    "nota": "teto do regime atingido",
}


def make_dogfood_like_e5() -> dict:
    """E5 sintético denso — reproduz a dupla truncação medida no run 6659d62c."""
    e5 = make_workspace_e5()
    e5["fluxo_caixa"] = json.loads(json.dumps(_DENSE_FLUXO_CAIXA))
    e5["consumo_consciente"] = json.loads(json.dumps(_DENSE_CONSUMO_CONSCIENTE))
    e5["protecao_patrimonial"] = json.loads(json.dumps(_PROTECAO_PATRIMONIAL))
    e5["previdencia_pgbl"].update(_PGBL_OVERRIDES)
    e5["ratios"].update(_RATIOS_OVERRIDES)
    return e5


def _split_parts(ctx: str) -> tuple[str, str]:
    """(corpo orçado, resto pós-cap: hints + catálogo)."""
    body, sep, tail = ctx.partition(_HINTS_HEADER)
    assert sep, "bloco de hints ausente do exec context"
    return body, tail


# ---------------------------------------------------------------------------
# 10/10 seções + probes (payload denso, budget 16KB do manifest 2.0)
# ---------------------------------------------------------------------------


def test_all_sections_present_with_dense_payload():
    manifest = load_manifest()
    ctx = distill_exec_context(manifest, make_dogfood_like_e5())
    for section in manifest.sections:
        assert f"### {section['title']}" in ctx, f"seção '{section['id']}' fora do exec context"
    assert _MARKER_PREFIX not in ctx, "budget 16KB não deveria evictar o corpo dogfood-like"


def test_probes_previdencia_e_protecao_presentes():
    """Dano do dogfood 6659d62c: limite_pgbl=0 e apólices 100% fora do contexto."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "limite_pgbl_anual: 0" in ctx
    assert "apolices_vigentes" in ctx
    assert "gap_qualitativo" in ctx
    assert "gap_qualitativo[0].flag: True" in ctx


def test_field_probes_blocos_densos_reformatados():
    """ADR-341 D3: resumo curado é vetor novo de truncação silenciosa —
    contagem de seção não basta; probes field-level nos blocos re-formatados."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "Fluxo líquido: R$ 720.000,00" in ctx
    assert "Despesa mensal essencial: R$ 22.000,00" in ctx
    assert "Receita PJ (pró-labore + lucros): R$ 1.500.000,00" in ctx
    assert "Taxa de poupança recorrente (12m, %): 33,33%" in ctx
    assert "Transferência patrimonial/aporte (12m): R$ 84.000,00" in ctx
    assert "**Despesas por categoria (12m)**" in ctx
    assert "moradia: 1333.33" in ctx
    assert "Folga mensal: R$ 15.000,00" in ctx
    assert "Teto sugerido de consumo mensal: R$ 28.750,00" in ctx
    assert "Análise: Identificados 40 gastos pontuais" in ctx


def test_detalhe_transacional_fica_no_drill_down():
    """Charts e itens de gasto pontual não entram no corpo (manifest decide)."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "receita_despesa_mensal_detalhado" not in ctx
    assert "gasto pontual sintetico" not in ctx
    assert "tabela_receitas" not in ctx


def test_sentinela_nd_nao_renderizada_como_dado():
    """Coordenação A37.l4: folha "N/D" é ausência — flatten pula."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "rentabilidade_pct" not in ctx
    assert "aliquota_efetiva_ir_pct: 22.50" in ctx


# ---------------------------------------------------------------------------
# Bases e denominadores canônicos rotulados (A37.l9 — manifest 2.0.1)
# ---------------------------------------------------------------------------


def test_tabela_classes_declara_base_por_coluna():
    """A37.l9: cada pct da tabela chega ao LLM com a base no rótulo — coluna
    '% do total investido' (inclui imóveis físicos) vs '% da carteira
    financeira' (ex-imóveis, '—' na linha de imóveis, fora da base)."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "% do total investido=25,00%" in ctx  # Imóveis Investimento
    assert "% da carteira financeira=—" in ctx  # imóveis fora da base financeira
    assert "% do total investido=18,70%" in ctx  # RF
    assert "% da carteira financeira=25,00%" in ctx  # RF ex-imóveis


def test_decomposicao_das_bases_no_exec_context():
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "Total investido (financeiro + imóveis de investimento): R$ 3.200.000,00" in ctx
    assert "Carteira financeira da tabela (ex-imóveis físicos): R$ 2.400.000,00" in ctx
    assert "Imóveis de investimento na tabela: R$ 800.000,00" in ctx
    assert "Fonte da tabela (irpf_bens = foto 31/12; difere do patrimonio): irpf_bens" in ctx


def test_exposicao_cambial_projetada_com_base_propria():
    """CTO-04/PE-05: exposição cambial entra no exec context como conceito
    próprio (posições em moeda estrangeira ÷ investível financeiro) — nunca
    fundida com a alocação internacional da tabela."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    assert "Exposição cambial total: R$ 52.000,00" in ctx
    assert "% do investível financeiro (posições atuais + caixa): 2,16%" in ctx
    assert "Tier (verde >=10% / amarelo 5-10% / vermelho <5%): vermelho" in ctx


def test_hints_de_base_presentes():
    """Checagem determinística do eval golden (A37.l9): diretrizes de base
    viajam nos hints — 'carteira financeira' nunca para base com imóvel,
    internacional ≠ cambial, alíquota 'efetiva (blended)'."""
    ctx = distill_exec_context(load_manifest(), make_dogfood_like_e5())
    _body, tail = _split_parts(ctx)
    assert "Rótulo de base obrigatório (A37.l9)" in tail
    assert "Internacional ≠ cambial (A37.l9)" in tail
    assert "efetiva (blended)" in tail


# ---------------------------------------------------------------------------
# Hints fora do corpo orçado (ADR-341 D4)
# ---------------------------------------------------------------------------


def test_hints_nao_consomem_budget_do_corpo():
    manifest = load_manifest()
    ctx = distill_exec_context(manifest, make_dogfood_like_e5())
    body, tail = _split_parts(ctx)
    assert "_hint (" not in body, "hint dentro do corpo orçado compete com dado"
    total_hints = sum(len(s.get("narrative_hints", []) or []) for s in manifest.sections)
    assert tail.count("_hint (") == total_hints
    assert len(body.encode("utf-8")) <= manifest.max_exec_context_bytes


def test_hints_sobrevivem_sob_budget_minusculo():
    """Mesmo com corpo evictado, TODOS os hints continuam anexados pós-cap."""
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=3500)
    ctx = distill_exec_context(manifest, make_dogfood_like_e5())
    _body, tail = _split_parts(ctx)
    total_hints = sum(len(s.get("narrative_hints", []) or []) for s in manifest.sections)
    assert tail.count("_hint (") == total_hints
    assert "_hint (plano_acao_atual):_" in tail  # hint de seção evictada permanece


# ---------------------------------------------------------------------------
# Eviction determinística por seção (ADR-341 D2)
# ---------------------------------------------------------------------------


def test_eviction_por_prioridade_com_marcador_nomeando_secoes():
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=3500)
    ctx = distill_exec_context(manifest, make_dogfood_like_e5())
    body, _tail = _split_parts(ctx)
    assert _MARKER_PREFIX in body
    marker = body[body.index(_MARKER_PREFIX) :]
    for section in manifest.sections:
        title_present = f"### {section['title']}" in body
        named_in_marker = str(section["id"]) in marker
        assert title_present != named_in_marker, (
            f"seção '{section['id']}' deve estar OU inteira no corpo OU nomeada "
            f"no marcador — nunca cortada no meio"
        )
    assert len(body.encode("utf-8")) <= 3500
    # Menor prioridade declarada (plano_acao_atual=10) sai primeiro; a mais
    # importante (sintese=1) é a última a sair.
    assert "plano_acao_atual" in marker
    assert "### Síntese e Comportamento" in body
    assert "get_e5_section" in marker  # rota de recovery no próprio marcador


def test_eviction_nunca_corta_bloco_de_secao_mantida():
    """Seção mantida rende inteira: última linha do bloco denso presente."""
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=6500)
    ctx = distill_exec_context(manifest, make_dogfood_like_e5())
    body, _tail = _split_parts(ctx)
    if "### Fluxo de Caixa" in body:
        assert "Meses na janela do diagnóstico: 12" in body  # última folha do bloco consumo


def test_eviction_deterministica():
    manifest = dataclasses.replace(load_manifest(), max_exec_context_bytes=3500)
    e5 = make_dogfood_like_e5()
    assert distill_exec_context(manifest, e5) == distill_exec_context(manifest, e5)


def test_corpo_pre_cap_igual_pos_cap_sob_budget_16k():
    """Medição in-process (fallback do eval owner-gated): corpo curado cabe no
    budget novo SEM eviction — pré-cap == pós-cap."""
    manifest = load_manifest()
    uncapped = dataclasses.replace(manifest, max_exec_context_bytes=65536)
    e5 = make_dogfood_like_e5()
    body_capped, _ = _split_parts(distill_exec_context(manifest, e5))
    body_uncapped, _ = _split_parts(distill_exec_context(uncapped, e5))
    assert body_capped == body_uncapped
    assert len(body_capped.encode("utf-8")) <= manifest.max_exec_context_bytes


# ---------------------------------------------------------------------------
# _short como safety-net declarável (ADR-341 D3)
# ---------------------------------------------------------------------------


def test_scalar_max_chars_declaravel():
    long_list = [f"alerta_sintetico_{i}" for i in range(30)]
    block = {
        "format": "scalar",
        "path": "$.alertas",
        "label": "Alertas",
        "value_format": "raw",
        "max_chars": 800,
    }
    out = render_block(block, {"alertas": long_list})
    assert "alerta_sintetico_29" in out  # cauda sobrevive além dos 300 default
    sem_declaracao = render_block(
        {k: v for k, v in block.items() if k != "max_chars"}, {"alertas": long_list}
    )
    assert "alerta_sintetico_29" not in sem_declaracao
