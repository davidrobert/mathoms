"""Ratchets do KR-B cross-grupo ([[A40.l1]]): whitelist, cobertura e tokens de render."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.ledger_cross_group import (  # noqa: E402
    EXPLAINED_DIVERGENCE,
    CrossGroupSummary,
    cross_group_coverage,
    cross_group_double_count,
    cross_group_explained,
    cross_group_numerator,
    cross_group_summary,
    fmt_cross_group,
    validate_explained,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    buckets as _buckets,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    carrier_adr354 as _carrier_adr354,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    coincidencia_cross_conta as _coincidencia_cross_conta,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    duas_ocorrencias_uma_imaterial as _duas_ocorrencias_uma_imaterial,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    tx as _tx,
)

# ───────── anti-Goodhart: a whitelist não pode alcançar o sinal da lane ─────────


def test_whitelist_congelada_vazia() -> None:
    # Ratchet FRACO (grátis, satisfeito por diff de 2 linhas — por isso não é O
    # ratchet): crescer exige diff deste teste. Os de dente vêm a seguir.
    assert EXPLAINED_DIVERGENCE == frozenset(), (
        "whitelist cresceu: entrada nova exige (i) ADR ou decisão de lane citada, "
        "(ii) fixture que prove a classe legítima, (iii) o diff no PR — e passa por "
        "validate_explained, que rejeita assinatura de carrier da ADR-354."
    )


def test_whitelist_declarada_nao_silencia_o_carrier_adr354() -> None:
    # RATCHET com dente: roda a whitelist DECLARADA (não uma inventada pelo teste)
    # contra a fixture carrier FIXA. Falha no instante em que alguém whitelista a
    # classe da lane — sem corpus, sem DB, sem PII.
    hits = cross_group_double_count(_carrier_adr354(), explained=EXPLAINED_DIVERGENCE)
    assert cross_group_numerator(hits), "whitelist declarada silenciou o carrier ADR-354 (A40.l1)"


def test_eixo_de_whitelist_e_valor_nao_nome_de_campo() -> None:
    # r1 mediu que o eixo de NOME de campo tira o falso-positivo E o
    # verdadeiro-positivo juntos: 'tipo_conta' casa os dois. O eixo agora é o shape
    # com VALORES de vocabulário fechado + fill-state de titular — nome de campo cru
    # nem parseia.
    with pytest.raises(ValueError, match="malformado"):
        cross_group_double_count(_carrier_adr354(), explained=frozenset({"tipo_conta"}))


def test_whitelisted_nunca_entra_no_numerador() -> None:
    # A whitelist opera no shape de VALOR e a partição é total (nenhum hit se perde
    # nem duplica). A classe alcançável é a coincidência declarada — contas
    # genuinamente distintas com as duas pernas preenchidas.
    buckets = _coincidencia_cross_conta()
    shape = cross_group_double_count(buckets)[0].explained_shape
    assert shape == "banco=bancoa~bancob|tipo_conta=extratoconta|titular=preenchido"
    hits = cross_group_double_count(buckets, explained=frozenset({shape}))
    assert cross_group_numerator(hits) == []
    assert len(cross_group_explained(hits)) == 1
    assert hits[0].whitelisted is True
    assert len(cross_group_numerator(hits)) + len(cross_group_explained(hits)) == len(hits)


def test_shape_do_carrier_e_estruturalmente_inalcancavel_pela_whitelist() -> None:
    # O fecho de F2: o shape que o próprio carrier emite é REJEITADO pelo validador,
    # então não existe entrada de whitelist que silencie a classe da lane. Erro, não
    # warning — warning é ignorável num harness de dev.
    shape = cross_group_double_count(_carrier_adr354())[0].explained_shape
    assert shape == "banco=bancoexemplo|tipo_conta=extrato~extratoconta|titular=parcial"
    with pytest.raises(ValueError, match="carrier"):
        validate_explained(frozenset({shape}))


def test_validate_explained_rejeita_as_tres_assinaturas_de_carrier() -> None:
    casos = {
        "titular parcial (carrier 2)": "banco=itau|tipo_conta=extratoconta|titular=parcial",
        "sentinela de vazio": "banco=(vazio)~itau|tipo_conta=extratoconta|titular=preenchido",
        "tipo_conta divergente (carrier 1)": (
            "banco=itau|tipo_conta=extrato~extratoconta|titular=preenchido"
        ),
    }
    for rotulo, entry in casos.items():
        with pytest.raises(ValueError):
            validate_explained(frozenset({entry}))
        assert rotulo  # nomeia o caso na falha


def test_validate_explained_aceita_a_coincidencia_declarada() -> None:
    # O validador não pode rejeitar tudo: a única classe legítima conhecida (mesma
    # assinatura em instituições distintas, pernas simétricas) passa.
    legitima = "banco=bancoa~bancob|tipo_conta=extratoconta|titular=preenchido"
    validate_explained(frozenset({legitima}))


# ───────── cobertura: o denominador que torna o 0 falsificável ─────────


def test_cobertura_fecha_e_declara_ok() -> None:
    cov = cross_group_coverage(_carrier_adr354())
    assert cov["rows_scanned"] == 2 and cov["declared_tx"] == 2
    assert cov["rows_keyed"] == 2 and cov["keys_distinct"] == 1
    assert cov["keys_multirow"] == 1 and cov["keys_multiprov"] == 1
    assert cov["provenance_triples"] == 2
    assert cov["buckets_ilegiveis"] == ()
    assert cov["particao_fecha"] is True
    assert cov["coverage_ok"] is True


def test_terceira_identidade_pega_filtro_silencioso_no_numerador() -> None:
    # RATCHET: um filtro dentro de `cross_group_numerator` (piso de materialidade,
    # cap, dedupe de shape) derruba o numerador SEM tocar nenhuma das duas
    # identidades anteriores. A 3ª compara o que o detector achou (keys_multiprov)
    # com o que saiu particionado.
    cg = cross_group_summary(_duas_ocorrencias_uma_imaterial())
    assert cg.coverage["keys_multiprov"] == 2
    assert cg.coverage["keys_multiprov"] == len(cg.numerador) + len(cg.explicadas)
    assert cg.coverage["particao_fecha"] is True and cg.coverage["coverage_ok"] is True
    engolido = cross_group_coverage(_duas_ocorrencias_uma_imaterial(), particionadas=1)
    assert engolido["particao_fecha"] is False
    assert engolido["coverage_ok"] is False


def test_cobertura_cega_nomeia_o_balde_ilegivel() -> None:
    # O fail-safe de `_bucket_rows` devolve 0 rows quando `dados` é LISTA; sem o
    # veredito de cobertura isso produz texto idêntico a "0 colisões" (falso-verde
    # que a lane existe para fechar).
    cov = cross_group_coverage({"despesas": {"dados": []}, "receitas": {"dados": {}}})
    assert cov["rows_scanned"] == 0
    assert cov["buckets_ilegiveis"] == ("despesas",)
    assert cov["coverage_ok"] is False


def test_cobertura_cega_em_corpus_de_fonte_unica() -> None:
    # 1 tripla de proveniência ⇒ o critério "≥2 triplas" é vacuoso ⇒ o detector NÃO
    # PODE flagar: distingue "0 porque limpo" de "0 porque fonte única".
    cov = cross_group_coverage(_buckets(despesas=[_tx(valor=10.0), _tx(valor=20.0)]))
    assert cov["provenance_triples"] == 1
    assert cov["coverage_ok"] is False


def test_invariante_scanned_menos_keyed_igual_soma_das_exclusoes() -> None:
    # Torna o dict de exclusões falsificável de graça: as razões declaradas TÊM de
    # explicar toda row varrida e não chaveada, sem resíduo. É auto-consistente —
    # por isso o predicado tem teste próprio (test_qualquer_valor_nao_zero_...).
    buckets = _buckets(
        despesas=[_tx(tipo_conta="extrato"), _tx(tipo_conta="extratoconta", valor=0.0)],
        receitas=[_tx(data="", valor=50.0)],
    )
    cov = cross_group_coverage(buckets)
    assert cov["rows_scanned"] - cov["rows_keyed"] == sum(cov["unkeyable"].values())
    assert sum(cov["unkeyable"].values()) == 2


# ───────── render: os tokens negativos precisam existir de verdade ─────────


def test_render_declara_cobertura_cega_sem_payload() -> None:
    # RATCHET F4: sem este teste, trocar a string do ramo `else` de `_fmt_coverage`
    # por "cobertura=OK" mantém a suíte verde e devolve o relatório a ser
    # byte-idêntico entre corpus limpo e detector cego.
    linhas = fmt_cross_group(CrossGroupSummary())
    assert any("cobertura=CEGA" in linha for linha in linhas)
    assert any("sem payload E4" in linha for linha in linhas)


def test_render_declara_bloco_nao_verificavel_no_balde_ilegivel() -> None:
    cg = cross_group_summary({"despesas": {"dados": []}, "receitas": {"dados": {}}})
    linhas = fmt_cross_group(cg)
    assert any("NÃO-VERIFICÁVEL" in linha for linha in linhas)
    assert any("cobertura=CEGA" in linha for linha in linhas)


def test_render_declara_cobertura_ok_e_os_dois_histogramas() -> None:
    texto = "\n".join(fmt_cross_group(cross_group_summary(_carrier_adr354(), 7)))
    assert "cobertura=OK" in texto and "CEGA" not in texto
    assert "3ª identidade" in texto and "⇒ fecha" in texto
    assert "histograma diagnóstico" in texto and "histograma por shape de whitelist" in texto
    assert "transferencias=7" in texto
    assert "unidade: ocorrências" in texto and "unidade: rows" in texto
