"""Tests — ``PrevidenciaAnalyzer`` (Sessão A5b)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from decimal import Decimal  # noqa: E402

from pipeline.domain.services.previdencia_analyzer import (  # noqa: E402
    CapacidadePgblIRPF,
    IRPFBracket,
    PrevidenciaAnalysis,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)


def _fluxo(pj: float = 0, num_months: int = 12) -> dict:
    return {
        "por_fonte": {"receita_pj": pj},
        "receita_despesa_mensal_detalhado": {
            "labels": [f"2026-{m:02d}" for m in range(1, num_months + 1)]
        },
    }


# =============================================================================
# Config
# =============================================================================


class TestConfig:
    def test_defaults_when_empty(self):
        cfg = PrevidenciaConfig.from_fiscal({})
        assert cfg.lucro_presumido_pct == 32.0
        assert cfg.pgbl_limite_pct == 12.0
        assert cfg.irpf_faixas == ()

    def test_from_fiscal_parses_faixas(self):
        cfg = PrevidenciaConfig.from_fiscal(
            {
                "lucro_presumido": {"percentual_servicos_pct": 32.0},
                "pgbl": {"limite_deducao_pct": 12.0},
                "irpf_tabela_progressiva": {
                    "faixas": [
                        {"limite_anual": 24_000, "aliquota_pct": 7.5},
                        {"limite_anual": 48_000, "aliquota_pct": 15.0},
                        {"limite_anual": None, "aliquota_pct": 27.5},
                    ]
                },
            }
        )
        assert len(cfg.irpf_faixas) == 3
        assert cfg.irpf_faixas[-1].limite_anual is None
        assert cfg.irpf_faixas[-1].aliquota_pct == 27.5


# =============================================================================
# Status N/D
# =============================================================================


class TestNoData:
    def test_returns_nd_when_no_pj_income(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=0))

        assert r.status == "N/D"
        assert r.renda_tributavel_anual == 0.0
        assert r.limite_pgbl_anual == 0.0
        assert r.aporte_mensal == 0.0
        assert r.economia_ir_anual == 0.0


# =============================================================================
# Cálculo completo
# =============================================================================


class TestCalculation:
    def test_lucro_presumido_applied_to_annualized_pj(self):
        # 12 meses de receita PJ, 10k cada → 120k ano
        # Lucro presumido 32% → 38.4k base tributável
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000, num_months=12))

        assert r.renda_tributavel_anual == pytest.approx(38_400.0)

    def test_anualiza_quando_menos_de_12_meses(self):
        # 6 meses, PJ total 60k → anualizado 120k → tributável 38.4k
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=60_000, num_months=6))

        assert r.renda_tributavel_anual == pytest.approx(38_400.0)

    def test_limite_pgbl_eh_12pct_da_base(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000, num_months=12))

        # 12% de 38.4k = 4.608
        assert r.limite_pgbl_anual == pytest.approx(4_608.0)

    def test_aporte_mensal_eh_limite_div_12(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000, num_months=12))

        assert r.aporte_mensal == pytest.approx(r.limite_pgbl_anual / 12)

    def test_status_calculado_com_receita_pj(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000))

        assert r.status == "Calculado"
        assert "PJ anualizada" in r.nota


# =============================================================================
# Alíquota marginal
# =============================================================================


class TestAliquotaMarginal:
    def test_usa_fallback_quando_sem_faixas(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000))

        # Default fallback 7.5%.
        assert r.aliquota_marginal == 7.5

    def test_sempre_aplica_ultima_faixa_sem_limite(self):
        """Paridade com legado (e5_analyze.py:1671-1678): o loop não quebra
        quando encontra a faixa correta; a última iteração (``limite=None``)
        sobrescreve a alíquota. Efetivamente, qualquer renda com tabela que
        tenha faixa ``None`` como última, recebe a alíquota dela.
        """
        cfg = PrevidenciaConfig.from_fiscal(
            {
                "irpf_tabela_progressiva": {
                    "faixas": [
                        {"limite_anual": 24_000, "aliquota_pct": 7.5},
                        {"limite_anual": 48_000, "aliquota_pct": 15.0},
                        {"limite_anual": None, "aliquota_pct": 27.5},
                    ]
                }
            }
        )
        # Base tributável 38.4k — última faixa (None, 27.5%) vence.
        r = PrevidenciaAnalyzer(cfg).analyze(_fluxo(pj=120_000, num_months=12))

        assert r.aliquota_marginal == 27.5

    def test_faixas_sem_ultima_none_usa_ultima_aplicavel(self):
        """Quando não há faixa ``None``, comportamento é o esperado: a
        última faixa cujo ``limite_anual < renda`` vence."""
        cfg = PrevidenciaConfig.from_fiscal(
            {
                "irpf_tabela_progressiva": {
                    "faixas": [
                        {"limite_anual": 24_000, "aliquota_pct": 7.5},
                        {"limite_anual": 48_000, "aliquota_pct": 15.0},
                    ]
                }
            }
        )
        # Base 38.4k > 24k mas < 48k → última faixa aplicável = 7.5%
        r = PrevidenciaAnalyzer(cfg).analyze(_fluxo(pj=120_000, num_months=12))

        assert r.aliquota_marginal == 7.5

    def test_ultima_faixa_sem_limite_captura_alta_renda(self):
        cfg = PrevidenciaConfig.from_fiscal(
            {
                "irpf_tabela_progressiva": {
                    "faixas": [
                        {"limite_anual": 24_000, "aliquota_pct": 7.5},
                        {"limite_anual": None, "aliquota_pct": 27.5},
                    ]
                }
            }
        )
        # Base 38.4k > 24k → última faixa (sem teto) 27.5%.
        r = PrevidenciaAnalyzer(cfg).analyze(_fluxo(pj=120_000, num_months=12))

        assert r.aliquota_marginal == 27.5


# =============================================================================
# Economia IR
# =============================================================================


class TestEconomiaIR:
    def test_economia_eh_limite_vezes_aliquota(self):
        cfg = PrevidenciaConfig.from_fiscal(
            {"irpf_tabela_progressiva": {"faixas": [{"limite_anual": None, "aliquota_pct": 27.5}]}}
        )
        r = PrevidenciaAnalyzer(cfg).analyze(_fluxo(pj=120_000, num_months=12))

        # limite 4608 × 27.5% ≈ 1267.2
        assert r.economia_ir_anual == pytest.approx(1_267.2, rel=1e-3)


# =============================================================================
# Legacy dict
# =============================================================================


class TestLegacyDict:
    def test_has_all_fields(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000))
        d = r.to_legacy_dict()

        required = {
            "status",
            "nota",
            "renda_tributavel_anual",
            "limite_pgbl_anual",
            "aporte_mensal",
            "aliquota_marginal",
            "economia_ir_anual",
        }
        assert required.issubset(d.keys())

    def test_result_is_analysis_type(self):
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=0))
        assert isinstance(r, PrevidenciaAnalysis)


# =============================================================================
# ADR-277 — reconciliação da recomendação PGBL via capacidade IRPF
# =============================================================================


def _capacidade(restante: str, renda: str = "38400", ano: int = 2024) -> CapacidadePgblIRPF:
    return CapacidadePgblIRPF(
        restante_anual=Decimal(restante),
        renda_tributavel_anual=Decimal(renda),
        ano_base=ano,
        fonte="irpf_pgbl_capacidade",
    )


class TestReconciliacaoIRPF:
    def test_inv_prev_3_recomenda_capacidade_restante_nao_teto_bruto(self):
        """INV-PREV-3: com já_aportado > 0, recomenda a capacidade RESTANTE,
        nunca o teto bruto que o proxy de receita PJ devolveria."""
        proxy = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000, num_months=12))
        recon = PrevidenciaAnalyzer().analyze(
            _fluxo(pj=120_000, num_months=12), capacidade_irpf=_capacidade("608")
        )

        assert proxy.limite_pgbl_anual == pytest.approx(4_608.0)  # teto bruto
        assert recon.limite_pgbl_anual == pytest.approx(608.0)  # restante real
        assert recon.aporte_mensal * 12 <= recon.limite_pgbl_anual + 1e-6
        assert recon.fonte_recomendacao == "irpf_capacidade"

    def test_inv_prev_3_no_teto_recomenda_zero(self):
        recon = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000), capacidade_irpf=_capacidade("0"))

        assert recon.status == "Calculado"
        assert recon.limite_pgbl_anual == 0.0
        assert recon.aporte_mensal == 0.0
        assert recon.fonte_recomendacao == "irpf_capacidade"

    def test_economia_usa_aliquota_marginal_da_renda_tributavel(self):
        cfg = PrevidenciaConfig.from_fiscal(
            {"irpf_tabela_progressiva": {"faixas": [{"limite_anual": None, "aliquota_pct": 27.5}]}}
        )
        recon = PrevidenciaAnalyzer(cfg).analyze(_fluxo(pj=0), capacidade_irpf=_capacidade("1000"))

        assert recon.economia_ir_anual == pytest.approx(275.0)

    def test_sem_capacidade_mantem_proxy(self):
        """Sem IRPF do titular → fallback ao proxy de receita PJ, sem mudança."""
        r = PrevidenciaAnalyzer().analyze(_fluxo(pj=120_000), capacidade_irpf=None)

        assert r.fonte_recomendacao == "proxy_receita_pj"
        assert r.limite_pgbl_anual == pytest.approx(4_608.0)


class TestINVPREV2:
    def test_recomendacao_nunca_vira_linha_de_ativo(self):
        """INV-PREV-2: PrevidenciaAnalysis é recomendação de aporte (fluxo
        dedutível), não tem campo de saldo/ativo patrimonial."""
        import dataclasses

        names = {f.name for f in dataclasses.fields(PrevidenciaAnalysis)}
        assert not (names & {"saldo", "saldo_31_12", "ativo", "valor", "valor_31_12"})


@pytest.mark.xfail(
    strict=True,
    reason="ADR-277 INV-PREV-1 (dedup de ativo previdência informe+G04): lane futura, "
    "sem caminho de input vivo — informe de previdência é órfão hoje.",
)
class TestINVPREV1Deferred:
    def test_mesmo_plano_informe_e_g04_vira_um_unico_ativo(self):
        from pipeline.domain.services import previdencia_dedup  # noqa: F401

        raise AssertionError("contrato de dedup de ativo de previdência ainda não existe")
