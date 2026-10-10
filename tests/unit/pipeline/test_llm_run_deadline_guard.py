"""O prazo do run no choke-point LLM: nenhuma tentativa começa ou continua depois dele (ADR-446)."""

# Medido em 2026-10-08: o sinal do soft time limit chega ao `except` do `LLMService`
# embrulhado (`InstructorRetryException → RetryError → InternalServerError →
# AnthropicError → SoftTimeLimitExceeded`, os dois últimos elos só em `__context__`),
# vira `provider_error` e a chamada é refeita. O instructor 1.15.1 retenta qualquer
# exceção por dentro do `create()`, e as threads do pool do E2-llm nunca recebem o sinal.

from __future__ import annotations

import sys
import threading
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from pipeline.llm.litellm_client import LLMConfig, LLMService
from pipeline.llm.run_deadline_guard import guarded_completion
from pipeline.llm.stream_assemble import completion_via_stream
from pipeline.run_deadline import RunDeadline, RunTimeLimitExceededError, is_time_limit
from pipeline.stage_thread_pool import cancelling_thread_pool


class _Out(BaseModel):
    value: str


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class _Hooks:
    """Hooks do run: carregam o prazo e contam o que o `LLMService` pede ao budget."""

    def __init__(self, deadline: RunDeadline) -> None:
        self.run_deadline = deadline
        self.budget_checks = 0

    def check_budget(self) -> None:
        self.budget_checks += 1

    def record_call(self, result, *, stage, prompt_version) -> None:
        pass


@pytest.fixture
def fake_billiard(monkeypatch):
    module = types.ModuleType("billiard.exceptions")

    class SoftTimeLimitExceeded(Exception):
        pass

    module.SoftTimeLimitExceeded = SoftTimeLimitExceeded
    monkeypatch.setitem(sys.modules, "billiard.exceptions", module)
    return SoftTimeLimitExceeded


def _service(hooks: _Hooks, create) -> LLMService:
    svc = LLMService(
        LLMConfig(
            provider="anthropic", api_key="sk-test", model_name="claude-test", call_hooks=hooks
        )
    )
    svc._ensure_client = lambda: None  # type: ignore[method-assign]
    svc._client = MagicMock()
    svc._client.chat.completions.create = create
    return svc


def _expired() -> RunDeadline:
    deadline = RunDeadline.starting_now(60)
    deadline.trip()
    return deadline


def test_chamada_depois_do_prazo_nao_toca_budget_nem_cliente():
    hooks = _Hooks(_expired())
    create = MagicMock()

    with pytest.raises(RunTimeLimitExceededError):
        _service(hooks, create).call(system_prompt="s", user_prompt="u", output_schema=_Out)

    assert hooks.budget_checks == 0 and create.call_count == 0


def test_sinal_embrulhado_no_retry_vira_erro_tipado_sem_retentar(fake_billiard, monkeypatch):
    deadline = RunDeadline.starting_now(60)
    monkeypatch.setattr("pipeline.llm.litellm_client.time.sleep", lambda s: pytest.fail("retentou"))

    def _create(**_kwargs):
        # Como o litellm faz: o sinal fica só no `__context__` do erro do provedor.
        try:
            raise fake_billiard()
        except fake_billiard:
            raise RuntimeError("litellm.InternalServerError: AnthropicException") from None

    create = MagicMock(side_effect=_create)
    with pytest.raises(RunTimeLimitExceededError) as raised:
        _service(_Hooks(deadline), create).call(
            system_prompt="s", user_prompt="u", output_schema=_Out
        )

    assert create.call_count == 1
    assert is_time_limit(raised.value)
    assert deadline.expired(), "quem observou o sinal dispara o prazo para as outras threads"


def test_retentativa_do_instructor_nao_chega_ao_provedor_depois_do_prazo():
    import instructor

    provider = MagicMock()
    client = instructor.from_litellm(guarded_completion(_expired()))

    with patch("litellm.completion", provider), pytest.raises(Exception) as raised:
        client.chat.completions.create(
            model="anthropic/claude-test",
            messages=[{"role": "user", "content": "x"}],
            response_model=_Out,
            max_retries=2,
            timeout=30,
        )

    assert provider.call_count == 0
    assert is_time_limit(raised.value)


def test_read_timeout_e_capado_ao_tempo_restante():
    clock = _Clock()
    deadline = RunDeadline.starting_now(60, clock=clock)
    clock.now += 45
    seen: dict = {}

    def _completion(*_args, **kwargs):
        seen.update(kwargs)
        return iter([])

    with (
        patch("litellm.completion", _completion),
        patch("litellm.stream_chunk_builder", return_value=object()),
    ):
        guarded_completion(deadline)(model="m", messages=[], timeout=300)

    assert seen["timeout"] == pytest.approx(15.0)


class _Stream:
    """Stream sync do litellm: chunks + um `completion_stream` que sabe fechar."""

    def __init__(self, chunks: int, on_chunk) -> None:
        self._chunks = chunks
        self._on_chunk = on_chunk
        self.completion_stream = MagicMock()

    def __iter__(self):
        for i in range(self._chunks):
            self._on_chunk(i)
            yield {"chunk": i}


def test_geracao_em_curso_para_no_chunk_e_fecha_o_stream():
    clock = _Clock()
    deadline = RunDeadline.starting_now(60, clock=clock)
    stream = _Stream(
        10, on_chunk=lambda i: setattr(clock, "now", clock.now + (100 if i == 2 else 0))
    )

    with patch("litellm.completion", return_value=stream), pytest.raises(RunTimeLimitExceededError):
        guarded_completion(deadline)(model="m", messages=[], timeout=300)

    stream.completion_stream.close.assert_called_once()


def test_sem_prazo_a_guarda_e_a_propria_funcao():
    assert guarded_completion(RunDeadline()) is completion_via_stream


def test_pool_cancela_pendentes_no_aborto_e_espera_o_em_voo():
    """O `shutdown` do `with ThreadPoolExecutor` rodava cada pendente antes de a exceção seguir."""
    started, release = threading.Event(), threading.Event()
    ran: list[int] = []

    def _task(i: int) -> None:
        if i == 0:
            started.set()
            release.wait(5)
        ran.append(i)

    with pytest.raises(RuntimeError), cancelling_thread_pool(1) as pool:
        for i in range(4):
            pool.submit(_task, i)
        started.wait(5)
        threading.Timer(0.1, release.set).start()
        raise RuntimeError("soft time limit no as_completed")

    assert ran == [0]


@pytest.fixture
def e2_ctx(tmp_path: Path, monkeypatch):
    """Workspace com 4 documentos para o E2-llm e um worker só: a ordem fica determinística."""
    from tests._llm_stage_fixtures import make_llm_ctx

    monkeypatch.setenv("MATHOMS_E2_LLM_CONCURRENCY", "1")
    monkeypatch.setattr(
        "pipeline.llm.text_extractor.DocumentTextExtractor.is_image", lambda *_a, **_k: False
    )
    docs_dir = tmp_path / "data" / "financial_statements"
    docs_dir.mkdir(parents=True)
    for i in range(4):
        (docs_dir / f"btg_informe_20241{i}-0_original.pdf").write_text("conteudo ficticio")
    return make_llm_ctx(tmp_path)


def _run_e2_llm(ctx, monkeypatch, create):
    """O `extract_with_llm` com o `LLMService.call` real e só o provedor trocado."""
    from pipeline.llm.text_extractor import ReaderOutcome, TextExtraction
    from pipeline.stages.extract_with_llm import run

    def _ensure(self):
        self._client = MagicMock()
        self._client.chat.completions.create = create

    monkeypatch.setattr(LLMService, "_ensure_client", _ensure)
    ok = TextExtraction(ReaderOutcome.ok, text="fake-content")
    with patch("pipeline.llm.text_extractor.DocumentTextExtractor.extract_result", return_value=ok):
        return run(ctx)


def test_e2_llm_documentos_pendentes_nao_chamam_o_provedor_depois_do_prazo(e2_ctx, monkeypatch):
    """Não-inércia: o 1º documento vê o prazo vencer; os pendentes nem chegam ao provedor."""
    from tests._llm_stage_fixtures import make_e2_llm_output

    deadline = RunDeadline.starting_now(60)
    e2_ctx.llm_call_hooks = _Hooks(deadline)
    provider_calls: list[int] = []

    def _create(**_kwargs):
        provider_calls.append(1)
        deadline.trip()
        return make_e2_llm_output()

    result = _run_e2_llm(e2_ctx, monkeypatch, _create)

    assert provider_calls == [1]
    assert result["success"] is False and len(result["errors"]) == 3


def test_e2_llm_sinal_no_as_completed_cancela_os_documentos_pendentes(
    e2_ctx, monkeypatch, fake_billiard
):
    """O sinal estoura na thread principal: o `with` do pool não pode processar a fila inteira."""
    from pipeline.stages import extract_with_llm
    from tests._llm_stage_fixtures import make_e2_llm_output

    provider_calls: list[int] = []
    release = threading.Event()

    def _create(**_kwargs):
        provider_calls.append(1)
        if len(provider_calls) > 1:
            release.wait(5)  # o 2º pode já estar em voo quando o sinal chega
        return make_e2_llm_output()

    def _signal_on_first_result(_progress):
        threading.Timer(0.1, release.set).start()
        raise fake_billiard()

    monkeypatch.setattr(extract_with_llm._E2LLMProgress, "increment", _signal_on_first_result)
    with pytest.raises(fake_billiard):
        _run_e2_llm(e2_ctx, monkeypatch, _create)

    assert len(provider_calls) <= 2, "documento que não começou não pode chegar ao provedor"


def test_write_na_thread_principal_relanca_o_fim_de_prazo_em_vez_de_virar_erro(fake_billiard):
    """`_persist_e2_llm_write` roda no laço do `as_completed`: engolir o sinal ali drenava a fila."""
    from pipeline.stages.extract_with_llm import (
        _E2LLMPendingWrite,
        _E2LLMProgress,
        _persist_e2_llm_write,
    )

    class _StoreSignaled:
        def write(self, *_args) -> None:
            raise fake_billiard()

    entry = {"file": "doc.pdf", "transactions": 0, "investments": 0, "confidence": 1.0}
    pending = _E2LLMPendingWrite(key="doc", payload={}, processed=entry)

    with pytest.raises(fake_billiard):
        _persist_e2_llm_write(_StoreSignaled(), pending, _E2LLMProgress(total=1, run_id=None))
