"""Handlers concretos — importar cada módulo aqui para disparar ``@register_handler``.

Descoberta automática via glob é explicitamente rejeitada (ADR-115): o
registro é frágil se depende da ordem de import dos arquivos. Aqui a
lista é explícita e revisável em PRs.

Handlers concretos são adicionados nos slices 2 e 3 deste track.
"""

from __future__ import annotations

from backend.app.events.handlers import (
    audit_log_handler,  # noqa: F401
    task_notification_handler,  # noqa: F401
)
