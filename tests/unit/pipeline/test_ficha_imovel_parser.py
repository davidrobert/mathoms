"""Parser da ficha de imóvel e join ficha↔item do E1.5a ([[A40.l121]] · [[ADR-440]] D1/D2)."""

# O texto sintético reproduz o layout medido nos PDFs reais (só a forma — rótulos, ordem e
# pares rótulo:valor por linha); todo valor aqui é inventado.

from __future__ import annotations

import ast
import copy
import json
from decimal import Decimal
from pathlib import Path

from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.stages import ficha_imovel_parser as parser
from pipeline.stages.extract_baseline import _output_to_baseline_json
from scripts.pipeline_common import _build_schema_validator, _schema_to_validate

_RAIZ = Path(__file__).resolve().parents[3]
_TOPO = (
    "IDENTIFICAÇÃO DO CONTRIBUINTE\n"
    "Logradouro: RUA DO CONTRIBUINTE Nº: 1\n"
    "DECLARAÇÃO DE BENS E DIREITOS (Valores em Reais)\n"
    "GRUPO CÓDIGO DISCRIMINAÇÃO SITUAÇÃO EM\n"
    "31/12/2023 31/12/2024\n"
)
_FIM = "DÍVIDAS E ÔNUS REAIS\n11 FINANCIAMENTO IMOBILIARIO 100.000,00 90.000,00\n"
_VEICULO = "02 01 AUTOMOVEL MARCA ZETA 50.000,00 50.000,00\nRENAVAM: 00000000000\n"


def _ficha(disc: str, valor: str, *, iptu: str | None = "1234567", comp: str = "APTO 1") -> str:
    linhas = [f"01 11 {disc} {valor} {valor}", "105 - BRASIL"]
    if iptu is not None:
        linhas.append(f"Inscrição Municipal (IPTU): {iptu}")
    linhas += [
        "Logradouro: RUA ALFA Nº: 100",
        f"Comp.: {comp} Bairro: CENTRO",
        "Município: CIDADE UF: XX CEP: 00000-000",
        "Área Total: 80,0 m² Data de Aquisição: 01/01/2010",
        "Registrado no Cartório: Sim Nome Cartório: 1 CARTORIO DE",
        "Matrícula: 54321 DE REGISTRO DE IMOVEIS",
    ]
    return "\n".join(linhas) + "\n"


def _texto(*fichas: str) -> str:
    return _TOPO + "".join(fichas) + _FIM


def _item(descricao: str, valor: str, **kw) -> dict:
    base = {"codigo": "11", "descricao": descricao, "valor_brl": valor, "membro": "m1", "ano": 2024}
    return {**base, "categoria_hint": "imovel", "secao": "bens_direitos", **kw}


def test_le_os_campos_crus_e_ignora_o_endereco_do_contribuinte() -> None:
    fichas = parser.ler_fichas(_texto(_ficha("APARTAMENTO ALFA", "100.000,00")))
    assert [f.campos for f in fichas] == [
        {
            "inscricao_municipal": "1234567",
            "logradouro": "RUA ALFA",
            "numero": "100",
            "complemento": "APTO 1",
            "matricula": "54321",
        }
    ]


def test_matricula_sem_digito_e_complemento_vazio_sao_omitidos() -> None:
    texto = _texto(_ficha("CASA BETA", "1,00", comp="").replace("54321 ", ""))
    assert set(parser.ler_fichas(texto)[0].campos) == {
        "inscricao_municipal",
        "logradouro",
        "numero",
    }


def test_iptu_da_ficha_seguinte_nao_vaza_para_a_anterior() -> None:
    """Regressão: o fim da ficha ia até o último rótulo antes do próximo `Logradouro`."""
    texto = _texto(
        _ficha("CASA BETA", "1,00", iptu=None), _ficha("CASA GAMA", "2,00", iptu="7654321")
    )
    primeira, segunda = parser.ler_fichas(texto)
    assert "inscricao_municipal" not in primeira.campos
    assert segunda.campos["inscricao_municipal"] == "7654321"
    assert "2,00" in segunda.janela and "1,00" not in segunda.janela


def test_join_pelo_valor_unico_atravessa_bem_que_nao_e_imovel() -> None:
    texto = _texto(
        _ficha("APARTAMENTO ALFA", "100.000,00"), _VEICULO, _ficha("CASA BETA", "200.000,00")
    )
    itens = [_item("APARTAMENTO ALFA", "100000.00"), _item("CASA BETA", "200000.00")]
    resultado = parser.ancorar(texto, itens)
    assert sorted(resultado.ancoras) == [0, 1]
    assert {a["join"] for a in resultado.ancoras.values()} == {"valor"}
    assert (resultado.ambiguas, resultado.sem_ficha) == (0, 0)


def test_mesmo_valor_desempata_por_tokens_com_margem() -> None:
    texto = _texto(
        _ficha("APARTAMENTO ALFA EDIFICIO SOL", "1,00"), _ficha("TERRENO LOTE RURAL", "1,00")
    )
    itens = [_item("TERRENO LOTE RURAL", "1.00"), _item("APARTAMENTO ALFA EDIFICIO SOL", "1.00")]
    resultado = parser.ancorar(texto, itens)
    assert {i: a["join"] for i, a in resultado.ancoras.items()} == {
        0: "valor_tokens",
        1: "valor_tokens",
    }


def test_empate_sem_margem_fica_sem_ancora_e_conta_como_ambiguo() -> None:
    texto = _texto(_ficha("APARTAMENTO ALFA", "1,00"), _ficha("APARTAMENTO ALFA", "1,00"))
    resultado = parser.ancorar(texto, [_item("APARTAMENTO ALFA", "1.00")])
    assert (resultado.ancoras, resultado.ambiguas) == ({}, 1)


def test_divida_de_mesmo_valor_nunca_recebe_ancora_nem_conta() -> None:
    texto = _texto(_ficha("APARTAMENTO ALFA", "100.000,00"))
    divida = _item("FINANCIAMENTO", "100000.00", secao="dividas_onus")
    resultado = parser.ancorar(texto, [divida])
    assert (resultado.ancoras, resultado.ambiguas, resultado.sem_ficha) == ({}, 0, 0)


def test_imovel_sem_ficha_conta_so_quando_o_layout_tem_fichas() -> None:
    com_fichas = parser.ancorar(_texto(_ficha("CASA BETA", "1,00")), [_item("SALA", "9.00")])
    sem_rotulo = parser.ancorar(_TOPO + _FIM, [_item("SALA", "9.00")])
    assert (com_fichas.sem_ficha, sem_rotulo.sem_ficha, sem_rotulo.fichas) == (1, 0, 0)


def test_campo_acima_do_limite_e_descartado() -> None:
    texto = _texto(_ficha("CASA BETA", "1,00").replace("RUA ALFA", "R" * 81))
    resultado = parser.ancorar(texto, [_item("CASA BETA", "1.00")])
    assert "logradouro" not in resultado.ancoras[0] and resultado.descartados == 1


def test_limites_espelham_o_schema_do_e15() -> None:
    schema, _ = _schema_to_validate("e15_baseline_extract.schema.json")
    props = schema["$defs"]["ancora_imovel"]["properties"]
    assert {k: v["maxLength"] for k, v in props.items() if k != "join"} == parser.LIMITE_POR_CAMPO


def test_aplicar_e_idempotente_carimba_a_versao_e_tira_ancora_velha() -> None:
    payload = {
        "itens": [_item("CASA BETA", "1.00"), {**_item("SALA", "9.00"), "ancora_imovel": {}}]
    }
    texto = _texto(_ficha("CASA BETA", "1,00"))
    parser.aplicar_ancoras(payload, texto)
    assinatura = parser.assinatura_de_ancoras(payload)
    parser.aplicar_ancoras(payload, texto)
    assert parser.assinatura_de_ancoras(payload) == assinatura
    assert (
        payload["ancora_versao"] == parser.ANCORA_VERSAO
        and "ancora_imovel" not in payload["itens"][1]
    )


def test_saida_real_do_produtor_com_ancora_valida_contra_o_schema() -> None:
    """A saída do E1.5a com a âncora aplicada — não um literal — cabe no contrato do PR0."""
    item = PatrimonialItem(
        code="11",
        description="APARTAMENTO ALFA",
        category_hint="imovel",
        secao="bens_direitos",
        value_brl=Decimal("100000.00"),
        member_key="m1",
        year=2024,
    )
    saida = BaselinePatrimonialOutput(items=[item], reference_year=2024, confidence=0.9)
    payload = _output_to_baseline_json(saida)
    parser.aplicar_ancoras(payload, _texto(_ficha("APARTAMENTO ALFA", "100.000,00")))
    schema, _ = _schema_to_validate("e15_baseline_extract.schema.json")
    assert payload["itens"][0]["ancora_imovel"]["join"] == "valor"
    assert [e.message for e in _build_schema_validator(schema).iter_errors(payload)] == []


def test_o_parser_so_importa_biblioteca_padrao() -> None:
    """[[ADR-280]]: extração emite valor cru — nem domínio, nem canonicalizer."""
    arvore = ast.parse((_RAIZ / "pipeline/stages/ficha_imovel_parser.py").read_text("utf-8"))
    modulos = {n.module for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)}
    modulos |= {a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert modulos == {"__future__", "json", "re", "unicodedata", "dataclasses", "decimal"}


def test_assinatura_muda_com_a_ancora_e_nao_com_a_ordem_das_chaves() -> None:
    a = {"ancora_versao": "1.0.0", "itens": [{"ancora_imovel": {"join": "valor", "numero": "1"}}]}
    b = copy.deepcopy(a)
    b["itens"][0]["ancora_imovel"] = {"numero": "1", "join": "valor"}
    c = json.loads(json.dumps(a))
    c["itens"][0]["ancora_imovel"]["numero"] = "2"
    assert parser.assinatura_de_ancoras(a) == parser.assinatura_de_ancoras(b)
    assert parser.assinatura_de_ancoras(a) != parser.assinatura_de_ancoras(c)
