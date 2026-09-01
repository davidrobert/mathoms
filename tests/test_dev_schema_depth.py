"""Gate do instrumento de grão ([[A42.l26]]) — o número tem de discriminar.

Métrica de cobertura que não muda quando a cobertura muda é decoração. Cada
teste aqui prende o `dev/schema_depth.py` a um fato do repo, não a si mesmo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))

from dev.schema_depth import medir_grao, medir_grao_por_nome  # noqa: E402

_BASELINE = _RAIZ / "config/schemas/baseline_patrimonial.schema.json"

# Os 4 terminais que a [[A42.l26]] apertou. A/B por MUTAÇÃO do arquivo vivo, não
# contra um SHA: `git show <sha>` morre no squash-merge, e uma cópia do schema
# antigo dentro do teste vira constante que ele compara consigo mesma.
_TERMINAIS_DA_LANE = {
    "$.imoveis_consolidados[]": "imoveis_consolidados",
    "$.investimentos_consolidados[]": "investimentos_consolidados",
    "$.veiculos_consolidados[]": "veiculos_consolidados",
}


def test_o_baseline_tem_grao_hoje():
    grao = medir_grao_por_nome("baseline_patrimonial.schema.json")
    assert grao is not None and grao.declarado, f"sem grão: {grao.sem_grao}"


def test_a_metrica_flipa_quando_o_required_do_item_some():
    """Não-inércia contra o arquivo vivo: sem `required` no item, o grão some.

    Mede o schema real com um mecanismo removido — se a métrica continuasse
    dizendo `declarado`, ela estaria lendo outra coisa que não o contrato.
    """
    schema = json.loads(_BASELINE.read_text(encoding="utf-8"))
    for colecao in _TERMINAIS_DA_LANE.values():
        schema["properties"][colecao]["items"].pop("required")
    schema["properties"]["patrimonio_por_ano"]["additionalProperties"].pop("required")
    grao = medir_grao(schema)
    assert not grao.declarado
    assert set(grao.sem_grao) == set(_TERMINAIS_DA_LANE) | {"$.patrimonio_por_ano.*"}


def test_mapa_de_chave_livre_conta_como_terminal():
    """`patrimonio_por_ano.*` é item tanto quanto `imoveis[]` — item de mapa é item.

    Sem isto o contrato fecharia o array e deixaria o mapa aberto, e o número
    diria `declarado` sobre um payload em que `{}` ainda atravessa.
    """
    grao = medir_grao(
        {
            "type": "object",
            "properties": {
                "por_ano": {"type": "object", "additionalProperties": {"type": "object"}}
            },
        }
    )
    assert grao.sem_grao == ("$.por_ano.*",)


def test_schema_sem_colecao_e_declarado_por_vacuidade():
    """Contrato sem item não tem grão por medir — penalizá-lo seria falso-vermelho."""
    grao = medir_grao({"type": "object", "properties": {"nome": {"type": "string"}}})
    assert grao.terminais == () and grao.declarado


def test_ref_entre_arquivos_e_seguido():
    """O backstop `anyOf` de `$ref` da [[ADR-427]] D4 mediria 0 terminais sem isto."""
    grao = medir_grao_por_nome("e4_unified.schema.json")
    assert grao is not None
    assert len(grao.terminais) > 1, "o backstop não delegou — `$ref` não foi seguido"


def test_o_denominador_nao_conta_propriedade_nomeada():
    """Objeto nomeado não é item; contá-lo inflaria e o número pararia de discriminar."""
    grao = medir_grao(
        {
            "type": "object",
            "properties": {"bloco": {"type": "object", "properties": {"x": {"type": "string"}}}},
        }
    )
    assert grao.terminais == ()


@pytest.mark.parametrize(
    "nome,esperado",
    [
        # Os dois schemas que a [[A42.l19]] promoveu para a fila de flip: o item
        # da coleção não exige chave nenhuma, então `{}` atravessa e o `0 erros`
        # deles não é afirmação sobre a transação.
        ("e4_cashflow.schema.json", ("$.dados.*[]",)),
        ("e4_investimentos.schema.json", ("$.dados[]",)),
    ],
)
def test_os_schemas_da_fila_de_flip_ainda_nao_tem_grao(nome, esperado):
    grao = medir_grao_por_nome(nome)
    assert grao is not None and grao.sem_grao == esperado


# ===========================================================================
# Cobertura por profundidade — o termo que veta o veredito ([[A42.l26]])
# ===========================================================================

from dev.schema_depth import medir_cobertura  # noqa: E402

_MAPA_COM_ITEM_DECLARADO = {
    "type": "object",
    "properties": {
        "dados": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {"type": "object", "properties": {"valor": {"type": "number"}}},
            },
        }
    },
}


def test_mapa_de_chave_livre_nao_dispara():
    """`{categoria → lançamentos}` modela dado na chave; diferenciá-la é falso-vermelho.

    Sem esta regra, 8 nós legítimos do repo reprovariam — medido na A42.l26.
    """
    cob = medir_cobertura(_MAPA_COM_ITEM_DECLARADO, {"dados": {"alimentacao": [{"valor": 1}]}})
    assert cob.completa


def test_item_do_mapa_com_chave_nao_declarada_dispara():
    """E o item DENTRO do mapa continua medido — a cobertura desce, ela não para na chave."""
    cob = medir_cobertura(
        _MAPA_COM_ITEM_DECLARADO, {"dados": {"alimentacao": [{"valor": 1, "extra": 2}]}}
    )
    assert cob.chaves_fora == {"$.dados.*[]": {"extra"}} and not cob.nos_indeclarados


def test_no_indeclarado_conta_como_defeito_e_nao_como_ausencia():
    """`{"type": "object"}` vazio é profundidade NÃO MEDIDA.

    Se contasse como ausência, apagar `properties` seria o caminho barato para o
    verde — a métrica passaria a premiar quem deleta a declaração.
    """
    schema = {"type": "object", "properties": {"itens": {"type": "array", "items": {"type": "object"}}}}
    cob = medir_cobertura(schema, {"itens": [{"a": 1}, {"b": 2}]})
    assert cob.nos_indeclarados == {"$.itens[]": 2} and not cob.completa


def test_chaves_de_no_indeclarado_nao_sao_publicadas():
    """Ali as chaves são DADO (mês, membro), não nome de campo — só path e contagem."""
    schema = {"type": "object", "properties": {"por_membro": {"type": "object"}}}
    cob = medir_cobertura(schema, {"por_membro": {"nome_de_pessoa": 1}})
    assert cob.chaves_fora == {} and cob.nos_indeclarados == {"$.por_membro": 1}


def test_ref_entre_arquivos_e_resolvido_na_cobertura():
    """Contrato cuja profundidade toda está atrás de `$ref` sairia verde sem isto."""
    schema = {
        "type": "object",
        "properties": {"razoes": {"type": "array", "items": {"$ref": "review_reason.schema.json"}}},
    }
    valido = {"razoes": [{"code": "x", "stage": "y", "artifact_key": "z"}]}
    assert medir_cobertura(schema, valido).completa
    cob = medir_cobertura(schema, {"razoes": [{"code": "x", "chave_inventada": 1}]})
    assert cob.chaves_fora == {"$.razoes[]": {"chave_inventada"}}


def test_a_uniao_de_ramos_vale_para_anyof():
    """Sob `anyOf`, basta UM ramo declarar — interseção fabricaria defeito inexistente."""
    schema = {
        "anyOf": [
            {"type": "object", "properties": {"a": {}}},
            {"type": "object", "properties": {"b": {}}},
        ]
    }
    assert medir_cobertura(schema, {"a": 1, "b": 2}).completa
