"""Gate PII-scan (CTO-03 / [[ADR-332]]): nenhum nome de membro nem CPF/CNPJ chega
ao provider LLM por NENHUM egresso do parecer — distiller E tool ``get_e5_section``
(devolve seções inteiras sem truncar). Red-before-green: nomes sintéticos semeados
em seções whitelistadas; pré-sanitize casa, pós-sanitize zero-hit. Zero PII real."""

from __future__ import annotations

import json

from backend.app.services.parecer_context_sanitizer import (
    build_name_role_pairs,
    sanitize_e5_for_parecer,
)
from backend.app.services.parecer_distiller import distill_exec_context
from backend.app.services.parecer_manifest import load_manifest
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from pipeline.observability.pii_patterns import contains_identifier
from tests.test_parecer_planejador_golden import make_workspace_e5

_FAMILY = {
    "titular": "fulano",
    "membros": {
        "fulano": {"nome_curto": "Fulano", "papel": "titular"},
        "beltrano": {"nome_curto": "Beltrano", "papel": "conjuge"},
    },
}
_NAMES = ("Fulano", "Beltrano")


# Sintético — identificador estrutural de apólice (ADR-341 D6, A37.l1 PR-2a).
_APOLICE_NUMERO = "51.824.917 236"
_APOLICE_VIGENTE = {
    "apolice_numero": _APOLICE_NUMERO,
    "seguradora": "portoseguro",
    "vigencia_inicio": "2026-01-01",
    "vigencia_fim": "2026-12-31",
    "premio_total_brl": "1234.56",
    "bens_count": 1,
}


def _seed_pii(e5: dict) -> dict:
    """Injeta nome de membro + CPF + nº de apólice em seções whitelistadas
    (tool devolve inteiras)."""
    e5 = json.loads(json.dumps(e5))
    e5["investimentos"]["top_ativos"] = [
        {"membro": "Fulano", "obs": "titular CPF 123.456.789-00", "valor": 100000.0}
    ]
    e5["fluxo_caixa"]["por_fonte_detalhado"] = {"PIX Fulano": 3000.0, "Salario Beltrano": 8000.0}
    e5["protecao_patrimonial"] = {"apolices_vigentes": [dict(_APOLICE_VIGENTE)]}
    return e5


def _effective_context(e5: dict) -> str:
    """Contexto efetivo dos 2 egressos: distiller + toda seção que a tool devolve."""
    manifest = load_manifest()
    parts = [distill_exec_context(manifest, e5)]
    drill = PlannerDrillDown(
        e5_data=e5, section_whitelist=manifest.tools_section_whitelist, format_hints={}
    )
    for section in sorted(manifest.tools_section_whitelist):
        result = drill.get_e5_section(section)
        if result.found:
            parts.append(json.dumps(result.value, ensure_ascii=False, default=str))
    return "\n".join(parts)


def test_pii_scan_red_before_green():
    seeded = _seed_pii(make_workspace_e5())

    raw_ctx = _effective_context(seeded)
    assert any(n in raw_ctx for n in _NAMES), "pré-condição: nome deve vazar sem sanitize"
    assert contains_identifier(raw_ctx), "pré-condição: CPF deve vazar sem sanitize"
    assert _APOLICE_NUMERO in raw_ctx, "pré-condição: nº de apólice deve vazar sem sanitize"

    clean_ctx = _effective_context(sanitize_e5_for_parecer(seeded, build_name_role_pairs(_FAMILY)))
    for name in _NAMES:
        assert name not in clean_ctx, f"nome '{name}' vazou no contexto efetivo do LLM"
    assert not contains_identifier(clean_ctx), "CPF/CNPJ vazou no contexto efetivo do LLM"
    assert _APOLICE_NUMERO not in clean_ctx, "nº de apólice vazou no contexto efetivo do LLM"
