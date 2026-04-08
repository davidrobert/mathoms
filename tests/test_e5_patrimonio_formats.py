#!/usr/bin/env python3
"""
Tests for e5_analyze._resolve_members() — ensures all 4 baseline formats
produce valid member dicts with expected structure.

Formats tested:
1. Dict format: members/membros as dict with david/mariana sub-dicts
2. List-of-dicts: membros as list of dicts with "nome" key
3. E1.5 declarations: membros as list of strings + declarations[]
4. Consolidated v1.5: patrimonio_por_ano + investimentos_consolidados + etc.

Run: python tests/test_e5_patrimonio_formats.py
"""

import sys
from pathlib import Path

# Add scripts/ to path so we can import e5_analyze
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from e5_analyze import _resolve_members, analyze_patrimonio, safe_float


def _assert_member_structure(david, mariana, label):
    """Validate that resolved members have expected structure."""
    assert isinstance(david, dict), f"[{label}] david should be dict, got {type(david).__name__}"
    assert isinstance(mariana, dict), f"[{label}] mariana should be dict, got {type(mariana).__name__}"

    # At least one member should have data
    has_data = bool(david) or bool(mariana)
    assert has_data, f"[{label}] Both david and mariana are empty"

    # Check structure of non-empty members
    for name, member in [("david", david), ("mariana", mariana)]:
        if not member:
            continue
        # Should have total_bens or bens
        has_bens = "total_bens" in member or "bens" in member
        assert has_bens, f"[{label}] {name} missing total_bens and bens"


def test_format_1_dict():
    """Format 1: members/membros as dict with david/mariana sub-dicts."""
    baseline = {
        "members": {
            "david": {
                "total_bens": 2500000,
                "total_dividas": 50000,
                "bens": {
                    "imoveis": [{"descricao": "Casa Tasso da Silveira", "valor_31_12_ano_base": 1000000}],
                    "investimentos": [{"descricao": "CDB Santander", "valor_31_12_ano_base": 300000}],
                    "veiculos": [{"descricao": "Fiat Toro", "valor_31_12_ano_base": 190000}],
                    "contas_bancarias": [],
                }
            },
            "mariana": {
                "total_bens": 900000,
                "total_dividas": 0,
                "bens": {
                    "imoveis": [{"descricao": "Apto Living Concept", "valor_31_12_ano_base": 270000}],
                    "investimentos": [{"descricao": "CDB BTG", "valor_31_12_ano_base": 22000}],
                    "veiculos": [],
                    "contas_bancarias": [],
                }
            }
        }
    }

    david, mariana = _resolve_members(baseline)
    _assert_member_structure(david, mariana, "format_1")
    assert safe_float(david.get("total_bens", 0)) == 2500000
    assert safe_float(mariana.get("total_bens", 0)) == 900000
    print("  ✓ Format 1 (dict) — PASS")


def test_format_2_list_of_dicts():
    """Format 2: membros as list of dicts with 'nome' key."""
    baseline = {
        "membros": [
            {
                "nome": "DAVID ROBERT CAMARGO FERREIRA CAMPOS",
                "total_bens": 2500000,
                "bens": {
                    "imoveis": [{"descricao": "Casa Tasso da Silveira", "valor_31_12_ano_base": 1000000}],
                    "investimentos": [],
                    "veiculos": [],
                    "contas_bancarias": [],
                }
            },
            {
                "nome": "MARIANA FERREIRA CAMPOS",
                "total_bens": 900000,
                "bens": {
                    "imoveis": [],
                    "investimentos": [],
                    "veiculos": [],
                    "contas_bancarias": [],
                }
            }
        ]
    }

    david, mariana = _resolve_members(baseline)
    _assert_member_structure(david, mariana, "format_2")
    assert safe_float(david.get("total_bens", 0)) == 2500000
    assert safe_float(mariana.get("total_bens", 0)) == 900000
    print("  ✓ Format 2 (list of dicts) — PASS")


def test_format_3_e15_declarations():
    """Format 3: E1.5 declarations — membros as list of strings + declarations[]."""
    baseline = {
        "pipeline_stage": "E1.5_Baseline_Patrimonial",
        "data_processamento": "2026-04-08",
        "membros": [
            "DAVID ROBERT CAMARGO FERREIRA CAMPOS",
            "MARIANA FERREIRA CAMPOS"
        ],
        "anos_base": [2024],
        "declarations": [
            {
                "membro": "DAVID ROBERT CAMARGO FERREIRA CAMPOS",
                "cpf": "287.766.948-36",
                "ano_base": 2024,
                "bens_direitos": [
                    {"grupo": "01", "codigo": "12", "descricao": "CASA - RUA TASSO DA SILVEIRA", "valor_31_12_atual": 996821.46},
                    {"grupo": "01", "codigo": "11", "descricao": "APARTAMENTO BARAO CAPANEMA", "valor_31_12_atual": 350000.0},
                    {"grupo": "02", "codigo": "01", "descricao": "VEICULO FIAT TORO", "valor_31_12_atual": 191354.0},
                    {"grupo": "04", "codigo": "02", "descricao": "CDB SANTANDER", "valor_31_12_atual": 243285.37},
                    {"grupo": "07", "codigo": "04", "descricao": "FUNDO ALASKA BLACK", "valor_31_12_atual": 60000.0},
                    {"grupo": "06", "codigo": "01", "descricao": "CONTA CORRENTE C6", "valor_31_12_atual": 4936.98},
                ],
                "total_bens": 1846397.81,
            },
            {
                "membro": "MARIANA FERREIRA CAMPOS",
                "cpf": "085.052.396-60",
                "ano_base": 2024,
                "bens_direitos": [
                    {"grupo": "01", "codigo": "11", "descricao": "APTO LIVING CONCEPT", "valor_31_12_atual": 270000.0},
                    {"grupo": "04", "codigo": "02", "descricao": "CDB BTG", "valor_31_12_atual": 22000.0},
                ],
                "total_bens": 292000.0,
            }
        ]
    }

    david, mariana = _resolve_members(baseline)
    _assert_member_structure(david, mariana, "format_3")

    # Check that declaration total_bens is used
    assert safe_float(david.get("total_bens", 0)) == 1846397.81
    assert safe_float(mariana.get("total_bens", 0)) == 292000.0

    # Check bens classification by IRPF grupo
    david_bens = david.get("bens", {})
    assert len(david_bens.get("imoveis", [])) == 2, "David should have 2 imóveis (G01)"
    assert len(david_bens.get("veiculos", [])) == 1, "David should have 1 veículo (G02)"
    assert len(david_bens.get("investimentos", [])) == 2, "David should have 2 investimentos (G04+G07)"
    assert len(david_bens.get("contas_bancarias", [])) == 1, "David should have 1 conta (G06)"

    print("  ✓ Format 3 (E1.5 declarations) — PASS")


def test_format_4_consolidated():
    """Format 4: Consolidated v1.5 — patrimonio_por_ano + listas consolidadas."""
    baseline = {
        "patrimonio_por_ano": {
            "2024": {"total_bens": 3400000, "total_dividas": 50000}
        },
        "imoveis_consolidados": [
            {"descricao": "Casa Tasso", "proprietario": "david", "valores_31_12": {"2024": 1000000}},
            {"descricao": "Apto Calixto", "proprietario": "david", "valores_31_12": {"2024": 350000}},
            {"descricao": "Apto Concept", "proprietario": "mariana", "valores_31_12": {"2024": 270000}},
        ],
        "investimentos_consolidados": [
            {"descricao": "CDB Santander", "tipo": "CDB", "proprietario": "david", "valores_31_12": {"2024": 300000}},
            {"descricao": "CDB BTG", "tipo": "CDB", "proprietario": "mariana", "valores_31_12": {"2024": 22000}},
        ],
        "veiculos_consolidados": [
            {"descricao": "Fiat Toro", "proprietario": "david", "valores_31_12": {"2024": 190000}},
        ],
        "dividas": [
            {"proprietario": "david", "saldo_31_12": {"2024": 50000}},
        ],
    }

    david, mariana = _resolve_members(baseline)
    _assert_member_structure(david, mariana, "format_4")

    # Consolidated uses patrimonio_por_ano.total_bens for authoritative total
    # David synthetic = 1000000 + 350000 + 300000 + 190000 = 1840000
    # Mariana synthetic = 270000 + 22000 = 292000
    # Total synthetic = 2132000 vs pat_ano 3400000 — diff assigned to david
    assert safe_float(david.get("total_bens", 0)) > 0
    assert safe_float(mariana.get("total_bens", 0)) == 292000.0
    assert safe_float(david.get("total_dividas", 0)) == 50000.0

    print("  ✓ Format 4 (consolidated) — PASS")


def test_analyze_patrimonio_with_current_positions():
    """Test that analyze_patrimonio uses current positions when available."""
    # Minimal baseline (format 3)
    baseline = {
        "membros": ["DAVID", "MARIANA"],
        "declarations": [
            {
                "membro": "DAVID",
                "ano_base": 2024,
                "bens_direitos": [
                    {"grupo": "01", "codigo": "12", "descricao": "CASA TASSO DA SILVEIRA", "valor_31_12_atual": 1000000},
                    {"grupo": "02", "codigo": "01", "descricao": "VEICULO", "valor_31_12_atual": 190000},
                    {"grupo": "04", "codigo": "02", "descricao": "CDB old", "valor_31_12_atual": 200000},
                ],
                "total_bens": 1390000,
            },
        ]
    }

    # Current positions (more recent)
    inv_atuais = {
        "dados": [
            {"nome": "CDB new", "membro": "david", "valor_atual": 350000},
        ],
        "total_por_membro": {"david": 350000.0},
        "total_geral": 350000.0,
        "n_posicoes": 1,
        "data_consolidacao": "2026-04-08",
    }

    result = analyze_patrimonio(baseline, investimentos_atuais=inv_atuais)

    assert result["fonte_investimentos"] == "posicoes_atuais"
    assert result["investimentos_david"] == 350000.0  # from current positions, not IRPF 200000
    # bruto = residencia (1M) + veiculos (190k) + investimentos (350k)
    assert result["bruto"] == 1540000.0

    # Without current positions — should use IRPF
    result_irpf = analyze_patrimonio(baseline, investimentos_atuais={"dados": []})
    assert result_irpf["fonte_investimentos"] == "irpf"
    assert result_irpf["investimentos_david"] == 200000.0  # from IRPF

    print("  ✓ analyze_patrimonio with current positions — PASS")


def test_empty_baseline():
    """Edge case: empty baseline should not crash."""
    david, mariana = _resolve_members({})
    assert isinstance(david, dict)
    assert isinstance(mariana, dict)
    print("  ✓ Empty baseline — PASS")


def main():
    print("=" * 60)
    print("E5 Patrimônio Format Tests")
    print("=" * 60)

    tests = [
        test_format_1_dict,
        test_format_2_list_of_dicts,
        test_format_3_e15_declarations,
        test_format_4_consolidated,
        test_analyze_patrimonio_with_current_positions,
        test_empty_baseline,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__} — FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} — ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
