"""A40.l80 PR1 ([[ADR-412]]): contrato das bases canônicas e do `PapelMembro`.

PR de schema permissivo: nenhum produtor escreve os campos novos ainda. O que
estes testes fecham é a **classe** — schema e enum não podem divergir, e as
chaves novas têm de ser aceitas quando presentes e dispensáveis quando ausentes,
senão o PR2 (que liga o produtor) descobre o desalinhamento em produção.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pipeline.domain.services.bases_financeiras import (
    BaseFinanceira,
    PapelMembro,
    chave_de_componente,
    publicavel_sozinha,
    termos_da_base,
)
from scripts.pipeline_common import validate_dict
from tests.fixtures.e5_fluxo_minimo import FLUXO_CAIXA_MINIMO

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "schemas" / "e5_analysis.schema.json"
)


@pytest.fixture(autouse=True)
def _strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin de modo: sob `warn`, `validate_dict` devolve True incondicionalmente."""
    monkeypatch.setenv("MATHOMS_PIPELINE_SCHEMA_MODE", "strict")


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _payload(**patrimonio_extra) -> dict:
    return {
        "score": {"valor": 5.0, "classificacao": "Regular"},
        "fluxo_caixa": deepcopy(FLUXO_CAIXA_MINIMO),
        "patrimonio": {"bruto": 100.0, "liquido": 80.0, **patrimonio_extra},
    }


# -- schema <-> enum: a classe, não a instância -------------------------------


def test_chaves_de_bases_no_schema_sao_exatamente_o_enum(schema: dict):
    """Base nova exige tocar schema E enum juntos — divergir é o defeito."""
    no_schema = set(schema["properties"]["patrimonio"]["properties"]["bases"]["properties"])
    assert no_schema == {b.value for b in BaseFinanceira}


def test_toda_base_declara_seus_termos():
    """Enum sem termos publicaria base cujo conteúdo só o código-fonte sabe."""
    for base in BaseFinanceira:
        assert termos_da_base(base), f"{base.value} sem termos"


def test_base_amputada_e_a_cheia_diferem_exatamente_pela_fatia_sem_dono():
    """A relação sobre a qual a [[ADR-412]] inteira se apoia, como dado."""
    cheia = set(termos_da_base(BaseFinanceira.carteira_financeira_familia))
    amputada = set(termos_da_base(BaseFinanceira.carteira_com_titular_identificado))
    assert cheia - amputada == {"investimentos_nao_atribuidos"}


# Termo pode nomear OUTRA base (`carteira_produtiva_familia` = carteira financeira
# + cat_2). Comparar sem resolver acusaria divergência onde só há indireção.
def _resolver(base: BaseFinanceira) -> set[str]:
    out: set[str] = set()
    for termo in termos_da_base(base):
        nome = termo.lstrip("-")
        vizinha = next((b for b in BaseFinanceira if b.value == nome), None)
        out |= _resolver(vizinha) if vizinha else {termo}
    return out


# Mata: proibir uma base que não tem par cheio (piso sem intervalo é número
# amputado com outro nome), ou liberar uma amputada como denominador sozinho.
def test_toda_base_proibida_tem_um_par_cheio_que_a_contem():
    proibidas = {b for b in BaseFinanceira if not publicavel_sozinha(b)}
    assert proibidas, "sem base proibida, o intervalo declarado não tem extremo"

    for piso in proibidas:
        alvo = _resolver(piso) | {"investimentos_nao_atribuidos"}
        pares = [b for b in BaseFinanceira if publicavel_sozinha(b) and _resolver(b) == alvo]
        assert len(pares) == 1, f"{piso.value} não tem par cheio único: {pares}"


def test_base_amputada_nunca_e_publicavel_sozinha():
    """A base que amputa a fatia sem dono só vale como extremo de intervalo."""
    assert not publicavel_sozinha(BaseFinanceira.carteira_com_titular_identificado)


# -- PapelMembro ------------------------------------------------------------


# `role_of` MORREU no C2 deste PR. O tripwire que a vigiava foi DELETADO junto,
# nunca relaxado ([[ADR-412]] §Emenda E8). O que resta é o que ainda importa:
# a string publicada não pode se mover.
def test_papel_membro_preserva_as_strings_publicadas():
    assert PapelMembro.titular.value == "titular"
    assert PapelMembro.conjuge.value == "conjuge"
    assert len(PapelMembro) == 3


def test_nao_existe_produtor_binario_de_papel():
    """Mata: ressuscitar `role_of`/`inv_key`, que colapsavam o terceiro caso."""
    from pipeline.domain.services.patrimonio_types import MemberIdentity

    assert not hasattr(MemberIdentity, "role_of")
    assert not hasattr(MemberIdentity, "inv_key")


# -- número-neutralidade: ausente valida, presente valida, lixo NÃO valida ----


# NÃO é o gate de neutralidade: 3 chaves contra um schema de ~3.700 linhas.
# Quem mede neutralidade é `tests/test_e5_golden_execution.py`, que roda o stage.
def test_payload_sem_os_campos_novos_continua_valido():
    """Payload sem os campos novos segue válido (o gate de neutralidade é o golden)."""
    assert validate_dict(_payload(), "e5_analysis.schema.json") is True


def test_payload_com_os_campos_novos_e_aceito():
    """Sem isto o PR2 escreveria campo que o schema rejeita."""
    payload = _payload(
        bases={
            "carteira_financeira_familia": {
                "termos": list(termos_da_base(BaseFinanceira.carteira_financeira_familia)),
                "valor_brl": 100.0,
            }
        },
        atribuicao_investimentos={
            "status": "parcial",
            "pct_carteira_financeira": 48.13,
            "piso_pct": 1.0,
            "motivo": "fatia sem titular acima do piso",
        },
    )
    assert validate_dict(payload, "e5_analysis.schema.json") is True


def test_base_fora_do_enum_e_rejeitada():
    """Mutação plausível: se isto passar, `additionalProperties` foi afrouxado."""
    payload = _payload(bases={"carteira_inventada": {"valor_brl": 1.0}})
    assert validate_dict(payload, "e5_analysis.schema.json") is False


def test_status_de_atribuicao_fora_do_vocabulario_e_rejeitado():
    """O status reusa o vocabulário fechado da [[ADR-403]]; valor novo é erro."""
    payload = _payload(atribuicao_investimentos={"status": "nao_apurado"})
    assert validate_dict(payload, "e5_analysis.schema.json") is False


# Inspecionar `schema[...]["properties"]` passava verde com `type` que o produtor
# não consegue escrever; por isso aqui valida payload de verdade.
def test_composicao_liquida_aceita_o_balde_sem_dono_e_recusa_sinonimo():
    """[[ADR-412]] §D4: mesmo nome do patrimônio, sem sinônimo — validando de verdade."""
    reserva = {"composicao_liquida": {"investimentos_nao_atribuidos": 10.0}}
    ok = _payload()
    ok["reserva_emergencia"] = reserva
    assert validate_dict(ok, "e5_analysis.schema.json") is True

    tipo_errado = _payload()
    tipo_errado["reserva_emergencia"] = {
        "composicao_liquida": {"investimentos_nao_atribuidos": "10"}
    }
    assert validate_dict(tipo_errado, "e5_analysis.schema.json") is False

    sinonimo = _payload()
    sinonimo["reserva_emergencia"] = {"composicao_liquida": {"investimentos_sem_dono": 10.0}}
    assert validate_dict(sinonimo, "e5_analysis.schema.json") is False


def test_chave_de_componente_casa_o_schema(schema: dict):
    """O par papel->chave é o que impede o PR2 de montar a chave por f-string."""
    props = schema["$defs"]["ReservaComposicaoLiquida"]["properties"]
    for papel in PapelMembro:
        assert chave_de_componente(papel.value) in props


# Mata: `_somar_termos` não resolver referência entre bases. Sem isso a base
# derivada sai ZERO quando o chamador não pré-computa a intermediária — foi
# exatamente assim que `carteira_produtiva_com_titular_identificado` saiu 0 no
# primeiro dogfood, e nenhum teste pegou: só a auditoria do snapshot.
_VALORES = {
    "investimentos_titular": 100.0,
    "investimentos_conjuge": 50.0,
    "investimentos_nao_atribuidos": 200.0,
    "caixa_total_brl": 10.0,
    "cat2_efetivo": 40.0,
    # Maior que `cat2_efetivo` de propósito: geradores ⊆ cat_2 completo, e é essa
    # diferença que separa `carteira_produtiva_fixa` da `carteira_produtiva_familia`.
    "imoveis_investimento": 90.0,
    # [[ADR-420]] §D6: termo de `carteira_produtiva_fixa` na série 2. Estritamente entre
    # `cat2_efetivo` (40) e cat_2 completo (90) — é subconjunto próprio de um e superset
    # do outro, e são essas duas desigualdades que mantêm as seis bases distintas.
    "imoveis_alocacao": 70.0,
    "bruto": 1000.0,
    "dividas": 300.0,
}


def _referencias(base: BaseFinanceira) -> list[str]:
    nomes = {b.value for b in BaseFinanceira}
    return [t.lstrip("-") for t in termos_da_base(base) if t.lstrip("-") in nomes]


def test_base_que_referencia_outra_resolve_o_valor():
    from pipeline.domain.services.bases_financeiras import publicar_bases

    bases = publicar_bases(_VALORES)["bases"]

    for base in BaseFinanceira:
        for nome in _referencias(base):
            valor = bases[base.value]["valor_brl"]
            assert valor > 0, f"{base.value} saiu ZERO — a referência não resolveu"
            assert (
                valor > bases[nome]["valor_brl"]
            ), f"{base.value} não é maior que a base que ela contém"


# ---------------------------------------------------------------------------
# G1 — auto-consistência: `valor_brl` soma exatamente os `termos` declarados
# ---------------------------------------------------------------------------


# Entre o #1741 e o #1757, `carteira_produtiva_com_titular_identificado` publicou
# `valor_brl` = só `cat2_efetivo`, CONTRADIZENDO o `termos` ao lado dela no mesmo bloco —
# e nenhum teste caiu, porque o que existia só checava `> 0` e monotonicidade. Este gate
# não precisa de golden e NUNCA precisa de rebaseline: ele compara o bloco consigo mesmo.
def test_toda_base_reproduz_sobre_os_proprios_termos():
    from backend.app.application.base_declarada import bases_reproduzem
    from pipeline.domain.services.bases_financeiras import publicar_bases

    patrimonio = {**_VALORES, **publicar_bases(_VALORES)}

    assert bases_reproduzem(patrimonio)


# É o que acontece no golden do dogfood, onde `cat2_efetivo` é 0: a base derivada
# reproduz mesmo se o termo sumir do payload.
def test_o_gate_de_reproducao_nao_e_vacuoso():
    """Cada termo cru é NÃO-NULO — com termo zero a soma bate por acidente."""
    from pipeline.domain.services.bases_financeiras import BaseFinanceira, termos_da_base

    nomes = {b.value for b in BaseFinanceira}
    crus = {t.lstrip("-") for b in BaseFinanceira for t in termos_da_base(b)} - nomes

    ausentes = sorted(t for t in crus if not _VALORES.get(t))
    assert not ausentes, f"termos nulos na fixture tornam o gate vacuoso: {ausentes}"


def test_valor_que_contradiz_os_termos_reprova():
    from backend.app.application.base_declarada import bases_reproduzem
    from pipeline.domain.services.bases_financeiras import BaseFinanceira, publicar_bases

    publicado = publicar_bases(_VALORES)
    alvo = BaseFinanceira.carteira_produtiva_com_titular_identificado.value
    # Exatamente o defeito do #1741: a derivada publica só o termo cru.
    publicado["bases"][alvo]["valor_brl"] = _VALORES["cat2_efetivo"]

    assert not bases_reproduzem({**_VALORES, **publicado})


def test_termo_que_some_do_payload_reprova():
    """O leitor resolve termo cru em `patrimonio`; ausente, ele NÃO pode passar calado."""
    from backend.app.application.base_declarada import bases_reproduzem
    from pipeline.domain.services.bases_financeiras import publicar_bases

    sem_termo = {k: v for k, v in _VALORES.items() if k != "cat2_efetivo"}

    assert not bases_reproduzem({**sem_termo, **publicar_bases(_VALORES)})


# ---------------------------------------------------------------------------
# G2 — congelamento de DEFINIÇÃO: termo de base existente exige bump de série
# ---------------------------------------------------------------------------

# Congelado em `BASE_VERSAO_CORRENTE == 1`. O bump responde a "a DEFINIÇÃO de alguma base
# publicada mudou?", nunca a "quantos membros o enum tem": adicionar membro é
# número-neutro (o #1782 é prova), e bumpar nele jogaria `serie_corrente()` em `False` no
# corpus inteiro, degradando o card cambial para `indeterminado` sem corrigir um centavo.
_TERMOS_CONGELADOS = {
    1: {
        "carteira_financeira_familia": (
            "investimentos_titular",
            "investimentos_conjuge",
            "investimentos_nao_atribuidos",
            "caixa_total_brl",
        ),
        "carteira_produtiva_familia": ("carteira_financeira_familia", "cat2_efetivo"),
        "carteira_com_titular_identificado": (
            "investimentos_titular",
            "investimentos_conjuge",
            "caixa_total_brl",
        ),
        "carteira_produtiva_com_titular_identificado": (
            "carteira_com_titular_identificado",
            "cat2_efetivo",
        ),
        "carteira_produtiva_fixa": ("carteira_financeira_familia", "imoveis_investimento"),
        "patrimonio_liquido": ("bruto", "-dividas"),
    },
    # Série 2 desde 2026-08-31 ([[ADR-420]] §D6): só `carteira_produtiva_fixa` muda —
    # o termo cat_2 COMPLETO vira `imoveis_alocacao`, para numerador e denominador da
    # concentração cortarem no mesmo lugar. As outras cinco ficam idênticas à série 1,
    # e é essa igualdade que prova que o bump não arrastou base alheia junto.
    2: {
        "carteira_financeira_familia": (
            "investimentos_titular",
            "investimentos_conjuge",
            "investimentos_nao_atribuidos",
            "caixa_total_brl",
        ),
        "carteira_produtiva_familia": ("carteira_financeira_familia", "cat2_efetivo"),
        "carteira_com_titular_identificado": (
            "investimentos_titular",
            "investimentos_conjuge",
            "caixa_total_brl",
        ),
        "carteira_produtiva_com_titular_identificado": (
            "carteira_com_titular_identificado",
            "cat2_efetivo",
        ),
        "carteira_produtiva_fixa": ("carteira_financeira_familia", "imoveis_alocacao"),
        "patrimonio_liquido": ("bruto", "-dividas"),
    },
}


# Foi o que o #1757 fez ao trocar `_somar_termos` por `_valor_da_base`: o VALOR das
# derivadas mudou sob `base_versao: 1` inalterado, e nada reprovou.
def test_termo_de_base_existente_nao_muda_sem_bump_de_serie():
    """Mudar o que uma base SIGNIFICA sem mover `base_versao` embarca híbrido sem rótulo."""
    from pipeline.domain.services.bases_financeiras import BASE_VERSAO_CORRENTE, termos_da_base

    congelado = _TERMOS_CONGELADOS.get(BASE_VERSAO_CORRENTE)
    assert congelado is not None, (
        f"`BASE_VERSAO_CORRENTE` virou {BASE_VERSAO_CORRENTE} e ninguém congelou os termos "
        "desta série — acrescente a entrada em `_TERMOS_CONGELADOS`"
    )

    for base in BaseFinanceira:
        if base.value not in congelado:
            continue  # membro NOVO é número-neutro: entra sem bump, por decisão
        assert termos_da_base(base) == congelado[base.value], (
            f"`{base.value}` mudou de definição sob `base_versao={BASE_VERSAO_CORRENTE}`. "
            "Bumpe `BASE_VERSAO_CORRENTE` e congele a série nova."
        )


def test_membro_novo_entra_sem_bump():
    """A polaridade oposta: adição pura é número-neutra e NÃO pode exigir bump."""
    from pipeline.domain.services.bases_financeiras import BASE_VERSAO_CORRENTE

    congelado = _TERMOS_CONGELADOS[BASE_VERSAO_CORRENTE]
    novos = {b.value for b in BaseFinanceira} - set(congelado)

    assert all(n not in congelado for n in novos), "membro novo não pode estar no congelado"
