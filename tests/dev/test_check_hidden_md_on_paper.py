"""Prova por mutação do gate A40.l54: `hidden md:block` novo sem par falha."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "dev"))

from check_hidden_md_on_paper import (  # noqa: E402
    line_offends,
    main,
    offenders,
)


def test_hidden_md_block_without_print_fails(tmp_path: Path) -> None:
    orphan = tmp_path / "NewDesktopOnly.tsx"
    orphan.write_text('<div className="hidden overflow-x-auto md:block">tabela</div>\n')
    assert main(["--root", str(tmp_path)]) == 1
    assert any(path == orphan for path, _lineno, _text in offenders(tmp_path))


def test_md_hidden_stack_without_print_fails(tmp_path: Path) -> None:
    orphan = tmp_path / "MobileOnly.tsx"
    orphan.write_text('<ul className="space-y-3 md:hidden">cards</ul>\n')
    assert main(["--root", str(tmp_path)]) == 1


def test_md_hidden_com_print_hidden_passa(tmp_path: Path) -> None:
    """A40.l6: o stack mobile some do papel — companheiro correto da direção `md:hidden`."""
    ok = tmp_path / "MdPair.tsx"
    ok.write_text(
        '<div className="space-y-3 md:hidden print:hidden">cards</div>\n'
        '<div className="hidden overflow-x-auto md:block print:block">tabela</div>\n'
    )
    assert main(["--root", str(tmp_path)]) == 0


def test_companheiro_da_direcao_errada_nao_salva() -> None:
    """O gate é direcional: `print:` qualquer não basta (A40.l6)."""
    # Direção A quer APARECER no papel; `print:hidden` some das duas superfícies.
    assert line_offends('className="hidden md:block print:hidden"')
    # Direção B quer SUMIR do papel; `print:block` empurra o stack mobile pra folha.
    assert line_offends('className="space-y-3 md:hidden print:block"')


def test_sm_pair_passes(tmp_path: Path) -> None:
    ok = tmp_path / "SmPair.tsx"
    ok.write_text(
        '<div className="hidden sm:block">tabela</div>\n' '<div className="sm:hidden">stack</div>\n'
    )
    assert main(["--root", str(tmp_path)]) == 0


def test_print_table_cell_companion_passes(tmp_path: Path) -> None:
    ok = tmp_path / "PrintCol.tsx"
    ok.write_text(
        '<td className="hidden whitespace-nowrap print:table-cell md:table-cell">Membro</td>\n'
    )
    assert main(["--root", str(tmp_path)]) == 0


def test_md_table_cell_without_print_fails() -> None:
    assert line_offends('className="hidden md:table-cell"')
    assert not line_offends('className="hidden print:table-cell md:table-cell"')
    assert not line_offends('className="hidden sm:block"')


def test_repo_report_tree_is_clean() -> None:
    assert main([]) == 0
