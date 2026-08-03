"""Erro compartilhado do harness de paridade Go↔Python (F2 do PLAN-go-shell)."""

from __future__ import annotations


class GateError(RuntimeError):
    """Falha de pré-condição ou de orquestração — nunca de paridade (isso é veredito)."""
