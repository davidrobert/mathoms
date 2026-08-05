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


def _git_repo(path: Path) -> str:
    """Repo git real e isolado — asserção contra ambiente não morde em CI."""
    for cmd in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "c0"],
    ):
        subprocess.run(["git", *cmd], cwd=path, check=True, capture_output=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()[:12]


def test_revisao_e_do_worktree_apontado_nao_do_cwd(tmp_path, monkeypatch) -> None:
    """Gate central: a revisão vem do worktree APONTADO, não do cwd do processo."""
    # Mutação que mata: `cwd=cwd` sem o fallback `or _ROOT` em `_git` — passaria a
    # devolver o HEAD de quem chama. O teste anterior comparava com `_ROOT` e rodava
    # DE `_ROOT`, então cwd == alvo e o mutante sobrevivia. Trocar o cwd é o que
    # separa "resolve do lugar certo" de "resolve de onde chamaram".
    outro = _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    head_do_repo = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()[:12]

    assert (resolve_revision() or "").startswith(head_do_repo)
    assert not (resolve_revision() or "").startswith(outro)


def test_arvore_limpa_nao_marca_dirty(tmp_path) -> None:
    """Determinístico: repo próprio, não o estado do checkout de quem roda."""
    _git_repo(tmp_path)
    assert not (resolve_revision(cwd=tmp_path) or "").endswith("-dirty")


def test_arquivo_untracked_marca_dirty(tmp_path) -> None:
    """Untracked marca dirty: `diff-index` mente por omissão, `status` não."""
    # Mutação que mata: `dirty = False` constante, ou trocar por `diff-index`.
    # Arquivo novo é módulo importável, logo muda o que o processo executa.
    _git_repo(tmp_path)
    (tmp_path / "modulo_novo.py").write_text("x = 1\n")
    assert (resolve_revision(cwd=tmp_path) or "").endswith("-dirty")


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


def test_preflight_nao_da_verde_com_arvore_suja() -> None:
    """Caso DOMINANTE do dogfood: sujo dos dois lados, iguais por string."""
    # Mutação que mata: ramo de igualdade antes da checagem de `-dirty` ⇒ None ⇒
    # imprime "worker vivo na revisão do HEAD" para worker que pode ser outro.
    w = preflight_warning("aaaaaaaaaaaa-dirty", "aaaaaaaaaaaa-dirty")
    assert w is not None and "INCONCLUSIVA" in w


def test_preflight_trata_literal_desconhecido_como_ausencia() -> None:
    """O worker loga `desconhecido` quando sobe sem a env — não é uma revisão."""
    assert "nenhum processo" in (preflight_warning("desconhecido", "aaaaaaaaaaaa") or "")


def test_preflight_avisa_quando_ninguem_anunciou() -> None:
    """Ausência nunca colapsa em "está tudo bem"."""
    assert "nenhum processo" in (preflight_warning(None, "aaaaaaaaaaaa") or "")


# Linha REAL do worker nativo (copiada de `_dev_pids/worker.log`, 2026-08-05).
# O Celery prefixa com o formatter dele, então o JSON não começa na coluna 0.
_LINHA_REAL_CELERY = (
    "[2026-08-05 15:17:21,534: WARNING/ForkPoolWorker-1] "
    '{"message": "mathoms.worker.boot", "executor_revision": "ceca2e9b7604", '
    '"timestamp": "2026-08-05T18:17:21.530530Z", "level": "INFO", "logger": "mathoms.worker"}'
)


def test_le_a_linha_que_o_worker_REALMENTE_emite() -> None:
    """Regressão: o parser exigia `startswith("{")` e pulava todas as linhas."""
    # O teste original alimentava JSON puro inventado por mim. O produtor emite
    # com prefixo do Celery, então o preflight ficava cego no ambiente real —
    # descoberto pelo dono rodando de verdade, não pela suíte.
    assert boot_revision_from_log(_LINHA_REAL_CELERY) == "ceca2e9b7604"


def test_linha_de_ruido_do_celery_sem_json_nao_quebra() -> None:
    """O Celery loga a mesma mensagem 2×: uma sem JSON, outra com."""
    ruido = "[2026-08-05 15:17:21,530: INFO/ForkPoolWorker-1] mathoms.worker.boot"
    assert boot_revision_from_log(ruido) is None
    assert boot_revision_from_log(f"{ruido}\n{_LINHA_REAL_CELERY}") == "ceca2e9b7604"


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
