"""Tests — árbitro de precedência temporal entre pools (ADR-383 · A40.l41)."""

from __future__ import annotations

from pipeline.domain.services.fonte_precedencia_arbiter import (
    FontePatrimonial,
    arbitrar_frescor,
    fontes_de_irpf,
    fontes_de_posicoes_atuais,
)

_HOJE = "2026-08-12"


def _fonte(pool: str, data: str | None, inst: str = "c6bank", membro: str = "david"):
    return FontePatrimonial(
        pool=pool,
        instituicao=inst,
        membro=membro,
        data_referencia=data,
        data_precisao="dia" if data else "desconhecida",
    )


# O caso medido no dogfood: posição E4 de 2025-03-31 (R$ 206k) contra IRPF
# 31/12/2025 (R$ 2,4k) — a mais fresca vence, e a contradição é emitida.
def test_irpf_mais_fresco_vence_posicao_stale_e_emite_contradicao():
    fontes = [_fonte("posicoes_atuais", "2025-03-31"), _fonte("irpf", "2025-12-31")]
    veredito = arbitrar_frescor(
        fontes, data_alvo=_HOJE, pool_atual_por_celula={("c6bank", "david"): "posicoes_atuais"}
    )
    assert veredito.vencedores[("c6bank", "david")].pool == "irpf"
    (contradicao,) = veredito.contradicoes
    assert (contradicao.pool_atual, contradicao.pool_mais_fresco) == ("posicoes_atuais", "irpf")
    assert "2025-12-31" in contradicao.format()


def test_posicao_mais_fresca_que_irpf_vence_sem_contradicao():
    """Polaridade inversa: qualidade NÃO inverte a ordem quando a data manda."""
    fontes = [_fonte("posicoes_atuais", "2026-07-31"), _fonte("irpf", "2025-12-31")]
    veredito = arbitrar_frescor(
        fontes, data_alvo=_HOJE, pool_atual_por_celula={("c6bank", "david"): "posicoes_atuais"}
    )
    assert veredito.vencedores[("c6bank", "david")].pool == "posicoes_atuais"
    assert veredito.contradicoes == ()


def test_sem_look_ahead_fonte_futura_e_inelegivel():
    fontes = [_fonte("posicoes_atuais", "2025-06-30"), _fonte("irpf", "2026-12-31")]
    veredito = arbitrar_frescor(fontes, data_alvo=_HOJE)
    assert veredito.vencedores[("c6bank", "david")].data_referencia == "2025-06-30"


def test_empate_de_data_desempata_por_qualidade():
    fontes = [_fonte("posicoes_atuais", "2025-12-31"), _fonte("irpf", "2025-12-31")]
    veredito = arbitrar_frescor(fontes, data_alvo=_HOJE)
    assert veredito.vencedores[("c6bank", "david")].pool == "irpf"


def test_desconhecida_nunca_vence_datada():
    fontes = [_fonte("irpf", None), _fonte("posicoes_atuais", "2024-12-31")]
    veredito = arbitrar_frescor(fontes, data_alvo=_HOJE)
    assert veredito.vencedores[("c6bank", "david")].pool == "posicoes_atuais"


def test_desconhecida_entra_quando_e_a_unica_fonte():
    veredito = arbitrar_frescor([_fonte("posicoes_atuais", None)], data_alvo=_HOJE)
    assert veredito.vencedores[("c6bank", "david")].pool == "posicoes_atuais"


def test_celulas_independentes_nao_se_contaminam():
    """Instituições distintas do mesmo membro arbitram em separado (ADR-383 §3)."""
    fontes = [
        _fonte("posicoes_atuais", "2025-03-31", inst="c6bank"),
        _fonte("irpf", "2025-12-31", inst="c6bank"),
        _fonte("posicoes_atuais", "2026-07-31", inst="rico"),
        _fonte("irpf", "2025-12-31", inst="rico"),
    ]
    veredito = arbitrar_frescor(fontes, data_alvo=_HOJE)
    assert veredito.vencedores[("c6bank", "david")].pool == "irpf"
    assert veredito.vencedores[("rico", "david")].pool == "posicoes_atuais"


def test_fonte_e4_usa_a_data_mais_velha_do_grupo():
    """A fonte é tão fresca quanto a posição mais velha que ela contém."""
    raw = {
        "dados": [
            {"instituicao": "Santander", "membro": "david", "data_referencia": "2026-04-08"},
            {"instituicao": "Santander", "membro": "david", "data_referencia": "2026-01-31"},
        ]
    }
    (fonte,) = fontes_de_posicoes_atuais(raw, membro_default="david")
    assert (fonte.instituicao, fonte.data_referencia) == ("santander", "2026-01-31")


def test_fonte_e4_sem_data_em_alguma_posicao_fica_desconhecida():
    raw = {
        "dados": [
            {"instituicao": "Itau", "membro": "david", "data_referencia": "2026-04-08"},
            {"instituicao": "Itau", "membro": "david", "data_referencia": ""},
        ]
    }
    (fonte,) = fontes_de_posicoes_atuais(raw, membro_default="david")
    assert fonte.data_referencia is None
    assert fonte.data_precisao == "desconhecida"


def test_fonte_e4_aceita_periodo_dict_do_produtor():
    raw = {
        "dados": [
            {
                "instituicao": "c6bank",
                "membro": "david",
                "data_referencia": {"inicio": "2025-03-01", "fim": "2025-03-31"},
            }
        ]
    }
    (fonte,) = fontes_de_posicoes_atuais(raw, membro_default="david")
    assert fonte.data_referencia == "2025-03-31"


def test_fontes_de_irpf_emitem_uma_fonte_por_ano_com_chave_legada():
    consolidados = [
        {
            "instituicao": "Banco C6 S.A.",
            "proprietario": "david",
            "valores_31_12": {"31_12_2024": 23439.0, "2025": 2404.0},
        }
    ]
    fontes = sorted(fontes_de_irpf(consolidados), key=lambda f: f.data_referencia or "")
    assert [f.data_referencia for f in fontes] == ["2024-12-31", "2025-12-31"]
    assert {f.instituicao for f in fontes} == {"bancoc6sa"}


def test_payload_observacional_nao_carrega_valor_monetario():
    """LGPD + fase observacional: o bloco declara pool e data, nunca valor."""
    veredito = arbitrar_frescor(
        [_fonte("posicoes_atuais", "2025-03-31"), _fonte("irpf", "2025-12-31")],
        data_alvo=_HOJE,
        pool_atual_por_celula={("c6bank", "david"): "posicoes_atuais"},
    )
    payload = veredito.to_payload()
    serializado = str(payload)
    assert "valor" not in serializado and "brl" not in serializado.lower()
    assert payload["celulas"][0]["pool_vencedor"] == "irpf"
    assert payload["contradicoes"][0]["data_mais_fresca"] == "2025-12-31"


# Contrato da FASE OBSERVACIONAL (ADR-383 §5): o árbitro roda e publica o
# veredito, mas nenhum número consumido pelo PL muda. Se este teste quebrar,
# o flip vazou para o PR errado.
def test_fase_observacional_nao_altera_nenhum_valor_do_patrimonio():
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.domain.services.e5_analyzer_adapter import E5AnalyzerAdapter

    store = InMemoryArtifactStore()
    store.seed(
        "E4",
        "investimentos",
        {
            "total_geral": 206_491.70,
            "n_posicoes": 1,
            "total_por_membro": {"david": 206_491.70},
            "dados": [
                {
                    "nome": "CDB C6 Bank",
                    "instituicao": "c6bank",
                    "membro": "david",
                    "valor_atual": 206_491.70,
                    "data_referencia": {"inicio": "2025-03-01", "fim": "2025-03-31"},
                }
            ],
        },
    )
    store.seed(
        "E4",
        "patrimonio",
        {
            "patrimonio_por_ano": {"2025": {"total_bens": 300_000.0, "total_dividas": 0.0}},
            "investimentos_consolidados": [
                {
                    "descricao": "BANCO C6 - APLICACAO EM RENDA FIXA",
                    "instituicao": "c6bank",
                    "proprietario": "david",
                    "tipo": "investimento",
                    "valores_31_12": {"2025": 2404.0},
                }
            ],
        },
    )
    patrimonio = E5AnalyzerAdapter().analyze_via_store(store).patrimonio_full

    # O veredito EXISTE e aponta a contradição real do dogfood...
    frescor = patrimonio["frescor_fontes"]
    assert frescor["contradicoes"], "árbitro deveria acusar a posição stale de 2025-03"
    assert frescor["contradicoes"][0]["pool_mais_fresco"] == "irpf"
    # ...mas o PL continua vindo do caminho atual (posições atuais), intocado.
    assert patrimonio["investimentos_titular"] == 206_491.70
