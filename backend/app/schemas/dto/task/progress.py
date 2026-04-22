"""``TaskProgressResponse`` — progresso derivado de transações do mês (F8.3).

Só faz sentido para tasks acionáveis recorrentes (ex: "Configurar
aporte R$ 20k/mês"). Para tasks binárias, ``is_trackable=False`` e
todos os campos monetários são ``None`` — UI esconde o card.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TaskProgressResponse(BaseModel):
    """Progresso de execução de uma tarefa recorrente."""

    is_trackable: bool = Field(
        ...,
        description="True se temos heurística para medir % executado.",
    )
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    target_brl: Optional[float] = Field(
        None,
        description="Valor-alvo do período (ex: aporte mensal R$ 20.000).",
    )
    executed_brl: Optional[float] = Field(
        None,
        description="Valor efetivamente movimentado no período (abs).",
    )
    percent_executed: Optional[float] = Field(
        None,
        description="0..100+ (pode passar de 100 se superou).",
    )
    matched_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords que dispararam o match da task (debug/UI).",
    )
    matched_transactions_count: int = 0
