"""InformeQuery — service de leitura de informes anuais para FiscalSource (ADR-238 D5)."""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from backend.app.repositories.pipeline_artifact_repository import PipelineArtifactRepository
from backend.app.services.crypto import read_artifact_content

logger = logging.getLogger("mathoms.informes.query")

_STAGE_DESCRIPTIVE = "extract_informes_anuais"
_STAGE_LEGACY = "E2-informe-anual"


class InformeQuery:
    """Lê informes anuais de ``pipeline_artifacts`` por workspace (ADR-238 D5; isolation OK via application/)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PipelineArtifactRepository(session)

    def list_for_workspace(
        self,
        workspace_id: str,
        *,
        ano_base: Optional[int] = None,
        tipo_informe: Optional[str] = None,
    ) -> list[dict]:
        """Payloads decriptados prontos para FiscalSource.from_informes (ano_base/tipo filtros opcionais)."""
        payloads = self._fetch_payloads(workspace_id)
        return self._filter_payloads(payloads, ano_base=ano_base, tipo_informe=tipo_informe)

    def list_previdencia(self, workspace_id: str, *, ano_base: Optional[int] = None) -> list[dict]:
        """Atalho semântico para previdência privada (PGBL/VGBL)."""
        return self.list_for_workspace(
            workspace_id, ano_base=ano_base, tipo_informe="previdencia_privada"
        )

    # ---- internals ----

    def _payload_for_key(
        self, workspace_id: str, stage: str, key: str, seen_ids: set[str]
    ) -> dict | None:
        """Resolve 1 artifact + dedup por id; retorna payload dict ou None."""
        art = self._repo.get_latest_for_workspace(workspace_id, stage=stage, artifact_key=key)
        if art is None or art.id in seen_ids or art.content_json is None:
            return None
        seen_ids.add(art.id)
        payload = read_artifact_content(art.content_json)
        return payload if isinstance(payload, dict) else None

    def _stage_keys(self, workspace_id: str) -> list[tuple[str, str]]:
        """Lista flat de ``(stage, key)`` em ambas as formas (descritivo + legacy)."""
        return [
            (stage, key)
            for stage in (_STAGE_DESCRIPTIVE, _STAGE_LEGACY)
            for key in self._repo.list_latest_keys(workspace_id, stage=stage)
        ]

    def _fetch_payloads(self, workspace_id: str) -> list[dict]:
        """Query pipeline_artifacts em ambas as formas (descritivo + legacy) sem dup."""
        seen_ids: set[str] = set()
        payloads = (
            self._payload_for_key(workspace_id, stage, key, seen_ids)
            for stage, key in self._stage_keys(workspace_id)
        )
        return [p for p in payloads if p is not None]

    @staticmethod
    def _filter_payloads(
        payloads: Iterable[dict],
        *,
        ano_base: Optional[int] = None,
        tipo_informe: Optional[str] = None,
    ) -> list[dict]:
        out: list[dict] = []
        for p in payloads:
            if ano_base is not None and p.get("ano_base") != ano_base:
                continue
            if tipo_informe is not None and p.get("tipo_informe") != tipo_informe:
                continue
            out.append(p)
        return out
