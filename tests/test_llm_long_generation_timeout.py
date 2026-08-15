"""Stages de geração 16k declaram timeout_s=300 (emenda ADR-270 2026-08-15)."""

from pathlib import Path

from pipeline.llm.error_classification import LLM_LONG_GENERATION_TIMEOUT_S

_REPO = Path(__file__).resolve().parents[1]

_LONG_GEN_STAGES = (
    "pipeline/stages/extract_baseline.py",
    "pipeline/stages/extract_members.py",
    "pipeline/stages/extract_irpf_full.py",
    "pipeline/stages/extract_informe_aluguel.py",
    "pipeline/stages/extract_with_llm.py",
)


def test_long_generation_timeout_is_300s() -> None:
    assert LLM_LONG_GENERATION_TIMEOUT_S == 300.0


def test_16k_stages_pass_long_generation_timeout() -> None:
    """Regressão do dogfood 2026-08-15: extract_baseline ficou no default 120s."""
    for rel in _LONG_GEN_STAGES:
        src = (_REPO / rel).read_text(encoding="utf-8")
        assert "timeout_s=LLM_LONG_GENERATION_TIMEOUT_S" in src, (
            f"{rel} deve passar timeout_s=LLM_LONG_GENERATION_TIMEOUT_S "
            "(16k max_tokens; sem isso o cap 120s mata a geração)"
        )
