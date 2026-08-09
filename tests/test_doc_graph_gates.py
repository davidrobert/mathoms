"""Gates de integridade do grafo de notas da vault (A40 §Pendência 12 · A40.l23 · ADR-182)."""
# Gate A (autorreferência em depends_on/parallel_with/supersedes/superseded_by)
# vive em dev/validate_frontmatter.py — intra-arquivo, então funciona com o
# pass_filenames: true do pre-commit. Gate B (id duplicado entre arquivos) já
# existe em dev/check_doc_links.py; os testes abaixo o PINAM porque aquele
# módulo está em 498/500 linhas e um split futuro pode dropá-lo em silêncio.
#
# A40.l23 acrescentou quatro gates, cada um com prova de mutação abaixo:
#   C  aresta órfã de frontmatter ....... dev/check_doc_graph_refs.py
#   D  coerência path ↔ sprint .......... dev/check_doc_filename_id.py
#   E  former_ids (renumeração auditável) docs/_schemas/note-lane.schema.json
#   F  ADR-NNN em prosa resolve ......... dev/check_adr_prose_refs.py

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


# ----------------------------------------------------------------------
# Gate C — aresta órfã de frontmatter (A40.l23 item 1b)
# ----------------------------------------------------------------------


def _write_vault_lane(tmp_path: Path, edges: str) -> Path:
    """Vault mínima com uma lane; o gate C varre por rglob, não por sprint/."""
    lane = _write_lane(tmp_path, edges)
    return lane


def test_dangling_frontmatter_edge_is_rejected(tmp_path: Path) -> None:
    """O caso que passava nos CINCO gates de doc: alvo de aresta que não existe."""
    import check_doc_graph_refs

    _write_vault_lane(tmp_path, 'depends_on:\n  - "[[A99.l999-nao-existe]]"\n')
    broken = check_doc_graph_refs.broken_edges(tmp_path)
    assert [(f, t) for _p, f, t in broken] == [("depends_on", "A99.l999-nao-existe")]


@pytest.mark.parametrize(
    "field,value",
    [
        ("parallel_with", '  - "[[nao-existe]]"\n'),
        ("adrs", '  - "[[ADR-999]]"\n'),
        ("adrs_canonical", '  - "[[ADR-999]]"\n'),
    ],
)
def test_dangling_edge_detected_in_every_edge_field(tmp_path: Path, field: str, value: str) -> None:
    """`adrs_canonical` está fora do schema mas vive em 16 lanes — foi medido, não presumido."""
    import check_doc_graph_refs

    _write_vault_lane(tmp_path, f"{field}:\n{value}")
    assert len(check_doc_graph_refs.broken_edges(tmp_path)) == 1


def test_edge_to_existing_note_passes(tmp_path: Path) -> None:
    """Controle anti-overfire: aresta cujo alvo existe na mesma vault passa."""
    import check_doc_graph_refs

    _write_vault_lane(tmp_path, 'depends_on:\n  - "[[A99.l2]]"\n')
    (tmp_path / "A99-l2-outra.md").write_text(
        LANE_FIXTURE.format(edges="").replace("A99.l1", "A99.l2"), encoding="utf-8"
    )
    assert check_doc_graph_refs.broken_edges(tmp_path) == []


def test_alias_resolves_the_edge(tmp_path: Path) -> None:
    """Aresta de frontmatter resolve por alias, mesma regra do wikilink de corpo."""
    import check_doc_graph_refs

    _write_vault_lane(tmp_path, 'depends_on:\n  - "[[apelido-da-outra]]"\n')
    other = LANE_FIXTURE.format(edges='aliases: ["apelido-da-outra"]\n').replace("A99.l1", "A99.l2")
    (tmp_path / "A99-l2-outra.md").write_text(other, encoding="utf-8")
    assert check_doc_graph_refs.broken_edges(tmp_path) == []


def test_cli_exits_nonzero_on_dangling_edge(tmp_path: Path) -> None:
    """Contrato do hook: EXIT≠0 e o campo ofensor nomeado no stdout."""
    _write_vault_lane(tmp_path, 'depends_on:\n  - "[[A99.l999-nao-existe]]"\n')
    proc = subprocess.run(
        [sys.executable, str(DEV_DIR / "check_doc_graph_refs.py"), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, f"gate passou verde: {proc.stdout}"
    assert "depends_on" in proc.stdout and "A99.l999-nao-existe" in proc.stdout


def test_live_vault_has_no_dangling_edge() -> None:
    """As 2 violações pré-existentes saíram no mesmo PR que criou o gate."""
    import check_doc_graph_refs

    broken = check_doc_graph_refs.broken_edges(DOCS)
    assert broken == [], f"aresta órfã viva: {[(str(p), f, t) for p, f, t in broken]}"


def test_live_vault_plan_refs_still_valid() -> None:
    """O gate herdado (`lane.plan`) não regrediu na fusão com o de arestas."""
    import check_doc_graph_refs

    assert check_doc_graph_refs.broken_plan_refs(DOCS) == []


# ----------------------------------------------------------------------
# Gate D — coerência path ↔ sprint (A40.l23 item 2)
# ----------------------------------------------------------------------


def test_lane_in_wrong_sprint_dir_is_rejected(tmp_path: Path) -> None:
    """Mover lane trocando só o campo `sprint` passava nos cinco gates de doc."""
    import check_doc_filename_id as gate

    home = tmp_path / "docs" / "sprint" / "A42" / "lanes"
    home.mkdir(parents=True)
    lane = home / "A99-l1-fixture.md"
    lane.write_text(LANE_FIXTURE.format(edges=""), encoding="utf-8")
    err, _warn = gate.check_note(lane, gate.parse_frontmatter(lane))
    assert err is not None and "A42" in err and "A99" in err


def test_lane_in_right_sprint_dir_passes(tmp_path: Path) -> None:
    """Controle anti-overfire: a mesma lane no diretório certo passa."""
    import check_doc_filename_id as gate

    home = tmp_path / "docs" / "sprint" / "A99" / "lanes"
    home.mkdir(parents=True)
    lane = home / "A99-l1-fixture.md"
    lane.write_text(LANE_FIXTURE.format(edges=""), encoding="utf-8")
    assert gate.check_note(lane, gate.parse_frontmatter(lane)) == (None, None)


def test_live_vault_lane_homes_are_coherent() -> None:
    """As 307 lanes vivas já satisfazem o gate — ele nasce verde."""
    import check_doc_filename_id as gate

    offenders = [
        f"{p.relative_to(DOCS)}: {gate._check_lane_home(fm.get('sprint'), p)}"
        for p in sorted(DOCS.glob("sprint/*/lanes/*.md"))
        if (fm := gate.parse_frontmatter(p)) and gate._check_lane_home(fm.get("sprint"), p)
    ]
    assert offenders == [], f"lane fora da casa: {offenders}"


# ----------------------------------------------------------------------
# Gate E — former_ids torna a renumeração auditável (A40.l23 item 3)
# ----------------------------------------------------------------------


def test_former_ids_rejects_id_outside_pattern(tmp_path: Path, schemas: dict) -> None:
    """Campo aditivo sem validação seria decorativo — o pattern é o gate."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, 'former_ids: ["id invalido!!"]\n')
    errors = validate_frontmatter.validate_note(lane, schemas, strict=False)
    assert [e.field for e in errors] == ["former_ids.0"]


def test_former_ids_accepts_real_renumbering(tmp_path: Path, schemas: dict) -> None:
    """Controle: os dois casos vivos da A40 são valores válidos."""
    import validate_frontmatter

    lane = _write_lane(tmp_path, 'former_ids: ["A41.l1", "A40.l25", "A40.l26"]\n')
    assert validate_frontmatter.validate_note(lane, schemas, strict=False) == []


@pytest.mark.parametrize(
    "lane_file,expected",
    [
        ("A40/lanes/A40-l24-gate-0-llm-no-boundary-do-sdk.md", ["A41.l1"]),
        ("A40/lanes/A40-l27-orfao-de-dispatch-residual.md", ["A40.l25", "A40.l26"]),
    ],
)
def test_known_renumberings_are_recorded(lane_file: str, expected: list[str]) -> None:
    """Sem retroaplicação o campo nasce sem os dois únicos casos que existem."""
    import check_doc_filename_id as gate

    fm = gate.parse_frontmatter(DOCS / "sprint" / lane_file)
    assert fm is not None and fm.get("former_ids") == expected


def test_former_id_may_be_live_elsewhere() -> None:
    """`A40.l25` é hoje OUTRA lane: o campo registra realocação, não colisão."""
    import check_doc_filename_id as gate

    live = DOCS / "sprint/A40/lanes/A40-l25-honestidade-do-cone-if.md"
    assert gate.parse_frontmatter(live)["id"] == "A40.l25"


# ----------------------------------------------------------------------
# Gate F — ADR-NNN em prosa resolve para arquivo (A40.l23, classe da ADR-345)
# ----------------------------------------------------------------------


def _write_doc(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "nota.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_adr_prose_ref_without_file_is_rejected(tmp_path: Path) -> None:
    """O caso da A39: 'ADR-345' citada 6× em prosa sem o arquivo existir."""
    import check_adr_prose_refs as gate

    doc = _write_doc(tmp_path, "Racional em ADR-999.\n")
    assert gate.unresolved_refs(doc, gate.known_adr_numbers()) == [(1, "ADR-999")]


@pytest.mark.parametrize(
    "body",
    [
        "Ver [[ADR-999]] aqui.\n",
        "Ver [[ADR-999|a nota]] aqui.\n",
        "Ver [[ADR-999#Escopo]] aqui.\n",
        "O id `ADR-999` é placeholder.\n",
        "```\nADR-999\n```\n",
        "~~~yaml\nadr: ADR-999\n~~~\n",
        # Mais dígitos: `\bADR-(\d{3})\b` não casa porque o boundary falha.
        # 5 dígitos e não 4 de propósito: o prefixo seguido de exatamente 4
        # dígitos casa o detector de PLACA do lint-no-real-pii
        # (`[A-Z]{3}-?\d{4}`) e derrubaria aquele gate com falso-positivo.
        "Ver ADR-99999 aqui.\n",
    ],
)
def test_adr_prose_gate_does_not_overfire(tmp_path: Path, body: str) -> None:
    """Wikilink é escopo do check_doc_links; code fence e inline code não são prosa."""
    import check_adr_prose_refs as gate

    assert gate.unresolved_refs(_write_doc(tmp_path, body), gate.known_adr_numbers()) == []


def test_adr_prose_ref_with_file_passes(tmp_path: Path) -> None:
    """Controle: ADR que existe em disco não dispara."""
    import check_adr_prose_refs as gate

    assert (
        gate.unresolved_refs(_write_doc(tmp_path, "Ver ADR-345.\n"), gate.known_adr_numbers()) == []
    )


@pytest.mark.parametrize(
    "rel,whitelisted",
    [
        ("docs/DECISIONS.md", True),
        ("docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md", True),
        ("docs/sprint/A40/_README.md", False),
        ("docs/adr/345-reserva-de-id-de-adr.md", False),
    ],
)
def test_adr_prose_whitelist_scope(rel: str, whitelisted: bool) -> None:
    """Shim e arqueologia são congelados por design; o resto da vault não é."""
    import check_adr_prose_refs as gate

    assert gate.is_whitelisted(gate.REPO_ROOT / rel) is whitelisted


def test_adr_prose_cli_exits_nonzero_with_file_and_line(tmp_path: Path) -> None:
    """Contrato do hook: EXIT≠0, arquivo e linha na mensagem."""
    doc = _write_doc(tmp_path, "linha 1\nRacional em ADR-999.\n")
    proc = subprocess.run(
        [sys.executable, str(DEV_DIR / "check_adr_prose_refs.py"), str(doc)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, f"gate passou verde: {proc.stdout}"
    assert ":2" in proc.stdout and "ADR-999" in proc.stdout


def test_live_vault_adr_prose_refs_all_resolve() -> None:
    """5860 refs em prosa, 0 órfãs — o gate nasce verde (medido 2026-08-08)."""
    import check_adr_prose_refs as gate

    known = gate.known_adr_numbers()
    offenders = [
        f"{p.relative_to(DOCS)}:{ln} {ref}"
        for p in sorted(DOCS.rglob("*.md"))
        for ln, ref in gate.unresolved_refs(p, known)
    ]
    assert offenders == [], f"reserva de ID em prosa viva: {offenders}"
