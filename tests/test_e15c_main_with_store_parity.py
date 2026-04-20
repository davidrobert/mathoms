"""Golden de paridade — `main(root_dir)` legado vs `main_with_store(ctx)`
(Sessão A5f da Fase 8).

Garante que o Caminho B do E1.5c produz output idêntico ao `main(root_dir)`
legado sobre o mesmo workspace sintético.

Cenários:
- ``cenario_itens_simples`` — baseline formato itens[] (schema atual E1.5 LLM):
  1 imóvel + 1 investimento; sem dívidas.
- ``cenario_declarations_legado`` — baseline formato declarations[] (schema
  legado): 1 membro com 2 bens e 1 dívida.

Teste estrutural:
- ``pipeline/stages/e15c.py`` não referencia ``stage_runner_compat``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

# =============================================================================
# Helpers — workspace builder
# =============================================================================

_FAMILY: dict = {
    "titular": "david",
    "membros": {"david": {"nome": "David"}},
    "imovel_match_keywords": ["apto", "apartamento"],
}

_PIPELINE: dict = {}


def _build_workspace(root: Path, *, baseline: dict) -> None:
    """Monta workspace mínimo com config + baseline no caminho E1.5c."""
    cfg = root / "config"
    cfg.mkdir(parents=True)
    (cfg / "family_members.json").write_text(
        json.dumps(_FAMILY), encoding="utf-8"
    )
    (cfg / "pipeline.json").write_text(json.dumps(_PIPELINE), encoding="utf-8")

    e2_dir = root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    # E1.5c lê e escreve no mesmo arquivo (baseline_patrimonial-1.5_consolidated.json)
    (e2_dir / "baseline_patrimonial-1.5_consolidated.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_consolidated(root: Path) -> dict:
    path = (
        root
        / "processed"
        / "E2_extracts"
        / "baseline_patrimonial-1.5_consolidated.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_close(a: float, b: float, *, tol: float = 0.01) -> None:
    assert abs(float(a) - float(b)) <= tol, f"valor diff {a} vs {b} > {tol}"


def _assert_payloads_parity(legacy: dict, new: dict, *, path: str = "") -> None:
    """Compara dois payloads campo a campo. Tolera floats (0.01 BRL)."""
    assert set(legacy.keys()) == set(new.keys()), (
        f"chaves divergiram em {path!r}: "
        f"only_legacy={set(legacy) - set(new)} only_new={set(new) - set(legacy)}"
    )
    for k in legacy:
        va, vb = legacy[k], new[k]
        key_path = f"{path}.{k}" if path else k
        _compare_values(va, vb, path=key_path)


def _compare_values(a, b, *, path: str) -> None:
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
        assert len(a) == len(b), (
            f"tamanho de lista divergiu em {path!r}: {len(a)} vs {len(b)}"
        )
        if a and all(isinstance(x, dict) for x in a):
            serialized_a = sorted(
                json.dumps(x, sort_keys=True, default=str) for x in a
            )
            serialized_b = sorted(
                json.dumps(x, sort_keys=True, default=str) for x in b
            )
            assert serialized_a == serialized_b, (
                f"lista de dicts divergiu em {path!r}"
            )
            return
        assert a == b, f"lista divergiu em {path!r}: {a} vs {b}"
        return

    assert a == b, f"campo divergiu em {path!r}: {a!r} vs {b!r}"


# =============================================================================
# Runners
# =============================================================================


def _run_legacy(workspace: Path) -> None:
    from scripts.e15_consolidate import _DEFAULT_BASE_DIR, _init_config
    from scripts.e15_consolidate import main as e15c_main

    original_dir = _DEFAULT_BASE_DIR
    try:
        e15c_main(root_dir=workspace)
    except SystemExit as exc:
        if exc.code not in (0, None):
            pytest.fail(f"E1.5c legado saiu com código {exc.code}")
    finally:
        _init_config(original_dir)


def _run_new(workspace: Path) -> dict:
    from pipeline.context import WorkspaceContext
    from scripts.e15_consolidate import main_with_store

    ctx = WorkspaceContext(root=workspace)
    return main_with_store(ctx)


# =============================================================================
# Cenários
# =============================================================================


def _cenario_itens_simples() -> dict:
    """Baseline no formato itens[] (schema atual do E1.5 LLM)."""
    return {
        "itens": [
            {
                "codigo": "G01",
                "descricao": "Apartamento Centro",
                "categoria": "imovel",
                "valor_brl": 500000.0,
                "membro": "david",
                "ano": 2024,
            },
            {
                "codigo": "G07",
                "descricao": "Fundo de Investimento XYZ",
                "categoria": "investimento",
                "valor_brl": 80000.0,
                "membro": "david",
                "ano": 2024,
            },
        ],
        "resumo": {
            "total_ativos": 580000.0,
            "total_passivos": 0.0,
            "patrimonio_liquido": 580000.0,
            "ano_referencia": 2024,
            "membros": ["David"],
        },
        "_meta": {"stage": "E1.5_Baseline_Patrimonial"},
    }


def _cenario_declarations_legado() -> dict:
    """Baseline no formato declarations[] (schema legado do E1.5 LLM)."""
    return {
        "declarations": [
            {
                "membro": "david",
                "ano_base": 2023,
                "bens_direitos": [
                    {
                        "grupo": "01",
                        "descricao": "Apartamento Residencial",
                        "situacao_atual": 450000.0,
                        "situacao_anterior": 420000.0,
                    },
                    {
                        "grupo": "07",
                        "descricao": "Fundo Multimercado",
                        "situacao_atual": 60000.0,
                        "situacao_anterior": 55000.0,
                    },
                ],
                "dividas": [
                    {
                        "descricao": "Financiamento imobiliário",
                        "situacao_atual": 200000.0,
                        "situacao_anterior": 220000.0,
                    },
                ],
            }
        ],
        "imoveis_xlsx": [],
        "veiculos_xlsx": [],
    }


# =============================================================================
# Testes de paridade
# =============================================================================


@pytest.mark.parametrize(
    "scenario_name,build_baseline",
    [
        ("itens_simples", _cenario_itens_simples),
        ("declarations_legado", _cenario_declarations_legado),
    ],
)
def test_main_with_store_parity_against_legacy(
    tmp_path: Path, scenario_name: str, build_baseline
):
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"

    baseline = build_baseline()
    _build_workspace(legacy_root, baseline=baseline)
    _build_workspace(new_root, baseline=baseline)

    _run_legacy(legacy_root)
    _run_new(new_root)

    legacy_out = _read_consolidated(legacy_root)
    new_out = _read_consolidated(new_root)

    _assert_payloads_parity(legacy_out, new_out, path=scenario_name)


def test_main_with_store_skip_when_no_baseline(tmp_path: Path) -> None:
    """main_with_store retorna skipped quando não há baseline (free tier)."""
    from pipeline.context import WorkspaceContext
    from scripts.e15_consolidate import main_with_store

    root = tmp_path / "empty"
    root.mkdir()
    (root / "config").mkdir()
    (root / "config" / "family_members.json").write_text(
        json.dumps(_FAMILY), encoding="utf-8"
    )
    (root / "config" / "pipeline.json").write_text(
        json.dumps(_PIPELINE), encoding="utf-8"
    )

    ctx = WorkspaceContext(root=root)
    result = main_with_store(ctx)

    assert result["success"] is True
    assert result.get("skipped") is True


# =============================================================================
# Teste estrutural
# =============================================================================


def test_pipeline_stages_e15c_does_not_import_stage_runner_compat():
    """Critério estrutural da Sessão A5f: wrapper E1.5c não usa mais bridge."""
    wrapper = _REPO / "pipeline" / "stages" / "e15c.py"
    src = wrapper.read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e15c.py ainda referencia stage_runner_compat — "
        "Sessão A5f deveria ter migrado para chamada direta a main_with_store."
    )
    assert "MaterializationBridge" not in src, (
        "pipeline/stages/e15c.py ainda referencia MaterializationBridge — "
        "Sessão A5f deveria ter removido o bridge."
    )
    assert "main_with_store" in src, (
        "pipeline/stages/e15c.py deveria chamar main_with_store após Sessão A5f."
    )
