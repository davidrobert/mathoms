"""Contador agregado em índice versionado é ponto de contenção de merge — e mente calado.

Medido em 2026-08-24 na fila de auto-merge: `main` mergeia ~7-9x/hora contra ciclos de CI
de ~7 min, e todo PR que toca `docs/**` regenera `docs/_MOC/_generated/`. Os conflitos
vivos eram **100% linha de contador** — nenhuma linha de item.

Pior que o conflito é o silêncio: quando dois PRs incrementam o MESMO contador, os dois
lados escrevem o mesmo valor novo, o git aceita o merge sem conflito, e o número resultante
está errado (lost update) — só o `--check` no CI pega, 7 minutos depois.

A asserção é dupla de propósito: `rc == 0` sozinho fecha o conflito e deixa a mentira
passar. Só comparar contra a regeneração VERDADEIRA fecha a classe, e qualquer contador
agregado reintroduzido volta a reprovar aqui.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import dev.build_doc_index as bdi
from dev.build_doc_index import regenerate_all

REPO_ROOT = Path(__file__).resolve().parents[2]

# TODOS os gerados, derivados do próprio `regenerate_all` — lista à mão envelhece, e o
# ponto do teste é justamente que nenhum deles volte a carregar agregado. O `DOC_STATS.md`
# saiu do gerador em 2026-08-25 por ser 100% agregado: não era reformável, só removível.
# `INDEX.md` é o resíduo DECLARADO e de outra classe: uma tabela só, ordenada por id, em
# que duas notas novas caem adjacentes — duas inserções no mesmo ponto conflitam por
# natureza do merge de linha, não por agregado. `strict=True` de propósito: se algum dia
# alguém resolver a adjacência, este teste reprova e avisa em vez de mentir verde.
_RESIDUO_ADJACENCIA = {"INDEX.md"}


def _param(nome: str):
    if nome in _RESIDUO_ADJACENCIA:
        return pytest.param(
            nome, marks=pytest.mark.xfail(strict=True, reason="adjacência de linha-de-item")
        )
    return nome


NAVEGAVEIS = tuple(_param(n) for n in sorted(regenerate_all(bdi.DOCS)))


_LANE_FM = (
    '---\nid: {lid}\ntype: lane\ntitle: "{lid}"\nsprint: {sprint}\n'
    "plan: PLAN-x\nstatus: {status}\ndepends_on: []\n---\n\n# {lid}\n"
)


def _lane(docs: Path, lane_id: str, status: str) -> None:
    sprint = lane_id.split(".")[0]
    target = docs / "sprint" / sprint / "lanes" / f"{lane_id.replace('.', '-')}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_LANE_FM.format(lid=lane_id, sprint=sprint, status=status), encoding="utf-8")


def _plan(docs: Path) -> None:
    """Um plano — sem ele o `PLAN_PROGRESS.md` nasce sem a linha de contadores."""
    target = docs / "plan" / "PLANX" / "_README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '---\nid: PLAN-x\ntype: plan\ntitle: "PlanX"\nstatus: "Em andamento"\n---\n\n# PlanX\n',
        encoding="utf-8",
    )


def _regenerate(docs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # `regenerate_all` recebe o docs_root, mas `_rel` (build_doc_index.py:134) usa o
    # `DOCS` de módulo — sem o pin o gerador levanta em vault sintética, e teste que
    # se auto-pula não é gate.
    monkeypatch.setattr(bdi, "DOCS", docs)
    target = docs / "_MOC" / "_generated"
    target.mkdir(parents=True, exist_ok=True)
    for name, content in regenerate_all(docs).items():
        (target / name).write_text(content, encoding="utf-8")


def _merge_file(ours: Path, base: Path, theirs: Path) -> int:
    """`git merge-file` in-place em `ours`; rc>0 quando há conflito."""
    done = subprocess.run(
        ["git", "merge-file", str(ours), str(base), str(theirs)],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode


# Cada lado mexe numa SEÇÃO DIFERENTE: as linhas de item ficam disjuntas de propósito,
# para isolar a classe agregada. Duas inserções no MESMO ponto conflitam por natureza do
# merge de linha — é resíduo conhecido, não a classe que este teste fecha.
_LADOS = (
    ("base", ()),
    ("a", (("A99.l3", "open"),)),
    ("b", (("A99.l7", "in_progress"),)),
    ("verdade", (("A99.l3", "open"), ("A99.l7", "in_progress"))),
)


def _build_side(root: Path, extra: tuple, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monta uma vault sintética com as lanes-base + as extras, e regenera."""
    docs = root / "docs"
    (docs / "_MOC" / "_generated").mkdir(parents=True, exist_ok=True)
    _plan(docs)
    _lane(docs, "A99.l0", "open")
    _lane(docs, "A99.l1", "in_progress")
    for lane_id, status in extra:
        _lane(docs, lane_id, status)
    _regenerate(docs, monkeypatch)
    return docs / "_MOC" / "_generated"


@pytest.mark.parametrize("nome", NAVEGAVEIS)
def test_dois_prs_concorrentes_mergeiam_limpo_e_dizem_a_verdade(
    tmp_path: Path, nome: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duas lanes novas sobre a mesma base: merge sem conflito E igual à regeneração real."""
    lados = {
        lado: _build_side(tmp_path / lado, extra, monkeypatch) / nome for lado, extra in _LADOS
    }
    if not lados["base"].exists():
        pytest.skip(f"{nome} não é gerado nesta vault sintética")
    rc = _merge_file(lados["a"], lados["base"], lados["b"])
    assert rc == 0, f"{nome}: merge de dois PRs disjuntos CONFLITA — contenção de merge"
    assert lados["a"].read_text() == lados["verdade"].read_text(), (
        f"{nome}: merge limpo porém MENTE (lost update) — o valor agregado não é derivável "
        f"linha a linha, então o git aceita dois incrementos como um só"
    )
