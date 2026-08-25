"""Tests — `pgbl_economia_ir.economia_diferencial` e a fiação dela (ADR-375 D5).

O D5 declarou que a diferencial **encerra** o `limite × alíquota marginal`. O
ataque à A40.l64 mediu que o instrumento encerrado era o único que rodava; estes
testes são o que torna a afirmação falsificável.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_analyzer import CapacidadePgbl, PgblStatus  # noqa: E402
from pipeline.domain.services.pgbl_economia_ir import economia_diferencial  # noqa: E402
from pipeline.domain.services.previdencia_analyzer import (  # noqa: E402
    CapacidadePgblIRPF,
    MotivoAusenciaPgbl,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)
from pipeline.domain.types.config import IRPFBracket  # noqa: E402


# Derivada da MIGRATION, nunca de literais: a cópia à mão divergia em centavos
# (472991 vs 472992) e o teste passaria a medir a fantasia, não a tabela que roda.
def _anual_da_seed(ano: int = 2026) -> tuple[IRPFBracket, ...]:
    from tests.pipeline_golden_substrate import fiscal_store_do_seed

    store = fiscal_store_do_seed(ano)
    return store.get_fiscal_for_period(date(ano, 1, 1), date(ano, 12, 31)).ir_brackets_anual.faixas


ANUAL_2026 = _anual_da_seed()


def _capacidade(restante: str, renda: str, base: str | None = None) -> CapacidadePgblIRPF:
    resto = Decimal(restante)
    teto = max(Decimal(renda) * Decimal("0.12"), resto)
    return CapacidadePgblIRPF(
        capacidade=CapacidadePgbl(
            teto=teto,
            aportado=teto - resto,
            restante=resto,
            status=(PgblStatus.capacidade_disponivel if resto > 0 else PgblStatus.no_teto),
            excedente_nao_dedutivel=Decimal("0"),
        ),
        renda_tributavel_anual=Decimal(renda),
        base_calculo_anual=Decimal(base) if base is not None else Decimal(renda),
        ano_base=2024,
        fonte="irpf_pgbl_capacidade",
    )


class TestEconomiaDiferencial:
    def test_atravessar_degrau_diverge_do_produto(self):
        """56.000 está em 27,5%; 56.000 − 6.720 = 49.280 cai em 22,5%."""
        economia = economia_diferencial(Decimal("56000"), Decimal("6720"), ANUAL_2026)

        assert economia == Decimal("1513.19")
        # O instrumento que o D5 encerra daria 6.720 × 27,5% = 1.848,00.
        assert economia != Decimal("6720") * Decimal("0.275")

    def test_base_isenta_devolve_zero(self):
        """Sem imposto a reduzir não há economia — o produto publicaria 180,00."""
        assert economia_diferencial(Decimal("20000"), Decimal("2400"), ANUAL_2026) == Decimal("0")

    def test_aporte_maior_que_a_base_nao_estoura(self):
        """`base − aporte` negativo é aritmética, não estado: satura em zero."""
        economia = economia_diferencial(Decimal("30000"), Decimal("90000"), ANUAL_2026)

        assert economia == Decimal("64.08")  # todo o IR devido, nada além dele

    def test_faixa_unica_sem_parcela_colapsa_no_produto(self):
        """Por que o teste histórico do produto sobreviveu ao D5: nesta tabela eles coincidem."""
        faixa = (
            IRPFBracket(upper_brl_cents=None, aliquota_pct=Decimal("27.5"), deducao_brl_cents=0),
        )

        assert economia_diferencial(Decimal("38400"), Decimal("4608"), faixa) == Decimal("1267.2")


class TestFiacaoNoAnalyzer:
    def test_analyzer_publica_a_diferencial(self):
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        r = PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_capacidade("6720", "56000"))

        assert r.economia_ir_anual == Decimal("1513.19")
        # A marginal publicada continua sendo a da faixa que CONTÉM a base (D6).
        assert r.aliquota_marginal == 27.5

    def test_zero_e_fato_publicado_nao_ausencia(self):
        """Invariante ADR-402: campo == 0 ⇒ motivo do campo é None."""
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        r = PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_capacidade("2400", "20000"))

        assert r.economia_ir_anual == Decimal("0")
        assert r.motivo_ausencia["economia"] is None

    # Braço de CONTROLE: sem ele os testes acima passariam com o caminho legado.
    def test_sem_tabela_degrada_para_o_fallback_declarado(self):
        cfg = PrevidenciaConfig(irpf_faixas=(), aliquota_fallback=7.5)
        r = PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_capacidade("4608", "38400"))

        assert r.economia_ir_anual == Decimal("4608") * Decimal("7.5") / Decimal("100")


# =============================================================================
# Defeito vivo destravado pelo PR2 — economia zero NÃO autoriza prescrever aporte
#
# `aporte_mensal` era gateado pelo MOTIVO, não pela economia. Com o diferencial,
# base isenta passou a devolver economia R$ 0,00 legítima — e o card seguia
# prescrevendo aporte ao lado dela. A ADR-375 D4 cond. 2 exige
# `IR(base) − IR(base − aporte) > 0` para prescrever; o gate não expressava isso.
# Decisão do `financial-planner` (2026-08-24): motivo próprio no campo `aporte`,
# último na precedência — é o único que coexiste com campos publicados.
# =============================================================================


class TestEconomiaZeroNaoPrescreve:
    def _isento(self):
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        return PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_capacidade("2400", "20000"))

    def test_aporte_e_retido_com_motivo_proprio(self):
        r = self._isento()

        assert r.aporte_mensal is None
        assert r.motivo_ausencia["aporte"] == MotivoAusenciaPgbl.sem_imposto_a_reduzir

    def test_a_economia_zero_continua_publicada_sem_motivo(self):
        """Invariante ADR-402: reter a prescrição não apaga o fato medido."""
        r = self._isento()

        assert r.economia_ir_anual == Decimal("0")
        assert r.motivo_ausencia["economia"] is None

    def test_marginal_sai_junto_do_aporte(self):
        """Marginal sem economia POSITIVA convida a reconstruir a prescrição retida."""
        r = self._isento()

        assert r.aliquota_marginal is None

    def test_o_teto_do_irpf_sobrevive(self):
        """Falsificável: sem isto o teste passaria por ausência de capacidade."""
        r = self._isento()

        assert r.limite_pgbl_anual == Decimal("2400")
        assert r.motivo_ausencia["teto"] is None

    def test_economia_positiva_segue_prescrevendo(self):
        """Braço de controle: o gate novo não pode calar o caso que deve falar."""
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        r = PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_capacidade("6720", "56000"))

        assert r.economia_ir_anual > 0
        assert r.aporte_mensal is not None
        assert r.aliquota_marginal is not None
        assert r.motivo_ausencia["aporte"] is None


# =============================================================================
# ADR-414 — o imposto incide sobre a BASE declarada, não sobre o bruto
# =============================================================================


class TestBaseDeCalculoDeclarada:
    def test_economia_usa_a_base_nao_o_bruto(self):
        """Mesmo bruto, bases diferentes ⇒ economias diferentes. O bruto não decide."""
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        sem_deducao = PrevidenciaAnalyzer(cfg).analyze(
            {}, capacidade_irpf=_capacidade("8400", "70000", base="70000")
        )
        com_deducao = PrevidenciaAnalyzer(cfg).analyze(
            {}, capacidade_irpf=_capacidade("8400", "70000", base="50000")
        )

        assert sem_deducao.economia_ir_anual != com_deducao.economia_ir_anual
        # 70.000 → faixa terminal dos dois lados: 8.400 × 27,5%.
        assert sem_deducao.economia_ir_anual == Decimal("2310.00")
        # 50.000 → 41.600 atravessa o degrau 22,5% → 15%.
        assert com_deducao.economia_ir_anual == Decimal("1634.06")

    def test_marginal_resolve_a_faixa_da_base(self):
        """ADR-375 D6 sempre falou de base; o call-site é que passava o bruto."""
        cfg = PrevidenciaConfig(irpf_faixas=ANUAL_2026)
        r = PrevidenciaAnalyzer(cfg).analyze(
            {}, capacidade_irpf=_capacidade("8400", "70000", base="50000")
        )

        assert r.aliquota_marginal == 22.5  # faixa de 50.000, não a de 70.000
        assert r.aliquota_marginal != 27.5

    # O teste `test_sem_base_declarada_nao_publica_economia` foi REMOVIDO junto
    # com a decisão de tornar `base_calculo_anual` obrigatória: ele construía um
    # estado que o tipo não representa mais. Teste de ramo que não dispara mede a
    # si mesmo — a garantia passou a ser do construtor.
