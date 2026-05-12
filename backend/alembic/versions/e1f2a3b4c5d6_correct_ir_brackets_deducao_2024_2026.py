"""Corrige ir_brackets.deducao_brl_cents em fiscal_parameters 2024-2026."""

# Revision ID: e1f2a3b4c5d6
# Revises: d0e1f2a3b4c5
# Create Date: 2026-05-12
#
# Bug origem (co-design ADR-197, 2026-05-12): seed A7.2b (migration
# y3z4a5b6c7d8) gravou todas as faixas IRPF 2024-2026 com deducao_brl_cents=0.
# Como nenhum cálculo de IR sobre fiscal_parameters.ir_brackets foi
# materializado ainda (grep confirma que só pgbl_limit_brl_cents e
# inss_ceiling_brl_cents são consumidos), o defeito passou em revisão.
#
# Apurar IR pela fórmula `IR = base × aliq - parcela_a_deduzir` com parcela
# zerada gera tributo até R$ 10k+/declaração acima do correto. Bloqueia card
# Δ contrafactual da ADR-197 (alt. A), relatório de eficiência tributária,
# simulações.
#
# Esta migration preserva vigência e source das rows; só atualiza o JSON.
# Idempotente: rows já corrigidas viram no-op.
#
# Valores (parcela a deduzir, cents, RFB pré-Lei 15.270/2025):
#   0%    → 0          (faixa 1, até R$ 26.963,20)
#   7,5%  → 16944      (faixa 2, até R$ 33.919,80   ≈ R$ 169,44)
#   15%   → 38144      (faixa 3, até R$ 45.012,60   ≈ R$ 381,44)
#   22,5% → 66277      (faixa 4, até R$ 55.976,16   ≈ R$ 662,77)
#   27,5% → 89600      (faixa 5, acima              ≈ R$ 896,00)
#
# FLAG para revisor — escala mensal vs. anual: os valores acima são as
# parcelas a deduzir MENSAIS publicadas pela RFB; o seed atual usa
# upper_brl_cents em escala ANUAL (R$ 26.963,20 = R$ 2.246,93/mês × 12, etc.).
# Para uso direto em `IR_anual = base_anual × aliq - parcela`, a parcela
# correta seria a anualização (×12) — ex. faixa 2: 16944 × 12 = 203328.
# Mantemos os valores literais indicados em co-design; o primeiro consumidor
# (card Δ contrafactual da ADR-197 ou similar) decide entre (a) reescalar
# parcelas para anual ou (b) reescalar brackets para mensal, e materializa
# em ADR follow-up. Confirmar contra fonte autoritativa antes de habilitar
# feature: https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/tabela-progressiva-mensal
#
# Cache: backend/app/services/fiscal_cache.py mantém TTL=1h por ano fiscal.
# Após apply, invalidar fiscal:y=2024/2025/2026 no Redis de produção (ou
# aguardar TTL natural). Cache não é gate de correctness, só de prontidão.

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mapa alíquota_pct (string canônica como gravada no seed) → deducao_brl_cents.
# Source: ADR-197 §5 co-design (2026-05-12). Tabela RFB mensal pré-Lei 15.270/2025.
_DEDUCAO_BY_ALIQUOTA: dict[str, int] = {
    "0.0": 0,
    "7.5": 16944,
    "15.0": 38144,
    "22.5": 66277,
    "27.5": 89600,
}

_AFFECTED_YEARS: tuple[int, ...] = (2024, 2025, 2026)


def upgrade() -> None:
    """Read-modify-write idempotente das rows 2024-2026."""
    if context.is_offline_mode():
        op.execute(
            "-- correct_ir_brackets_deducao skipped in offline mode; "
            "run via online migration on target DB."
        )
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, year, ir_brackets FROM fiscal_parameters WHERE year IN (:y1, :y2, :y3)"
        ),
        {"y1": _AFFECTED_YEARS[0], "y2": _AFFECTED_YEARS[1], "y3": _AFFECTED_YEARS[2]},
    ).fetchall()

    for row_id, year, ir_brackets in rows:
        corrected = _correct_brackets(ir_brackets)
        if corrected is None:
            continue
        bind.execute(
            sa.text("UPDATE fiscal_parameters SET ir_brackets = :ir WHERE id = :id"),
            {"ir": json.dumps(corrected), "id": row_id},
        )


def downgrade() -> None:
    """Restaura deducao_brl_cents=0 (compat operacional; coordenar antes de usar)."""
    if context.is_offline_mode():
        op.execute("-- correct_ir_brackets_deducao downgrade skipped in offline mode.")
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, ir_brackets FROM fiscal_parameters WHERE year IN (:y1, :y2, :y3)"),
        {"y1": _AFFECTED_YEARS[0], "y2": _AFFECTED_YEARS[1], "y3": _AFFECTED_YEARS[2]},
    ).fetchall()

    for row_id, ir_brackets in rows:
        zeroed = _zero_deducoes(ir_brackets)
        if zeroed is None:
            continue
        bind.execute(
            sa.text("UPDATE fiscal_parameters SET ir_brackets = :ir WHERE id = :id"),
            {"ir": json.dumps(zeroed), "id": row_id},
        )


def _parse_ir_brackets(raw: object) -> list[dict] | None:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _correct_brackets(raw_ir_brackets: object) -> list[dict] | None:
    brackets = _parse_ir_brackets(raw_ir_brackets)
    if brackets is None:
        return None

    changed = False
    out: list[dict] = []
    for bracket in brackets:
        if not isinstance(bracket, dict):
            out.append(bracket)
            continue
        aliquota = str(bracket.get("aliquota_pct", ""))
        expected = _DEDUCAO_BY_ALIQUOTA.get(aliquota)
        if expected is None:
            out.append(bracket)
            continue
        new_bracket = dict(bracket)
        if new_bracket.get("deducao_brl_cents") != expected:
            new_bracket["deducao_brl_cents"] = expected
            changed = True
        out.append(new_bracket)
    return out if changed else None


def _zero_deducoes(raw_ir_brackets: object) -> list[dict] | None:
    brackets = _parse_ir_brackets(raw_ir_brackets)
    if brackets is None:
        return None

    changed = False
    out: list[dict] = []
    for bracket in brackets:
        if not isinstance(bracket, dict):
            out.append(bracket)
            continue
        new_bracket = dict(bracket)
        if new_bracket.get("deducao_brl_cents") != 0:
            new_bracket["deducao_brl_cents"] = 0
            changed = True
        out.append(new_bracket)
    return out if changed else None
