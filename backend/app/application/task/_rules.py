"""Regras de domínio puras do agregado ``Task``.

Mantido separado para que use cases orquestrem enquanto os predicados
ficam testáveis em isolamento. O grafo de transições de status espelha
``backend.app.services.task_service.ALLOWED_TRANSITIONS`` — duplicação
deliberada: o service sobrevive apenas até A6e.4 4b fazer o router fino
apagar a versão antiga. Fonte de verdade do novo layer é aqui.
"""

from __future__ import annotations

# Grafo: de → set de destinos aceitos. `done` e `cancelled` permitem reabrir
# explicitamente (audit trail via status_reason + updated_at).
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"in_progress", "done", "cancelled", "blocked"}),
    "in_progress": frozenset({"pending", "done", "cancelled", "blocked"}),
    "blocked": frozenset({"pending", "in_progress", "cancelled"}),
    "done": frozenset({"pending", "in_progress"}),
    "cancelled": frozenset({"pending"}),
}
