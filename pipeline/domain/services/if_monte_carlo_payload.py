"""Serialização do bloco ``if_monte_carlo`` do payload E5 (ADR-361 · ADR-369)."""

# Separado de ``if_monte_carlo`` por responsabilidade — lá mora a SIMULAÇÃO,
# aqui o CONTRATO DO WIRE — e porque o módulo de origem passou do teto de 500
# linhas. A ORDEM de composição é parte do contrato: o distiller do parecer
# corta prefixalmente, então o que vem antes é o que o LLM garantidamente lê.

from __future__ import annotations

from pipeline.domain.services.if_monte_carlo import MonteCarloIFResult


def _cone_cenarios(mc: MonteCarloIFResult) -> dict:
    """Anos do cone com a flag de censura INTERCALADA (ADR-361)."""
    # O corte do distiller é prefixal, então flags agrupadas depois dos três anos
    # abririam uma janela em que o LLM lê o ano sem saber que foi censurado.
    return {
        "ano_if_cenario_favoravel": mc.ano_if_cenario_favoravel,
        "ano_if_cenario_favoravel_censurado": mc.ano_if_cenario_favoravel_censurado,
        "ano_if_cenario_central": mc.ano_if_cenario_central,
        "ano_if_cenario_central_censurado": mc.ano_if_cenario_central_censurado,
        "ano_if_cenario_adverso": mc.ano_if_cenario_adverso,
        "ano_if_cenario_adverso_censurado": mc.ano_if_cenario_adverso_censurado,
    }


def _cone_premissas(mc: MonteCarloIFResult) -> dict:
    """Probabilidades (dois prazos distintos) + proveniência do alvo declarado."""
    # A proveniência do prazo fica COLADA na probabilidade que ela qualifica,
    # pelo mesmo motivo das flags de censura (ADR-361 D5): o corte do distiller é
    # prefixal, e um número de compromisso sem o dono da data é pior que ausente.
    return {
        "prob_if_ate_prazo_declarado": mc.prob_if_ate_prazo_declarado,
        "prazo_declarado_anos": mc.prazo_declarado_anos,
        "ano_alvo_declarado": mc.ano_alvo_declarado,
        "declarado_em": mc.declarado_em,
        "prazo_declarado_truncado": mc.prazo_declarado_truncado,
        "motivo_sem_prazo_declarado": mc.motivo_sem_prazo_declarado,
        "prob_if_ate_horizonte_simulado": mc.prob_if_ate_horizonte_simulado,
        "sigma_usado": mc.sigma_usado,
        "exibir_cone": mc.exibir_cone,
        "aporte_mensal_usado": float(mc.aporte_mensal_usado),
        "motivo_sem_cone": mc.motivo_sem_cone,
    }


def _cone_series_e_proveniencia(mc: MonteCarloIFResult) -> dict:
    """Séries ano→BRL e, no fim, a proveniência do run."""
    # ADR-360 — proveniência no FIM de propósito: o distiller renderiza o bloco
    # raw com cap de chars, então metadado não desloca dado de domínio do LLM.
    return {
        "caminho_p10": [list(p) for p in mc.caminho_p10],
        "caminho_p50": [list(p) for p in mc.caminho_p50],
        "caminho_p90": [list(p) for p in mc.caminho_p90],
        "mc_version": mc.mc_version,
        "seed_usado": mc.seed_usado,
        "n_simulacoes_usado": mc.n_simulacoes_usado,
        "horizonte_simulado_anos": mc.horizonte_simulado_anos,
    }


def monte_carlo_to_dict(mc: MonteCarloIFResult) -> dict:
    """Bloco ``if_monte_carlo`` do payload E5 — a ORDEM de composição é o contrato."""
    # Pública porque o gate de orçamento do exec context do parecer mede a ordem
    # de produção, não uma cópia dela.
    return {
        **_cone_cenarios(mc),
        **_cone_premissas(mc),
        **_cone_series_e_proveniencia(mc),
    }
