"""Audit trail do console interno — sink em arquivo JSONL (ADR-116).

Sink trocável para tabela `audit_entries` quando 7B.5 fechar. Por enquanto,
append em `logs/internal_ops_audit.log` (fora de git) — imutável por
convenção, sem rotação interna (logrotate externo cuida).

Regras:
- Nunca persistir senha (nem mascarada).
- Nunca persistir conteúdo monetário total (ADR-110 masking).
- Timestamp UTC ISO-8601; uma linha por evento; JSON válido por linha.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import settings

_FORBIDDEN_KEYS = frozenset(
    {"password", "new_password", "hashed_password", "token", "jwt", "secret"}
)

# Lock serializa writes no mesmo processo; entre processos, append-only
# garante atomicidade por linha em tmpfs/ext4/apfs (<4KB).
_write_lock = threading.Lock()


@dataclass(frozen=True)
class AuditRecord:
    """Evento imutável de audit interno."""

    action: str
    actor: str
    target_type: str | None = None
    target_id: str | None = None
    result: str = "ok"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        payload = asdict(self)
        payload["details"] = _redact(payload["details"])
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _redact(details: dict[str, Any]) -> dict[str, Any]:
    """Remove chaves sensíveis independentemente do caller."""
    return {k: v for k, v in details.items() if k.lower() not in _FORBIDDEN_KEYS}


def audit_log_path() -> Path:
    """Caminho do arquivo de audit (criado sob demanda em `append_audit`)."""
    root = Path(settings.STORAGE_ROOT).parent
    return root / "logs" / "internal_ops_audit.log"


def append_audit(record: AuditRecord, *, path: Path | None = None) -> None:
    """Appenda uma entrada no log. Thread-safe; idempotência é do caller."""
    target = path or audit_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    line = record.to_json() + "\n"
    with _write_lock:
        with target.open("a", encoding="utf-8") as fh:
            fh.write(line)


def read_audit(*, path: Path | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    """Lê o log como lista de dicts (mais recentes por último).

    `limit` retorna as N últimas entradas. Uso: UI + testes.
    """
    target = path or audit_log_path()
    if not target.exists():
        return []
    with target.open("r", encoding="utf-8") as fh:
        lines = fh.readlines()
    if limit is not None:
        lines = lines[-limit:]
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
