"""Tests — `InMemoryPropertyOverridesResolver` (ADR-215 P3 connection fix)."""

from __future__ import annotations

from pipeline.adapters.in_memory_property_overrides_resolver import (
    InMemoryPropertyOverridesResolver,
)
from pipeline.ports import PropertyOverridesResolver


def test_satisfies_protocol():
    resolver = InMemoryPropertyOverridesResolver()
    assert isinstance(resolver, PropertyOverridesResolver)


def test_empty_workspace_returns_empty_dict():
    resolver = InMemoryPropertyOverridesResolver()
    assert resolver.list_for_workspace("ws-empty") == {}


def test_returns_seeded_overrides():
    resolver = InMemoryPropertyOverridesResolver(
        {
            "ws-1": {
                "prop-a": "residencia_principal",
                "prop-b": "locado",
            }
        }
    )
    assert resolver.list_for_workspace("ws-1") == {
        "prop-a": "residencia_principal",
        "prop-b": "locado",
    }


def test_isolates_workspaces():
    resolver = InMemoryPropertyOverridesResolver(
        {
            "ws-1": {"prop-a": "residencia_principal"},
            "ws-2": {"prop-x": "uso_pessoal"},
        }
    )
    assert resolver.list_for_workspace("ws-1") == {"prop-a": "residencia_principal"}
    assert resolver.list_for_workspace("ws-2") == {"prop-x": "uso_pessoal"}


def test_returns_copy_not_internal_reference():
    # Mutar o retorno não deve afetar o estado interno.
    resolver = InMemoryPropertyOverridesResolver({"ws-1": {"prop-a": "residencia_principal"}})
    snapshot = resolver.list_for_workspace("ws-1")
    snapshot["prop-z"] = "especulacao"
    assert resolver.list_for_workspace("ws-1") == {"prop-a": "residencia_principal"}


def test_set_overrides_workspace():
    resolver = InMemoryPropertyOverridesResolver()
    resolver.set("ws-1", "prop-a", "residencia_principal")
    resolver.set("ws-1", "prop-b", "locado")
    assert resolver.list_for_workspace("ws-1") == {
        "prop-a": "residencia_principal",
        "prop-b": "locado",
    }
