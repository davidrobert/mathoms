"""Testes do par tripwire + cortador de histórico de sprint.

A mutação de origem é a da A40: em 2026-08-05 o `_README` saltou de 251 para
888 linhas em dois dias, sem `_HISTORY.md`, e ninguém notou por 9 dias — só
apareceu quando o custo de token de uma sessão ficou alto.

O gate roda também sobre a vault viva (último teste): gate provado só em
fixture não prova que nasce verde.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dev import split_sprint_history
from dev.check_sprint_readme_size import (
    MAX_README_LINES_WITHOUT_HISTORY,
    SPRINT_DIR,
    count_historical_blocks,
    scan,
)


def _sprint(root: Path, name: str, readme_lines: int, *, history: bool = False) -> Path:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"linha {i}" for i in range(readme_lines))
    (folder / "_README.md").write_text(body, encoding="utf-8")
    if history:
        (folder / "_HISTORY.md").write_text("# histórico\n", encoding="utf-8")
    return folder


def test_readme_pequeno_passa(tmp_path: Path) -> None:
    _sprint(tmp_path, "A99", 137)  # mediana medida do vault
    assert scan(tmp_path) == ([], [])


def test_readme_grande_sem_history_falha(tmp_path: Path) -> None:
    _sprint(tmp_path, "A99", MAX_README_LINES_WITHOUT_HISTORY + 1)
    violations, _advisories = scan(tmp_path)
    assert len(violations) == 1
    assert "não existe `_HISTORY.md`" in violations[0]


def test_readme_grande_com_history_passa(tmp_path: Path) -> None:
    # O gate mede a patologia (grande SEM histórico), não o tamanho: sprint
    # grande e bem organizada não pode reprovar, senão vira Goodhart — infla-se
    # o `_HISTORY` para passar.
    _sprint(tmp_path, "A99", 5000, history=True)
    violations, _advisories = scan(tmp_path)
    assert violations == []


def test_exatamente_no_teto_passa(tmp_path: Path) -> None:
    _sprint(tmp_path, "A99", MAX_README_LINES_WITHOUT_HISTORY)
    assert scan(tmp_path)[0] == []


@pytest.mark.parametrize(
    "texto",
    [
        "> **Estado da Onda 3 em 2026-08-07** (o snapshot acima é datado)",
        "> **Delta 2026-08-06 — o predicado tem custo de manutenção**",
        "O diagnóstico abaixo fica como registro do que foi medido.",
        "A tabela acima é medição datada em `33bb0710`; não a reescreva.",
    ],
)
def test_marcadores_de_registro_fechado_sao_contados(texto: str) -> None:
    assert count_historical_blocks(texto) >= 1


def test_prosa_normal_nao_conta_como_registro() -> None:
    assert count_historical_blocks("A l5 vem antes das lanes de correção.") == 0


def test_cortador_move_secao_e_deixa_ponteiro(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "A99"
    folder.mkdir(parents=True)
    (folder / "_README.md").write_text(
        "# Sprint A99\n\n## Tese\n\nviva.\n\n## Pendências\n\nresolvida.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(split_sprint_history, "SPRINT_DIR", tmp_path)
    count, _lines = split_sprint_history.split("A99", ["Pendências"], "2026-08-14")
    readme = (folder / "_README.md").read_text(encoding="utf-8")
    history = (folder / "_HISTORY.md").read_text(encoding="utf-8")
    assert count == 1
    assert "Movida para [`_HISTORY`](_HISTORY.md)" in readme
    assert "## Tese" in readme and "viva." in readme  # não tocou o que governa
    assert "resolvida." in history


def test_cortador_nao_move_sem_section(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "A99"
    folder.mkdir(parents=True)
    (folder / "_README.md").write_text("# A99\n\n## Tese\n\nviva.\n", encoding="utf-8")
    monkeypatch.setattr(split_sprint_history, "SPRINT_DIR", tmp_path)
    assert split_sprint_history.split("A99", [], "2026-08-14") == (0, 0)
    assert not (folder / "_HISTORY.md").exists()


def test_id_do_history_nao_casa_padrao_de_moc_de_sprint(tmp_path: Path, monkeypatch) -> None:
    # `MOC-sprint-<x>` faria build_doc_index listar o histórico como sprint.
    folder = tmp_path / "A99"
    folder.mkdir(parents=True)
    (folder / "_README.md").write_text("# A99\n\n## Velha\n\nresolvida.\n", encoding="utf-8")
    monkeypatch.setattr(split_sprint_history, "SPRINT_DIR", tmp_path)
    split_sprint_history.split("A99", ["Velha"], "2026-08-14")
    assert "id: MOC-a99-historico" in (folder / "_HISTORY.md").read_text(encoding="utf-8")


def test_vault_viva_esta_verde() -> None:
    """Nasce verde sobre as 37 sprints reais — senão é dívida, não gate."""
    assert scan(SPRINT_DIR)[0] == []
