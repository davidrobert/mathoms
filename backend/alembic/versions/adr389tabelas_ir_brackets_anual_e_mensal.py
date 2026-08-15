"""ADR-389 · A40.l56 — ir_brackets vira duas tabelas importadas, com proveniência.

O seed A7.2b gravou UMA constante para 2024/2025/2026, com tetos ANUAIS e
parcelas MENSAIS na mesma estrutura. Nem reescalar parcelas nem reescalar tetos
resolve: a RFB publica duas tabelas distintas, e a anual não é 12× a mensal (em
ano de transição é mistura ponderada por mês; em ano limpo diverge por
arredondamento). Ver ADR-389.

Expand puro: as colunas novas são nullable e `ir_brackets` fica intacta. O
contract sai em lane própria, depois que nenhum leitor a use.

Revision ID: adr389tabelas
Revises: adr387pr2snap
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "adr389tabelas"
down_revision: Union[str, None] = "adr387pr2snap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# As seis tabelas, verbatim. Fonte e nível de verificação por tabela.
#
# ATENÇÃO ao alterar: `dev/check_fiscal_brackets_continuity.py` importa ESTAS
# constantes e aplica os invariantes da ADR-389 D3 sobre elas. Não duplique os
# valores em teste — o gate lê os bytes que esta migration grava.
# ---------------------------------------------------------------------------

_VERIFICACAO = "portal RFB + convergência adversarial; texto do ato não lido (A40.l56)"


def _faixas(linhas):
    return [{"upper_brl_cents": u, "aliquota_pct": a, "deducao_brl_cents": d} for a, u, d in linhas]


# Mensal vigente ao FIM de cada ano-calendário. Janeiro/2024 (isento 2.112,00) e
# jan-abr/2025 (isento 2.259,20) NÃO estão representados — vigência intra-anual
# é não-objetivo da ADR-389, e o leitor recusa ≥2 rows no mesmo período.
_MENSAL_2024 = _faixas(
    [
        ("0.0", 225920, 0),
        ("7.5", 282665, 16944),
        ("15.0", 375105, 38144),
        ("22.5", 466468, 66277),
        ("27.5", None, 89600),
    ]
)
# MP 1.294/2025 (Lei 15.191/2025) — vigora ininterruptamente desde 01/05/2025,
# e a Lei 15.270/2025 não a alterou. Por isso 2025 e 2026 são idênticas: é o
# dado correto, não cópia (ADR-389 §Correção de 2026-08-15).
_MENSAL_2025_2026 = _faixas(
    [
        ("0.0", 242880, 0),
        ("7.5", 282665, 18216),
        ("15.0", 375105, 39416),
        ("22.5", 466468, 67549),
        ("27.5", None, 90873),
    ]
)

_ANUAL_2024 = _faixas(
    [
        ("0.0", 2696320, 0),
        ("7.5", 3391980, 202224),
        ("15.0", 4501260, 456623),
        ("22.5", 5597616, 794217),
        ("27.5", None, 1074098),
    ]
)
_ANUAL_2025 = _faixas(
    [
        ("0.0", 2846720, 0),
        ("7.5", 3391980, 213504),
        ("15.0", 4501260, 467903),
        ("22.5", 5597616, 805497),
        ("27.5", None, 1085378),
    ]
)
_ANUAL_2026 = _faixas(
    [
        ("0.0", 2914560, 0),
        ("7.5", 3391980, 218592),
        ("15.0", 4501260, 472991),
        ("22.5", 5597616, 810585),
        ("27.5", None, 1090466),
    ]
)

_TRANSICAO_2024 = (
    "anual é mistura ponderada por mês: 2.112,00×1 (jan, Lei 14.663/2023) + "
    "2.259,20×11 (fev-dez, MP 1.206/2024) = 26.963,20"
)
_TRANSICAO_2025 = (
    "anual é mistura ponderada por mês: 2.259,20×4 (jan-abr) + "
    "2.428,80×8 (mai-dez, MP 1.294/2025) = 28.467,20"
)

TABELAS_POR_ANO: dict[int, dict] = {
    2024: {
        "anual": {
            "faixas": _ANUAL_2024,
            "vigencia_ref": "Tabela progressiva anual do ajuste — 'exercício de 2025, "
            "ano-calendário de 2024'. IN RFB 2.174, de 14/02/2024.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": _TRANSICAO_2024,
        },
        "mensal": {
            "faixas": _MENSAL_2024,
            "vigencia_ref": "Tabela progressiva mensal (IRRF) — 'a partir do mês de "
            "fevereiro do ano-calendário de 2024'. MP 1.206/2024, convertida na Lei "
            "14.848/2024. Janeiro/2024 não está representado.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": _TRANSICAO_2024,
        },
        "regime_completo": True,
        "componentes_ausentes": [],
    },
    2025: {
        "anual": {
            "faixas": _ANUAL_2025,
            "vigencia_ref": "Tabela progressiva anual do ajuste — 'Exercício de 2026, "
            "ano-calendário de 2025'. IN RFB 2.299, de 17/12/2025.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": _TRANSICAO_2025,
        },
        "mensal": {
            "faixas": _MENSAL_2025_2026,
            "vigencia_ref": "Tabela progressiva mensal (IRRF) — 'maio/2025 em diante'. "
            "MP 1.294/2025, convertida na Lei 15.191/2025. Jan-abr/2025 não está "
            "representado.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": _TRANSICAO_2025,
        },
        "regime_completo": True,
        "componentes_ausentes": [],
    },
    2026: {
        "anual": {
            "faixas": _ANUAL_2026,
            "vigencia_ref": "Tabela progressiva anual do ajuste — 'a partir do "
            "exercício de 2027, ano-calendário de 2026'. IN RFB 2.299, de 17/12/2025.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": "",
        },
        "mensal": {
            "faixas": _MENSAL_2025_2026,
            "vigencia_ref": "Tabela de Incidência Mensal a partir de janeiro de 2026 — "
            "geometria da MP 1.294/2025 mantida; a Lei 15.270/2025 não alterou faixas "
            "nem parcelas. IN RFB 2.299, de 17/12/2025.",
            "source": _VERIFICACAO,
            "motivo_divergencia_x12": "",
        },
        # A Lei 15.270/2025 criou redutor (função do rendimento BRUTO) e IRPFM,
        # que não são faixas e quebram a diferencial ingênua do D5 da ADR-375.
        # A recusa lê esta flag — nunca `if year >= 2026`. Dono: [[A40.l64]].
        "regime_completo": False,
        "componentes_ausentes": ["redutor_lei_15270", "irpfm"],
    },
}


def _table() -> sa.Table:
    return sa.table(
        "fiscal_parameters",
        sa.column("id", sa.String),
        sa.column("year", sa.Integer),
        sa.column("ir_brackets_anual", sa.JSON),
        sa.column("ir_brackets_mensal", sa.JSON),
        sa.column("regime_completo", sa.Boolean),
        sa.column("componentes_ausentes", sa.JSON),
    )


_COLUNAS_NOVAS = (
    ("ir_brackets_anual", sa.JSON(), True, None),
    ("ir_brackets_mensal", sa.JSON(), True, None),
    ("regime_completo", sa.Boolean(), False, sa.true()),
    ("componentes_ausentes", sa.JSON(), True, None),
)


def _add_columns() -> None:
    # `batch_alter_table` recria a tabela e não é emitível em `--sql` (SQLite).
    # ADD COLUMN é; o afrouxamento de `ir_brackets` para nullable não é, e fica
    # anotado no script para o DBA aplicar.
    if context.is_offline_mode():
        for nome, tipo, null, default in _COLUNAS_NOVAS:
            op.add_column(
                "fiscal_parameters",
                sa.Column(nome, tipo, nullable=null, server_default=default),
            )
        op.execute("-- ADR-389: 'ir_brackets' deve virar NULLABLE — aplicar no DB alvo.")
        return
    with op.batch_alter_table("fiscal_parameters") as batch:
        for nome, tipo, null, default in _COLUNAS_NOVAS:
            batch.add_column(sa.Column(nome, tipo, nullable=null, server_default=default))
        batch.alter_column("ir_brackets", existing_type=sa.JSON(), nullable=True)


def _exige_cobertura(anos_no_banco: set) -> None:
    nao_cobertos = anos_no_banco - set(TABELAS_POR_ANO)
    if nao_cobertos:
        # Abortar, não pular. Row sem tabela nova é row que o leitor novo lê como
        # ausente — e ausência silenciosa foi o que produziu o defeito original.
        raise RuntimeError(
            f"fiscal_parameters tem anos sem tabela nesta migration: {sorted(nao_cobertos)}; "
            f"cobertos: {sorted(TABELAS_POR_ANO)}"
        )


def _backfill(bind) -> None:
    tabela = _table()
    anos_no_banco = {r[0] for r in bind.execute(sa.text("SELECT year FROM fiscal_parameters"))}
    _exige_cobertura(anos_no_banco)
    for year, dados in TABELAS_POR_ANO.items():
        if year not in anos_no_banco:
            continue
        bind.execute(
            tabela.update()
            .where(tabela.c.year == year)
            .values(
                ir_brackets_anual=dados["anual"],
                ir_brackets_mensal=dados["mensal"],
                regime_completo=dados["regime_completo"],
                componentes_ausentes=dados["componentes_ausentes"],
            )
        )


def upgrade() -> None:
    _add_columns()
    if context.is_offline_mode():
        # Backfill precisa ler os anos existentes; em --sql não há conexão.
        return
    _backfill(op.get_bind())


def downgrade() -> None:
    with op.batch_alter_table("fiscal_parameters") as batch:
        batch.drop_column("componentes_ausentes")
        batch.drop_column("regime_completo")
        batch.drop_column("ir_brackets_mensal")
        batch.drop_column("ir_brackets_anual")
        # `ir_brackets` volta a NOT NULL: `e1f2a3b4c5d6.downgrade()` faz
        # `SELECT id, ir_brackets` e a coluna precisa existir preenchida. Este
        # upgrade nunca a esvazia, então a reversão é segura.
        batch.alter_column("ir_brackets", existing_type=sa.JSON(), nullable=False)
