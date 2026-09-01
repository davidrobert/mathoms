"""Gate [[ADR-432]] D5 — o contrato do baseline declara o que os produtores emitem.

Igualdade de conjunto nos **dois sentidos** ([[ADR-427]] D5), porque cada direção
pega um defeito diferente:

- **emitida ⊄ declarada** — chave nova entra calada e, sob `additionalProperties:
  false`, aborta o write em `strict`. Foi o que a [[ADR-409]] §F mediu: 8 chaves
  emitidas fora do contrato, 3 delas em 100% dos artefatos.
- **declarada ⊄ emitível** — fantasma acumula. Eram 6 quando esta lane começou
  (`anos_base`, `declarations`, `properties`, `receipts`, `summary` + as 2 fósseis
  que o PR-A matou), e o contrato descrevia 5 de 11.

O conjunto emitido vem de **rodar o produtor**, nunca de lista à mão — lista à mão é
a fantasma da próxima vez. `membros` é o único declarado por alcance de código: o
`BaselineNormalizer` a emite por alias de `membros_familia`, que o corpus não tem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))

_SCHEMA = _RAIZ / "config/schemas/baseline_patrimonial.schema.json"
_EXTRACT = _RAIZ / "tests/fixtures/pipeline_golden/dogfood/baseline-1.5.json"

# Passthrough do extract E1.5: `consolidate` copia as chaves do input para o output.
# Vive aqui, e não na fixture golden, para não rebaselinar golden alheio.
_PASSTHROUGH = {"_meta": {}, "payload_version": 1, "prompt_version": "v1"}

# Emitíveis só por caminho que o corpus não exercita. Cada entrada é **exercitada**
# abaixo, nunca só afirmada — exceção sem alcance provado é a próxima fantasma.
_EMITIVEIS_POR_ALIAS = {
    "membros": "BaselineNormalizer passo 1, alias de `membros_familia`",
}


def _declaradas() -> set[str]:
    return set(json.loads(_SCHEMA.read_text(encoding="utf-8"))["properties"])


def _emitidas_pelo_produtor() -> set[str]:
    """O que `consolidate_baseline` escreve, medido rodando-o (inclui o merge de informe)."""
    from scripts.consolidate_baseline import consolidate

    entrada = json.loads(_EXTRACT.read_text(encoding="utf-8")) | _PASSTHROUGH
    saida = consolidate(entrada)
    _aplicar_merge_de_informe(saida)
    return set(saida)


def _aplicar_merge_de_informe(consolidado: dict) -> None:
    # O call-site real precisa de sessão de DB, mas a função aceita `merge_fn` e
    # `session_factory` por parâmetro — então o caminho roda hermético.
    """`informe_pf_saldos_31_12` + `wise_fiscal_flags` ([[ADR-238]]) com fakes injetados."""
    from contextlib import contextmanager
    from types import SimpleNamespace

    from scripts.consolidate_baseline import _invoke_informe_pf_merge

    @contextmanager
    def _sessao_falsa():
        yield None

    def _merge(baseline, *, workspace_id, db):
        return SimpleNamespace(
            saldos_added=1,
            fiscal_flags=["sintetica"],
            baseline={"informe_pf_saldos_31_12": [], "wise_fiscal_flags": []},
        )

    _invoke_informe_pf_merge(_merge, _sessao_falsa, "ws-sintetico", consolidado)


def _emitidas_pelo_normalizer(base: dict) -> set[str]:
    """O que o E4 publica no balde `patrimonio` a partir do mesmo baseline."""
    from pipeline.domain.services.baseline_normalizer import BaselineNormalizer

    return set(BaselineNormalizer().normalize(base).data)


def test_nenhuma_chave_emitida_fica_fora_do_contrato():
    emitidas = _emitidas_pelo_produtor()
    assert emitidas, "produtor devolveu payload vazio — o gate seria vácuo"
    fora = emitidas - _declaradas()
    assert fora == set(), (
        f"emitidas e não declaradas: {sorted(fora)}. Com `additionalProperties: false` "
        "isto aborta o write em `strict` ([[ADR-432]] D4)."
    )


def test_o_balde_do_e4_tambem_cabe_no_contrato():
    """A segunda ponta: o E4 publica o mesmo contrato pela `artifact_key` ([[ADR-427]] D3)."""
    base = _emitidas_pelo_produtor()
    entrada = json.loads(_EXTRACT.read_text(encoding="utf-8"))
    from scripts.consolidate_baseline import consolidate

    fora = _emitidas_pelo_normalizer(consolidate(entrada)) - _declaradas()
    assert base and fora == set(), f"o E4 emite fora do contrato: {sorted(fora)}"


def test_nenhuma_declarada_e_fantasma():
    emitiveis = _emitidas_pelo_produtor() | set(_EMITIVEIS_POR_ALIAS)
    fantasmas = _declaradas() - emitiveis
    assert fantasmas == set(), (
        f"declaradas que produtor nenhum emite: {sorted(fantasmas)}. "
        "Contrato que descreve o que ninguém escreve é o defeito da [[ADR-409]] §F."
    )


def test_o_merge_de_informe_realmente_emite_as_duas_chaves():
    """Não-inércia do fake: se o merge parar de emitir, o gate acima vira vácuo."""
    from scripts.consolidate_baseline import consolidate

    consolidado = consolidate(json.loads(_EXTRACT.read_text(encoding="utf-8")))
    antes = set(consolidado)
    _aplicar_merge_de_informe(consolidado)

    assert set(consolidado) - antes == {"informe_pf_saldos_31_12", "wise_fiscal_flags"}


def test_o_passthrough_do_extract_chega_ao_consolidado():
    """Idem: se `consolidate` parar de copiar, as 3 chaves sumiriam do conjunto medido."""
    from scripts.consolidate_baseline import consolidate

    saida = consolidate(json.loads(_EXTRACT.read_text(encoding="utf-8")) | _PASSTHROUGH)

    assert set(_PASSTHROUGH) <= set(saida)


def test_toda_excecao_de_alias_e_mesmo_emitivel():
    """Não-inércia da whitelist: cada exceção tem de ser alcançável de fato."""
    from pipeline.domain.services.baseline_normalizer import BaselineNormalizer

    saida = BaselineNormalizer().normalize({"membros_familia": [{"nome": "Sintetico"}]}).data
    assert "membros" in saida, "a exceção `membros` não é mais emitível — remova-a da whitelist"
    assert set(_EMITIVEIS_POR_ALIAS) == {
        "membros"
    }, "exceção nova exige emissor nomeado e um teste de alcance como o acima"


def test_o_ramo_declarations_da_raiz_nao_voltou():
    """[[ADR-432]] D3 — `oneOf` de raiz colapsado; Format B era ramo morto."""
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    assert "oneOf" not in schema
    assert schema["required"] == ["patrimonio_por_ano"]
    assert schema["additionalProperties"] is False
