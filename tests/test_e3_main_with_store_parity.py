"""Golden de paridade — `main(root_dir)` legado vs `main_with_store(ctx)`
(Sessão A2 da Fase 6).

Garante que o Caminho B do E3 produz output **idêntico** (a menos de
campos comprovadamente derivados de I/O, como `notas`) ao que o script
legado produzia. Roda os dois caminhos sobre o **mesmo** workspace
sintético em `tmp_path` e compara campo a campo.

Tolerância: `0.01` BRL para campos monetários, exato para os demais.
Ordem-insensitive em `fontes` e `transacoes` (ordenadas por `data`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


# =============================================================================
# Helpers
# =============================================================================


def _build_workspace(root: Path, *, name: str, e2_payloads: dict[str, dict]) -> None:
    """Cria estrutura mínima em ``root`` com config + E2 fixtures."""
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "pipeline.json").write_text(
        json.dumps(
            {
                "reconciliation": {
                    "skip_types": [],
                    "skip_files": [],
                    "tolerances": {
                        "saldo_diff": 0.01,
                        "temporal_gap_days": 4,
                        "baseline_irpf_diff": 1.00,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (cfg_dir / "family_members.json").write_text("{}", encoding="utf-8")
    (cfg_dir / "institutions.json").write_text(
        json.dumps({"banco_canonical": {"itau": "Itaú", "c6bank": "C6 Bank"}}),
        encoding="utf-8",
    )

    e2_dir = root / "processed" / "E2_extracts"
    e2_dir.mkdir(parents=True)
    for filename, payload in e2_payloads.items():
        (e2_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _read_e3_outputs(root: Path) -> dict[str, dict]:
    """Lê todos os ``*-3_reconciled.json`` em ``processed/E3_reconciled``."""
    e3_dir = root / "processed" / "E3_reconciled"
    if not e3_dir.exists():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(e3_dir.glob("*-3_reconciled.json")):
        out[path.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _normalize_for_compare(payload: dict) -> dict:
    """Normaliza um payload E3 para comparação ordem-insensitive."""
    out = dict(payload)
    out["fontes"] = sorted(out.get("fontes") or [])
    txns = list(out.get("transacoes") or [])
    txns.sort(key=lambda t: (t.get("data", ""), t.get("descricao", ""), t.get("valor", 0)))
    out["transacoes"] = txns
    return out


def _assert_money_close(a: float, b: float, *, tol: float = 0.01) -> None:
    assert abs(float(a) - float(b)) <= tol, f"saldo diff {a} vs {b} > {tol}"


def _assert_payloads_parity(legacy: dict, new: dict) -> None:
    """Compara dois payloads E3 com tolerância 0.01 em monetários."""
    a = _normalize_for_compare(legacy)
    b = _normalize_for_compare(new)

    # Campos textuais exatos.
    for field in ("banco", "tipo_conta", "moeda"):
        assert a.get(field) == b.get(field), (
            f"field {field!r} divergiu: legacy={a.get(field)!r} new={b.get(field)!r}"
        )

    assert a["periodo_cobertura"] == b["periodo_cobertura"], (
        f"periodo_cobertura divergiu: legacy={a['periodo_cobertura']} "
        f"new={b['periodo_cobertura']}"
    )

    # Saldos com tolerância.
    _assert_money_close(a["saldo_inicial"], b["saldo_inicial"])
    _assert_money_close(a["saldo_final"], b["saldo_final"])
    assert a["saldo_inicial_unknown"] == b["saldo_inicial_unknown"]
    assert a["saldo_final_unknown"] == b["saldo_final_unknown"]

    # Contagens.
    assert a["transacoes_total"] == b["transacoes_total"]
    assert a["transacoes_duplicadas_removidas"] == b["transacoes_duplicadas_removidas"]

    # Fontes (ordenadas no normalize).
    assert a["fontes"] == b["fontes"]

    # Transações: mesma quantidade + por linha.
    assert len(a["transacoes"]) == len(b["transacoes"])
    for ta, tb in zip(a["transacoes"], b["transacoes"]):
        assert ta.get("data") == tb.get("data")
        assert ta.get("descricao") == tb.get("descricao")
        _assert_money_close(ta.get("valor", 0), tb.get("valor", 0))


def _run_legacy(workspace: Path) -> None:
    """Executa o ``main(root_dir)`` legado, restaurando globals depois."""
    from scripts.e3_reconcile import _DEFAULT_BASE_DIR, _init_config, main as e3_main

    try:
        e3_main(root_dir=workspace)
    except SystemExit as exc:
        if exc.code not in (0, None):
            pytest.fail(f"E3 legado saiu com {exc.code}")
    finally:
        _init_config(_DEFAULT_BASE_DIR)


def _run_new(workspace: Path) -> dict:
    """Executa o ``main_with_store(ctx)`` novo via ``WorkspaceContext``."""
    from pipeline.context import WorkspaceContext
    from scripts.e3_reconcile import main_with_store

    ctx = WorkspaceContext(root=workspace)
    return main_with_store(ctx)


# =============================================================================
# Fixtures de cenário
# =============================================================================


def _conta_extrato_simples() -> dict[str, dict]:
    """1 extrato, sem duplicatas, sem sobreposição."""
    return {
        "itau_extratoconta_202601_202601-2_extract.json": {
            "pipeline_stage": "E2",
            "banco": "itau",
            "tipo": "extratoconta",
            "moeda": "BRL",
            "periodo": {"inicio": "2026-01-01", "fim": "2026-01-31"},
            "saldo_inicial": 1000.00,
            "saldo_final": 870.00,
            "transacoes": [
                {"data": "2026-01-05", "descricao": "MERCADO", "valor": -100.00},
                {"data": "2026-01-10", "descricao": "UBER", "valor": -30.00},
            ],
        }
    }


def _conta_extratos_sobrepostos_com_dup() -> dict[str, dict]:
    """2 extratos da mesma conta no mesmo período, com 1 dup cross-file."""
    base = {
        "pipeline_stage": "E2",
        "banco": "itau",
        "tipo": "extratoconta",
        "moeda": "BRL",
        "periodo": {"inicio": "2026-01-01", "fim": "2026-01-31"},
    }
    return {
        "itau_extratoconta_202601_202601_a-2_extract.json": {
            **base,
            "saldo_inicial": 1000.00,
            "saldo_final": 870.00,
            "transacoes": [
                {"data": "2026-01-05", "descricao": "MERCADO", "valor": -100.00},
                {"data": "2026-01-10", "descricao": "UBER", "valor": -30.00},
            ],
        },
        "itau_extratoconta_202601_202601_b-2_extract.json": {
            **base,
            "saldo_inicial": 1000.00,
            "saldo_final": 790.00,
            "transacoes": [
                {"data": "2026-01-05", "descricao": "MERCADO", "valor": -100.00},
                {"data": "2026-01-15", "descricao": "RESTAURANTE", "valor": -80.00},
            ],
        },
    }


# =============================================================================
# Testes de paridade
# =============================================================================


@pytest.mark.parametrize(
    "scenario_name,build_payloads",
    [
        ("conta_simples", _conta_extrato_simples),
        ("conta_sobrepostos_com_dup", _conta_extratos_sobrepostos_com_dup),
    ],
)
def test_main_with_store_parity_against_legacy(
    tmp_path: Path,
    scenario_name: str,
    build_payloads,
):
    """Roda ambos os caminhos no mesmo cenário sintético; output deve bater."""
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"

    payloads = build_payloads()
    _build_workspace(legacy_root, name=scenario_name, e2_payloads=payloads)
    _build_workspace(new_root, name=scenario_name, e2_payloads=payloads)

    _run_legacy(legacy_root)
    _run_new(new_root)

    legacy_outputs = _read_e3_outputs(legacy_root)
    new_outputs = _read_e3_outputs(new_root)

    assert sorted(legacy_outputs.keys()) == sorted(new_outputs.keys()), (
        f"filenames divergiram entre caminhos: "
        f"legacy={sorted(legacy_outputs)} new={sorted(new_outputs)}"
    )

    for filename in legacy_outputs:
        _assert_payloads_parity(legacy_outputs[filename], new_outputs[filename])


def test_pipeline_stages_e3_does_not_import_stage_runner_compat():
    """Critério de aceite formal da Sessão A2: o wrapper E3 não usa mais o
    ``MaterializationBridge`` (via ``stage_runner_compat``)."""
    e3_wrapper = Path(__file__).resolve().parents[1] / "pipeline" / "stages" / "e3.py"
    src = e3_wrapper.read_text(encoding="utf-8")
    assert "stage_runner_compat" not in src, (
        "pipeline/stages/e3.py ainda referencia stage_runner_compat — "
        "Sessão A2 deveria ter migrado para chamada direta a main_with_store."
    )
    assert "main_with_store" in src, (
        "pipeline/stages/e3.py deveria chamar main_with_store após Sessão A2."
    )
