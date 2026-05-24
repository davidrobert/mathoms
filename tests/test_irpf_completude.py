"""Unit tests para ``irpf_completude`` — ADR-266 tri-state."""

# Cobertura: prazo RFB (provisorio/incompleto), shell-only, continuidade familiar,
# pick_default_year (fallback completo > provisorio > incompleto), regressão
# workspace 1b9f2cf5 (2023 incompleto, 2024 completo, 2025 incompleto).

from __future__ import annotations

import datetime as _dt
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.domain.services.irpf_completude import (
    CompletudeAno,
    compute_completude,
    pick_default_year,
)
from pipeline.llm.schemas.e16_irpf_full import (
    CodigoRendimentoIsento,
    Contribuinte,
    FontePagadoraPJ,
    ImpostoApurado,
    IRPFFullOutput,
    ModeloDeclaracao,
    NaturezaContribuinte,
    RendimentoIsento,
)


def _zero_imposto() -> ImpostoApurado:
    return ImpostoApurado(
        base_calculo_brl=Decimal("0"),
        ir_devido_brl=Decimal("0"),
        deducoes_totais_brl=Decimal("0"),
        ir_pago_brl=Decimal("0"),
        ir_a_pagar_brl=Decimal("0"),
    )


def _pj(n: int) -> list[FontePagadoraPJ]:
    return [
        FontePagadoraPJ(
            cnpj="**.***.***/****-**",
            nome=f"PJ {i}",
            rendimentos_tributaveis_brl=Decimal("1000"),
            contrib_previdenciaria_brl=Decimal("0"),
            ir_retido_brl=Decimal("0"),
        )
        for i in range(n)
    ]


def _iso(n: int) -> list[RendimentoIsento]:
    return [
        RendimentoIsento(
            codigo_rfb=CodigoRendimentoIsento.lucros_dividendos,
            descricao=f"iso {i}",
            valor_brl=Decimal("500"),
        )
        for i in range(n)
    ]


def _contrib(cpf: str, nome: str, ano: int) -> Contribuinte:
    return Contribuinte(
        cpf_masked=cpf,
        nome=nome,
        ano_base=ano,
        exercicio=ano + 1,
        modelo=ModeloDeclaracao.completo,
        natureza=NaturezaContribuinte.titular,
    )


def _make_decl(
    *,
    cpf: str = "***.***.***-36",
    nome: str = "DAVID",
    ano: int = 2024,
    pj: int = 0,
    iso: int = 0,
) -> IRPFFullOutput:
    return IRPFFullOutput(
        contribuinte=_contrib(cpf, nome, ano),
        rendimentos_pj=_pj(pj),
        rendimentos_isentos=_iso(iso),
        imposto_apurado=_zero_imposto(),
        confidence=0.95,
    )


_HOJE_2026_05 = _dt.date(2026, 5, 23)
_HOJE_2026_07 = _dt.date(2026, 7, 1)


# -----------------------------------------------------------------------------
# Prazo RFB
# -----------------------------------------------------------------------------


def test_provisorio_dentro_janela_rfb():
    # Ano 2025: prazo final 31/maio/2026. Hoje 23/maio/2026 → ainda dentro.
    decls = {2025: [_make_decl(ano=2025, pj=1)]}
    state, motivo = compute_completude(decls, 2025, _HOJE_2026_05)
    assert state == CompletudeAno.provisorio
    assert "janela RFB" in (motivo or "")


def test_incompleto_dentro_janela_sem_dados():
    decls = {2025: []}
    state, motivo = compute_completude(decls, 2025, _HOJE_2026_05)
    assert state == CompletudeAno.incompleto


def test_completo_pos_prazo_com_dados():
    # Ano 2024: prazo final 31/maio/2025; hoje julho/2026 → muito após.
    decls = {2024: [_make_decl(ano=2024, pj=2)]}
    state, motivo = compute_completude(decls, 2024, _HOJE_2026_07)
    assert state == CompletudeAno.completo
    assert motivo is None


# -----------------------------------------------------------------------------
# Shell-only
# -----------------------------------------------------------------------------


def test_incompleto_se_todas_shell():
    # Pós-prazo, mas todas declarações são shell — sem dados de renda.
    decls = {2024: [_make_decl(ano=2024, pj=0, iso=0)]}
    state, motivo = compute_completude(decls, 2024, _HOJE_2026_07)
    assert state == CompletudeAno.incompleto
    assert "renda" in (motivo or "").lower()


# -----------------------------------------------------------------------------
# Continuidade familiar
# -----------------------------------------------------------------------------


def test_incompleto_falta_cpf_de_ano_anterior():
    # 2023: casal (DAVID + MARIANA). 2024: só DAVID.
    decls = {
        2023: [
            _make_decl(cpf="***.***.***-36", ano=2023, pj=2),
            _make_decl(cpf="***.***.***-60", ano=2023, pj=2),
        ],
        2024: [_make_decl(cpf="***.***.***-36", ano=2024, pj=2)],
    }
    state, motivo = compute_completude(decls, 2024, _HOJE_2026_07)
    assert state == CompletudeAno.incompleto
    assert "***.***.***-60" in (motivo or "")


def test_completo_mesma_familia():
    decls = {
        2023: [_make_decl(cpf="***.***.***-36", ano=2023, pj=2)],
        2024: [_make_decl(cpf="***.***.***-36", ano=2024, pj=2)],
    }
    state, _ = compute_completude(decls, 2024, _HOJE_2026_07)
    assert state == CompletudeAno.completo


def test_completo_familia_cresceu():
    # 2023: só DAVID. 2024: DAVID + MARIANA — não conta como lacuna.
    decls = {
        2023: [_make_decl(cpf="***.***.***-36", ano=2023, pj=2)],
        2024: [
            _make_decl(cpf="***.***.***-36", ano=2024, pj=2),
            _make_decl(cpf="***.***.***-60", ano=2024, pj=2),
        ],
    }
    state, _ = compute_completude(decls, 2024, _HOJE_2026_07)
    assert state == CompletudeAno.completo


# -----------------------------------------------------------------------------
# pick_default_year
# -----------------------------------------------------------------------------


def test_pick_default_prefers_completo_over_provisorio():
    completude = {
        2023: CompletudeAno.completo,
        2024: CompletudeAno.completo,
        2025: CompletudeAno.provisorio,
    }
    assert pick_default_year(completude) == 2024


def test_pick_default_falls_back_to_provisorio():
    completude = {2024: CompletudeAno.provisorio, 2025: CompletudeAno.incompleto}
    assert pick_default_year(completude) == 2024


def test_pick_default_falls_back_to_incompleto():
    completude = {2023: CompletudeAno.incompleto, 2024: CompletudeAno.incompleto}
    assert pick_default_year(completude) == 2024


def test_pick_default_empty():
    assert pick_default_year({}) is None


# -----------------------------------------------------------------------------
# Regressão workspace 1b9f2cf5
# -----------------------------------------------------------------------------


def _workspace_1b9f2cf5_decls() -> dict[int, list[IRPFFullOutput]]:
    """2023: Mariana sozinha. 2024: casal. 2025: só DAVID + shell -87 (OCR)."""
    return {
        2023: [_make_decl(cpf="***.***.***-60", nome="MARIANA", ano=2023, pj=1)],
        2024: [
            _make_decl(cpf="***.***.***-36", nome="DAVID", ano=2024, pj=2),
            _make_decl(cpf="***.***.***-60", nome="MARIANA", ano=2024, pj=2),
        ],
        2025: [
            _make_decl(cpf="***.***.***-36", nome="DAVID", ano=2025, pj=1, iso=2),
            _make_decl(cpf="***.***.***-87", nome="DAVID", ano=2025, pj=0, iso=0),
        ],
    }


def test_regression_workspace_1b9f2cf5():
    # Hoje 23/maio/2026: 2025 ainda na janela RFB.
    decls = _workspace_1b9f2cf5_decls()
    s23, _ = compute_completude(decls, 2023, _HOJE_2026_05)
    s24, _ = compute_completude(decls, 2024, _HOJE_2026_05)
    s25, _ = compute_completude(decls, 2025, _HOJE_2026_05)
    assert s23 == CompletudeAno.completo  # sem ano anterior, MARIANA sozinha ok
    assert s24 == CompletudeAno.completo  # casal completo
    assert s25 == CompletudeAno.provisorio  # ainda na janela RFB


def test_regression_workspace_1b9f2cf5_apos_prazo():
    # Mesma estrutura, mas hoje = 1/jul/2026 (após prazo RFB).
    decls = {
        2023: [_make_decl(cpf="***.***.***-60", ano=2023, pj=1)],
        2024: [
            _make_decl(cpf="***.***.***-36", ano=2024, pj=2),
            _make_decl(cpf="***.***.***-60", ano=2024, pj=2),
        ],
        2025: [_make_decl(cpf="***.***.***-36", ano=2025, pj=1, iso=2)],
    }
    s25, motivo = compute_completude(decls, 2025, _HOJE_2026_07)
    # Pós-prazo + MARIANA ausente em 2025 → incompleto.
    assert s25 == CompletudeAno.incompleto
    assert "-60" in (motivo or "")
