"""W2-T05 · ADR-233 — testes do gate ``dev/check_prompt_version_bumped.py``."""

# Estratégia: mini-repo git temporário + MATHOMS_PROMPT_VERSION_BASE=main.
# Cobre os 4 cenários do track + edge cases (formato, bypass, arquivo novo,
# prefix legado).

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "dev" / "check_prompt_version_bumped.py"
_SPEC = importlib.util.spec_from_file_location("check_prompt_version_bumped", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


# =============================================================================
# Helpers
# =============================================================================


def _run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {args} failed: {result.stderr}")
    return result.stdout


def _init_repo(tmp_path: Path) -> Path:
    """Bootstrap git repo com branch main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")
    return repo


def _seed_prompts(repo: Path) -> None:
    prompts_dir = repo / "pipeline" / "llm" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "__init__.py").write_text("")
    (prompts_dir / "alpha.py").write_text(
        '"""Alpha prompt."""\n\n'
        'PROMPT_VERSION = "1.0.0"\n\n'
        'SYSTEM_PROMPT = """system v1"""\n'
        'USER_PROMPT_TEMPLATE = """user v1"""\n'
    )
    # Arquivo sem PROMPT_VERSION — gate deve ignorar.
    (prompts_dir / "other.py").write_text('"""Helper sem prompt."""\n\nFOO = "bar"\n')


def _seed_schemas(repo: Path) -> None:
    schemas_dir = repo / "pipeline" / "llm" / "schemas"
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "__init__.py").write_text("")
    # Semver puro pós-A20.l12 — o repo não carrega mais formatos legados.
    (schemas_dir / "legacy.py").write_text(
        '"""Schema migrado para semver puro (A20.l12)."""\n\nPROMPT_VERSION = "2.3.4"\n'
    )


def _make_repo(tmp_path: Path) -> Path:
    """Mini-repo git com 2 prompts seedados em commit inicial."""
    repo = _init_repo(tmp_path)
    _seed_prompts(repo)
    _seed_schemas(repo)
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-q", "-m", "seed")
    return repo


def _capture_main(argv: list[str]) -> tuple[int, str]:
    """Roda gate.main(argv) capturando stderr."""
    import sys
    from io import StringIO

    buf = StringIO()
    sys.stderr, original = buf, sys.stderr
    try:
        code = gate.main(argv)
    finally:
        sys.stderr = original
    return code, buf.getvalue()


def _gate_in_repo(repo: Path, argv: list[str] | None = None) -> tuple[int, str]:
    """Roda ``gate.main`` com cwd=repo + MATHOMS_PROMPT_VERSION_BASE=main."""
    cwd = os.getcwd()
    old_base = os.environ.get("MATHOMS_PROMPT_VERSION_BASE")
    os.environ["MATHOMS_PROMPT_VERSION_BASE"] = "main"
    gate.UPSTREAM_REF = "main"
    os.chdir(repo)
    try:
        return _capture_main(argv or [])
    finally:
        os.chdir(cwd)
        if old_base is None:
            os.environ.pop("MATHOMS_PROMPT_VERSION_BASE", None)
        else:
            os.environ["MATHOMS_PROMPT_VERSION_BASE"] = old_base
        gate.UPSTREAM_REF = os.environ.get("MATHOMS_PROMPT_VERSION_BASE", "origin/main")


# =============================================================================
# Cenário 1: diff sem bump → fail
# =============================================================================


def test_diff_without_bump_fails(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "alpha.py"
    target.write_text(
        '"""Alpha prompt."""\n\n'
        'PROMPT_VERSION = "1.0.0"\n\n'
        'SYSTEM_PROMPT = """system v2 — content changed"""\n'
        'USER_PROMPT_TEMPLATE = """user v1"""\n'
    )

    code, err = _gate_in_repo(repo)
    assert code == 1
    assert "alpha.py" in err
    assert "PROMPT_VERSION continua '1.0.0'" in err
    assert "1.0.1" in err  # sugestão de bump


# =============================================================================
# Cenário 2: diff com bump → pass
# =============================================================================


def test_diff_with_bump_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "alpha.py"
    target.write_text(
        '"""Alpha prompt."""\n\n'
        'PROMPT_VERSION = "1.0.1"\n\n'
        'SYSTEM_PROMPT = """system v2 — content changed"""\n'
        'USER_PROMPT_TEMPLATE = """user v1"""\n'
    )

    code, err = _gate_in_repo(repo)
    assert code == 0, f"unexpected fail: {err}"


# =============================================================================
# Cenário 3: diff em arquivo fora de prompts/schemas → pass
# =============================================================================


def test_diff_in_non_prompt_file_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    # Arquivo fora dos diretórios monitorados.
    other = repo / "pipeline" / "stages" / "extract.py"
    other.parent.mkdir(parents=True)
    other.write_text('PROMPT_VERSION = "1.0.0"  # not in monitored dir\n')

    code, _ = _gate_in_repo(repo, argv=[str(other.relative_to(repo))])
    assert code == 0


# =============================================================================
# Cenário 4: sem diff → pass
# =============================================================================


def test_no_diff_passes(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    code, _ = _gate_in_repo(repo)
    assert code == 0


# =============================================================================
# Edge cases — formato, bypass, arquivo novo, prefix legado
# =============================================================================


def test_invalid_format_fails(tmp_path: Path) -> None:
    """``PROMPT_VERSION = "v1"`` não casa o regex canônico (ADR-233)."""
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "alpha.py"
    target.write_text(
        '"""Alpha prompt."""\n\n' 'PROMPT_VERSION = "v1"\n\n' 'SYSTEM_PROMPT = """system v1"""\n'
    )

    code, err = _gate_in_repo(repo)
    assert code == 1
    assert "formato canônico" in err


def test_bypass_env_skips(tmp_path: Path, monkeypatch) -> None:
    """``MATHOMS_SKIP_PROMPT_VERSION_CHECK=1`` retorna 0 sem verificar."""
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "alpha.py"
    target.write_text('"""changed."""\n\nPROMPT_VERSION = "1.0.0"\n')

    monkeypatch.setenv("MATHOMS_SKIP_PROMPT_VERSION_CHECK", "1")
    code, _ = _gate_in_repo(repo)
    assert code == 0


def test_new_file_in_pr_passes(tmp_path: Path) -> None:
    """Arquivo novo (não existe em upstream) → versão inicial aceita."""
    repo = _make_repo(tmp_path)
    new = repo / "pipeline" / "llm" / "prompts" / "beta.py"
    new.write_text(
        '"""Beta prompt."""\n\n' 'PROMPT_VERSION = "1.0.0"\n\n' 'SYSTEM_PROMPT = """new"""\n'
    )

    code, _ = _gate_in_repo(repo)
    assert code == 0


def test_legacy_prefix_v_format_rejected(tmp_path: Path) -> None:
    """Errata ADR-233 §Migration (A20.l12): ``<slug>-v<semver>`` deixou de ser aceito."""
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "schemas" / "legacy.py"
    target.write_text(
        '"""Legacy schema with prefix-v<semver>."""\n\n'
        'PROMPT_VERSION = "legacy-v2.4.0"\n'  # bumped, mas formato legado
        '\nNEW_CONST = "added"\n'
    )

    code, err = _gate_in_repo(repo)
    assert code == 1, "formato legado <slug>-v<semver> deveria falhar no modo estrito"


def test_file_without_prompt_version_is_ignored(tmp_path: Path) -> None:
    """Arquivo em prompts/ sem ``PROMPT_VERSION`` é skipado silenciosamente."""
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "other.py"
    # Modifica conteúdo sem adicionar PROMPT_VERSION.
    target.write_text('"""Helper sem prompt."""\n\nFOO = "baz"\n')

    code, _ = _gate_in_repo(repo)
    # Como ``other.py`` não tem PROMPT_VERSION, _discover_prompts não o
    # inclui — comportamento esperado é exit 0.
    assert code == 0


def test_argv_mode_filters_to_prompt_files(tmp_path: Path) -> None:
    """Quando ``argv`` é passado (pre-commit), só checa esses arquivos."""
    repo = _make_repo(tmp_path)
    target = repo / "pipeline" / "llm" / "prompts" / "alpha.py"
    target.write_text(
        '"""Alpha prompt."""\n\n'
        'PROMPT_VERSION = "1.0.0"\n\n'
        'SYSTEM_PROMPT = """system v2 — changed"""\n'
    )

    # Passa um arquivo NÃO monitorado — gate ignora e retorna 0.
    code, _ = _gate_in_repo(repo, argv=["README.md"])
    assert code == 0

    # Agora passa o arquivo bugado — gate falha.
    code, err = _gate_in_repo(repo, argv=[str(target.relative_to(repo))])
    assert code == 1
    assert "alpha.py" in err


# =============================================================================
# Validações puras do regex canônico (sem git)
# =============================================================================


@pytest.mark.parametrize(
    "version,valid",
    [
        ("1.0.0", True),
        ("2.1.3", True),
        ("10.20.30", True),
        # Errata ADR-233 §Migration (A20.l12): prefixo legado deixou de valer.
        ("e16-v1.1.0", False),
        ("informe-aluguel-v1.1.0", False),
        ("legacy-v2.4.0", False),
        ("v1", False),
        ("1.0", False),
        ("1", False),
        ("e16-1.1.0", False),  # falta o "v"
        ("e16-v1.1", False),  # semver incompleto
        ("", False),
    ],
)
def test_canonical_version_regex(version: str, valid: bool) -> None:
    match = gate.CANONICAL_VERSION_RE.match(version)
    assert bool(match) == valid


@pytest.mark.parametrize(
    "current,expected",
    [
        ("1.0.0", "1.0.1"),
        ("2.1.3", "2.1.4"),
        ("e16-v1.1.0", "e16-v1.1.1"),
    ],
)
def test_suggest_bump(current: str, expected: str) -> None:
    assert gate._suggest_bump(current) == expected
