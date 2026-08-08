"""Carrier do contador de colapso cross-documento E3→E4→E5 ([[A40.l2]] PR3c1).

O teste que carrega o PR é `test_soma_inclui_statement_zerado_pelo_colapso`: o E4 filtra
`p.get("transacoes")` antes de classificar, e o statement da perna LLM **zerado pelo colapso**
é justamente o de maior `count`. Somar sobre a lista filtrada subconta **exatamente onde o
colapso foi total — e fecha VERDE**, porque bate com o que o E4 enxerga. Achado do co-design
de 2026-08-08; sem este teste, a subcontagem seria indistinguível do número certo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.e3_load_report import (  # noqa: E402
    consolidacao_cross_documento,
)


def _e3(count: int, meses: list[tuple[str, int]], *, transacoes: int = 3) -> dict:
    """Payload E3 mínimo com o canal do colapso preenchido."""
    canal: dict = {"count": count, "valor_cents": -100 * count}
    if meses:
        canal["meses"] = [{"mes": m, "count": n} for m, n in meses]
    return {
        "transacoes": [{"id": i} for i in range(transacoes)],
        "remocoes": {"cross_document_collapse": canal},
    }


def test_soma_inclui_statement_zerado_pelo_colapso():
    """A perna LLM que o colapso ESVAZIA continua contando — é o de maior `count`."""
    # `transacoes=0` é a classe que a lane declara como esperada ("statement da perna LLM pode
    # ficar com 0 transações e ainda escrever artefato"). Somar sobre a lista já filtrada por
    # `p.get("transacoes")` perderia estas 9 e o número fecharia verde contra o E4.
    payloads = [_e3(2, [("2026-01", 2)]), _e3(9, [("2026-02", 9)], transacoes=0)]

    agregado = consolidacao_cross_documento(payloads)

    assert agregado is not None
    assert agregado["count"] == 11, "o statement zerado saiu da conta"
    assert {m["mes"] for m in agregado["meses"]} == {"2026-01", "2026-02"}


def test_meses_sao_mesclados_e_ordenados():
    """Determinismo: mesma entrada ⇒ mesmos bytes ⇒ mesma chave de cache do parecer."""
    payloads = [_e3(1, [("2026-03", 1)]), _e3(2, [("2026-01", 1), ("2026-03", 1)])]

    agregado = consolidacao_cross_documento(payloads)

    assert agregado["meses"] == [
        {"mes": "2026-01", "count": 1},
        {"mes": "2026-03", "count": 2},
    ]
    assert json.dumps(agregado, sort_keys=True) == json.dumps(
        consolidacao_cross_documento(list(reversed(payloads))), sort_keys=True
    )


def test_sem_colapso_devolve_none_para_o_campo_ser_omitido():
    """Ausência ≠ zero: campo presente mudaria o sha256 do E5 e regeraria o parecer da base."""
    assert consolidacao_cross_documento([_e3(0, [])]) is None
    assert consolidacao_cross_documento([]) is None
    assert consolidacao_cross_documento([{"transacoes": [{"id": 1}]}]) is None


def test_payload_sem_remocoes_nao_estoura():
    """Artefato E3 anterior ao canal (compat) — leitor tem de ser tolerante."""
    assert consolidacao_cross_documento([{"remocoes": {}}, {}]) is None


# `is_monetary` é monetário-por-DEFAULT: só `count` e leaves string sobrevivem. Este teste é o
# que impede alguém de "simplificar" `meses` para escalar ou mapa — as duas formas passariam
# no resto da suíte e sairiam 100× erradas no snapshot e no `delta_cents`.
@pytest.mark.parametrize(
    "campo,esperado",
    [("count", False), ("meses", True), ("mes", True)],
)
def test_armadilha_do_is_monetary_esta_documentada_pelo_teste(campo, esperado):
    """`meses` É monetário no `golden_diff` — por isso a forma é LISTA, com `mes` string."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "dev"))
    import golden_diff

    assert golden_diff.is_monetary(campo) is esperado


def test_forma_de_lista_neutraliza_a_armadilha():
    """O leaf que carrega o mês é STRING, e `to_cents` só se aplica a int/float."""
    agregado = consolidacao_cross_documento([_e3(1, [("2026-01", 1)])])

    (item,) = agregado["meses"]

    assert isinstance(item["mes"], str), "mês como número seria multiplicado por 100"
    assert isinstance(item["count"], int)


# Os testes acima provam a FUNÇÃO; este prova a ESCOLHA DA LISTA que o adapter faz — e só ele
# fica vermelho quando `categorize_via_store` volta a passar `accounts` (pós-filtro) no lugar
# de `readable`. Medido: sem este teste a mutação sobrevive à suíte inteira, que é exatamente
# "teste nomeia o mecanismo sem exercitá-lo".
def test_adapter_soma_sobre_readable_e_nao_sobre_a_lista_filtrada():
    """Ponta a ponta pelo store: o statement zerado pelo colapso entra no contador."""
    from pipeline.artifact_store import InMemoryArtifactStore
    from pipeline.domain.services.e4_categorizer_adapter import E4CategorizerAdapter

    store = InMemoryArtifactStore()
    store.write("reconcile_transactions", "com_tx", _e3(2, [("2026-01", 2)]))
    store.write("reconcile_transactions", "zerado", _e3(9, [("2026-02", 9)], transacoes=0))

    resultado = E4CategorizerAdapter.from_configs().categorize_via_store(store)

    assert resultado.consolidacao_cross_documento is not None
    assert resultado.consolidacao_cross_documento["count"] == 11, (
        "o adapter somou sobre a lista filtrada por `transacoes` — o statement que o "
        "colapso ZEROU é o de maior count e sumiu do contador"
    )
