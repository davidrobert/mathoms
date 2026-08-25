"""ADR-414 D3 — redutor da Lei 15.270/2025 co-localizado na row fiscal.

O redutor indexa o rendimento BRUTO; a tabela progressiva indexa a BASE. São duas
variáveis, e por isso o redutor não cabe em `ir_brackets`. Fica na MESMA row porque
`regime_completo` afirma sobre ela: em tabela própria, virar `true` seria afirmação
sobre outra tabela com outra vigência.

Vigência assimétrica, e é ela que impede o desarme do D5 para anos antigos: o
redutor MENSAL vale de 01/01/2026; o ANUAL só a partir do exercício 2027 (AC2026).
AC <= 2025 fica com o VO zerado — que o parser lê como "não há redutor", nunca
como "não carregou".

Revision ID: adr414redutor
Revises: adr411locator
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr414redutor"
down_revision: Union[str, None] = "adr411locator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Conferidos em fonte primária no co-design de 2026-08-24 (RFB, orientação de
# dez/2025 + Exemplos de Aplicação nº 4, que fixa a base no rendimento BRUTO).
# O teto de cada banda NÃO é coluna: é o imposto no piso, propriedade derivada —
# armazená-lo deixaria a row capaz de discordar de si mesma.
_VERIFICACAO = "RFB orientação 2025-12 + Exemplos de Aplicação; texto do ato não lido (A40.l64)"

_ANUAL_2026 = {
    "piso_bruto_brl_cents": 6_000_000,
    "teto_bruto_brl_cents": 8_820_000,
    "intercepto_brl_cents": 842_973,
    "coeficiente": "0.095575",
    "vigencia_ref": "Lei 15.270/2025 — ajuste anual, a partir do exercício de 2027 "
    "(ano-calendário de 2026). Art. 11-A da Lei 9.250/1995.",
    "source": _VERIFICACAO,
}

_MENSAL_2026 = {
    "piso_bruto_brl_cents": 500_000,
    "teto_bruto_brl_cents": 735_000,
    "intercepto_brl_cents": 97_862,
    "coeficiente": "0.133145",
    "vigencia_ref": "Lei 15.270/2025 — retenção mensal, rendimentos pagos a partir "
    "de 01/01/2026.",
    "source": _VERIFICACAO,
}

#: Só AC2026. 2024 e 2025 ficam sem redutor — e é isso que preserva o D5 lá.
REDUTOR_POR_ANO = {2026: {"anual": _ANUAL_2026, "mensal": _MENSAL_2026}}

_COLUNAS = (("redutor_anual", sa.JSON()), ("redutor_mensal", sa.JSON()))


def _table() -> sa.Table:
    return sa.table(
        "fiscal_parameters",
        sa.column("year", sa.Integer),
        sa.column("redutor_anual", sa.JSON),
        sa.column("redutor_mensal", sa.JSON),
    )


def _add_columns() -> None:
    if context.is_offline_mode():
        for nome, tipo in _COLUNAS:
            op.add_column("fiscal_parameters", sa.Column(nome, tipo, nullable=True))
        return
    with op.batch_alter_table("fiscal_parameters") as batch:
        for nome, tipo in _COLUNAS:
            batch.add_column(sa.Column(nome, tipo, nullable=True))


def upgrade() -> None:
    _add_columns()
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    tabela = _table()
    anos = {r[0] for r in bind.execute(sa.text("SELECT year FROM fiscal_parameters"))}
    for year, dados in REDUTOR_POR_ANO.items():
        if year not in anos:
            continue
        bind.execute(
            tabela.update()
            .where(tabela.c.year == year)
            .values(redutor_anual=dados["anual"], redutor_mensal=dados["mensal"])
        )


def downgrade() -> None:
    with op.batch_alter_table("fiscal_parameters") as batch:
        batch.drop_column("redutor_mensal")
        batch.drop_column("redutor_anual")
