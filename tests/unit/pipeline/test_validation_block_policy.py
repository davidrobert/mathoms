"""CTO-3 (§r7) — tabela de política de `validation.valid`, exercitada por produtor."""

# O único produtor com teste comportamental era o E3
# (`test_e3_domain_review_reasons.py`), e é o único que honra `BLOCKING_CODES`.
# Os demais eram cobertos por afirmação de pertinência em conjunto
# (`code not in BLOCKING_CODES`), que não toca o predicado que retém o run.
# Este arquivo caracteriza o comportamento MEDIDO em 2026-08-19, divergências
# incluídas. É o baseline do RV7-03/DE-3: quando o predicado de pausa virar
# `any(code ∈ BLOCKING_CODES)`, os casos marcados DIVERGE mudam de valor — e
# mudá-los tem de ser ato deliberado, não descoberta em produção.

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipeline.domain.review_reason import BLOCKING_CODES, ReviewReason, ReviewReasonCode

_KW = dict(stage="s", artifact_key="k", document_id=None)

_ADVISORY = ReviewReasonCode.domain_balance_gap
_BLOCKING = ReviewReasonCode.extract_missing_required_field


def _reason(code: ReviewReasonCode) -> ReviewReason:
    return ReviewReason(code=code, offending_value="index=0", expected="x", message="m", **_KW)


def test_o_par_advisory_blocking_da_tabela_e_real() -> None:
    """Sem isto, os casos abaixo passariam pelo motivo errado."""
    assert _ADVISORY not in BLOCKING_CODES
    assert _BLOCKING in BLOCKING_CODES


class TestE3HonraBlockingCodes:
    """Referência: é o único produtor cujo `valid` deriva de `BLOCKING_CODES`."""

    def _block(self, *codes: ReviewReasonCode) -> dict:
        from scripts.reconcile_transactions import _e3_validation_block

        class _Result:
            review_reasons = tuple(_reason(c) for c in codes)

        return _e3_validation_block(_Result())

    def test_advisory_nao_invalida(self) -> None:
        assert self._block(_ADVISORY)["valid"] is True

    def test_blocking_invalida(self) -> None:
        assert self._block(_BLOCKING)["valid"] is False

    def test_advisory_ao_lado_de_blocking_nao_dilui(self) -> None:
        assert self._block(_ADVISORY, _BLOCKING)["valid"] is False


# É a contradição que a emenda 2026-08-19 da ADR-393 registra: a §D4 promete
# "o run segue", e o predicado publica `valid=False`.
class TestE2LlmIgnoraBlockingCodes:
    """DIVERGE — `extract.reader_missing` é advisory e mesmo assim invalida."""

    def _block(self, skipped: list[dict]) -> dict:
        from pipeline.stages.extract_with_llm import _e2llm_validation_block

        return _e2llm_validation_block([], skipped)

    def test_skip_com_defeito_invalida_apesar_de_advisory(self) -> None:
        assert ReviewReasonCode.extract_reader_missing not in BLOCKING_CODES
        block = self._block([{"file": "x.xls", "motivo": "sem_leitor"}])
        assert block["valid"] is False, "DIVERGE do E3: advisory retém o run"

    def test_documento_vazio_e_a_unica_excecao(self) -> None:
        assert self._block([{"file": "x.pdf", "motivo": "documento_vazio"}])["valid"] is True

    def test_sem_skip_e_valido(self) -> None:
        assert self._block([])["valid"] is True


# `ValidationResult` alimenta E1, E1.5 e E1.6. `add_issue(severity="error")`
# empurra para `errors`, e `valid` é `len(errors) == 0` — o vocabulário de
# `ReviewReasonCode` nunca é consultado.
class TestProdutoresQueDerivamDeSeveridade:
    """DIVERGE — `valid` deriva da severidade da issue, não do code."""

    def _result(self, severity: str, code: str):
        from pipeline.llm.validators import ValidationResult

        result = ValidationResult()
        result.add_issue(code=code, severity=severity, legacy_message="m")
        return result.to_dict()

    def test_severity_error_invalida(self) -> None:
        assert self._result("error", "e15.item.empty_code")["valid"] is False

    def test_severity_warning_nao_invalida(self) -> None:
        assert self._result("warning", "e15.item.empty_code")["valid"] is True

    def test_code_de_blocking_com_severity_warning_nao_retem(self) -> None:
        """A medição da divergência: o code MAIS bloqueante do vocabulário não
        retém aqui, porque quem decide é a severidade."""
        block = self._result("warning", _BLOCKING.value)
        assert _BLOCKING in BLOCKING_CODES
        assert block["valid"] is True, "DIVERGE do E3: BLOCKING_CODES é inerte"

    def test_code_advisory_com_severity_error_retem(self) -> None:
        """E o inverso: advisory retém, se a severidade disser."""
        block = self._result("error", _ADVISORY.value)
        assert _ADVISORY not in BLOCKING_CODES
        assert block["valid"] is False, "DIVERGE do E3: advisory retém o run"

    def test_bloco_do_validator_nao_carrega_review_reasons(self) -> None:
        """Sem a chave, não há por onde um code advisory reverter o veredito."""
        assert "review_reasons" not in self._result("error", "x")
