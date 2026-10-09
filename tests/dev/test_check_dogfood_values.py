"""Gate de valor do dogfood ([[ADR-442]]): formas, commit a commit, saída muda, falha."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_DEV = Path(__file__).resolve().parents[2] / "dev"


def _load(nome: str):
    spec = importlib.util.spec_from_file_location(nome, _DEV / f"{nome}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[nome] = module
    spec.loader.exec_module(module)
    return module


gate = _load("check_dogfood_values")
gerador = _load("build_dogfood_denylist")
nucleo = sys.modules["_dogfood_values"]

# Valores SINTÉTICOS que a denylist de teste trata como "do dogfood".
_REAL = 12345678  # R$ 123.456,78
_OUTRO = 98765432  # R$ 987.654,32
_CANARIO = 123456789  # R$ 1.234.567,89
_CHAVE = bytes(range(32))
_FORMAS_DO_REAL = ("123.456,78", "123456.78", "123,456.78", "123_456.78", "12345678", "123456")


def _gravar_denylist(diretorio: Path, *, idade_dias: int = 0, valores=(_REAL, _OUTRO)) -> None:
    diretorio.mkdir(parents=True, exist_ok=True)
    todos = set().union(*(gerador.variantes(v) for v in valores)) | {_CANARIO}
    (diretorio / nucleo.KEY_NAME).write_text(_CHAVE.hex())
    (diretorio / nucleo.DENYLIST_NAME).write_text(
        "\n".join(nucleo.digest(_CHAVE, v) for v in todos)
    )
    gerada = datetime.now(timezone.utc) - timedelta(days=idade_dias)
    manifesto = {"generated_at": gerada.isoformat(), "canary_cents": _CANARIO}
    (diretorio / nucleo.MANIFEST_NAME).write_text(json.dumps(manifesto))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def denylist(tmp_path, monkeypatch) -> Path:
    diretorio = tmp_path / "config"
    _gravar_denylist(diretorio)
    monkeypatch.setenv(nucleo.DIR_ENV, str(diretorio))
    return diretorio


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    for var, valor in (("NAME", "Teste"), ("EMAIL", "teste@example.com")):
        monkeypatch.setenv(f"GIT_AUTHOR_{var}", valor)
        monkeypatch.setenv(f"GIT_COMMITTER_{var}", valor)
    _git(raiz, "init", "-q")
    monkeypatch.chdir(raiz)
    return raiz


def _stage(repo: Path, nome: str, texto: str) -> None:
    (repo / nome).write_text(texto, encoding="utf-8")
    _git(repo, "add", nome)


def _sem_valor(texto: str) -> bool:
    return not any(f in texto for f in _FORMAS_DO_REAL)


@pytest.mark.parametrize(
    "linha",
    [
        "saldo de R$ 123.456,78 no run",
        '{"valor": 123456.78}',
        "USD 123,456.78 convertido",
        "valor = 123_456.78",
        "caiu para R$ 123.456 no card",
    ],
)
def test_cada_forma_do_valor_reprova(denylist, repo, capsys, linha):
    _stage(repo, "nota.md", f"cabeçalho\n{linha}\n")
    assert gate.main(["--staged"]) == 1
    erro = capsys.readouterr().err
    assert "nota.md:2: VALOR_DOGFOOD" in erro
    assert _sem_valor(erro)


def test_valor_sintetico_fora_da_lista_passa(denylist, repo):
    _stage(repo, "nota.md", "saldo de R$ 111.111,11 e de 222222.22\n")
    assert gate.main(["--staged"]) == 0


def test_valor_abaixo_do_tier_a_nunca_e_consultado(denylist, repo, monkeypatch):
    chamadas = []
    monkeypatch.setattr(gate.Denylist, "contem", lambda self, c: chamadas.append(c) or False)
    _stage(repo, "nota.md", "gasto de R$ 1.234,56 e de R$ 50.000,00\n")
    gate.main(["--staged"])
    assert chamadas == []


def test_mensagem_de_commit_reprova_e_ignora_comentario(denylist, tmp_path, capsys):
    mensagem = tmp_path / "COMMIT_EDITMSG"
    mensagem.write_text("fix: algo\n\n# R$ 987.654,32 em comentário\nmediu 987654.32\n")
    assert gate.main(["--commit-msg", str(mensagem)]) == 1
    assert "COMMIT_EDITMSG:4: VALOR_DOGFOOD" in capsys.readouterr().err


def test_pre_push_le_commit_a_commit_e_nao_o_diff_liquido(denylist, repo, monkeypatch):
    _stage(repo, "base.md", "base\n")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    _stage(repo, "wip.md", "medido: R$ 123.456,78\n")
    _git(repo, "commit", "-q", "-m", "wip")
    _stage(repo, "wip.md", "medido: positivo\n")
    _git(repo, "commit", "-q", "-m", "saneia")
    assert _sem_valor(_git(repo, "diff", f"{base}..HEAD")), "diff líquido não pode conter o valor"
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", base)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", _git(repo, "rev-parse", "HEAD").strip())
    assert gate.main(["--pre-push"]) == 1


def test_conteudo_que_comeca_com_mais_mais_nao_cega_o_hunk(denylist, repo):
    _stage(repo, "nota.md", "++ linha que vira +++ no diff\nR$ 123.456,78\n")
    assert gate.main(["--staged"]) == 1


def test_sem_diretorio_o_gate_fica_inativo(repo, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(nucleo.DIR_ENV, str(tmp_path / "nao-existe"))
    _stage(repo, "nota.md", "R$ 123.456,78\n")
    assert gate.main(["--staged"]) == 0
    assert "inativo" in capsys.readouterr().err


def test_diretorio_sem_denylist_falha_fechado(repo, tmp_path, monkeypatch):
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    monkeypatch.setenv(nucleo.DIR_ENV, str(vazio))
    assert gate.main(["--staged"]) == 1


def test_denylist_corrompida_falha_sem_vazar(denylist, repo, capsys):
    (denylist / nucleo.DENYLIST_NAME).write_text("123456.78\nlixo\n")
    assert gate.main(["--staged"]) == 1
    assert _sem_valor(capsys.readouterr().err)


def test_manifesto_velho_avisa_e_passa(tmp_path, repo, monkeypatch, capsys):
    diretorio = tmp_path / "velho"
    _gravar_denylist(diretorio, idade_dias=30)
    monkeypatch.setenv(nucleo.DIR_ENV, str(diretorio))
    assert gate.main(["--staged"]) == 0
    assert "30 dias" in capsys.readouterr().err


def test_self_test_acha_o_canario(denylist):
    assert gate.main(["--self-test"]) == 0


def test_tree_lista_o_arquivo_versionado(denylist, repo, capsys):
    _stage(repo, "a.md", "nada\n")
    _stage(repo, "b.md", "x\n123_456.78\n")
    assert gate.main(["--tree"]) == 1
    assert "b.md:2: VALOR_DOGFOOD" in capsys.readouterr().err


def test_variantes_cobrem_reais_inteiros_que_seguem_tier_a():
    assert gerador.variantes(_REAL) == {12345678, 12345600, 12345700}
    assert gerador.variantes(1_000_000) == set(), "R$ 10.000,00 redondo não é tier A"


def test_folhas_monetarias_ignoram_campo_nao_monetario():
    payload = {"saldo": 123456.78, "taxa_pct": 123456.78, "itens": [{"valor": "987.654,32"}]}
    assert gerador.valores_do_dogfood([payload]) == gerador.variantes(_REAL) | gerador.variantes(
        _OUTRO
    )


def test_constantes_publicas_saem_da_lista(tmp_path):
    con = sqlite3.connect(":memory:")
    con.execute(
        "create table fiscal_parameters (year int, pgbl_limit_brl_cents int, ir_brackets_anual text)"
    )
    faixas = json.dumps({"faixas": [{"upper_brl_cents": 2846720, "deducao_brl_cents": 213504}]})
    con.execute("insert into fiscal_parameters values (2025, 0, ?)", (faixas,))
    curadas = tmp_path / "publicas.json"
    curadas.write_text(json.dumps([{"cents": 1675434, "fonte": "teste"}]))
    assert gerador.constantes_publicas(con, curadas) == {0, 2846720, 213504, 1675434}


def test_gerador_recusa_gravar_dentro_de_repositorio(repo):
    with pytest.raises(SystemExit):
        gerador.gravar_denylist(repo / "config", {_REAL}, rotacionar=False)


def test_gerador_grava_0600_e_o_canario_e_detectavel(tmp_path, monkeypatch, capsys):
    diretorio = tmp_path / "fora"
    manifesto = gerador.gravar_denylist(diretorio, {_REAL}, rotacionar=False)
    assert oct((diretorio / nucleo.DENYLIST_NAME).stat().st_mode & 0o777) == "0o600"
    assert set(manifesto) >= {"generated_at", "n_valores", "n_digests", "canary_cents"}
    monkeypatch.setenv(nucleo.DIR_ENV, str(diretorio))
    assert gate.main(["--self-test"]) == 0


@pytest.mark.parametrize(
    "valor", [1e30, "1e400", "1e9999999", "-1E+1000000", "NaN", "Infinity", 10**20, True, None]
)
def test_escalar_fora_do_dominio_monetario_e_ignorado(valor):
    assert gerador.centavos_do_escalar(valor) == set()


def _pr_publicado_recebe_main_antiga(repo: Path) -> str:
    """Branch `pr` já pushada recebe merge de uma main cujo commit antigo tem o valor."""
    _stage(repo, "base.md", "base\n")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "pr")
    _stage(repo, "pr.md", "trabalho do PR\n")
    _git(repo, "commit", "-q", "-m", "pr")
    pr_publicado = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-q", "-")
    _stage(repo, "antigo.md", "medido: R$ 123.456,78\n")
    _git(repo, "commit", "-q", "-m", "main antiga, já pública")
    _git(repo, "update-ref", "refs/remotes/origin/main", _git(repo, "rev-parse", "HEAD").strip())
    _git(repo, "update-ref", "refs/remotes/origin/pr", pr_publicado)
    _git(repo, "checkout", "-q", "pr")
    _git(repo, "merge", "-q", "--no-edit", "refs/remotes/origin/main")
    return pr_publicado


def test_pre_push_de_merge_da_main_nao_reescaneia_o_que_ja_e_publico(denylist, repo, monkeypatch):
    """Com `de..para`, o merge da main numa branch já pushada reescaneava a main: um valor
    antigo dela bloqueava o push de todo PR (2026-10-09). Commit novo segue barrado."""
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", _pr_publicado_recebe_main_antiga(repo))
    monkeypatch.setenv("PRE_COMMIT_TO_REF", _git(repo, "rev-parse", "HEAD").strip())
    assert gate.main(["--pre-push"]) == 0
    _stage(repo, "novo.md", "medido: R$ 123.456,78\n")
    _git(repo, "commit", "-q", "-m", "commit novo do PR")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", _git(repo, "rev-parse", "HEAD").strip())
    assert gate.main(["--pre-push"]) == 1
