"""Testes do gate `dev/check_lane_status_predicate.py`.

Cada caso escreve arquivos de lane reais numa vault sintética e roda o gate
sobre ela. As mutações são as TRÊS que a Sprint A40 mediu em dois dias
(_README §Predicado, §Delta 2026-08-06 e §Delta 2026-08-07), não violações
inventadas: `open` com dep pendente, `blocked` com dep já shippada, e o caso
de amarra parcial que deve continuar passando.

O gate também roda sobre a vault VIVA (último teste) — gate que só é provado
em fixture não prova que nasce verde.
"""

from __future__ import annotations

from pathlib import Path

from dev.check_lane_status_predicate import DOCS, collect_lanes, find_violations


def _lane(root: Path, lane_id: str, status: str, *, deps: list[str] | None = None, **extra) -> None:
    """Escreve `docs/sprint/<X>/lanes/<id>.md` com o frontmatter mínimo de lane."""
    sprint = lane_id.split(".")[0]
    folder = root / "sprint" / sprint / "lanes"
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"id: {lane_id}", "type: lane", f'title: "{lane_id}"', f"sprint: {sprint}"]
    lines.append(f"status: {status}")
    for key, value in extra.items():
        lines.append(f"{key}: {str(value).lower() if isinstance(value, bool) else value}")
    if deps:
        lines.append("depends_on:")
        lines.extend(f'  - "[[{dep}]]"' for dep in deps)
    else:
        lines.append("depends_on: []")
    lines.extend(["---", "", f"# {lane_id}", ""])
    (folder / f"{lane_id.replace('.', '-')}.md").write_text("\n".join(lines), encoding="utf-8")


def _run(root: Path) -> list[str]:
    return find_violations(collect_lanes(root))


def test_open_com_dep_terminal_passa(tmp_path: Path) -> None:
    _lane(tmp_path, "A99.l1", "shipped")
    _lane(tmp_path, "A99.l2", "open", deps=["A99.l1"])
    assert _run(tmp_path) == []


def test_open_com_dep_pendente_falha(tmp_path: Path) -> None:
    # Mutação de origem: A40.l18 ficou `open` dependendo da l21 `open` — quem
    # seguisse a ordem óbvia do SPRINT_CURRENT pegava a lane que não termina.
    _lane(tmp_path, "A99.l1", "open")
    _lane(tmp_path, "A99.l2", "open", deps=["A99.l1"])
    violations = _run(tmp_path)
    assert len(violations) == 1
    assert "A99.l2 está `open` com dependência pendente" in violations[0]
    assert "A99.l1 (open)" in violations[0]


def test_open_com_dep_pendente_e_amarra_parcial_passa(tmp_path: Path) -> None:
    # 2ª cláusula do predicado: precedentes A40.l20, A40.l27 e A40.l60.
    _lane(tmp_path, "A99.l1", "in_progress")
    _lane(tmp_path, "A99.l2", "open", deps=["A99.l1"], partial_delivery=True)
    assert _run(tmp_path) == []


def test_blocked_com_dep_ja_shippada_falha(tmp_path: Path) -> None:
    # Mutação de origem: a A40.l18 mergeou e o `blocked` da lane dependente
    # virou stale — a lane sumiu do SPRINT_CURRENT quando ficou pegável.
    _lane(tmp_path, "A99.l1", "shipped")
    _lane(tmp_path, "A99.l2", "blocked", deps=["A99.l1"])
    violations = _run(tmp_path)
    assert len(violations) == 1
    assert "TODAS as dependências" in violations[0]


def test_blocked_com_dep_pendente_passa(tmp_path: Path) -> None:
    _lane(tmp_path, "A99.l1", "in_progress")
    _lane(tmp_path, "A99.l2", "blocked", deps=["A99.l1"])
    assert _run(tmp_path) == []


def test_blocked_sem_depends_on_passa(tmp_path: Path) -> None:
    # Bloqueador externo não é derivável de frontmatter. Precedente vivo:
    # F12.2-F12.5, retidas por gate fora do vault.
    _lane(tmp_path, "A99.l1", "blocked")
    assert _run(tmp_path) == []


def test_dep_inexistente_e_ignorada(tmp_path: Path) -> None:
    # Aresta que não resolve é escopo de `check_doc_graph_refs`. Dois gates
    # reclamando do mesmo defeito com mensagens diferentes é ruído.
    _lane(tmp_path, "A99.l2", "open", deps=["A99.l404"])
    assert _run(tmp_path) == []


def test_cancelled_satisfaz_dependencia(tmp_path: Path) -> None:
    _lane(tmp_path, "A99.l1", "cancelled")
    _lane(tmp_path, "A99.l2", "open", deps=["A99.l1"])
    assert _run(tmp_path) == []


def test_vault_viva_esta_verde() -> None:
    """O gate nasce verde sobre a vault real — senão é dívida, não gate."""
    assert find_violations(collect_lanes(DOCS)) == []
