"""Tests — ``E5AnalyzerAdapter`` (Sessão A5c)."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402
from pipeline.domain.services.e5_analyzer_adapter import (  # noqa: E402
    E5AnalysisResult,
    E5AnalyzerAdapter,
)

_DAVID_DOB = date(1985, 6, 15)


def _seed_apolice_auto_vigente(store: InMemoryArtifactStore) -> None:
    """Apólice sintética PII-zero vigente hoje (A28.l6)."""
    hoje = date.today()
    store.seed(
        "extract_comprovantes_bens",
        "apolice_auto_2026",
        {
            "apolice_numero": "AUTO-1",
            "seguradora": "seguradora-sintetica",
            "vigencia_inicio": (hoje - timedelta(days=30)).isoformat(),
            "vigencia_fim": (hoje + timedelta(days=300)).isoformat(),
            "premio_total_brl": "1500.00",
            "bens_segurados": [{"tipo": "veiculo", "coberturas": []}],
        },
    )


def _seed_minimal(store: InMemoryArtifactStore) -> None:
    store.seed(
        "E4",
        "receitas",
        {
            "total_geral": 120_000,
            "totais_por_categoria": {"receita_clt": 120_000},
            "dados": {
                "receita_clt": [{"data": "2026-01-05", "descricao": "SALARIO", "valor": 10_000}]
            },
            "periodo": "2026-01 a 2026-12",
        },
    )
    store.seed(
        "E4",
        "despesas",
        {
            "total_geral": 60_000,
            "totais_por_categoria": {"mercado": 40_000, "uber": 20_000},
            "dados": {
                "mercado": [{"data": "2026-01-10", "descricao": "MERCADO", "valor": 5000}],
                "uber": [{"data": "2026-01-15", "descricao": "UBER", "valor": 3000}],
            },
        },
    )
    store.seed(
        "E4",
        "fluxo_mensal_detalhado",
        {
            "meses_ordenados": [f"2026-{m:02d}" for m in range(1, 13)],
            "receitas": {
                "por_mes": {
                    f"2026-{m:02d}": {"Empregador A": 10_000, "_total": 10_000}
                    for m in range(1, 13)
                }
            },
            "despesas": {
                "por_mes": {
                    f"2026-{m:02d}": {"mercado": 3_333, "uber": 1_667, "_total": 5_000}
                    for m in range(1, 13)
                }
            },
        },
    )
    store.seed(
        "E4",
        "patrimonio",
        {
            "pipeline_stage": "E1.5",
            "patrimonio_por_ano": {"2024": {"total_bens": 1_500_000, "total_dividas": 200_000}},
            "membros": ["David", "Mariana"],
            "imoveis_consolidados": [
                {"descricao": "Casa Vila Madalena", "valores_31_12": {"2024": 800_000}},
            ],
            "dividas": [
                {"proprietario": "david", "saldo_31_12": {"2024": 200_000}},
            ],
        },
    )
    store.seed(
        "E4",
        "investimentos",
        {
            "total_geral": 500_000,
            "n_posicoes": 3,
            "total_por_membro": {"david": 300_000, "mariana": 200_000},
            "dados": [],
        },
    )


class TestAdapterConstruction:
    def test_from_configs_with_titular_dob_enables_if_projector(self):
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )
        # IFProjector deve estar habilitado.
        assert adapter._if_projector is not None

    def test_from_configs_without_titular_dob_disables_if_and_cenarios(self):
        adapter = E5AnalyzerAdapter.from_configs()
        assert adapter._if_projector is None
        assert adapter._cenarios is None

    def test_from_configs_without_goals_keeps_if_disabled(self):
        adapter = E5AnalyzerAdapter.from_configs(titular_dob=_DAVID_DOB)
        assert adapter._if_projector is None  # sem goals.if_meta

    def test_defaults_all_other_services(self):
        adapter = E5AnalyzerAdapter()
        # Todos os services defaults devem estar presentes.
        assert adapter._ratios is not None
        assert adapter._orcamento is not None
        assert adapter._endividamento is not None
        assert adapter._previdencia is not None
        assert adapter._inv_classes is not None
        assert adapter._consumo is not None
        assert adapter._equilibrio is not None
        assert adapter._diagnostico is not None
        assert adapter._pontos_fortes is not None
        assert adapter._pontos_urgentes is not None

    def test_from_configs_propagates_property_classification_overrides(self):
        # ADR-215 P3 (fix de conexão): overrides DB-first chegam ao
        # `PatrimonioConfig` via `from_configs(property_classification_overrides=...)`.
        # Sem esta propagação, o split lazy em `PatrimonioCalculator._split_imoveis`
        # ignora a classificação user-driven gravada pelo endpoint P4 / UI P5.
        overrides = {
            "prop-abc": "residencia_principal",
            "prop-def": "uso_pessoal",
        }
        adapter = E5AnalyzerAdapter.from_configs(
            property_classification_overrides=overrides,
        )
        assert adapter._patrimonio._config.property_classification_overrides == overrides

    def test_from_configs_default_overrides_empty_dict(self):
        # Sem `property_classification_overrides` (CLI legado / teste isolado),
        # field default é dict vazio — calculator cai no fallback keyword.
        adapter = E5AnalyzerAdapter.from_configs()
        assert adapter._patrimonio._config.property_classification_overrides == {}


class TestAnalyzeViaStore:
    def test_minimal_store_returns_result(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )

        result = adapter.analyze_via_store(store)

        assert isinstance(result, E5AnalysisResult)
        assert result.members is not None
        assert result.fluxo_enriched is not None
        assert result.ratios is not None

    def test_if_projection_populated_when_configured(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter.from_configs(
            goals={"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 4.0}},
            titular_dob=_DAVID_DOB,
        )

        result = adapter.analyze_via_store(store)

        assert result.if_projection is not None
        assert result.if_projection.if_meta == 5_000_000

    def test_if_projection_none_without_config(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()  # sem configs

        result = adapter.analyze_via_store(store)

        assert result.if_projection is None

    def test_ratios_uses_12m_window(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 12m janela com 12 meses.
        assert result.ratios.janela_n_meses == 12
        # Receita 120k, despesa 60k → taxa total = 50%
        assert result.ratios.taxa_poupanca_total_pct == pytest.approx(50.0)

    def test_orcamento_divide_by_num_months(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 60k / 12 = 5k total mensal
        assert result.orcamento.total == pytest.approx(5_000.0)

    def test_endividamento_computa_percentual(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # 200k dividas / 1.5M bruto = 13.33%
        assert result.endividamento.percentual_patrimonio == pytest.approx(13.33, rel=1e-2)

    def test_previdencia_nd_when_sem_receita_pj(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # por_fonte: {"receita_clt": 120_000} — sem PJ.
        assert result.previdencia.status == "N/D"

    def test_consumo_consciente_sem_pontuais(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Valores R$3000-5000 abaixo do threshold default R$2000? ON: R$5000 ≥ 2000
        # Ah, MERCADO R$5000 ≥ R$2000 → é pontual.
        # Mas "mercado" NÃO está em RECURRENT_CATEGORIES default.
        # Moradia é. Mercado está em RECURRENT_CATEGORIES? Não — "moradia" sim.
        # Então mercado R$5000 é pontual.
        # Pelo menos um item.
        assert len(result.consumo_consciente.itens) >= 1

    def test_diagnostico_comportamental_populated(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Sempre retorna ao menos 1 (fallback ou real).
        assert len(result.diagnosticos) >= 1

    def test_pontos_urgentes_inclui_seguro(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        acoes = {p.acao for p in result.pontos_urgentes}
        assert "Contratar seguro de vida e invalidez" in acoes

    def test_protecao_patrimonial_sempre_presente(self):
        """A28.l6 (ADR-240 D8): payload sempre presente — sem apólice = G6-b."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        assert result.protecao_patrimonial is not None
        assert result.protecao_patrimonial["apolices_vigentes"] == []

    def test_apolice_vigente_flui_do_store_para_protecao(self):
        """A28.l6: apólice de ``extract_comprovantes_bens`` chega ao E5 e
        condiciona o item de seguro em pontos_urgentes (copy diferenciada)."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        _seed_apolice_auto_vigente(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        assert len(result.protecao_patrimonial["apolices_vigentes"]) == 1
        seguro = [
            p for p in result.pontos_urgentes if p.acao == "Contratar seguro de vida e invalidez"
        ]
        assert len(seguro) == 1
        assert "nenhuma apólice identificada" not in seguro[0].impacto

    def test_equilibrio_cerbasi_computed(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        assert result.equilibrio_cerbasi.pct_presente > 0

    def test_empty_store_returns_defaulted_result(self):
        store = InMemoryArtifactStore()
        adapter = E5AnalyzerAdapter()

        result = adapter.analyze_via_store(store)

        # Todos os valores zerados mas sem exceção.
        assert result.fluxo_enriched.receita_total == 0
        assert result.ratios.taxa_poupanca_recorrente_pct == 0


class TestMoedaEstrangeiraFallback:
    """ADR-245 — fallback baseline IRPF para `caixa_moeda_estrangeira`."""

    def test_extract_me_caixa_picks_usd_deposit(self):
        from pipeline.domain.services.e5_analyzer_adapter import _extract_me_caixa_from_baseline

        baseline = {
            "investimentos_consolidados": [
                {
                    "descricao": "DEPOSITO EM MOEDA NACIONAL DECORRENTE DE MOEDA ESTRANGEIRA - U$ 6.524,00",
                    "valores_31_12": {"2025": 34433.67},
                    "proprietario": "david_robert",
                },
                {
                    "descricao": "DEPOSITO EM MOEDA ESTRANGEIRA DOLAR (PAIS: ILHAS CAYMAN)",
                    "valores_31_12": {"2025": 484.80},
                    "proprietario": "david_robert",
                },
                {
                    "descricao": "BANCO ITAU - APLICACAO RENDA FIXA RDB/CDB",
                    "valores_31_12": {"2025": 151602.49},
                    "proprietario": "david_robert",
                },
            ]
        }

        total, detalhes = _extract_me_caixa_from_baseline(baseline)

        assert total == pytest.approx(34918.47, abs=0.01)
        assert len(detalhes) == 2
        assert all(d.tipo == "moeda_estrangeira_irpf" for d in detalhes)
        assert all(d.moeda == "USD" for d in detalhes)

    def test_extract_me_caixa_handles_eur(self):
        from pipeline.domain.services.e5_analyzer_adapter import _extract_me_caixa_from_baseline

        baseline = {
            "investimentos_consolidados": [
                {
                    "descricao": "DEPOSITO EM MOEDA ESTRANGEIRA EURO",
                    "valores_31_12": {"2024": 5000.0},
                }
            ]
        }
        total, detalhes = _extract_me_caixa_from_baseline(baseline)
        assert total == 5000.0
        assert detalhes[0].moeda == "EUR"

    def test_extract_me_caixa_skips_non_me_items(self):
        from pipeline.domain.services.e5_analyzer_adapter import _extract_me_caixa_from_baseline

        baseline = {
            "investimentos_consolidados": [
                {"descricao": "CDB Itau", "valores_31_12": {"2025": 100000}},
                {"descricao": "Acoes PETR4", "valores_31_12": {"2025": 50000}},
            ]
        }
        total, detalhes = _extract_me_caixa_from_baseline(baseline)
        assert total == 0
        assert detalhes == []

    def test_extract_me_caixa_skips_zero_values(self):
        from pipeline.domain.services.e5_analyzer_adapter import _extract_me_caixa_from_baseline

        baseline = {
            "investimentos_consolidados": [
                {
                    "descricao": "DEPOSITO MOEDA ESTRANGEIRA DOLAR (zerado)",
                    "valores_31_12": {"2025": 0.0},
                }
            ]
        }
        total, detalhes = _extract_me_caixa_from_baseline(baseline)
        assert total == 0
        assert detalhes == []

    def test_load_caixa_fallback_kicks_in_when_no_foreign_in_e3(self):
        """E2-llm Itaú só trouxe E3 BRL (informe não tem extrato bancário).
        Sem fallback ME, card 'Caixa e Moeda Estrangeira' fica zerado mesmo
        com USD em baseline IRPF.
        """
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "itau_extratoconta_BRL_202512_202512",
            {
                "banco": "itau",
                "tipo_conta": "extrato",
                "moeda": "BRL",
                "saldo_final": 1000.0,
                "periodo_cobertura": {"inicio": "2025-12-01", "fim": "2025-12-31"},
                "transacoes": [{"data": "2025-12-31", "valor": 100, "descricao": "TED"}],
            },
        )
        adapter = E5AnalyzerAdapter()
        baseline = {
            "investimentos_consolidados": [
                {
                    "descricao": "DEPOSITO EM MOEDA NACIONAL DECORRENTE DE MOEDA ESTRANGEIRA - U$ 6.524,00",
                    "valores_31_12": {"2025": 34433.67},
                }
            ]
        }

        total, detalhes = adapter._load_caixa_from_e3(store, baseline=baseline)

        assert total == pytest.approx(35433.67, abs=0.01)  # 1000 BRL + 34433.67 IRPF
        assert any(d.tipo == "moeda_estrangeira_irpf" for d in detalhes)
        assert any(d.tipo == "caixa" for d in detalhes)

    def test_load_caixa_no_fallback_when_e3_has_foreign(self):
        """E3 tem extrato USD reconciliado → fallback IRPF NÃO dispara."""
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "c6_extratocontaglobalusd_USD_202512_202512",
            {
                "banco": "c6bank",
                "tipo_conta": "extratoconta",
                "moeda": "USD",
                "saldo_final": 1000.0,
                "periodo_cobertura": {"inicio": "2025-12-01", "fim": "2025-12-31"},
                "transacoes": [{"data": "2025-12-15", "valor": 100, "descricao": "PIX"}],
            },
        )
        adapter = E5AnalyzerAdapter()
        baseline = {
            "investimentos_consolidados": [
                {
                    "descricao": "DEPOSITO EM MOEDA ESTRANGEIRA DOLAR",
                    "valores_31_12": {"2025": 99999.0},
                }
            ]
        }

        total, detalhes = adapter._load_caixa_from_e3(store, baseline=baseline)

        # Apenas o E3 USD entra; baseline IRPF não aplica fallback.
        assert all(d.tipo != "moeda_estrangeira_irpf" for d in detalhes)
        assert total < 99000.0  # bem menor que o IRPF


class TestResultType:
    def test_result_is_frozen(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        result = adapter.analyze_via_store(store)

        # Frozen dataclass — não permite atribuição.
        with pytest.raises(Exception):
            result.receitas = {}  # type: ignore[misc]


class TestA6d33Wiring:
    """Testes das integrações A6d.3.3 (sem placeholders)."""

    def test_patrimonio_full_has_full_fidelity_keys(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        result = adapter.analyze_via_store(store)

        # Todas as chaves do legado ``analyze_patrimonio`` devem aparecer.
        required = {
            "bruto",
            "dividas",
            "liquido",
            "residencia",
            "imoveis_investimento",
            "caixa_moeda_estrangeira",
            "caixa_detalhes",
            "investivel_financeiro",
            "investivel_efetivo",
            "veiculos",
            "composicao",
            "tabela_categorias",
            "fonte_investimentos",
            "investimentos_david",
            "investimentos_mariana",
        }
        assert required.issubset(result.patrimonio_full.keys())

    def test_reserva_has_paridade_keys(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        result = adapter.analyze_via_store(store)

        required = {
            "despesas_mensais",
            "nivel_6_meses",
            "nivel_12_meses",
            "composicao_liquida",
            "total_liquida",
            "cobertura_meses",
            "avaliacao_liquidity",
            "niveis",
        }
        assert required.issubset(result.reserva.keys())

    def test_score_has_paridade_keys(self):
        # ADR-217 D3 acrescenta `score_version` ao shape v2.E.7 do ScoreCard.
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        result = adapter.analyze_via_store(store)
        expected = {
            "valor",
            "max",
            "classificacao",
            "score_version",
            "componentes",
            "breakdown",
            "formula",
            "context",
            "conclusion",
        }
        assert set(result.score.keys()) == expected
        assert result.score["max"] == 10
        assert len(result.score["componentes"]) == 5

    def test_no_placeholders_in_adapter(self):
        """Garantia estrutural: nenhuma string 'placeholder' no módulo."""
        from pathlib import Path

        src = Path("pipeline/domain/services/e5_analyzer_adapter.py").read_text()
        # Menção em comentário é OK (evidência histórica); identificadores não.
        assert "_placeholder" not in src
        assert "score_placeholder" not in src
        assert "reserva_placeholder" not in src

    def test_load_caixa_from_e3_returns_zero_when_no_keys(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        adapter = E5AnalyzerAdapter()
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 0.0
        assert detalhes == []

    def test_load_caixa_from_e3_sums_brl_cc(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed(
            "E3",
            "bradesco_cc_BRL_202601_202612",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bradesco",
                "moeda": "BRL",
                "saldo_final": 5000.0,
            },
        )
        adapter = E5AnalyzerAdapter()
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 5000.0
        assert len(detalhes) == 1
        assert detalhes[0].tipo == "caixa"
        assert detalhes[0].moeda == "BRL"

    def test_load_caixa_from_e3_converts_usd_via_taxas(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed(
            "E3",
            "bofa_cc_USD_202601_202612",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter(taxas={"cambio_usd_brl": 5.50})
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 5500.0
        assert detalhes[0].tipo == "moeda_estrangeira"
        assert detalhes[0].moeda == "USD"

    def test_load_caixa_skips_fatura_poupanca_pj(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed("E3", "itau_fatura", {"tipo_conta": "fatura", "saldo_final": 999})
        store.seed("E3", "itau_poupanca", {"tipo_conta": "poupanca", "saldo_final": 999})
        store.seed("E3", "itau_pj", {"tipo_conta": "pj_corrente", "saldo_final": 999})
        adapter = E5AnalyzerAdapter()
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 0.0

    def test_load_caixa_skips_investment_banks(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed(
            "E3",
            "btg",
            {
                "tipo_conta": "cc",
                "banco": "BTG Pactual",
                "moeda": "BRL",
                "saldo_final": 999,
            },
        )
        adapter = E5AnalyzerAdapter()
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 0.0

    def test_load_caixa_skips_unknown_saldo(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed(
            "E3",
            "unknown",
            {
                "tipo_conta": "cc",
                "banco": "Bradesco",
                "moeda": "BRL",
                "saldo_final": None,
                "saldo_final_unknown": True,
            },
        )
        adapter = E5AnalyzerAdapter()
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 0.0

    def test_load_caixa_dedupes_multiple_periods_same_account(self):
        """Vários extratos da mesma conta (períodos diferentes) não são somados —
        prevalece o saldo do período com ``periodo_cobertura.fim`` mais recente."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        for per_fim, saldo in (
            ("2024-03-31", 22120.66),
            ("2025-01-31", 80629.65),
            ("2026-04-15", 847.26),
            ("2024-10-31", 149551.72),
        ):
            store.seed(
                "E3",
                f"itau_extratoconta_BRL_{per_fim.replace('-', '')}",
                {
                    "tipo_conta": "extratoconta",
                    "banco": "Itaú",
                    "moeda": "BRL",
                    "saldo_final": saldo,
                    "periodo_cobertura": {"inicio": "2024-01-01", "fim": per_fim},
                },
            )
        adapter = E5AnalyzerAdapter()
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 847.26
        assert len(detalhes) == 1
        assert detalhes[0].saldo_original == 847.26

    def test_load_caixa_keeps_distinct_accounts(self):
        """Contas distintas (banco ou titular diferente) não são deduplicadas."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        store.seed(
            "E3",
            "itau_david_202604",
            {
                "tipo_conta": "extratoconta",
                "banco": "Itaú",
                "moeda": "BRL",
                "titular": "David",
                "saldo_final": 1000.0,
                "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-04-15"},
            },
        )
        store.seed(
            "E3",
            "itau_mariana_202604",
            {
                "tipo_conta": "extratoconta",
                "banco": "Itaú",
                "moeda": "BRL",
                "titular": "Mariana",
                "saldo_final": 2500.0,
                "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-04-15"},
            },
        )
        store.seed(
            "E3",
            "santander_david_202604",
            {
                "tipo_conta": "extratoconta",
                "banco": "Santander",
                "moeda": "BRL",
                "titular": "David",
                "saldo_final": 500.0,
                "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-04-15"},
            },
        )
        adapter = E5AnalyzerAdapter()
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 4000.0
        assert len(detalhes) == 3

    def test_identity_from_family_with_nome_curto(self):
        """``from_configs`` extrai nome_curto do family config."""
        family = {
            "titular": "carlos",
            "membros": {
                "carlos": {"nome_curto": "Carlão"},
                "ana": {"papel": "conjuge", "nome_curto": "Aninha"},
            },
        }
        adapter = E5AnalyzerAdapter.from_configs(family=family)
        assert adapter._identity.titular_nome == "Carlão"
        assert adapter._identity.conjuge_nome == "Aninha"
        assert adapter._identity.titular_key == "carlos"
        assert adapter._identity.conjuge_key == "ana"

    def test_residencia_property_ids_extracted_from_overrides(self):
        """ADR-215 §1 sunset: subset `residencia_principal` é extraído de
        `property_classification_overrides` e propagado para analyzers
        downstream (`classes`, `top_ativos`, `instituicoes`)."""
        adapter = E5AnalyzerAdapter.from_configs(
            property_classification_overrides={
                "prop-residencia": "residencia_principal",
                "prop-locado": "locado",
            }
        )
        assert adapter._inv_classes._config.residencia_property_ids == frozenset(
            {"prop-residencia"}
        )
        assert adapter._top_ativos._config.classes_config.residencia_property_ids == frozenset(
            {"prop-residencia"}
        )
        assert adapter._instituicoes._config.classes_config.residencia_property_ids == frozenset(
            {"prop-residencia"}
        )

    def test_investment_banks_from_institutions(self):
        institutions = {"investment_banks": ["Custom Broker", "Another Bank"]}
        adapter = E5AnalyzerAdapter.from_configs(institutions=institutions)
        assert "custom broker" in adapter._investment_banks
        assert "another bank" in adapter._investment_banks

    def test_investment_banks_default_when_institutions_empty(self):
        adapter = E5AnalyzerAdapter.from_configs()
        assert "btg pactual" in adapter._investment_banks


class TestA75TypedCambio:
    """A7.5 — ``cambio_usd_brl``/``cambio_eur_brl`` typed têm prioridade sobre ``taxas`` dict."""

    def test_typed_usd_overrides_taxas_dict(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "bofa_cc_USD",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter(
            taxas={"cambio_usd_brl": 5.50},  # legacy
            cambio_usd_brl=Decimal("6.00"),  # typed prioritário
        )
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 6000.0  # 1000 * 6.00 (typed), não 5500 (taxas)
        assert detalhes[0].valor_brl == 6000.0

    def test_typed_eur_overrides_taxas_dict(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "wise_cc_EUR",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Wise",
                "moeda": "EUR",
                "saldo_final": 500.0,
            },
        )
        adapter = E5AnalyzerAdapter(
            taxas={"cambio_eur_brl": 6.00},
            cambio_eur_brl=Decimal("7.00"),
        )
        total, detalhes = adapter._load_caixa_from_e3(store)
        assert total == 3500.0  # 500 * 7.00 (typed), não 3000 (taxas)
        assert detalhes[0].valor_brl == 3500.0

    def test_taxas_dict_used_when_typed_none(self):
        """Backward compat: sem typed, lê do dict legacy."""
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "bofa_cc_USD",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter(taxas={"cambio_usd_brl": 5.50})
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 5500.0

    def test_default_cambio_when_neither_typed_nor_dict(self):
        """Sem typed nem dict, usa default 5.80/6.35."""
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "bofa_cc_USD",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter()
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 5800.0  # 1000 * 5.80 default

    def test_typed_cambio_accepts_float(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "bofa_cc_USD",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter(cambio_usd_brl=5.75)
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 5750.0

    def test_from_configs_propagates_typed_cambio(self):
        """``from_configs`` propaga ``cambio_usd_brl`` e ``cambio_eur_brl`` para o adapter."""
        adapter = E5AnalyzerAdapter.from_configs(
            cambio_usd_brl=Decimal("6.10"),
            cambio_eur_brl=Decimal("7.20"),
        )
        assert adapter._cambio_usd_brl == 6.10
        assert adapter._cambio_eur_brl == 7.20

    def test_from_configs_typed_cambio_overrides_taxas_dict_in_caixa(self):
        store = InMemoryArtifactStore()
        store.seed(
            "E3",
            "bofa_cc_USD",
            {
                "tipo_conta": "conta_corrente",
                "banco": "Bank of America",
                "moeda": "USD",
                "saldo_final": 1000.0,
            },
        )
        adapter = E5AnalyzerAdapter.from_configs(
            taxas={"cambio_usd_brl": 5.0},
            cambio_usd_brl=Decimal("6.50"),
        )
        total, _ = adapter._load_caixa_from_e3(store)
        assert total == 6500.0


# ─────────────────────────────────────────────────────────────────────
# A8.3 PR-C — IRPF + PassiveIncomeCalculator wire
# ─────────────────────────────────────────────────────────────────────


_IRPF_CONTRIB = {
    "cpf_masked": "***.***.***-99",
    "nome": "David",
    "modelo": "completo",
    "natureza": "titular",
}
_IRPF_IMPOSTO = {
    "base_calculo_brl": "0",
    "ir_devido_brl": "0",
    "deducoes_totais_brl": "0",
    "ir_pago_brl": "0",
}
_IRPF_ISENTO_DIV_12K = {
    "codigo_rfb": "09",
    "descricao": "Lucros e dividendos",
    "valor_brl": "12000.00",
}


def _irpf_payload(ano_base: int) -> dict:
    return {
        "contribuinte": {**_IRPF_CONTRIB, "ano_base": ano_base, "exercicio": ano_base + 1},
        "rendimentos_pj": [],
        "rendimentos_pf": [],
        "rendimentos_exterior": [],
        "rendimentos_isentos": [_IRPF_ISENTO_DIV_12K],
        "rendimentos_tributacao_exclusiva": [],
        "pagamentos_efetuados": [],
        "bens_e_direitos": [],
        "dividas_e_onus": [],
        "doacoes_efetuadas": [],
        "espolio": [],
        "dependentes": [],
        "imposto_apurado": _IRPF_IMPOSTO,
        "confidence": 0.95,
    }


def _seed_irpf_full(store: InMemoryArtifactStore, *, ano_base: int = 2024) -> None:
    """Seed payload mínimo de extract_irpf_full com cod 09 (dividendos R$ 12k)."""
    store.seed("extract_irpf_full", f"david_{ano_base}-1.6_irpf_full", _irpf_payload(ano_base))


_GOALS_TRS_5 = {"independencia_financeira": {"if_meta": 5_000_000, "trs_pct": 5.0}}


def _adapter_a83(reference_date: date | None = None) -> E5AnalyzerAdapter:
    """Adapter padrão para os testes A8.3 (David titular, TRS 5%)."""
    return E5AnalyzerAdapter.from_configs(
        goals=_GOALS_TRS_5,
        titular_dob=_DAVID_DOB,
        reference_date=reference_date,
    )


class TestPassiveIncomeWiring:
    """Item 3 da Lane A8.3 PR-C — adapter integra IRPF + PassiveIncomeCalculator."""

    def test_passive_income_status_ok_when_irpf_present(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        _seed_irpf_full(store, ano_base=2024)

        result = _adapter_a83(date(2025, 6, 1)).analyze_via_store(store)

        assert result.passive_income is not None
        assert result.passive_income.status == "ok"
        assert result.passive_income.ano_referencia_irpf == 2024
        assert result.passive_income.renda_passiva_anual_brl == Decimal("12000.00")
        assert result.passive_income.trs_efetiva_pct > Decimal("0")

    def test_passive_income_status_sem_irpf_when_no_artifact(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)

        result = _adapter_a83().analyze_via_store(store)

        assert result.passive_income is not None
        assert result.passive_income.status == "sem_irpf"
        assert result.passive_income.renda_passiva_anual_brl == Decimal("0")
        assert result.passive_income.trs_efetiva_pct == Decimal("0")

    def test_acumuladores_pct_high_when_holdings_match(self):
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        _seed_irpf_full(store, ano_base=2024)
        store.seed("E4", "investimentos", _ivvb11_holdings_300k())

        result = _adapter_a83(date(2025, 6, 1)).analyze_via_store(store)

        assert result.passive_income is not None
        assert result.passive_income.status == "ok"
        # IVVB11 é detectado como acumulador — pct > 0 mostra heurística viva.
        assert result.passive_income.acumuladores_pct_gerador > Decimal("0")

    def test_ratios_rentabilidade_populated_when_passive_income_ok(self):
        """Item 4 sanity: ratios.rentabilidade_pct sai do placeholder 'N/D'."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)
        _seed_irpf_full(store, ano_base=2024)

        result = _adapter_a83(date(2025, 6, 1)).analyze_via_store(store)

        assert result.ratios.rentabilidade_pct is not None
        assert result.ratios.to_legacy_dict()["rentabilidade_pct"] != "N/D"

    def test_ratios_rentabilidade_nd_when_no_irpf(self):
        """Sem IRPF → rentabilidade volta a 'N/D' no legacy dict (back-compat)."""
        store = InMemoryArtifactStore()
        _seed_minimal(store)

        result = _adapter_a83().analyze_via_store(store)

        assert result.ratios.to_legacy_dict()["rentabilidade_pct"] == "N/D"


def _ivvb11_holdings_300k() -> dict:
    return {
        "total_geral": 500_000,
        "n_posicoes": 1,
        "total_por_membro": {"david": 500_000, "mariana": 0},
        "dados": [{"nome": "IVVB11", "tipo": "etf", "valor_atual": 300_000.0}],
    }
