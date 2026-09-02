"""Dois valores para a mesma grandeza na mesma seção reprovam o item (A40.l120)."""

from __future__ import annotations

import pytest

from backend.app.services.parecer_prose_coerencia import (
    TERMOS_POR_METRICA,
    _meio_passo,
    _normaliza,
    divergencias_de_item,
)


class _Metrica:
    def __init__(self, key: str, section_id: str, valor_atual: str):
        self.metrica_key = key
        self.section_id = section_id
        self.valor_atual = valor_atual


_ALVOS = {
    "alocacao_renda_fixa": {
        "unidade": "pct",
        "rotulo": "Alocação em renda fixa, previdência inclusa (% da carteira líquida)",
    },
    "if_prazo_ano": {
        "unidade": "ano",
        "rotulo": "Ano projetado da independência (cenário central)",
    },
    "protecao_custo_premio": {
        "unidade": "ratio_0_1",
        "rotulo": "Custo dos seguros sobre a renda anual",
    },
    "reserva_cobertura_meses": {"unidade": "meses", "rotulo": "Cobertura da reserva de emergência"},
}


def _roda(texto: str, *, key="alocacao_renda_fixa", carimbo="94,4%", secao="S1"):
    return divergencias_de_item(
        campos={"descricao": texto},
        section_id=secao,
        metricas=[_Metrica(key, secao, carimbo)],
        kpi_targets=_ALVOS,
    )


class TestToleranciaDerivadaDaPrecisao:
    """A tolerância é meio passo da última casa ESCRITA — nunca uma banda escolhida."""

    def test_meio_passo_por_grafia(self):
        passos = [float(_meio_passo(g)) for g in ("94", "94,4", "90,25")]
        assert passos == [0.5, 0.05, 0.005]

    def test_arredondamento_declarado_passa(self):
        """ "94%" declara meio ponto de folga e o carimbo é 94,4 — dentro."""
        assert _roda("a renda fixa é 94% da carteira") == []

    def test_numero_contraditorio_reprova_com_a_grandeza_na_mensagem(self):
        achados = _roda("a renda fixa é 90,25% da carteira")
        assert len(achados) == 1
        assert achados[0].metrica_key == "alocacao_renda_fixa"
        assert achados[0].section_id == "S1"
        assert achados[0].valor_prosa == "90,25"

    def test_aproximacao_grosseira_reprova(self):
        """ "cerca de 90%" declara meio ponto e erra 4,4 — reprova, e deve."""
        assert len(_roda("a renda fixa é cerca de 90% da carteira")) == 1


class TestNaoDisparoPorUnidade:
    """Meio-passo de ponto percentual contra ano/meses/razão fabrica falso positivo."""

    @pytest.mark.parametrize(
        "key,texto",
        [
            ("if_prazo_ano", "a independência financeira chega em 2041, e não 2035%"),
            ("protecao_custo_premio", "o custo dos seguros sobre a renda anual é 2,6%"),
            ("reserva_cobertura_meses", "a cobertura da reserva de emergência é 18%"),
        ],
    )
    def test_unidade_fora_de_ponto_percentual_nao_dispara(self, key, texto):
        assert _roda(texto, key=key, carimbo="18%") == []


class TestAtribuicaoConservadora:
    def test_secao_diferente_nao_confronta(self):
        assert _roda("a renda fixa é 90,25% da carteira", secao="S1") != []
        achados = divergencias_de_item(
            campos={"descricao": "a renda fixa é 90,25% da carteira"},
            section_id="S3",
            metricas=[_Metrica("alocacao_renda_fixa", "S1", "94,4%")],
            kpi_targets=_ALVOS,
        )
        assert achados == []

    def test_sem_o_termo_canonico_nao_dispara(self):
        assert _roda("o indicador ficou em 90,25% no período") == []

    def test_percentual_de_outra_clausula_nao_e_atribuido(self):
        """As demais linhas da tabela de classes moram no mesmo campo e não são a grandeza."""
        texto = "renda fixa 94%. previdência 4,14%. outros 5,61%"
        assert _roda(texto) == []

    def test_limiar_de_meta_distante_nao_vira_afirmacao(self):
        texto = "a renda fixa é 94% da carteira e o plano prevê reduzir a exposição para 50%"
        assert _roda(texto) == []


def test_todo_termo_e_substring_do_rotulo_do_catalogo():
    """O termo não é vocabulário livre: renomear a grandeza no catálogo quebra AQUI."""
    for key, termos in TERMOS_POR_METRICA.items():
        rotulo = _ALVOS.get(key, {}).get("rotulo")
        if rotulo is None:
            continue
        for termo in termos:
            assert _normaliza(termo) in _normaliza(rotulo), (key, termo)
