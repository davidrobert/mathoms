"""LC06 (A42.l3) — a P0 nº 1 da rubrica passa a ser exercitada sobre o agregado certo.

O check que rodava (`investment_double_count`) varre o balde E4 `investimentos` — origem
E2, 18 posições. O eixo cross-year/cross-declarante vive em `investimentos_consolidados`
do E1.5c, que viaja dentro do balde `patrimonio`: população e vetor DIFERENTES.
"""

from __future__ import annotations

from dev.ledger_baseline_invariants import (
    baseline_invariants,
    fmt_baseline_invariants,
    pat_1,
)
from dev.ledger_verdicts import CONSERVADO, NAO_VERIFICAVEL, PERDA_SILENCIOSA


def _inv(**kw) -> dict:
    base = {"investment_id": "i1", "proprietario": "A", "valores_31_12": {"2024": 100.0}}
    base.update(kw)
    return base


def _imo(**kw) -> dict:
    base = {"property_id": "p1", "proprietario": "A", "valores_31_12": {"2024": 500.0}}
    base.update(kw)
    return base


def _por(id_: str, r: list):
    return next(x for x in r if x.id == id_)


# ── partição de julgabilidade: invariante que não discrimina NÃO diz "conservado" ──


def test_pat1_com_um_ano_so_nao_se_declara_conservado() -> None:
    """Com um ano só, max-ano e Σ-anos coincidem: o invariante seria `P ∨ ¬P`, o modo de
    falha que a A42.l16 mediu no CV18. Ele declara que não julga."""
    r = pat_1(
        {
            "investimentos_consolidados": [_inv()],
            "patrimonio_por_ano": {"2024": {"total_bens": 100.0}},
        }
    )

    assert r.verdict == NAO_VERIFICAVEL
    assert "COINCIDEM" in r.detail and r.julgaveis == 0


def test_pat1_pega_o_agregado_que_somou_os_anos() -> None:
    """O defeito que PAT-1 nomeia: a contribuição vira Σ anos em vez de max-ano."""
    item = _inv(valores_31_12={"2023": 40.0, "2024": 100.0})
    r = pat_1(
        {
            "investimentos_consolidados": [item],
            "patrimonio_por_ano": {"2024": {"total_bens": 140.0}},
        }
    )

    assert r.verdict == PERDA_SILENCIOSA
    assert "somou os anos" in r.detail and r.julgaveis == 1


def test_pat1_fecha_quando_o_agregado_usa_o_ano_maximo() -> None:
    item = _inv(valores_31_12={"2023": 40.0, "2024": 100.0})
    r = pat_1(
        {
            "investimentos_consolidados": [item],
            "patrimonio_por_ano": {"2024": {"total_bens": 100.0}},
        }
    )

    assert r.verdict == CONSERVADO and r.julgaveis == 1


def test_pat1_declara_quando_o_total_tem_categorias_de_fora() -> None:
    """Nem toda divergência é o defeito: o total pode incluir categorias fora das listas
    consolidadas. O invariante diz isso em vez de acusar."""
    item = _inv(valores_31_12={"2023": 40.0, "2024": 100.0})
    r = pat_1(
        {
            "investimentos_consolidados": [item],
            "patrimonio_por_ano": {"2024": {"total_bens": 777.0}},
        }
    )

    assert r.verdict == NAO_VERIFICAVEL
    assert "categorias de fora" in r.detail


# ── INV-1/2 e IMO-1/2: identidade viva 2× e identidade partida por declarante ──


def test_inv1_pega_investment_id_vivo_duas_vezes() -> None:
    r = _por("INV-1", baseline_invariants({"investimentos_consolidados": [_inv(), _inv()]}))

    assert r.verdict == PERDA_SILENCIOSA and "dupla-contagem" in r.detail


def test_inv2_pega_co_declaracao_que_virou_duas_linhas() -> None:
    """ADR-246: item co-declarado é UMA linha com `proprietarios` união."""
    itens = [_inv(proprietario="A"), _inv(proprietario="B")]
    r = _por("INV-2", baseline_invariants({"investimentos_consolidados": itens}))

    assert r.verdict == PERDA_SILENCIOSA and "identidade(s) partida(s)" in r.detail


def test_imo1_e_imo2_cobrem_o_mesmo_par_para_imovel() -> None:
    dobrado = baseline_invariants({"imoveis_consolidados": [_imo(), _imo()]})
    partido = baseline_invariants(
        {"imoveis_consolidados": [_imo(proprietario="A"), _imo(proprietario="B")]}
    )

    assert _por("IMO-1", dobrado).verdict == PERDA_SILENCIOSA
    assert _por("IMO-2", partido).verdict == PERDA_SILENCIOSA


def test_id_ausente_nao_vira_conservado() -> None:
    """Item sem identidade declarada não é "limpo": é não-julgável, e a partição diz."""
    r = _por(
        "INV-1", baseline_invariants({"investimentos_consolidados": [_inv(investment_id=None)]})
    )

    assert r.verdict == NAO_VERIFICAVEL and r.julgaveis == 0


def test_mem1_pega_proprietario_sem_entrada_em_membros() -> None:
    payload = {"membros": [{"nome": "A"}], "investimentos_consolidados": [_inv(proprietario="Z")]}
    r = _por("MEM-1", baseline_invariants(payload))

    assert r.verdict == PERDA_SILENCIOSA and "sem entrada em `membros`" in r.detail


# ── o eixo inteiro ──


def test_balde_ausente_nao_afirma_cobertura() -> None:
    r = baseline_invariants(None)

    assert r[0].verdict == NAO_VERIFICAVEL


def test_os_seis_invariantes_saem_sempre_com_a_particao_impressa() -> None:
    """Silêncio não é opção: invariante que não julga aparece com o motivo."""
    linhas = fmt_baseline_invariants(baseline_invariants({}))
    texto = "\n".join(linhas)

    for ident in ("PAT-1", "INV-1", "INV-2", "IMO-1", "IMO-2", "MEM-1"):
        assert f"`{ident}`" in texto
    assert "julgável em" in texto and "exercitados: **0/6**" in texto


def test_corpus_limpo_e_julgavel_sai_conservado_nos_quatro_eixos_de_identidade() -> None:
    payload = {
        "membros": [{"nome": "A"}, {"nome": "B"}],
        "investimentos_consolidados": [_inv(), _inv(investment_id="i2", proprietario="B")],
        "imoveis_consolidados": [_imo(), _imo(property_id="p2", proprietario="B")],
    }
    r = baseline_invariants(payload)

    assert [_por(i, r).verdict for i in ("INV-1", "INV-2", "IMO-1", "IMO-2", "MEM-1")] == [
        CONSERVADO
    ] * 5
