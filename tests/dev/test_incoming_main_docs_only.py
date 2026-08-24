"""Skip-class do trem (ADR-322) sobre um merge-ref REAL.

O teste anterior injetava booleanos na função pura e por isso não viu que o
predicado estava ancorado no commit errado — a feature era inerte e a suíte
verde. Aqui cada caso monta um repo git com a forma que o CI enxerga
(`refs/pull/N/merge`: `HEAD^1` = base, `HEAD^2` = head da branch) e chama
`decide()` de ponta a ponta.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from dev import incoming_main_docs_only as mod

# Capturado ANTES do fixture autouse: ele stuba `aggregate_is_green`, e um
# teste que chamasse `mod.aggregate_is_green` mediria o stub, não a função.
AGGREGATE_REAL = mod.aggregate_is_green

CODIGO = "backend/app/x.py"
DOC = "docs/adr/999-nota.md"


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _commit(repo: Path, path: str, texto: str, msg: str) -> str:
    alvo = repo / path
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(texto, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _repo_com_branch(tmp_path: Path) -> Path:
    """Repo com `main` (código) e `pr` (trabalho do PR) já divergentes."""
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _commit(repo, CODIGO, "v1", "base")
    _git(repo, "checkout", "-q", "-b", "pr")
    _commit(repo, "frontend/y.ts", "pr", "trabalho do PR")
    return repo


def _avanca_main(repo: Path, trazido: dict[str, str]) -> None:
    _git(repo, "checkout", "-q", "main")
    for path, texto in trazido.items():
        _commit(repo, path, texto, f"main: {path}")


@pytest.fixture
def merge_ref(tmp_path: Path):
    """Constrói base + branch + merge do update-branch + merge-ref sintético."""

    def build(*, trazido: dict[str, str], com_merge: bool = True) -> tuple[Path, str]:
        repo = _repo_com_branch(tmp_path)
        _avanca_main(repo, trazido)
        _git(repo, "checkout", "-q", "pr")
        if com_merge:
            _git(repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'main' into pr", "main")
        head_da_branch = _git(repo, "rev-parse", "HEAD")
        _git(repo, "checkout", "-q", "-b", "mergeref", "main")
        _git(repo, "merge", "-q", "--no-ff", "-m", "merge-ref sintético", "pr")
        return repo, head_da_branch

    return build


@pytest.fixture(autouse=True)
def verde(monkeypatch: pytest.MonkeyPatch):
    """Default: o SHA anterior da branch fechou verde. Caso a caso sobrescreve."""
    monkeypatch.setattr(mod, "aggregate_is_green", lambda *_a, **_k: True)


def test_merge_docs_only_com_verde_anterior_pula(merge_ref) -> None:
    """A ÂNCORA: com o predicado lendo `HEAD` (versão anterior) isto dava False
    sempre, porque o head do PR nunca é ancestral da base num repo squash-only."""
    repo, head = merge_ref(trazido={DOC: "texto"})
    skip, motivo = mod.decide(repo, event_head_sha=head, repo_slug="o/r")
    assert skip is True, motivo


def test_delta_com_codigo_nao_pula(merge_ref) -> None:
    repo, head = merge_ref(trazido={DOC: "texto", CODIGO: "v2"})
    skip, motivo = mod.decide(repo, event_head_sha=head, repo_slug="o/r")
    assert skip is False
    assert "doc inerte" in motivo


@pytest.mark.parametrize(
    "path", ["docs/reference/api/openapi.json", "docs/reference/DB_SCHEMA_REFERENCE.md"]
)
def test_doc_que_e_input_de_gate_nao_pula(merge_ref, path: str) -> None:
    """Estes vivem em `docs/` mas são lidos do disco por teste de job skipável."""
    repo, head = merge_ref(trazido={path: "x"})
    skip, _ = mod.decide(repo, event_head_sha=head, repo_slug="o/r")
    assert skip is False


def test_merge_ref_obsoleto_nao_pula(merge_ref) -> None:
    """`refs/pull/N/merge` é assíncrono: servido velho, `HEAD^2` é o head anterior
    e a decisão sairia de uma árvore que não é a do evento."""
    repo, _ = merge_ref(trazido={DOC: "texto"})
    skip, motivo = mod.decide(repo, event_head_sha="0" * 40, repo_slug="o/r")
    assert skip is False
    assert "obsoleto" in motivo


def test_sem_verde_anterior_nao_pula(merge_ref, monkeypatch: pytest.MonkeyPatch) -> None:
    """PR vermelho + update-branch docs-only mergearia código nunca testado —
    `all-green` aceita `skipped`, então job pulado É required check verde."""
    monkeypatch.setattr(mod, "aggregate_is_green", lambda *_a, **_k: False)
    repo, head = merge_ref(trazido={DOC: "texto"})
    skip, motivo = mod.decide(repo, event_head_sha=head, repo_slug="o/r")
    assert skip is False
    assert "All checks green" in motivo


def test_sem_merge_do_update_branch_nao_pula(merge_ref) -> None:
    repo, head = merge_ref(trazido={DOC: "texto"}, com_merge=False)
    skip, motivo = mod.decide(repo, event_head_sha=head, repo_slug="o/r")
    assert skip is False
    assert "parents" in motivo


def test_falha_de_io_nega_o_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha de leitura NUNCA concede skip — era o que a inferência de frescor
    do Nightly invertia (5xx virava "smoke fresco")."""
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 1, "", "HTTP 503"),
    )
    assert AGGREGATE_REAL("abc", "o/r") is False


@pytest.mark.parametrize("payload", ["", "nao-json", '{"check_runs": []}', "[]"])
def test_payload_sem_agregado_verde_nega_o_skip(payload: str) -> None:
    assert mod._has_green_aggregate(payload) is False


def test_agregado_verde_e_reconhecido() -> None:
    payload = '{"check_runs": [{"name": "All checks green", "conclusion": "success"}]}'
    assert mod._has_green_aggregate(payload) is True


def test_delta_vazio_nao_pula() -> None:
    assert mod.paths_are_inert_docs([]) is False


# ---------------------------------------------------------------------------
# Gate de CLASSE: `docs/**` não é uniformemente inerte. Três paths já eram input
# de gate quando isto foi escrito, e a lista é denylist chaveada em conhecimento
# que mora dentro de arquivo de teste — apodrece calada. Este teste fecha a
# classe: o 4º consumidor reprova aqui em vez de virar fail-open no merge.
# ---------------------------------------------------------------------------

# Jobs que o skip-class pula. `pipeline-tests` e `lint-all` NÃO estão aqui —
# é por isso que `docs/adr/**` (o maior churn de doc) não precisa de exceção.
DIRS_DE_JOB_SKIPAVEL = ("backend/tests",)


def _docstrings(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        corpo = getattr(node, "body", None)
        if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant):
            ids.add(id(corpo[0].value))
    return ids


def _literais_docs(arquivo: Path) -> set[str]:
    """String de código apontando para `docs/` — docstring e comentário fora."""
    try:
        tree = ast.parse(arquivo.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    pulados = _docstrings(tree)
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith("docs/")
        and id(node) not in pulados
    }


def _nao_excetuados(arquivo: Path, raiz: Path) -> dict[str, str]:
    fora = {}
    for literal in _literais_docs(arquivo):
        if not any(literal.startswith(p) for p in mod.DOCS_GATE_INPUTS):
            fora[literal] = str(arquivo.relative_to(raiz))
    return fora


def test_todo_docs_lido_por_job_skipavel_esta_na_excecao() -> None:
    raiz = Path(__file__).resolve().parents[2]
    achados: dict[str, str] = {}
    for d in DIRS_DE_JOB_SKIPAVEL:
        for arquivo in sorted((raiz / d).rglob("*.py")):
            achados.update(_nao_excetuados(arquivo, raiz))
    assert not achados, (
        "path de `docs/` usado como literal de código em job skipável e ausente de "
        f"DOCS_GATE_INPUTS — o skip o trataria como inerte: {achados}"
    )
