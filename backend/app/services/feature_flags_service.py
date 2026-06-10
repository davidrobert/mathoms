"""Feature flags workspace-level — ADR-074 §"Feature flag".

Implementação mínima: flags armazenadas num único ConfigBlob dedicado por
workspace (`type='feature_flags'`). Defaults compilados no código (abaixo
em DEFAULTS) — se a row não existe ou não tem a flag, cai para o default.

Uso típico:
    enabled = await is_enabled(workspace_id, "tasks_v2_enabled", db=db)

Para F8/F9+, flags permitem rollout controlado: Ferreira Campos tem
`tasks_v2_enabled=True` por default (já consumimos em produção), novas
workspaces recebem o default (atualmente True também — pode virar False
em F8.4 se quisermos opt-in para beta testers).

Persistência: só há uma linha por workspace com `key='feature_flags'` e
`value_json={flag: bool, ...}`. Evita proliferação de rows ao adicionar
flag nova.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.models.feature_flag import FeatureFlag

# Defaults de produto. Flags definidas aqui têm efeito imediato no CI
# e em qualquer workspace que ainda não tenha a row persistida.
DEFAULTS: dict[str, bool] = {
    # F8.2 — backlog interativo de tarefas. Em F8.4 (cutover), vira default True
    # para todos. Por enquanto True porque a UI /plano-de-acao já está em produção
    # para Ferreira Campos.
    "tasks_v2_enabled": True,
    # F8.3 — anexos em tarefas. Pode ser False enquanto o quota de storage por
    # workspace não está configurado em produção.
    "task_attachments_enabled": True,
    # F8.3 — snapshot automático de tasks no relatório.
    "report_tasks_snapshot_enabled": True,
    # F8.3 — scan automático de prazos por cron beat.
    "task_deadline_notifications_enabled": True,
    # A12 P3 — learning loop endpoints (ADR-186/188). Default False:
    # gate dogfood (CEO ≥5 regras / 7d) decide cutover global. Por workspace
    # via ``set_flag(..., 'learning_loop_enabled', True)``.
    "learning_loop_enabled": False,
    # ADR-229 — IRPF pre-fill cards no /config → Membros. Default True:
    # blast radius é zero para workspaces sem IRPF processado (endpoint
    # retorna suggestions=[]), e a UI exige clique humano para qualquer
    # ação. Flag permanece como circuit-breaker para desligar por workspace
    # se aparecer bug não-capturado pelos testes.
    "irpf_prefill_enabled": True,
    # ADR-279 · A25.l5 — selo de proveniência N1 + popover N2 no relatório
    # (/reports/[id]). Default False: rollout controlado por workspace
    # (dogfood primeiro); flag off ⇒ relatório idêntico ao atual.
    "report_provenance_enabled": False,
    # ADR-282 — read-path do override casa no natural_key v2 (em vez do legado
    # generate_transaction_hash). Default False: ativado por workspace só após o
    # backfill (slice 3) cobrir 100% + dogfood de reancoragem verde. Enquanto off,
    # os write-paths apenas populam natural_key_hash (dual-write); o match continua
    # no transaction_hash legado.
    "override_natural_key_v2_enabled": False,
}


def _merge_with_defaults(flags_json: Any) -> dict[str, bool]:
    flags: dict[str, bool] = dict(DEFAULTS)
    if isinstance(flags_json, dict):
        for k, v in flags_json.items():
            if k in flags and isinstance(v, bool):
                flags[k] = v
    return flags


async def _get_flags_row(workspace_id: str, *, db: AsyncSession) -> FeatureFlag | None:
    stmt = select(FeatureFlag).where(
        FeatureFlag.workspace_id == workspace_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_flags(workspace_id: str, *, db: AsyncSession) -> dict[str, bool]:
    """Retorna dict com todas as flags aplicáveis ao workspace (defaults
    + overrides). Sempre tem todas as chaves de DEFAULTS."""
    row = await _get_flags_row(workspace_id, db=db)
    return _merge_with_defaults(row.flags_json if row else None)


async def is_enabled(
    workspace_id: str,
    flag: str,
    *,
    db: AsyncSession,
) -> bool:
    """Shortcut para uma flag única. Se a flag não existe em DEFAULTS,
    retorna False (fail-safe)."""
    if flag not in DEFAULTS:
        return False
    flags = await get_flags(workspace_id, db=db)
    return flags.get(flag, False)


def is_enabled_sync(workspace_id: str, flag: str, *, db: Session) -> bool:
    """Variante sync de ``is_enabled`` — learning loop / apply engine / preview
    rodam com ``Session`` (Celery + service layer sync)."""
    if flag not in DEFAULTS:
        return False
    row = db.execute(
        select(FeatureFlag).where(FeatureFlag.workspace_id == workspace_id)
    ).scalar_one_or_none()
    return _merge_with_defaults(row.flags_json if row else None).get(flag, False)


async def set_flag(
    workspace_id: str,
    flag: str,
    enabled: bool,
    *,
    db: AsyncSession,
) -> dict[str, bool]:
    """Persiste mudança. Cria a row de config_blob se não existe.
    Só aceita flags de DEFAULTS (fail-safe contra typos)."""
    if flag not in DEFAULTS:
        raise ValueError(f"Flag desconhecida: {flag}")
    row = await _get_flags_row(workspace_id, db=db)
    if row is None:
        row = FeatureFlag(
            workspace_id=workspace_id,
            flags_json={flag: enabled},
        )
        db.add(row)
    else:
        current: dict[str, Any] = dict(row.flags_json or {})
        current[flag] = enabled
        row.flags_json = current
        db.add(row)
    await db.flush()
    return await get_flags(workspace_id, db=db)


__all__ = ["DEFAULTS", "get_flags", "is_enabled", "is_enabled_sync", "set_flag"]
