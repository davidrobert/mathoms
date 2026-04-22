"""Gerador de ``docs/DB_SCHEMA_REFERENCE.md`` (A6f.4 · ADR-102 R20).

Introspecciona ``Base.metadata`` após importar todos os models em
``backend/app/models/`` e emite um markdown determinístico com:

- Todas as tabelas (ordem alfabética), colunas, tipos SQL, nullability,
  defaults, constraints (PK/FK/UK/CHECK) e indexes.
- Equivalentes Go por tabela — struct + ``db`` / ``json`` tags — para
  servir de referência em uma migração Go futura.
- Auditoria de 3 categorias de risco cross-schema:
  1. Uso de ``PickleType`` / ``TypeDecorator`` (bloqueante).
  2. Enums como ``SQLAlchemy Enum`` nativo vs ``VARCHAR + CHECK``.
  3. Timestamps ``DateTime`` naive vs ``DateTime(timezone=True)``.

O output é determinístico: mesma entrada = mesmo byte output. O teste
``backend/tests/test_db_schema_reference_snapshot.py`` compara o doc em
disco com o output atual.

Rode via ``make update-db-schema-reference`` ou direto:
``python dev/generate_db_schema_reference.py > docs/DB_SCHEMA_REFERENCE.md``.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.environ.setdefault(
    "MATHOMS_FERNET_KEY",
    "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=",
)

from sqlalchemy import (  # noqa: E402
    CheckConstraint,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    Table,
    UniqueConstraint,
)
from sqlalchemy.types import JSON, DateTime, Enum, PickleType, TypeDecorator  # noqa: E402

# Trigger model registration.
import backend.app.models  # noqa: E402,F401
from backend.app.core.database import Base  # noqa: E402

SNAPSHOT_PATH = _REPO_ROOT / "docs" / "DB_SCHEMA_REFERENCE.md"


# ---------------------------------------------------------------------------
# SQL type → Go type mapping (A6f.4 · R20)
# ---------------------------------------------------------------------------


_PLURAL_OVERRIDES = {
    "audit_logs": "AuditLog",
    "bank_accounts": "BankAccount",
    "categories": "Category",
    "category_keywords": "CategoryKeyword",
    "documents": "Document",
    "family_members": "FamilyMember",
    "feature_flags": "FeatureFlag",
    "goals": "Goal",
    "institution_configs": "InstitutionConfig",
    "llm_configs": "LLMConfig",
    "notifications": "Notification",
    "password_vault": "PasswordVault",
    "pipeline_artifacts": "PipelineArtifact",
    "pipeline_configs": "PipelineConfig",
    "pipeline_runs": "PipelineRun",
    "pipeline_stage_logs": "PipelineStageLog",
    "report_layouts": "ReportLayout",
    "reports": "Report",
    "stage_reviews": "StageReview",
    "task_attachments": "TaskAttachment",
    "task_suggestions": "TaskSuggestion",
    "tasks": "Task",
    "transaction_overrides": "TransactionOverride",
    "users": "User",
    "workspace_invitations": "WorkspaceInvitation",
    "workspace_members": "WorkspaceMember",
    "workspaces": "Workspace",
}


def _go_ident(name: str) -> str:
    """Convert snake_case column name to Go PascalCase."""
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _sql_to_go(sa_type, nullable: bool) -> str:
    """Map SQLAlchemy column type to Go struct field type.

    Pointers (``*T``) são usados para colunas nullable — distinguem NULL de
    zero-value. JSON vira ``json.RawMessage`` (nil quando NULL).
    """
    sa_str = str(sa_type).upper()

    if isinstance(sa_type, JSON):
        return "json.RawMessage"
    if isinstance(sa_type, Enum):
        base = "string"
    elif "BIGINT" in sa_str:
        base = "int64"
    elif "INTEGER" in sa_str or sa_str == "INT":
        base = "int"
    elif "BOOLEAN" in sa_str or "BOOL" in sa_str:
        base = "bool"
    elif "FLOAT" in sa_str or "REAL" in sa_str:
        base = "float64"
    elif "NUMERIC" in sa_str or "DECIMAL" in sa_str:
        base = "decimal.Decimal"
    elif "DATETIME" in sa_str or "TIMESTAMP" in sa_str:
        base = "time.Time"
    elif sa_str == "DATE":
        base = "time.Time"
    elif "VARCHAR" in sa_str or "CHAR" in sa_str or sa_str == "TEXT":
        base = "string"
    else:
        base = "string"  # conservative fallback

    if nullable and base not in {"json.RawMessage"}:
        return f"*{base}"
    return base


def _go_struct_name(tablename: str) -> str:
    """Map table → Go struct name. Overrides explícitos pra evitar
    pluralização ruim (``categories`` → ``Categorie``).
    """
    if tablename in _PLURAL_OVERRIDES:
        return _PLURAL_OVERRIDES[tablename]
    singular = tablename[:-1] if tablename.endswith("s") else tablename
    return "".join(part[:1].upper() + part[1:] for part in singular.split("_") if part)


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------


def _column_default(col) -> str:
    if col.server_default is not None:
        txt = getattr(col.server_default, "arg", col.server_default)
        return f"server: `{txt}`"
    if col.default is None:
        return ""
    default = col.default
    if getattr(default, "is_callable", False):
        callee = default.arg
        name = getattr(callee, "__name__", repr(callee))
        return f"callable: `{name}`"
    arg = getattr(default, "arg", default)
    return f"`{arg!r}`"


def _column_tags(col, table: Table) -> list[str]:
    tags: list[str] = []
    if col.primary_key:
        tags.append("PK")
    for fk in col.foreign_keys:
        tags.append(f"FK→{fk.target_fullname}")
    if col.unique:
        tags.append("UNIQUE")
    if col.index:
        tags.append("INDEX")
    return tags


def _format_constraint(c) -> str | None:
    if isinstance(c, PrimaryKeyConstraint):
        cols = ", ".join(col.name for col in c.columns)
        return f"PRIMARY KEY ({cols})"
    if isinstance(c, ForeignKeyConstraint):
        local = ", ".join(col.name for col in c.columns)
        remote = ", ".join(e.target_fullname for e in c.elements)
        name = c.name or "(unnamed)"
        ondelete = f" ON DELETE {c.ondelete}" if c.ondelete else ""
        onupdate = f" ON UPDATE {c.onupdate}" if c.onupdate else ""
        return f"FOREIGN KEY ({local}) REFERENCES {remote}{ondelete}{onupdate} — `{name}`"
    if isinstance(c, UniqueConstraint):
        cols = ", ".join(col.name for col in c.columns)
        name = c.name or "(unnamed)"
        return f"UNIQUE ({cols}) — `{name}`"
    if isinstance(c, CheckConstraint):
        name = c.name or "(unnamed)"
        return f"CHECK (`{c.sqltext}`) — `{name}`"
    return None


def _render_table_block(table: Table) -> str:
    buf = io.StringIO()
    buf.write(f"### `{table.name}`\n\n")

    buf.write("| Column | Type | Nullable | Default | Tags |\n")
    buf.write("|---|---|---|---|---|\n")
    for col in table.columns:
        typ = str(col.type)
        nullable = "yes" if col.nullable else "no"
        default = _column_default(col)
        tags = ", ".join(_column_tags(col, table)) or "—"
        buf.write(f"| `{col.name}` | `{typ}` | {nullable} | {default or '—'} | {tags} |\n")
    buf.write("\n")

    constraints = []
    for c in table.constraints:
        formatted = _format_constraint(c)
        if formatted is None:
            continue
        if isinstance(c, PrimaryKeyConstraint) and len(c.columns) == 1:
            continue
        constraints.append(formatted)
    if constraints:
        buf.write("**Constraints:**\n\n")
        for line in sorted(constraints):
            buf.write(f"- {line}\n")
        buf.write("\n")

    indexes = sorted(table.indexes, key=lambda ix: ix.name or "")
    if indexes:
        buf.write("**Indexes:**\n\n")
        for ix in indexes:
            cols = ", ".join(col.name for col in ix.columns)
            unique = "UNIQUE " if ix.unique else ""
            buf.write(f"- {unique}`{ix.name}` ({cols})\n")
        buf.write("\n")

    return buf.getvalue()


def _render_go_block(table: Table) -> str:
    struct = _go_struct_name(table.name)
    buf = io.StringIO()
    buf.write(f"### `{table.name}` → `type {struct} struct`\n\n")
    buf.write("```go\n")
    buf.write(f"type {struct} struct {{\n")
    for col in table.columns:
        field_name = _go_ident(col.name)
        go_type = _sql_to_go(col.type, col.nullable)
        tag = f'`db:"{col.name}" json:"{col.name}"`'
        buf.write(f"\t{field_name} {go_type} {tag}\n")
    buf.write("}\n")
    buf.write("```\n\n")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@dataclass
class AuditReport:
    pickle_or_typedecorator: list[str] = field(default_factory=list)
    native_enums: list[str] = field(default_factory=list)
    naive_datetimes: list[str] = field(default_factory=list)
    json_columns: list[str] = field(default_factory=list)


def _audit(tables: Iterable[Table]) -> AuditReport:
    report = AuditReport()
    for table in tables:
        for col in table.columns:
            t = col.type
            if isinstance(t, PickleType) or isinstance(t, TypeDecorator):
                report.pickle_or_typedecorator.append(
                    f"{table.name}.{col.name} ({type(t).__name__})"
                )
            if isinstance(t, Enum):
                values = ", ".join(sorted(t.enums or []))
                report.native_enums.append(f"{table.name}.{col.name} → ({values})")
            if isinstance(t, DateTime) and not t.timezone:
                report.naive_datetimes.append(f"{table.name}.{col.name}")
            if isinstance(t, JSON):
                report.json_columns.append(f"{table.name}.{col.name}")
    return report


def _render_audit(report: AuditReport) -> str:
    buf = io.StringIO()
    buf.write("## Auditoria de risco (A6f.4 · R20)\n\n")
    buf.write(
        "Três categorias que quebram portabilidade language-neutral. "
        "Zero ocorrências nas 3 primeiras é o alvo; listagens positivas "
        "indicam trabalho pendente.\n\n"
    )

    buf.write("### 1. `PickleType` / `TypeDecorator` exótico (bloqueante)\n\n")
    if not report.pickle_or_typedecorator:
        buf.write("✅ **Zero ocorrências.** Schema é 100% nativo SQL.\n\n")
    else:
        for item in sorted(report.pickle_or_typedecorator):
            buf.write(f"- ⚠️ `{item}`\n")
        buf.write("\n")

    buf.write("### 2. Timestamps naive (sem `timezone=True`)\n\n")
    if not report.naive_datetimes:
        buf.write(
            "✅ **Zero ocorrências.** Todos os `DateTime` usam `timezone=True` "
            "(UTC-aware em Python, `TIMESTAMP WITH TIME ZONE` no SQL quando o "
            "dialeto suporta).\n\n"
        )
    else:
        for item in sorted(report.naive_datetimes):
            buf.write(f"- ⚠️ `{item}`\n")
        buf.write("\n")

    buf.write("### 3. Enums — nativo SQLAlchemy `Enum` vs `VARCHAR + CHECK`\n\n")
    if not report.native_enums:
        buf.write("✅ Nenhum enum nativo. Todos os status/role são `VARCHAR`.\n\n")
    else:
        buf.write(
            "Schema usa `SQLAlchemy Enum()` nativo (Python enum → DB enum ou "
            "`VARCHAR + CHECK` dependendo do dialect). Em Postgres vira um "
            "TYPE real; em SQLite degrada para `VARCHAR + CHECK`. Portável "
            "para Go via tipo alias `type Status string` + constantes.\n\n"
        )
        for item in sorted(report.native_enums):
            buf.write(f"- `{item}`\n")
        buf.write("\n")

    buf.write("### 4. Colunas JSON (observação, não risco)\n\n")
    if not report.json_columns:
        buf.write("Nenhuma coluna JSON.\n\n")
    else:
        buf.write(
            "Campos JSON exigem schema explícito (documentado em "
            "`config/schemas/*.json` ou docstring do model) para serem "
            "portáveis cross-language.\n\n"
        )
        for item in sorted(report.json_columns):
            buf.write(f"- `{item}`\n")
        buf.write("\n")

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate() -> str:
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)

    out = io.StringIO()
    out.write("# DB Schema Reference — Mathoms AI\n\n")
    out.write(
        "> **Auto-gerado** por `dev/generate_db_schema_reference.py`. "
        "Não edite manualmente — rode `make update-db-schema-reference` e "
        "comite o diff.\n\n"
    )
    out.write(
        "Referência canônica de schema do banco. Cobre todos os models "
        "registrados em `backend/app/models/` via `Base.metadata`.\n\n"
    )
    out.write(f"**Total de tabelas:** {len(tables)}\n\n")
    out.write("---\n\n")

    out.write("## Índice\n\n")
    for table in tables:
        out.write(f"- [`{table.name}`](#{table.name.replace('_', '')})\n")
    out.write("\n---\n\n")

    out.write("## Tabelas\n\n")
    for table in tables:
        out.write(_render_table_block(table))
    out.write("---\n\n")

    out.write(_render_audit(_audit(tables)))
    out.write("---\n\n")

    out.write("## Equivalentes Go (referência para migração futura)\n\n")
    out.write(
        "Mapeamento mecânico de cada tabela para `type XXX struct`. "
        "Nullable vira ponteiro (`*T`). `JSON` vira `json.RawMessage`. "
        "`DateTime(timezone=True)` vira `time.Time`. `Numeric` vira "
        "`decimal.Decimal` (pacote `github.com/shopspring/decimal`).\n\n"
    )
    out.write(
        "> **Nota sobre convenções idiomáticas Go.** Field names usam "
        "PascalCase simples (`Id`, `IpAddress`, `JsonField`). Na migração "
        "real, ajustar para `ID`, `IPAddress`, `JSONField` (ver "
        "[Effective Go — MixedCaps](https://go.dev/doc/effective_go#mixed-caps)). "
        "Este doc é **referência estrutural**, não codegen final.\n\n"
    )
    out.write("Imports sugeridos:\n\n")
    out.write("```go\n")
    out.write("import (\n")
    out.write('\t"encoding/json"\n')
    out.write('\t"time"\n\n')
    out.write('\t"github.com/shopspring/decimal"\n')
    out.write(")\n")
    out.write("```\n\n")
    for table in tables:
        out.write(_render_go_block(table))

    # Normaliza EOF: um único '\n' final (paridade com end-of-file-fixer do
    # pre-commit; sem isso, o snapshot test oscila entre gerar/comitar).
    return out.getvalue().rstrip("\n") + "\n"


def main() -> int:
    content = generate()
    if "--check" in sys.argv:
        current = SNAPSHOT_PATH.read_text(encoding="utf-8") if SNAPSHOT_PATH.exists() else ""
        if current != content:
            sys.stderr.write(
                "DB_SCHEMA_REFERENCE.md desatualizado. Rode "
                "`make update-db-schema-reference` e comite o diff.\n"
            )
            return 1
        return 0
    sys.stdout.write(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
