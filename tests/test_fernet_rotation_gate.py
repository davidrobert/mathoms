"""Gate executável da rotação Fernet (A34.l3 · ADR-171): avaliação pura das duas condições do G0 sobre reports sintéticos — janela fechada dá falso-limpo, lote interrompido não passa, failed nunca fecha o gate. Sem DB, sem vault, sem rede."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_MOD = "fernet_rotation_gate"

OPEN_WINDOW = 2
CLOSED_WINDOW = 1


def _load():
    spec = importlib.util.spec_from_file_location(_MOD, _REPO / "dev" / f"{_MOD}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MOD] = module
    spec.loader.exec_module(module)
    return module


def _report(**targets) -> dict:
    """`_report(col_a=(rotated, skipped, failed))`; tupla de 5 inclui `(plaintext, após-cutover)`."""
    out = {}
    for name, counts in targets.items():
        r, sk, f = counts[:3]
        pt, pt_novo = (counts[3], counts[4]) if len(counts) == 5 else (0, 0)
        out[name] = {
            "rotated": r,
            "skipped": sk,
            "failed": f,
            "plaintext": pt,
            "plaintext_after_cutover": pt_novo,
        }
    return {"dry_run": True, "targets": out}


def test_summarize_soma_todos_os_targets():
    gate = _load()
    report = _report(a=(1, 2, 3), b=(10, 20, 30))
    assert gate.summarize(report) == {
        "rotated": 11,
        "skipped": 22,
        "failed": 33,
        "plaintext": 0,
        "plaintext_after_cutover": 0,
    }


def test_summarize_report_vazio():
    gate = _load()
    assert gate.summarize({}) == {
        "rotated": 0,
        "skipped": 0,
        "failed": 0,
        "plaintext": 0,
        "plaintext_after_cutover": 0,
    }


def test_janela_fechada_bloqueia_mesmo_com_report_limpo():
    """O caso perigoso: sem a chave antiga no conjunto, o valor dela vira `skipped`
    e o report sai limpo sem provar nada."""
    gate = _load()
    limpo = _report(cpf=(0, 500, 0))
    assert gate.evaluate(limpo, CLOSED_WINDOW, expect_idle=True)
    assert "falso-limpo" in gate.evaluate(limpo, CLOSED_WINDOW, expect_idle=True)[0]


def test_janela_aberta_com_report_ocioso_passa():
    gate = _load()
    assert gate.evaluate(_report(cpf=(0, 500, 0)), OPEN_WINDOW, expect_idle=True) == []


def test_failed_bloqueia_o_gate():
    gate = _load()
    problems = gate.evaluate(_report(art=(0, 10, 1)), OPEN_WINDOW, expect_idle=True)
    assert len(problems) == 1
    assert "failed=1" in problems[0]


def test_lote_interrompido_nao_passa_no_segundo_passe():
    """A task é resumível — sem exigir `rotated=0` no 2º passe, um lote parcial
    passaria como sucesso."""
    gate = _load()
    problems = gate.evaluate(_report(cpf=(7, 100, 0)), OPEN_WINDOW, expect_idle=True)
    assert len(problems) == 1
    assert "rotated=7" in problems[0]


def test_primeiro_passe_tolera_rotated_positivo():
    gate = _load()
    assert gate.evaluate(_report(cpf=(7, 100, 0)), OPEN_WINDOW, expect_idle=False) == []


def test_janela_fechada_e_failed_acumulam_problemas():
    gate = _load()
    problems = gate.evaluate(_report(a=(3, 1, 2)), CLOSED_WINDOW, expect_idle=True)
    assert len(problems) == 3


def test_format_report_nao_vaza_nada_alem_de_contadores():
    gate = _load()
    out = gate.format_report(_report(family_members_cpf=(1, 2, 0)))
    assert "family_members_cpf" in out and "TOTAL" in out


def test_sqlite_ausente_bloqueia(tmp_path):
    """Rodar de um worktree aponta para um `mathoms.db` que não existe — e
    `rotate` diria "nada a rotacionar" com toda a confiança sobre o banco errado."""
    gate = _load()
    problem = gate.sqlite_problem(tmp_path / "nao-existe.db")
    assert problem and "NÃO existe" in problem


def test_sqlite_vazio_bloqueia(tmp_path):
    gate = _load()
    vazio = tmp_path / "mathoms.db"
    vazio.touch()
    problem = gate.sqlite_problem(vazio)
    assert problem and "vazio" in problem


def test_sqlite_com_dado_passa(tmp_path):
    gate = _load()
    real = tmp_path / "mathoms.db"
    real.write_bytes(b"SQLite format 3\x00" + b"\x00" * 500)
    assert gate.sqlite_problem(real) is None


def test_caminho_sqlite_preserva_a_barra_inicial(monkeypatch):
    """`sqlite:////abs` → urlparse devolve `//abs`; um lstrip("/") ingênuo come
    as duas e vira caminho RELATIVO, que nunca existe → falso bloqueio."""
    gate = _load()

    class _S:
        DATABASE_URL = "sqlite+aiosqlite:////srv/mathoms/mathoms.db"

    import types

    fake = types.ModuleType("backend.app.core.config")
    fake.settings = _S()
    monkeypatch.setitem(sys.modules, "backend.app.core.config", fake)
    desc, path = gate.db_target()
    assert str(path) == "/srv/mathoms/mathoms.db"
    assert path.is_absolute()


def test_query_de_kid_usa_o_literal_do_dialeto():
    """`->>` sobre booleano JSON devolve TEXTO 'true' no Postgres e o INTEIRO 1
    no sqlite. Literal errado casa zero linhas e a auditoria sai "limpa" sem ter
    olhado nada — medido contra o dogfood: vazio com 11.722 artifacts cifrados."""
    gate = _load()
    assert "= 1" in gate.kid_audit_sql(is_sqlite=True)
    assert "'true'" not in gate.kid_audit_sql(is_sqlite=True)
    assert "'true'" in gate.kid_audit_sql(is_sqlite=False)


def test_alvo_nao_sqlite_nao_e_checado():
    """Postgres não tem arquivo para inspecionar — sem falso bloqueio."""
    gate = _load()
    assert gate.sqlite_problem(None) is None


def test_roda_da_raiz_do_repo_sem_module_not_found():
    """`python3 dev/fernet_rotation_gate.py` põe `dev/` no sys.path, não a raiz.
    Sem o insert de _REPO_ROOT, `import backend.app...` quebra — e o erro só
    aparece em produção, porque a avaliação pura acima nunca importa backend."""
    import subprocess

    proc = subprocess.run(
        [sys.executable, "dev/fernet_rotation_gate.py", "preflight"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "MATHOMS_FERNET_KEY": "x" * 44 + "="},
        timeout=60,
    )
    combined = proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in combined, combined[-800:]
    # Qualquer uma destas provou que o import de backend passou: o guard de
    # alvo local, o de janela fechada, ou a leitura das chaves.
    assert "banco alvo" in combined, combined[-800:]


def test_help_nao_exige_vault(monkeypatch, capsys):
    """`--help` precisa funcionar sem MATHOMS_FERNET_KEY — imports do vault são lazy."""
    gate = _load()
    monkeypatch.delenv("MATHOMS_FERNET_KEY", raising=False)
    monkeypatch.delenv("MATHOMS_FERNET_KEYS", raising=False)
    monkeypatch.setattr("sys.argv", ["fernet_rotation_gate.py", "--help"])
    try:
        gate.main()
    except SystemExit as exc:
        assert exc.code == 0
    assert "preflight" in capsys.readouterr().out


# ─── corpus vazio (medido 2026-08-19) ───


def test_corpus_vazio_nao_fecha_o_gate():
    """O furo medido: DB com schema e ZERO linhas fechava com "GATE OK"."""
    gate = _load()
    vazio = _report(cpf=(0, 0, 0), artifacts=(0, 0, 0))
    problems = gate.evaluate(vazio, OPEN_WINDOW, expect_idle=True)
    assert problems
    assert "todo-zero" in problems[0]


def test_passe_real_com_skipped_fecha_o_gate():
    """O contraste: mesmos rotated/failed, mas com material inspecionado."""
    gate = _load()
    real = _report(cpf=(0, 12150, 0))
    assert gate.evaluate(real, OPEN_WINDOW, expect_idle=True) == []


def test_empty_corpus_problem_olha_a_soma_e_nao_so_rotated():
    gate = _load()
    assert gate.empty_corpus_problem({"rotated": 0, "skipped": 0, "failed": 0})
    assert gate.empty_corpus_problem({"rotated": 0, "skipped": 1, "failed": 0}) is None
    assert gate.empty_corpus_problem({"rotated": 0, "skipped": 0, "failed": 1}) is None


# ─── armadilha do fallback (runbook §7) ───


def test_armadilha_quando_fallback_difere_da_primaria():
    gate = _load()
    problem = gate.fallback_problem("05d68234", "51c36c21")
    assert problem and "ARMADILHA" in problem


def test_fallback_igual_a_primaria_esta_ok():
    gate = _load()
    assert gate.fallback_problem("05d68234", "05d68234") is None


def test_fallback_ausente_esta_ok():
    """Fora de janela, sem FERNET_KEY setada, não há o que comparar."""
    gate = _load()
    assert gate.fallback_problem("05d68234", "") is None


def test_kid_of_bate_com_o_key_id_do_crypto(monkeypatch):
    """Amarra a fórmula duplicada em `kid_of` à canônica em `crypto._key_id`."""
    gate = _load()
    from backend.app.core.config import settings
    from backend.app.services.security import crypto

    chave = "NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA="
    monkeypatch.setattr(settings, "FERNET_KEYS", chave)
    assert gate.kid_of(chave) == crypto._key_id()


# ─── janela que já cumpriu a função ───


def test_janela_sem_funcao_quando_nada_sobrou_na_antiga():
    gate = _load()
    problem = gate.stale_window_problem({"05d68234": 15874}, "05d68234")
    assert problem and "passo 7" in problem


def test_janela_com_residuo_na_antiga_nao_e_reclamada():
    """Ainda há o que rotacionar — a janela está fazendo o trabalho dela."""
    gate = _load()
    inventory = {"05d68234": 15874, "51c36c21": 42}
    assert gate.stale_window_problem(inventory, "05d68234") is None


def test_plaintext_nao_conta_como_residuo_de_chave_antiga():
    """`<sem kid>` é artifact não cifrado, não resíduo de rotação."""
    gate = _load()
    inventory = {"05d68234": 15874, "<sem kid>": 418}
    assert gate.stale_window_problem(inventory, "05d68234") is not None


def test_window_problems_ignora_stale_fora_de_janela():
    """Com 1 chave a janela está fechada — cobrar "janela sem função" seria ruído."""
    gate = _load()
    inventory = {"05d68234": 15874}
    assert gate.window_problems("05d68234", "05d68234", inventory, CLOSED_WINDOW) == []


def test_window_problems_acumula_armadilha_e_stale():
    gate = _load()
    problems = gate.window_problems("05d68234", "51c36c21", {"05d68234": 15874}, OPEN_WINDOW)
    assert len(problems) == 2


def test_require_any_key_bloqueia_ambiente_sem_chave():
    gate = _load()
    with pytest.raises(gate.PreflightError):
        gate._require_any_key(0)
    assert gate._require_any_key(1) is None


# ─── plaintext: bucket próprio, gate por recência ───


def test_plaintext_recente_bloqueia_o_gate():
    """Drift vivo: row em claro gravada DEPOIS do cutover de encryption."""
    gate = _load()
    report = _report(artifacts=(0, 15874, 0, 1, 1))
    problems = gate.evaluate(report, OPEN_WINDOW, expect_idle=True)
    assert problems
    assert "plaintext_after_cutover" in problems[0]


def test_plaintext_historico_nao_bloqueia():
    """Resíduo pré-cutover é dívida conhecida, não drift — não pode travar o gate."""
    gate = _load()
    report = _report(artifacts=(0, 15874, 0, 418, 0))
    assert gate.evaluate(report, OPEN_WINDOW, expect_idle=True) == []


def test_gate_de_plaintext_nao_nasce_morto():
    """O absoluto zera após o backfill; o recorte de recência continua vivo."""
    gate = _load()
    pos_backfill = _report(artifacts=(0, 16292, 0, 0, 0))
    assert gate.evaluate(pos_backfill, OPEN_WINDOW, expect_idle=True) == []
    drift = _report(artifacts=(0, 16292, 0, 1, 1))
    assert gate.evaluate(drift, OPEN_WINDOW, expect_idle=True)


def test_corpus_so_de_plaintext_nao_passa_como_vazio():
    """`skipped` deixou de absorver plaintext — o corpus 100% em claro é visível."""
    gate = _load()
    report = _report(artifacts=(0, 0, 0, 500, 0))
    assert gate.summarize(report)["plaintext"] == 500
    assert gate.empty_corpus_problem(gate.summarize(report)) is None


def test_plaintext_problem_isola_o_recorte():
    gate = _load()
    assert gate.plaintext_problem({"plaintext": 418, "plaintext_after_cutover": 0}) is None
    assert gate.plaintext_problem({"plaintext": 1, "plaintext_after_cutover": 1})
    assert gate.plaintext_problem({}) is None
