"""Golden de paridade — `main(root_dir)` legado vs `main_with_store(ctx)`
(Sessão A5d da Fase 8).

Garante que o Caminho B do E5 produz output idêntico ao legado sobre o
mesmo workspace sintético. Normaliza campos variáveis (timestamps de
``data_analise`` se divergirem entre runs no mesmo segundo são idênticos,
portanto não precisam de normalização).

Cenário: fluxo E3 → E4 → E5 sobre tenant mínimo (1 receita CLT + 1 despesa)
com configs compatíveis com as funções legadas. Roda o legado e o novo
caminho, compara os 2 outputs `analise_financeira-5_analysis.json`
campo-a-campo (tolerância 0.01 BRL em monetários, ordem-insensitive em listas).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


# =============================================================================
# Fixtures (configs mínimas + E3 fixture)
# =============================================================================


_E3_FIXTURE = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e3" / "minimal-conta-com-despesa-3_reconciled.json"
)
_BASELINE_MIN = (
    _REPO / "tests" / "fixtures" / "pipeline_golden" / "e2" / "minimal-baseline-1.5_consolidated.json"
)

_GOALS_MIN = {
    "independencia_financeira": {
        "if_meta": 1_000_000.0,
        "trs_pct": 4.0,
    }
}

_FAMILY_E5 = {
    "titular": "david",
    "membros": {
        "david": {
            "nome_curto": "David",
            "data_nascimento": "1985-06-15",
        }
    },
}

_CATEGORIZATION = {
    "expense_keywords": {"mercado": ["mercado"]},
    "income_keywords": {"receita_clt": ["salario"]},
    "internal_transfer_patterns": [],
    "pj_source_mapping": {},
    "clt_source_mapping": {"empresa": "Empresa X"},
}


def _build_workspace(root: Path) -> None:
    cfg = root / "config"
    cfg.mkdir(parents=True)
    (cfg / "categorization.json").write_text(
        json.dumps(_CATEGORIZATION, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cfg / "family_members.json").write_text(
        json.dumps(_FAMILY_E5, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (cfg / "pipeline.json").write_text("{}", encoding="utf-8")
    (cfg / "goals.json").write_text(
        json.dumps(_GOALS_MIN, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    e3_dir = root / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    # Copia fixture E3.
    e3_payload = json.loads(_E3_FIXTURE.read_text(encoding="utf-8"))
    (e3_dir / "minimal-conta-com-despesa-3_reconciled.json").write_text(
        json.dumps(e3_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Baseline consolidado.
    e2_dir = root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    baseline_payload = json.loads(_BASELINE_MIN.read_text(encoding="utf-8"))
    (e2_dir / "baseline_patrimonial-1.5_consolidated.json").write_text(
        json.dumps(baseline_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_e5_output(root: Path) -> dict:
    path = root / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))


# =============================================================================
# Comparação com tolerância
# =============================================================================


_MONETARY_FIELDS = {
    "bruto", "liquido", "dividas", "residencia", "imoveis_investimento",
    "veiculos", "caixa_moeda_estrangeira", "investivel",
    "receita_total", "receita_recorrente", "receita_one_time",
    "despesa_total", "despesa_mensal_media", "fluxo_liquido",
    "if_meta", "if_gap", "if_trs_monthly_value",
    "total_dividas", "total_pontuais", "folga_mensal",
    "aporte_mensal", "total_liquida", "nivel_6_meses", "nivel_12_meses",
}


def _assert_close(a, b, tol: float = 0.01) -> None:
    if a is None or b is None:
        assert a == b, f"{a} != {b}"
        return
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        assert a == b
        return
    assert abs(fa - fb) <= tol, f"{fa} vs {fb} (diff {abs(fa-fb)} > {tol})"


def _assert_payloads_parity(a: dict, b: dict, *, path: str = "") -> None:
    """Compara payloads E5 campo a campo.

    - Campos monetários (whitelist): tolerância 0.01.
    - Campos ``data_analise`` / ``data_consolidacao``: removidos antes.
    - Listas de dicts: sorted comparison por JSON string.
    """
    a = _normalize_payload(a)
    b = _normalize_payload(b)

    assert set(a.keys()) == set(b.keys()), (
        f"chaves divergiram em {path!r}: "
        f"only_a={set(a) - set(b)} only_b={set(b) - set(a)}"
    )

    for k in a:
        va, vb = a[k], b[k]
        key_path = f"{path}.{k}" if path else k
        _compare_values(va, vb, path=key_path)


def _normalize_payload(payload):
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    # Campos variáveis entre runs.
    out.pop("data_analise", None)
    out.pop("consolidation_date", None)
    out.pop("data_consolidacao", None)
    out.pop("data_processamento", None)
    return out


def _compare_values(a, b, *, path: str) -> None:
    # Campo monetário conhecido (whitelist).
    field_name = path.split(".")[-1]
    if field_name in _MONETARY_FIELDS:
        _assert_close(a, b)
        return

    if isinstance(a, float) or isinstance(b, float):
        try:
            _assert_close(a, b)
            return
        except (TypeError, ValueError):
            pass

    if isinstance(a, dict) and isinstance(b, dict):
        _assert_payloads_parity(a, b, path=path)
        return

    if isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), f"tamanho divergiu em {path}: {len(a)} vs {len(b)}"
        if a and all(isinstance(x, dict) for x in a):
            sa = sorted(
                json.dumps(_normalize_payload(x), sort_keys=True, default=str)
                for x in a
            )
            sb = sorted(
                json.dumps(_normalize_payload(x), sort_keys=True, default=str)
                for x in b
            )
            assert sa == sb, f"lista de dicts divergiu em {path}"
            return
        assert a == b, f"lista divergiu em {path}: {a} vs {b}"
        return

    assert a == b, f"campo divergiu em {path}: {a!r} vs {b!r}"


# =============================================================================
# Runners
# =============================================================================


def _run_legacy_full_pipeline(workspace: Path) -> None:
    """Roda E4 + E5 legados sobre workspace."""
    from scripts import pipeline_common as _pc
    from scripts.e4_categorize import (
        _DEFAULT_BASE_DIR as E4_DEFAULT,
        _init_config as e4_init,
        main as e4_main,
    )
    from scripts.e5_analyze import (
        _DEFAULT_BASE_DIR as E5_DEFAULT,
        _init_config as e5_init,
        main as e5_main,
    )

    original_pc_root = _pc.PROJECT_DIR
    try:
        _pc._init_config(workspace)
        e4_main(root_dir=workspace)
        e5_main(root_dir=workspace)
    except SystemExit as exc:
        if exc.code not in (0, None):
            pytest.fail(f"Pipeline legado saiu com {exc.code}")
    finally:
        _pc._init_config(original_pc_root)
        e4_init(E4_DEFAULT)
        e5_init(E5_DEFAULT)


def _run_new_full_pipeline(workspace: Path) -> None:
    """Roda E4 novo + E5 novo sobre workspace via main_with_store."""
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store as e4_mws
    from scripts.e5_analyze import main_with_store as e5_mws

    ctx = WorkspaceContext(root=workspace)
    e4_mws(ctx)
    e5_mws(ctx)


# =============================================================================
# Testes
# =============================================================================


def test_main_with_store_parity_against_legacy(tmp_path: Path):
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"

    _build_workspace(legacy_root)
    _build_workspace(new_root)

    _run_legacy_full_pipeline(legacy_root)
    _run_new_full_pipeline(new_root)

    legacy_output = _read_e5_output(legacy_root)
    new_output = _read_e5_output(new_root)

    _assert_payloads_parity(legacy_output, new_output)


def test_pipeline_stages_e5_does_not_import_stage_runner_compat():
    """Critério estrutural A5d."""
    src = (_REPO / "pipeline" / "stages" / "e5.py").read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e5.py ainda referencia stage_runner_compat — "
        "Sessão A5d deveria ter migrado para main_with_store direto."
    )
    assert "main_with_store" in src
