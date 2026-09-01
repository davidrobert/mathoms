"""Regressão — `codigo` na forma `GG-CC` perde o GRUPO e some da classificação (A42.l15).

A ficha "Bens e Direitos" passou a emitir `Grupo-Código` (`'07-04'`) ao lado do código
plano legado (`'41'`). Os dois consumidores que interpretam o código são indexados por
**grupo** — `_classify_investimento` ramifica em `'03'/'04'/'06'/'07'/'99'` e o catálogo
`e15_secoes_rfb_*.yaml` tem chaves de 2 dígitos — e nenhum dos dois parseava o composto.

Medido no corpus (836 artefatos `E1.5a`, 7.213 itens) em 2026-09-01: 131 itens em `GG-CC`,
**todos ano-base 2025** (4,3% dos itens de 2025; zero em 2023–2024). Destes, 102 caem em
`categoria_hint='investimento'` e os 102 saíam no balde genérico `'investimento'` — 96
deles são `07-*` (Grupo 07 = Fundos) e deveriam ser `fundo_investimento`.

Por que ler o GRUPO e não o subcódigo: nos 131 compostos, 107 (81,7%) resolvem para
subtipos DIFERENTES conforme se leia `GG` ou `CC`, e a leitura por `CC` é demonstravelmente
errada — `'07-01'` (fundo) daria `imovel` e `'04-02'` (ouro) daria `veiculo`. Pinar a forma
plana de 2 dígitos emitiria o subcódigo (25 de 26 pares divergentes medidos assim), então
ela não é "a mesma informação mais curta": ela troca o grupo pelo subcódigo em silêncio.
"""

from __future__ import annotations

import pytest

from pipeline.domain.services.baseline_item_classifier import BaselineCatalog, grupo_rfb


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("07-04", "07"),
        ("01-11", "01"),
        ("99-06", "99"),
        ("41", "41"),
        ("07", "07"),
        ("G01", "01"),
        ("1", "01"),
        ("", "00"),
    ],
)
def test_grupo_rfb_extrai_o_grupo_das_duas_formas(codigo: str, esperado: str) -> None:
    assert grupo_rfb(codigo) == esperado


def test_grupo_rfb_preserva_o_contrato_legado_de_normalize_grupo() -> None:
    """`normalize_grupo` aceitava `Any` e zero-padava — a forma plana não pode mudar."""
    from scripts.consolidate_baseline import normalize_grupo

    assert normalize_grupo(1) == "01"
    assert normalize_grupo("G1") == "01"
    assert normalize_grupo("41") == "41"
    # A regressão: o composto virava chave inexistente em vez do grupo.
    assert normalize_grupo("07-04") == "07"


class TestClassifyInvestimentoLeOComposto:
    """Ponta viva: `_classify_investimento` decide `tipo`, que ENTRA no `_identity_key`."""

    @pytest.mark.parametrize(
        ("codigo", "descricao", "esperado"),
        [
            ("07-04", "fundo de investimento", "fundo_investimento"),
            ("07-01", "fundo", "fundo_investimento"),
            ("04-02", "ouro ativo financeiro", "renda_fixa"),
            ("06-01", "conta corrente", "conta_bancaria"),
            ("03-01", "acoes", "acao"),
        ],
    )
    def test_composto_classifica_pelo_grupo(
        self, codigo: str, descricao: str, esperado: str
    ) -> None:
        from scripts.consolidate_baseline import _classify_investimento, normalize_grupo

        assert _classify_investimento(normalize_grupo(codigo), descricao) == esperado

    @pytest.mark.parametrize(
        ("codigo", "descricao", "esperado"),
        [
            ("04", "cdb", "renda_fixa"),
            ("07", "fundo", "fundo_investimento"),
            ("06", "dolar", "moeda_estrangeira"),
            ("99", "qualquer", "outros"),
        ],
    )
    def test_forma_plana_legada_nao_se_move(
        self, codigo: str, descricao: str, esperado: str
    ) -> None:
        """98,18% do corpus é plano — o fix não pode movê-lo."""
        from scripts.consolidate_baseline import _classify_investimento, normalize_grupo

        assert _classify_investimento(normalize_grupo(codigo), descricao) == esperado


class TestCatalogoCaiParaOGrupo:
    """O catálogo YAML só tem chaves de 2 dígitos: composto dava miss silencioso."""

    _CAT = BaselineCatalog(
        ano_base=2024,
        subtipo_por_secao_codigo={
            ("bens_direitos", "07"): "fundo",
            ("bens_direitos", "07-04"): "fundo_exato",
            ("bens_direitos", "41"): "poupanca",
        },
    )

    def test_composto_sem_chave_exata_cai_para_o_grupo(self) -> None:
        assert self._CAT.subtipo("bens_direitos", "07-99") == "fundo"

    def test_chave_exata_vence_o_grupo(self) -> None:
        """Fallback é ADITIVO: lookup que já acertava não pode mudar de resposta."""
        assert self._CAT.subtipo("bens_direitos", "07-04") == "fundo_exato"

    def test_plano_legado_inalterado(self) -> None:
        assert self._CAT.subtipo("bens_direitos", "41") == "poupanca"

    def test_grupo_ausente_do_catalogo_continua_none(self) -> None:
        """Grupo 06 não está no YAML — o fallback não pode inventar resposta."""
        assert self._CAT.subtipo("bens_direitos", "06-01") is None

    def test_sem_secao_nada_e_consultado(self) -> None:
        assert self._CAT.subtipo(None, "07-04") is None
