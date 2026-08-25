"""Tests — detector de vinculação do IRPFM (A40.l64 PR4 · [[ADR-414]] D5).

O produto não precisa do IRPFM ao centavo para não errar o SINAL. Acima do piso,
o IR devido pela tabela é abatido do mínimo e a economia do PGBL tende a zero;
prescrever ali é conselho invertido no público principal (PJ de serviço com
pró-labore baixo e dividendos altos).
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.services.irpf_pgbl_capacidade import (  # noqa: E402
    CapacidadePgbl,
    PgblStatus,
)
from pipeline.domain.services.previdencia_analyzer import (  # noqa: E402
    CapacidadePgblIRPF,
    MotivoAusenciaPgbl,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
)
from tests.unit.pipeline.test_pgbl_economia_diferencial import ANUAL_2026  # noqa: E402

_PISO = 60_000_000  # R$ 600.000 em cents


def _cap(rend_upper: str, renda: str = "300000") -> CapacidadePgblIRPF:
    resto = Decimal(renda) * Decimal("0.12")
    return CapacidadePgblIRPF(
        capacidade=CapacidadePgbl(
            teto=resto,
            aportado=Decimal("0"),
            restante=resto,
            status=PgblStatus.capacidade_disponivel,
            excedente_nao_dedutivel=Decimal("0"),
        ),
        renda_tributavel_anual=Decimal(renda),
        ano_base=2026,
        fonte="irpf_pgbl_capacidade",
        base_calculo_anual=Decimal(renda),
        rend_upper_anual=Decimal(rend_upper),
    )


def _cfg(limiar: int = _PISO) -> PrevidenciaConfig:
    return PrevidenciaConfig(irpf_faixas=ANUAL_2026, irpfm_limiar_brl_cents=limiar)


class TestDetector:
    def test_acima_do_piso_retem_prescricao(self):
        r = PrevidenciaAnalyzer(_cfg()).analyze({}, capacidade_irpf=_cap("700000"))

        assert r.economia_ir_anual is None
        assert r.aporte_mensal is None
        assert r.motivo_ausencia["economia"] == MotivoAusenciaPgbl.irpfm_pode_vincular

    def test_abaixo_do_piso_publica(self):
        """Braço de controle: sem ele o detector poderia calar todo mundo."""
        r = PrevidenciaAnalyzer(_cfg()).analyze({}, capacidade_irpf=_cap("599999"))

        assert r.economia_ir_anual is not None
        assert r.motivo_ausencia["economia"] is None

    def test_o_FATO_do_irpf_sobrevive(self):
        # O espaço de 12% vem do IRPF e não depende do mínimo.
        """Mesma polaridade de `regime_fiscal_incompleto`: anula prescrição, não fato."""
        r = PrevidenciaAnalyzer(_cfg()).analyze({}, capacidade_irpf=_cap("700000"))

        assert r.limite_pgbl_anual > 0
        assert r.motivo_ausencia["teto"] is None

    def test_ano_sem_irpfm_nunca_vincula(self):
        """AC <= 2025: limiar 0 na row ⇒ o detector é inerte, sem `if year`."""
        r = PrevidenciaAnalyzer(_cfg(limiar=0)).analyze({}, capacidade_irpf=_cap("5000000"))

        assert r.economia_ir_anual is not None

    def test_a_borda_e_inclusiva(self):
        """`>=` porque o art. 16-A começa a incidir NO piso, não acima dele."""
        r = PrevidenciaAnalyzer(_cfg()).analyze({}, capacidade_irpf=_cap("600000"))

        assert r.economia_ir_anual is None

    def test_a_nota_nomeia_o_mecanismo(self):
        nota = PrevidenciaAnalyzer(_cfg()).analyze({}, capacidade_irpf=_cap("700000")).nota

        assert "IRPFM" in nota and "15.270" in nota
        # Explica o mecanismo, não só declara ausência.
        assert "abatido do mínimo" in nota


# =============================================================================
# A40.l64 §Critério 3 — o que torna o flip do AC2026 SEGURO
#
# Flipar `regime_completo` liga a publicação. Com 2+ declarações no ano a base do
# card é SOMA familiar e a progressividade não é aditiva (`IR(a+b) > IR(a)+IR(b)`),
# então a economia sairia SUPERESTIMADA. Publica-se onde está certo; recusa-se
# onde se sabe enviesado ([[ADR-414]] §Limitação).
# =============================================================================


class TestBaseFamiliarNaoParticionada:
    def _com(self, n: int):
        cap = _cap("100000", renda="300000")
        from dataclasses import replace

        return PrevidenciaAnalyzer(_cfg()).analyze(
            {}, capacidade_irpf=replace(cap, declaracoes_no_ano=n)
        )

    def test_duas_declaracoes_retem_a_prescricao(self):
        r = self._com(2)

        assert r.economia_ir_anual is None
        assert r.aporte_mensal is None
        assert r.motivo_ausencia["economia"] == MotivoAusenciaPgbl.base_familiar_nao_particionada

    def test_uma_declaracao_publica(self):
        """Braço de controle: o flip existe para ESTE caso — sem ele nada muda."""
        r = self._com(1)

        assert r.economia_ir_anual is not None
        assert r.motivo_ausencia["economia"] is None

    def test_o_fato_do_irpf_sobrevive_nos_dois(self):
        assert self._com(2).limite_pgbl_anual > 0
        assert self._com(1).limite_pgbl_anual > 0

    def test_a_nota_diz_que_a_limitacao_e_nossa(self):
        # O cliente não tem o que corrigir — "não se aplica" empurraria para ele um
        # problema de modelagem nosso.
        nota = self._com(2).nota

        assert "mais de uma declaração" in nota
        assert "superestimaria" in nota
