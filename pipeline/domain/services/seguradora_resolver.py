"""Canonicalização de ``seguradora`` no boundary E2→domínio (A37.l11 · PD-05).

O prompt de apólice instrui o LLM a emitir codes canônicos do
``institution_catalog`` (``category=insurance``), mas a instrução pode ser
violada — evidência 2026-07-20: ``porto`` e ``portoseguro`` no mesmo run para
a mesma cia, inflando ``seguradoras_count`` e duplicando rótulos na UI.
Resolução: match por code; fallback pelo nome normalizado do catálogo; code
fora do catálogo é normalizado e persiste com flag SOFT de telemetria
(``in_catalog=False``) — ``needs_review`` só em ambiguidade real
(``ambiguous=True``), porque o catálogo de seguradoras é esparso e over-fire
degradaria a análise de proteção inteira.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SeguradoraResolution:
    """Resultado da resolução contra o catálogo (code → nome de exibição)."""

    code: str
    display_name: str
    in_catalog: bool
    ambiguous: bool = False


def normalize_seguradora_code(raw: str) -> str:
    """Formato dos codes do catálogo: lowercase, sem acentos, só ``[a-z0-9]``."""
    text = unicodedata.normalize("NFD", (raw or "").strip().lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return "".join(c for c in text if c.isalnum())


def fallback_seguradora_display(raw: str) -> str:
    """Display capitalizado quando o catálogo não resolve — nunca o code cru."""
    return " ".join(w.capitalize() for w in (raw or "").strip().split())


def resolve_seguradora(raw: str, catalog: Mapping[str, str]) -> SeguradoraResolution:
    """Match por code; fallback por nome normalizado; fora do catálogo normaliza."""
    token = normalize_seguradora_code(raw)
    if not token:
        return SeguradoraResolution(code="", display_name="", in_catalog=False)
    if token in catalog:
        return SeguradoraResolution(code=token, display_name=catalog[token], in_catalog=True)
    matches = [c for c, nome in catalog.items() if normalize_seguradora_code(nome) == token]
    if len(matches) == 1:
        code = matches[0]
        return SeguradoraResolution(code=code, display_name=catalog[code], in_catalog=True)
    return SeguradoraResolution(
        code=token,
        display_name=fallback_seguradora_display(raw),
        in_catalog=False,
        ambiguous=len(matches) > 1,
    )


def canonicalize_apolice_seguradora(apolice: dict, catalog: Mapping[str, str]) -> dict:
    """Cópia rasa com ``seguradora`` canônico + ``seguradora_nome`` de exibição;
    ``_seguradora_fora_catalogo`` (chave interna, não serializada em resumo)
    marca o caso fora do catálogo para telemetria agregada."""
    res = resolve_seguradora(str(apolice.get("seguradora") or ""), catalog)
    out = dict(apolice)
    out["seguradora"] = res.code
    out["seguradora_nome"] = res.display_name
    if res.code and not res.in_catalog:
        out["_seguradora_fora_catalogo"] = True
    return out
