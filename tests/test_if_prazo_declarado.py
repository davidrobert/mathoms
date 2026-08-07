"""Alvo do Monte Carlo é o prazo que a família declarou (ADR-369 D2)."""

# Três provas, e a primeira é a que decide se a lane é real:
#
# 1. Trava por AST no call-site do stage — asserção sobre o VALOR deixaria um
#    refactor reintroduzir a derivação (`if_projection.idade_titular_if`) com o
#    teste verde. O que não pode voltar é a expressão, não o número.
# 2. Grade de FOLGA (`prazo_declarado − prazo_determinístico`). A grade de
#    "≥6 planos" do critério original era insatisfazível: os oito planos da
#    medição da ADR-361 têm todos folga zero, e é por isso que a `prob` era
#    plana — continuaria plana com QUALQUER fonte de alvo.
# 3. Os três estados de ausência, cada um com o seu motivo, e a prova de que
#    prazo vencido emite ausência em vez de `prob = 0`.

from __future__ import annotations

import ast
import inspect
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.domain.services import e5_analyzer_adapter
from pipeline.domain.services.if_monte_carlo import (
    IFMonteCarloConfig,
    PrazoDeclarado,
    run_monte_carlo_if,
)

_ANO_BASE = 2026
_DECLARADO_EM = "2026-03-01"


# =============================================================================
# 1. Trava por AST no call-site
# =============================================================================


def _kwargs_do_call_site() -> dict[str, ast.expr]:
    """kwargs da chamada a ``run_monte_carlo_if`` no adapter do stage E5."""
    fonte = Path(inspect.getsourcefile(e5_analyzer_adapter)).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(fonte)):
        alvo = getattr(node, "func", None)
        if isinstance(node, ast.Call) and getattr(alvo, "id", None) == "run_monte_carlo_if":
            return {kw.arg: kw.value for kw in node.keywords if kw.arg}
    pytest.fail("chamada a run_monte_carlo_if não encontrada em e5_analyzer_adapter")


def _nome_do_no(no: ast.AST) -> str | None:
    """Identificador de um nó de expressão, se ele nomeia algo."""
    if isinstance(no, ast.Name):
        return no.id
    return no.attr if isinstance(no, ast.Attribute) else None


def _nomes_referenciados(no: ast.expr) -> set[str]:
    """Todo identificador e atributo alcançável a partir de uma expressão."""
    return {n for n in map(_nome_do_no, ast.walk(no)) if n}


def test_call_site_nao_deriva_o_alvo_da_projecao_determinstica():
    """O alvo não pode voltar a sair do projetor — é a métrica medindo a si mesma."""
    kwargs = _kwargs_do_call_site()
    assert "prazo_declarado" in kwargs, "o kwarg do alvo sumiu do call-site"
    assert "idade_meta_if" not in kwargs, "kwarg da semântica antiga ressuscitou"
    referenciados = _nomes_referenciados(kwargs["prazo_declarado"])
    proibidos = {"if_projection", "idade_titular_if", "idade_conjuge_if", "ano_if"}
    vazou = referenciados & proibidos
    assert not vazou, (
        f"o prazo passado ao Monte Carlo referencia a projeção determinística ({vazou}) — "
        "P(o modelo bater a data que ele mesmo imprimiu) é constante de modelo, não "
        "métrica do cliente (ADR-369 D2)"
    )


# =============================================================================
# 2. Grade de folga
# =============================================================================


def _config(pv: float, fv: float, pmt: float, retorno: float = 0.05) -> IFMonteCarloConfig:
    return IFMonteCarloConfig(
        patrimonio_investivel=Decimal(str(pv)),
        meta_if=Decimal(str(fv)),
        aporte_mensal=Decimal(str(pmt)),
        retorno_real_esperado=retorno,
        ano_base=_ANO_BASE,
        seed=360,
    )


def _prazo_deterministico(pv: float, fv: float, pmt: float, retorno: float = 0.05) -> int:
    """Anos até a meta sem variação de mercado — o eixo da folga."""
    w, pmt_anual = pv, pmt * 12.0
    for t in range(1, 81):
        w = w * (1 + retorno) + pmt_anual
        if w >= fv:
            return t
    return 80


def _prob_para_folga(perfil: dict, folga: int) -> float | None:
    """`prob` do plano com o prazo declarado deslocado de `folga` anos."""
    cfg = _config(**perfil)
    anos = _prazo_deterministico(**perfil) + folga
    prazo = PrazoDeclarado(anos=anos, ano_alvo=_ANO_BASE + anos, declarado_em=_DECLARADO_EM)
    return run_monte_carlo_if(
        cfg, ano_base=_ANO_BASE, prazo_declarado=prazo
    ).prob_if_ate_prazo_declarado


_FOLGAS = (-5, -2, 0, 3, 7, 12)
_PERFIS = {
    "acumulacao-media": {"pv": 500_000, "fv": 3_000_000, "pmt": 5_000},
    "patrimonio-alto": {"pv": 1_500_000, "fv": 5_000_000, "pmt": 8_000},
}


@pytest.mark.parametrize("nome", sorted(_PERFIS))
def test_prob_e_monotona_nao_decrescente_em_folga(nome: str):
    """Mais prazo nunca pode reduzir a chance — seria erro direcional."""
    # Seed FIXA por perfil (ADR-360 §Alternativa A): seed derivada do input
    # re-sortearia entre pontos da grade e quebraria a monotonia por ruído.
    probs = [_prob_para_folga(_PERFIS[nome], f) for f in _FOLGAS]
    assert all(p is not None for p in probs)
    for anterior, atual, f_ant, f_at in zip(probs, probs[1:], _FOLGAS, _FOLGAS[1:]):
        assert atual >= anterior, f"{nome}: folga {f_ant}→{f_at} reduziu a prob"


@pytest.mark.parametrize("nome", sorted(_PERFIS))
def test_amplitude_da_grade_de_folga_supera_40pp(nome: str):
    """A `prob` mede o PLANO agora: a folga move o número, a fonte do alvo não movia."""
    # A medição da ADR-361 (8 planos, todos com folga zero) achou 14,8 pp de
    # amplitude e concluiu "constante de modelo". A conclusão estava certa; a
    # causa era a folga zero, não a fonte do alvo.
    probs = [_prob_para_folga(_PERFIS[nome], f) for f in _FOLGAS]
    amplitude = (max(probs) - min(probs)) * 100
    assert amplitude > 40, f"{nome}: amplitude de apenas {amplitude:.1f} pp entre folga -5 e +12"


@pytest.mark.parametrize("nome", sorted(_PERFIS))
def test_folga_zero_e_no_maximo_um_cara_ou_coroa(nome: str):
    """Cumprir exatamente o prazo determinístico nunca é notícia confortável."""
    # DUAS forças opostas, e o co-design só contava uma. (a) `mu_log =
    # log(1+r) − ½σ²` põe a mediana simulada ATRÁS do determinístico; (b) o
    # prazo determinístico é resolvido em anos inteiros e arredonda para CIMA
    # (medido: 18,54→19 e 14,45→15, isto é 0,46-0,55 ano de folga escondida),
    # o que devolve parte do atraso. Medido em folga zero: 49,3% e 50,7% — o
    # teto de 50% que o §Co-design pinou fica do lado errado por 0,7 pp num dos
    # perfis. A banda abaixo é o envelope medido com folga, e a afirmação que
    # ela protege continua de pé: é cara-ou-coroa, não 85%.
    prob = _prob_para_folga(_PERFIS[nome], 0)
    assert 0.30 <= prob <= 0.55, f"{nome}: folga zero deu {prob:.1%}, fora de [30%, 55%]"


@pytest.mark.parametrize("nome", sorted(_PERFIS))
def test_prob_do_prazo_nunca_supera_a_da_janela_simulada(nome: str):
    """As duas probabilidades ficam adjacentes na tela; inversão seria visível."""
    perfil = _PERFIS[nome]
    cfg = _config(**perfil)
    anos = _prazo_deterministico(**perfil) + 7
    prazo = PrazoDeclarado(anos=anos, ano_alvo=_ANO_BASE + anos, declarado_em=_DECLARADO_EM)
    r = run_monte_carlo_if(cfg, ano_base=_ANO_BASE, prazo_declarado=prazo)
    assert r.prob_if_ate_prazo_declarado <= r.prob_if_ate_horizonte_simulado


# =============================================================================
# 3. Os três estados de ausência
# =============================================================================


_PLANO = {"pv": 2_000_000, "fv": 10_000_000, "pmt": 15_000}


def test_prazo_nao_declarado_emite_ausencia_com_motivo():
    """Goal semeado no onboarding não declarou nada — não há alvo a medir."""
    r = run_monte_carlo_if(_config(**_PLANO), ano_base=_ANO_BASE, prazo_declarado=None)
    assert r.prob_if_ate_prazo_declarado is None
    assert r.motivo_sem_prazo_declarado == "prazo ainda não declarado"
    assert r.prazo_declarado_anos is None and r.ano_alvo_declarado is None
    # O cone independe do alvo e continua publicado.
    assert r.ano_if_cenario_central is not None


def test_prazo_vencido_emite_ausencia_e_preserva_a_proveniencia():
    """Goal versionado permite "3 anos" em 2020 ⇒ alvo 2023, no passado."""
    prazo = PrazoDeclarado(anos=3, ano_alvo=2023, declarado_em="2020-05-01")
    r = run_monte_carlo_if(_config(**_PLANO), ano_base=_ANO_BASE, prazo_declarado=prazo)
    assert r.prob_if_ate_prazo_declarado is None
    assert r.motivo_sem_prazo_declarado == "prazo declarado já venceu"
    # A proveniência sobrevive: o usuário precisa ver QUAL prazo venceu.
    assert (r.prazo_declarado_anos, r.ano_alvo_declarado) == (3, 2023)


def test_prazo_vencido_nao_publica_zero():
    """`prob = 0` é aritmeticamente correto e inútil (raciocínio do D8/ADR-361)."""
    # "0%" afirma "nenhuma simulação atinge"; o que houve é que a pergunta
    # deixou de se aplicar. São frases diferentes e o cliente decide sobre elas.
    prazo = PrazoDeclarado(anos=3, ano_alvo=2023, declarado_em="2020-05-01")
    r = run_monte_carlo_if(_config(**_PLANO), ano_base=_ANO_BASE, prazo_declarado=prazo)
    assert r.prob_if_ate_prazo_declarado != 0.0


def test_prazo_alem_da_janela_clampa_com_flag_e_publica_piso():
    """Declarável até 50, janela 40: clampa — estender mudaria a base da censura."""
    prazo = PrazoDeclarado(anos=48, ano_alvo=_ANO_BASE + 48, declarado_em=_DECLARADO_EM)
    cfg = _config(**_PLANO)
    r = run_monte_carlo_if(cfg, ano_base=_ANO_BASE, prazo_declarado=prazo)
    assert r.prazo_declarado_truncado is True
    assert r.prazo_declarado_anos == 48, "publica o DECLARADO, não o clampado"
    # É piso, não teto: truncar a janela só remove sucessos. O número publicado
    # coincide com o da janela porque é literalmente ele.
    assert r.prob_if_ate_prazo_declarado == r.prob_if_ate_horizonte_simulado
    assert r.horizonte_simulado_anos == cfg.horizonte_simulado_anos


def test_prazo_dentro_da_janela_nao_levanta_a_flag():
    """Mutação-guarda: flag sempre ligada passaria o teste acima sozinha."""
    prazo = PrazoDeclarado(anos=20, ano_alvo=_ANO_BASE + 20, declarado_em=_DECLARADO_EM)
    r = run_monte_carlo_if(_config(**_PLANO), ano_base=_ANO_BASE, prazo_declarado=prazo)
    assert r.prazo_declarado_truncado is False
    assert r.prob_if_ate_prazo_declarado < r.prob_if_ate_horizonte_simulado


def test_ancoragem_e_absoluta_nao_relativa_ao_run():
    """ "15 anos" em 2026 relido em 2030 significa 2041, não 2045."""
    # Sem a âncora absoluta o compromisso escorrega um ano a cada re-run — o
    # cliente nunca alcançaria a própria data.
    prazo = PrazoDeclarado(anos=15, ano_alvo=2041, declarado_em="2026-03-01")
    em_2030 = run_monte_carlo_if(_config(**_PLANO), ano_base=2030, prazo_declarado=prazo)
    assert em_2030.ano_alvo_declarado == 2041
    # 11 anos restantes em 2030, não 15: a janela medida encolheu com o tempo.
    em_2026 = run_monte_carlo_if(_config(**_PLANO), ano_base=2026, prazo_declarado=prazo)
    assert em_2030.prob_if_ate_prazo_declarado < em_2026.prob_if_ate_prazo_declarado
