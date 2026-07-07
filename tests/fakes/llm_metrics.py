"""Fake nomeado do ``LLMMetricsEmitter`` (A33.l7) — captura emissões em listas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RecordingLLMMetricsEmitter:
    """Implementação em memória do protocol ``pipeline.llm.metrics.LLMMetricsEmitter``."""

    call_qualities: list[dict] = field(default_factory=list)
    cache_lookups: list[dict] = field(default_factory=list)
    riscos_truncados: list[dict] = field(default_factory=list)
    raise_on_record: Optional[Exception] = None

    def record_call_quality(
        self,
        *,
        prompt_name: str,
        prompt_version: str,
        model: str,
        confidence: Optional[float],
        needs_review: bool,
    ) -> None:
        if self.raise_on_record is not None:
            raise self.raise_on_record
        self.call_qualities.append(
            {
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "model": model,
                "confidence": confidence,
                "needs_review": needs_review,
            }
        )

    def record_cache_lookup(self, *, hit: bool, prompt_name: str, prompt_version: str) -> None:
        if self.raise_on_record is not None:
            raise self.raise_on_record
        self.cache_lookups.append(
            {"hit": hit, "prompt_name": prompt_name, "prompt_version": prompt_version}
        )

    def record_riscos_truncados(
        self, *, dropped: int, prompt_name: str, prompt_version: str
    ) -> None:
        if self.raise_on_record is not None:
            raise self.raise_on_record
        self.riscos_truncados.append(
            {"dropped": dropped, "prompt_name": prompt_name, "prompt_version": prompt_version}
        )
