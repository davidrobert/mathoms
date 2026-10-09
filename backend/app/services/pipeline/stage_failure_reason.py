"""Reexporta o classificador de não-entrega de `pipeline/stage_failure_reason.py` (ADR-446)."""

# O classificador migrou para o pipeline porque a classe sai do objeto vivo, e a
# exceção do runner só existe dentro de `orchestrator._run_stage`. Este módulo fica
# para os importadores do backend — e é o alvo que `test_stage_degradation`
# monkeypatcha, porque `_execute_stages_loop` resolve `sfr.reason_from_stage_detail`
# aqui na hora da chamada.

from pipeline.stage_failure_reason import (
    StageFailureReason,
    reason_from_exception,
    reason_from_stage_detail,
)

__all__ = ["StageFailureReason", "reason_from_exception", "reason_from_stage_detail"]
