"""backfill workspace_category_overrides from existing categories (A7.3 · ADR-137)

Revision ID: d8e9f0a1b2c3
Revises: b6c7d8e9f0a1
Create Date: 2026-04-27

Para cada row existente em ``categories``, compara com o template v1 e
cria entrada em ``workspace_category_overrides`` somente onde diverge
(label/keywords/cap). Workspaces com 0 customização → 0 overrides;
workspaces que já tinham edições mantêm as customizações via
override.

Idempotente: skip silencioso se override já existe para
(workspace_id, template_key).

**Não dropa** ``categories`` / ``category_keywords`` — A7.5 fará o
cleanup após verificação humana de paridade.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEMPLATE_VERSION = 1


def upgrade() -> None:
    if context.is_offline_mode():
        op.execute(
            "-- A7.3 backfill (workspace_category_overrides) skipped in offline mode."
        )
        return

    bind = op.get_bind()
    template_by_key = _load_template(bind)
    if not template_by_key:
        # template ainda não seedado (ex.: bootstrap fora-de-ordem) — sem-op.
        return

    existing_pairs = _existing_override_pairs(bind)
    cat_rows = _load_existing_categories(bind)

    override_table = sa.table(
        "workspace_category_overrides",
        sa.column("id", sa.String),
        sa.column("workspace_id", sa.String),
        sa.column("template_key", sa.String),
        sa.column("label_override", sa.String),
        sa.column("keywords_override", sa.JSON),
        sa.column("monthly_cap_brl_cents_override", sa.BigInteger),
        sa.column("disabled", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    rows_to_insert: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for cat in cat_rows:
        ws_id = cat["workspace_id"]
        code = cat["code"]
        if code not in template_by_key:
            # categoria custom que não existe no template — sem destino
            # canônico ainda; A7.5 decide migração explícita.
            continue
        if (ws_id, code) in existing_pairs:
            continue
        diff = _compute_diff(cat, template_by_key[code])
        if diff is None:
            continue
        rows_to_insert.append(_make_override_row(ws_id, code, diff, now))

    if rows_to_insert:
        op.bulk_insert(override_table, rows_to_insert)


def _load_template(bind) -> dict[str, dict[str, Any]]:
    try:
        result = bind.execute(
            sa.text(
                "SELECT key, label, default_keywords, default_monthly_cap_brl_cents "
                "FROM category_templates WHERE template_version = :v"
            ),
            {"v": _TEMPLATE_VERSION},
        ).fetchall()
    except Exception:
        return {}
    return {
        r[0]: {
            "label": r[1],
            "keywords": _normalize_keywords(r[2]),
            "monthly_cap_brl_cents": r[3],
        }
        for r in result
    }


def _load_existing_categories(bind) -> list[dict[str, Any]]:
    try:
        result = bind.execute(
            sa.text(
                "SELECT id, workspace_id, code, name, monthly_cap "
                "FROM categories"
            )
        ).fetchall()
    except Exception:
        return []
    rows = []
    for r in result:
        cat_id = r[0]
        kw_rows = bind.execute(
            sa.text(
                "SELECT keyword FROM category_keywords WHERE category_id = :cid"
            ),
            {"cid": cat_id},
        ).fetchall()
        rows.append(
            {
                "id": cat_id,
                "workspace_id": r[1],
                "code": r[2],
                "name": r[3],
                "monthly_cap_brl_cents": _float_to_cents(r[4]),
                "keywords": [kr[0] for kr in kw_rows],
            }
        )
    return rows


def _existing_override_pairs(bind) -> set[tuple[str, str]]:
    try:
        result = bind.execute(
            sa.text(
                "SELECT workspace_id, template_key FROM workspace_category_overrides"
            )
        ).fetchall()
        return {(r[0], r[1]) for r in result}
    except Exception:
        return set()


def _compute_diff(
    cat: dict[str, Any], tmpl: dict[str, Any]
) -> dict[str, Any] | None:
    """Retorna ``None`` se categoria == template (sem override necessário)."""
    label_diff = (
        cat["name"] if cat["name"] != tmpl["label"] else None
    )
    keywords_diff = (
        list(cat["keywords"])
        if list(cat["keywords"]) != list(tmpl["keywords"])
        else None
    )
    cap_diff = (
        cat["monthly_cap_brl_cents"]
        if cat["monthly_cap_brl_cents"] != tmpl["monthly_cap_brl_cents"]
        else None
    )
    if label_diff is None and keywords_diff is None and cap_diff is None:
        return None
    return {
        "label_override": label_diff,
        "keywords_override": keywords_diff,
        "monthly_cap_brl_cents_override": cap_diff,
    }


def _make_override_row(
    ws_id: str, template_key: str, diff: dict[str, Any], now: datetime
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "workspace_id": ws_id,
        "template_key": template_key,
        "label_override": diff["label_override"],
        "keywords_override": diff["keywords_override"],
        "monthly_cap_brl_cents_override": diff["monthly_cap_brl_cents_override"],
        "disabled": False,
        "created_at": now,
        "updated_at": now,
    }


def _normalize_keywords(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return list(raw)


def _float_to_cents(value: Any) -> int | None:
    """``categories.monthly_cap`` é Float legado; converte para cents (ADR-090)."""
    if value is None:
        return None
    return int(round(float(value) * 100))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM workspace_category_overrides"))
