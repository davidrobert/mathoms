"""Tests — ``ConsumoConscienteCalculator`` (Sessão A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.consumo_consciente_calculator import (  # noqa: E402
    ConsumoConsciente,
    ConsumoConscienteCalculator,
    ConsumoConscienteConfig,
    GastoPontualItem,
)


def _fluxo(
    *,
    rec_rec_mensal: float = 20_000,
    desp_mensal: float = 15_000,
    n_meses: int = 12,
) -> dict:
    return {
        "janela_12m": {
            "receita_recorrente_mensal": rec_rec_mensal,
            "despesa_mensal_media": desp_mensal,
            "n_meses": n_meses,
        }
    }


def _despesas(**categorias_to_txns) -> dict:
    return {"dados": categorias_to_txns}


def _txn(
    data: str, descricao: str, valor: float, banco: str = "Itaú", tipo_conta: str = "extratoconta"
) -> dict:
    return {
        "data": data,
        "descricao": descricao,
        "valor": valor,
        "banco": banco,
        "tipo_conta": tipo_conta,
    }


# =============================================================================
# Config
# =============================================================================


class TestConfig:
    def test_defaults_consumo_min_2000(self):
        cfg = ConsumoConscienteConfig.from_configs()
        assert cfg.consumo_min == 2000.0

    def test_from_scoring_overrides_min(self):
        cfg = ConsumoConscienteConfig.from_configs(
            scoring={"thresholds_alertas": {"consumo_consciente_min": 5000}}
        )
        assert cfg.consumo_min == 5000.0

    def test_from_goals_overrides_aporte(self):
        cfg = ConsumoConscienteConfig.from_configs(
            goals={"aportes": {"meta_aporte_mensal": 10_000}}
        )
        assert cfg.aporte_mensal == 10_000.0

    def test_recurrent_categories_defaults(self):
        cfg = ConsumoConscienteConfig.from_configs()
        assert "moradia" in cfg.recurrent_categories
        assert "seguros" in cfg.recurrent_categories


# =============================================================================
# Filtro por threshold + categorias recorrentes
# =============================================================================


class TestFiltragem:
    def test_valor_abaixo_threshold_eh_excluido(self):
        cfg = ConsumoConscienteConfig(consumo_min=2000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-01-05", "Jantar", 500)]),
        )
        assert r.itens == ()

    def test_valor_acima_threshold_eh_incluido(self):
        cfg = ConsumoConscienteConfig(consumo_min=2000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-01-05", "Viagem", 5000)]),
        )
        assert len(r.itens) == 1
        assert r.itens[0].descricao == "Viagem"
        assert r.itens[0].valor == 5000

    def test_categoria_recorrente_eh_excluida(self):
        cfg = ConsumoConscienteConfig(consumo_min=2000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(
                moradia=[_txn("2026-01-05", "Aluguel", 5000)],  # recorrente → skip
                lazer=[_txn("2026-01-10", "Viagem", 5000)],  # aparece
            ),
        )
        assert len(r.itens) == 1
        assert r.itens[0].descricao == "Viagem"

    def test_non_list_transacoes_eh_ignorada(self):
        cfg = ConsumoConscienteConfig(consumo_min=100)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            {"dados": {"lazer": "not a list"}},
        )
        assert r.itens == ()


# =============================================================================
# Ordering (valor desc)
# =============================================================================


class TestOrdering:
    def test_itens_ordenados_por_valor_desc(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(
                lazer=[
                    _txn("2026-01-05", "Médio", 3000),
                    _txn("2026-01-10", "Grande", 10_000),
                    _txn("2026-01-15", "Pequeno", 1500),
                ]
            ),
        )
        valores = [i.valor for i in r.itens]
        assert valores == [10_000, 3000, 1500]


# =============================================================================
# Conta/cartão + mês
# =============================================================================


class TestContaCartao:
    def test_formata_banco_com_tipo_conta(self):
        cfg = ConsumoConscienteConfig(consumo_min=100)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(
                lazer=[_txn("2026-03-05", "X", 500, banco="Nubank", tipo_conta="faturacarbon")]
            ),
        )
        assert r.itens[0].conta_cartao == "Nubank (faturacarbon)"

    def test_banco_apenas_quando_sem_tipo_conta(self):
        cfg = ConsumoConscienteConfig(consumo_min=100)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-03-05", "X", 500, banco="Itaú", tipo_conta="")]),
        )
        assert r.itens[0].conta_cartao == "Itaú"

    def test_mes_derivado_de_data(self):
        cfg = ConsumoConscienteConfig(consumo_min=100)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-03-05", "X", 500)]),
        )
        assert r.itens[0].mes == "2026-03"


# =============================================================================
# Equivalente-meses-aporte
# =============================================================================


class TestEquivalenteAporte:
    def test_calculado_quando_aporte_configurado(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000, aporte_mensal=5000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-01-05", "X", 15_000)]),
        )
        # 15k / 5k = 3.0
        assert r.equivalente_meses_aporte == 3.0

    def test_zero_quando_sem_aporte(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000, aporte_mensal=0)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-01-05", "X", 5000)]),
        )
        assert r.equivalente_meses_aporte == 0.0


# =============================================================================
# Folga / teto sugerido
# =============================================================================


class TestFolgaETeto:
    def test_folga_positiva_com_receita_maior(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        # receita 20k, despesa total 15k → folga positiva.
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(rec_rec_mensal=20_000, desp_mensal=15_000),
            _despesas(),  # sem pontuais
        )
        assert r.folga_mensal == 5_000.0
        assert r.folga_pct == 25.0

    def test_teto_sugerido_eh_115pct_das_recorrentes(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(desp_mensal=10_000),
            _despesas(),
        )
        # Despesas 10k, sem pontuais → recorrentes = 10k → teto = 11500
        assert r.teto_sugerido == pytest.approx(11_500.0)

    def test_folga_zero_quando_receita_zero(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(rec_rec_mensal=0, desp_mensal=5_000),
            _despesas(),
        )
        assert r.folga_pct == 0.0


# =============================================================================
# Janela fallback
# =============================================================================


class TestJanela:
    def test_pontuais_fora_da_janela_nao_entram_na_folga(self):
        """ADR-306 §D6 — pontuais full-period diluídos no denominador 12m inflavam a folga."""
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        fluxo = {
            "janela_12m": {
                "receita_recorrente_mensal": 10_000,
                "despesa_mensal_media": 8_000,
                "n_meses": 12,
                "periodo": "2025-07 a 2026-06",
            }
        }
        despesas = _despesas(
            lazer=[_txn("2024-01-05", "ANTIGO", 6_000), _txn("2026-01-05", "RECENTE", 2_400)]
        )
        r = ConsumoConscienteCalculator(cfg).calculate(fluxo, despesas)
        assert r.total_pontuais == 8_400.0
        assert r.total_pontuais_janela == 2_400.0
        assert r.folga_mensal == pytest.approx(10_000 - (8_000 - 2_400 / 12))
        assert r.janela == "12m"
        assert r.janela_meses == 12

    def test_folga_reconciliavel_com_base_canonica(self):
        """folga == receita_rec_mensal − despesa_mensal_media + pontuais_janela/n."""
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        fluxo = {
            "janela_12m": {
                "receita_recorrente_mensal": 12_000,
                "despesa_mensal_media": 9_000,
                "n_meses": 12,
                "periodo": "2025-07 a 2026-06",
            }
        }
        r = ConsumoConscienteCalculator(cfg).calculate(
            fluxo, _despesas(lazer=[_txn("2025-12-10", "VIAGEM", 3_600)])
        )
        esperado = 12_000 - 9_000 + r.total_pontuais_janela / 12
        assert r.folga_mensal == pytest.approx(esperado)

    def test_fallback_ao_periodo_completo_sem_janela(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000)
        fluxo = {
            "receita_recorrente_mensal": 10_000,
            "despesa_mensal_media": 8_000,
            "num_months": 6,
        }
        r = ConsumoConscienteCalculator(cfg).calculate(fluxo, _despesas())
        # Folga = 10k - 8k = 2k
        assert r.folga_mensal == 2_000.0


# =============================================================================
# Análise textual
# =============================================================================


class TestAnalise:
    def test_texto_quando_ha_itens(self):
        cfg = ConsumoConscienteConfig(consumo_min=1000, aporte_mensal=5000)
        r = ConsumoConscienteCalculator(cfg).calculate(
            _fluxo(),
            _despesas(lazer=[_txn("2026-01-05", "X", 5_000)]),
        )
        assert "Identificados 1 gastos" in r.analise
        assert "1.0 meses" in r.analise

    def test_texto_quando_sem_itens(self):
        r = ConsumoConscienteCalculator().calculate(_fluxo(), _despesas())
        assert "Nenhum gasto pontual" in r.analise


# =============================================================================
# Result type
# =============================================================================


class TestResult:
    def test_result_is_frozen(self):
        r = ConsumoConscienteCalculator().calculate(_fluxo(), _despesas())
        assert isinstance(r, ConsumoConsciente)

    def test_legacy_dict_has_all_fields(self):
        r = ConsumoConscienteCalculator().calculate(_fluxo(), _despesas())
        d = r.to_legacy_dict()

        required = {
            "itens",
            "total_pontuais",
            "equivalente_meses_aporte",
            "folga_mensal",
            "folga_pct",
            "teto_sugerido",
            "analise",
        }
        assert required.issubset(d.keys())

    def test_item_to_dict_has_all_fields(self):
        item = GastoPontualItem(
            descricao="X",
            conta_cartao="Y",
            data="2026-01-01",
            mes="2026-01",
            valor=1000,
            categoria="lazer",
        )
        d = item.to_dict()
        assert {
            "descricao",
            "conta_cartao",
            "data",
            "mes",
            "valor",
            "categoria",
            "observacao",
        }.issubset(d.keys())
