"""Testes do gate `dev/check_lane_transition.py` (A40.l59).

A prova exigida pelo §Critério de aceite da lane é **por amostra medida**, não por
anedota: o §Ataque mediu 23 de 42 transições da A40 que seriam barradas, em dois
eixos. Cada eixo entra aqui com um caso REAL nomeado, reconstruído em vault
sintética a partir do que a história de `main` mostra:

  - `ship_pr` ausente no commit do flip → A40.l71, que flipou em #1517 com o número
    só no ASSUNTO do commit ("closeout l71 — shipped #1511"); o campo entrou no #1533.
  - PR não citado no registro → A40.l19/#1241, ausente do `_README` no commit do
    flip e hoje na linha 732.

E os casos NEGATIVOS declarados, que o gate não pode acusar: o l7/#1375 (transição
ausente — não há diff) e a lane que fecha a si mesma feita na ordem prescrita.

O último teste roda o gate sobre a vault VIVA: gate provado só em fixture não prova
que nasce verde.
"""

from __future__ import annotations

from pathlib import Path

from dev._lane_closure_predicates import lane_ids_with_table_row, pr_is_cited
from dev.check_lane_transition import (
    DOCS,
    check_coherence,
    check_creation,
    check_flip,
)

SPRINT = "A40"


def _lane_text(lane_id: str, status: str, **extra: object) -> str:
    """Frontmatter mínimo de lane, com os campos extras na ordem dada."""
    lines = ["---", f"id: {lane_id}", "type: lane", f'title: "{lane_id}"', f"sprint: {SPRINT}"]
    lines.append(f"status: {status}")
    lines += [f"{key}: {value}" for key, value in extra.items()]
    lines += ["---", "", f"# {lane_id}", ""]
    return "\n".join(lines)


def _vault(root: Path, *, readme: str = "", history: str = "") -> Path:
    docs = root / "docs"
    folder = docs / "sprint" / SPRINT
    (folder / "lanes").mkdir(parents=True, exist_ok=True)
    (folder / "_README.md").write_text(readme, encoding="utf-8")
    if history:
        (folder / "_HISTORY.md").write_text(history, encoding="utf-8")
    return docs


def _path(lane_id: str) -> str:
    return f"docs/sprint/{SPRINT}/lanes/{lane_id.replace('.', '-')}.md"


# --------------------------------------------------------------------------- T1


def test_flip_sem_ship_pr_acusa_caso_a40_l71(tmp_path: Path) -> None:
    """Eixo 1 das 23 barradas: o número existia (estava no assunto), o campo não."""
    docs = _vault(tmp_path, readme="# A40\n\n#1511 entregue\n")
    before = _lane_text("A40.l71", "in_progress")
    after = _lane_text("A40.l71", "shipped")
    problems = check_flip(_path("A40.l71"), before, after, docs)
    assert len(problems) == 1
    assert "`ship_pr` e `ship_date`" in problems[0]
    assert "gh pr create" in problems[0], "a mensagem tem de trazer a sequência prescrita"


def test_flip_com_pr_nao_citado_acusa_caso_a40_l19(tmp_path: Path) -> None:
    """Eixo 2 das 23 barradas: campos presentes, registro da sprint sem o PR."""
    docs = _vault(tmp_path, readme="# A40\n\nnada sobre esta entrega\n")
    after = _lane_text("A40.l19", "shipped", ship_pr=1241, ship_date="2026-08-06")
    problems = check_flip(_path("A40.l19"), _lane_text("A40.l19", "open"), after, docs)
    assert len(problems) == 1
    assert "#1241 não aparece no registro" in problems[0]


def test_flip_completo_passa(tmp_path: Path) -> None:
    docs = _vault(tmp_path, readme="# A40\n\n[[A40.l19]] ✅ (#1241)\n")
    after = _lane_text("A40.l19", "shipped", ship_pr=1241, ship_date="2026-08-06")
    assert check_flip(_path("A40.l19"), _lane_text("A40.l19", "open"), after, docs) == []


def test_pr_citado_no_history_vale(tmp_path: Path) -> None:
    """§Ataque §3: 24 PRs da A40 vivem só no `_HISTORY`, por política mandatória."""
    docs = _vault(tmp_path, readme="# A40\n", history="## histórico\n\n[[A40.l1]] ✅ (#1118)\n")
    after = _lane_text("A40.l1", "shipped", ship_pr=1118, ship_date="2026-08-01")
    assert check_flip(_path("A40.l1"), _lane_text("A40.l1", "open"), after, docs) == []


def test_lane_que_ja_era_shipped_nao_e_transicao(tmp_path: Path) -> None:
    """Editar lane já `shipped` não re-dispara — o gate é na TRANSIÇÃO."""
    docs = _vault(tmp_path, readme="# A40\n")
    já = _lane_text("A40.l19", "shipped")
    assert check_flip(_path("A40.l19"), já, já, docs) == []


# --------------------------------------------------------------------------- T2


def test_lane_nova_sem_linha_na_tabela_acusa(tmp_path: Path) -> None:
    """Caso retroativo do #1411: l47/l48/l49 nasceram sem linha no `_README`."""
    docs = _vault(tmp_path, readme="# A40\n\n| Lane | Título |\n| --- | --- |\n")
    problems = check_creation(_path("A40.l47"), _lane_text("A40.l47", "open"), docs)
    assert len(problems) == 1
    assert "não tem linha na tabela" in problems[0]


def test_lane_nova_com_linha_passa(tmp_path: Path) -> None:
    docs = _vault(tmp_path, readme="| Lane |\n| --- |\n| [[A40.l47]] | x |\n")
    assert check_creation(_path("A40.l47"), _lane_text("A40.l47", "open"), docs) == []


def test_mencao_em_prosa_nao_substitui_linha_de_tabela(tmp_path: Path) -> None:
    # A A40.l77 era citada no `_README` — numa tabela de roteamento — e seguia fora
    # da §Lanes. Predicado frouxo ("id aparece no `_README`") deixaria passar.
    """§Ataque §6: os dois predicados discordam, e o certo é LINHA de tabela."""
    docs = _vault(tmp_path, readme="A [[A40.l77]] foi aberta aqui e roteada.\n")
    assert check_creation(_path("A40.l77"), _lane_text("A40.l77", "open"), docs) != []


# --------------------------------------------------------------------------- C1


def test_coerencia_acusa_lane_nao_terminal_com_pr_mergeado(tmp_path: Path) -> None:
    """A classe que mascarou o `blocked` da l58: l5 `in_progress` com PR mergeado."""
    docs = _vault(tmp_path)
    lane = docs / "sprint" / SPRINT / "lanes" / "A40-l5.md"
    lane.write_text(_lane_text("A40.l5", "in_progress", ship_pr=1450), encoding="utf-8")
    problems = check_coherence(docs, merged={1450})
    assert len(problems) == 1
    assert "Estado e entrega discordam" in problems[0]


def test_coerencia_silencia_quando_o_pr_ainda_nao_mergeou(tmp_path: Path) -> None:
    docs = _vault(tmp_path)
    lane = docs / "sprint" / SPRINT / "lanes" / "A40-l5.md"
    lane.write_text(_lane_text("A40.l5", "in_progress", ship_pr=1450), encoding="utf-8")
    assert check_coherence(docs, merged=set()) == []


def test_coerencia_silencia_em_lane_terminal(tmp_path: Path) -> None:
    docs = _vault(tmp_path)
    lane = docs / "sprint" / SPRINT / "lanes" / "A40-l5.md"
    lane.write_text(_lane_text("A40.l5", "shipped", ship_pr=1450), encoding="utf-8")
    assert check_coherence(docs, merged={1450}) == []


# ------------------------------------------------------- casos NEGATIVOS


def test_caso_bandeira_l7_nao_dispara_e_isso_e_declarado(tmp_path: Path) -> None:
    # O gate não pode inventar violação onde nada mudou. É o limite declarado no
    # docstring do módulo e no §Deferimento da lane, não um bug.
    """l7/#1375: transição AUSENTE — o PR não tocou a lane, não há diff que gatear."""
    docs = _vault(tmp_path, readme="# A40\n")
    inalterado = _lane_text("A40.l7", "in_progress")
    assert check_flip(_path("A40.l7"), inalterado, inalterado, docs) == []
    assert check_coherence(docs, merged={1375}) == []


def test_self_closing_na_ordem_prescrita_passa(tmp_path: Path) -> None:
    """§Ataque §4: 6 das 42 fecham a si mesmas; 2 já fazem na ordem certa."""
    docs = _vault(tmp_path, readme="# A40\n\nfecha a lane (#1278)\n")
    after = _lane_text("A40.l20", "shipped", ship_pr=1278, ship_date="2026-08-07")
    assert check_flip(_path("A40.l20"), _lane_text("A40.l20", "open"), after, docs) == []


# ------------------------------------------------------------- vault viva


def test_vault_viva_esta_coerente() -> None:
    """Gate provado só em fixture não prova que nasce verde."""
    from dev.check_lane_transition import merged_pr_numbers

    assert check_coherence(DOCS, merged_pr_numbers()) == []


def test_predicados_leem_a_vault_viva() -> None:
    # Regex que não casa passa ABERTO — foi assim que o `check_lane_counter` ficou inerte.
    """Os predicados compartilhados enxergam a A40 real."""
    assert pr_is_cited(DOCS, "A40", 1648), "o PR desta lane está no registro"
    rows = lane_ids_with_table_row(DOCS, "A40")
    assert "A40.l59" in rows and "A40.l77" in rows


def test_predicado_do_registro_e_o_mesmo_nos_dois_consumidores() -> None:
    # A skill lia só o `_README` e acusava 4 lanes da A40 cujo PR o
    # `split_sprint_history.py` moveu — teto de falso-positivo da skill é 20%.
    """§Colisão: `check_closure` e o gate compartilham `pr_is_cited`, não duas cópias."""
    import sys

    sys.path.insert(0, str(DOCS.parent / ".claude/skills/lane-closeout/references"))
    import check_closure as cc

    assert cc.pr_is_cited is pr_is_cited
    for pr in (1118, 1124, 1139, 1269):
        assert pr_is_cited(DOCS, "A40", pr), f"#{pr} vive no _HISTORY e é citação válida"
