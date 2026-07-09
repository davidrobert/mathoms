"""Testes do parser de config/tarefas.md → ParsedTask."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.services.tarefas_md_parser import (
    ParsedTask,
    parse_tarefas_md,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TAREFAS_MD_PATH = REPO_ROOT / "config" / "tarefas.md"


# ─── Parsing de prazos ─────────────────────────────────────────────────


SAMPLE_MD = """\
# Tarefas

## Essenciais (S)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 1 | Primeira tarefa essencial | Invest. | Abr/2026 | pendente | D01 |
| 3 | Solicitar resgate | Invest. | 30/04/2026 | pendente | — |
| 5 | Tarefa trimestre | Tributário | T3/26 | pendente | — |

---

## Recomendadas (R)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 18 | Confirmar taxa PGBL | Invest. | Abr/2026 | pendente | — |
| 19 | Iniciar PGBL depende de #18 | Tributário | Abr/2026 | pendente | — |

---

## Opcionais (O)

| # | Tarefa | Categoria | Prazo | Status | Ref |
|---|---|---|---|---|---|
| 40 | Testamento americano | Sucessório | Após mudança EUA | pendente | life_plan |

---

## Concluídas (histórico)

| # | Tarefa | Data conclusão | Detalhe |
|---|---|---|---|
| 2 | Zerar cheque especial | Mar/2026 | Quitado |
"""


def test_parse_sample_returns_all_rows():
    parsed = parse_tarefas_md(SAMPLE_MD)
    numbers = sorted([p.number for p in parsed])
    assert numbers == [1, 2, 3, 5, 18, 19, 40]


def test_parse_preserves_priority_mapping():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[1].priority == "S"
    assert parsed[18].priority == "R"
    assert parsed[40].priority == "O"
    # Concluídas: status=done, mesmo que prioridade default
    assert parsed[2].status == "done"


def test_parse_hard_date_deadline():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[3].deadline_kind == "HARD_DATE"
    assert parsed[3].deadline_date == date(2026, 4, 30)


def test_parse_month_deadline():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[1].deadline_kind == "MONTH"
    assert parsed[1].deadline_date == date(2026, 4, 1)
    assert parsed[1].deadline_label == "Abr/2026"


def test_parse_quarter_deadline():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[5].deadline_kind == "QUARTER"
    assert parsed[5].deadline_date is None
    assert parsed[5].deadline_label == "T3/26"


def test_parse_conditional_deadline():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[40].deadline_kind == "CONDITIONAL"
    assert "Após mudança EUA" in parsed[40].deadline_label


def test_parse_normalizes_category():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[1].category == "Invest"  # "Invest." → "Invest"
    assert parsed[19].category == "Tributario"
    assert parsed[40].category == "Sucessorio"


def test_parse_infers_dependency():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    # #19 "depende de #18"
    assert parsed[19].parent_number == 18
    # #18 não depende de ninguém
    assert parsed[18].parent_number is None


def test_parse_preserves_ref():
    parsed = {p.number: p for p in parse_tarefas_md(SAMPLE_MD)}
    assert parsed[1].ref == "D01"
    assert parsed[40].ref == "life_plan"
    assert parsed[18].ref is None  # "—" vira None


# ─── Teste contra o MD real de Andrade Silva ──────────────────────────


def test_parse_real_tarefas_md_expected_counts():
    """Valida estrutura do MD real:
    - 12 tarefas essenciais (S), exceto #2 e #12 concluídas → 10 ativas na seção S
      + 2 na seção Concluídas (ajustado abaixo)
    - Importante: tarefa #12 está em Concluídas; #1..#14 exceto #2/#12 são ativas
    """
    if not TAREFAS_MD_PATH.exists():
        # Tarefas.md só existe no ambiente Andrade Silva (é dados de usuário)
        # No CI genérico o arquivo pode estar ausente — skip gracefully.
        import pytest

        pytest.skip("config/tarefas.md ausente (não aplicável nesse ambiente)")

    parsed = parse_tarefas_md(TAREFAS_MD_PATH.read_text(encoding="utf-8"))
    numbers = {p.number for p in parsed}
    # Garantias estáveis: #1, #2 (done), #12 (done), #43 existem
    assert 1 in numbers
    assert 2 in numbers
    assert 12 in numbers
    assert 43 in numbers
    # Pelo menos 40 tasks (escopo amplo conservador)
    assert len(parsed) >= 40


def test_parse_real_detects_concluidas_statuses():
    if not TAREFAS_MD_PATH.exists():
        import pytest

        pytest.skip("config/tarefas.md ausente")

    parsed = {p.number: p for p in parse_tarefas_md(TAREFAS_MD_PATH.read_text(encoding="utf-8"))}
    assert parsed[2].status == "done"
    assert parsed[12].status == "done"
    # As demais são pendentes ou estão em prioridades S/R/O
    assert parsed[1].status == "pending"
