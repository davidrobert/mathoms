"""Canal de Issue do watchdog de agendados — o corpo do relatório é gatilho de
abertura E de auto-close, então o que entra nele decide se o alerta apodrece
(ADR-210 §Adendo 2026-08-21b)."""

from __future__ import annotations

import pytest

from dev import check_scheduled_workflows as mod

# Forma medida na #1122: aberta 21 dias porque o waiver do nightly (válido até
# 2026-10-15) mantinha o relatório não-vazio, e o auto-close só dispara quando
# ele é vazio. Nome de workflow genérico de propósito — o defeito é do canal,
# não daquela entrada.
WAIVED = mod.Violation("S1", "qualquer-agendado.yml", "está `disabled_manually`", waived=True)
MUDO = mod.Violation("GH", "qualquer-agendado.yml", "`gh` não respondeu")
REAL = mod.Violation("S2", "qualquer-agendado.yml", "último run há 9d (limite 3d)")


def _corpo(violations, capsys) -> str:
    assert mod._report(violations) == 0
    return capsys.readouterr().out.strip()


def test_waived_sozinho_deixa_o_corpo_vazio(capsys):
    """Vazio é o que fecha a Issue. Renderizar WAIVED a mantinha viva para sempre."""
    assert _corpo([WAIVED], capsys) == ""


def test_gh_sozinho_deixa_o_corpo_vazio(capsys):
    """Ruído de API não pode iniciar o relógio de rot do S3."""
    assert _corpo([MUDO], capsys) == ""


def test_violacao_real_alimenta_a_issue(capsys):
    corpo = _corpo([WAIVED, MUDO, REAL], capsys)
    assert "último run há 9d" in corpo
    assert "disabled_manually" not in corpo
    assert "não respondeu" not in corpo


def test_gh_continua_bloqueando_o_gate(monkeypatch):
    """Fail-closed em "não sei medir" é a postura da camada — o docstring do
    módulo já afirmou o contrário, e é isso que este teste impede de voltar."""
    monkeypatch.delenv("MATHOMS_PR_LABELS", raising=False)
    assert mod._gate([MUDO]) == 1


def test_waived_sozinho_nao_bloqueia_o_gate(monkeypatch):
    monkeypatch.delenv("MATHOMS_PR_LABELS", raising=False)
    assert mod._gate([WAIVED]) == 0
