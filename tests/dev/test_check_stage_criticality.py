"""ADR-357 §1 · A40.l18 — testes do gate `dev/check_stage_criticality.py`."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev.check_stage_criticality import main as gate_main

# Cada caso escreve um `stage_spec.py` sintético e afirma o exit code. Os
# ofensores são as mutações que um refactor REAL faria — acrescentar um add-on
# na cauda e esquecer de decidir, ou marcar a cabeça como degradável — não
# violações artificiais.


def _render(
    *,
    tail_specs: list[str],
    tail_order: list[str],
    head_specs: tuple[str, str] = (
        '"reconcile_transactions": StageSpec("reconcile_transactions"),',
        '"analyze_finances": StageSpec("analyze_finances"),',
    ),
) -> str:
    lines = ["STAGE_REGISTRY = {"]
    lines += [f"    {s}" for s in head_specs]
    lines += [f"    {s}" for s in tail_specs]
    lines += ["}", "", "FULL_ORDER = [", '    "reconcile_transactions",', '    "analyze_finances",']
    lines += [f'    "{n}",' for n in tail_order]
    lines += ["]", ""]
    return "\n".join(lines)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "stage_spec.py"
    path.write_text(content, encoding="utf-8")
    return path


def _spec_file(tmp_path: Path, *, tail: list[str]) -> Path:
    """`stage_spec.py` sintético; `tail` são linhas literais de StageSpec da cauda."""
    names = [t.split('"')[1] for t in tail]
    return _write(tmp_path, _render(tail_specs=tail, tail_order=names))


def test_cauda_declarada_passa(tmp_path: Path) -> None:
    path = _spec_file(
        tmp_path,
        tail=['"generate_narratives": StageSpec("generate_narratives", criticality="degradable"),'],
    )
    assert gate_main([str(path)]) == 0


def test_cauda_sem_declaracao_falha(tmp_path: Path) -> None:
    # A mutação central: add-on novo depois de analyze_finances herdando o
    # default `required` em silêncio — o incidente de origem da ADR-357.
    path = _spec_file(
        tmp_path,
        tail=['"publish_digest": StageSpec("publish_digest"),'],
    )
    assert gate_main([str(path)]) == 1


def test_cauda_pode_declarar_required(tmp_path: Path) -> None:
    # O gate exige DECLARAÇÃO, não o valor `degradable`: o §Delta do co-design
    # (2026-08-06, item 3) recusou forçar a cauda para dentro da classe por CI.
    path = _spec_file(
        tmp_path,
        tail=['"publish_digest": StageSpec("publish_digest", criticality="required"),'],
    )
    assert gate_main([str(path)]) == 0


_TAIL_OK = '"generate_narratives": StageSpec("generate_narratives", criticality="degradable"),'


def test_cabeca_degradavel_falha(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _render(
            tail_specs=[_TAIL_OK],
            tail_order=["generate_narratives"],
            head_specs=(
                '"reconcile_transactions": StageSpec("reconcile_transactions"),',
                '"analyze_finances": StageSpec("analyze_finances", criticality="degradable"),',
            ),
        ),
    )
    assert gate_main([str(path)]) == 1


@pytest.mark.parametrize("bad", ["degradeable", "optional", "REQUIRED", ""])
def test_valor_invalido_falha(tmp_path: Path, bad: str) -> None:
    path = _spec_file(
        tmp_path,
        tail=[f'"generate_narratives": StageSpec("generate_narratives", criticality="{bad}"),'],
    )
    assert gate_main([str(path)]) == 1


def test_commit_flag_em_required_falha(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _render(
            tail_specs=[_TAIL_OK],
            tail_order=["generate_narratives"],
            head_specs=(
                '"reconcile_transactions": StageSpec("reconcile_transactions", commit_artifacts_on_degrade=True),',
                '"analyze_finances": StageSpec("analyze_finances"),',
            ),
        ),
    )
    assert gate_main([str(path)]) == 1


def test_stage_em_full_order_sem_spec_falha(tmp_path: Path) -> None:
    path = _write(tmp_path, _render(tail_specs=[], tail_order=["publish_digest"]))
    assert gate_main([str(path)]) == 1


def test_registry_real_passa() -> None:
    """O gate roda verde contra o `pipeline/stage_spec.py` de produção."""
    assert gate_main([]) == 0
