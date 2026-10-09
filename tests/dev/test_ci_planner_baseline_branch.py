"""Job privilegiado do rebaseline do golden mensal do parecer — a candidata vem de
job NÃO confiável (deps de terceiros + LLM). Sem rede, sem git."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import dev.ci_planner_baseline_branch as branch_job  # noqa: E402

_METRICS = {"p0_count": 1, "riscos_count": 4, "ancora_dominante_riscos": "Perini"}


def _payload(**overrides: object) -> dict:
    base = {"generated_at": "2026-10-01T06:00:00+00:00", "yyyy_mm": "2026-10"}
    return {**base, "metrics": dict(_METRICS), **overrides}


def _b64(obj: object) -> str:
    return base64.b64encode(json.dumps(obj).encode()).decode()


def test_candidata_valida_passa_intacta():
    assert branch_job.decode_candidate(_b64(_payload()), "2026-10") == _payload()


@pytest.mark.parametrize(
    "b64,yyyy_mm,match",
    [
        (_b64(_payload()), "2026-13", "YYYY-MM"),
        (_b64(_payload(yyyy_mm="2026-09")), "2026-10", "yyyy_mm="),
        ("não-é-base64", "2026-10", "base64"),
        ("@@@@", "2026-10", "base64"),
        (_b64({**_payload(), "extra": 1}), "2026-10", "expected keys"),
        (_b64(_payload(metrics={})), "2026-10", "metrics"),
        (_b64(_payload(metrics={"P0": 1})), "2026-10", "snake_case"),
        (_b64(_payload(metrics={"x": 1.5})), "2026-10", "int|null"),
        (_b64(_payload(metrics={"x": True})), "2026-10", "int|null"),
        (_b64(_payload(metrics={"x": "a | b"})), "2026-10", "int|null"),
        (_b64(_payload(metrics={"x": "[pwn](http://x)"})), "2026-10", "int|null"),
        (_b64(_payload(generated_at="`rm`")), "2026-10", "generated_at"),
        (_b64({"pad": "x" * branch_job.MAX_BYTES}), "2026-10", "bytes"),
    ],
)
def test_candidata_fora_do_shape_e_rejeitada(b64, yyyy_mm, match):
    with pytest.raises(ValueError, match=match):
        branch_job.decode_candidate(b64, yyyy_mm)


def test_tabela_marca_o_que_mudou_e_a_semeadura():
    prev = {**_METRICS, "p0_count": 2}
    table = branch_job.metrics_table(prev, _METRICS)
    assert "| `p0_count` | `2` | `1` | sim |" in table
    assert "| `riscos_count` | `4` | `4` | não |" in table
    assert "| `p0_count` | — | `1` | — |" in branch_job.metrics_table(None, _METRICS)


def test_link_de_pr_carrega_titulo_conventional_e_corpo(tmp_path):
    url = branch_job.compare_url(
        "https://github.com", "o/r", "agent/planner-golden-baseline/202610-9-1", "t: x", "a b"
    )
    parts = urlsplit(url)
    assert parts.path == "/o/r/compare/main...agent/planner-golden-baseline/202610-9-1"
    assert parse_qs(parts.query) == {"quick_pull": ["1"], "title": ["t: x"], "body": ["a b"]}
    assert branch_job.pr_title("2026-10").startswith("chore(test): ")


def _run_main(tmp_path: Path, monkeypatch, b64: str) -> int:
    monkeypatch.setenv("BASELINE_B64", b64)
    argv = ["--yyyy-mm", "2026-10", "--branch", "agent/planner-golden-baseline/202610-9-1"]
    argv += ["--repo", "o/r", "--server-url", "https://github.com", "--run-url", "https://run"]
    argv += ["--summary-out", str(tmp_path / "summary.md")]
    return branch_job.main([*argv, "--baseline-dir", str(tmp_path / "golden_baselines")])


def test_main_escreve_so_a_baseline_do_mes_e_compara_com_a_anterior(tmp_path, monkeypatch):
    anterior = branch_job.write_baseline(
        _payload(yyyy_mm="2026-09", metrics={**_METRICS, "p0_count": 2}),
        tmp_path / "golden_baselines",
    )
    assert _run_main(tmp_path, monkeypatch, _b64(_payload())) == 0
    escritos = sorted(p.name for p in anterior.parent.iterdir())
    assert escritos == ["parecer_monthly_2026-09.json", "parecer_monthly_2026-10.json"]
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "`parecer_monthly_2026-09.json`" in summary and "| sim |" in summary


def test_main_rejeita_candidata_sem_escrever_nada(tmp_path, monkeypatch, capsys):
    assert _run_main(tmp_path, monkeypatch, _b64(_payload(yyyy_mm="2026-09"))) == 1
    assert not (tmp_path / "golden_baselines").exists()
    assert not (tmp_path / "summary.md").exists()
    assert "::error::baseline candidata rejeitada" in capsys.readouterr().err
