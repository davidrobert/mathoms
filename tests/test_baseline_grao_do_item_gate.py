"""Gate [[A42.l26]] — o contrato do baseline mede o **item**, não só a raiz.

A [[ADR-432]] fechou a raiz (`required` + `additionalProperties: false` nas 15
chaves de topo) e o defeito desceu um nível: o item de `imoveis_consolidados`,
`investimentos_consolidados` e `veiculos_consolidados` não tinha `required` nem
fecho, então **item vazio `{}`, campo não previsto e valor fora de tipo
atravessavam** — medidos, 8 casos. Guard que valida largura declara cobertura que
não tem, que é a classe da [[A42.l24]].

Duas famílias de teste, e cada uma pega um defeito que a outra não pega:

- **completude por igualdade de conjunto no grão do item**, nos dois sentidos e
  derivada de **rodar o produtor** ([[ADR-427]] D5 · [[ADR-432]] D5). Sem ela, o
  fecho vira armadilha: chave nova no item aborta o write em `strict`.
- **contrafactual por caso, com não-inércia por subconjunto**. Cada mecanismo do
  aperto é mutado sozinho; o caso que deixa de reprovar nomeia qual mecanismo o
  sustenta. Sem isso, um `additionalProperties` a mais faria os 8 casos passarem
  e nenhum teste distinguiria qual linha os produz.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))

_SCHEMA = _RAIZ / "config/schemas/baseline_patrimonial.schema.json"
_COLECOES = ("imoveis_consolidados", "investimentos_consolidados", "veiculos_consolidados")

# Emitíveis só pelo ramo `consolidate_from_declarations` (IRPF legado + XLSX de
# imóveis), que o corpus não exercita — 0/1154 itens em 171 artefatos. Declaradas
# por **alcance de código**, na forma da [[ADR-432]] D1: sob
# `additionalProperties: false` em `strict`, chave emitível e não declarada aborta
# o write. Cada entrada é exercitada em
# `test_o_ramo_legado_emite_as_tres_chaves_do_alcance` — exceção sem alcance
# provado é a próxima fantasma.
_EMITIVEIS_POR_ALCANCE = {
    "imoveis_consolidados": {"endereco", "dados_completos", "fonte"},
}


# ===========================================================================
# Substrato — o produtor real, rodado sobre entrada sintética PII-zero
# ===========================================================================


def _item(**kw) -> dict:
    base = {"membro": "membro_a", "ano": 2024, "valor_brl": 100.0, "secao": "bens_direitos"}
    base.update(kw)
    return base


# Cada linha existe para exercitar um ramo do produtor ou de um enriquecedor; o
# comentário diz qual. Linha sem ramo próprio é massa morta que infla o gate.
_ENTRADA = {
    "resumo": {"ano_referencia": 2024},
    "itens": [
        # co-declarado (mesmo `codigo`+`descricao`, dois membros) → `imoveis_dedup`
        # funde e emite `proprietarios` + `_dedup_warning` (valores divergem >10%).
        _item(codigo="01", descricao="APTO ALFA", categoria_hint="imovel"),
        _item(codigo="01", descricao="APTO ALFA", categoria_hint="imovel", membro="membro_b", valor_brl=200.0),
        # `instituicao` no item do E1.5 → copiada para o balde.
        _item(codigo="11", descricao="SALA DELTA", categoria_hint="imovel", instituicao="INST X"),
        # sem `secao` → eixo decidido por hint → `property_identity_enricher`
        # recusa o mint ([[ADR-398]]) e emite `needs_review` + `review_reasons`.
        _item(codigo="12", descricao="LOTE GAMA", categoria_hint="imovel", secao=None),
        _item(codigo="02", descricao="CARRO 2020", categoria_hint="veiculo"),
        _item(codigo="02", descricao="MOTO 2019", categoria_hint="veiculo", membro="membro_b"),
        # âncora de CNPJ + valor divergente → `investimentos_dedup` marca
        # `_dedup_warning: possivel_duplicata` sem fundir.
        _item(codigo="03", descricao="CDB", categoria_hint="investimento", instituicao="BCO", cnpj_emissor="12345678000199"),
        _item(codigo="03", descricao="CDB", categoria_hint="investimento", instituicao="BCO", cnpj_emissor="12345678000199", membro="membro_b", valor_brl=140.0),
        # âncora + valor idêntico ao centavo → funde e emite `proprietarios`.
        _item(codigo="05", descricao="LCI", categoria_hint="investimento", instituicao="BCO2", cnpj_emissor="98765432000155"),
        _item(codigo="05", descricao="LCI", categoria_hint="investimento", instituicao="BCO2", cnpj_emissor="98765432000155", membro="membro_b"),
        _item(codigo="04", descricao="FUNDO", categoria_hint="investimento"),
        # sem descrição e sem âncora → recusa de identidade ([[A42.l15]]) com
        # `review_reasons` no próprio item.
        _item(codigo="04", descricao="", categoria_hint="investimento"),
    ],
}


class _ResolverDeIdentidade:
    """Fake do `PropertyIdentityResolver` — id derivado do lookup, não constante.

    Constante faria o `imoveis_dedup` fundir imóveis distintos e o gate mediria
    um payload que produtor nenhum escreve.
    """

    def match_or_create(self, *, workspace_id, lookup, first_seen_year, descricao_sample):
        return SimpleNamespace(
            property_id=f"prop-{lookup.codigo_rfb}-{lookup.endereco_canonical}",
            endereco_canonical=lookup.endereco_canonical,
            low_confidence=False,
        )


def _baseline_do_produtor() -> dict:
    """Roda o produtor e a cadeia de enriquecedores puros que `main_with_store` roda."""
    from pipeline.domain.services.imoveis_dedup import dedup_imoveis_consolidados
    from pipeline.domain.services.investimentos_dedup import dedup_investimentos_consolidados
    from pipeline.domain.services.property_identity_enricher import (
        enrich_imoveis_with_property_ids,
    )
    from pipeline.domain.services.valor_nao_apurado import sanear_baseline
    from pipeline.domain.services.vehicle_reconciliation import reconcile_baseline_veiculos
    from scripts.consolidate_baseline import consolidate_from_itens

    base = consolidate_from_itens(copy.deepcopy(_ENTRADA))
    enrich_imoveis_with_property_ids(base, resolver=_ResolverDeIdentidade(), workspace_id="ws")
    base["imoveis_consolidados"] = dedup_imoveis_consolidados(
        base["imoveis_consolidados"], titular_key="membro_a"
    ).imoveis
    base["investimentos_consolidados"] = dedup_investimentos_consolidados(
        base["investimentos_consolidados"]
    ).investimentos
    base, _ = reconcile_baseline_veiculos(
        base, [{"id": "v1", "label": "CARRO 2020", "proprietario": "membro_a"}], "ws"
    )
    # O negativo que o saneamento de boundary existe para pegar ([[ADR-431]]): o
    # ramo por item já o desviou para dívidas, e é o merge de informe que o
    # reintroduz depois. Injetar aqui é reproduzir esse caminho, não fabricá-lo.
    for colecao in ("imoveis_consolidados", "veiculos_consolidados"):
        base[colecao][0]["valores_31_12"]["2023"] = -1.0
    sanear_baseline(base)
    return base


def _declaradas(colecao: str) -> set[str]:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return set(schema["properties"][colecao]["items"]["properties"])


def _emitidas(baseline: dict, colecao: str) -> set[str]:
    return {k for item in baseline.get(colecao) or [] for k in item}


# ===========================================================================
# Completude no grão do item — igualdade de conjunto nos dois sentidos
# ===========================================================================


@pytest.fixture(scope="module")
def baseline() -> dict:
    return _baseline_do_produtor()


@pytest.mark.parametrize("colecao", _COLECOES)
def test_nenhuma_chave_de_item_fica_fora_do_contrato(baseline, colecao):
    emitidas = _emitidas(baseline, colecao)
    assert emitidas, f"{colecao} saiu vazia — o gate seria vácuo"
    fora = emitidas - _declaradas(colecao)
    assert fora == set(), (
        f"{colecao}[] emite e não declara: {sorted(fora)}. Com "
        "`additionalProperties: false` no item, isto aborta o write em `strict`."
    )


@pytest.mark.parametrize("colecao", _COLECOES)
def test_nenhuma_declarada_no_item_e_fantasma(baseline, colecao):
    emitiveis = _emitidas(baseline, colecao) | _EMITIVEIS_POR_ALCANCE.get(colecao, set())
    fantasmas = _declaradas(colecao) - emitiveis
    assert fantasmas == set(), (
        f"{colecao}[] declara o que produtor nenhum emite: {sorted(fantasmas)}. "
        "Contrato que descreve o que ninguém escreve é o defeito da [[ADR-409]] §F."
    )


def test_o_ramo_legado_emite_as_tres_chaves_do_alcance(tmp_path):
    """Não-inércia do allowlist: as 3 exceções têm produtor, não são afirmação."""
    import scripts.consolidate_baseline as cb

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "family_members.json").write_text(
        json.dumps({"titular": "membro_a", "membros": {"membro_a": {}, "membro_b": {}}}),
        encoding="utf-8",
    )
    anteriores = (cb.PROJECT_DIR, cb._FAMILY, cb._TITULAR, cb._MEMBROS, cb._MEMBER_KEYS, cb._IMOVEL_MATCH_KEYWORDS)
    try:
        cb._init_config(tmp_path)
        saida = cb.consolidate(
            {
                "declarations": [
                    {
                        "membro": "membro_a",
                        "ano_base": 2024,
                        "bens_direitos": [{"grupo": "01", "descricao": "APTO ALFA", "situacao_atual": 100.0}],
                    }
                ],
                "imoveis_xlsx": [
                    {"nome": "APTO ALFA", "membro": "membro_a", "endereco": "R 1", "valor_compra": 90.0},
                    {"nome": "CASA BETA", "membro": "membro_b", "endereco": "R 2", "valor_compra": 50.0},
                ],
            }
        )
    finally:
        (cb.PROJECT_DIR, cb._FAMILY, cb._TITULAR, cb._MEMBROS, cb._MEMBER_KEYS, cb._IMOVEL_MATCH_KEYWORDS) = anteriores
    emitidas = _emitidas(saida, "imoveis_consolidados")
    assert _EMITIVEIS_POR_ALCANCE["imoveis_consolidados"] <= emitidas, (
        f"o ramo legado não emitiu o allowlist; emitiu {sorted(emitidas)}"
    )
    assert emitidas <= _declaradas("imoveis_consolidados"), (
        f"o ramo legado emite fora do contrato: {sorted(emitidas - _declaradas('imoveis_consolidados'))}"
    )


# ===========================================================================
# Contrafactual por caso — e não-inércia por subconjunto
# ===========================================================================

_ITEM_OK = {
    "descricao": "APTO ALFA",
    "proprietario": "membro_a",
    "tipo": "imovel",
    "valores_31_12": {"2024": 100.0},
}
_ANO_OK = {"total_bens": 1.0, "total_dividas": 0.0}

# Os 8 casos que **atravessavam** o guard antes desta lane, medidos contra o
# schema de `HEAD` em 2026-09-01. `CTRL` é o controle positivo: item real e
# completo continua passando, senão o aperto seria um `False` constante.
_CASOS: dict[str, dict] = {
    "item_vazio_imoveis": {"imoveis_consolidados": [{}]},
    "item_vazio_investimentos": {"investimentos_consolidados": [{}]},
    "item_vazio_veiculos": {"veiculos_consolidados": [{}]},
    "campo_lixo_no_item": {"imoveis_consolidados": [_ITEM_OK | {"campo_lixo": "x"}]},
    "num_como_str_em_chave_nao_ano": {
        "imoveis_consolidados": [_ITEM_OK | {"valores_31_12": {"total": "100.00"}}]
    },
    "ano_objeto_vazio": {"patrimonio_por_ano": {"2024": {}}},
    "lixo_no_ano_objeto": {"patrimonio_por_ano": {"2024": _ANO_OK | {"lixo": "x"}}},
    "chave_nao_ano_em_patrimonio_por_ano": {"patrimonio_por_ano": {"total": _ANO_OK}},
    # Valor NUMÉRICO de propósito: com string, o caso seria pego pelo fecho de
    # `valores_31_12` e não distinguiria nada do `campo_lixo`. Com número, ele só
    # reprova pela CONJUNÇÃO (fecho + pattern sem a alternativa fantasma) — e é
    # por isso que aparece nos dois conjuntos de `_MUTACOES`.
    "chave_com_prefixo_31_12_fantasma": {
        "imoveis_consolidados": [_ITEM_OK | {"valores_31_12": {"31_12_2024": 100.0}}]
    },
}

# Cada mutação desliga UM mecanismo do aperto; o valor é o conjunto EXATO de
# casos que deixam de reprovar sem ele. Igualdade, não `>=`: mutação que derruba
# caso a mais estaria acoplando mecanismos, e mutação que não derruba nenhum é
# linha inerte no schema.
_MUTACOES: dict[str, set[str]] = {
    "item_sem_additionalProperties": {"campo_lixo_no_item"},
    "item_sem_required": {
        "item_vazio_imoveis",
        "item_vazio_investimentos",
        "item_vazio_veiculos",
    },
    "valores_31_12_sem_additionalProperties": {
        "num_como_str_em_chave_nao_ano",
        "chave_com_prefixo_31_12_fantasma",
    },
    "ano_sem_required": {"ano_objeto_vazio"},
    "ano_sem_additionalProperties": {"lixo_no_ano_objeto"},
    "patrimonio_por_ano_sem_propertyNames": {"chave_nao_ano_em_patrimonio_por_ano"},
    "valores_31_12_com_pattern_legado": {"chave_com_prefixo_31_12_fantasma"},
}


def _schema() -> dict:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def _mutar(schema: dict, mutacao: str) -> dict:
    s = copy.deepcopy(schema)
    itens = [s["properties"][c]["items"] for c in _COLECOES]
    ano = s["properties"]["patrimonio_por_ano"]["additionalProperties"]
    if mutacao == "item_sem_additionalProperties":
        for it in itens:
            it.pop("additionalProperties", None)
    elif mutacao == "item_sem_required":
        for it in itens:
            it.pop("required", None)
    elif mutacao == "valores_31_12_sem_additionalProperties":
        for it in itens:
            it["properties"]["valores_31_12"].pop("additionalProperties", None)
    elif mutacao == "ano_sem_required":
        ano.pop("required", None)
    elif mutacao == "ano_sem_additionalProperties":
        ano.pop("additionalProperties", None)
    elif mutacao == "valores_31_12_com_pattern_legado":
        for it in itens:
            padroes = it["properties"]["valores_31_12"]["patternProperties"]
            padroes["^(31_12_)?\\d{4}$"] = padroes.pop("^\\d{4}$")
    elif mutacao == "patrimonio_por_ano_sem_propertyNames":
        s["properties"]["patrimonio_por_ano"].pop("propertyNames", None)
    else:  # pragma: no cover - guarda de digitação
        raise AssertionError(f"mutação desconhecida: {mutacao}")
    return s


def _payload(caso: str) -> dict:
    p = {"patrimonio_por_ano": {"2024": copy.deepcopy(_ANO_OK)}}
    p.update(copy.deepcopy(_CASOS[caso]))
    return p


def _reprova(schema: dict, payload: dict) -> bool:
    from scripts.pipeline_common import _build_schema_validator

    return bool(list(_build_schema_validator(schema).iter_errors(payload)))


@pytest.mark.parametrize("caso", sorted(_CASOS))
def test_o_grao_do_item_reprova_o_caso(caso):
    assert _reprova(_schema(), _payload(caso)), (
        f"{caso} atravessa o contrato — era exatamente o que a [[A42.l26]] mediu."
    )


def test_item_real_do_produtor_continua_passando(baseline):
    """Controle positivo — sem ele, um contrato impossível passaria nos 8 casos."""
    assert not _reprova(_schema(), baseline), "o payload do produtor real reprova no próprio contrato"


@pytest.mark.parametrize("mutacao", sorted(_MUTACOES))
def test_nao_inercia_por_subconjunto(mutacao):
    mutado = _mutar(_schema(), mutacao)
    sobreviventes = {c for c in _CASOS if not _reprova(mutado, _payload(c))}
    assert sobreviventes == _MUTACOES[mutacao], (
        f"sem `{mutacao}` atravessam {sorted(sobreviventes)}; o esperado é "
        f"{sorted(_MUTACOES[mutacao])}. Diferença = mecanismo acoplado ou linha inerte."
    )


def test_o_gate_de_completude_le_o_produtor_e_nao_uma_lista(monkeypatch):
    """Não-inércia do gate de completude, mutando o **produtor** — não o payload.

    Payload mutado prova só que o validador roda. O que precisa ser provado é o
    acoplamento: se `consolidate_from_itens` passar a emitir chave nova no item,
    o gate tem de ficar vermelho **sem ninguém tocar no teste**. Sem isto,
    `_emitidas` poderia estar lendo uma lista congelada e o verde seria vácuo.
    """
    import scripts.consolidate_baseline as cb

    original = cb.consolidate_from_itens

    def _com_chave_nova(*args, **kwargs):
        saida = original(*args, **kwargs)
        for item in saida.get("imoveis_consolidados") or []:
            item["chave_que_o_contrato_nao_conhece"] = 1
        return saida

    monkeypatch.setattr(cb, "consolidate_from_itens", _com_chave_nova)
    mutado = _baseline_do_produtor()
    fora = _emitidas(mutado, "imoveis_consolidados") - _declaradas("imoveis_consolidados")
    assert fora == {"chave_que_o_contrato_nao_conhece"}, (
        "o gate não enxergou a chave que o produtor mutado emitiu — "
        f"diferença medida: {sorted(fora)}"
    )
    assert _reprova(_schema(), mutado), "o contrato aceitou a chave nova no item"
