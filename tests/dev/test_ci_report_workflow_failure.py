"""Canal de falha dos compensadores agendados (ADR-210 §camada 4, KR-F do
PLAN-ci-trust). Sem rede — `gh` nunca é chamado."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_report_workflow_failure as reporter  # noqa: E402


def _fake_gh(existing: int | None = None) -> Any:
    calls: list[str] = []

    def run(args: list[str]) -> str:
        calls.append(" ".join(args))
        if args[:2] == ["issue", "list"]:
            return json.dumps([{"number": existing}] if existing else [])
        return ""

    run.calls = calls  # type: ignore[attr-defined]
    return run


def _writes(run: Any) -> list[str]:
    return [c for c in run.calls if c.startswith(("issue create", "issue comment"))]


class TestPrimeiraFalha:
    def test_abre_issue_com_a_label_declarada(self) -> None:
        run = _fake_gh()
        assert reporter.main(["--workflow", "stale.yml", "--label", "ops-stale"], run) == 0
        assert len(_writes(run)) == 1
        assert "issue create" in _writes(run)[0]
        assert "--label ops-stale" in _writes(run)[0]

    def test_corpo_nomeia_o_workflow_e_o_modo_de_falha(self) -> None:
        corpo = reporter.first_body("auto-update-prs.yml", "ops-train")
        assert "auto-update-prs.yml" in corpo
        assert "iniciado" in corpo and "10×" in corpo


class TestFalhaSeguinte:
    """A #642 ficou 46 dias mascarando falhas novas porque a trava
    anti-duplicata SILENCIAVA em vez de acumular. Aqui cada falha acrescenta."""

    def test_acrescenta_em_vez_de_silenciar(self) -> None:
        run = _fake_gh(existing=42)
        reporter.main(["--workflow", "stale.yml", "--label", "ops-stale"], run)
        assert _writes(run) == [w for w in _writes(run) if w.startswith("issue comment 42")]
        assert len(_writes(run)) == 1

    def test_nao_abre_segunda_issue_para_a_mesma_label(self) -> None:
        run = _fake_gh(existing=42)
        reporter.main(["--workflow", "stale.yml", "--label", "ops-stale"], run)
        assert not any(w.startswith("issue create") for w in _writes(run))


class TestDryRun:
    def test_nao_escreve_nada(self, capsys: Any) -> None:
        run = _fake_gh()
        reporter.main(["--workflow", "x.yml", "--label", "l", "--dry-run"], run)
        assert _writes(run) == []
        assert "[dry-run]" in capsys.readouterr().out


class TestRunUrl:
    def test_monta_a_url_do_run_quando_no_actions(self, monkeypatch: Any) -> None:
        """Sem a URL, a Issue diz que algo falhou e não onde olhar."""
        for k, v in {
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "o/r",
            "GITHUB_RUN_ID": "99",
        }.items():
            monkeypatch.setenv(k, v)
        assert reporter.run_url() == "https://github.com/o/r/actions/runs/99"

    @pytest.mark.parametrize(
        "faltante", ["GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"]
    )
    def test_fora_do_actions_nao_inventa_url(self, monkeypatch: Any, faltante: str) -> None:
        for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"):
            monkeypatch.setenv(k, "x")
        monkeypatch.delenv(faltante)
        assert reporter.run_url() == ""


class TestLabelGarantida:
    """`gh issue create --label X` aborta se X não existe e o gh não a cria.
    Como este caminho só roda quando o compensador falha, a ausência ficaria
    latente e explodiria no primeiro incidente — precedente `merge-protection`
    no run 32887693308 (ADR-415)."""

    def test_cria_a_label_antes_da_issue(self) -> None:
        run = _fake_gh()
        reporter.main(["--workflow", "stale.yml", "--label", "ops-hygiene"], run)
        idx_label = next(i for i, c in enumerate(run.calls) if c.startswith("label create"))
        idx_issue = next(i for i, c in enumerate(run.calls) if c.startswith("issue create"))
        assert idx_label < idx_issue, "a label precisa existir ANTES do create"
        assert "--force" in run.calls[idx_label], "sem --force o create falha se já existir"

    def test_nao_recria_label_quando_so_comenta(self) -> None:
        """Issue já aberta ⇒ a label existe; a chamada seria desperdício."""
        run = _fake_gh(existing=7)
        reporter.main(["--workflow", "stale.yml", "--label", "ops-hygiene"], run)
        assert not any(c.startswith("label create") for c in run.calls)


class TestManifestoTemProdutor:
    """KR-F: `alerts:` sem step que produza a Issue é entrada DECORATIVA — o
    manifesto afirmaria cobertura que não existe, que é a classe que a
    ADR-210 §camada 4 existe para matar. Fecha a classe, não a instância:
    entrada nova sem produtor reprova sozinha."""

    def _manifesto(self) -> list[dict]:
        import yaml

        return yaml.safe_load((REPO_ROOT / ".github/scheduled-workflows.yml").read_text())[
            "workflows"
        ]

    def test_toda_label_declarada_tem_produtor_no_workflow(self) -> None:
        orfas = []
        for w in self._manifesto():
            wf = REPO_ROOT / ".github/workflows" / w["file"]
            texto = wf.read_text(encoding="utf-8") if wf.exists() else ""
            for alerta in w.get("alerts") or []:
                if alerta["label"] not in texto:
                    orfas.append(f"{w['file']} declara `{alerta['label']}` e nenhum step a produz")
        assert not orfas, "\n".join(orfas)

    def test_toda_entrada_do_manifesto_declara_canal(self) -> None:
        """Era 2 de 9 em 2026-08-21; o KR-F fecha em 9 de 9."""
        sem = [w["file"] for w in self._manifesto() if not (w.get("alerts") or [])]
        assert not sem, f"entradas sem canal de falha: {sem}"
