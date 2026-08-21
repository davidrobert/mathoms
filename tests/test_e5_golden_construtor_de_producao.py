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
    """Aceite da lane: ≥1 execução golden passa por `from_fiscal_parameters`."""
    assert _motivo_economia(analise_com_config_store) == _MOTIVO_SO_DO_CAMINHO_DB
    assert "15.270" in _previdencia(analise_com_config_store)["nota"]


def test_a_aliquota_publicada_nao_e_a_do_fallback(analise_com_config_store):
    """Sem esta asserção, o teste acima passaria com o caminho legado."""
    assert _aliquota(analise_com_config_store) != _ALIQUOTA_DO_FALLBACK_LEGADO
    # Bicondicional da ADR-402: retida a economia, a marginal sai junto.
    assert _aliquota(analise_com_config_store) is None
    assert _previdencia(analise_com_config_store)["economia_ir_anual"] is None
    # Reter prescrição não apaga fato: o espaço de 12% do IRPF continua publicado.
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
# A40.l64 — a recusa do regime incompleto chega ao payload E5
#
# O unit test do analyzer prova a regra; este prova a FIAÇÃO. A row que
# `fiscal_store_do_seed` semeia vem da migration ADR-389, onde AC2026 nasce
# `regime_completo=False` — e esta fixture roda com `date.today().year`.
# Sem esta asserção, o wiring `FiscalParameters → PrevidenciaConfig` poderia
# voltar a descartar o marcador e nenhum golden ficaria vermelho.
# =============================================================================


def _previdencia(analise: dict) -> dict:
    return analise.get("previdencia_pgbl") or {}


@pytest.mark.skipif(
    date.today().year < 2026,
    reason="a row incompleta é AC2026+; antes disso não há o que recusar",
)
def test_regime_incompleto_retem_a_economia_no_payload(analise_com_config_store):
    """AC2026 publica capacidade e NÃO publica economia (ADR-375 D4 · A40.l64)."""
    bloco = _previdencia(analise_com_config_store)

    # Falsificável: sem o par, `economia is None` passaria por AUSÊNCIA de
    # capacidade — que é outro caminho (`_sem_capacidade_declarada`) e mediria
    # a fixture, não a recusa.
    assert bloco.get("limite_pgbl_anual") is not None, "a capacidade do IRPF tem de sobreviver"
    assert bloco.get("economia_ir_anual") is None
    assert bloco.get("aporte_mensal") is None


@pytest.mark.skipif(date.today().year < 2026, reason="ver acima")
def test_a_nota_nomeia_a_lei_que_falta_modelar(analise_com_config_store):
    """Motivo genérico não é motivo: a copy cita a norma e o ano-calendário."""
    nota = _previdencia(analise_com_config_store).get("nota") or ""

    assert "15.270" in nota
    assert str(date.today().year) in nota
