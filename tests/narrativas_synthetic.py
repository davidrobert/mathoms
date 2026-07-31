"""Substrato sintético dos testes de narrativa E5.N (A40.l4 · ADR-355).

Família, `GoalsBundle` e payload E5 mínimos + o atalho que roda o builder e
devolve `summaries`. Extraído de `tests/test_e5n_anti_hardcode.py` quando o
arquivo passou de 500 linhas (CLAUDE.md §Code style): o substrato é
responsabilidade própria e agora é lido por dois módulos de teste — o das guardas
de conteúdo e o da classificação derivada de parâmetros.

O `GoalsBundle` aqui tem o **shape de produção** de cada bloco (ver a nota em
`goals_bundle`); teste que precise de outro shape monta o seu, não muda este.
"""

from __future__ import annotations

from typing import Any, Mapping

import scripts.generate_narratives as e5n
from pipeline.domain.services.narrativas import E5NarrativasBuilder

FAMILY: dict[str, Any] = {
    "titular": "alex",
    "endereco": {},
    "membros": {
        "alex": {"papel": "titular", "nome_curto": "Alex", "data_nascimento": "1985-06-15"},
        "bia": {"papel": "conjuge", "nome_curto": "Bia", "data_nascimento": "1987-03-20"},
    },
}

RISCOS = [
    {
        "name": "Cobertura de vida abaixo do recomendado",
        "probability": "média",
        "impact_level": "alto",
    },
]
DECISOES = [
    {"title": "Iniciar aporte mensal recorrente"},
    {"title": "Contratar seguro de vida term"},
    {"title": "Consolidar reserva de emergência"},
    {"title": "Revisar alocação em renda variável"},
]


# `params` / `seed` carregam os valores; os nomes das chaves ficam dentro do
# dict, não em parâmetros anotados como float (ADR-090 §gate P5).
PARAMS_A: dict[str, float] = {
    "trs_pct": 4.0,
    "aporte": 20_000.0,
    "usd": 100_000.0,
    "holding": 12,
    "vida_min": 2_000_000,
    "vida_max": 4_000_000,
}
PARAMS_B: dict[str, float] = {
    "trs_pct": 3.0,
    "aporte": 31_500.0,
    "usd": 250_000.0,
    "holding": 24,
    "vida_min": 3_000_000,
    "vida_max": 6_000_000,
}


def _goals_if(params: Mapping[str, float]) -> dict[str, Any]:
    """Bloco `independencia_financeira` — só a TRS varia entre A e B."""
    return {
        "if_meta": 5_000_000.0,
        "trs_pct": params["trs_pct"],
        "taxa_retirada_segura_pct": params["trs_pct"],
        "renda_passiva_meta_mensal": 16_000.0,
    }


# Shape de produção de `bundle["tributario"]` (`pipeline_adapter`
# `_assemble_tributario_section`): `regime` (não o label) é o sinal de perfil
# declarado (ADR-236 §D5) e `contador_nome` existe; NÃO existe `contador_mensal`
# (ADR-355 §D7 — o `get(..., 0)` legado publicava honorário "R$ 0,00/mês"). A base
# da classificação de efeito tem de ser esse shape, senão as classificações
# descrevem outro mundo.
def _goals_tributario(params: Mapping[str, float]) -> dict[str, Any]:
    return {
        "regime": "simples",
        "regime_label": "Simples Nacional — Anexo III",
        "contador_nome": "Escritório contábil",
        "holding_prazo_meses": params["holding"],
    }


def goals_bundle(params: Mapping[str, float]) -> dict[str, Any]:
    """GoalsBundle sintético; `params` traz só os valores citáveis."""
    return {
        "independencia_financeira": _goals_if(params),
        "aportes": {"meta_aporte_mensal": params["aporte"]},
        "dolarizacao": {"meta_usd": params["usd"], "aporte_mensal_brl": 2_000.0},
        "seguros": {
            "vida_term_minimo": params["vida_min"],
            "vida_term_maximo": params["vida_max"],
        },
        "tributario": _goals_tributario(params),
        "risks_projection": RISCOS,
        "top5_decisoes_projection": DECISOES,
    }


GOALS_A = goals_bundle(PARAMS_A)
GOALS_B = goals_bundle(PARAMS_B)

SEED_A: dict[str, float] = {
    "bruto": 2_500_000.0,
    "imoveis": 400_000.0,
    "ano": 480_000.0,
    "mes": 40_000.0,
    "gasto_mes": 25_000.0,
    "cobertura": 12.0,
}
SEED_B: dict[str, float] = {
    "bruto": 7_100_000.0,
    "imoveis": 1_250_000.0,
    "ano": 930_000.0,
    "mes": 77_500.0,
    "gasto_mes": 41_300.0,
    "cobertura": 31.0,
}


def _patrimonio(seed: Mapping[str, float]) -> dict[str, Any]:
    """Bloco `patrimonio` do E5 sintético."""
    return {
        "bruto": seed["bruto"],
        "investivel_efetivo": 1_500_000.0,
        "residencia": 800_000.0,
        "imoveis_investimento": seed["imoveis"],
        "composicao": [{"categoria": "imoveis", "valor": 1.0}],
    }


def _fluxo(seed: Mapping[str, float]) -> dict[str, Any]:
    """Bloco `fluxo_caixa` do E5 sintético."""
    return {
        "receita_total": seed["ano"],
        "receita_recorrente_mensal": seed["mes"],
        "despesa_mensal_media": seed["gasto_mes"],
        "despesa_total": seed["gasto_mes"] * 12,
        "por_fonte": {},
        "despesas_por_categoria": {"moradia": 1_000.0},
    }


def e5_payload(seed: Mapping[str, float] = SEED_A) -> dict[str, Any]:
    """Payload E5 sintético mínimo para os narradores."""
    return {
        "patrimonio": _patrimonio(seed),
        "goals": {"if_meta": 5_000_000.0, "ano_if": 2039, "if_gap": 3_500_000.0},
        "fluxo_caixa": _fluxo(seed),
        "ratios": {"taxa_poupanca_recorrente_pct": 35.0, "taxa_endividamento_pct": 8.0},
        "score": {"valor": 7.5, "classificacao": "Saudável"},
        "reserva_emergencia": {"cobertura_meses": seed["cobertura"]},
    }


def summaries(e5: dict[str, Any], goals_cfg: dict[str, Any]) -> dict[str, str]:
    """Roda o builder e devolve só `summaries`."""
    metrics = e5n.load_metrics_from_e5(e5, goals_cfg=goals_cfg)
    return E5NarrativasBuilder.from_family_config(FAMILY).build(metrics, FAMILY)["summaries"]


def build_all(goals_cfg: dict[str, Any]) -> dict[str, Any]:
    """Artefato `narrativas` completo (perfil + summaries + charts)."""
    metrics = e5n.load_metrics_from_e5(e5_payload(), goals_cfg=goals_cfg)
    return E5NarrativasBuilder.from_family_config(FAMILY).build(metrics, FAMILY)


def set_path(blob: dict[str, Any], path: tuple[str, ...], valor: Any) -> None:
    """Seta `path` (tupla de chaves) em `blob`, criando dicts intermediários."""
    node = blob
    for chave in path[:-1]:
        node = node.setdefault(chave, {})
    node[path[-1]] = valor


def pin_tenant_config(tmp_path, monkeypatch) -> None:
    """Tenant vazio: sem `parametros_fiscais.json` nem `taxas.json` (A7.2b)."""
    e5n._init_config(tmp_path)
    monkeypatch.setattr(e5n, "_load_taxas", lambda: {"cambio_usd_brl": 5.80})
