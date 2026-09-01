"""Produtor da âncora `cnpj_emissor` — boundary, artefato e carreta ([[A42.l15]] PR1).

Três pernas, porque cada uma cai por um motivo diferente e nenhuma cobre a outra:

1. **Boundary** — o `field_validator` normaliza a máscara do documento e degrada para
   ``None`` o que não soma 14 dígitos. Pino NORMALIZADOR (molde [[ADR-288]]), não de
   vacuidade: falhar aqui derrubaria o documento inteiro via reask ([[ADR-292]]).
2. **Artefato** — `_output_to_baseline_json` tem de EMITIR a chave. O schema é
   `additionalProperties: false`, então produtor e contrato divergem em silêncio.
3. **Carreta** — `consolidate_from_itens` monta `entry` campo a campo. Sem copiar a
   âncora, o produtor nasce inerte para a chave, que é o consumidor. É a §Armadilha (A)
   da lane na direção inversa: consumidor sem caminho até o produtor.
"""

from __future__ import annotations

import contextlib
import io
from decimal import Decimal

import pytest

from pipeline.llm.schemas.e15_baseline import BaselinePatrimonialOutput, PatrimonialItem
from pipeline.stages.extract_baseline import _output_to_baseline_json
from scripts.consolidate_baseline import consolidate_from_itens

_CNPJ = "12345678000195"


def _item(**over) -> PatrimonialItem:
    base = dict(
        code="41",
        description="CDB BANCO EXEMPLO",
        category_hint="investimento",
        institution="Banco Exemplo",
        value_brl=Decimal("600000.00"),
        member_key="m1",
        year=2025,
    )
    base.update(over)
    return PatrimonialItem(**base)


class TestBoundaryNormaliza:
    @pytest.mark.parametrize(
        "bruto",
        ["12.345.678/0001-95", "12345678000195", " 12.345.678/0001-95 ", "12 345 678 0001 95"],
    )
    def test_mascara_do_documento_vira_14_digitos(self, bruto: str) -> None:
        assert _item(cnpj_emissor=bruto).cnpj_emissor == _CNPJ

    @pytest.mark.parametrize("bruto", ["<UNKNOWN>", "N/A", "", "123", "1234567800019", None])
    def test_ilegivel_degrada_para_none_sem_derrubar_o_item(self, bruto) -> None:
        """Degradar mantém o sinal item-level; levantar queimaria reask do documento."""
        assert _item(cnpj_emissor=bruto).cnpj_emissor is None

    def test_ausente_e_a_forma_certa_do_campo(self) -> None:
        assert _item().cnpj_emissor is None


class TestArtefatoEmite:
    def test_com_ancora_a_chave_aparece(self) -> None:
        out = BaselinePatrimonialOutput(
            items=[_item(cnpj_emissor="12.345.678/0001-95")], reference_year=2025, confidence=0.9
        )
        assert _output_to_baseline_json(out)["itens"][0]["cnpj_emissor"] == _CNPJ

    def test_sem_ancora_a_chave_NAO_aparece(self) -> None:
        """`None` explícito violaria o `pattern` do schema — omitir é o contrato."""
        out = BaselinePatrimonialOutput(items=[_item()], reference_year=2025, confidence=0.9)
        assert "cnpj_emissor" not in _output_to_baseline_json(out)["itens"][0]


def _consolida(itens: list[dict]) -> list[dict]:
    with contextlib.redirect_stdout(io.StringIO()):
        cons = consolidate_from_itens({"resumo": {"ano_referencia": 2025}, "itens": itens})
    return cons.get("investimentos_consolidados") or []


_ITEM_BRUTO = {
    "codigo": "41",
    "descricao": "CDB BANCO EXEMPLO",
    "categoria_hint": "investimento",
    "valor_brl": "600000.00",
    "membro": "m1",
    "ano": 2025,
}


class TestCarretaAteOConsumidor:
    def test_ancora_sobrevive_ao_consolidador(self) -> None:
        entradas = _consolida([{**_ITEM_BRUTO, "cnpj_emissor": _CNPJ}])
        assert entradas and entradas[0].get("cnpj_emissor") == _CNPJ

    def test_sem_ancora_o_consolidador_nao_inventa(self) -> None:
        entradas = _consolida([dict(_ITEM_BRUTO)])
        assert entradas and "cnpj_emissor" not in entradas[0]

    def test_a_carreta_nao_depende_de_instituicao(self) -> None:
        """`instituicao` falta em 25,8% do corpus e sai da chave ([[ADR-400]] §1)."""
        entradas = _consolida([{**_ITEM_BRUTO, "cnpj_emissor": _CNPJ}])
        assert entradas[0].get("cnpj_emissor") == _CNPJ
        assert "instituicao" not in entradas[0]
