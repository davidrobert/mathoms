"""Testes de `dev/lane_pickup.py` — a sonda de ocupação viva.

O veredito é a parte que decide pickup, e ela é pura: recebe frontmatter +
deps pendentes + sinais. Os sinais vêm de git e são injetados, não mockados
com MagicMock (CLAUDE.md §Testes: fakes nomeados).

O caso de origem é o da A40.l35 em 2026-08-13: frontmatter `open`, sem branch
remota, sem PR — e uma sessão viva num worktree há 2h.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dev import lane_pickup
from dev.lane_pickup import Occupancy, _pending_deps, _verdict

_OCUPADA = [Occupancy("worktree", "a40-l35-bundle [agent/...] · 20 arq. sujos")]


def test_ocupacao_vence_status_nao_terminal() -> None:
    # A l35 dizia `open` e sem dep pendente. O sinal de worktree é o único que
    # a contradiz — e tem de vencer, senão a sonda repete o erro da superfície.
    # Estreitado em 2026-08-17: vence status NÃO-terminal (ver o teste abaixo).
    assert _verdict({"status": "open"}, [], _OCUPADA).startswith("OCUPADA")


# ---------------------------------------------------------------------------
# Regressões medidas em 2026-08-17, varrendo a A40 inteira com `--sprint A40`.
# As duas fazem a sonda dizer OCUPADA para lane que ninguém está tocando —
# e falso-positivo em ferramenta de pickup custa o mesmo que falso-negativo:
# manda o agente para outra lane, e a lane certa fica parada.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token, ref",
    [
        ("a40-l5", "agent/a40-l50-consolidate-baseline/20260814-1530"),
        ("a40-l5", "agent/a40-l56-tabela-fiscal/20260815-0900"),
        ("a40-l1", "agent/a40-l18-criticidade-de-stage/20260806-0900"),
        ("a40-l2", "a40-l22-base"),
        ("a40-l3", "agent/a40-l34-base-limite-pgbl/20260811-0330"),
    ],
)
def test_token_de_lane_nao_casa_por_prefixo(token: str, ref: str) -> None:
    """`a40-l5` não é `a40-l50`. O dígito seguinte muda a lane, não a decora."""
    assert not lane_pickup._mentions(token, ref)


@pytest.mark.parametrize(
    "token, ref",
    [
        ("a40-l5", "agent/a40-l5-contrato-view-model/20260808-2123"),
        ("a40-l5", "agent/a40-l5/20260811-0200"),
        ("a40-l18", "claude/ataque-a40-l18-3c4356"),
        ("a40-l35", "a40-l35-bundle"),
        ("a40-l63", "origin/agent/a40-l63-conversao-me/20260817-1720"),
        ("a40-l2", "agent/a40-l2-3c1-carrier/20260808-0450"),
    ],
)
def test_token_de_lane_casa_a_propria_lane(token: str, ref: str) -> None:
    """Estreitar não pode cegar: hífen, barra e fim de string são fronteira."""
    assert lane_pickup._mentions(token, ref)


def test_mentions_ignora_caixa() -> None:
    assert lane_pickup._mentions("a40-l5", "Agent/A40-L5-Contrato/2026")


# Medido na A40: as 34 lanes `shipped` respondiam OCUPADA por causa das próprias
# branches já mergeadas. "Não pegue sem falar com quem está nela" manda procurar
# interlocutor que não existe; o certo é "nada a pegar".
@pytest.mark.parametrize("status", ["shipped", "cancelled"])
def test_terminal_vence_branch_residual(status: str) -> None:
    """Lane entregue não é 'ocupada' — a branch que sobrou é o fim normal dela."""
    assert _verdict({"status": status}, [], _OCUPADA).startswith("TERMINAL")


# Caso real: `a40-l35-bundle` tem 6 arquivos não-commitados numa lane `shipped`.
# Reclassificar o veredito não pode apagar essa linha, senão o fix troca um
# falso-positivo por um ponto cego.
def test_terminal_nao_engole_o_sinal_de_ocupacao(monkeypatch: pytest.MonkeyPatch) -> None:
    """O veredito muda; a evidência continua IMPRESSA — worktree sujo importa."""
    sujo = [Occupancy("worktree", "a40-l35-bundle [agent/a40-l62-pr1] · 6 arq. sujos")]
    monkeypatch.setattr(lane_pickup, "occupancy_signals", lambda *_: (sujo, []))
    lanes = {"A1.l1": {"status": "shipped", "title": "t", "priority": "P1"}}
    texto, code = lane_pickup.report("A1.l1", lanes)
    assert "TERMINAL" in texto
    assert "6 arq. sujos" in texto, "sinal medido não pode sumir do relatório"
    assert code == 1


def test_livre_quando_open_sem_dep_e_sem_sinal() -> None:
    assert _verdict({"status": "open"}, [], []) == "LIVRE"


def test_planned_nao_e_pegavel() -> None:
    assert _verdict({"status": "planned"}, [], []).startswith("NÃO LIBERADA")


@pytest.mark.parametrize("status", ["shipped", "cancelled"])
def test_terminal_nao_tem_o_que_pegar(status: str) -> None:
    assert _verdict({"status": status}, [], []).startswith("TERMINAL")


def test_dep_pendente_bloqueia() -> None:
    assert _verdict({"status": "open"}, ["A40.l5 (in_progress)"], []).startswith("BLOQUEADA")


def test_amarra_parcial_destrava_dep_pendente() -> None:
    verdict = _verdict({"status": "open", "partial_delivery": True}, ["A40.l5 (in_progress)"], [])
    assert verdict.startswith("PEGÁVEL COM AMARRA PARCIAL")


def test_pending_deps_ignora_dep_terminal_e_desconhecida() -> None:
    lanes = {"A1.l1": {"status": "shipped"}, "A1.l2": {"status": "open"}}
    front = {"depends_on": ["[[A1.l1]]", "[[A1.l2]]", "[[A1.l404]]"]}
    assert _pending_deps(front, lanes) == ["A1.l2 (open)"]


def test_pending_deps_aceita_wikilink_com_apelido() -> None:
    lanes = {"A1.l1": {"status": "open"}}
    assert _pending_deps({"depends_on": ["[[A1.l1|a primeira]]"]}, lanes) == ["A1.l1 (open)"]


def test_id_ausente_sem_sinal_e_id_livre(monkeypatch: pytest.MonkeyPatch) -> None:
    # Contrato novo (2026-08-16): devolve (sinais, degradações).
    monkeypatch.setattr(lane_pickup, "occupancy_signals", lambda *_: ([], []))
    text, code = lane_pickup._report_unknown("A40.l99")
    assert "id livre" in text
    assert code == 2


def test_id_ausente_com_sinal_avisa_para_nao_realocar(monkeypatch: pytest.MonkeyPatch) -> None:
    # §Pendência 13 da A40: 8 renumerações numa sessão porque `ls` local mede
    # o teto errado enquanto outra sessão segura o id sem commitar.
    monkeypatch.setattr(
        lane_pickup,
        "occupancy_signals",
        lambda *_: ([Occupancy("branch", "agent/a40-l61-x/2026")], []),
    )
    text, code = lane_pickup._report_unknown("A40.l61")
    assert "TOMADO" in text
    assert code == 1


# ---------------------------------------------------------------------------
# Sondas cegas — o modo de falha PERIGOSO não é o crash, é o silêncio.
#
# Medido em 2026-08-16: o tool crashou com FileNotFoundError num worktree
# registrado cujo diretório sumiu (`_scratch/a40-l5-pr3-clean`). `subprocess.run`
# levanta ANTES de rodar o git, então `check=False` não protege.
#
# O crash é ruidoso e, portanto, seguro. O que assusta é a variante muda: se a
# sonda falhar sem crashar, `_worktrees_mentioning` devolve lista vazia e a lane
# vira LIVRE — que é exatamente a colisão que este tool existe para evitar.
# ---------------------------------------------------------------------------


class _WorktreeFake:
    """Substituto nomeado de `git worktree list` + git por-worktree (CLAUDE.md §Testes)."""

    def __init__(self, paths, *, branches=None, sumidos=()):
        self.paths = [Path(p) for p in paths]
        self.branches = branches or {}
        self.sumidos = {str(p) for p in sumidos}

    def worktree_paths(self):
        return list(self.paths)

    def git(self, *args, cwd=None):
        if cwd is not None and str(cwd) in self.sumidos:
            raise FileNotFoundError(2, "No such file or directory", str(cwd))
        if args and args[0] == "rev-parse":
            return self.branches.get(str(cwd), "main") + "\n"
        return ""


@pytest.fixture
def worktree_sumido(monkeypatch, tmp_path):
    vivo = tmp_path / "a40-l99-viva"
    vivo.mkdir()
    morto = tmp_path / "a40-l99-fantasma"  # registrado, nunca criado
    fake = _WorktreeFake(
        [vivo, morto],
        branches={str(vivo): "agent/outra-coisa/2026"},
        sumidos=[morto],
    )
    monkeypatch.setattr(lane_pickup, "_worktree_paths", fake.worktree_paths)
    monkeypatch.setattr(lane_pickup, "_git", fake.git)
    return fake


def test_worktree_sumido_nao_derruba_a_sonda(worktree_sumido) -> None:
    """Regressão do crash de 2026-08-16 — o tool tem de responder, não abortar."""
    lane_pickup._worktrees_mentioning("a40-l99")


def test_worktree_sumido_vira_degradacao_declarada(worktree_sumido) -> None:
    """Não basta não crashar: a sonda cega tem de APARECER."""
    _, degradacoes = lane_pickup._worktrees_mentioning("a40-l99")
    assert degradacoes, "sonda que não rodou não pode sumir do relatório"
    assert any("fantasma" in d.motivo or "fantasma" in d.probe for d in degradacoes)


def test_veredito_nao_afirma_livre_limpo_com_sonda_cega() -> None:
    """A direção perigosa é o LIVRE falso — degradação tem de contaminar o veredito."""
    cega = [lane_pickup.Degradacao("worktree", "a40-l99-fantasma: diretório não existe")]
    veredito = _verdict({"status": "open"}, [], [], degradacoes=cega)
    assert veredito != "LIVRE"
    assert "RESSALVA" in veredito.upper()


def test_degradacao_nao_mascara_sinal_real() -> None:
    """Ocupação medida continua vencendo — a ressalva não pode diluir o sinal."""
    veredito = _verdict(
        {"status": "open"},
        [],
        _OCUPADA,
        degradacoes=[lane_pickup.Degradacao("worktree", "x: diretório não existe")],
    )
    assert veredito.startswith("OCUPADA")


def test_relatorio_prescreve_o_conserto_do_ambiente(worktree_sumido) -> None:
    """Diagnóstico read-only: prescreve `git worktree prune`, não muta git."""
    texto, _ = lane_pickup.report("A40.l99", {})
    assert "worktree prune" in texto


# O modo SILENCIOSO, que é o perigoso: antes do fix, git com exit != 0 devolvia
# string vazia, o worktree não casava o token e era pulado sem deixar rastro —
# LIVRE falso.
def test_worktree_que_existe_mas_git_falha_nao_some_calado(monkeypatch, tmp_path) -> None:
    """Git que falha vira degradação declarada, não worktree pulado."""
    quebrado = tmp_path / "worktree-corrompido"
    quebrado.mkdir()
    monkeypatch.setattr(lane_pickup, "_worktree_paths", lambda: [quebrado])
    monkeypatch.setattr(
        lane_pickup,
        "_git_probe",
        lambda *a, **kw: ("", "fatal: not a git repository"),
    )
    sinais, degradacoes = lane_pickup._worktrees_mentioning("a40-l99")
    assert sinais == []
    assert len(degradacoes) == 1
    assert "not a git repository" in degradacoes[0].motivo


def test_remedio_do_prune_so_aparece_quando_e_registro_orfao() -> None:
    """Prescrição errada é ruído: git corrompido não se conserta com `prune`."""
    orfao = [lane_pickup.Degradacao("worktree", "x: FileNotFoundError: No such file or directory")]
    corrompido = [lane_pickup.Degradacao("worktree", "y: fatal: not a git repository")]
    assert any("prune" in ln for ln in lane_pickup._linhas_de_degradacao(orfao))
    assert not any("prune" in ln for ln in lane_pickup._linhas_de_degradacao(corrompido))
