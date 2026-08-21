"""Reduz os insumos de um run a um ``review_snapshot.json`` PII-safe ([[ADR-343]]).

Metade "snapshot" do ``compare_reviews``: zero literal monetário, zero nome
próprio, zero descrição de transação. Só contagens, enums, estados e
percentuais. Separado em [[ADR-406]], quando o arquivo único cruzou 500 linhas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

SCHEMA_VERSION = "2"

# Seções do view-model E5 cuja ausência/esvaziamento é regressão.
_SECTION_KEYS = (
    "patrimonio",
    "fluxo_caixa",
    "ratios",
    "reserva_emergencia",
    "endividamento",
    "previdencia_pgbl",
    "investimentos",
    "real_estate",
    "protecao_patrimonial",
    "passive_income",
    "exposicao_cambial",
    "programa_milhas",
    "narrativas",
)


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def elapsed_minutes(started: object, completed: object) -> float | None:
    """Duração em minutos, calculada em Python e não em SQL."""
    # O coletor usava `julianday()`, que só existe em SQLite — dev roda SQLite e
    # prod roda Postgres, então o read-path da review não rodava contra prod.
    # Aceita datetime (asyncpg) e str (aiosqlite): os dois dialetos, um número.
    start, end = _as_datetime(started), _as_datetime(completed)
    if start is None or end is None:
        return None
    if (start.tzinfo is None) != (end.tzinfo is None):
        start, end = start.replace(tzinfo=None), end.replace(tzinfo=None)
    return round((end - start).total_seconds() / 60, 1)


def _leaf(path: str) -> str:
    return path.rsplit(".", 1)[-1].split("[", 1)[0]


def _sum_leaf(obj: Any, leaf: str) -> int | None:
    """Soma recursiva dos valores numéricos de todas as folhas ``leaf`` (ou None)."""
    found: list[int] = []
    _collect_leaf(obj, leaf, found)
    return sum(found) if found else None


def _collect_leaf(obj: Any, leaf: str, out: list[int]) -> None:
    if isinstance(obj, dict):
        _collect_dict(obj, leaf, out)
    elif isinstance(obj, list):
        _collect_list(obj, leaf, out)


def _collect_list(items: list, leaf: str, out: list[int]) -> None:
    for item in items:
        _collect_leaf(item, leaf, out)


def _collect_dict(obj: dict, leaf: str, out: list[int]) -> None:
    for key, value in obj.items():
        _collect_leaf_kv(key, value, leaf, out)


def _collect_leaf_kv(key: str, value: Any, leaf: str, out: list[int]) -> None:
    if key == leaf and isinstance(value, (int, float)) and not isinstance(value, bool):
        out.append(int(value))
    else:
        _collect_leaf(value, leaf, out)


def _section_state(data: dict, key: str) -> str:
    if key not in data:
        return "absent"
    return "empty" if data[key] in (None, {}, [], "") else "populated"


def _sections_map(data: dict) -> dict[str, str]:
    return {k: _section_state(data, k) for k in _SECTION_KEYS}


def _parecer_snapshot(parecer: Any) -> dict[str, Any]:
    """Sinal estrutural do parecer (não persiste o texto: PII + maior artefato)."""
    if not isinstance(parecer, dict) or not parecer:
        return {"status": "ausente", "n_secoes": 0, "schema_valid": False, "cache_hit": False}
    secoes = parecer.get("secoes", parecer.get("sections"))
    n = len(secoes) if isinstance(secoes, (list, dict)) else len(parecer)
    meta = parecer.get("_meta")
    hit = bool(meta.get("cache_hit")) if isinstance(meta, dict) else False
    return {"status": "ok", "n_secoes": n, "schema_valid": True, "cache_hit": hit}


def _cv_snapshot(cv_results: list[dict]) -> list[dict]:
    """Só check_id/severity/passed — dropa ``details`` (embute R$: PII)."""
    return [
        {"check_id": c["check_id"], "severity": c["severity"], "passed": bool(c["passed"])}
        for c in cv_results
    ]


def _needs_review_map(rows: list[dict]) -> dict[str, int]:
    return {r["doc_type"]: r["n"] for r in rows if r.get("doc_type")}


def _run_health(report_data: dict, meta: dict) -> dict:
    costs, calls = meta.get("costs", []), meta.get("calls", [])
    run = meta.get("run", {})
    return {
        "status": run.get("status"),
        "failed_at_stage": run.get("failed_at_stage"),
        "tier_at_run": run.get("tier_at_run"),
        "total_documents": run.get("total_documents"),
        "transacoes_total": _sum_leaf(report_data, "transacoes_total"),
        "duration_min": run.get("minutes"),
        "llm_cost_usd_cents": sum(int(c.get("cost_usd_cents") or 0) for c in costs) or None,
        "llm_calls": len(calls),
        "tool_iterations_total": sum(int(c.get("tool_iterations") or 0) for c in costs) or None,
    }


# Percentual em CENTÉSIMOS de ponto (int) — comparar float run-a-run reintroduz
# o ruído de arredondamento que o `golden_diff` já resolveu em cents.
def _mix_investimentos(report_data: dict) -> dict:
    inv = report_data.get("investimentos") or {}
    return {
        "classes": _classes_em_centesimos(inv.get("tabela_classes") or []),
        "nao_classificado_pct": round(float(inv.get("nao_classificado_pct") or 0) * 100),
        # Pares `[n_posicoes, n_instituicoes]` ordenados pelo próprio par: o
        # nome do membro é PII (`nome_curto`) e nunca entra no snapshot.
        "membros": _cobertura_por_membro(inv.get("instituicoes_por_membro") or []),
    }


def _classes_em_centesimos(tabela: list) -> dict[str, int]:
    return {
        str(r.get("categoria")): round(float(r.get("pct_carteira_financeira") or 0) * 100)
        for r in tabela
        if isinstance(r, dict) and r.get("pct_carteira_financeira") is not None
    }


def _cobertura_por_membro(por_membro: list) -> list[list[int]]:
    pares = [
        [int(m.get("n_posicoes") or 0), len(m.get("instituicoes") or [])]
        for m in por_membro
        if isinstance(m, dict)
    ]
    return sorted(pares, reverse=True)


def build_snapshot(
    *,
    run_id: str,
    report_data: dict,
    cv_results: list[dict],
    meta: dict,
    parecer: Any,
    provenance: dict | None = None,
) -> dict:
    """Snapshot PII-safe (meta = {run, needs_review, costs, calls}, telemetria do run)."""
    snap = _snapshot_body(run_id, report_data, cv_results, meta, parecer)
    # `provenance` é chave TOP-LEVEL, fora do `run_health` (ADR-343 §Emenda): os 9
    # campos de run_health são todos consumidos por perna ou supressor, e um campo
    # não-comparável ali seria assumido comparável pelo próximo leitor.
    return {**snap, "provenance": provenance} if provenance else snap


def _snapshot_body(
    run_id: str, report_data: dict, cv_results: list[dict], meta: dict, parecer: Any
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "run_health": _run_health(report_data, meta),
        "needs_review": _needs_review_map(meta.get("needs_review", [])),
        "cross_validation": _cv_snapshot(cv_results),
        "sections": _sections_map(report_data),
        "investimentos_mix": _mix_investimentos(report_data),
        "parecer": _parecer_snapshot(parecer),
    }


__all__ = ["SCHEMA_VERSION", "_SECTION_KEYS", "_leaf", "build_snapshot", "elapsed_minutes"]
