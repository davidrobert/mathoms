"""Regressão QUAL-02 (A36.l5): saldo malformado no baseline não some em silêncio.

`from_baseline_dict` fazia `except Exception: continue` após `Money.of`, dropando
uma conta com saldo malformado sem sinal — a conta escapava da reconciliação E3
(sem `BaselineDiffWarning`). Agora estreita para `(InvalidOperation, ValueError)`
e loga WARNING estruturado, sem PII (banco+ano, nunca o valor nem o membro).
Nota (data-engineer): `decimal.InvalidOperation` NÃO herda de `ValueError`.
"""

from __future__ import annotations

import decimal
import logging

from pipeline.domain.models.transaction import Money
from pipeline.domain.services.baseline_validator import BaselineAccountSaldo

_LOGGER = "mathoms.pipeline.baseline_validator"


def _baseline(saldo) -> dict:
    return {
        "members": {
            "Fulano de Tal": {
                "contas_bancarias": [
                    {"banco": "itau", "saldo_31_12": saldo, "ano_base": 2024, "tipo": "corrente"}
                ]
            }
        }
    }


def test_invalidoperation_nao_e_subclasse_de_valueerror() -> None:
    """A pegadinha que torna `except ValueError` sozinho um no-op."""
    assert not issubclass(decimal.InvalidOperation, ValueError)


def test_saldo_malformado_dropa_com_warning_sem_pii(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        out = BaselineAccountSaldo.from_baseline_dict(_baseline("N/D"))
    assert out == []  # conta dropada (não parseia)
    recs = [r for r in caplog.records if r.name == _LOGGER]
    assert recs and recs[0].message == "baseline_saldo_unparseable"
    assert recs[0].bank == "itau" and recs[0].year == 2024
    blob = " ".join(f"{r.getMessage()} {r.__dict__}" for r in recs)
    assert "N/D" not in blob  # nunca o valor do saldo
    assert "Fulano" not in blob  # nunca o nome do membro (PII)


def test_saldo_valido_e_incluido() -> None:
    out = BaselineAccountSaldo.from_baseline_dict(_baseline("1234.56"))
    assert len(out) == 1
    assert out[0].bank == "itau"
    assert out[0].saldo == Money.of("1234.56", "BRL")


def test_campos_ausentes_seguem_silenciosos(caplog) -> None:
    """Saldo ausente (não malformado) segue ignorado em silêncio, sem WARNING."""
    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        out = BaselineAccountSaldo.from_baseline_dict(
            {"members": {"X": {"contas_bancarias": [{"banco": "itau", "ano_base": 2024}]}}}
        )
    assert out == []
    assert [r for r in caplog.records if r.name == _LOGGER] == []
