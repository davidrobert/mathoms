"""A ausência de row fiscal recusa, e a fixture não pode resolver ano que a produção não resolve.

[[A40.l79]]. O defeito: a seed de `fiscal_parameters` termina em 2026-12-31,
`list_covering_period` não tem clamp, e o `except Exception` de `analyze_finances`
mandava a ausência para o dict legado — que presume `regime_completo=True`, não tem
tabela, redutor nem piso de IRPFM. Pós-flip do AC2026 esse `True` virou o estado
NORMAL, então o número errado saía sem rastro nenhum.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
from pipeline.domain.types.config import FiscalParameters  # noqa: E402
from pipeline.ports.config_store import FiscalParametersAusentes  # noqa: E402


def _cap(bruto: str = "70000", base: str = "56000") -> CapacidadePgblIRPF:
    resto = Decimal(bruto) * Decimal("0.12")
    return CapacidadePgblIRPF(
        capacidade=CapacidadePgbl(
            teto=resto,
            aportado=Decimal("0"),
            restante=resto,
            status=PgblStatus.capacidade_disponivel,
            excedente_nao_dedutivel=Decimal("0"),
        ),
        renda_tributavel_anual=Decimal(bruto),
        ano_base=2027,
        fonte="irpf_pgbl_capacidade",
        base_calculo_anual=Decimal(base),
        rend_upper_anual=Decimal(bruto),
    )


class TestRecusaPorTabelaAusente:
    def _sem_row(self):
        cfg = PrevidenciaConfig.from_fiscal_parameters(
            FiscalParameters(year=2027, tabela_ausente=True)
        )
        return PrevidenciaAnalyzer(cfg).analyze({}, capacidade_irpf=_cap())

    def test_nao_publica_economia(self):
        # Sem o fix o legado publicava R$ 630,00 com marginal de 7,5% — número que
        # não vem de tabela nenhuma.
        r = self._sem_row()

        assert r.economia_ir_anual is None
        assert r.aporte_mensal is None

    def test_o_motivo_distingue_de_regime_incompleto(self):
        """`regime_fiscal_incompleto` AFIRMA sobre um regime conhecido; aqui não há."""
        r = self._sem_row()

        assert r.motivo_ausencia["economia"] == MotivoAusenciaPgbl.sem_tabela_fiscal_do_ano
        assert r.motivo_ausencia["economia"] != MotivoAusenciaPgbl.regime_fiscal_incompleto

    def test_o_fato_do_irpf_sobrevive(self):
        """Falsificável: sem isto o teste passaria por ausência de capacidade."""
        r = self._sem_row()

        assert r.limite_pgbl_anual > 0
        assert r.motivo_ausencia["teto"] is None

    def test_a_nota_nomeia_o_ano_e_o_que_falta(self):
        nota = self._sem_row().nota

        assert "2027" in nota
        assert "tabela" in nota.lower()

    def test_com_row_publica(self):
        """Braço de controle: a recusa é da AUSÊNCIA, não de todo AC2027."""
        from tests.pipeline_golden_substrate import fiscal_store_do_seed

        fp = fiscal_store_do_seed(2026).get_fiscal_for_period(date(2026, 1, 1), date(2026, 12, 31))
        r = PrevidenciaAnalyzer(PrevidenciaConfig.from_fiscal_parameters(fp)).analyze(
            {}, capacidade_irpf=_cap()
        )

        assert r.economia_ir_anual is not None


class TestFixtureNaoResolveOQueProducaoNaoResolve:
    # `fiscal_store_do_seed` fazia `max(a for a in tabelas if a <= year)` e servia a
    # linha de 2026 para 2027 e 2030 — clamp que a produção não tem. O golden ficava
    # verde num eixo em que a produção falha.
    """§Critério 2 da lane: o clamp da fixture deixa de ser invisível."""

    def _anos_semeados(self) -> set[int]:
        from tests.pipeline_golden_substrate import _tabelas_da_migration_adr389

        return set(_tabelas_da_migration_adr389())

    @pytest.mark.parametrize("ano", [2027, 2030])
    def test_ano_nao_semeado_nao_resolve_na_fixture(self, ano: int):
        from tests.pipeline_golden_substrate import fiscal_store_do_seed

        assert ano not in self._anos_semeados(), "fixture do teste ficou obsoleta"
        with pytest.raises(FiscalParametersAusentes):
            fiscal_store_do_seed(ano).get_fiscal_for_period(date(ano, 1, 1), date(ano, 12, 31))

    def test_ano_semeado_continua_resolvendo(self):
        """Braço de controle: sem ele, uma fixture quebrada passaria o teste acima."""
        from tests.pipeline_golden_substrate import fiscal_store_do_seed

        fp = fiscal_store_do_seed(2026).get_fiscal_for_period(date(2026, 1, 1), date(2026, 12, 31))

        assert fp.year == 2026
        assert fp.ir_brackets_anual.faixas


class TestFiacaoNoAnalyzeFinances:
    # Os testes acima constroem o VO direto e provam a REGRA. Este prova a FIAÇÃO:
    # que `analyze_finances` traduz a exceção do port em recusa, em vez de mandar a
    # ausência para o dict legado. Sem ele, o fix de produção não tem gate — a
    # mutação de reverter aquele `except` passava com tudo verde.
    """O caminho de produção traduz ausência em recusa, não em fallback."""

    def _store_sem_row(self):
        from pipeline.adapters.in_memory_config_store import InMemoryConfigStore

        # `fiscal_by_year` vazio ⇒ `get_fiscal_for_period` levanta a exceção do port,
        # que é exatamente o que a produção vê quando a seed não cobre o ano.
        return InMemoryConfigStore(fiscal_by_year={})

    def _bloco_previdencia(self, tmp_path: Path) -> dict:
        from tests.pipeline_golden_substrate import run_e3_e4_e5, write_e5_config
        from tests.test_e5_golden_construtor_de_producao import (
            _ANO_BASE_IRPF,
            _e3_payload,
            _irpf_com_renda_tributavel,
        )

        write_e5_config(tmp_path)
        analise = run_e3_e4_e5(
            tmp_path,
            e3_payloads=_e3_payload(),
            irpf_payloads={f"irpfdeclaracao_{_ANO_BASE_IRPF}": _irpf_com_renda_tributavel()},
            config_store=self._store_sem_row(),
        )
        return analise.get("previdencia_pgbl") or {}

    def test_payload_recusa_com_o_motivo_da_ausencia(self, tmp_path: Path):
        bloco = self._bloco_previdencia(tmp_path)

        assert bloco.get("economia_ir_anual") is None
        assert bloco.get("aporte_mensal") is None
        assert bloco["motivo_ausencia"]["economia"] == "sem_tabela_fiscal_do_ano"
        # Falsificável: sem isto, o teste passaria por ausência de CAPACIDADE.
        assert bloco.get("limite_pgbl_anual") is not None
