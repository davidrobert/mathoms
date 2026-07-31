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
    _assert_explicadas_declaradas,
    _coverage_ok,
    cross_group_coverage,
    cross_group_double_count,
    cross_group_explained,
    cross_group_numerator,
    cross_group_summary,
    validate_explained,
)
from dev.ledger_cross_group_render import fmt_cross_group  # noqa: E402
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    buckets as _buckets,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    carrier_1_vocabulario as _carrier_1_vocabulario,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    carrier_adr354 as _carrier_adr354,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    carrier_e_coincidencia as _carrier_e_coincidencia,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    coincidencia_cross_conta as _coincidencia_cross_conta,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    corpus_denso as _corpus_denso,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    corpus_multi_eixo as _corpus_multi_eixo,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    duas_ocorrencias_uma_imaterial as _duas_ocorrencias_uma_imaterial,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    par_sem_descricao as _par_sem_descricao,
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


def test_validate_explained_rejeita_carrier_e_sentinela_de_vazio() -> None:
    casos = {
        "titular parcial (carrier 2)": "banco=itau|tipo_conta=extratoconta|titular=parcial",
        "sentinela ao lado de valor real = banco parcial (carrier 2)": (
            "banco=(vazio)~itau|tipo_conta=extratoconta|titular=preenchido"
        ),
        "tipo_conta divergente (carrier 1)": (
            "banco=itau|tipo_conta=extrato~extratoconta|titular=preenchido"
        ),
        "vazio em TODAS as pernas (eixo próprio: sentinela, não carrier)": (
            "banco=(vazio)|tipo_conta=extratoconta|titular=preenchido"
        ),
    }
    for rotulo, entry in casos.items():
        with pytest.raises(ValueError):
            validate_explained(frozenset({entry}))
        assert rotulo  # nomeia o caso na falha


def test_rota_alternativa_de_whitelist_nao_esvazia_o_numerador() -> None:
    # RATCHET: `whitelisted = shape in explained or not descricao` passava 76/76 e
    # esvaziava o numerador PARA DENTRO de `explicadas` sem tocar na whitelist (medido no
    # corpus: 261→200, explicadas 0→61, `particao_fecha=True`, `coverage_ok=True` — todo o
    # aparato anti-Goodhart contornado). Com a invariante, a rota é impossível: ocorrência
    # explicada com shape fora de `explained` é erro, não linha de relatório.
    cg = cross_group_summary(_par_sem_descricao())
    assert len(cg.numerador) == 1 and cg.numerador[0].descricao_vazia is True
    assert cg.explicadas == [] and cg.explained_shapes == ()


def test_explicada_fora_da_whitelist_declarada_e_erro() -> None:
    # O dente da invariante no grão da função: `explicadas` não-vazia com whitelist vazia
    # é impossível POR CONSTRUÇÃO, não por convenção do call-site.
    hit = cross_group_double_count(_carrier_adr354())[0]
    with pytest.raises(ValueError, match="FORA da whitelist"):
        _assert_explicadas_declaradas([hit], frozenset())
    _assert_explicadas_declaradas([hit], frozenset({hit.explained_shape}))


def test_validate_explained_aceita_a_coincidencia_declarada() -> None:
    # O validador não pode rejeitar tudo: a única classe legítima conhecida (mesma
    # assinatura em instituições distintas, pernas simétricas) passa.
    legitima = "banco=bancoa~bancob|tipo_conta=extratoconta|titular=preenchido"
    validate_explained(frozenset({legitima}))


# ───────── UMA definição de carrier: partição e validador não podem divergir ─────────


def _rejeita_como_carrier(shape: str) -> bool:
    """A whitelist rejeita este shape POR SER carrier (não por outro eixo)?"""
    try:
        validate_explained(frozenset({shape}))
    except ValueError as exc:
        return "carrier" in str(exc)
    return False


def test_carrier_1_sozinho_e_carrier_shaped() -> None:
    # RATCHET: `defect_shaped = bool(parciais)` captura só o carrier 2 (titular
    # assimétrico). O carrier 1 da ADR-354 — `tipo_conta` com vocabulário divergente —
    # NÃO produz campo parcial quando titular é simétrico, então saía
    # coincidence-shaped (não escala a P0) enquanto `_validate_entry` no MESMO módulo
    # se recusava a whitelistar o mesmo shape chamando-o de carrier 1.
    hit = cross_group_double_count(_carrier_1_vocabulario())[0]
    assert hit.parciais == ""
    assert hit.divergence == "tipo_conta"
    assert hit.carriers == ("tipo_conta:c1",)
    assert hit.defect_shaped is True


def test_token_de_carrier_nao_embute_separador_de_campo() -> None:
    # O valor de `carriers=` fica ao lado de campos `key=value` na linha de ocorrência; um
    # `=`, espaço ou `+` DENTRO do valor quebra qualquer parse do relatório off-git.
    hit = cross_group_double_count(_carrier_adr354())[0]
    assert hit.carriers == ("titular:c2", "tipo_conta:c1")
    for token in hit.carriers:
        assert not set(token) & set("= +"), token


def test_particao_e_validador_compartilham_a_definicao_de_carrier() -> None:
    # RATCHET com dente: o defeito era ter DUAS definições de carrier no mesmo módulo.
    # Para cada classe medida, "é carrier-shaped na partição" e "é rejeitado como
    # carrier pela whitelist" TÊM de concordar. Fora do escopo desta equivalência:
    # vazio em TODAS as pernas de campo de vocabulário, rejeitado por eixo próprio.
    casos = {
        "carrier 1+2 (titular parcial + tipo_conta variante)": _carrier_adr354(),
        "carrier 1 sozinho (titular simétrico)": _carrier_1_vocabulario(),
        "coincidência cross-conta (pernas simétricas)": _coincidencia_cross_conta(),
    }
    for rotulo, buckets in casos.items():
        hit = cross_group_double_count(buckets)[0]
        assert hit.defect_shaped is _rejeita_como_carrier(hit.explained_shape), rotulo


# ───────── cobertura: o denominador que torna o 0 falsificável ─────────


def test_particionadas_e_obrigatorio_para_afirmar_cobertura() -> None:
    # RATCHET: com o default (`particionadas=None` ⇒ keys_multiprov), a 3ª identidade
    # vira tautologia e um filtro dentro de `cross_group_numerator` fica invisível —
    # medido na r3 (`and c.direction == "debit"` passava com a suíte verde).
    with pytest.raises(TypeError):
        cross_group_coverage(_carrier_adr354())  # type: ignore[call-arg]


def test_cobertura_fecha_e_declara_ok() -> None:
    cov = cross_group_coverage(_carrier_adr354(), particionadas=1)
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
    cov = cross_group_coverage(
        {"despesas": {"dados": []}, "receitas": {"dados": {}}}, particionadas=0
    )
    assert cov["rows_scanned"] == 0
    assert cov["buckets_ilegiveis"] == ("despesas",)
    assert cov["coverage_ok"] is False


def test_cobertura_cega_em_corpus_de_fonte_unica() -> None:
    # 1 tripla de proveniência ⇒ o critério "≥2 triplas" é vacuoso ⇒ o detector NÃO
    # PODE flagar: distingue "0 porque limpo" de "0 porque fonte única".
    cov = cross_group_coverage(
        _buckets(despesas=[_tx(valor=10.0), _tx(valor=20.0)]), particionadas=0
    )
    assert cov["provenance_triples"] == 1
    assert cov["coverage_ok"] is False


def test_invariante_scanned_menos_keyed_igual_soma_das_exclusoes() -> None:
    # Torna o dict de exclusões falsificável de graça: as razões declaradas TÊM de
    # explicar toda row varrida e não chaveada, sem resíduo. É auto-consistente —
    # por isso o predicado tem teste próprio
    # (test_so_valor_exatamente_zero_e_excluido_por_valor, no arquivo irmão).
    buckets = _buckets(
        despesas=[_tx(tipo_conta="extrato"), _tx(tipo_conta="extratoconta", valor=0.0)],
        receitas=[_tx(data="", valor=50.0)],
    )
    cov = cross_group_coverage(buckets, particionadas=0)
    assert cov["rows_scanned"] - cov["rows_keyed"] == sum(cov["unkeyable"].values())
    assert sum(cov["unkeyable"].values()) == 2


def test_identidade_interna_quebra_com_residuo_nao_declarado() -> None:
    # TRIPWIRE: `interna = True` em `_coverage_ok` sobrevive a mutação hoje porque os dois
    # ramos compartilham `_unkeyable_reason` (é no-op enquanto não divergirem) — logo o
    # termo pode ser DELETADO sem sinal. Aqui o resíduo é artificial e bilateral: 2 rows
    # não chaveadas com 1 exclusão declarada reprova; com 2 declaradas, aprova.
    cov = {
        "rows_scanned": 10,
        "rows_keyed": 8,
        "unkeyable": {"valor_zero": 1},
        "declared_tx": 10,
        "particao_fecha": True,
        "buckets_ilegiveis": (),
        "provenance_triples": 2,
    }
    assert _coverage_ok(cov) is False
    cov["unkeyable"] = {"valor_zero": 2}
    assert _coverage_ok(cov) is True


def test_identidade_externa_quebra_quando_o_declarado_nao_bate() -> None:
    # RATCHET: `externa` (rows_scanned == Σ total_transacoes) é o ÚNICO termo de
    # `_coverage_ok` que NÃO é auto-consistente — o detector não lê `total_transacoes` —
    # e era o único sem teste: forçar `externa = True` mantinha a suíte verde, e um
    # balde que perde rows na leitura passava como cobertura OK.
    buckets = _carrier_adr354()
    buckets["despesas"]["total_transacoes"] = 3
    cov = cross_group_coverage(buckets, particionadas=1)
    assert cov["rows_scanned"] == 2 and cov["declared_tx"] == 3
    assert cov["coverage_ok"] is False


def test_numerador_atravessa_os_dois_baldes_cinco_categorias_e_duas_moedas() -> None:
    # RATCHET: as fixturas de 1 categoria / 1 balde / 1 moeda deixavam passar filtro em
    # QUALQUER desses eixos (medido na r3: varrer só a 1ª categoria de `dados`, ou
    # `and c.direction == "debit"` dentro do numerador, com a suíte verde).
    cg = cross_group_summary(_corpus_multi_eixo())
    assert len(cg.numerador) == 5
    assert {c.direction for c in cg.numerador} == {"debit", "credit"}
    assert {c.moeda for c in cg.numerador} == {"BRL", "USD"}
    assert cg.coverage["rows_scanned"] == 10 and cg.coverage["declared_tx"] == 10
    assert cg.coverage["particao_fecha"] is True
    assert cg.coverage["coverage_ok"] is True


_N_DENSO = 150


def test_numerador_nao_tem_cap_constante() -> None:
    # RATCHET: `[:100]` dentro de `cross_group_numerator` passava 76/76 — só `[:1]` era
    # pego, porque a fixture mais densa tinha 5 colisões. Em produção o cap PEGA e a 3ª
    # identidade reprova a cobertura, então o furo é no gate pré-merge, não no runtime.
    # 150 colisões (~300 rows sintéticas) fecham qualquer cap constante plausível.
    cg = cross_group_summary(_corpus_denso(_N_DENSO))
    assert len(cg.numerador) == _N_DENSO
    assert cg.coverage["keys_multiprov"] == _N_DENSO
    assert cg.coverage["rows_scanned"] == 2 * _N_DENSO
    assert cg.coverage["particao_fecha"] is True and cg.coverage["coverage_ok"] is True


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
    # O número IMPRESSO (o que a skill manda grepar) tem asserção própria: 1 ocorrência,
    # 2 proveniências, 100,00 ⇒ (P−1)·valor = 10000 cents.
    assert "não-explicada: 1 ocorrência(s)" in texto
    assert "Σ excesso 10000 cents" in texto
    # A partição imprime a definição de carrier que a whitelist USA — sem isso, o leitor
    # não tem como saber que "coincidence-shaped" não inclui carrier 1.
    assert "carrier-shaped=1" in texto and "coincidence-shaped=0" in texto
    assert "a MESMA definição que a whitelist rejeita" in texto
    assert "carriers=titular:c2+tipo_conta:c1" in texto


def test_render_pina_o_numero_impresso_em_corpus_misto() -> None:
    # RATCHET: o numerador estava pinado no grão de DADOS, mas o número IMPRESSO não —
    # `len(hits)` → `sum(1 for c in hits if c.defect_shaped)` e `_sum_excess → 0` passavam
    # 76/76. Corpus MISTO de propósito: com só carrier, filtrar por `defect_shaped` é
    # indistinguível de `len`. Σ = 10000 (carrier) + 20000 (coincidência).
    cg = cross_group_summary(_carrier_e_coincidencia())
    assert len(cg.numerador) == 2
    texto = "\n".join(fmt_cross_group(cg))
    assert "não-explicada: 2 ocorrência(s)" in texto
    assert "Σ excesso 30000 cents" in texto
    assert "carrier-shaped=1" in texto and "coincidence-shaped=1" in texto
