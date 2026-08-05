"""ADR-362 — revisão do executor: normalização, preflight e raiz divergente."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from backend.app.core.executor_revision import normalize_executor_revision
from dev.build_info import (
    boot_revision_from_log,
    divergent_roots_warning,
    preflight_warning,
    resolve_revision,
)

_ROOT = Path(__file__).resolve().parents[2]


# ─────────────────────────── normalização ───────────────────────────


def test_trunca_sha_de_40_preservando_dirty() -> None:
    """Mutação que mata: `String(20)` sem truncar ⇒ DataError no Postgres."""
    # O CI injeta `${{ github.sha }}` = 40 chars; com `-dirty` dá 46.
    sha40 = "a" * 40
    assert normalize_executor_revision(sha40) == "a" * 12
    assert normalize_executor_revision(f"{sha40}-dirty") == "a" * 12 + "-dirty"
    assert len(normalize_executor_revision(f"{sha40}-dirty")) <= 48


def test_ausencia_nunca_vira_string_unknown() -> None:
    """`None`/vazio ⇒ None, nunca `"unknown"` — um 3º vocabulário mataria o grep."""
    for raw in (None, "", "   ", "-dirty", 123):
        assert normalize_executor_revision(raw) is None  # type: ignore[arg-type]


def test_normalizacao_nunca_levanta() -> None:
    """O critério da ADR-362 exige que o processo SUBA sem a env."""
    assert normalize_executor_revision("não-é-um-sha!!") == "não-é-um-sha"


# ─────────────────────── anti-fabricação (gate central) ───────────────────────


def test_revisao_e_do_worktree_apontado_nao_do_cwd() -> None:
    """Gate central: a revisão vem do worktree pinado, não do HEAD ambiente."""
    # Mutação que mata: resolver sem `cwd` — passaria a devolver o HEAD de quem
    # chama, que é a fabricação que a ADR-362 proíbe (worker de 07:28 servindo
    # HEAD de 08:13).
    head_aqui = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()[:12]
    assert (resolve_revision() or "").startswith(head_aqui)


def test_arvore_suja_marca_dirty() -> None:
    """Árvore suja ⇒ o sha não identifica o código; igualdade acerta sozinha."""
    rev = resolve_revision()
    assert rev is not None
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert rev.endswith("-dirty") is bool(porcelain)


def test_sem_git_devolve_none(tmp_path: Path) -> None:
    assert resolve_revision(cwd=tmp_path) is None


# ─────────────────────────── preflight ───────────────────────────


def _boot_line(rev: str) -> str:
    return json.dumps({"message": "mathoms.worker.boot", "executor_revision": rev})


def test_preflight_avisa_quando_worker_roda_codigo_velho() -> None:
    """Mutação que mata: comparar o run PASSADO em vez do processo vivo."""
    w = preflight_warning("aaaaaaaaaaaa", "bbbbbbbbbbbb")
    assert w is not None
    assert "aaaaaaaaaaaa" in w and "bbbbbbbbbbbb" in w
    assert "VELHO" in w


def test_preflight_silencioso_quando_worker_esta_no_head() -> None:
    assert preflight_warning("aaaaaaaaaaaa", "aaaaaaaaaaaa") is None


def test_preflight_avisa_quando_ninguem_anunciou() -> None:
    """Ausência nunca colapsa em "está tudo bem"."""
    assert "nenhum processo" in (preflight_warning(None, "aaaaaaaaaaaa") or "")


def test_boot_revision_pega_a_ultima_do_log() -> None:
    """Worker recicla filhos (max-tasks-per-child); vale a última."""
    log = "\n".join(
        ["ruído não-JSON", _boot_line("aaaaaaaaaaaa"), "{malformado", _boot_line("bbbbbbbbbbbb")]
    )
    assert boot_revision_from_log(log) == "bbbbbbbbbbbb"


def test_boot_revision_ignora_log_sem_a_chave() -> None:
    assert boot_revision_from_log('{"message": "outra coisa"}\n') is None
    assert boot_revision_from_log("") is None


# ─────────────────────────── raízes divergentes ───────────────────────────


def test_avisa_quando_pipeline_e_backend_vem_de_arvores_diferentes() -> None:
    """O modo de falha do PYTHONPATH de worktree vencendo o editable install."""
    w = divergent_roots_warning("/a/worktree", "/b/checkout")
    assert w is not None and "DIFERENTES" in w


def test_nao_avisa_quando_as_raizes_coincidem() -> None:
    assert divergent_roots_warning("/mesma", "/mesma") is None
    assert divergent_roots_warning(None, "/mesma") is None
