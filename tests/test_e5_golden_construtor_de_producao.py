"""Golden que atravessa ``from_fiscal_parameters`` — o construtor de PRODUÇÃO (A40.l56).

Antes desta lane, ZERO goldens o atravessavam: `ctx.config_store` era `None` em
todo caminho de teste e `analyze_finances` caía em `from_fiscal` (dict legado).
Consequência medida: o falsy-zero corrigido no #1383 foi corrigido às cegas do
golden — só unit test cobria o construtor que roda em produção.

A sonda de aceite é a mutação de CALL-SITE: trocar `from_fiscal_parameters` por
`from_fiscal` em `e5_analyzer_adapter` tem de derrubar este teste.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tests.pipeline_golden_substrate import (
    fiscal_store_do_seed,
    run_e3_e4_e5,
    write_e5_config,
)
from tests.unit.pipeline._passive_income_builders import decl, exterior_rend

# Dimensionada para a sonda MORDER. `aliquota_fallback` do caminho legado é 7,5%
# e a 2ª faixa da tabela real também — com base tributável na faixa de 7,5% os
# dois caminhos devolvem o MESMO número e o golden passaria verde sem medir nada.
# R$ 40.000/ano cai na faixa de 15% da tabela anual.
#
# Pós-ADR-402 o observável MUDOU DE FORMA, não de dono: `aliquota_marginal` é
# bicondicional com `economia_ir_anual`, e a row AC2026 do seed nasce
# `regime_completo=False` (A40.l64) — o caminho de produção RETÉM a estimativa e
# publica ausência com motivo. `regime_completo`/`componentes_ausentes` só
# existem em `from_fiscal_parameters`; o legado presume completo e publica o
# fallback. A divergência DB↔legado continua sendo o que a sonda morde.
_RENDA_ANUAL_NA_FAIXA_DE_15 = 40_000.0
_ALIQUOTA_DO_FALLBACK_LEGADO = 7.5
_MOTIVO_SO_DO_CAMINHO_DB = "regime_fiscal_incompleto"


_ANO_BASE_IRPF = 2024


def _irpf_com_renda_tributavel() -> dict:
    """`_renda_tributavel` = PJ + PF + exterior; uso exterior por ser o caminho
    mais curto para um valor exato, e o valor é o que dimensiona a sonda."""
    return decl(
        ano_base=_ANO_BASE_IRPF,
        exterior=[exterior_rend(f"{_RENDA_ANUAL_NA_FAIXA_DE_15:.2f}")],
        # Base DECLARADA = bruto menos o desconto simplificado de 20%. Zerá-la fazia
        # a economia degenerar a zero e o golden parava de exercitar a tabela
        # progressiva — cobertura perdida em silêncio quando a [[ADR-414]] tornou a
        # base load-bearing.
        base_calculo=f"{_RENDA_ANUAL_NA_FAIXA_DE_15 * 0.8:.2f}",
    ).model_dump(mode="json")


def _e3_payload() -> dict[str, dict]:
    mensal = round(_RENDA_ANUAL_NA_FAIXA_DE_15 / 12, 2)
    return {
        "itau_extratoconta_BRL_202601_202612": {
            "banco": "itau",
            "tipo_conta": "extratoconta",
            "moeda": "BRL",
            "transacoes": [
                {
                    "data": f"2026-{mes:02d}-05",
                    "descricao": "PRO-LABORE",
                    "valor": mensal,
                    "tipo": "credito",
                    "categoria": "pro_labore",
                }
                for mes in range(1, 13)
            ],
        }
    }


@pytest.fixture
def analise_com_config_store(tmp_path: Path) -> dict:
    # Ano por `date.today().year`, nunca literal: `{2026: fp}` passa hoje e vira
    # KeyError silencioso em 2027 — engolido pelo `except Exception` de
    # analyze_finances:2163, que devolveria o golden ao caminho legado sem falhar.
    ano = date.today().year
    write_e5_config(tmp_path)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads=_e3_payload(),
        irpf_payloads={f"irpfdeclaracao_{_ANO_BASE_IRPF}": _irpf_com_renda_tributavel()},
        config_store=fiscal_store_do_seed(ano),
    )


def _previdencia(analise: dict) -> dict:
    return analise.get("previdencia_pgbl") or {}


def _aliquota(analise: dict):
    return _previdencia(analise).get("aliquota_marginal")


def _motivo_economia(analise: dict):
    return (_previdencia(analise).get("motivo_ausencia") or {}).get("economia")


def test_golden_atravessa_o_construtor_de_producao(analise_com_config_store):
    # Pós-flip do AC2026 (§Critério 3) a marca do caminho DB deixou de ser a RECUSA
    # e passou a ser a alíquota: o fallback legado não tem tabela e devolve 7,5%
    # fixo; só a row do DB resolve a faixa que contém a base.
    """Aceite da lane: ≥1 execução golden passa por `from_fiscal_parameters`."""
    assert _aliquota(analise_com_config_store) != _ALIQUOTA_DO_FALLBACK_LEGADO
    assert _previdencia(analise_com_config_store)["economia_ir_anual"] is not None


def test_o_redutor_da_row_alcanca_o_payload(analise_com_config_store):
    # Compor só o `regime_completo` e esquecer redutor e IRPFM deixava o golden
    # rodando um regime que não existe — completo, mas sem os dois. Com o redutor
    # ativo, bruto de 40.000 fica na banda 1 e o imposto zera.
    """Gate da composição da fixture: ela tem de carregar as TRÊS migrations."""
    bloco = _previdencia(analise_com_config_store)

    assert bloco["economia_ir_anual"] == 0.0
    assert bloco["motivo_ausencia"]["aporte"] == "sem_imposto_a_reduzir"
    # Zero legítimo é FATO publicado sem motivo (invariante ADR-402).
    assert bloco["motivo_ausencia"]["economia"] is None
    # E o fato do IRPF sobrevive.
    assert bloco["limite_pgbl_anual"] > 0


def test_a_aliquota_publicada_nao_e_a_do_fallback(analise_com_config_store):
    """Sem esta asserção, o teste acima passaria com o caminho legado."""
    # 15% é a faixa que CONTÉM a base de 40.000 na tabela anual do seed; o fallback
    # legado não tem tabela e devolveria 7,5% para qualquer base.
    assert _aliquota(analise_com_config_store) != _ALIQUOTA_DO_FALLBACK_LEGADO
    assert _previdencia(analise_com_config_store)["limite_pgbl_anual"] > 0


# Braço de CONTROLE. É ele que torna a sonda de mutação falsificável: os dois
# caminhos precisam divergir NESTA fixture, senão trocar o construtor não muda
# nada e o golden acima passaria verde sem medir o que diz medir.
def test_caminho_legado_devolve_o_fallback(tmp_path: Path):
    """Sem `config_store`, a MESMA fixture não produz a alíquota do DB."""
    write_e5_config(tmp_path)
    analise = run_e3_e4_e5(
        tmp_path,
        e3_payloads=_e3_payload(),
        irpf_payloads={f"irpfdeclaracao_{_ANO_BASE_IRPF}": _irpf_com_renda_tributavel()},
    )
    assert _aliquota(analise) == _ALIQUOTA_DO_FALLBACK_LEGADO
    assert _motivo_economia(analise) is None


# =============================================================================
# A40.l64 — a FIAÇÃO da recusa chega ao payload E5
#
# Pós-flip do AC2026 (§Critério 3) nenhum ano do seed é incompleto, então a recusa
# não é mais observável por ano. Ela continua sendo o mecanismo que protege o ano
# em que uma norma nova entrar — e é o que a [[A40.l79]] depende. Por isso a row
# incompleta passa a ser SINTÉTICA: o teste mede a fiação
# `FiscalParameters → PrevidenciaConfig → payload`, não qual ano está incompleto.
# =============================================================================


def _previdencia(analise: dict) -> dict:
    return analise.get("previdencia_pgbl") or {}


def _store_com_regime_incompleto(ano: int):
    """Row sintética incompleta — independe de qual ano o seed marca."""
    from dataclasses import replace as _replace

    from pipeline.adapters.in_memory_config_store import InMemoryConfigStore

    base = fiscal_store_do_seed(ano).get_fiscal_for_period(date(ano, 1, 1), date(ano, 12, 31))
    incompleta = _replace(
        base, regime_completo=False, componentes_ausentes=("redutor_lei_15270", "irpfm")
    )
    return InMemoryConfigStore(fiscal_by_year={ano: incompleta})


def _analise_com_regime_incompleto(tmp_path: Path) -> dict:
    write_e5_config(tmp_path)
    return run_e3_e4_e5(
        tmp_path,
        e3_payloads=_e3_payload(),
        irpf_payloads={f"irpfdeclaracao_{_ANO_BASE_IRPF}": _irpf_com_renda_tributavel()},
        config_store=_store_com_regime_incompleto(date.today().year),
    )


def test_regime_incompleto_retem_a_economia_no_payload(tmp_path: Path):
    """Row incompleta ⇒ card publica capacidade e NÃO publica economia (ADR-375 D4)."""
    bloco = _previdencia(_analise_com_regime_incompleto(tmp_path))

    # Falsificável: sem o par, `economia is None` passaria por AUSÊNCIA de
    # capacidade — que é outro caminho e mediria a fixture, não a recusa.
    assert bloco.get("limite_pgbl_anual") is not None, "a capacidade do IRPF tem de sobreviver"
    assert bloco.get("economia_ir_anual") is None
    assert bloco.get("aporte_mensal") is None


def test_a_nota_nomeia_a_lei_que_falta_modelar(tmp_path: Path):
    """Motivo genérico não é motivo: a copy cita a norma e o ano-calendário."""
    nota = _previdencia(_analise_com_regime_incompleto(tmp_path)).get("nota") or ""

    assert "15.270" in nota
    assert str(date.today().year) in nota
