"""Cobertura direta do stage runner E7 (`pipeline/stages/validate_cross.py`).

E7 é read-only por design (dead code de write desde ADR-199 — ver CLAUDE.md
§Convenções de naming): roda os checks CV sobre o E5 e **não** grava artifact.
Estes testes travam shape do retorno, a propriedade read-only, idempotência e
a falha limpa quando o E5 está ausente ou sem narrativas.
"""

from __future__ import annotations

from pathlib import Path

import scripts.validate_cross as _scripts_validate_cross
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.context import WorkspaceContext
from pipeline.stages import validate_cross

_REQUIRED_CHARTS = (
    "score_gauge",
    "patrimonio_doughnut",
    "alocacao_atual_vs_alvo",
    "fluxo_mensal",
    "receita_bar",
    "receita_despesa_mensal",
    "despesas_doughnut",
)


class WriteRecordingArtifactStore(InMemoryArtifactStore):
    """Fake nomeado que registra cada write — prova que E7 não grava artifact."""

    def __init__(self) -> None:
        super().__init__()
        self.write_calls: list[tuple[str, str]] = []

    def write(self, stage: str, key: str, data: dict, *, document_id=None) -> None:
        self.write_calls.append((stage, key))
        super().write(stage, key, data, document_id=document_id)


def _minimal_e5() -> dict:
    """E5 sintético mínimo que passa os 6 checks always-on (CV9-CV14), zero PII."""
    return {
        "narrativas": {
            "summaries": {f"s{i}": "texto sintético" for i in range(1, 11)},
            "charts": {c: {"context": "ctx", "conclusion": "fim"} for c in _REQUIRED_CHARTS},
        },
        "tarefas": [{"t": "tarefa sintética", "p": "alta"}],
        "diagnostico_comportamental": [{"padrao": "sintético"}],
        "score": {"valor": 0, "classificacao": "Crítico"},
    }


def _seeded_ctx(tmp_path: Path, store: InMemoryArtifactStore) -> WorkspaceContext:
    (tmp_path / "config").mkdir(exist_ok=True)
    return WorkspaceContext(root=tmp_path, artifact_store=store)


def test_stage_run_shape_and_read_only(tmp_path: Path) -> None:
    """`run(ctx)` retorna shape crossval completo e não escreve row nova no store."""
    store = WriteRecordingArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _minimal_e5())
    store.write_calls.clear()  # seed() delega a write(); só interessa o que o E7 fizer
    result = validate_cross.run(_seeded_ctx(tmp_path, store))
    assert result["success"] is True
    assert result["stage"] == "validate_cross"
    assert result["mode"] == "crossval"
    assert result["checks_total"] == 6  # só os always-on; opcionais skipam sem dados
    assert result["checks_failed"] == 0
    assert {r["check_id"] for r in result["results"]} == {f"CV{i}" for i in range(9, 15)}
    assert store.write_calls == [], "E7 é read-only — não pode gravar artifact"


def test_stage_run_is_idempotent(tmp_path: Path) -> None:
    """Segunda execução sobre o mesmo E5 produz resultado idêntico."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", _minimal_e5())
    ctx = _seeded_ctx(tmp_path, store)
    assert validate_cross.run(ctx) == validate_cross.run(ctx)


def test_stage_run_fails_cleanly_without_e5(tmp_path: Path) -> None:
    """E5 ausente → retorno estruturado (não raise), reason `e5_not_found`."""
    result = validate_cross.run(_seeded_ctx(tmp_path, InMemoryArtifactStore()))
    assert result == {"success": False, "reason": "e5_not_found", "stage": "validate_cross"}


def test_stage_run_fails_cleanly_without_narrativas(tmp_path: Path) -> None:
    """E5 sem narrativas (E5.N não rodou) → reason `missing_narrativas`."""
    store = InMemoryArtifactStore()
    store.seed("analyze_finances", "analise_financeira", {"score": {"valor": 0}})
    result = validate_cross.run(_seeded_ctx(tmp_path, store))
    assert result == {"success": False, "reason": "missing_narrativas", "stage": "validate_cross"}


def test_cv16_passa_quando_baldes_dentro_do_total() -> None:
    """ADR-330: pj+clt+aluguel <= receita_total → conservação OK."""
    e5 = {
        "fluxo_caixa": {
            "receita_total": 10000.0,
            "receita_por_natureza": {
                "receita_pj": 7000.0,
                "receita_clt": 3000.0,
                "receita_aluguel": 0.0,
            },
        }
    }
    r = _scripts_validate_cross._cv16_receita_natureza(e5)
    assert r is not None and r.passed


def test_cv16_detecta_dupla_contagem() -> None:
    """Resíduo negativo (baldes > total) = dupla-contagem → error."""
    e5 = {
        "fluxo_caixa": {
            "receita_total": 5000.0,
            "receita_por_natureza": {"receita_pj": 7000.0, "receita_clt": 3000.0},
        }
    }
    r = _scripts_validate_cross._cv16_receita_natureza(e5)
    assert r is not None and not r.passed and r.severity == "error"


def test_cv16_none_sem_bloco() -> None:
    """Payload sem receita_por_natureza (legado) → skip (None)."""
    assert _scripts_validate_cross._cv16_receita_natureza({"fluxo_caixa": {}}) is None


def _passive_income_conservativo() -> dict:
    """Bloco passive_income sintético conservativo (shape de `_passive_income_to_dict`
    pós-A37.l7 PR-2): o dict fecha com o headline (53000 = 12000+30000+3000+8000+0);
    distribuicao PJ (ADR-191) e ganho de capital (ADR-336) vivem em campos irmãos
    explícitos, fora do dict. Fictício, zero PII."""
    return {
        "status": "ok",
        "renda_passiva_anual_brl": 53000.0,
        "renda_passiva_por_fonte_brl": {
            "dividendos": 12000.0,
            "jcp": 30000.0,
            "aplicacoes": 3000.0,
            "exterior": 8000.0,
            "alugueis": 0.0,
        },
        "renda_ativa_pj_excluida_brl": 284000.0,
        "ganho_capital_excluido_brl": 20000.0,
    }


def test_cv17_passa_quando_headline_conserva() -> None:
    """Σ(fontes) == headline (dict auto-conservativo) → OK (severity info)."""
    r = _scripts_validate_cross._cv17_renda_passiva_conservacao(
        {"passive_income": _passive_income_conservativo()}
    )
    assert r is not None and r.passed and r.severity == "info"


def test_cv17_detecta_fonte_vazando_no_headline() -> None:
    """Headline inflado sem contrapartida no dict (53000 → 73000) → error."""
    pi = _passive_income_conservativo()
    pi["renda_passiva_anual_brl"] = 73000.0
    r = _scripts_validate_cross._cv17_renda_passiva_conservacao({"passive_income": pi})
    assert r is not None and not r.passed and r.severity == "error"


def test_cv17_detecta_componente_excluido_de_volta_no_dict() -> None:
    """Regressão DE-04: distribuicao_pj_titular re-injetada no dict (shape antigo,
    ~7,84× o headline) quebra a conservação → error."""
    pi = _passive_income_conservativo()
    pi["renda_passiva_por_fonte_brl"]["distribuicao_pj_titular"] = 284000.0
    r = _scripts_validate_cross._cv17_renda_passiva_conservacao({"passive_income": pi})
    assert r is not None and not r.passed and r.severity == "error"


def test_cv17_tolerancia_zero_um_centavo() -> None:
    """Cents inteiros, tolerância ZERO: 1 centavo de drift já reprova (ADR-090)."""
    pi = _passive_income_conservativo()
    pi["renda_passiva_anual_brl"] = 53000.01
    r = _scripts_validate_cross._cv17_renda_passiva_conservacao({"passive_income": pi})
    assert r is not None and not r.passed


def test_cv17_none_sem_bloco() -> None:
    """Payload sem passive_income (legado) ou sem fontes → skip (None)."""
    assert _scripts_validate_cross._cv17_renda_passiva_conservacao({}) is None
    assert _scripts_validate_cross._cv17_renda_passiva_conservacao({"passive_income": {}}) is None


def test_cv17_registrado_em_run_cross_validation() -> None:
    """CV17 participa do run agregado quando o bloco está presente."""
    e5 = _minimal_e5()
    e5["passive_income"] = _passive_income_conservativo()
    results = _scripts_validate_cross.run_cross_validation(e5)
    assert "CV17" in {r.check_id for r in results}
