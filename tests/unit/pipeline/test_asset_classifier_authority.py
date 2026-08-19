"""Tests — contrato de autoridade do classificador de ativos (DE-1 · §r7).

Fixtures sintéticas, PII-zero: nenhum nome real de instituição, pessoa ou valor.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.asset_classifier import (  # noqa: E402
    AssetAuthority,
    AssetClassification,
    AtivoSemHaystackWarning,
    classify_asset,
    classify_asset_outcome,
)
from pipeline.domain.services.investimentos_classes_analyzer import (  # noqa: E402
    InvestimentosClassesAnalyzer,
    InvestimentosClassesConfig,
)

_AMOSTRAS = (
    ("", ""),
    ("outros", "xyz"),
    ("investimento", "CDB"),
    ("investimento", "HGLG11"),
    ("poupanca", "saldo"),
    ("conta_bancaria", ""),
    ("previdencia", "plano"),
)


# Marca sintética que É keyword de `Caixa` na config do teste. Sem isso a
# mutação não é plausível: uma marca que não bate keyword nenhuma devolve
# `Outros` com e sem o fix, e o teste passa nos dois lados do flip.
_MARCA_CURTA = "bancoalfa"
_MARCA_CANONICA = "banco_alfa_pagamentos"

# Reproduz a forma do caso medido em r5→r7: a forma curta bate keyword de um
# balde nomeado; a canônica normaliza para dois tokens e não bate nada.
_SCORING_COM_MARCA = {
    "asset_class_keywords": {"Caixa": ["conta corrente", _MARCA_CURTA, "saldo em conta"]}
}


def _analyzer_com_marca_de_caixa() -> InvestimentosClassesAnalyzer:
    return InvestimentosClassesAnalyzer(
        InvestimentosClassesConfig.from_configs(scoring=_SCORING_COM_MARCA)
    )


def _carteira_de_duas_linhas(instituicao: str) -> dict:
    """Duas linhas cuja classe só pode vir de `tipo`/`descricao` — nunca da marca."""
    linhas = [("conta_bancaria", "saldo", 1000.0), ("fundo_investimento", "quotas", 2000.0)]
    return {
        "investimentos": [
            {"tipo": t, "descricao": d, "valor": v, "instituicao": instituicao}
            for t, d, v in linhas
        ]
    }


def _mix(resultado) -> dict:
    return {c.categoria: c.valor for c in resultado.tabela_classes}


class TestInstituicaoForaDaEntrada:
    """O teste central de DE-1: a marca da instituição deixa de decidir classe."""

    def test_classify_asset_nao_aceita_instituicao(self):
        # Assinatura é contrato: `instituicao` é propriedade do institution_catalog
        # (ADR-137/ADR-384), não do classificador. Posicional extra = TypeError.
        with pytest.raises(TypeError):
            classify_asset("conta_bancaria", "saldo", "qualquer-coisa")

    @pytest.mark.parametrize(
        "forma_canonica",
        ["bancoalfa", "banco_alfa_pagamentos", "BANCO ALFA S.A.", "alfa-pagamentos-sa"],
    )
    def test_forma_canonica_da_instituicao_nao_move_a_classe(self, forma_canonica):
        # O renomeio `nubank` -> `nu_pagamentos` no catálogo de instituições
        # reclassificava ativo sem diff no classificador, sem revisão e sem sinal.
        # A instituição do item existe no payload e nenhuma forma dela move a classe.
        item = {
            "tipo": "fundo_investimento",
            "descricao": "quotas",
            "valor": 1000.0,
            "instituicao": forma_canonica,
        }
        resultado = InvestimentosClassesAnalyzer().analyze([{"investimentos": [item]}])
        assert {c.categoria for c in resultado.tabela_classes} == {"Outros"}

    def test_troca_de_instituicao_no_golden_nao_move_nenhum_balde(self):
        # Mutação que prova o fix: devolver `instituicao` ao haystack de
        # `classify_asset_outcome` faz este teste falhar. A config do analyzer
        # registra `_MARCA_CURTA` como keyword de `Caixa`, então antes do fix a
        # forma curta somava R$3.000 em `Caixa` e a canônica em `Outros` — a
        # mesma assinatura compensatória medida entre r5 e r7. Sem essa keyword
        # as duas formas caem em `Outros` e o teste passa nos dois lados.
        analyzer = _analyzer_com_marca_de_caixa()
        curta = analyzer.analyze([_carteira_de_duas_linhas(_MARCA_CURTA)])
        canonica = analyzer.analyze([_carteira_de_duas_linhas(_MARCA_CANONICA)])
        assert _mix(curta) == _mix(canonica) == {"Outros": 3000.0}


class TestAutoridadeDeclarada:
    def test_keyword_declara_autoridade_keyword(self):
        r = classify_asset_outcome("investimento", "CDB pos-fixado")
        assert r == AssetClassification(classe="Renda Fixa", autoridade=AssetAuthority.KEYWORD)

    def test_sem_match_declara_outros(self):
        r = classify_asset_outcome("outros", "ativo exotico xyz")
        assert r.classe == "Outros"
        assert r.autoridade is AssetAuthority.SEM_MATCH

    def test_sem_haystack_declara_outros(self):
        r = classify_asset_outcome("", "")
        assert r.classe == "Outros"
        assert r.autoridade is AssetAuthority.SEM_HAYSTACK

    def test_moeda_e_lastro_nascem_no_shape_e_vazios_no_pr1(self):
        # Declarados agora para não haver segunda mudança de contrato nos 5
        # consumidores; populados só quando o catálogo entrar (PR2).
        r = classify_asset_outcome("investimento", "CDB pos-fixado")
        assert r.moeda is None
        assert r.lastro is None

    def test_degrau_1_e_membro_do_enum_sem_produtor_no_pr1(self):
        # Deliberado: quem emite CONCLUSIVO/PRESUNTIVO/SEM_MAPA é o degrau 1
        # (`_TIPO_TO_CLASSE`), que entra no PR2. Enum com membro inalcançável é
        # dívida se ninguém souber que é intencional — este teste é o registro.
        produzidas = {classify_asset_outcome(t, d).autoridade for t, d in _AMOSTRAS}
        sem_produtor = {
            AssetAuthority.CONCLUSIVO,
            AssetAuthority.PRESUNTIVO,
            AssetAuthority.SEM_MAPA,
        }
        assert produzidas.isdisjoint(sem_produtor)
        assert produzidas <= {
            AssetAuthority.KEYWORD,
            AssetAuthority.TICKER,
            AssetAuthority.SEM_MATCH,
            AssetAuthority.SEM_HAYSTACK,
        }

    def test_imovel_declara_origem_em_vez_de_nulo(self):
        # `None` significaria ao mesmo tempo "a origem decidiu" e "campo não
        # populado" — a ambiguidade que o RV7-04 denuncia, com o agravante de o
        # consumidor do DE-2 ter de destratá-la por item.
        from pipeline.domain.services.top_ativos_analyzer import TopAtivosAnalyzer

        bens = {"imoveis": [{"valor_31_12_ano_base": 500_000.0, "property_id": "p-1"}]}
        (ativo,) = TopAtivosAnalyzer().analyze([("titular", bens)]).top_ativos
        assert ativo.classe == "Imóveis Investimento"
        assert ativo.autoridade == AssetAuthority.ORIGEM.value
        assert ativo.autoridade is not None

    def test_sem_mapa_conta_como_nao_classificado(self):
        # Contrato pré-declarado: quando o degrau 1 emitir SEM_MAPA, a supressão
        # graduada já o contabiliza — não é `Outros` mudo.
        vo = AssetClassification(classe="Outros", autoridade=AssetAuthority.SEM_MAPA)
        assert vo.nao_classificado


class TestSemMatchDiferenteDeSemHaystack:
    """Asserção COMPORTAMENTAL — o consumidor faz coisa diferente nos dois casos."""

    def test_sem_haystack_emite_warning_tipado_e_sem_match_nao(self):
        sem_haystack = classify_asset_outcome("", "")
        sem_match = classify_asset_outcome("outros", "ativo exotico xyz")

        assert [type(w) for w in sem_haystack.warnings] == [AtivoSemHaystackWarning]
        assert sem_match.warnings == ()

    def test_warning_de_sem_haystack_formata_sem_vazar_conteudo(self):
        (warning,) = classify_asset_outcome("", "   ").warnings
        texto = warning.format()
        assert "produtor" in texto
        assert isinstance(texto, str) and texto

    def test_ambos_contam_como_nao_classificado(self):
        assert classify_asset_outcome("", "").nao_classificado
        assert classify_asset_outcome("outros", "xyz").nao_classificado
        assert not classify_asset_outcome("investimento", "CDB").nao_classificado


class TestTickerNaoDecideSozinho:
    """`XXXX11` é sufixo de FII, ETF, UNIT e BDR — não prova FII."""

    @pytest.mark.parametrize(
        "descricao,esperado",
        [
            ("IVVB11", "Internacional"),
            ("BOVA11", "Ações BR"),
            ("HASH11", "Cripto"),
            ("BPAC11", "Ações BR"),
            ("TAEE11", "Ações BR"),
            ("HGLG11", "FIIs"),
        ],
    )
    def test_ticker_conhecido_resolve_para_a_classe_nomeada(self, descricao, esperado):
        assert classify_asset("investimento", descricao) == esperado

    def test_ticker_desconhecido_sem_sinal_e_declarado_nao_classificado(self):
        r = classify_asset_outcome("investimento", "SCHP11")
        assert r.classe == "Outros"
        assert r.autoridade is AssetAuthority.SEM_MATCH

    def test_keyword_explicita_vence_o_ticker(self):
        # A keyword `ivvb` deixa de ser dead code: é ela quem decide aqui.
        r = classify_asset_outcome("investimento", "IVVB11")
        assert r.classe == "Internacional"
        assert r.autoridade is AssetAuthority.KEYWORD

    def test_ticker_declara_autoridade_ticker(self):
        r = classify_asset_outcome("investimento", "HGLG11 quotas")
        assert r.autoridade is AssetAuthority.TICKER


class TestParidadeFachadaPrimitiva:
    @pytest.mark.parametrize(
        "tipo,descricao",
        [
            ("investimento", "CDB pos-fixado"),
            ("conta_bancaria", "saldo em conta"),
            ("", ""),
            ("outros", "ativo exotico xyz"),
            ("investimento", "IVVB11"),
            ("investimento", "SCHP11"),
            ("previdencia", "PGBL"),
        ],
    )
    def test_fachada_devolve_a_classe_da_primitiva(self, tipo, descricao):
        assert classify_asset(tipo, descricao) == classify_asset_outcome(tipo, descricao).classe


# Os limiares não são novos: 2pp é `SEVERITY_ALINHADO_MAX_PP` e 10pp é o da
# ADR-141 item 9. A incerteza de classificação não pode ser maior que a menor
# diferença que o produto trata como acionável.
class TestSupressaoGraduadaPorIncerteza:
    """Os 3 degraus exercitados no ``AlocacaoDeviationResult`` REAL, sem mock."""

    @staticmethod
    def _resultado():
        from pipeline.domain.services.alocacao_alvo_deviation import (
            AlocacaoAlvoDeviationCalculator,
        )

        tabela = [
            {"categoria": "Renda Fixa", "valor": 60000.0},
            {"categoria": "Ações BR", "valor": 30000.0},
            {"categoria": "Outros", "valor": 10000.0},
        ]
        return AlocacaoAlvoDeviationCalculator().calculate(
            tabela, {"rf_pos_pct": 40.0, "acoes_br_pct": 40.0, "fiis_pct": 20.0}
        )

    def test_abaixo_de_2pct_publica_tudo(self):
        base = self._resultado()
        suprimido = base.suprimir_por_incerteza(1.9)
        assert suprimido.desvio_max_pct == base.desvio_max_pct
        assert suprimido.next_aporte_classe == base.next_aporte_classe
        assert suprimido.motivo_supressao is None

    def test_entre_2_e_10pct_cai_so_a_classe_do_proximo_aporte(self):
        base = self._resultado()
        suprimido = base.suprimir_por_incerteza(5.0)
        assert suprimido.next_aporte_classe is None
        assert suprimido.desvio_max_pct == base.desvio_max_pct
        assert "nao_classificado" in (suprimido.motivo_supressao or "")

    def test_acima_de_10pct_cai_tambem_o_desvio_maximo(self):
        suprimido = self._resultado().suprimir_por_incerteza(10.0)
        assert suprimido.next_aporte_classe is None
        assert suprimido.desvio_max_pct is None
        assert "nao_classificado" in (suprimido.motivo_supressao or "")

    def test_descricao_da_carteira_sobrevive_em_todos_os_degraus(self):
        base = self._resultado()
        for pct in (1.0, 5.0, 50.0):
            suprimido = base.suprimir_por_incerteza(pct)
            assert suprimido.carteira_liquida_brl == base.carteira_liquida_brl
            assert suprimido.comparaveis == base.comparaveis

    def test_motivo_preexistente_nao_e_sobrescrito(self):
        # Cobertura por membro e incerteza de classe são causas distintas; perder
        # a primeira ao acrescentar a segunda apagaria a razão que já governava.
        base = self._resultado().suprimir_prescricao("cobertura_incompleta: conjuge")
        suprimido = base.suprimir_por_incerteza(5.0)
        assert "cobertura_incompleta" in suprimido.motivo_supressao
        assert "nao_classificado" in suprimido.motivo_supressao


class TestNaoClassificadoPctNoPayload:
    def test_pct_e_a_fracao_da_carteira_financeira(self):
        carteira = {
            "investimentos": [
                {"tipo": "investimento", "descricao": "CDB pos-fixado", "valor": 900.0},
                {"tipo": "outros", "descricao": "ativo exotico xyz", "valor": 100.0},
            ]
        }
        resultado = InvestimentosClassesAnalyzer().analyze([carteira])
        assert resultado.nao_classificado_pct == pytest.approx(10.0)
        assert resultado.to_legacy_dict()["nao_classificado_pct"] == pytest.approx(10.0)

    def test_carteira_toda_classificada_publica_zero(self):
        carteira = {
            "investimentos": [
                {"tipo": "investimento", "descricao": "CDB pos-fixado", "valor": 900.0}
            ]
        }
        assert InvestimentosClassesAnalyzer().analyze([carteira]).nao_classificado_pct == 0.0
