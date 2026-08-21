"""RV6-15 / FP-4 — RL2 lê taxa NUMÉRICA e declara o período.

Quatro cegueiras independentes deixavam a RL2 hard inalcançável; esta lane fecha
duas delas (B4/B5, do lado do parser):

- B4: `_parse_taxa_mensal` exigia `%` LITERAL na string, mas o schema tipa
  `taxa_juros_aa` (então `taxa_juros`) como `["number","null"]` — taxa numérica
  válida NÃO disparava.
- B5 (latente): o limiar `> 1,5` é MENSAL e o único produtor estruturado de taxa
  no produto (`debts.taxa_juros_aa`, ADR-227) guarda ANUAL. Preencher direto faria
  12,5% a.a. ser lido como mensal — over-firing de hard-block em 100% dos
  financiamentos imobiliários.

B1/B2 (o portão `_is_aporte_risco`) seguem abertos e são de outra lane: mexer neles
mexe também na RL1, que é hard-block.

Fixtures sintéticas PII-zero.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import jsonschema
import pytest

from backend.app.services.parecer_guardrails_divida import _TAXA_PATH
from backend.app.services.parecer_red_lines import (
    LIMIAR_TAXA_MENSAL_PCT,
    RED_LINES_VERSION,
    TAXA_KEYS,
    _taxa_mensal_equivalente,
    check_red_lines,
    taxa_declarada,
)
from tests.fixtures.parecer_red_lines import CLEAN, POISONED, _e5, _output, _sug

_APORTE = "Aportar mais em ações de dividendos para acelerar o patrimônio."


def _com_divida(taxa) -> dict:
    return _e5(
        endividamento={
            "dividas": [
                {"descricao": "Cartão rotativo", "saldo_devedor": 20_000.0, "taxa_juros_aa": taxa}
            ]
        }
    )


class TestParserDeTaxa:
    @pytest.mark.parametrize(
        ("taxa_aa", "esperado_am"),
        [(180.0, 8.96), (25.0, 1.88), (12.0, 0.95)],
    )
    def test_numero_e_lido_como_percentual_ao_ano(self, taxa_aa, esperado_am):
        assert _taxa_mensal_equivalente(taxa_aa) == pytest.approx(esperado_am, abs=0.01)

    def test_string_com_percent_nao_e_adivinhada(self):
        """B5: string não declara período de forma confiável; adivinhar é o
        over-firing. O schema já proíbe string aqui."""
        assert _taxa_mensal_equivalente("5,5% a.m.") is None
        assert _taxa_mensal_equivalente("N/D") is None

    def test_nulo_e_ausencia(self):
        assert _taxa_mensal_equivalente(None) is None

    def test_booleano_nao_e_numero(self):
        """`bool` é subclasse de `int` — sem guarda, True viraria 100% a.a."""
        assert _taxa_mensal_equivalente(True) is None


class TestRL2ComTaxaNumerica:
    def test_taxa_de_cartao_dispara_hard_block(self):
        result = check_red_lines(_output(sugestoes_execucao=[_sug(_APORTE)]), _com_divida(180.0))
        assert {v.rl_id: v.severity for v in result.violations}.get("RL2") == "block"

    def test_financiamento_imobiliario_nao_dispara(self):
        """Polaridade — a cegueira B5 faria 12% a.a. bloquear como se fosse mensal."""
        result = check_red_lines(_output(sugestoes_execucao=[_sug(_APORTE)]), _com_divida(12.0))
        assert "RL2" not in {v.rl_id for v in result.violations}

    def test_limiar_e_declarado_em_ao_mes(self):
        assert LIMIAR_TAXA_MENSAL_PCT == 1.5

    def test_versao_bumpada(self):
        """Bump invalida o cache do parecer (compute_cache_key)."""
        assert RED_LINES_VERSION != "1.4"


@functools.lru_cache(maxsize=None)
def _e5_divida_items_schema() -> dict:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "config/schemas/e5_analysis.schema.json").read_text())
    return schema["properties"]["endividamento"]["properties"]["dividas"]["items"]


@pytest.mark.parametrize("fx", [*POISONED, *CLEAN], ids=lambda f: getattr(f, "fixture_id", "?"))
def test_dividas_das_fixtures_respeitam_o_contrato_do_e5(fx):
    """Fixture e código compartilhavam a crença errada: a fixture que "provava" a
    RL2 usava `"5,5% a.m."`, forma que o schema do E5 REJEITA. Sem este gate,
    consertar o código deixa o teste provando o payload impossível."""
    items_schema = _e5_divida_items_schema()
    for divida in (fx.e5.get("endividamento") or {}).get("dividas") or []:
        jsonschema.validate(divida, items_schema)


# Sem estes testes o merge do vizinho reintroduz a cegueira B3 em SILÊNCIO: o rename
# vive em arquivos que este PR não toca, então dá zero conflito e zero teste vermelho.
class TestComposicaoComORename:
    """O RV6-15 (#1573) renomeia `taxa_juros` → `taxa_juros_aa` no produtor do E5."""

    def test_dispara_no_formato_novo(self):
        result = check_red_lines(_output(sugestoes_execucao=[_sug(_APORTE)]), _com_divida(180.0))
        assert {v.rl_id: v.severity for v in result.violations}.get("RL2") == "block"

    def test_dispara_no_formato_legado(self):
        """Ponte: a red line não pode depender de ordem de merge nem de artefato já
        persistido. As duas chaves carregam a MESMA semântica (% a.a.)."""
        e5 = _e5(
            endividamento={
                "dividas": [{"descricao": "Cartão", "saldo_devedor": 20_000.0, "taxa_juros": 180.0}]
            }
        )
        result = check_red_lines(_output(sugestoes_execucao=[_sug(_APORTE)]), e5)
        assert {v.rl_id: v.severity for v in result.violations}.get("RL2") == "block"

    def test_chave_canonica_vem_primeiro(self):
        assert TAXA_KEYS[0] == "taxa_juros_aa"
        assert taxa_declarada({"taxa_juros_aa": 180.0, "taxa_juros": 5.0}) == 180.0

    def test_piso_do_fp4_injeta_o_path_canonico(self):
        """O pedido alimenta a expansão do manifest — apontar para a chave aposentada
        mandaria o próximo leitor procurar no lugar errado."""
        assert _TAXA_PATH.endswith(".taxa_juros_aa")
