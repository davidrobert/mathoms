"""FP-5A: o teto de 12% e a capacidade restante são grandezas distintas.

Antes do fix, ``limite_pgbl_anual`` — nome de **teto** — carregava a
``capacidade restante`` e publicava ``0.0`` em declaração simplificada, onde o
teto sequer existe. Valor correto sob rótulo errado: o leitor (humano e LLM) lê
"seu limite de PGBL é R$ 0" quando o fato é "o modelo escolhido desabilita a
dedução". Ver ADR-402.

O gate mede o MECANISMO, não a aparência: para cada
(``PgblStatus`` × ``regime_completo``) assere a **coocorrência** entre o campo
publicado e o fragmento canônico da nota. Nota e campos derivam ambos do VO —
nunca um do outro —, então divergir aqui é divergência de fonte, não de texto.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pipeline.domain.services.irpf_analyzer import CapacidadePgbl, PgblStatus
from pipeline.domain.services.previdencia_analyzer import (
    CAMPOS_MOTIVO_PGBL,
    FRAGMENTO_CANONICO_MOTIVO,
    CapacidadePgblIRPF,
    MotivoAusenciaPgbl,
    PrevidenciaAnalyzer,
    PrevidenciaConfig,
    motivo_dominante,
)

_RENDA = Decimal("100000")
_TETO = _RENDA * Decimal("0.12")


def _vo(status: PgblStatus, *, aportado: str = "0") -> CapacidadePgbl:
    """VO coerente com o status — o analyzer não recalcula, ele publica."""
    ap = Decimal(aportado)
    if status in (PgblStatus.modelo_simplificado, PgblStatus.sem_renda_tributavel):
        return CapacidadePgbl(
            teto=None, aportado=ap, restante=None, status=status, excedente_nao_dedutivel=ap
        )
    restante = Decimal("0") if status is PgblStatus.no_teto else _TETO - ap
    return CapacidadePgbl(
        teto=_TETO,
        aportado=ap,
        restante=restante,
        status=status,
        excedente_nao_dedutivel=Decimal("0"),
    )


def _cap(status: PgblStatus, *, aportado: str = "0") -> CapacidadePgblIRPF:
    return CapacidadePgblIRPF(
        capacidade=_vo(status, aportado=aportado),
        renda_tributavel_anual=_RENDA,
        ano_base=2024,
        fonte="irpf_pgbl_capacidade",
    )


def _config(regime_completo: bool) -> PrevidenciaConfig:
    return PrevidenciaConfig(
        regime_completo=regime_completo,
        componentes_ausentes=() if regime_completo else ("redutor_lei_15270",),
        ano_fiscal=2026,
    )


def _analise(status: PgblStatus, regime_completo: bool, aportado: str = "0"):
    return PrevidenciaAnalyzer(_config(regime_completo)).analyze(
        {}, capacidade_irpf=_cap(status, aportado=aportado)
    )


_MATRIZ = [(status, regime) for status in PgblStatus for regime in (True, False)]


@pytest.mark.parametrize("status,regime_completo", _MATRIZ)
def test_motivo_dominante_segue_a_precedencia_declarada(status, regime_completo):
    r = _analise(status, regime_completo)
    esperado = {
        PgblStatus.modelo_simplificado: MotivoAusenciaPgbl.modelo_simplificado,
        PgblStatus.sem_renda_tributavel: MotivoAusenciaPgbl.sem_renda_tributavel,
    }.get(status, None if regime_completo else MotivoAusenciaPgbl.regime_fiscal_incompleto)

    assert motivo_dominante(r.motivo_ausencia) == esperado


@pytest.mark.parametrize("status,regime_completo", _MATRIZ)
def test_ausencia_de_campo_e_bicondicional_com_motivo(status, regime_completo):
    """``campo is None ⟺ motivo_ausencia[campo] is not None`` — sem null mudo."""
    r = _analise(status, regime_completo)
    valores = {
        "teto": r.limite_pgbl_anual,
        "restante": r.capacidade_restante_anual,
        "aporte": r.aporte_mensal,
        "economia": r.economia_ir_anual,
    }
    assert set(valores) == set(CAMPOS_MOTIVO_PGBL)
    for campo, valor in valores.items():
        motivo = r.motivo_ausencia[campo]
        assert (valor is None) == (motivo is not None), (campo, valor, motivo)


@pytest.mark.parametrize("status,regime_completo", _MATRIZ)
def test_zero_publicado_nunca_carrega_motivo_de_ausencia(status, regime_completo):
    """Invariante global: ``campo == 0.0 ⇒ motivo_ausencia[campo] is None``."""
    r = _analise(status, regime_completo)
    for campo, valor in (
        ("teto", r.limite_pgbl_anual),
        ("restante", r.capacidade_restante_anual),
        ("aporte", r.aporte_mensal),
        ("economia", r.economia_ir_anual),
    ):
        if valor is not None and Decimal(valor) == 0:
            assert r.motivo_ausencia[campo] is None, campo


@pytest.mark.parametrize("status,regime_completo", _MATRIZ)
def test_nota_coocorre_com_o_motivo_e_exclui_os_demais(status, regime_completo):
    """O fragmento canônico do motivo dominante está na nota; o dos outros, não."""
    r = _analise(status, regime_completo)
    dominante = motivo_dominante(r.motivo_ausencia)

    if dominante is not None:
        assert FRAGMENTO_CANONICO_MOTIVO[dominante] in r.nota
    for motivo, fragmento in FRAGMENTO_CANONICO_MOTIVO.items():
        if motivo is not dominante:
            assert fragmento not in r.nota, (status, regime_completo, motivo)


@pytest.mark.parametrize("status,regime_completo", _MATRIZ)
def test_aliquota_marginal_e_bicondicional_com_economia(status, regime_completo):
    """Marginal sem economia publicável é ruído citável que convida a reconstrução."""
    r = _analise(status, regime_completo)
    assert (r.aliquota_marginal is not None) == (r.economia_ir_anual is not None)


def test_teto_e_doze_por_cento_da_base_nao_a_capacidade_restante():
    """O defeito de origem: com aporte já feito, teto ≠ restante."""
    r = _analise(PgblStatus.capacidade_disponivel, True, aportado="4000")

    assert r.limite_pgbl_anual == _TETO
    assert r.capacidade_restante_anual == _TETO - Decimal("4000")
    assert r.limite_pgbl_anual > r.capacidade_restante_anual


def test_simplificado_nao_publica_teto_zero():
    """Regressão FP-5A: ``0.0`` sob o nome ``limite_pgbl_anual`` é rótulo errado."""
    r = _analise(PgblStatus.modelo_simplificado, True)

    assert r.limite_pgbl_anual is None
    assert r.motivo_ausencia["teto"] == MotivoAusenciaPgbl.modelo_simplificado
    assert r.aliquota_marginal is None


def test_simplificado_anula_tudo_e_cala_o_regime_incompleto():
    """Precedência: com regime incompleto E simplificado, a nota diz UMA coisa."""
    r = _analise(PgblStatus.modelo_simplificado, False)

    assert set(r.motivo_ausencia.values()) == {MotivoAusenciaPgbl.modelo_simplificado}
    assert FRAGMENTO_CANONICO_MOTIVO[MotivoAusenciaPgbl.regime_fiscal_incompleto] not in r.nota


def test_regime_incompleto_preserva_teto_e_restante():
    r = _analise(PgblStatus.capacidade_disponivel, False, aportado="4000")

    assert r.limite_pgbl_anual == _TETO
    assert r.capacidade_restante_anual == _TETO - Decimal("4000")
    assert r.aporte_mensal is None
    assert r.economia_ir_anual is None
    assert r.motivo_ausencia["aporte"] == MotivoAusenciaPgbl.regime_fiscal_incompleto


def test_sem_irpf_processado_marca_os_quatro_campos():
    r = PrevidenciaAnalyzer().analyze({}, capacidade_irpf=None)

    assert set(r.motivo_ausencia.values()) == {MotivoAusenciaPgbl.sem_irpf_processado}
    assert r.limite_pgbl_anual is None
    assert r.capacidade_restante_anual is None


def test_excedente_nao_dedutivel_sobrevive_ao_clamp():
    """``max(0, teto − aportado)`` apagava o terceiro fato — o mais acionável."""
    cap = CapacidadePgblIRPF(
        capacidade=CapacidadePgbl(
            teto=None,
            aportado=Decimal("9000"),
            restante=None,
            status=PgblStatus.modelo_simplificado,
            excedente_nao_dedutivel=Decimal("9000"),
        ),
        renda_tributavel_anual=_RENDA,
        ano_base=2024,
        fonte="irpf_pgbl_capacidade",
    )
    r = PrevidenciaAnalyzer(_config(True)).analyze({}, capacidade_irpf=cap)

    assert r.excedente_nao_dedutivel_anual == Decimal("9000")
    assert r.pgbl_aportado_anual == Decimal("9000")


def test_wire_publica_estado_que_so_existia_em_prosa():
    d = _analise(PgblStatus.modelo_simplificado, True).to_legacy_dict()

    assert d["pgbl_status"] == "modelo_simplificado"
    assert d["limite_pgbl_anual"] is None
    assert d["capacidade_restante_anual"] is None
    assert d["motivo_ausencia"]["teto"] == "modelo_simplificado"
    assert d["pgbl_aportado_anual"] == 0.0
