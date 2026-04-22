"""Literais de vocabulário do agregado ``Task`` (ADR-074).

Fonte de verdade dupla: estes ``Literal`` valem para Pydantic + OpenAPI;
os ``frozenset`` em ``backend/app/models/task.py`` valem para validação
runtime fora-do-schema (ex.: categorias adicionadas via config). Quando
divergir, Pydantic rejeita antes do model.
"""

from __future__ import annotations

from typing import Literal

DeadlineKind = Literal["HARD_DATE", "MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED"]

TaskStatus = Literal["pending", "in_progress", "done", "cancelled", "blocked"]

Priority = Literal["S", "R", "O"]

CreatedFrom = Literal["manual", "seed", "llm_suggestion"]

SuggestionStatus = Literal["pending", "approved", "rejected", "merged"]

SuggestionSource = Literal["e5n_llm", "cross_validation", "system_rule"]
