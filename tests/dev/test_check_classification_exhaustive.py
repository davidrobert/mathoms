"""ADR-235 · A16 — testes do gate `dev/check_classification_exhaustive.py`."""

from __future__ import annotations

from pathlib import Path

from dev.check_classification_exhaustive import main as gate_main


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_ts_switch_without_default_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "renderer.tsx",
        """\
function render(p: { classification: string }) {
  switch (p.classification) {
    case "locado":
      return "Locado";
    case "uso_pessoal":
      return "Uso pessoal";
  }
}
""",
    )
    assert gate_main([str(path)]) == 1


def test_ts_switch_with_default_passes(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "renderer.tsx",
        """\
function render(p: { classification: string }) {
  switch (p.classification) {
    case "locado":
      return "Locado";
    default:
      return "Outro";
  }
}
""",
    )
    assert gate_main([str(path)]) == 0


def test_py_match_without_case_default_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "classifier.py",
        """\
def label(classification: str) -> str:
    match classification:
        case "locado":
            return "Locado"
        case "uso_pessoal":
            return "Uso pessoal"
    return "fallthrough"
""",
    )
    assert gate_main([str(path)]) == 1


def test_py_match_with_case_default_passes(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "classifier.py",
        """\
def label(classification: str) -> str:
    match classification:
        case "locado":
            return "Locado"
        case _:
            return "Outro"
""",
    )
    assert gate_main([str(path)]) == 0


def test_comments_are_ignored(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "doc.tsx",
        """\
// Example doc: avoid `switch (classification)` without default.
function ok() { return 1; }
""",
    )
    assert gate_main([str(path)]) == 0


def test_unrelated_switch_passes(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "other.tsx",
        """\
function f(kind: string) {
  switch (kind) {
    case "a": return 1;
  }
}
""",
    )
    assert gate_main([str(path)]) == 0


def test_match_nested_attribute_detected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "deep.py",
        """\
def label(p):
    match p.classification:
        case "locado":
            return "L"
""",
    )
    assert gate_main([str(path)]) == 1
