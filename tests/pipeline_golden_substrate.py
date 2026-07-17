"""Substrato compartilhado dos goldens E3→E4→E5 (A23.l2): config mínima de tenant + run puro num ``InMemoryArtifactStore`` ([[ADR-212]]), determinístico. Reusado pelos invariantes de conservação, snapshot do view-model e fixture dogfood."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_LEGACY_CONFIGS = _REPO / "tests" / "fixtures" / "legacy_configs"

_DEFAULT_FAMILY = {
    "titular": "david",
    "membros": {"david": {"nome_curto": "David", "data_nascimento": "1985-06-15"}},
}
_DEFAULT_GOALS = {"independencia_financeira": {"if_meta": 1_000_000.0, "trs_pct": 4.0}}


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _categorization(expense_keywords: dict | None, income_keywords: dict | None = None) -> dict:
    return {
        "expense_keywords": expense_keywords or {},
        "income_keywords": income_keywords or {"renda": ["PIX"]},
        "internal_transfer_patterns": [],
        "pj_source_mapping": {},
        "clt_source_mapping": {},
    }


def _copy_legacy(cfg: Path) -> None:
    shutil.copy(_REPO / "config" / "scoring.json", cfg / "scoring.json")
    shutil.copy(_LEGACY_CONFIGS / "parametros_fiscais.json", cfg / "parametros_fiscais.json")
    shutil.copy(_LEGACY_CONFIGS / "taxas.json", cfg / "taxas.json")


def write_e5_config(
    tmp_path: Path,
    *,
    family: dict | None = None,
    goals: dict | None = None,
    expense_keywords: dict | None = None,
    income_keywords: dict | None = None,
) -> None:
    """Escreve config mínima de tenant para rodar E4/E5 isolado."""
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    _dump(cfg / "categorization.json", _categorization(expense_keywords, income_keywords))
    _dump(cfg / "family_members.json", family or _DEFAULT_FAMILY)
    _dump(cfg / "goals.json", goals or _DEFAULT_GOALS)
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")
    _copy_legacy(cfg)


def _seed_store(
    e3_payloads: dict[str, dict],
    baseline: dict | None,
    irpf_payloads: dict[str, dict] | None = None,
):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    for key, payload in e3_payloads.items():
        store.seed("E3", key, payload)
    if baseline is not None:
        store.seed("E1.5c", "baseline_patrimonial", baseline)
    for key, payload in (irpf_payloads or {}).items():
        store.seed("extract_irpf_full", key, payload)
    return store


def run_e3_e4_e5(
    root: Path,
    *,
    e3_payloads: dict[str, dict],
    baseline: dict | None = None,
    irpf_payloads: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Roda E4→E5 sobre E3 seeded; ``irpf_payloads`` semeia extract_irpf_full (DE-02)."""
    from pipeline.context import WorkspaceContext
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws

    store = _seed_store(e3_payloads, baseline, irpf_payloads)
    ctx = WorkspaceContext(root=root, artifact_store=store)
    e4_mws(ctx)
    e5_mws(ctx)
    return ctx.artifact_store.read("E5", "analise_financeira")


def _seed_dogfood_store(raw_baseline: dict, e2_extracts: dict[str, dict]):
    from pipeline.artifact_store import InMemoryArtifactStore

    store = InMemoryArtifactStore()
    store.seed("E1.5", "baseline_patrimonial", raw_baseline)
    for key, payload in e2_extracts.items():
        store.seed("E2-extratos", key, payload)
    return store


def run_dogfood_pipeline(
    root: Path, *, raw_baseline: dict, e2_extracts: dict[str, dict]
) -> dict[str, Any]:
    """Roda E1.5c→E3→E4→E5 sobre baseline bruto + extratos E2 seeded; exercita dedup genuíno (ADR-271 em E1.5c, ADR-255 em E3); retorna ``analise_financeira``."""
    from pipeline.context import WorkspaceContext
    from scripts.analyze_finances import main_with_store as e5_mws
    from scripts.categorize_transactions import main_with_store as e4_mws
    from scripts.consolidate_baseline import main_with_store as e15_mws
    from scripts.reconcile_transactions import main_with_store as e3_mws

    ctx = WorkspaceContext(root=root, artifact_store=_seed_dogfood_store(raw_baseline, e2_extracts))
    for stage in (e15_mws, e3_mws, e4_mws, e5_mws):
        stage(ctx)
    return ctx.artifact_store.read("E5", "analise_financeira")


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
