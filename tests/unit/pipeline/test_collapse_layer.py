"""Ratchets da camada E3 do colapso ([[A40.l2]] PR1b · [[ADR-354]] §Emenda).

O instrumento existe porque o detector da [[A40.l1]] varre **E4** e o colapsador opera
em **E3**: medido em 2026-08-05, 70 de 331 chaves colapsáveis ficam fora do campo de
visão do detector, com 58% dos cents. Sem contar a camada E3, "o numerador caiu a 0" é
prova vácua.

Cada teste aqui existe para **morder** — a suíte foi validada por mutação (remover o
mecanismo que o teste nomeia derruba o teste).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dev.ledger_collapse_layer import (  # noqa: E402
    collapse_layer_summary,
    detector_digests,
    fmt_collapse_layer,
)


class _Cand:
    """Duck-type de ``CollapseCandidate`` — só os campos que a camada lê."""

    def __init__(
        self,
        digest: str,
        *,
        blocked: str | None = None,
        rows: int = 1,
        cents: int = 10000,
        card: int = 1,
        no_bucket: int | None = None,
    ) -> None:
        self.key_digest = digest
        self.blocked_reason = blocked
        self.removable_rows = 0 if blocked else rows
        self.valor_cents = cents
        self.survivor_cardinality = card
        # `no_bucket > removable_rows` ⇒ alvo pede remoção PARCIAL de bucket.
        self.rows_alcancadas_por_hash = 0 if blocked else (no_bucket or rows)

    @property
    def collapsible(self) -> bool:
        return self.blocked_reason is None and self.removable_rows > 0

    @property
    def alvo_ambiguo(self) -> bool:
        return self.rows_alcancadas_por_hash != self.removable_rows


class _Collision:
    def __init__(self, digest: str) -> None:
        self.key_digest = digest


def _cg(*digests: str):
    return type("CG", (), {"numerador": [_Collision(d) for d in digests]})()


# ── as 3 identidades ──


def test_particao_fecha_e_pega_filtro_silencioso() -> None:
    cands = [_Cand("aaaaaaaaaa"), _Cand("bbbbbbbbbb", blocked="descricao_vazia")]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa")))

    assert (s.candidatos, s.colapsaveis, s.bloqueados) == (2, 1, 1)
    assert s.particao_fecha
    assert s.layer_ok


def test_paridade_fecha_em_ambos_mais_so_no_colapsador() -> None:
    cands = [_Cand("aaaaaaaaaa"), _Cand("cccccccccc")]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa")))

    assert (s.em_ambos, s.so_no_detector, s.so_no_colapsador) == (1, 0, 1)
    assert s.paridade_fecha


def test_cardinalidade_fecha_contra_colapsaveis() -> None:
    cands = [_Cand("aaaaaaaaaa", card=1), _Cand("bbbbbbbbbb", card=2, rows=2)]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa", "bbbbbbbb")))

    assert s.cardinalidade == {1: 1, 2: 1}
    assert s.cardinalidade_fecha
    assert s.rows_removiveis == 3


# ── ponto cego: o único eixo que autoriza usar o detector como oráculo ──


def test_digest_do_detector_ausente_no_colapsador_acende_ponto_cego() -> None:
    """Detector ⊄ colapsador ⇒ o gate mede algo que o fix não cobre. Tem de aparecer."""
    s = collapse_layer_summary([_Cand("aaaaaaaaaa")], detector_digests(_cg("aaaaaaaa", "zzzzzzzz")))

    assert s.so_no_detector == 1
    assert not s.sem_ponto_cego
    assert "PONTO CEGO" in "\n".join(fmt_collapse_layer(s))


def test_chave_bloqueada_nao_conta_como_ponto_cego() -> None:
    """O colapsador VIU a chave e decidiu não colapsar — é predicado, não cobertura."""
    cands = [_Cand("aaaaaaaaaa", blocked="tipo_conta_fora_da_allow_list")]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa")))

    assert s.so_no_detector == 0
    assert s.sem_ponto_cego
    assert s.em_ambos == 0  # bloqueada não entra na interseção de colapsáveis


# ── o truncamento é DERIVADO, não literal ──


@pytest.mark.parametrize("n", [8, 10, 12, 16])
def test_paridade_sobrevive_a_qualquer_comprimento_de_digest_do_detector(n) -> None:
    """Se alguém trocar o `[:8]` do detector, a paridade não pode passar a mentir."""
    digest = "0123456789abcdef0123"

    s = collapse_layer_summary([_Cand(digest)], detector_digests(_cg(digest[:n])))

    assert s.digest_len == n
    assert (s.em_ambos, s.so_no_detector, s.so_no_colapsador) == (1, 0, 0)


def test_digest_heterogeneo_do_detector_e_erro_nao_warning() -> None:
    with pytest.raises(ValueError, match="comprimentos distintos"):
        collapse_layer_summary([_Cand("aaaaaaaaaa")], detector_digests(_cg("aaaaaaaa", "bbbb")))


def test_detector_vazio_nao_finge_paridade() -> None:
    """Sem numerador não há contra o que casar — `em_ambos` não pode sair inflado."""
    s = collapse_layer_summary([_Cand("aaaaaaaaaa"), _Cand("bbbbbbbbbb")], frozenset())

    assert (s.em_ambos, s.so_no_detector, s.so_no_colapsador) == (0, 0, 2)
    assert s.orfas_rows == 2  # nenhuma é observada pelo detector


# ── sem cap silencioso, e o número IMPRESSO é pinado ──


def test_colapsaveis_nao_tem_cap_constante() -> None:
    """Corpus denso fecha qualquer `[:100]` plausível de uma vez (lição da [[A40.l1]])."""
    # Prefixo de 8 DISTINTO por candidato — senão o truncamento colide e o teste
    # mediria colisão de digest em vez de cap (ver o teste seguinte).
    cands = [_Cand(f"{i:08d}ff") for i in range(150)]

    s = collapse_layer_summary(cands, detector_digests(_cg(*(f"{i:08d}" for i in range(150)))))

    assert s.candidatos == 150
    assert s.colapsaveis == 150
    assert s.em_ambos == 150
    assert s.rows_removiveis == 150
    assert s.layer_ok


def test_colisao_de_prefixo_de_digest_derruba_a_identidade_de_paridade() -> None:
    """Truncar o digest do colapsador ao comprimento do detector pode colidir. Se
    colidir, `so_no_colapsador` SUBCONTA — e a identidade tem de reprovar em vez de
    imprimir um número menor com cara de correto."""
    # 3 candidatos distintos que truncam para o MESMO prefixo de 8.
    cands = [_Cand("00000000aa"), _Cand("00000000bb"), _Cand("00000000cc")]

    s = collapse_layer_summary(cands, frozenset({"11111111"}))

    assert s.colapsaveis == 3
    assert s.so_no_colapsador == 1  # os 3 colapsaram num único prefixo
    assert not s.paridade_fecha
    assert not s.layer_ok
    assert "layer_ok=false" in "\n".join(fmt_collapse_layer(s))


def test_render_pina_os_numeros_impressos() -> None:
    """O que alimenta o baseline off-git é a STRING; sem asserção sobre ela, um
    `sum(...)` trocado por `len(...)` passa a suíte verde."""
    cands = [
        _Cand("aaaaaaaaaa", cents=10000, rows=1, card=1),
        _Cand("bbbbbbbbbb", cents=20000, rows=2, card=2),
        _Cand("cccccccccc", blocked="par_nao_e_nativo_mais_llm"),
    ]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa")))
    texto = "\n".join(fmt_collapse_layer(s))

    assert "candidatos cross-proveniência: **3**" in texto
    assert "colapsáveis **2**" in texto
    assert "bloqueados 1" in texto
    assert "rows removíveis: **3**" in texto
    assert "cents removíveis: **50000**" in texto  # 10000*1 + 20000*2
    assert "bloqueio `par_nao_e_nativo_mais_llm`: 1" in texto
    assert "só no colapsador **1**" in texto
    assert "layer_ok=true" in texto


def _corpus_misto(n: int = 150) -> list:
    """1 em 5 bloqueado, `rows` e `card` variando — nenhum eixo constante."""
    return [
        _Cand(
            f"{i:08d}ff",
            blocked="descricao_vazia" if i % 5 == 0 else None,
            rows=1 + i % 3,
            card=1 + i % 4,
        )
        for i in range(n)
    ]


def test_summary_nao_capa_nem_filtra_a_entrada() -> None:
    """As identidades 1 e 3 são **auto-consistentes**: cap sobre a lista de entrada
    reduz os dois lados e elas seguem fechando. O que dá dente é ancorar cada
    contagem em valor computado FORA do sumário."""
    cands = _corpus_misto()
    esperado_col = sum(1 for c in cands if c.collapsible)
    esperado_rows = sum(c.removable_rows for c in cands if c.collapsible)
    esperado_cents = sum(c.valor_cents * c.removable_rows for c in cands if c.collapsible)

    s = collapse_layer_summary(cands, frozenset({"99999999"}))

    assert s.candidatos == 150  # pega cap aplicado a `todos`
    assert s.colapsaveis == esperado_col
    assert s.bloqueados == 150 - esperado_col
    assert s.rows_removiveis == esperado_rows
    assert s.cents_removiveis == esperado_cents
    assert sum(s.cardinalidade.values()) == esperado_col  # pega cap no histograma
    assert s.so_no_colapsador == len({c.key_digest[:8] for c in cands if c.collapsible})


def test_filtro_assimetrico_dentro_do_sumario_derruba_a_particao() -> None:
    """O que a identidade 1 realmente pega: contagem de um lado sem o outro."""
    from dev.ledger_collapse_layer import CollapseLayerSummary

    s = CollapseLayerSummary(candidatos=10, colapsaveis=4, bloqueados_por_motivo={"x": 3})

    assert not s.particao_fecha
    assert not s.layer_ok


def test_histograma_de_cardinalidade_incompleto_derruba_a_identidade_3() -> None:
    """Isolada: só a identidade 3 falha, então `layer_ok` não pode ser carregado pelas
    outras duas. Sem este teste, `cardinalidade_fecha → True` sobrevive à mutação."""
    from dev.ledger_collapse_layer import CollapseLayerSummary

    s = CollapseLayerSummary(candidatos=5, colapsaveis=5, cardinalidade={1: 3}, so_no_colapsador=5)

    assert s.particao_fecha and s.paridade_fecha  # isolamento: só a 3 falha
    assert not s.cardinalidade_fecha
    assert not s.layer_ok
    assert "cardinalidade False" in "\n".join(fmt_collapse_layer(s))


def test_alvo_nao_enderecavel_e_REPORTADO_mas_nao_gateia() -> None:
    """T4 da desfusão: o número continua impresso e visível, sem prender `layer_ok`."""
    # `alvo_enderecavel` mede dano contrafactual de um consumidor que apaga por CONJUNTO
    # de hash — consumidor que `collapse()` garante não existir (remove por `id()` na
    # mesma lista). Prender a LEGIBILIDADE do instrumento a isso era ADR-342 invertida.
    cands = [_Cand("aaaaaaaaaa", rows=1, no_bucket=2)]

    s = collapse_layer_summary(cands, frozenset({"aaaaaaaa"}))

    assert (s.rows_removiveis, s.rows_alcancadas) == (1, 2)
    assert s.candidatos_com_alvo_ambiguo == 1
    assert not s.alvo_enderecavel  # o fato segue medido
    assert s.layer_ok  # ...e as 3 identidades de legibilidade fecham
    texto = "\n".join(fmt_collapse_layer(s))
    assert "ALVO NÃO ENDEREÇÁVEL" in texto  # ratchet T4: o número NÃO some do render
    assert "removeria 1 rows a mais" in texto
    assert "é REPORTADO, não gateia" in texto


def test_render_declara_clausulas_inexercitadas_quando_nada_bloqueia() -> None:
    """0 bloqueados não pode ler como "predicado validado" — é o falso-verde da tese."""
    texto = "\n".join(
        fmt_collapse_layer(
            collapse_layer_summary([_Cand("aaaaaaaaaa")], detector_digests(_cg("aaaaaaaa")))
        )
    )

    assert "não foram exercitadas por este corpus" in texto


def test_orfas_contam_rows_e_cents_so_do_que_o_detector_nao_ve() -> None:
    cands = [
        _Cand("aaaaaaaaaa", cents=10000, rows=1),
        _Cand("dddddddddd", cents=30000, rows=2),
    ]

    s = collapse_layer_summary(cands, detector_digests(_cg("aaaaaaaa")))

    assert s.orfas_rows == 2
    assert s.orfas_cents == 60000
    assert s.cents_removiveis == 70000


def test_formula_de_cents_e_rows_nao_proveniencias() -> None:
    """A fórmula declarada é cents × rows. O detector soma (n_prov−1) × cents; confundir
    as duas foi o erro que a §Medição do PR1 registra."""
    s = collapse_layer_summary([_Cand("aaaaaaaaaa", cents=10000, rows=3, card=3)], frozenset())

    assert s.cents_removiveis == 30000


_SENTINELA = {
    "candidatos": 111,
    "colapsaveis": 222,
    "rows_removiveis": 333,
    "cents_removiveis": 444,
    "alvo_ambiguo": 555,
}


def test_instrumento_delega_ao_shadow_counts_do_dominio(monkeypatch) -> None:
    """Prova a DELEGAÇÃO, não os valores — recomputar local dá o mesmo número hoje."""
    # Teste de valores passa com ou sem delegação, e o instrumento volta a ter cópia
    # própria da fórmula: o bug do `keep_split`, onde as duas derivações concordavam na
    # fixture e divergiam no corpus.
    import dev.ledger_collapse_layer as mod

    monkeypatch.setattr(mod, "shadow_counts", lambda _c: _SENTINELA)

    s = collapse_layer_summary([_Cand("aaaaaaaaaa", cents=10000, rows=3, card=3)], frozenset())

    assert (s.candidatos, s.colapsaveis) == (111, 222)
    assert (s.rows_removiveis, s.cents_removiveis) == (333, 444)
    assert s.candidatos_com_alvo_ambiguo == 555
