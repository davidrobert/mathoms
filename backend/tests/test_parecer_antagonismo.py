"""Par P1 que se cancela na mesma classe é rebaixado (§r7 FP-6, braço 2).

O replay usa o par **medido no r7** — "reduzir a concentração em renda fixa" +
"desenvolver estratégia de previdência privada" — que hoje passa verde. Previdência
é componente da comparável que a outra sugestão manda reduzir
(`_BUCKET_TO_COMPARABLE["Previdência"] == "renda_fixa"`).
"""

from __future__ import annotations

import hashlib

from backend.app.services.parecer_antagonismo import rebaixa_sugestoes_antagonicas
from pipeline.llm.schemas.parecer_planejador import Sugestao

WS = "ws-teste"

# Texto do r7, encurtado ao que carrega verbo + classe (sem PII, sem valor real).
ACAO_REDUZ_RF = (
    "Reduzir gradualmente a concentração em renda fixa e ampliar diversificação por "
    "classe (renda variável brasileira, FIIs, internacional) via rebalanceamento por aporte"
)
ACAO_AUMENTA_PREV = (
    "Desenvolver estratégia de previdência privada integrada ao planejamento "
    "patrimonial e sucessório"
)


def _sug(
    acao: str, *, prioridade: str = "P1", impacto: str = "impacto sintetico de teste"
) -> Sugestao:
    return Sugestao(
        prioridade=prioridade,
        acao=acao,
        impacto_qualitativo=impacto,
        ancora_metodologica="convergencia",
        tema_canonico="Alocação",
        confianca="alta",
        section_id="S3",
        suggestion_dedup_key=hashlib.sha256(acao.encode()).hexdigest(),
    )


def test_par_medido_no_r7_dispara_e_rebaixa_quem_aumenta():
    saida, n = rebaixa_sugestoes_antagonicas(
        [_sug(ACAO_REDUZ_RF), _sug(ACAO_AUMENTA_PREV)], workspace_id=WS
    )

    assert n == 1
    assert saida[0].prioridade == "P1", "quem manda REDUZIR não é tocado"
    assert saida[1].prioridade == "P2" and saida[1].confianca == "media"


# Sem este teste o check vira supressor cego: rebaixaria qualquer par de P1.
def test_classes_diferentes_nao_sao_antagonicas():
    saida, n = rebaixa_sugestoes_antagonicas(
        [_sug(ACAO_REDUZ_RF), _sug("Ampliar exposição internacional via aportes")],
        workspace_id=WS,
    )

    assert n == 0
    assert [s.prioridade for s in saida] == ["P1", "P1"]


def test_condicao_de_reconciliacao_declarada_deixa_as_duas_conviverem():
    """Previdência com subjacente não-RF reduz a classe em vez de aumentá-la — o
    par deixa de ser contraditório e o produto não pode proibi-lo."""
    saida, n = rebaixa_sugestoes_antagonicas(
        [
            _sug(ACAO_REDUZ_RF),
            _sug(
                ACAO_AUMENTA_PREV,
                impacto="ganho tributario; subjacente multimercado, sem aporte novo na classe",
            ),
        ],
        workspace_id=WS,
    )

    assert n == 0
    assert saida[1].prioridade == "P1"


def test_prioridade_menor_nao_entra_no_par():
    saida, n = rebaixa_sugestoes_antagonicas(
        [_sug(ACAO_REDUZ_RF), _sug(ACAO_AUMENTA_PREV, prioridade="P2")], workspace_id=WS
    )

    assert n == 0


# Direção por proximidade, não por presença: a ação do r7 tem "reduzir" E "ampliar"
# na mesma frase, com quatro classes. Um matcher por presença marcaria renda fixa
# como aumento e o par medido nunca dispararia.
def test_direcao_vem_do_verbo_mais_proximo_nao_da_presenca():
    saida, n = rebaixa_sugestoes_antagonicas(
        [_sug(ACAO_REDUZ_RF), _sug("Ampliar alocação em renda fixa")], workspace_id=WS
    )

    assert n == 1, "renda fixa é REDUÇÃO na primeira sugestão, apesar de 'ampliar' na frase"
    assert saida[1].prioridade == "P2"
