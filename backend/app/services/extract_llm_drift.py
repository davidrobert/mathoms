"""Drift-check estrutural do ``extract_with_llm`` — corpo do job nightly (A33.l5 · ADR-307 F2).

Reusa o prompt/schema REAIS do stage (``pipeline/llm/prompts/e2_llm.py`` +
``LLMExtractOutput``) — drift de provider aparece aqui antes de quebrar
documento real. O client LLM é injetado (fake em CI, ``LLMService`` real no
Celery); este módulo nunca resolve API key.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, Sequence

from backend.app.services.extract_llm_drift_fixtures import (
    EXTRACT_LLM_DRIFT_FIXTURES,
    DriftFixture,
    StructuralExpectation,
)
from pipeline.llm.call_hooks import LLMBudgetExceededError
from pipeline.llm.institution_catalog import CATALOG_UNAVAILABLE_BLOCK
from pipeline.llm.prompts.e2_llm import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from pipeline.llm.schemas.e2_llm_extract import LLMExtractOutput

#: Stage constante em ``llm_call_log`` — distingue o trial nightly da
#: extração real e mantém cardinalidade baixa (ADR-260).
DRIFT_STAGE = "extract_llm_drift"

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StructuredLLMClient(Protocol):
    """Subconjunto de ``LLMService`` usado pelo drift-check (fake-able)."""

    def call(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class FixtureDriftResult:
    """Pass/fail estrutural de 1 fixture em 1 execução."""

    fixture_id: str
    passed: bool
    failures: tuple[str, ...]
    duration_ms: int = 0


def evaluate_structural(output: LLMExtractOutput, expect: StructuralExpectation) -> list[str]:
    """Falhas estruturais (vazio = pass) — shape/campos/contagem, não bit-exact."""
    failures = _check_identity(output, expect)
    failures.extend(_check_counts(output, expect))
    failures.extend(_check_date_shapes(output))
    return failures


def _check_identity(output: LLMExtractOutput, expect: StructuralExpectation) -> list[str]:
    failures: list[str] = []
    institution = (output.institution or "").strip()
    if not institution:
        failures.append("institution: expected non-empty canonical code, got ''")
    elif expect.institution is not None and institution != expect.institution:
        failures.append(f"institution: expected {expect.institution!r}, got {institution!r}")
    if output.currency != expect.currency:
        failures.append(f"currency: expected {expect.currency!r}, got {output.currency!r}")
    return failures


def _check_counts(output: LLMExtractOutput, expect: StructuralExpectation) -> list[str]:
    failures: list[str] = []
    n_tx = len(output.transactions)
    if n_tx < expect.min_transactions:
        failures.append(f"transactions: expected >= {expect.min_transactions}, got {n_tx}")
    if expect.max_transactions is not None and n_tx > expect.max_transactions:
        failures.append(f"transactions: expected <= {expect.max_transactions}, got {n_tx}")
    n_inv = len(output.investments)
    if n_inv < expect.min_investments:
        failures.append(f"investments: expected >= {expect.min_investments}, got {n_inv}")
    return failures


def _check_date_shapes(output: LLMExtractOutput) -> list[str]:
    failures: list[str] = []
    for i, tx in enumerate(output.transactions):
        if not _ISO_DATE_RE.match(tx.date or ""):
            failures.append(f"transactions[{i}].date: expected YYYY-MM-DD, got {tx.date!r}")
    for i, inv in enumerate(output.investments):
        failures.extend(_check_investment_dates(inv, i))
    return failures


def _check_investment_dates(inv: Any, index: int) -> list[str]:
    failures: list[str] = []
    for field_name in ("applied_date", "maturity_date"):
        value = getattr(inv, field_name)
        if value is not None and not _ISO_DATE_RE.match(value):
            failures.append(
                f"investments[{index}].{field_name}: expected YYYY-MM-DD or null, got {value!r}"
            )
    return failures


def run_extract_llm_drift(
    llm_client: StructuredLLMClient,
    fixtures: Sequence[DriftFixture] = EXTRACT_LLM_DRIFT_FIXTURES,
) -> list[FixtureDriftResult]:
    """1 trial por fixture; exceção vira fail e budget hard-stop curto-circuita."""
    results: list[FixtureDriftResult] = []
    budget_blocked = False
    for fixture in fixtures:
        result, budget_blocked = _drift_one_fixture(llm_client, fixture, budget_blocked)
        results.append(result)
    return results


def _drift_one_fixture(
    llm_client: StructuredLLMClient, fixture: DriftFixture, budget_blocked: bool
) -> tuple[FixtureDriftResult, bool]:
    """(resultado, budget_blocked) — hard-stop ADR-173 pula os trials restantes."""
    if budget_blocked:
        return _failed(fixture, "budget_exceeded: hard-stop ADR-173 pré-call"), True
    try:
        result = _call_one(llm_client, fixture)
    except LLMBudgetExceededError as exc:
        return _failed(fixture, f"budget_exceeded: {str(exc)[:200]}"), True
    except Exception as exc:  # noqa: BLE001 — 1 fixture nunca derruba o batch
        message = f"llm_call_failed: {type(exc).__name__}: {str(exc)[:200]}"
        return _failed(fixture, message), False
    return _evaluated(fixture, result), False


def _evaluated(fixture: DriftFixture, result: Any) -> FixtureDriftResult:
    failures = evaluate_structural(result.output, fixture.expect)
    return FixtureDriftResult(
        fixture_id=fixture.fixture_id,
        passed=not failures,
        failures=tuple(failures),
        duration_ms=int(getattr(result, "duration_ms", 0) or 0),
    )


def _call_one(llm_client: StructuredLLMClient, fixture: DriftFixture) -> Any:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        filename=fixture.filename,
        doc_type="unknown",
        institution="unknown",
        # A33.l8: eval de drift é sintético/determinístico — usa o fallback
        # documentado em vez do catálogo em DB (paridade entre runs).
        institution_catalog=CATALOG_UNAVAILABLE_BLOCK,
        document_text=fixture.document_text,
    )
    return llm_client.call(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        output_schema=LLMExtractOutput,
        max_retries=2,
        max_tokens=4096,
        stage=DRIFT_STAGE,
        prompt_version=PROMPT_VERSION,
    )


def _failed(fixture: DriftFixture, message: str) -> FixtureDriftResult:
    return FixtureDriftResult(fixture_id=fixture.fixture_id, passed=False, failures=(message,))


def persist_drift_results(
    results: Sequence[FixtureDriftResult],
    *,
    model_name: str,
    batch_id: Optional[str] = None,
    session_factory: Optional[Callable[[], Any]] = None,
) -> str:
    """Grava 1 row por fixture em ``llm_drift_check``; retorna o ``batch_id``."""
    resolved_batch_id = batch_id or str(uuid.uuid4())
    session = (session_factory or _default_session_factory())()
    try:
        for result in results:
            session.add(_drift_row(result, batch_id=resolved_batch_id, model_name=model_name))
        session.commit()
    finally:
        session.close()
    return resolved_batch_id


def _default_session_factory() -> Callable[[], Any]:
    from backend.app.core.database import SyncSessionLocal

    return SyncSessionLocal


def _drift_row(result: FixtureDriftResult, *, batch_id: str, model_name: str) -> Any:
    from backend.app.models.llm_drift_check import LLMDriftCheck

    return LLMDriftCheck(
        batch_id=batch_id,
        stage=DRIFT_STAGE,
        fixture_id=result.fixture_id,
        prompt_version=PROMPT_VERSION,
        model_name=model_name,
        passed=result.passed,
        failures=list(result.failures) or None,
        duration_ms=result.duration_ms,
    )
