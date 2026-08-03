"""`TributarioSectionResolver` — read-model tributário resolvido em stage-time (RV3-11 · A40.l9)."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


# O agregado não é config: valor que só existe em t=E4 não tem lugar num mapa
# materializado em t=0 (goals.json). O resolver é invocado quando a cascata é
# necessária (E5.N), momento em que o E4 do run corrente já foi escrito.
@runtime_checkable
class TributarioSectionResolver(Protocol):
    """Boundary para a seção tributária derivada do E4 (RV3-11 · A40.l9)."""

    def resolve(self, workspace_id: str) -> Optional[dict[str, Any]]:
        # Retorna a seção `tributario` do bundle (shape de
        # ``TributarioBundleSection``) computada do último run COM E4, ou
        # ``None`` quando indisponível — caller degrada para o materializado.
        ...
