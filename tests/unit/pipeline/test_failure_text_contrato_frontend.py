"""ADR-441 D2 — o marcador do texto redigido é contrato Python ↔ TypeScript.

O headline do `FailedRunCard` decide pelo marcador ANTES de qualquer padrão: nome de
coluna no texto redigido (`api_key_encrypted`, `schema_version`) casaria a regra de
senha ou de formato por acidente. O lado TypeScript lê este arquivo Python de volta.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.observability.failure_text import DATABASE_VALUES_OMITTED

_TS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "pipelineErrorMessages.ts"


def test_o_frontend_declara_o_mesmo_marcador():
    declaracao = f'export const DATABASE_VALUES_OMITTED = "{DATABASE_VALUES_OMITTED}";'
    assert declaracao in _TS.read_text(encoding="utf-8")
