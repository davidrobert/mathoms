"""Auditoria da proteção de main (ADR-415): o SHA que entrou foi gateado?
Casos ancorados em merges reais de 2026-08-25. Sem rede — `gh` nunca é chamado."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_audit_merge_protection as audit  # noqa: E402
from dev.ci_audit_merge_protection import (  # noqa: E402
    ABSENT,
    GATED,
    LATE,
    RED,
    UNKNOWN,
    MergeVerdict,
    audit_shas,
    classify,
    verdict_for_sha,
)

MERGE_TS = "2026-08-25T11:57:42Z"


def _check(conclusion: str = "success", completed_at: str = "2026-08-25T11:50:00Z") -> dict:
    return {"name": audit.GATE_CHECK, "conclusion": conclusion, "completed_at": completed_at}


def _fake_gh(
    pulls: dict[str, list[dict]],
    checks: dict[str, list[dict]],
    suites: list[dict] | None = None,
    suites_error: str | None = None,
    existing_issue: bool = False,
) -> Any:
    """Runner que responde aos 3 endpoints reais, por prefixo de path."""
    calls: list[str] = []

    def _suites_page(path: str) -> str:
        if suites_error:
            raise RuntimeError(suites_error)
        page = int(path.split("&page=")[1]) if "&page=" in path else 1
        return json.dumps(suites or [] if page == 1 else [])

    def _match(path: str, table: dict[str, list[dict]], endpoint: str) -> str | None:
        for sha, payload in table.items():
            if f"commits/{sha}/{endpoint}" in path:
                return json.dumps(payload if endpoint == "pulls" else {"check_runs": payload})
        return None

    def run(args: list[str]) -> str:
        # Grava a chamada INTEIRA: gravar `args[1]` registrava "create" para
        # `["issue","create",...]`, e o guard de dry-run (que procurava por
        # "issue") passava sem nunca casar nada. 5 mutações sobreviviam.
        calls.append(" ".join(args))
        if args[0] == "issue":
            return json.dumps([{"number": 99}] if existing_issue else [])
        return _api_response(args[1] if len(args) > 1 else "")

    def _api_response(path: str) -> str:
        if "rulesets/rule-suites" in path:
            return _suites_page(path)
        return _match(path, pulls, "pulls") or _match(path, checks, "check-runs") or json.dumps([])

    run.calls = calls  # type: ignore[attr-defined]
    return run


class TestClassify:
    """O predicado é o veredito NO MOMENTO DO MERGE. Ler só `conclusion` deixa
    passar o caso mais traiçoeiro: verde que chegou depois do merge."""

    def test_verde_antes_do_merge_gateia(self) -> None:
        assert classify(_check(), MERGE_TS)[0] == GATED

    def test_verde_depois_do_merge_nao_gateia(self) -> None:
        """#1699 (2026-08-25): `All checks green` = success 43s APÓS o merge."""
        verdict, detail = classify(_check(completed_at="2026-08-25T11:58:25Z"), MERGE_TS)
        assert verdict == LATE
        assert "43s DEPOIS" in detail

    def test_vermelho_no_head(self) -> None:
        """#1701 (2026-08-25): entrou em main com o required check em failure."""
        assert classify(_check(conclusion="failure"), MERGE_TS)[0] == RED

    def test_pendente_conta_como_vermelho(self) -> None:
        """Check sem conclusão no instante do merge não protegeu nada."""
        assert classify({"name": audit.GATE_CHECK, "conclusion": None}, MERGE_TS)[0] == RED

    def test_check_ausente(self) -> None:
        assert classify(None, MERGE_TS)[0] == ABSENT

    def test_sem_timestamp_nao_inventa_veredito(self) -> None:
        """Sem os dois instantes não há ordem — declarar `gated` seria fabricar."""
        assert classify(_check(completed_at=None), MERGE_TS)[0] == UNKNOWN
        assert classify(_check(), None)[0] == UNKNOWN


class TestVerdictForSha:
    def test_resolve_pr_e_le_check_do_HEAD_nao_do_sha_de_main(self) -> None:
        """O squash cria commit novo: check-runs do SHA de main são sempre vazios,
        e um detector que os lesse diria `absent` para 100% dos merges."""
        run = _fake_gh(
            pulls={"deadbeef": [{"number": 42, "head": {"sha": "head42"}, "merged_at": MERGE_TS}]},
            checks={"head42": [_check()]},
        )
        verdict = verdict_for_sha(run, "deadbeef")
        assert (verdict.pr, verdict.verdict) == (42, GATED)
        assert any("commits/head42/check-runs" in c for c in run.calls)

    def test_sha_sem_pr_associado(self) -> None:
        verdict = verdict_for_sha(_fake_gh(pulls={}, checks={}), "orfao")
        assert verdict.verdict == UNKNOWN and verdict.pr is None

    def test_outro_check_do_head_nao_e_confundido_com_o_gate(self) -> None:
        run = _fake_gh(
            pulls={"s": [{"number": 1, "head": {"sha": "h"}, "merged_at": MERGE_TS}]},
            checks={"h": [{"name": "Lint", "conclusion": "success", "completed_at": MERGE_TS}]},
        )
        assert verdict_for_sha(run, "s").verdict == ABSENT


class TestAuditShas:
    def _run_com(self, conclusion: str, suites: list[dict] | None = None, **kw: Any) -> Any:
        return _fake_gh(
            pulls={"s1": [{"number": 7, "head": {"sha": "h1"}, "merged_at": MERGE_TS}]},
            checks={"h1": [_check(conclusion=conclusion)]},
            suites=suites,
            **kw,
        )

    def test_sha_gateado_nao_vira_linha(self) -> None:
        assert audit_shas(self._run_com("success"), ["s1"]) == ([], None)

    def test_indice_de_bypass_e_preguicoso_no_caminho_feliz(self) -> None:
        """Enriquecer lista vazia custaria até 8 páginas de API por push em main."""
        run = self._run_com("success")
        audit_shas(run, ["s1"])
        assert not any("rule-suites" in c for c in run.calls)

    def test_sha_sem_gate_vira_linha_com_ator_do_bypass(self) -> None:
        suites = [{"result": "bypass", "after_sha": "s1", "actor_name": "davidrobert"}]
        lines, note = audit_shas(self._run_com("failure", suites), ["s1"])
        assert len(lines) == 1 and "davidrobert" in lines[0] and note is None

    def test_sem_gate_e_sem_bypass_ainda_e_reportado(self) -> None:
        """Corrida e outage não deixam rastro em rule-suites — o veredito do SHA
        é o instrumento primário, e o bypass só refina a causa."""
        lines, _ = audit_shas(self._run_com("failure", suites=[]), ["s1"])
        assert len(lines) == 1 and "bypass" not in lines[0]

    def test_rule_suites_inacessivel_declara_a_lacuna_em_vez_de_silenciar(self) -> None:
        """`GITHUB_TOKEN` não tem permissão de administração: a ausência do
        enriquecimento precisa aparecer, senão vira 'nenhum bypass' falso."""
        run = self._run_com("failure", suites_error="HTTP 403: admin required")
        lines, note = audit_shas(run, ["s1"])
        assert len(lines) == 1
        assert note is not None and "403" in note
        assert "403" in audit._issue_body(lines, note)


class TestBypassIndex:
    def test_le_a_janela_certa_e_filtra_so_bypass(self) -> None:
        """O default da API é `time_period=day` — foi assim que uma leitura viu
        2 de 64 bypasses em 2026-08-25 (ADR-415 §D4)."""
        run = _fake_gh(
            pulls={},
            checks={},
            suites=[
                {"result": "bypass", "after_sha": "a", "actor_name": "x"},
                {"result": "pass", "after_sha": "b", "actor_name": "y"},
            ],
        )
        assert audit.bypass_index(run) == {"a": "x"}
        assert any("time_period=week" in c for c in run.calls)

    def test_pagina_cheia_continua_paginando(self) -> None:
        """Página parcial é fim da leitura; página CHEIA obriga a buscar a
        próxima — parar nela perderia bypass silenciosamente."""
        chamadas: list[str] = []
        cheia = [
            {"result": "bypass", "after_sha": f"p1-{i}", "actor_name": "x"}
            for i in range(audit.PAGE_SIZE)
        ]

        def run(args: list[str]) -> str:
            chamadas.append(" ".join(args))
            pagina = int(args[1].split("&page=")[1])
            if pagina == 1:
                return json.dumps(cheia)
            return json.dumps([{"result": "bypass", "after_sha": "p2", "actor_name": "y"}])

        achados = audit.bypass_index(run)
        assert "p2" in achados, "parou na primeira página mesmo ela vindo cheia"
        assert len(achados) == audit.PAGE_SIZE + 1
        assert len(chamadas) == 2, "não parou na página parcial"


class TestIssueBody:
    def test_corpo_declara_o_predicado_temporal(self) -> None:
        body = audit._issue_body(["`abc` (PR #1) — **late**: ..."], None)
        assert "no momento do merge" in body and "não protegeu nada" in body

    def test_verdict_ungated_cobre_as_quatro_classes(self) -> None:
        for veredito in (LATE, RED, ABSENT, UNKNOWN):
            assert MergeVerdict("s", 1, veredito, "").is_ungated
        assert not MergeVerdict("s", 1, GATED, "").is_ungated


def _writes(run: Any) -> list[str]:
    return [c for c in run.calls if c.startswith(("issue create", "issue edit", "issue comment"))]


class TestEfeitoDaIssue:
    """A Issue é a ÚNICA saída do detector em produção, e era invisível à suíte:
    o fake gravava `args[1]` (= "create"), então o guard de dry-run casava
    nada e 5 mutações do lado da escrita sobreviviam."""

    def _ungated(self, existing_issue: bool = False) -> Any:
        return _fake_gh(
            pulls={"s1": [{"number": 7, "head": {"sha": "h1"}, "merged_at": MERGE_TS}]},
            checks={"h1": [_check(conclusion="failure")]},
            suites=[],
            existing_issue=existing_issue,
        )

    def test_sha_sem_gate_escreve_issue(self) -> None:
        run = self._ungated()
        assert audit.main(["--sha", "s1"], run) == 0
        assert len(_writes(run)) == 1

    def test_corpo_da_issue_carrega_a_linha_do_sha(self) -> None:
        run = self._ungated()
        audit.main(["--sha", "s1"], run)
        assert "s1" in _writes(run)[0] and "**red**" in _writes(run)[0]

    def test_issue_criada_com_o_label_que_o_workflow_garante(self) -> None:
        """Afirmar `--label {AUDIT_LABEL}` seria ler a mesma constante dos dois
        lados: renomear a constante passaria (mutação medida sobrevivendo). O
        elo real é o workflow, que CRIA a label — se os dois divergirem, o
        `gh issue create` aborta com 'label not found' no primeiro incidente."""
        workflow = (REPO_ROOT / ".github/workflows/merge-audit.yml").read_text(encoding="utf-8")
        criada = re.search(r"gh label create (\S+)", workflow)
        assert criada is not None, "workflow deixou de garantir a label"
        assert criada.group(1) == audit.AUDIT_LABEL
        run = self._ungated()
        audit.main(["--sha", "s1"], run)
        assert f"--label {criada.group(1)}" in _writes(run)[0]

    def test_sha_gateado_nao_escreve_nada(self) -> None:
        run = _fake_gh(
            pulls={"s1": [{"number": 7, "head": {"sha": "h1"}, "merged_at": MERGE_TS}]},
            checks={"h1": [_check()]},
        )
        assert audit.main(["--sha", "s1"], run) == 0
        assert _writes(run) == []

    def test_segundo_merge_sem_gate_ACRESCENTA_em_vez_de_substituir(self) -> None:
        """`issue edit --body` troca o corpo inteiro: com um merge por dia, o
        registro guardaria só o último — a ADR-415 promete o contrário."""
        run = self._ungated(existing_issue=True)
        audit.main(["--sha", "s1"], run)
        assert _writes(run)[0].startswith("issue comment 99")


class TestSweepNaoAfirmaSemMedir:
    """`rulesets/rule-suites` exige Administration:read, que o GITHUB_TOKEN não
    pode receber — o 403 é o caso esperado, não o excepcional."""

    def test_sem_leitura_nao_imprime_contagem_e_sai_diferente_de_zero(self, capsys: Any) -> None:
        run = _fake_gh(pulls={}, checks={}, suites_error="HTTP 403: not accessible")
        rc = audit.main(["--sweep"], run)
        out = capsys.readouterr()
        assert rc != 0
        assert "0 merge(s)" not in out.out
        assert "NÃO MEDIDO" in out.err

    def test_com_leitura_afirma_a_contagem(self, capsys: Any) -> None:
        run = _fake_gh(pulls={}, checks={}, suites=[])
        assert audit.main(["--sweep"], run) == 0
        assert "0 merge(s)" in capsys.readouterr().out


class TestSweepTambemAcrescenta:
    """O modo `--sha` acrescenta; se o `--sweep` sobrescrevesse, um sweep
    apagaria os merges que o pós-merge registrou entre dois sweeps."""

    def test_sweep_com_issue_existente_acrescenta(self) -> None:
        run = _fake_gh(
            pulls={"s1": [{"number": 7, "head": {"sha": "h1"}, "merged_at": MERGE_TS}]},
            checks={"h1": [_check(conclusion="failure")]},
            suites=[{"result": "bypass", "after_sha": "s1", "actor_name": "x"}],
            existing_issue=True,
        )
        assert audit.main(["--sweep"], run) == 0
        assert _writes(run)[0].startswith("issue comment 99")


class TestTruncagemNaoEZero:
    def test_paginas_cheias_ate_o_teto_viram_erro(self) -> None:
        """Sair pelo teto com páginas cheias é truncagem silenciosa — a mesma
        classe do `time_period=day` que a ADR-415 §D4 denuncia."""
        cheia = [{"result": "pass", "after_sha": f"x{i}", "actor_name": "y"} for i in range(100)]

        def run(args: list[str]) -> str:
            return json.dumps(cheia)

        with pytest.raises(RuntimeError, match="truncada"):
            audit.bypass_index(run)


class TestCheckRunQuery:
    def test_filtra_por_nome_e_pede_pagina_grande(self) -> None:
        """Default é `per_page=30` e um head real traz 20 check-runs: passar de
        30 empurraria o gate para fora da página e daria `absent` falso."""
        run = _fake_gh(
            pulls={"s": [{"number": 1, "head": {"sha": "h"}, "merged_at": MERGE_TS}]},
            checks={"h": [_check()]},
        )
        verdict_for_sha(run, "s")
        chamada = next(c for c in run.calls if "check-runs" in c)
        assert "per_page=100" in chamada and "check_name=" in chamada


@pytest.mark.parametrize("modo", [["--sha", "s1"], ["--sweep"]])
class TestMain:
    def test_nao_escreve_issue_em_dry_run(self, modo: list[str], capsys: Any) -> None:
        run = _fake_gh(pulls={}, checks={}, suites=[])
        audit.main([*modo, "--dry-run"], run)
        assert _writes(run) == []
