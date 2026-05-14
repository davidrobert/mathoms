"""Golden mensal com LLM real (ADR-199 Ato 6 T-27). Roda APENAS via workflow `planner-golden-monthly.yml` — skipa em CI normal via marker + env check. Compara métricas estruturais vs baseline; falha se variação > threshold."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Feature flag precisa estar habilitada.
os.environ.setdefault("MATHOMS_ENABLE_PARECER_PLANEJADOR", "true")

from pipeline.artifact_store import InMemoryArtifactStore  # noqa: E402

_REPO = Path(__file__).resolve().parents[1]
_BASELINE_DIR = _REPO / "tests" / "golden_baselines"


def _real_llm_or_skip() -> None:
    """Skipa se chave Anthropic não está no env (CI normal sem secret)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip(
            "Monthly golden real-LLM exige ANTHROPIC_API_KEY. "
            "Rode via .github/workflows/planner-golden-monthly.yml."
        )


def _load_canonical_e5() -> dict:
    """Fixture canônica do mês — família alta renda, perfil estável."""
    from tests.test_parecer_planejador_golden import make_workspace_e5

    return make_workspace_e5()


def _all_sugestoes(artifact: dict) -> list:
    return (
        artifact.get("sugestoes_execucao", [])
        + artifact.get("sugestoes_taticas", [])
        + artifact.get("sugestoes_estrategicas", [])
    )


def _dominant_ancora(riscos: list) -> str | None:
    """Âncora metodológica mais frequente entre riscos; None se vazio."""
    counts: dict[str, int] = {}
    for risco in riscos:
        a = risco["ancora_metodologica"]
        counts[a] = counts.get(a, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _structural_metrics(artifact: dict) -> dict:
    """Reduz output do parecer a métricas estruturais comparáveis cross-month."""
    all_sug = _all_sugestoes(artifact)
    riscos = artifact.get("riscos", [])
    return {
        "p0_count": sum(1 for s in all_sug if s["prioridade"] == "P0"),
        "p1_count": sum(1 for s in all_sug if s["prioridade"] == "P1"),
        "p2_count": sum(1 for s in all_sug if s["prioridade"] == "P2"),
        "riscos_count": len(riscos),
        "riscos_criticos_count": sum(1 for r in riscos if r["severidade"] == "Crítica"),
        "metricas_count": len(artifact.get("metricas", [])),
        "notas_count": len(artifact.get("notas_metodologicas", [])),
        "pontos_fortes_count": len(artifact.get("pontos_fortes", [])),
        "ancora_dominante_riscos": _dominant_ancora(riscos),
    }


def _baseline_path(yyyy_mm: str) -> Path:
    return _BASELINE_DIR / f"parecer_monthly_{yyyy_mm}.json"


def _latest_baseline_path() -> Path | None:
    """Última baseline disponível (lex order = chrono ascending por filename)."""
    if not _BASELINE_DIR.exists():
        return None
    files = sorted(_BASELINE_DIR.glob("parecer_monthly_*.json"))
    return files[-1] if files else None


def _drift_threshold_exceeded(prev: dict, current: dict) -> list[str]:
    """Retorna lista de campos com variação acima do threshold. Empty = sem drift."""
    drift: list[str] = []
    # P0 count: mudança exata indica drift sério (cap=2, sensível).
    if prev.get("p0_count") != current.get("p0_count"):
        drift.append(f"p0_count: {prev.get('p0_count')} → {current.get('p0_count')}")
    # Riscos count: variação > 50% indica drift de detecção.
    prev_r = prev.get("riscos_count", 0)
    curr_r = current.get("riscos_count", 0)
    if prev_r > 0 and abs(curr_r - prev_r) / prev_r > 0.5:
        drift.append(f"riscos_count: {prev_r} → {curr_r} (>50% variação)")
    # Âncora dominante: mudança = persona/manifest drift forte.
    if prev.get("ancora_dominante_riscos") != current.get("ancora_dominante_riscos"):
        drift.append(
            f"ancora_dominante_riscos: "
            f"{prev.get('ancora_dominante_riscos')!r} → {current.get('ancora_dominante_riscos')!r}"
        )
    return drift


def _call_real_llm(workspace_e5: dict) -> dict:
    """Helper — roda stage de verdade (sem mock). Caller já validou env via _real_llm_or_skip."""
    from pipeline.context import WorkspaceContext
    from pipeline.stages import parecer_planejador as stage_mod

    store = InMemoryArtifactStore()
    store.seed("E5", "analise_financeira", workspace_e5)
    with tempfile.TemporaryDirectory() as tmp:
        ctx = WorkspaceContext(
            root=Path(tmp), artifact_store=store, workspace_id="ws-golden-monthly"
        )
        result = stage_mod.run(ctx)
    if result.get("skipped") or result.get("status") == "needs_review":
        pytest.fail(f"Stage skipped/needs_review: {result}")
    artifact = store.read("E6-parecer", "parecer_planejador")
    assert artifact is not None
    return artifact


def _write_baseline(metrics: dict, yyyy_mm: str) -> Path:
    """Persiste baseline em disco (commit via workflow se update_baseline=true)."""
    _BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    path = _baseline_path(yyyy_mm)
    enriched = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "yyyy_mm": yyyy_mm,
        "metrics": metrics,
    }
    path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _assert_no_drift_or_update(prev_metrics: dict, current: dict, yyyy_mm: str) -> None:
    """Valida drift; respeita ``MATHOMS_GOLDEN_UPDATE_BASELINE=1`` para aceitar mudança."""
    update_flag = os.environ.get("MATHOMS_GOLDEN_UPDATE_BASELINE") == "1"
    drift = _drift_threshold_exceeded(prev_metrics, current)
    if drift:
        if update_flag:
            _write_baseline(current, yyyy_mm)
            pytest.skip(f"Baseline atualizada manualmente (drift aceito): {drift}")
        pytest.fail(
            "Drift detectado vs baseline anterior:\n  - "
            + "\n  - ".join(drift)
            + f"\n\nPrev: {prev_metrics}\nCurr: {current}"
        )
    _write_baseline(current, yyyy_mm)


@pytest.mark.monthly_real
class TestPlannerGoldenMonthly:
    def test_real_llm_call_succeeds_and_validates_schema(self):
        """Chamada real do LLM gera output que passa no JSON Schema."""
        _real_llm_or_skip()
        e5 = _load_canonical_e5()
        artifact = _call_real_llm(e5)
        # Schema validation já está em parecer_planejador stage; aqui confirma artifact presente.
        assert artifact["_meta"]["cost_usd"] > 0
        assert artifact["diagnostico_geral"]

    def test_drift_vs_baseline_or_create_first(self):
        """Compara métricas estruturais vs último baseline. Sem baseline = cria primeiro."""
        _real_llm_or_skip()
        artifact = _call_real_llm(_load_canonical_e5())
        current = _structural_metrics(artifact)
        yyyy_mm = datetime.now(timezone.utc).strftime("%Y-%m")
        prev_baseline_path = _latest_baseline_path()
        if prev_baseline_path is None:
            path = _write_baseline(current, yyyy_mm)
            pytest.skip(f"Primeiro baseline criado em {path}")
        prev_metrics = json.loads(prev_baseline_path.read_text(encoding="utf-8"))["metrics"]
        _assert_no_drift_or_update(prev_metrics, current, yyyy_mm)
