"""AuditService — helper para registrar eventos de auditoria.

Uso típico dentro de um endpoint:

    from backend.app.services.audit import audit_log, AuditAction

    await audit_log(
        db,
        action=AuditAction.document_upload,
        resource_type="document",
        resource_id=doc.id,
        workspace_id=ws.id,
        actor_user_id=user.id,
        request=request,  # opcional, captura IP + UA
        details={"filename": filename, "size_bytes": size, "content_hash": h},
    )

Observações:
- O `db.commit()` final continua sendo do chamador — o audit_log faz apenas
  `db.add()` para que o insert participe da transação do endpoint e role
  junto se algo falhar.
- Para jobs em background (Celery), passe `request=None` e use a sessão
  síncrona do worker.
"""

from __future__ import annotations

import enum
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog


class AuditAction(str, enum.Enum):
    """Enum canônico de ações auditáveis.

    Convenção: `<recurso>.<verbo>` — facilita filtrar por prefixo.
    Adicione novas ações aqui à medida que novas rotas sensíveis forem
    criadas (auth, config, pipeline, …).
    """

    # Documentos
    document_upload = "document.upload"
    document_delete = "document.delete"
    document_retry_unlock = "document.retry_unlock"
    document_update_classification = "document.update_classification"

    # Storage / workspace
    workspace_purge = "workspace.purge"
    workspace_export = "workspace.export"

    # Auth (reservado para quando for instrumentado)
    auth_login = "auth.login"
    auth_login_failed = "auth.login_failed"
    auth_logout = "auth.logout"

    # Vault
    vault_password_add = "vault.password.add"
    vault_password_delete = "vault.password.delete"

    # LGPD self-service (Art. 18 — direitos do titular)
    lgpd_export_requested = "lgpd.export_requested"
    lgpd_export_ready = "lgpd.export_ready"
    lgpd_export_failed = "lgpd.export_failed"
    lgpd_export_downloaded = "lgpd.export_downloaded"
    lgpd_export_expired = "lgpd.export_expired"
    lgpd_deletion_requested = "lgpd.deletion_requested"
    lgpd_deletion_canceled = "lgpd.deletion_canceled"
    lgpd_deletion_completed = "lgpd.deletion_completed"

    # LGPD Art. 37 — auditoria de acesso a leitura de dado sensível (ADR-275)
    report_read = "report.read"
    report_download = "report.download"
    transactions_read = "transactions.read"
    transactions_export = "transactions.export"
    family_member_read = "family_member.read"
    document_read = "document.read"
    document_download = "document.download"
    cpf_view_full = "cpf.view_full"

    # Meta — purge de retenção de audit de leitura (ADR-275 D5; retido, não purgado)
    audit_purge = "audit.purge"

    # Override natural_key v2 — snapshot do gate da M2 destrutiva (ADR-282 §Emenda / A26.l4).
    # Mutação-adjacente (evidência de gate): NÃO entra em READ_ACCESS_ACTIONS → sobrevive ao purge.
    override_v2_dualread_snapshot = "override.v2_dualread_snapshot"

    # Supersessão de PropertyIdentity — merge de override com classificações
    # divergentes (ADR-324). Mutação: sobrevive ao purge de leitura.
    property_override_supersession_merge = "property_override.supersession_merge"


# Ações de **leitura** (Art.37) — retenção 365d, purgadas por
# ``purge_expired_audit_logs`` (ADR-275 D5). Audit de mutação NÃO entra aqui:
# base legal + prazo distintos (Art.16), sobrevive ao purge.
READ_ACCESS_ACTIONS: frozenset[str] = frozenset(
    {
        AuditAction.report_read.value,
        AuditAction.report_download.value,
        AuditAction.transactions_read.value,
        AuditAction.transactions_export.value,
        AuditAction.family_member_read.value,
        AuditAction.document_read.value,
        AuditAction.document_download.value,
        AuditAction.cpf_view_full.value,
    }
)


def client_meta(request: Optional[Request] = None) -> tuple[Optional[str], Optional[str]]:
    """Extrai (ip, user_agent) de um Request FastAPI.

    Exposto para routers emitirem ``AuditLogEvent`` sem duplicar a lógica
    de X-Forwarded-For (A6e.events-migration).
    """
    if request is None:
        return None, None
    # Respeita X-Forwarded-For se presente (Traefik / reverse proxy)
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    ua = request.headers.get("user-agent")
    return ip, ua


# Alias legado — mantido para compat com chamadas internas (audit_log).
_client_meta = client_meta


def _build(
    *,
    action: AuditAction | str,
    resource_type: str,
    resource_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    return AuditLog(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action.value if isinstance(action, AuditAction) else action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip,
        user_agent=ua,
        details=details,
    )


async def audit_log(
    db: AsyncSession,
    *,
    action: AuditAction | str,
    resource_type: str,
    resource_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    request: Optional[Request] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Versão async para uso nos endpoints FastAPI.

    NÃO faz commit — o chamador é dono da transação.
    """
    ip, ua = _client_meta(request)
    entry = _build(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        ip=ip,
        ua=ua,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry


def audit_log_sync(
    db: Session,
    *,
    action: AuditAction | str,
    resource_type: str,
    resource_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Versão síncrona para jobs Celery / threads de background."""
    entry = _build(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        details=details,
    )
    db.add(entry)
    db.flush()
    return entry
