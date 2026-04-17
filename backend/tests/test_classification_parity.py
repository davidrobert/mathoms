"""P2.3 — paridade: nome canônico E0 reproduz institution/doc_type do roteamento."""

import pytest

from scripts.e0_route import build_final_name, classify_by_name


@pytest.mark.parametrize(
    ("institution", "doc_type", "dest_group", "period"),
    [
        ("itau", "extratocontabrl", "extratos", "2026-04"),
        ("c6bank", "faturaunique", "faturas", "2026-03"),
        ("bradesco", "extratocontabrl", "extratos", "2025-12"),
    ],
)
def test_canonical_filename_parseable_by_classify_by_name(
    institution: str,
    doc_type: str,
    dest_group: str,
    period: str,
):
    """O mesmo ``build_final_name`` usado após classificação deve ser re-parseável
    por ``classify_by_name`` (regex de filename), evitando drift entre pasta física
    e convenções de nome quando o pipeline/CLI processam só o basename.
    """
    routing = {
        "institution": institution,
        "doc_type": doc_type,
        "dest_group": dest_group,
        "period": period,
        "member": None,
        "source": "parity_test",
    }
    final = build_final_name(routing, ".pdf")
    parsed = classify_by_name(final)
    assert parsed is not None, f"classify_by_name failed for {final!r}"
    assert parsed["doc_type"] == doc_type
    assert parsed["institution"] == institution
