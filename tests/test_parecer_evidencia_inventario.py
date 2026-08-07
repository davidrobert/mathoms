"""Denominador + inventário de prosa do verificador de citação (A40.l30 itens 1 e 7).

O que estes testes existem para impedir, medido: (a) item com ``ancoras: []``
contribuía 0 em ``ancoras_total`` e não gerava entry, então "densidade" conflacia
*menos âncoras por item* com *menos itens* — foi o que impediu decompor o 9→5 que a
A40.l16 mediu; (b) o detector inspecionava 3 campos dos 8+ que a R22 cobre, logo
``3,5`` era piso, não medida (defeito nº 3 da ADR-358, vivo); (c) ``_MONEY_RE`` e
``_REAIS_RE`` casavam ambos "R$ 720 mil reais" — 1 valor virava 2 tokens (defeito (a)
da ADR-304 §"evidência inflada").

Módulo próprio porque ``tests/test_parecer_evidencia_path.py`` está em 484 linhas
(limite 500 do CLAUDE.md §Code style).
"""

from __future__ import annotations

import pytest

from backend.app.services.parecer_evidencia import (
    PROSE_INVENTORY_VERSION,
    _extract_money_tokens,
    _extract_usd_tokens,
    verify_evidencia,
)
from pipeline.llm.schemas.parecer_planejador import Ancora
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from tests.test_parecer_planejador_golden import make_canned_output, make_workspace_e5

# Âncora que resolve e pareia (rotulo == root do path) — isola o que cada teste mede.
_RESERVA = ("$.reserva_emergencia.total_liquida", "reserva_emergencia")


def _drill() -> PlannerDrillDown:
    e5 = make_workspace_e5()
    return PlannerDrillDown(e5_data=e5, section_whitelist=frozenset(e5.keys()), format_hints={})


def _verify(output):
    return verify_evidencia(output=output, drill=_drill())


def _summary(output) -> dict:
    return _verify(output).summary(needs_review_triggered=False)


def _shaped(*, n_riscos: int, n_exec: int, n_ancoras: int):
    """Output com cardinalidade de itens e densidade de âncoras controladas.
    ``sugestoes_taticas``/``_estrategicas`` (1 cada no golden) ficam intactas."""
    base = _with_ancora(make_canned_output(), ancoras=[_RESERVA] * n_ancoras)
    return base.model_copy(
        update={
            "riscos": base.riscos[:n_riscos],
            "sugestoes_execucao": base.sugestoes_execucao[:n_exec],
        }
    )


def _with_ancora(output, *, ancoras: list[tuple[str, str]]):
    """Todo risco e toda sugestão recebem as mesmas âncoras — controla o denominador."""
    made = [Ancora(path=p, rotulo=r) for p, r in ancoras]
    riscos = [r.model_copy(update={"ancoras": list(made)}) for r in output.riscos]
    update = {"riscos": riscos}
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        update[horizon] = [
            s.model_copy(update={"ancoras": list(made)}) for s in getattr(output, horizon)
        ]
    return output.model_copy(update=update)


# -----------------------------------------------------------------------
# Item 1 — o denominador que faltava
# -----------------------------------------------------------------------


class TestDenominador:
    def test_itens_total_e_a_mesma_unidade_dos_counts_do_output_summary(self):
        """Invariante de unidade: ``itens_total`` tem de bater com
        ``riscos_count + Σ sugestoes_*_count`` que o stage já persiste — senão a tabela
        retroativa dos 19 runs (PR3) e a métrica forward não são a mesma coisa."""
        output = make_canned_output()
        esperado = len(output.riscos) + sum(
            len(getattr(output, h))
            for h in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")
        )
        assert _summary(output)["itens_total"] == esperado

    def test_item_sem_ancora_e_contado(self):
        """O fail-open que explica ``evidencia_failed: 0`` nos 19 runs: item com
        ``ancoras: []`` não gera entry e contribui 0 — mas agora é CONTADO."""
        output = _with_ancora(make_canned_output(), ancoras=[])
        summary = _summary(output)
        assert summary["ancoras_total"] == 0
        assert summary["evidencia_failed"] == 0  # segue fail-open (não é o fix desta lane)
        assert summary["itens_total"] == summary["itens_sem_ancora"] > 0

    def test_item_com_ancora_nao_conta_como_sem_ancora(self):
        output = _with_ancora(make_canned_output(), ancoras=[_RESERVA])
        summary = _summary(output)
        assert summary["itens_sem_ancora"] == 0
        assert summary["ancoras_total"] == summary["itens_total"]

    def test_densidade_por_item_distingue_menos_ancoras_de_menos_itens(self):
        """O ponto do denominador: dois outputs com ``ancoras_total`` IGUAL (6) e
        densidade por item diferente (2,0 vs 1,0). Sem ``itens_total`` os dois são
        indistinguíveis — é exatamente a ambiguidade do 9→5 que a A40.l16 mediu."""
        poucos_itens = _shaped(n_riscos=1, n_exec=0, n_ancoras=2)  # 3 itens × 2
        muitos_itens = _shaped(n_riscos=3, n_exec=1, n_ancoras=1)  # 6 itens × 1
        a, b = _summary(poucos_itens), _summary(muitos_itens)
        assert a["ancoras_total"] == b["ancoras_total"] == 6
        assert (a["itens_total"], b["itens_total"]) == (3, 6)

    def test_prosa_sem_contrato_de_ancora_fica_fora_do_denominador(self):
        """``diagnostico_geral``/``pontos_fortes``/``notas_metodologicas`` não têm
        ``ancoras`` no schema — inflar o denominador com eles produziria densidade
        estruturalmente inatingível."""
        output = make_canned_output()
        nao_ancoraveis = 1 + len(output.pontos_fortes) + len(output.notas_metodologicas)
        assert nao_ancoraveis > 0  # o corpus de fato exercita a classe
        assert _summary(output)["itens_total"] == len(output.riscos) + 4


# -----------------------------------------------------------------------
# Item 7 — inventário 3 → 9 campos, ANTES de qualquer re-baseline
# -----------------------------------------------------------------------


def _money_prose(output, **update):
    return _verify(output.model_copy(update=update)).money_tokens_total


class TestInventarioAmpliado:
    """Cada campo aqui era INVISÍVEL ao detector: R$ nele não contava nada."""

    def test_impacto_qualitativo_e_inspecionado(self):
        """Nomeado explicitamente na R22 e jamais inspecionado."""
        output = make_canned_output()
        sug = output.sugestoes_execucao[0].model_copy(
            update={"impacto_qualitativo": "Libera folga mensal de R$ 4.200,00 no orçamento."}
        )
        antes = _verify(output).money_tokens_total
        depois = _money_prose(output, sugestoes_execucao=[sug, *output.sugestoes_execucao[1:]])
        assert depois == antes + 1

    def test_diagnostico_geral_e_inspecionado(self):
        output = make_canned_output()
        sujo = output.diagnostico_geral + " O patrimônio líquido soma R$ 3.450.000,00 hoje."
        assert _money_prose(output, diagnostico_geral=sujo) == 1

    def test_titulo_de_risco_e_inspecionado(self):
        output = make_canned_output()
        risco = output.riscos[0].model_copy(update={"titulo": "Descoberto de R$ 9.876,00 no mês"})
        assert _money_prose(output, riscos=[risco, *output.riscos[1:]]) == 1

    def test_nota_metodologica_e_inspecionada(self):
        output = make_canned_output()
        nota = output.notas_metodologicas[0]
        sujo = nota.model_copy(update={"conteudo": nota.conteudo + " Base de R$ 720.000,00."})
        assert _money_prose(output, notas_metodologicas=[sujo]) == 1

    def test_ponto_forte_e_inspecionado(self):
        output = make_canned_output()
        forte = output.pontos_fortes[0].model_copy(
            update={"descricao": "Carteira diversificada de R$ 1.200.000,00 entre classes."}
        )
        assert _money_prose(output, pontos_fortes=[forte, *output.pontos_fortes[1:]]) == 1

    def test_caveat_de_impacto_estimado_e_inspecionado(self):
        """Prosa user-visible que entra pelo item ancorável, via ``impacto_estimado``."""
        output = make_canned_output()
        alvo = next((i, s) for i, s in enumerate(output.sugestoes_execucao) if s.impacto_estimado)
        index, sug = alvo
        impacto = sug.impacto_estimado.model_copy(
            update={"caveat": "Premissa de retorno real sobre base de R$ 500.000,00."}
        )
        sujo = sug.model_copy(update={"impacto_estimado": impacto})
        novas = list(output.sugestoes_execucao)
        novas[index] = sujo
        assert _money_prose(output, sugestoes_execucao=novas) == 1

    def test_campos_faltantes_motivo_fica_fora_do_inventario(self):
        """Critério de fronteira: **prosa renderizada ao usuário**, não "nomeado na
        R22". ``campos_faltantes`` vira ``ReviewReason`` e tem 0 readers no frontend —
        sem regra explícita o próximo agente re-litiga a inclusão."""
        from pipeline.llm.schemas.parecer_planejador import CampoFaltante

        output = make_canned_output()
        campo = CampoFaltante(field_path=None, motivo="faltou a base de R$ 720.000,00")
        assert _money_prose(output, campos_faltantes_pediria_se_iterasse=[campo]) == 0


# -----------------------------------------------------------------------
# Item 7 — dedupe de span (defeito (a) da ADR-304) e chaves de unidade separada
# -----------------------------------------------------------------------


class TestDedupeDeSpan:
    @pytest.mark.parametrize(
        "prosa",
        [
            "R$ 720 mil reais",  # _MONEY_RE (0,10) + _REAIS_RE (3,16) — spans sobrepostos
            "R$ 1.234,56 reais",
        ],
    )
    def test_um_valor_conta_um_token(self, prosa):
        assert len(_extract_money_tokens([prosa])) == 1

    def test_valores_distintos_seguem_contando_separado(self):
        assert len(_extract_money_tokens(["R$ 500,00 e depois 300 reais"])) == 2

    def test_token_vencedor_preserva_o_multiplicador(self):
        """O match com prefixo R$ vence, e é o que lê "mil" corretamente."""
        assert _extract_money_tokens(["R$ 720 mil reais"])[0].cents == 72_000_000

    def test_numero_nao_monetario_segue_ignorado(self):
        prosa = "Cobertura de 2,1 meses, 44,7% da renda, meta 25× até 2030 em 6 meses."
        assert _extract_money_tokens([prosa]) == []


class TestUnidadesSeparadas:
    def test_usd_conta_em_chave_propria_fora_de_money_tokens_total(self):
        """Medido em 2026-08-07: o exec context não contém nenhum US$ (``FormatHint``
        não tem ``usd``, ``_format_brl`` é a única saída monetária). Logo US$ na prosa
        é FABRICAÇÃO, não transcrição — e folhá-lo em ``money_tokens_total`` misturaria
        moedas num número só (defeito de unidade da ADR-358 §3)."""
        output = make_canned_output()
        sujo = output.diagnostico_geral + " A exposição externa soma US$ 250.000."
        verification = _verify(output.model_copy(update={"diagnostico_geral": sujo}))
        assert verification.money_tokens_usd == 1
        assert verification.money_tokens_total == 0

    @pytest.mark.parametrize("prosa", ["US$ 50.000", "USD 1.000", "50 mil dólares"])
    def test_formas_de_moeda_estrangeira_detectadas(self, prosa):
        assert len(_extract_usd_tokens([prosa])) == 1

    def test_metricas_contam_em_chave_propria_e_nao_poluem_pureza_de_prosa(self):
        """``valor_atual``/``target`` são "string formatada" POR CONTRATO e contêm R$
        legitimamente hoje. Incluí-los na pureza de prosa daria falso-positivo em
        massa; a chave própria é o *before* executável da RV2-01."""
        output = make_canned_output()
        metrica = output.metricas[0].model_copy(
            update={"valor_atual": "R$ 12.000,00", "target": "R$ 60.000,00"}
        )
        summary = _summary(output.model_copy(update={"metricas": [metrica]}))
        assert summary["metricas_money_tokens"] == 2
        assert summary["money_tokens_total"] == 0
        assert summary["failures_by_layer"]["number_in_prose"] == 0


class TestEstratificadorDoSummary:
    def test_summary_declara_a_versao_do_inventario(self):
        """Ausência da chave (summary servido por cache hit pré-instrumento) é
        ``unknown`` para todo leitor — nunca 0. Ver comentário do constante."""
        assert _summary(make_canned_output())["prose_inventory_version"] == PROSE_INVENTORY_VERSION

    def test_versao_do_inventario_e_dois(self):
        """Muda quando o conjunto de campos muda — é o que torna a janela do PR3
        comparável. A l31 sincroniza a enumeração da R22 e bumpa para 3."""
        assert PROSE_INVENTORY_VERSION == 2
