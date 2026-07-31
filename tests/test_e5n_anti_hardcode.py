"""Anti-hardcode das narrativas E5.N (A40.l4 · ADR-356).

Guarda de **conteúdo**, complementar à guarda de forma
(`tests/test_e5n_delivery_contract.py`): nenhum teste de shape detecta um
summary que cita parâmetro congelado. Quatro braços aqui, todos declarativos:

- **A — por PARÂMETRO citado.** Para cada parâmetro citável há uma linha em
  `_PARAMS_CITAVEIS`: onde ele mora, qual summary o cita, dois valores e como o
  produtor o renderiza. O teste exige que o **token do valor** apareça no texto —
  com os dois valores. A granularidade importa: comparar o summary inteiro entre
  dois configs (a versão anterior desta guarda) fica VERDE quando se congela um
  literal entre outros parâmetros que ainda variam, que é exatamente a classe
  corrigida à mão na §D7 da ADR-356.
- **B — invariância.** Summary ancorado só no payload não pode mudar quando só a
  config muda (pega acoplamento acidental de texto medido a parâmetro).
- **C — afirmação incondicional.** Frase que o produtor imprime sempre,
  independente de haver dado que a sustente.
- **D — número que não vem do payload.** Regra unificadora do co-design
  financial-planner: *nenhum número entregue vem de default de código — ou vem do
  payload, ou não é afirmado*. Cobre as três instâncias da mesma doença (alíquota
  DAS 6%, `diversificacao or 5`, `trs_pct ?? 5.0`), a contagem de imóveis do `s4`
  e o silêncio sobre DAS enquanto o balde `das_simples` estiver contaminado
  (PR #1133).

O braço **A2** — que deriva do fonte do builder o universo de parâmetros e exige
classificação para cada um, fechando o furo da curadoria — vive em
`tests/test_e5n_param_classification.py`: mesma família de guarda, arquivo
próprio porque este passou de 500 linhas (CLAUDE.md §Code style).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import pytest

import scripts.generate_narratives as e5n
from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
)
from tests.narrativas_synthetic import (
    FAMILY,
    GOALS_A,
    GOALS_B,
    build_all,
    e5_payload,
    pin_tenant_config,
    set_path,
    summaries,
)


@pytest.fixture(autouse=True)
def _pinned_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    pin_tenant_config(tmp_path, monkeypatch)


# ──────────────── Braço A — por PARÂMETRO citado (granularidade) ────────────


@dataclass(frozen=True)
class ParamCitavel:
    """Um parâmetro citável: onde mora, quem o cita, e como aparece no texto."""

    nome: str
    summary_key: str
    fonte: str  # "goals" | "e5"
    path: tuple[str, ...]
    valores: tuple[Any, Any]
    render: Callable[[Any], str]


def set_path(blob: dict[str, Any], path: tuple[str, ...], valor: Any) -> None:
    node = blob
    for chave in path[:-1]:
        node = node.setdefault(chave, {})
    node[path[-1]] = valor


def _summary_com_param(p: ParamCitavel, valor: Any) -> str:
    """Renderiza `p.summary_key` com o parâmetro setado em `valor`."""
    import copy

    payload, goals = copy.deepcopy(e5_payload()), copy.deepcopy(GOALS_A)
    set_path(payload if p.fonte == "e5" else goals, p.path, valor)
    return summaries(payload, goals)[p.summary_key]


_SWR_PATH = ("independencia_financeira", "taxa_retirada_segura_pct")
_RETORNO_PATH = ("independencia_financeira", "retorno_real_anual_pct")
_REGIME_PATH = ("tributario", "regime_label")


def _p(key: str, fonte: str, path: tuple[str, ...], a: Any, b: Any, render) -> ParamCitavel:
    """Linha compacta da tabela; `nome` sai do path."""
    return ParamCitavel(".".join(path), key, fonte, path, (a, b), render)


def _tok_swr(v: Any) -> str:
    return f"({fmt_num(v, 0)}% retirada segura)"


def _tok_retorno(v: Any) -> str:
    return f"retorno real {fmt_num(v, 0)}%"


def _tok_vida_min(v: Any) -> str:
    return f"R$ {int(v) // 1_000_000}-"


def _tok_vida_max(v: Any) -> str:
    return f"-{int(v) // 1_000_000}M em seguro term"


def _tok_holding(v: Any) -> str:
    return f"pendente para {v} meses"


def _tok_distribuicao(v: Any) -> str:
    from pipeline.domain.services.narrativas.format_helpers import fmt_aporte_distribuicao

    return f"({fmt_aporte_distribuicao(v)})"


def _tok_contador(v: Any) -> str:
    return f"Contador cadastrado ({fmt_currency(v)}/mês"


# Valores escolhidos para produzir tokens distintos entre si e do resto do
# texto — token repetido no mesmo parágrafo daria falso-verde.
_PARAMS_CITAVEIS: tuple[ParamCitavel, ...] = (
    _p("s1", "e5", ("patrimonio", "bruto"), 2_500_000.0, 7_100_000.0, fmt_currency),
    _p("s1", "e5", ("patrimonio", "residencia"), 812_000.0, 934_000.0, fmt_currency),
    _p("s1", "e5", ("ratios", "taxa_endividamento_pct"), 8.0, 23.0, fmt_percent),
    _p("s2", "e5", ("score", "valor"), 7.5, 4.2, fmt_num),
    _p("s2", "e5", ("reserva_emergencia", "cobertura_meses"), 12.0, 31.0, fmt_num),
    _p("s2", "e5", ("fluxo_caixa", "receita_total"), 481_000.0, 933_000.0, fmt_currency),
    _p("s4", "e5", ("patrimonio", "imoveis_investimento"), 417_000.0, 1_253_000.0, fmt_currency),
    _p("s5", "e5", ("fluxo_caixa", "despesa_mensal_media"), 25_300.0, 41_700.0, fmt_currency),
    _p("s7", "e5", ("goals", "if_meta"), 5_100_000.0, 8_300_000.0, fmt_currency),
    _p("s7", "e5", ("goals", "if_gap"), 3_400_000.0, 6_700_000.0, fmt_currency),
    _p("s7", "e5", ("goals", "ano_if"), 2039, 2047, str),
    _p("s6", "goals", ("dolarizacao", "meta_usd"), 101_000.0, 253_000.0, fmt_usd),
    _p("s6", "goals", ("dolarizacao", "aporte_mensal_brl"), 2_100.0, 4_700.0, fmt_currency),
    _p("s7", "goals", _SWR_PATH, 4.0, 7.0, _tok_swr),
    _p("s7", "goals", _RETORNO_PATH, 6.0, 9.0, _tok_retorno),
    _p("s7", "goals", ("aportes", "meta_aporte_mensal"), 20_100.0, 31_500.0, fmt_currency),
    _p("s10", "goals", ("aportes", "meta_aporte_mensal"), 20_100.0, 31_500.0, fmt_currency),
    _p("s9", "goals", ("seguros", "vida_term_minimo"), 2_000_000, 3_000_000, _tok_vida_min),
    _p("s9", "goals", ("seguros", "vida_term_maximo"), 4_000_000, 6_000_000, _tok_vida_max),
    _p("s8", "goals", _REGIME_PATH, "Simples Nacional — Anexo III", "Lucro Presumido", str),
    _p("s8", "goals", ("tributario", "holding_prazo_meses"), 12, 30, _tok_holding),
    _p(
        "s10",
        "goals",
        ("aportes", "distribuicao"),
        {"ipca_plus": 12_100.0},
        {"ivvb11": 8_300.0},
        _tok_distribuicao,
    ),
    # Ramo DORMENTE, não morto: `contador_mensal` não existe no bundle de hoje
    # (§D7), então a cláusula sai sem valor. A linha existe para que o dia em
    # que o bundle passar a carregar o campo, o número impresso venha DELE — a
    # versão anterior imprimia `get(..., 0)` como "R$ 0,00/mês".
    _p("s8", "goals", ("tributario", "contador_mensal"), 1_830.0, 4_250.0, _tok_contador),
)


@pytest.mark.parametrize("param", _PARAMS_CITAVEIS, ids=lambda p: f"{p.summary_key}-{p.nome}")
def test_trecho_que_cita_parametro_varia_com_o_parametro(param: ParamCitavel) -> None:
    """O TOKEN do valor aparece no texto — com os dois valores do parâmetro."""
    for valor in param.valores:
        texto = _summary_com_param(param, valor)
        token = param.render(valor)
        assert token in texto, (
            f"summaries.{param.summary_key} não cita `{param.nome}` = {valor!r} "
            f"(token esperado {token!r}). O trecho está congelado: o número no "
            f"texto não vem de {param.fonte}. Texto: {texto}"
        )


# ─────────────────────── Braço B — invariância ───────────────────────

# Summaries ancorados exclusivamente no payload E5 — invariância a config é
# obrigatória; mudança aqui denuncia acoplamento acidental.
_INVARIANTE_A_GOALS = ("s1", "s2", "s3", "s4", "s5")


@pytest.mark.parametrize("key", _INVARIANTE_A_GOALS)
def test_summary_ancorado_no_e5_ignora_goals(key: str) -> None:
    """Summary de dado medido não pode mudar quando só a config muda."""
    payload = e5_payload()
    a = summaries(payload, GOALS_A)[key]
    b = summaries(payload, GOALS_B)[key]
    assert a == b, (
        f"summaries.{key} mudou só porque `goals.json` mudou — acoplou texto "
        "de dado medido a parâmetro de configuração"
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
    out = build_all(goals_cfg)
    perfil = out["perfil_familia"]
    partes = [perfil.get("left", ""), perfil.get("right", ""), *out["summaries"].values()]
    for chart in out["charts"].values():
        if isinstance(chart, dict):
            partes += [str(chart.get("context", "")), str(chart.get("conclusion", ""))]
    return " ".join(partes)


@pytest.mark.parametrize("needle", _EUA_LITERAIS)
def test_narrativas_nao_afirmam_obrigacao_fiscal_eua(needle: str) -> None:
    """Nenhum texto emitido afirma obrigação fiscal dos EUA como fato universal."""
    texto = _all_narrative_text(GOALS_A)
    assert needle.lower() not in texto.lower(), (
        f"literal `{needle}` emitido incondicionalmente — texto do Modo USA "
        "(ADR-168) afirmado para toda família, independente de residência"
    )


# ───────── Braço D — número que não vem do payload (regra unificadora) ──────
#
# "Nenhum número entregue vem de default de código — ou vem do payload, ou não
# é afirmado." Três instâncias da mesma doença, uma guarda por instância.


# A estimativa saiu inteira (co-design financial-planner): a alíquota vinha de
# default 6% (só válido na 1ª faixa do Simples, RBT12 ≤ R$ 180k) e a base era
# entrada na conta PF, não faturamento bruto — derivação proibida por ADR-236
# §Emenda CTO-05. O card `impostos_pj` da MESMA seção publica carga e receita
# bruta pela cascata canônica: um número, um dono.
def test_s8_nao_estima_carga_fiscal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nem com fonte fiscal legada disponível o s8 volta a estimar DAS/alíquota."""
    monkeypatch.setattr(e5n, "FISCAL", {"das_simples": {"aliquota_efetiva_pct": 11.0}})
    s8 = summaries(e5_payload(), GOALS_A)["s8"]
    for proibido in ("alíquota efetiva", "DAS mensal estimado", "receita PJ anualizada"):
        assert proibido not in s8, f"`{proibido}` voltou ao s8: {s8}"
    assert s8.strip(), "s8 vazio quebraria validate_narrativas"


# `regime_label` NUNCA é vazio (`_regime_to_label(None, …)` devolve "Perfil
# tributário incompleto"), então ramificar por string de label deixava o
# fallback inalcançável e a família lia o rótulo pelado, sem CTA.
def test_s8_sem_regime_declarado_nao_imprime_rotulo_pelado() -> None:
    """`regime is None` ⇒ estado pendente com o que informar, não o label cru."""
    goals = {**GOALS_A, "tributario": {"regime_label": "Perfil tributário incompleto"}}
    s8 = summaries(e5_payload(), goals)["s8"]
    assert "Perfil tributário PJ pendente" in s8, s8
    assert "informe regime, anexo e CNAE" in s8, s8


# `_DAS_KEYWORDS = ("DAS",)` casava a preposição, e a medição do balde
# `despesas_por_categoria.das_simples` no dogfood deu 100% de falso-positivo
# (pedágio, supermercado). O fix é o PR #1133, não mergeado — até lá, afirmar
# "DAS recolhido: R$ X" publicaria consumo como tributo. Nem estimado (default de
# código, §D7) nem recolhido (sinal contaminado).
def test_s8_nao_afirma_das_nem_com_o_balde_populado() -> None:
    """O s8 fica em SILÊNCIO sobre DAS enquanto o balde estiver contaminado."""
    payload = e5_payload()
    payload["fluxo_caixa"]["despesas_por_categoria"] = {"moradia": 1_000.0, "das_simples": 9_600.0}
    s8 = summaries(payload, GOALS_A)["s8"]
    assert "DAS" not in s8, s8
    assert "R$ 0,00" not in s8, s8


def test_s8_nao_publica_honorario_de_contador_fabricado() -> None:
    """`contador_mensal` não existe em `bundle["tributario"]` — o
    `get(..., 0)` publicava "(R$ 0,00/mês)" em todo workspace com contador."""
    goals = {
        **GOALS_A,
        "tributario": {**GOALS_A["tributario"], "contador_nome": "Escritório contábil"},
    }
    s8 = summaries(e5_payload(), goals)["s8"]
    assert "Contador cadastrado." in s8, s8
    assert "R$ 0,00" not in s8, s8


# A contagem que o narrador tem (`investimentos.n_imoveis_total`, do baseline
# IRPF) não é a que a tabela da S4 renderiza (`real_estate.imoveis`, filtro
# estrito por `codigo_rfb`). Medido no dogfood: 6 vs 4 na MESMA seção. E a fonte
# da seção nem existe quando o narrador roda (`_e5n_populate_real_estate` vem
# depois de montar as narrativas), então "afirma se as duas concordarem" seria
# guarda em ramo morto. O regex cobre qualquer contagem, não só a divergente.
_CONTAGEM_IMOVEIS_RE = re.compile(r"\d+\s+im[óo]ve(l|is)")


def test_s4_nao_afirma_contagem_de_imoveis() -> None:
    """Divergência 6 (narrador) vs 4 (tabela da seção) ⇒ o s4 não conta imóveis."""
    payload = e5_payload()
    payload["investimentos"] = {"n_imoveis_total": 6, "instituicoes_por_membro": []}
    payload["real_estate"] = {"imoveis": [{"codigo_rfb": str(i)} for i in range(4)]}
    s4 = summaries(payload, GOALS_A)["s4"]
    achado = _CONTAGEM_IMOVEIS_RE.search(s4)
    assert achado is None, (
        f"o s4 afirmou contagem de imóveis ({achado.group(0)!r}) a partir de "
        "`n_imoveis_total`, que não é a fonte da tabela da S4 "
        f"(`real_estate.imoveis`). Texto: {s4}"
    )
    assert "Portfólio imobiliário com" in s4, s4


def test_s4_sem_valor_de_imovel_nao_afirma_ausencia_de_imovel() -> None:
    """Valor zerado é ausência de VALOR, não de imóvel — a contagem não é nossa."""
    payload = e5_payload()
    payload["patrimonio"]["residencia"] = 0
    payload["patrimonio"]["imoveis_investimento"] = 0
    payload["investimentos"] = {"n_imoveis_total": 6, "instituicoes_por_membro": []}
    s4 = summaries(payload, GOALS_A)["s4"]
    assert "Sem valor de imóveis identificado" in s4, s4
    assert _CONTAGEM_IMOVEIS_RE.search(s4) is None, s4


def test_s4_nao_publica_valor_zero_de_residencia() -> None:
    """`residência (R$ 0,00)` lê-se como "sua casa não vale nada" — parcela sai."""
    payload = e5_payload()
    payload["patrimonio"]["residencia"] = 0
    s4 = summaries(payload, GOALS_A)["s4"]
    assert "residência" not in s4, s4
    assert "imóveis de investimento somando" in s4, s4


def test_s3_nao_inventa_contagem_de_categorias() -> None:
    """`composicao` vazia ⇒ o s3 declara a ausência (era `len(...) or 5`)."""
    payload = e5_payload()
    payload["patrimonio"]["composicao"] = []
    s3 = summaries(payload, GOALS_A)["s3"]
    assert "5 categorias" not in s3, s3
    assert "ainda não classificada por categoria" in s3, s3


def test_s3_conta_categorias_quando_ha_composicao() -> None:
    """A supressão é condicional: com composição, a contagem volta."""
    payload = e5_payload()
    payload["patrimonio"]["composicao"] = [
        {"categoria": c, "valor": 1.0} for c in ("imoveis", "rf", "rv")
    ]
    assert "entre 3 categorias de ativos" in summaries(payload, GOALS_A)["s3"]


def test_s9_nao_afirma_ausencia_de_seguro_sem_sinal() -> None:
    """`protecao_patrimonial` ausente ⇒ o s9 não afirma que não há cobertura."""
    s9 = summaries(e5_payload(), GOALS_A)["s9"]
    assert "Seguros de vida e invalidez inexistentes" not in s9, s9


def test_s9_afirma_ausencia_quando_gap_qualitativo_sinaliza() -> None:
    """Com `gap_qualitativo[vida].flag = True`, a afirmação é legítima."""
    payload = e5_payload()
    payload["protecao_patrimonial"] = {
        "gap_qualitativo": [{"categoria": "vida", "flag": True, "rationale": "sem apólice"}]
    }
    s9 = summaries(payload, GOALS_A)["s9"]
    assert "Seguros de vida e invalidez inexistentes" in s9, s9


def test_s9_empty_state_nao_duplica_cta_do_componente() -> None:
    """`_S9_EMPTY` imprime acima do <EmptyState/> da S9 — CTA só no componente."""
    from pipeline.domain.services.narrativas.summaries_narrator import _S9_EMPTY

    for cta in ("Plano de Ação", "Cadastrar", "Mapeie"):
        assert cta not in _S9_EMPTY, (
            f"`{cta}` em _S9_EMPTY duplica o call-to-action do <EmptyState/> "
            "que renderiza logo abaixo, com wording diferente"
        )
