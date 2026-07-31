"""Gate executável da rotação Fernet (A34.l3 · ADR-171): avaliação pura das duas condições do G0 sobre reports sintéticos — janela fechada dá falso-limpo, lote interrompido não passa, failed nunca fecha o gate. Sem DB, sem vault, sem rede."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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
    """`_report(col_a=(rotated, skipped, failed))` → report no shape da task."""
    return {
        "dry_run": True,
        "targets": {
            name: {"rotated": r, "skipped": s, "failed": f} for name, (r, s, f) in targets.items()
        },
    }


def test_summarize_soma_todos_os_targets():
    gate = _load()
    report = _report(a=(1, 2, 3), b=(10, 20, 30))
    assert gate.summarize(report) == {"rotated": 11, "skipped": 22, "failed": 33}


def test_summarize_report_vazio():
    gate = _load()
    assert gate.summarize({}) == {"rotated": 0, "skipped": 0, "failed": 0}


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


def test_looks_local_reconhece_loopback_e_sqlite():
    """Rodar no laptop responde a pergunta errada em silêncio — a l3 é sobre
    o dado de PRODUÇÃO."""
    gate = _load()
    for alvo in ("localhost:5432/mathoms", "127.0.0.1/db", "sqlite:mathoms.db", "::1:5432/x"):
        assert gate.looks_local(alvo), alvo


def test_looks_local_nao_marca_host_remoto():
    gate = _load()
    for alvo in ("db.interno:5432/mathoms_prod", "postgres.svc:5432/app", "10.0.1.5:5432/x"):
        assert not gate.looks_local(alvo), alvo


def test_alvo_local_bloqueia_sem_allow_local(monkeypatch):
    import pytest

    gate = _load()
    monkeypatch.setattr(gate, "db_target", lambda: "localhost:5432/mathoms")
    with pytest.raises(gate.PreflightError) as exc:
        gate._require_prod_target(allow_local=False)
    assert "--allow-local" in str(exc.value)


def test_allow_local_aceito_depois_do_subcomando():
    """`preflight --allow-local` é a forma que se digita; definida só no parser
    do topo, argparse exigiria `--allow-local preflight` e falharia."""
    gate = _load()
    for cmd in ("preflight", "rotate", "verify"):
        args = gate.build_parser().parse_args([cmd, "--allow-local"])
        assert args.allow_local is True and args.cmd == cmd


def test_allow_local_libera_o_alvo(monkeypatch):
    gate = _load()
    monkeypatch.setattr(gate, "db_target", lambda: "localhost:5432/mathoms")
    assert gate._require_prod_target(allow_local=True) == "localhost:5432/mathoms"


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
