"""Testes unitários dos mappers DTO do agregado Task (+ sub-agregados).

Cobrem:

- ``task_to_response`` preserva campos (incluindo timestamps e
  ``status_reason``), enum strings e campos opcionais None.
- ``task_attachment_to_response`` mapeia metadata sem tocar o binário.
- ``task_suggestion_to_response`` preserva ``proposed_payload`` dict
  intacto (sem reformatação).
- Mappers funcionam sem AsyncSession.
- ``TaskFilters`` defaults corretos (include_done=False etc.).
- ``TaskCreateCommand`` ``number`` opcional (auto-atribuído no service).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from backend.app.schemas.dto.task import (
    TaskCreateCommand,
    TaskFilters,
    TaskStatusTransitionCommand,
    TaskUpdateCommand,
    task_attachment_to_response,
    task_suggestion_to_response,
    task_to_response,
)


def _fake_task(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="task-1",
        workspace_id="ws-1",
        number=5,
        title="Revisar alocação de caixa",
        description="Rebalancear ~10% para RF",
        category="Invest",
        priority="R",
        deadline_kind="MONTH",
        deadline_date=None,
        deadline_label="Mai/2026",
        ref="# plano-investimento",
        parent_task_id=None,
        related_transaction_id=None,
        related_goal_id=None,
        assigned_to=None,
        status="pending",
        status_reason=None,
        created_from="manual",
        source_suggestion_id=None,
        completed_at=None,
        cancelled_at=None,
        created_by="user-1",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_attachment(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="att-1",
        task_id="task-1",
        workspace_id="ws-1",
        original_filename="comprovante.pdf",
        content_type="application/pdf",
        size_bytes=120456,
        uploaded_by="user-1",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_suggestion(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="sugg-1",
        workspace_id="ws-1",
        proposed_payload={
            "title": "Revisar PGBL",
            "category": "Invest",
            "priority": "R",
            "deadline_kind": "UNSCHEDULED",
        },
        source="e5n_llm",
        source_run_id="run-1",
        status="pending",
        rejection_reason=None,
        approved_task_id=None,
        reviewed_by=None,
        reviewed_at=None,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestTaskToResponse:
    def test_minimal_task(self):
        task = _fake_task()

        resp = task_to_response(task)

        assert resp.id == "task-1"
        assert resp.number == 5
        assert resp.title == "Revisar alocação de caixa"
        assert resp.priority == "R"
        assert resp.deadline_kind == "MONTH"
        assert resp.status == "pending"

    def test_completed_task(self):
        completed_at = datetime(2026, 4, 15, tzinfo=timezone.utc)
        task = _fake_task(
            status="done",
            status_reason="Rebalanceamento concluído",
            completed_at=completed_at,
        )

        resp = task_to_response(task)

        assert resp.status == "done"
        assert resp.status_reason == "Rebalanceamento concluído"
        assert resp.completed_at == completed_at
        assert resp.cancelled_at is None

    def test_with_parent_and_relations(self):
        task = _fake_task(
            parent_task_id="parent-1",
            related_transaction_id="tx-1",
            related_goal_id="goal-1",
            assigned_to="member-1",
        )

        resp = task_to_response(task)

        assert resp.parent_task_id == "parent-1"
        assert resp.related_transaction_id == "tx-1"
        assert resp.related_goal_id == "goal-1"
        assert resp.assigned_to == "member-1"

    def test_hard_date_deadline(self):
        task = _fake_task(
            deadline_kind="HARD_DATE",
            deadline_date=date(2026, 5, 15),
            deadline_label=None,
        )

        resp = task_to_response(task)

        assert resp.deadline_kind == "HARD_DATE"
        assert resp.deadline_date == date(2026, 5, 15)
        assert resp.deadline_label is None

    def test_llm_suggestion_source(self):
        task = _fake_task(
            created_from="llm_suggestion",
            source_suggestion_id="sugg-42",
        )

        resp = task_to_response(task)

        assert resp.created_from == "llm_suggestion"
        assert resp.source_suggestion_id == "sugg-42"


class TestTaskAttachmentToResponse:
    def test_pdf_attachment(self):
        att = _fake_attachment()

        resp = task_attachment_to_response(att)

        assert resp.id == "att-1"
        assert resp.task_id == "task-1"
        assert resp.original_filename == "comprovante.pdf"
        assert resp.content_type == "application/pdf"
        assert resp.size_bytes == 120456

    def test_attachment_without_content_type(self):
        att = _fake_attachment(content_type=None, size_bytes=None)

        resp = task_attachment_to_response(att)

        assert resp.content_type is None
        assert resp.size_bytes is None


class TestTaskSuggestionToResponse:
    def test_pending_suggestion_payload_preserved(self):
        payload = {
            "title": "Nova task",
            "category": "Orcamento",
            "priority": "S",
            "deadline_kind": "HARD_DATE",
            "deadline_date": "2026-05-01",
            "extra": {"nested": True},
        }
        sugg = _fake_suggestion(proposed_payload=payload)

        resp = task_suggestion_to_response(sugg)

        # Mapper NÃO reformata o payload — preserva shape original.
        assert resp.proposed_payload == payload
        assert resp.status == "pending"

    def test_approved_suggestion(self):
        reviewed_at = datetime(2026, 4, 10, tzinfo=timezone.utc)
        sugg = _fake_suggestion(
            status="approved",
            approved_task_id="task-7",
            reviewed_by="user-2",
            reviewed_at=reviewed_at,
        )

        resp = task_suggestion_to_response(sugg)

        assert resp.status == "approved"
        assert resp.approved_task_id == "task-7"
        assert resp.reviewed_by == "user-2"
        assert resp.reviewed_at == reviewed_at

    def test_rejected_suggestion(self):
        sugg = _fake_suggestion(
            status="rejected",
            rejection_reason="Duplicado",
        )

        resp = task_suggestion_to_response(sugg)

        assert resp.status == "rejected"
        assert resp.rejection_reason == "Duplicado"


class TestTaskFiltersDefaults:
    def test_defaults_exclude_done_and_cancelled(self):
        filters = TaskFilters()
        assert filters.include_done is False
        assert filters.include_cancelled is False
        assert filters.status is None
        assert filters.priority is None


class TestTaskCommands:
    def test_task_create_number_optional(self):
        cmd = TaskCreateCommand(
            title="Task nova",
            category="Invest",
            priority="R",
        )
        # number é auto-atribuído no service.
        assert cmd.number is None

    def test_task_create_number_explicit(self):
        cmd = TaskCreateCommand(
            title="Task migrada",
            category="Invest",
            priority="S",
            number=42,
        )
        assert cmd.number == 42

    def test_task_update_all_optional(self):
        cmd = TaskUpdateCommand()
        # Todos os campos None → partial update válido.
        assert cmd.model_dump(exclude_unset=True) == {}

    def test_task_update_partial(self):
        cmd = TaskUpdateCommand(title="Novo título")
        assert cmd.model_dump(exclude_unset=True) == {"title": "Novo título"}

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValueError):
            TaskCreateCommand(
                title="x",
                category="Invest",
                priority="X",  # type: ignore[arg-type]
            )

    def test_status_transition_command(self):
        cmd = TaskStatusTransitionCommand(
            status="done",
            status_reason="Tarefa concluída pelo usuário",
        )
        assert cmd.status == "done"
        assert cmd.status_reason == "Tarefa concluída pelo usuário"

    def test_status_transition_reason_too_long_rejected(self):
        with pytest.raises(ValueError):
            TaskStatusTransitionCommand(
                status="done",
                status_reason="x" * 1001,
            )
