"""Wiring do catálogo de citação no exec context destilado (A26.l1)."""

from __future__ import annotations

import dataclasses

from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_manifest import CitationCatalogConfig, load_manifest
from tests.test_parecer_planejador_golden import make_workspace_e5

_CATALOG_HEADER = "### Evidência citável (evidencia_paths_disponiveis)"


def _with_catalog(emit: bool, **overrides):
    manifest = load_manifest()
    cfg = dataclasses.replace(manifest.citation_catalog, emit=emit, **overrides)
    return dataclasses.replace(manifest, citation_catalog=cfg)


def test_emit_false_is_byte_identical_to_pre_a26():
    e5 = make_workspace_e5()
    off = distill_exec_context(_with_catalog(False), e5)
    assert _CATALOG_HEADER not in off
    # Catálogo ON apenas ANEXA — o prefixo das narrativas é idêntico.
    on = distill_exec_context(_with_catalog(True), e5)
    assert on.startswith(off)
    assert _CATALOG_HEADER in on


def test_catalog_appended_after_sections():
    on = distill_exec_context(_with_catalog(True), make_workspace_e5())
    assert on.index("### Patrimônio") < on.index(_CATALOG_HEADER)
    assert "`$.reserva_emergencia.total_liquida` → R$ 84.000,00" in on


def test_catalog_survives_narrative_truncation():
    """Narrativas truncam sob max_exec_context_bytes; o catálogo (orçamento próprio) sobrevive."""
    manifest = dataclasses.replace(_with_catalog(True), max_exec_context_bytes=512)
    out = distill_exec_context(manifest, make_workspace_e5())
    assert "[exec context truncado" in out  # narrativas cortadas
    assert _CATALOG_HEADER in out  # catálogo íntegro depois do corte
    assert "`$.reserva_emergencia.total_liquida`" in out


def test_default_manifest_emits_catalog():
    """O manifest versionado (1.5) liga o catálogo por default."""
    assert load_manifest().citation_catalog.emit is True
    assert isinstance(load_manifest().citation_catalog, CitationCatalogConfig)
