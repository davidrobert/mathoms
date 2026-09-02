"""Destino de leitura derivado — totalidade, anti-envelhecimento e não-inércia (A40.l117)."""

from __future__ import annotations

import typing

import pytest

from backend.app.generated.report_layout import LAYOUT
from backend.app.services.parecer_section_route import (
    _METRICA_PARA_CARD,
    _RAIZ_COM_SEDE,
    _TEMA_PARA_CARD,
    DESTINO_FALLBACK,
    card_para_secao,
    resolve_destino,
)
from pipeline.domain.services.kpi_target_catalog import METRICA_KEYS
from pipeline.llm.schemas.parecer_planejador import SectionId, TemaCanonico

_E5_COMPLETO = {"real_estate": {"x": 1}, "irpf_kpis": {"x": 1}, "protecao_patrimonial": {"x": 1}}


def _secoes_habilitadas() -> set[str]:
    return {s.id for s in LAYOUT.estrategico.sections if s.enabled}


class TestTotalidade:
    def test_todo_tema_resolve_para_secao_do_enum(self):
        for tema in typing.get_args(TemaCanonico):
            destino, passo = resolve_destino(tema_canonico=tema, e5_data=_E5_COMPLETO)
            assert destino in typing.get_args(SectionId), (tema, destino)
            assert passo != "fallback", f"tema {tema!r} caiu no terminal"

    def test_toda_metrica_do_vocabulario_fechado_tem_destino(self):
        """`METRICA_KEYS` é derivado do catálogo; chave nova sem entrada reprova aqui."""
        assert set(_METRICA_PARA_CARD) == set(METRICA_KEYS), (
            f"faltam={sorted(set(METRICA_KEYS) - set(_METRICA_PARA_CARD))} "
            f"sobram={sorted(set(_METRICA_PARA_CARD) - set(METRICA_KEYS))}"
        )
        for key in METRICA_KEYS:
            destino, passo = resolve_destino(metrica_key=key, e5_data=_E5_COMPLETO)
            assert passo == "metrica_key" and destino in typing.get_args(SectionId)


class TestAntiEnvelhecimento:
    """O mapa aponta para CARD; card muda de seção e o destino tem de seguir."""

    @pytest.mark.parametrize("tabela", [_TEMA_PARA_CARD, _METRICA_PARA_CARD, _RAIZ_COM_SEDE])
    def test_todo_card_citado_existe_no_layout(self, tabela):
        mapa = card_para_secao()
        orfaos = sorted({c for c in tabela.values() if c not in mapa})
        assert not orfaos, f"card citado não existe no layout: {orfaos}"

    def test_todo_destino_e_secao_habilitada(self):
        mapa, habilitadas = card_para_secao(), _secoes_habilitadas()
        for tabela in (_TEMA_PARA_CARD, _METRICA_PARA_CARD, _RAIZ_COM_SEDE):
            for card in tabela.values():
                assert mapa[card] in habilitadas, (card, mapa[card])

    def test_mover_o_card_de_secao_move_o_destino(self, monkeypatch):
        """Contrafactual do desenho: se isto falhar, o mapa virou `tema → seção` na prática."""
        antes, _ = resolve_destino(tema_canonico="Liquidez", e5_data=_E5_COMPLETO)
        monkeypatch.setattr(
            "backend.app.services.parecer_section_route.card_para_secao",
            lambda: {**card_para_secao(), "reserva_emergencia": "S10"},
        )
        depois, _ = resolve_destino(tema_canonico="Liquidez", e5_data=_E5_COMPLETO)
        assert antes == "S1" and depois == "S10"


class TestPrecedencia:
    """Tema primeiro; âncora só desempata dentro da allowlist de raízes com sede única."""

    def test_ancora_de_raiz_de_armazenamento_nao_vence_o_tema(self):
        """Regressão do caso que inverteria a regra: renda passiva ancorada no estoque."""
        destino, passo = resolve_destino(
            tema_canonico="Renda passiva",
            ancora_paths=["$.investimentos.total_financeiro"],
            e5_data=_E5_COMPLETO,
        )
        assert (destino, passo) == ("S7", "tema")

    def test_ancora_com_sede_unica_desempata(self):
        destino, passo = resolve_destino(
            tema_canonico="Alocação",
            ancora_paths=["$.exposicao_cambial.total_brl"],
            e5_data=_E5_COMPLETO,
        )
        assert (destino, passo) == ("S1", "raiz_com_sede")

    def test_imovel_vai_para_real_estate_e_nao_para_a_carteira(self):
        """S3 declara imóvel físico FORA da base que compara; S4 publica o peso."""
        for tipo in ("risco", "sugestao"):
            destino, _ = resolve_destino(
                tema_canonico="Alocação",
                ancora_paths=["$.investimentos.total_imoveis_investimento"],
                e5_data=_E5_COMPLETO,
            )
            assert destino == "S4", tipo

    def test_risco_e_sugestao_irmaos_pousam_juntos(self):
        kw = dict(
            tema_canonico="Alocação", ancora_paths=["$.investimentos.total_imoveis_investimento"]
        )
        assert resolve_destino(**kw, e5_data=_E5_COMPLETO) == resolve_destino(
            **kw, e5_data=_E5_COMPLETO
        )


class TestSecaoOculta:
    """Destino morto é PIOR que o status quo: manda o leitor a seção que não imprime."""

    def test_sem_real_estate_o_destino_degrada(self):
        destino, passo = resolve_destino(
            tema_canonico="Alocação",
            ancora_paths=["$.investimentos.total_imoveis_investimento"],
            e5_data={},
        )
        assert (destino, passo) == ("S1", "raiz_com_sede+degradado")

    def test_sem_cobertura_a_metrica_de_protecao_degrada_para_a_lacuna(self):
        assert resolve_destino(metrica_key="protecao_custo_premio", e5_data={})[0] == "S9"

    def test_sem_payload_nao_degrada(self):
        """Ausência de sinal não é sinal: sem E5 para julgar, o destino é o declarado."""
        assert resolve_destino(metrica_key="protecao_custo_premio")[0] == "S_PROTECAO"


def test_fallback_existe_e_e_secao_real():
    assert DESTINO_FALLBACK in typing.get_args(SectionId)
    assert DESTINO_FALLBACK in _secoes_habilitadas()
