"""Gates de integridade do grafo de notas da vault (A40 §Pendência 12 · ADR-182)."""
# Gate A (autorreferência em depends_on/parallel_with/supersedes/superseded_by)
# vive em dev/validate_frontmatter.py — intra-arquivo, então funciona com o
# pass_filenames: true do pre-commit. Gate B (id duplicado entre arquivos) já
# existe em dev/check_doc_links.py; os testes abaixo o PINAM porque aquele
# módulo está em 498/500 linhas e um split futuro pode dropá-lo em silêncio.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_DIR = REPO_ROOT / "dev"
DOCS = REPO_ROOT / "docs"

if str(DEV_DIR) not in sys.path:
    sys.path.insert(0, str(DEV_DIR))


LANE_FIXTURE = """---
id: A99.l1
type: lane
title: "Lane de fixture"
sprint: A99
status: open
{edges}tags:
  - type/lane
---

# A99.l1
"""


def _write_lane(tmp_path: Path, edges: str, name: str = "A99-l1-fixture.md") -> Path:
    """Escreve lane de fixture com o bloco `edges` injetado no frontmatter."""
    path = tmp_path / name
    path.write_text(LANE_FIXTURE.format(edges=edges), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def schemas() -> dict:
    import validate_frontmatter

    return validate_frontmatter.load_schemas()


@pytest.mark.parametrize("field", ["depends_on", "parallel_with"])
def test_self_reference_is_rejected(tmp_path: Path, schemas: dict, field: str) -> None:
    """Nota que se lista no próprio campo de aresta é erro (caso real: A40.l27)."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, f'{field}:\n  - "[[A99.l1]]"\n')
    errors = validate_frontmatter.validate_note(lane, schemas, strict=False)
    assert [e.field for e in errors] == [field], f"gate não pegou autorreferência em {field}"
    assert "autorreferência" in errors[0].message


@pytest.mark.parametrize("raw", ["[[A99.l1]]", "[[A99.l1|apelido]]", "[[A99.l1#Escopo]]"])
def test_self_reference_detected_through_alias_and_anchor(
    tmp_path: Path, schemas: dict, raw: str
) -> None:
    """Alias `|` e anchor `#` não escondem a autorreferência."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, f'depends_on:\n  - "{raw}"\n')
    errors = validate_frontmatter.validate_note(lane, schemas, strict=False)
    assert len(errors) == 1, f"{raw} deveria disparar exatamente 1 erro, deu {len(errors)}"


def test_edge_to_other_note_is_accepted(tmp_path: Path, schemas: dict) -> None:
    """Controle anti-overfire: aresta para OUTRA nota passa."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, 'depends_on:\n  - "[[A99.l2]]"\n')
    assert validate_frontmatter.validate_note(lane, schemas, strict=False) == []


def test_dangling_edge_is_out_of_scope(tmp_path: Path, schemas: dict) -> None:
    """Aresta para id inexistente NÃO é escopo deste gate (é cross-arquivo)."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, 'depends_on:\n  - "[[A99.l999-nao-existe]]"\n')
    assert validate_frontmatter.validate_note(lane, schemas, strict=False) == []


def test_cli_exits_nonzero_on_self_reference(tmp_path: Path) -> None:
    """Prova o contrato do pre-commit: exit code ≠ 0 e campo nomeado no stdout."""
    lane = _write_lane(tmp_path, 'depends_on:\n  - "[[A99.l1]]"\n')
    proc = subprocess.run(
        [sys.executable, str(DEV_DIR / "validate_frontmatter.py"), str(lane)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, f"gate passou verde: {proc.stdout}"
    assert "depends_on" in proc.stdout


def test_live_vault_has_no_self_reference() -> None:
    """A vault viva está limpa — find-replace de renumeração futura falha aqui."""
    import validate_frontmatter as vf

    offenders: list[str] = []
    for md_path in vf.collect_md_files(DOCS):
        try:
            fm = vf.parse_frontmatter(md_path)
        except ValueError:
            continue
        if fm:
            offenders += [
                f"{md_path.relative_to(DOCS)}:{e.field}"
                for e in vf._self_reference_errors(md_path, fm)
            ]
    assert offenders == [], f"autorreferência viva na vault: {offenders}"


def test_duplicate_id_across_files_is_hard_error(tmp_path: Path) -> None:
    """check_doc_links reporta colisão de id como ERRO (não WARN)."""
    import check_doc_links

    _write_lane(tmp_path, "", name="A99-l1-a.md")
    _write_lane(tmp_path, "", name="A99-l1-b.md")
    notes = check_doc_links.collect_notes(tmp_path)
    _index, messages = check_doc_links.build_id_index(notes)
    errors = [m for m in messages if m.startswith("ERRO:")]
    assert len(errors) == 1, f"colisão de id não virou ERRO: {messages}"
    assert "id duplicado 'A99.l1'" in errors[0]


def test_duplicate_id_fails_the_cli(tmp_path: Path) -> None:
    """Colisão de id faz `check_doc_links.py --docs-root` sair 1 (contrato do hook)."""
    _write_lane(tmp_path, "", name="A99-l1-a.md")
    _write_lane(tmp_path, "", name="A99-l1-b.md")
    proc = subprocess.run(
        [sys.executable, str(DEV_DIR / "check_doc_links.py"), "--docs-root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, f"colisão não falhou o gate: {proc.stdout}"
    assert "id duplicado" in proc.stdout


def test_live_vault_has_no_duplicate_id() -> None:
    """Nenhum id colide na vault viva (l27 foi renumerada; isto trava a regressão)."""
    import check_doc_links

    notes = check_doc_links.collect_notes(DOCS)
    _index, messages = check_doc_links.build_id_index(notes)
    assert [m for m in messages if m.startswith("ERRO:")] == []
