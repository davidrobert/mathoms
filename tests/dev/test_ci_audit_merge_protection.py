"""Auditoria da proteção de main (ADR-415 · ADR-448): o SHA que entrou foi
gateado, e cada incidente vira UMA issue. Casos ancorados em merges reais de
2026-08-25 e 2026-10-09. Sem rede — `gh` nunca é chamado."""

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
import dev.merge_incident_issues as incidents  # noqa: E402
from dev.ci_audit_merge_protection import (  # noqa: E402
    ABSENT,
    GATED,
    LATE,
    RED,
    UNKNOWN,
    BypassRecord,
    MergeVerdict,
    audit_shas,
    classify,
    verdict_for_sha,
)
from tests.dev._merge_audit_fake_gh import (  # noqa: E402
    DEPOIS_DA_448,
    MERGE_TS,
    NOW,
    FakeGh,
    check,
    incident,
)

SHA = "s1" + "0" * 38


def _pull(number: int = 7, head: str = "h1") -> list[dict]:
    return [{"number": number, "head": {"sha": head}, "merged_at": MERGE_TS}]


def _gh(conclusion: str = "failure", **tables: Any) -> FakeGh:
    """Um SHA de main (`SHA`, PR #7, head `h1`) com o gate no estado pedido."""
    return FakeGh(pulls={SHA: _pull()}, checks={"h1": [check(conclusion)]}, **tables)


def _bypass(sha: str = SHA, pushed_at: str = DEPOIS_DA_448, actor: str = "davidrobert") -> dict:
    return {
        "result": "bypass",
        "after_sha": sha,
        "actor_name": actor,
        "id": 123,
        "pushed_at": pushed_at,
    }


def _creates(run: FakeGh) -> list[str]:
    return [c for c in run.writes if c.startswith("issue create")]


class TestClassify:
    """O predicado é o veredito NO MOMENTO DO MERGE. Ler só `conclusion` deixa
    passar o caso mais traiçoeiro: verde que chegou depois do merge."""

    def test_verde_antes_do_merge_gateia(self) -> None:
        assert classify(check(), MERGE_TS)[0] == GATED

    def test_verde_depois_do_merge_nao_gateia(self) -> None:
        """#1699 (2026-08-25): `All checks green` = success 43s APÓS o merge."""
        verdict, detail = classify(check(completed_at="2026-08-25T11:58:25Z"), MERGE_TS)
        assert verdict == LATE
        assert "43s DEPOIS" in detail

    def test_vermelho_no_head(self) -> None:
        """#1701 (2026-08-25): entrou em main com o required check em failure."""
        assert classify(check(conclusion="failure"), MERGE_TS)[0] == RED

    def test_pendente_conta_como_vermelho(self) -> None:
        """Check sem conclusão no instante do merge não protegeu nada."""
        assert classify({"name": audit.GATE_CHECK, "conclusion": None}, MERGE_TS)[0] == RED

    def test_check_ausente(self) -> None:
        assert classify(None, MERGE_TS)[0] == ABSENT

    def test_sem_timestamp_nao_inventa_veredito(self) -> None:
        """Sem os dois instantes não há ordem — declarar `gated` seria fabricar."""
        assert classify(check(completed_at=None), MERGE_TS)[0] == UNKNOWN
        assert classify(check(), None)[0] == UNKNOWN

    def test_verdict_ungated_cobre_as_quatro_classes(self) -> None:
        for veredito in (LATE, RED, ABSENT, UNKNOWN):
            assert MergeVerdict("s", 1, veredito, "").is_ungated
        assert not MergeVerdict("s", 1, GATED, "").is_ungated


class TestVerdictForSha:
    def test_resolve_pr_e_le_check_do_HEAD_nao_do_sha_de_main(self) -> None:
        """O squash cria commit novo: check-runs do SHA de main são sempre vazios,
        e um detector que os lesse diria `absent` para 100% dos merges."""
        run = FakeGh(pulls={"deadbeef": _pull(42, "head42")}, checks={"head42": [check()]})
        verdict = verdict_for_sha(run, "deadbeef")
        assert (verdict.pr, verdict.verdict) == (42, GATED)
        assert any("commits/head42/check-runs" in c for c in run.calls)

    def test_sha_sem_pr_associado(self) -> None:
        verdict = verdict_for_sha(FakeGh(), "orfao")
        assert verdict.verdict == UNKNOWN and verdict.pr is None

    def test_outro_check_do_head_nao_e_confundido_com_o_gate(self) -> None:
        lint = {"name": "Lint", "conclusion": "success", "completed_at": MERGE_TS}
        run = FakeGh(pulls={"s": _pull(1, "h")}, checks={"h": [lint]})
        assert verdict_for_sha(run, "s").verdict == ABSENT

    def test_filtra_por_nome_e_pede_pagina_grande(self) -> None:
        """Default é `per_page=30` e um head real traz 20 check-runs: passar de
        30 empurraria o gate para fora da página e daria `absent` falso."""
        run = _gh("success")
        verdict_for_sha(run, SHA)
        chamada = next(c for c in run.calls if "check-runs" in c)
        assert "per_page=100" in chamada and "check_name=" in chamada


class TestAuditShas:
    """Modo `--backfill`: só imprime, nunca escreve."""

    def test_sha_gateado_nao_vira_linha(self) -> None:
        assert audit_shas(_gh("success"), [SHA]) == ([], None)

    def test_indice_de_bypass_e_preguicoso_no_caminho_feliz(self) -> None:
        """Enriquecer lista vazia custaria até 8 páginas de API por push em main."""
        run = _gh("success")
        audit_shas(run, [SHA])
        assert not any("rule-suites" in c for c in run.calls)

    def test_sha_sem_gate_vira_linha_com_ator_do_bypass(self) -> None:
        lines, note = audit_shas(_gh(suites=[_bypass()]), [SHA])
        assert len(lines) == 1 and "davidrobert" in lines[0] and note is None

    def test_sem_gate_e_sem_bypass_ainda_e_reportado(self) -> None:
        """Corrida e outage não deixam rastro em rule-suites — o veredito do SHA
        é o instrumento primário, e o bypass só refina a causa."""
        lines, _ = audit_shas(_gh(), [SHA])
        assert len(lines) == 1 and "bypass" not in lines[0]


class TestBypassIndex:
    def test_le_a_janela_certa_e_filtra_so_bypass(self) -> None:
        """O default da API é `time_period=day` — foi assim que uma leitura viu
        2 de 64 bypasses em 2026-08-25 (ADR-415 §D4)."""
        passe = {"result": "pass", "after_sha": "b", "actor_name": "y"}
        run = FakeGh(suites=[_bypass("a", actor="x"), passe])
        assert audit.bypass_index(run) == {"a": BypassRecord("x", 123, audit._ts(DEPOIS_DA_448))}
        assert any("time_period=week" in c for c in run.calls)

    def test_filtra_no_servidor_por_resultado_e_ref(self) -> None:
        """Sem o filtro, `--period month` lê toda avaliação de main (93 num dia de
        2026-10-09, 24 delas bypass) e chega perto do teto de 8 páginas."""
        run = FakeGh()
        audit.bypass_index(run, "month")
        chamada = next(c for c in run.calls if "rule-suites" in c)
        assert "rule_suite_result=bypass" in chamada and "ref=refs/heads/main" in chamada

    def test_pagina_cheia_continua_paginando(self) -> None:
        """Página parcial é fim da leitura; página CHEIA obriga a buscar a
        próxima — parar nela perderia bypass silenciosamente."""
        cheia = [_bypass(f"p1-{i}", actor="x") for i in range(audit.PAGE_SIZE)]
        run = FakeGh(suites=[*cheia, _bypass("p2", actor="y")])
        achados = audit.bypass_index(run)
        assert "p2" in achados, "parou na primeira página mesmo ela vindo cheia"
        assert len(achados) == audit.PAGE_SIZE + 1
        assert len([c for c in run.calls if "rule-suites" in c]) == 2

    def test_paginas_cheias_ate_o_teto_viram_erro(self) -> None:
        """Sair pelo teto com páginas cheias é truncagem silenciosa — a mesma
        classe do `time_period=day` que a ADR-415 §D4 denuncia."""
        cheia = [{"result": "pass", "after_sha": f"x{i}"} for i in range(100)]

        def run(args: list[str]) -> str:
            return json.dumps(cheia)

        with pytest.raises(RuntimeError, match="truncada"):
            audit.bypass_index(run)


class TestUmaIssuePorIncidente:
    """ADR-448: a #1728 acumulou 56 comentários e ninguém reagiu. Cada SHA de
    main fora do gate abre a SUA issue, com o SHA curto e o PR no título."""

    def test_sha_sem_gate_abre_issue_propria(self) -> None:
        run = _gh()
        assert audit.main(["--sha", SHA], run) == 0
        assert len(_creates(run)) == 1
        assert "CI: s1000000 (PR #7) entrou em main sem gate — red" in _creates(run)[0]

    def test_corpo_carrega_o_marcador_do_sha_completo_e_o_veredito(self) -> None:
        run = _gh()
        audit.main(["--sha", SHA], run)
        corpo = _creates(run)[0]
        assert f"<!-- merge-audit:sha={SHA} -->" in corpo and "**red**" in corpo

    def test_segundo_sha_sem_gate_abre_OUTRA_issue_em_vez_de_comentar(self) -> None:
        """O formato antigo comentava na issue única; o novo nunca comenta."""
        run = _gh(issues=[incident("sha=" + "f" * 40)])
        audit.main(["--sha", SHA], run)
        assert len(_creates(run)) == 1
        assert not any(c.startswith("issue comment") for c in run.calls)

    def test_mesmo_sha_nao_duplica_no_rerun(self) -> None:
        run = _gh(issues=[incident(f"sha={SHA}")])
        audit.main(["--sha", SHA], run)
        assert run.writes == []

    def test_issue_fechada_conta_como_registrada(self) -> None:
        """SHA mergeado é passado imutável: triado e fechado, não volta."""
        run = _gh(issues=[incident(f"sha={SHA}", state="closed")])
        audit.main(["--sha", SHA], run)
        assert run.writes == []

    def test_sha_gateado_nao_le_registro_nem_escreve(self) -> None:
        """Caminho feliz de todo push em main: custo de API inalterado."""
        run = _gh("success")
        assert audit.main(["--sha", SHA], run) == 0
        assert run.writes == [] and not any("/issues?" in c for c in run.calls)

    def test_corpo_traz_ator_do_rule_suite_quando_legivel(self) -> None:
        run = _gh(suites=[_bypass()])
        audit.main(["--sha", SHA], run)
        assert "`bypass` por `davidrobert` (rule-suite 123)" in _creates(run)[0]

    def test_rule_suites_inacessivel_declara_a_lacuna_na_issue(self) -> None:
        """`GITHUB_TOKEN` não tem permissão de administração: a ausência do
        enriquecimento aparece, senão vira 'nenhum bypass' falso."""
        run = _gh(suites_error="HTTP 403: admin required")
        audit.main(["--sha", SHA], run)
        assert "não lido — HTTP 403" in _creates(run)[0]

    def test_merged_by_entra_rotulado_como_tal(self) -> None:
        """Legível sem admin; rotulado para não se passar por ator do bypass."""
        run = _gh(merged_by={7: "fulano"})
        audit.main(["--sha", SHA], run)
        assert "mergeado por `fulano` (`merged_by` do PR)" in _creates(run)[0]

    def test_issue_criada_com_o_label_que_o_workflow_garante(self) -> None:
        """Afirmar `--label {AUDIT_LABEL}` seria ler a mesma constante dos dois
        lados: renomear a constante passaria. O elo real é o workflow, que CRIA
        a label — se divergirem, o `gh issue create` aborta no 1º incidente."""
        workflow = (REPO_ROOT / ".github/workflows/merge-audit.yml").read_text(encoding="utf-8")
        criadas = set(re.findall(r"gh label create (\S+)", workflow))
        assert criadas == {audit.AUDIT_LABEL}, "workflow deixou de garantir a label"
        run = _gh()
        audit.main(["--sha", SHA], run)
        assert f"--label {audit.AUDIT_LABEL}" in _creates(run)[0]


class TestRegistro:
    """A idempotência vale o que vale a leitura do registro."""

    def test_le_a_listagem_rest_e_nunca_a_search_api(self) -> None:
        """`gh issue list --label` usa a search API (medido no gh 2.102), que
        indexa com atraso: um sweep logo após o push duplicaria a issue."""
        run = _gh(issues=[incident(f"sha={SHA}")])
        audit.main(["--sha", SHA], run)
        leitura = [c for c in run.calls if "/issues?" in c]
        assert leitura and "state=all" in leitura[0] and "labels=merge-protection" in leitura[0]
        assert not any(c.startswith("issue list") or "search" in c for c in run.calls)

    def test_pagina_cheia_continua_lendo(self) -> None:
        outros = [incident(f"sha={i:040d}", number=i) for i in range(incidents.PAGE_SIZE)]
        run = _gh(issues=[*outros, incident(f"sha={SHA}")])
        audit.main(["--sha", SHA], run)
        assert run.writes == [], "parou na página 1 e duplicou a issue da página 2"

    def test_teto_de_paginas_cheias_vira_erro(self) -> None:
        cheia = [incident(f"sha={i:040d}", number=i) for i in range(100)]

        def run(args: list[str]) -> str:
            return json.dumps(cheia)

        with pytest.raises(RuntimeError, match="truncada"):
            incidents.registry(run)


class TestSweepAbreIncidentes:
    def test_bypass_com_veredito_gated_vira_incidente(self) -> None:
        """#2163 (2026-10-09): verde no head ~1h antes, base desatualizada sob
        `strict` — rule-suite `bypass`, e o lock entrou violando o piso do
        `cryptography`. `gated` no head não é "o que entrou foi testado"."""
        run = _gh("success", suites=[_bypass()])
        assert audit.main(["--sweep"], run, NOW) == 0
        assert "entrou em main por bypass do Ruleset" in _creates(run)[0]

    def test_bypass_anterior_a_adr448_nao_reabre_a_rajada(self, capsys: Any) -> None:
        """Os 24 de 2026-10-09 têm registro legado (#1728): virariam 24 issues."""
        run = _gh(suites=[_bypass(pushed_at="2026-10-09T13:55:25Z")])
        audit.main(["--sweep"], run, NOW)
        assert run.writes == [] and "(1 anteriores à ADR-448)" in capsys.readouterr().out

    def test_sweep_nao_duplica_sha_ja_registrado(self) -> None:
        run = _gh(suites=[_bypass()], issues=[incident(f"sha={SHA}", state="closed")])
        audit.main(["--sweep"], run, NOW)
        assert run.writes == []


class TestSweepNaoAfirmaSemMedir:
    """`rulesets/rule-suites` exige Administration:read, que o GITHUB_TOKEN não
    pode receber — o 403 é o caso esperado, não o excepcional."""

    def test_sem_leitura_nao_imprime_contagem_e_sai_diferente_de_zero(self, capsys: Any) -> None:
        run = FakeGh(suites_error="HTTP 403: not accessible")
        rc = audit.main(["--sweep"], run, NOW)
        out = capsys.readouterr()
        assert rc != 0
        assert "0 merge(s)" not in out.out
        assert "NÃO MEDIDO" in out.err

    def test_com_leitura_afirma_a_contagem(self, capsys: Any) -> None:
        assert audit.main(["--sweep"], FakeGh(), NOW) == 0
        assert "0 merge(s)" in capsys.readouterr().out


@pytest.mark.parametrize("modo", [["--sha", SHA], ["--sweep"], ["--ruleset"]])
class TestDryRun:
    def test_nao_escreve_issue_em_dry_run(self, modo: list[str]) -> None:
        run = _gh(suites=[_bypass()])
        audit.main([*modo, "--dry-run"], run, NOW)
        assert run.writes == []
