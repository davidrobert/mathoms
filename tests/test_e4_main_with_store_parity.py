"""Golden de paridade — `main(root_dir)` legado vs `main_with_store(ctx)`
(Sessão A4b da Fase 7).

Garante que o Caminho B do E4 produz output idêntico ao `main(root_dir)`
legado sobre o mesmo workspace sintético. Normaliza campos variáveis
(timestamps de ``consolidation_date``) antes de comparar. Valor com
tolerância 0.01 BRL.

Cenários parametrizados:
- ``receitas_despesas_simples`` — 1 CLT + 2 despesas, sem baseline.
- ``com_baseline_e_investimentos`` — E3 + baseline v2 + 1 posição BTG.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


# =============================================================================
# Helpers — workspace builder
# =============================================================================


# Mínimos: só o que `e4_categorize._init_config` precisa ler.
_CATEGORIZATION = {
    "expense_keywords": {
        "mercado": ["mercado"],
        "uber": ["uber"],
    },
    "income_keywords": {
        "receita_clt": ["salario"],
    },
    "internal_transfer_patterns": [],
    "pj_source_mapping": {},
    "clt_source_mapping": {"empresa": "Empresa X CLT"},
}

_FAMILY: dict = {"transferencias_internas": {"patterns_pix": [], "recipients": [], "patterns_bank_specific": {}, "patterns_global": []}}

_PIPELINE = {"reconciliation": {}}


def _build_workspace(root: Path, *, e3_accounts: dict[str, dict], baseline: dict | None = None, e2_positions: dict[str, dict] | None = None) -> None:
    """Monta workspace com configs + E3 + opcional baseline + opcional posições."""
    cfg = root / "config"
    cfg.mkdir(parents=True)
    (cfg / "categorization.json").write_text(json.dumps(_CATEGORIZATION), encoding="utf-8")
    (cfg / "family_members.json").write_text(json.dumps(_FAMILY), encoding="utf-8")
    (cfg / "pipeline.json").write_text(json.dumps(_PIPELINE), encoding="utf-8")

    # Diretórios processed/
    e3_dir = root / "processed" / "E3_reconciled"
    e3_dir.mkdir(parents=True)
    e2_dir = root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)

    for name, payload in e3_accounts.items():
        (e3_dir / f"{name}-3_reconciled.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if baseline is not None:
        (e2_dir / "baseline_patrimonial-1.5_consolidated.json").write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    for name, payload in (e2_positions or {}).items():
        (e2_dir / f"{name}-2_extract.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _read_e4_outputs(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    e4_dir = root / "processed" / "E4_unified"
    if not e4_dir.exists():
        return out
    for path in sorted(e4_dir.glob("*-4_unified.json")):
        out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _normalize_payload(payload: dict) -> dict:
    """Remove campos variáveis que diferem entre execuções."""
    out = dict(payload)
    # Timestamps.
    out.pop("consolidation_date", None)
    out.pop("data_consolidacao", None)
    out.pop("data_processamento", None)
    return out


def _assert_close(a: float, b: float, *, tol: float = 0.01) -> None:
    assert abs(float(a) - float(b)) <= tol, f"valor diff {a} vs {b} > {tol}"


def _assert_payloads_parity(legacy: dict, new: dict, *, path: str = "") -> None:
    """Compara dois payloads E4 campo a campo. Tolera:
    - ``consolidation_date`` / ``data_consolidacao`` / ``data_processamento``
      (removidos antes de comparar)
    - Floats com tolerância 0.01
    - Listas potencialmente reordenadas (comparação por conteúdo)
    """
    a = _normalize_payload(legacy)
    b = _normalize_payload(new)

    assert set(a.keys()) == set(b.keys()), (
        f"chaves divergiram em {path}: "
        f"only_legacy={set(a) - set(b)} only_new={set(b) - set(a)}"
    )

    for k in a:
        va, vb = a[k], b[k]
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
        assert len(a) == len(b), f"tamanho de lista divergiu em {path}: {len(a)} vs {len(b)}"
        # Para listas de dict, não garantimos ordem — tentamos uma
        # correspondência relaxada. Para escalares, comparamos posicionalmente.
        if a and all(isinstance(x, dict) for x in a):
            # Compara por cardinalidade de JSON-serialized (ignora ordem
            # de chaves dentro do dict).
            serialized_a = sorted(
                json.dumps(_normalize_payload(x) if isinstance(x, dict) else x, sort_keys=True, default=str)
                for x in a
            )
            serialized_b = sorted(
                json.dumps(_normalize_payload(x) if isinstance(x, dict) else x, sort_keys=True, default=str)
                for x in b
            )
            assert serialized_a == serialized_b, f"lista de dicts divergiu em {path}"
            return
        assert a == b, f"lista divergiu em {path}: {a} vs {b}"
        return

    assert a == b, f"campo divergiu em {path}: {a!r} vs {b!r}"


def _run_legacy(workspace: Path) -> None:
    from scripts import pipeline_common as _pc
    from scripts.e4_categorize import _init_config, main as e4_main

    # O `e4_categorize._init_config(workspace)` configura globals do próprio
    # módulo, mas NÃO reinicializa `pipeline_common.CONFIG_DIR` — que
    # `_load_json_config_from` usa via `_pc.load_json_config`. Forçamos o
    # pipeline_common para apontar ao workspace do teste; senão o legacy
    # leria as configs globais do repo e divergeria do Caminho B.
    original_pc_root = _pc.PROJECT_DIR
    _pc._init_config(workspace)
    try:
        e4_main(root_dir=workspace)
    except SystemExit as exc:
        if exc.code not in (0, None):
            pytest.fail(f"E4 legado saiu com {exc.code}")
    finally:
        # Restaurar pipeline_common + e4 globals para o estado default.
        _pc._init_config(original_pc_root)
        from scripts import e4_categorize as _e4
        _init_config(_e4._DEFAULT_BASE_DIR)


def _run_new(workspace: Path) -> dict:
    from pipeline.context import WorkspaceContext
    from scripts.e4_categorize import main_with_store

    ctx = WorkspaceContext(root=workspace)
    return main_with_store(ctx)


# =============================================================================
# Cenários
# =============================================================================


def _cenario_receitas_despesas_simples() -> dict:
    return {
        "e3_accounts": {
            "itau_extratoconta_BRL_202601_202601": {
                "banco": "Itaú",
                "tipo_conta": "extratoconta",
                "titular": "david",
                "moeda": "BRL",
                "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-01-31"},
                "saldo_inicial": 1000.0,
                "saldo_inicial_unknown": False,
                "saldo_final": 4700.0,
                "saldo_final_unknown": False,
                "fontes": ["itau_202601-2_extract.json"],
                "transacoes_total": 3,
                "transacoes_duplicadas_removidas": 0,
                "transacoes": [
                    {"data": "2026-01-05", "descricao": "SALARIO EMPRESA", "valor": 5000.0, "tipo": "credito"},
                    {"data": "2026-01-10", "descricao": "MERCADO PAO", "valor": -200.0, "tipo": "debito"},
                    {"data": "2026-01-15", "descricao": "UBER 2026-01", "valor": -100.0, "tipo": "debito"},
                ],
            },
        },
    }


def _cenario_com_baseline_e_investimentos() -> dict:
    return {
        "e3_accounts": {
            "itau_extratoconta_BRL_202601_202601": {
                "banco": "Itaú",
                "tipo_conta": "extratoconta",
                "titular": "david",
                "moeda": "BRL",
                "periodo_cobertura": {"inicio": "2026-01-01", "fim": "2026-01-31"},
                "saldo_inicial": 0.0,
                "saldo_inicial_unknown": False,
                "saldo_final": 5000.0,
                "saldo_final_unknown": False,
                "fontes": ["itau_202601-2_extract.json"],
                "transacoes_total": 1,
                "transacoes_duplicadas_removidas": 0,
                "transacoes": [
                    {"data": "2026-01-05", "descricao": "SALARIO EMPRESA", "valor": 5000.0, "tipo": "credito"},
                ],
            },
        },
        "baseline": {
            "pipeline_stage": "E1.5_Baseline_Patrimonial",
            "data_processamento": "2025-06-30",
            "membros": ["David"],
            "patrimonio_por_ano": {
                "2024": {"total_bens": 1_000_000.0, "total_dividas": 100_000.0}
            },
        },
        "e2_positions": {
            "btg_investimentosposicao_202603": {
                "banco": "BTG Pactual",
                "instituicao": "BTG Pactual",
                "tipo": "investimentosposicao",
                "membro": "david",
                "data_referencia": "2026-03-31",
                "saldo_atual": 100_000.0,
                "posicoes": [
                    {"nome": "Tesouro 2030", "tipo": "tesouro", "valor_total": 100_000.0},
                ],
            },
        },
    }


# =============================================================================
# Testes de paridade
# =============================================================================


@pytest.mark.parametrize(
    "scenario_name,build_scenario",
    [
        ("receitas_despesas_simples", _cenario_receitas_despesas_simples),
        ("com_baseline_e_investimentos", _cenario_com_baseline_e_investimentos),
    ],
)
def test_main_with_store_parity_against_legacy(tmp_path: Path, scenario_name: str, build_scenario):
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"

    scenario = build_scenario()
    _build_workspace(legacy_root, **scenario)
    _build_workspace(new_root, **scenario)

    _run_legacy(legacy_root)
    _run_new(new_root)

    legacy_outputs = _read_e4_outputs(legacy_root)
    new_outputs = _read_e4_outputs(new_root)

    assert sorted(legacy_outputs.keys()) == sorted(new_outputs.keys()), (
        f"filenames divergiram: legacy={sorted(legacy_outputs)} new={sorted(new_outputs)}"
    )

    for filename in legacy_outputs:
        _assert_payloads_parity(
            legacy_outputs[filename], new_outputs[filename], path=filename
        )


def test_pipeline_stages_e4_does_not_import_stage_runner_compat():
    """Critério estrutural da Sessão A4b: o wrapper E4 não usa mais bridge."""
    e4_wrapper = Path(__file__).resolve().parents[1] / "pipeline" / "stages" / "e4.py"
    src = e4_wrapper.read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e4.py ainda referencia stage_runner_compat — "
        "Sessão A4b deveria ter migrado para chamada direta a main_with_store."
    )
    assert "main_with_store" in src, (
        "pipeline/stages/e4.py deveria chamar main_with_store após Sessão A4b."
    )
