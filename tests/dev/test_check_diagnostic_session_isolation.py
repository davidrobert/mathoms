"""CTO-6 · ADR-404 — testes do gate ``dev/check_diagnostic_session_isolation.py``.

O gate tem de FALHAR na forma pré-fix e PASSAR na pós-fix. Fonte sintética
espelha as duas, e o scan real de `backend/app` fecha o repo de hoje.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _REPO_ROOT / "dev" / "check_diagnostic_session_isolation.py"
_SPEC = importlib.util.spec_from_file_location("check_diagnostic_session_isolation", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def _check(src: str) -> list[str]:
    return gate.violations_in_source(src, "sintetico.py")


_PRE_FIX = """
def _new_review_reason_row(payload, *, run_id):
    return ReviewReason(pipeline_run_id=run_id, code=payload["code"])


def _materialize_review_reasons(db, *, run_id, reasons):
    for payload in reasons:
        db.add(_new_review_reason_row(payload, run_id=run_id))


def _record_stage_needs_review(run_id, stage_name, reasons):
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.needs_review
        run.paused_at_stage = stage_name
        _materialize_review_reasons(db, run_id=run_id, reasons=reasons)
        db.commit()
"""

_POS_FIX = """
def _new_review_reason_row(payload, *, run_id):
    return ReviewReason(pipeline_run_id=run_id, code=payload["code"])


def _materialize_review_reasons(db, *, run_id, reasons):
    for payload in reasons:
        db.add(_new_review_reason_row(payload, run_id=run_id))


def _commit_pause(run_id, stage_name):
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.needs_review
        run.paused_at_stage = stage_name
        db.commit()


def _materialize_isolated(run_id, reasons):
    try:
        with SyncSessionLocal() as db:
            _materialize_review_reasons(db, run_id=run_id, reasons=reasons)
            db.commit()
    except Exception:
        logger.exception("diagnostico perdido, run segue")


def _record_stage_needs_review(run_id, stage_name, reasons):
    _commit_pause(run_id, stage_name)
    _materialize_isolated(run_id, reasons)
"""


class TestPolaridade:
    def test_forma_pre_fix_e_violacao(self):
        assert len(_check(_PRE_FIX)) == 1

    def test_forma_pos_fix_esta_limpa(self):
        assert _check(_POS_FIX) == []


class TestFechaClasseNaoSintaxe:
    def test_escrita_extraida_para_helper_ainda_e_pega(self):
        """Fecho transitivo de 3 níveis — indireção é como o gate ingênuo cega."""
        src = _PRE_FIX.replace(
            "_materialize_review_reasons(db, run_id=run_id, reasons=reasons)",
            "_wrap(db, run_id, reasons)",
        ).replace(
            "def _record_stage_needs_review",
            "def _wrap(db, run_id, reasons):\n"
            "    _materialize_review_reasons(db, run_id=run_id, reasons=reasons)\n\n\n"
            "def _record_stage_needs_review",
        )
        assert len(_check(src)) == 1

    def test_sessao_por_atribuicao_tambem_conta(self):
        src = """
def _new_row(run_id):
    return ReviewReason(pipeline_run_id=run_id)


def _both(run_id):
    db = SyncSessionLocal()
    run = db.get(PipelineRun, run_id)
    run.status = PipelineRunStatus.needs_review
    db.add(_new_row(run_id))
    db.commit()
"""
        assert len(_check(src)) == 1

    def test_transicao_por_helper_tambem_conta(self):
        src = """
def _pausa(run, stage):
    run.status = PipelineRunStatus.needs_review
    run.paused_at_stage = stage


def _grava(db, run_id):
    db.add(ReviewReason(pipeline_run_id=run_id))


def _both(run_id, stage):
    with SyncSessionLocal() as db:
        _pausa(db.get(PipelineRun, run_id), stage)
        _grava(db, run_id)
        db.commit()
"""
        assert len(_check(src)) == 1


class TestSemFalsoPositivo:
    def test_transicao_sozinha_passa(self):
        src = """
def _finalize(run_id):
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.completed
        db.commit()
"""
        assert _check(src) == []

    def test_diagnostico_sozinho_passa(self):
        src = """
def _diag(run_id):
    with SyncSessionLocal() as db:
        db.add(ReviewReason(pipeline_run_id=run_id))
        db.commit()
"""
        assert _check(src) == []

    def test_status_de_stage_log_nao_e_transicao_de_run(self):
        """`PipelineStageStatus` no RHS não é transição de run — sem esta guarda
        o gate acusaria todo `_record_stage_*`."""
        src = """
def _stage(run_id, log_id):
    with SyncSessionLocal() as db:
        log = db.get(PipelineStageLog, log_id)
        log.status = PipelineStageStatus.needs_review
        db.add(ReviewReason(pipeline_run_id=run_id))
        db.commit()
"""
        assert _check(src) == []

    def test_stage_review_convive_com_a_transicao(self):
        """Decisão explícita da ADR-404: `StageReview` é contrato de pausa —
        `resume_run` exige zero reviews `pending` —, não diagnóstico."""
        src = """
def _pause(run_id, stage):
    with SyncSessionLocal() as db:
        run = db.get(PipelineRun, run_id)
        run.status = PipelineRunStatus.needs_review
        run.paused_at_stage = stage
        db.add(StageReview(pipeline_run_id=run_id, stage=stage))
        db.commit()
"""
        assert _check(src) == []


class TestRepoReal:
    def test_backend_app_esta_limpo(self):
        assert gate.collect_violations() == []


def _boundary(src: str, path: str) -> list[str]:
    return gate.boundary_violations(src, path)


_SINK = "backend/app/services/diagnostics/review_reason_sink.py"
_FORA = "backend/app/tasks/pipeline_task.py"


class TestBoundaryDoSink:
    def test_construir_o_model_fora_do_sink_e_violacao(self):
        src = "from backend.app.models.review_reason import ReviewReason\n\n\ndef f(db):\n    db.add(ReviewReason(code='x'))\n"
        assert len(_boundary(src, _FORA)) == 1

    def test_dentro_do_sink_e_permitido(self):
        src = "from backend.app.models.review_reason import ReviewReason\n\n\ndef _f(db):\n    db.add(ReviewReason(code='x'))\n"
        assert _boundary(src, _SINK) == []

    def test_dataclass_do_dominio_nao_e_o_model(self):
        """`ReviewReason` é os DOIS: model do backend e dataclass do domínio.
        Sem desambiguar pelo import, o gate acusaria 11 produtores legítimos."""
        src = "from pipeline.domain.review_reason import ReviewReason\n\n\ndef f():\n    return ReviewReason(code='x')\n"
        assert _boundary(src, "pipeline/domain/services/anachronic_guard.py") == []

    def test_api_publica_do_sink_nao_aceita_session(self):
        src = "def record_review_reasons(db, *, run_id):\n    pass\n"
        assert len(_boundary(src, _SINK)) == 1

    def test_helper_privado_do_sink_pode_receber_session(self):
        """O sink abre a sessão e a passa aos próprios helpers — é o ponto."""
        src = "def _materialize(db, *, run_id):\n    pass\n"
        assert _boundary(src, _SINK) == []

    def test_session_por_anotacao_tambem_conta(self):
        src = "def record(conn: Session, *, run_id):\n    pass\n"
        assert len(_boundary(src, _SINK)) == 1


class TestTracebackNaoVazaPII:
    def test_logger_exception_no_sink_e_violacao(self):
        src = "def _f():\n    try:\n        pass\n    except Exception:\n        logger.exception('x')\n"
        assert len(_boundary(src, _SINK)) == 1

    def test_exc_info_true_e_violacao(self):
        src = "def _f():\n    logger.error('x', exc_info=True)\n"
        assert len(_boundary(src, _SINK)) == 1

    def test_exc_info_false_passa(self):
        src = "def _f():\n    logger.error('x', exc_info=False)\n"
        assert _boundary(src, _SINK) == []

    def test_fora_do_sink_nao_e_medido(self):
        """A regra é do sink: o resto do backend loga traceback legitimamente."""
        src = "def f():\n    logger.exception('x')\n"
        assert _boundary(src, _FORA) == []
