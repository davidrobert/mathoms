"""Drill-down tools do parecer planejador — get_e5_section/get_e5_jsonpath (ADR-203)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from pipeline.llm.value_formatter import format_value

# Padrão JSONPath aceito (subset): $.a, $.a.b, $.arr[*], $.arr[*].field, $.a.b.c[0]
# Rejeita explicitamente `$..*` (recursive descent), filtros e operadores.
# Cada segmento deve começar com letra/_, ter chars alfanuméricos/_/[]/*/digit,
# e separadores são literalmente `.` entre segmentos (não duplicado).
_JSONPATH_RE = re.compile(r"^\$\.[A-Za-z_][A-Za-z_0-9\[\]*]*(\.[A-Za-z_][A-Za-z_0-9\[\]*]*)*$")
_SEGMENT_RE = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)(\[(\*|\d+)\])*$")

# Padrões hostis em ``narrativas`` — ADR-203 §D9.
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(previous|all|prior)\s+instruction", re.IGNORECASE),
    re.compile(r"</?(system|instructions?|assistant|prompt|im_end|im_start)\b", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a\s+", re.IGNORECASE),
    re.compile(r"esque[çc]a\s+(suas|tudo|as)", re.IGNORECASE),
    re.compile(r"aja\s+como\s+", re.IGNORECASE),
    re.compile(r"<\|\w+\|>"),  # special tokens (e.g. <|im_end|>)
)

# Limite de chars por string narrativa antes de injeção no contexto LLM.
_MAX_NARRATIVA_CHARS = 500
_NARRATIVAS_KEYS = ("narrativas",)


@dataclass(frozen=True)
class ToolResult:
    """Resultado canônico de uma tool call (ADR-203 §D7)."""

    found: bool
    value: Any = None
    reason: str | None = None  # path_not_whitelisted | value_null | value_absent
    type_name: str | None = None

    def to_llm_payload(self) -> dict:
        """Shape consumido pelo LLM (não inclui telemetria interna)."""
        if self.found:
            return {"found": True, "value": self.value}
        return {"found": False, "reason": self.reason or "value_absent"}


@dataclass
class ToolTraceEntry:
    """Audit trail entry — uma chamada de tool (ADR-203 §D5)."""

    iter: int
    tool: str
    input: dict
    result_summary: dict
    latency_ms: int
    cache_hit: bool


@dataclass
class PlannerDrillDown:
    """Provider das 2 tools — E5 in-memory + cache per-call + audit trail (ADR-203)."""

    e5_data: Mapping[str, Any]
    section_whitelist: frozenset[str]
    format_hints: Mapping[str, str] = field(default_factory=dict)

    _section_cache: dict[str, ToolResult] = field(default_factory=dict, init=False)
    _path_cache: dict[str, ToolResult] = field(default_factory=dict, init=False)
    trace: list[ToolTraceEntry] = field(default_factory=list, init=False)
    _iter: int = field(default=0, init=False)

    # ------------------------------------------------------------------
    # Tool 1: get_e5_section
    # ------------------------------------------------------------------

    def get_e5_section(self, section: str) -> ToolResult:
        """Lê seção top-level do E5. Whitelist enum validada antes."""
        return self._invoke(
            tool_name="get_e5_section",
            cache=self._section_cache,
            key=section,
            resolver=self._resolve_section,
            input_dict={"section": section},
        )

    def _resolve_section(self, section: str) -> ToolResult:
        if section not in self.section_whitelist:
            return ToolResult(found=False, reason="path_not_whitelisted")
        value = self.e5_data.get(section)
        if value is None:
            return ToolResult(found=False, reason="value_null", type_name="NoneType")
        sanitized = _sanitize_narrativas(value) if section == "narrativas" else value
        return ToolResult(found=True, value=sanitized, type_name=type(value).__name__)

    # ------------------------------------------------------------------
    # Tool 2: get_e5_jsonpath
    # ------------------------------------------------------------------

    def get_e5_jsonpath(self, path: str) -> ToolResult:
        """Lê path JSONPath subset do E5."""
        return self._invoke(
            tool_name="get_e5_jsonpath",
            cache=self._path_cache,
            key=path,
            resolver=self._resolve_path,
            input_dict={"path": path},
        )

    def _invoke(
        self,
        *,
        tool_name: str,
        cache: dict[str, ToolResult],
        key: str,
        resolver,
        input_dict: dict,
    ) -> ToolResult:
        """Despacha tool call genérico — cache lookup + audit trail + iter inc."""
        self._iter += 1
        start = time.monotonic()
        cache_hit = key in cache
        result = cache[key] if cache_hit else resolver(key)
        if not cache_hit:
            cache[key] = result
        latency_ms = int((time.monotonic() - start) * 1000)
        self.trace.append(
            ToolTraceEntry(
                iter=self._iter,
                tool=tool_name,
                input=input_dict,
                result_summary=_summarize_result(result),
                latency_ms=latency_ms,
                cache_hit=cache_hit,
            )
        )
        return result

    def _resolve_path(self, path: str) -> ToolResult:
        """Resolve JSONPath subset; rejeita sintaxe/semântica fora da whitelist."""
        if not _JSONPATH_RE.match(path):
            return ToolResult(found=False, reason="path_not_whitelisted")
        segments = _parse_jsonpath(path)
        if segments is None or segments[0][0] not in self.section_whitelist:
            return ToolResult(found=False, reason="path_not_whitelisted")
        try:
            value = _walk_segments(self.e5_data, segments)
        except (KeyError, IndexError, TypeError):
            return ToolResult(found=False, reason="value_absent")
        if value is None:
            return ToolResult(found=False, reason="value_null", type_name="NoneType")
        formatted = _apply_path_post(value, path, segments[0][0], self.format_hints)
        return ToolResult(found=True, value=formatted, type_name=type(value).__name__)

    # ------------------------------------------------------------------
    # Audit accessors
    # ------------------------------------------------------------------

    # OBS-1 (A37.l1 · ADR-341): telemetria, NÃO o cap. Conta cache hits
    # (cache_in_session evita recomputar, não a contagem) e chamadas pós-LLM
    # (stamp_ancora_values re-resolve âncoras via este provider, ADR-296) —
    # por isso pode EXCEDER max_tool_iterations do manifest (ex.: trace com
    # 8 calls sob cap 6, 3 cache_hit). Não é o número de round-trips LLM→tool.
    @property
    def iterations_count(self) -> int:
        """Total de invocações de tool nesta instância (telemetria; ver comment acima)."""
        return self._iter

    def to_trace_dicts(self) -> list[dict]:
        """Serializa trace para persistência em ``_meta.tool_trace``."""
        return [
            {
                "iter": e.iter,
                "tool": e.tool,
                "input": e.input,
                "result_summary": e.result_summary,
                "latency_ms": e.latency_ms,
                "cache_hit": e.cache_hit,
            }
            for e in self.trace
        ]


# ----------------------------------------------------------------------
# Helpers privados
# ----------------------------------------------------------------------


def _apply_path_post(value: Any, path: str, head_key: str, format_hints: Mapping[str, str]) -> Any:
    """Aplica format hint + sanitização anti-injection ao valor retornado de path."""
    fmt = format_hints.get(path)
    formatted = format_value(value, fmt) if fmt else value
    if head_key in _NARRATIVAS_KEYS:
        formatted = _sanitize_narrativas(formatted)
    return formatted


def _summarize_result(result: ToolResult) -> dict:
    """Reduz ToolResult a metadata (sem valor cru — ADR-203 §D5)."""
    out: dict[str, Any] = {"found": result.found}
    if result.found:
        out["type"] = result.type_name or type(result.value).__name__
    elif result.reason:
        out["reason"] = result.reason
    return out


def _parse_jsonpath(path: str) -> list[tuple[str, list[str]]] | None:
    """Tokeniza JSONPath subset em ``[(key, indices)...]``; rejeita ``$..*`` e filtros."""
    if not path.startswith("$."):
        return None
    segments: list[tuple[str, list[str]]] = []
    for raw_seg in path[2:].split("."):
        m = _SEGMENT_RE.match(raw_seg)
        if not m:
            return None
        key = m.group(1)
        indices = re.findall(r"\[(\*|\d+)\]", raw_seg)
        segments.append((key, indices))
    return segments


def _walk_segments(data: Any, segments: list[tuple[str, list[str]]]) -> Any:
    """Anda segmentos parseados; wildcard ``[*]`` só no segmento final (lista inteira)."""
    current: Any = data
    for seg_i, (key, indices) in enumerate(segments):
        if not isinstance(current, Mapping):
            raise TypeError(f"expected dict at segment {key!r}")
        current = current[key]
        is_last = seg_i == len(segments) - 1
        for idx_i, idx in enumerate(indices):
            idx_is_last = is_last and idx_i == len(indices) - 1
            if idx == "*":
                if not isinstance(current, list):
                    raise TypeError(f"expected list for wildcard at {key!r}")
                if idx_is_last:
                    return current
                # Wildcard intermediário só faz sentido seguido de sub-key.
                # Não suportado nessa whitelist mínima — rejeita.
                raise TypeError(f"intermediate wildcard not supported at {key!r}")
            current = current[int(idx)]
    return current


def _sanitize_narrativas(value: Any) -> Any:
    """Redação anti-injeção em strings de ``narrativas`` (ADR-203 §D9)."""
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, Mapping):
        return {k: _sanitize_narrativas(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_narrativas(v) for v in value]
    return value


def _sanitize_string(text: str) -> str:
    if len(text) > _MAX_NARRATIVA_CHARS:
        text = text[:_MAX_NARRATIVA_CHARS] + "…"
    for pat in _INJECTION_PATTERNS:
        if pat.search(text):
            return "[REDACTED_SUSPECT_PATTERN]"
    return text
