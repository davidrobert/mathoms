"""Anti-hardcode das narrativas E5.N (A40.l4 · ADR-355).

Guarda de **conteúdo**, complementar à guarda de forma
(`tests/test_e5n_delivery_contract.py`): nenhum teste de shape detecta um
summary que cita parâmetro congelado. Três braços, todos declarativos:

- **A — parâmetros de `goals.json`.** Dois `goals_cfg` que diferem só em
  valores citáveis. Os summaries que citam esses parâmetros TÊM de variar;
  os que não citam TÊM de permanecer idênticos (invariância como assert de
  igualdade — pega refactor futuro que acople texto a config por acidente).
- **B — payload E5.** Dois E5 semeados diferindo só em valores medidos.
  Pega número congelado ancorado no payload.
- **C — afirmação incondicional.** Frase que o produtor imprime sempre,
  independente de haver dado que a sustente.

Por que o predicado NÃO é "todo summary que cita `%` tem de variar entre dois
`goals_cfg`": os `%` de s1/s2 (`pct_investivel`, `taxa_endividamento`,
`taxa_poupanca`, `pct_receita_*`) vêm do **payload E5**, não de `goals.json`, e
são legitimamente invariantes a config. Tratá-los como bug levaria a reescrever
dois summaries corretos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

import scripts.generate_narratives as e5n
from pipeline.domain.services.narrativas import E5NarrativasBuilder

_FAMILY: dict[str, Any] = {
    "titular": "alex",
    "endereco": {},
    "membros": {
        "alex": {"papel": "titular", "nome_curto": "Alex", "data_nascimento": "1985-06-15"},
        "bia": {"papel": "conjuge", "nome_curto": "Bia", "data_nascimento": "1987-03-20"},
    },
}

_RISKS = [
    {
        "name": "Cobertura de vida abaixo do recomendado",
        "probability": "média",
        "impact_level": "alto",
    },
]
_DECISOES = [
    {"title": "Iniciar aporte mensal recorrente"},
    {"title": "Contratar seguro de vida term"},
    {"title": "Consolidar reserva de emergência"},
    {"title": "Revisar alocação em renda variável"},
]


# `params` / `seed` carregam os valores; os nomes das chaves ficam dentro do
# dict, não em parâmetros anotados como float (ADR-090 §gate P5).
_PARAMS_A: dict[str, float] = {
    "trs_pct": 4.0,
    "aporte": 20_000.0,
    "usd": 100_000.0,
    "holding": 12,
    "vida_min": 2_000_000,
    "vida_max": 4_000_000,
}
_PARAMS_B: dict[str, float] = {
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


def _goals(params: Mapping[str, float]) -> dict[str, Any]:
    """GoalsBundle sintético; `params` traz só os valores citáveis."""
    return {
        "independencia_financeira": _goals_if(params),
        "aportes": {"meta_aporte_mensal": params["aporte"]},
        "dolarizacao": {"meta_usd": params["usd"], "aporte_mensal_brl": 2_000.0},
        "seguros": {
            "vida_term_minimo": params["vida_min"],
            "vida_term_maximo": params["vida_max"],
        },
        "tributario": {
            "regime_label": "Simples Nacional (Anexo III)",
            "holding_prazo_meses": params["holding"],
        },
        "risks_projection": _RISKS,
        "top5_decisoes_projection": _DECISOES,
    }


_GOALS_A = _goals(_PARAMS_A)
_GOALS_B = _goals(_PARAMS_B)

_SEED_A: dict[str, float] = {
    "bruto": 2_500_000.0,
    "imoveis": 400_000.0,
    "ano": 480_000.0,
    "mes": 40_000.0,
    "gasto_mes": 25_000.0,
    "cobertura": 12.0,
}
_SEED_B: dict[str, float] = {
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


def _e5_payload(seed: Mapping[str, float] = _SEED_A) -> dict[str, Any]:
    """Payload E5 sintético mínimo para os narradores."""
    return {
        "patrimonio": _patrimonio(seed),
        "goals": {"if_meta": 5_000_000.0, "ano_if": 2039, "if_gap": 3_500_000.0},
        "fluxo_caixa": _fluxo(seed),
        "ratios": {"taxa_poupanca_recorrente_pct": 35.0, "taxa_endividamento_pct": 8.0},
        "score": {"valor": 7.5, "classificacao": "Saudável"},
        "reserva_emergencia": {"cobertura_meses": seed["cobertura"]},
    }


def _summaries(e5_payload: dict[str, Any], goals_cfg: dict[str, Any]) -> dict[str, str]:
    metrics = e5n.load_metrics_from_e5(e5_payload, goals_cfg=goals_cfg)
    builder = E5NarrativasBuilder.from_family_config(_FAMILY)
    return builder.build(metrics, _FAMILY)["summaries"]


@pytest.fixture(autouse=True)
def _pinned_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tenant vazio: sem `parametros_fiscais.json` nem `taxas.json` (A7.2b)."""
    e5n._init_config(tmp_path)
    monkeypatch.setattr(e5n, "_load_taxas", lambda: {"cambio_usd_brl": 5.80})


# ─────────────────── Braço A — parâmetros de goals.json ───────────────────

# Summaries que CITAM parâmetro de `goals.json` — variação é obrigatória.
_VARIA_COM_GOALS = ("s6", "s7", "s8", "s9", "s10")
# Summaries ancorados exclusivamente no payload E5 — invariância é obrigatória.
_INVARIANTE_A_GOALS = ("s1", "s2", "s3", "s4", "s5")


@pytest.mark.parametrize("key", _VARIA_COM_GOALS)
def test_summary_varia_com_parametro_de_goals(key: str) -> None:
    """Parâmetro citável mudou ⇒ o texto muda. Igualdade = número congelado."""
    payload = _e5_payload()
    a = _summaries(payload, _GOALS_A)[key]
    b = _summaries(payload, _GOALS_B)[key]
    assert a != b, (
        f"summaries.{key} é idêntico com metas/prazos/faixas diferentes — "
        "o texto cita parâmetro congelado (hardcode) em vez de ler goals.json"
    )


@pytest.mark.parametrize("key", _INVARIANTE_A_GOALS)
def test_summary_ancorado_no_e5_ignora_goals(key: str) -> None:
    """Summary de dado medido não pode mudar quando só a config muda."""
    payload = _e5_payload()
    a = _summaries(payload, _GOALS_A)[key]
    b = _summaries(payload, _GOALS_B)[key]
    assert a == b, (
        f"summaries.{key} mudou só porque `goals.json` mudou — acoplou texto "
        "de dado medido a parâmetro de configuração"
    )


# ─────────────────────── Braço B — payload E5 ────────────────────────

_VARIA_COM_E5 = ("s1", "s2", "s4", "s5")


@pytest.mark.parametrize("key", _VARIA_COM_E5)
def test_summary_varia_com_payload_e5(key: str) -> None:
    """Valor medido mudou ⇒ o texto muda (pega número congelado no template)."""
    a = _summaries(_e5_payload(_SEED_A), _GOALS_A)[key]
    b = _summaries(_e5_payload(_SEED_B), _GOALS_A)[key]
    assert a != b, (
        f"summaries.{key} é idêntico com patrimônio/receita/reserva diferentes "
        "— o número no texto está congelado, não vem do payload E5"
    )


# ───────────────── Braço C — afirmação incondicional ─────────────────

# Resíduos do Modo USA (ADR-168) que o cleanup da A10.1 tirou do s5 e deixou
# nos vizinhos s6/s8.
#
# Scan sobre o OUTPUT construído com dados neutros (não sobre o código-fonte):
# (a) fonte pega comentário e docstring, que não são user-facing; (b) fonte
# pega `_ACTION_LINES[(True, *)]` do `bubble_riscos`, que é CONDICIONAL a
# `has_us_exposure` por design (ADR-192 §D4) — este braço mede afirmação
# INCONDICIONAL. E como os inputs de usuário da fixture (nomes de risco,
# títulos de decisão) são neutros por construção, um cliente que legitimamente
# escreva "FBAR" no nome de um risco não produz falso-positivo aqui.
_EUA_LITERAIS = (
    "EUA",
    "FBAR",
    "Form 8938",
    "PFIC",
    "CPA expatriado",
    "pré-EUA",
)


def _all_narrative_text(goals_cfg: dict[str, Any]) -> str:
    metrics = e5n.load_metrics_from_e5(_e5_payload(), goals_cfg=goals_cfg)
    out = E5NarrativasBuilder.from_family_config(_FAMILY).build(metrics, _FAMILY)
    perfil = out["perfil_familia"]
    partes = [perfil.get("left", ""), perfil.get("right", ""), *out["summaries"].values()]
    for chart in out["charts"].values():
        if isinstance(chart, dict):
            partes += [str(chart.get("context", "")), str(chart.get("conclusion", ""))]
    return " ".join(partes)


@pytest.mark.parametrize("needle", _EUA_LITERAIS)
def test_narrativas_nao_afirmam_obrigacao_fiscal_eua(needle: str) -> None:
    """Nenhum texto emitido afirma obrigação fiscal dos EUA como fato universal."""
    texto = _all_narrative_text(_GOALS_A)
    assert needle.lower() not in texto.lower(), (
        f"literal `{needle}` emitido incondicionalmente — texto do Modo USA "
        "(ADR-168) afirmado para toda família, independente de residência"
    )


# `parametros_fiscais.json` migrou para a tabela `fiscal_parameters` em A7.2b
# e é path proibido no git: em produção `FISCAL` é `{}`. O default 6.0 fazia o
# texto parecer calculado.
def test_s8_omite_aliquota_sem_fonte_fiscal() -> None:
    """Sem parâmetro fiscal vigente, o s8 não publica alíquota nem DAS."""
    s8 = _summaries(_e5_payload(), _GOALS_A)["s8"]
    assert "alíquota efetiva" not in s8, s8
    assert "DAS mensal estimado" not in s8, s8
    assert s8.strip(), "s8 vazio quebraria validate_narrativas"


def test_s8_publica_aliquota_quando_ha_fonte_fiscal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Com fonte fiscal declarada, a cláusula volta — a supressão é condicional."""
    monkeypatch.setattr(e5n, "FISCAL", {"das_simples": {"aliquota_efetiva_pct": 11.0}})
    s8 = _summaries(_e5_payload(), _GOALS_A)["s8"]
    assert "alíquota efetiva 11%" in s8, s8


def test_s9_nao_afirma_ausencia_de_seguro_sem_sinal() -> None:
    """`protecao_patrimonial` ausente ⇒ o s9 não afirma que não há cobertura."""
    s9 = _summaries(_e5_payload(), _GOALS_A)["s9"]
    assert "Seguros de vida e invalidez inexistentes" not in s9, s9


def test_s9_afirma_ausencia_quando_gap_qualitativo_sinaliza() -> None:
    """Com `gap_qualitativo[vida].flag = True`, a afirmação é legítima."""
    payload = _e5_payload()
    payload["protecao_patrimonial"] = {
        "gap_qualitativo": [{"categoria": "vida", "flag": True, "rationale": "sem apólice"}]
    }
    s9 = _summaries(payload, _GOALS_A)["s9"]
    assert "Seguros de vida e invalidez inexistentes" in s9, s9


def test_s9_empty_state_nao_duplica_cta_do_componente() -> None:
    """`_S9_EMPTY` imprime acima do <EmptyState/> da S9 — CTA só no componente."""
    from pipeline.domain.services.narrativas.summaries_narrator import _S9_EMPTY

    for cta in ("Plano de Ação", "Cadastrar", "Mapeie"):
        assert cta not in _S9_EMPTY, (
            f"`{cta}` em _S9_EMPTY duplica o call-to-action do <EmptyState/> "
            "que renderiza logo abaixo, com wording diferente"
        )
