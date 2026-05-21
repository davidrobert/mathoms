"""Gates LGPD para a telemetria da cascata fiscal PJ (ADR-236 §D6 + P6 · Sprint A16)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import pytest

from backend.app.core.logging import (
    REDACTED_PLACEHOLDER,
    SENSITIVE_FIELD_SUBSTRINGS,
    MathomsJsonFormatter,
)
from backend.app.services.tributario_telemetry import (
    compute_profile_completeness,
    emit_cascata_rendered,
    emit_profile_incomplete,
    emit_telemetry_for_section,
    emit_trigger_shown,
)

_TRIBUTARIO_LOGGER = "mathoms.tributario"

# Whitelist explícita — só estes campos podem aparecer em ``extra=`` de cada
# evento. Qualquer chave adicional é regressão LGPD (ADR-236 §D6).
_WHITELIST_BY_EVENT: dict[str, set[str]] = {
    "mathoms.tributario.cascata_rendered": {
        "event_type",
        "regime",
        "has_complete_profile",
        "triggers_count",
    },
    "mathoms.tributario.trigger_shown": {
        "event_type",
        "trigger_code",
        "regime",
    },
    "mathoms.tributario.profile_incomplete": {
        "event_type",
        "missing_fields",
    },
}

# Campos monetários canônicos da CascataOutput — não podem aparecer como
# *key* nem como *valor* (substring) em nenhum evento.
_MONEY_KEYS_FORBIDDEN: tuple[str, ...] = (
    "receita_bruta",
    "receita_pj_anual",
    "tributos_federais",
    "iss_total",
    "lucro_contabil_pj",
    "pro_labore_bruto",
    "pro_labore_mensal",
    "lucros_distribuidos",
    "inss_patronal",
    "inss_empregado",
    "irrf_pro_labore",
    "renda_pf_tributavel_total",
    "pgbl_base_anual",
    "pgbl_limite_anual",
    "folha_pj_mensal",
    "das_pago_mensal",
    "iss_pago_mensal",
    "outras_rendas_tributaveis_pf_anual",
    "carga_total_pct",
    "fator_r_break_even",
    "cnpj",
    "razao_social",
    "nome_fantasia",
)


# ─────────────────────────────────────────────────────────────────────────────
# Pure unit — compute_profile_completeness
# ─────────────────────────────────────────────────────────────────────────────


def test_profile_completeness_all_required():
    is_complete, missing = compute_profile_completeness(
        regime="simples",
        anexo_simples="III",
        tipo_declaracao_ir="completa",
    )
    assert is_complete is True
    assert missing == []


def test_profile_completeness_missing_regime():
    is_complete, missing = compute_profile_completeness(
        regime=None,
        anexo_simples=None,
        tipo_declaracao_ir=None,
    )
    assert is_complete is False
    assert "regime" in missing
    assert "tipo_declaracao_ir" in missing


def test_profile_completeness_simples_requires_anexo():
    is_complete, missing = compute_profile_completeness(
        regime="simples",
        anexo_simples=None,
        tipo_declaracao_ir="completa",
    )
    assert is_complete is False
    assert missing == ["anexo_simples"]


def test_profile_completeness_mei_does_not_require_anexo():
    is_complete, missing = compute_profile_completeness(
        regime="mei",
        anexo_simples=None,
        tipo_declaracao_ir="simplificada",
    )
    assert is_complete is True
    assert missing == []


def test_profile_completeness_presumido_with_tipo_declaracao():
    is_complete, missing = compute_profile_completeness(
        regime="lucro_presumido",
        anexo_simples=None,
        tipo_declaracao_ir="completa",
    )
    assert is_complete is True
    assert missing == []


# ─────────────────────────────────────────────────────────────────────────────
# Telemetria emit — caplog whitelist gate
# ─────────────────────────────────────────────────────────────────────────────


def _extract_records(records: list[logging.LogRecord]) -> list[dict[str, Any]]:
    """Extrai ``extra=`` de cada record do logger tributário."""
    rows: list[dict[str, Any]] = []
    standard = set(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys())
    standard.update({"message", "asctime"})
    for r in records:
        if not r.name.startswith(_TRIBUTARIO_LOGGER):
            continue
        rows.append({k: v for k, v in r.__dict__.items() if k not in standard})
    return rows


def test_emit_cascata_rendered_whitelist(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_cascata_rendered(regime="simples", has_complete_profile=True, triggers_count=2)
    rows = _extract_records(caplog.records)
    assert len(rows) == 1
    extras = set(rows[0].keys())
    allowed = _WHITELIST_BY_EVENT["mathoms.tributario.cascata_rendered"]
    assert extras.issubset(allowed), f"campos extras nao-whitelisted: {extras - allowed}"


def test_emit_trigger_shown_whitelist(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_trigger_shown(trigger_code="T1", regime="simples")
    rows = _extract_records(caplog.records)
    assert len(rows) == 1
    extras = set(rows[0].keys())
    allowed = _WHITELIST_BY_EVENT["mathoms.tributario.trigger_shown"]
    assert extras.issubset(allowed)


def test_emit_profile_incomplete_whitelist(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_profile_incomplete(missing_fields=["regime", "tipo_declaracao_ir"])
    rows = _extract_records(caplog.records)
    assert len(rows) == 1
    extras = set(rows[0].keys())
    allowed = _WHITELIST_BY_EVENT["mathoms.tributario.profile_incomplete"]
    assert extras.issubset(allowed)


def test_emit_full_section_pipeline(caplog: pytest.LogCaptureFixture):
    """Cascata renderizada + 5 triggers + profile_incomplete (cenário com missing)."""
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_telemetry_for_section(
            regime="simples",
            has_complete_profile=False,
            missing_fields=["anexo_simples"],
            trigger_codes=["T1", "T2", "T3", "T4", "T5"],
        )
    rows = _extract_records(caplog.records)
    # 1 cascata_rendered + 5 trigger_shown + 1 profile_incomplete = 7
    assert len(rows) == 7
    by_event: dict[str, int] = {}
    for row in rows:
        by_event[row["event_type"]] = by_event.get(row["event_type"], 0) + 1
    assert by_event["mathoms.tributario.cascata_rendered"] == 1
    assert by_event["mathoms.tributario.trigger_shown"] == 5
    assert by_event["mathoms.tributario.profile_incomplete"] == 1


def test_emit_full_section_complete_profile_no_incomplete_event(
    caplog: pytest.LogCaptureFixture,
):
    """Quando profile está completo, profile_incomplete não é emitido."""
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_telemetry_for_section(
            regime="mei",
            has_complete_profile=True,
            missing_fields=[],
            trigger_codes=[],
        )
    rows = _extract_records(caplog.records)
    events = {row["event_type"] for row in rows}
    assert "mathoms.tributario.profile_incomplete" not in events
    assert events == {"mathoms.tributario.cascata_rendered"}


# ─────────────────────────────────────────────────────────────────────────────
# Gate hard — denylist via formatter (defesa em profundidade)
# ─────────────────────────────────────────────────────────────────────────────


def _format_record(record: logging.LogRecord) -> dict[str, Any]:
    fmt = MathomsJsonFormatter()
    return json.loads(fmt.format(record))


def _make_record(name: str, msg: str, extra: dict[str, Any]) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=msg,
        args=None,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_tributario_no_money_in_logs(caplog: pytest.LogCaptureFixture):
    """Gate LGPD hard — formatter mascara qualquer key monetária da cascata."""
    for key in _MONEY_KEYS_FORBIDDEN:
        record = _make_record(
            "mathoms.tributario.cascata_rendered",
            "regression",
            {"event_type": "mathoms.tributario.cascata_rendered", key: 123456.78},
        )
        rendered = _format_record(record)
        assert (
            rendered.get(key) == REDACTED_PLACEHOLDER
        ), f"campo {key!r} vazou: {rendered.get(key)!r}"


_TRIBUTARIO_DENYLIST_REQUIRED: tuple[str, ...] = (
    "receita_bruta",
    "receita_pj",
    "pro_labore",
    "lucros_distribuidos",
    "lucro_contabil",
    "folha_pj",
    "das_pago",
    "iss_pago",
    "iss_total",
    "pgbl_base",
    "pgbl_limite",
    "renda_pf",
    "outras_rendas",
    "inss_patronal",
    "inss_empregado",
    "irrf",
    "tributos_federais",
    "carga_total",
    "break_even",
    "razao_social",
    "nome_fantasia",
)


def test_tributario_money_substrings_in_denylist():
    """Garante substrings monetários do domínio tributário na denylist (gate de ADR evolution)."""
    missing = [s for s in _TRIBUTARIO_DENYLIST_REQUIRED if s not in SENSITIVE_FIELD_SUBSTRINGS]
    assert missing == [], f"substrings tributários ausentes da denylist: {missing}"


def _row_contains_forbidden(row: dict[str, Any]) -> Optional[tuple[str, str]]:
    return next(
        (
            (key, forbidden)
            for key in row
            for forbidden in _MONEY_KEYS_FORBIDDEN
            if forbidden in key.lower()
        ),
        None,
    )


def test_emitted_events_have_no_money_keys(caplog: pytest.LogCaptureFixture):
    """Pipeline real: emitter completo não tem nenhuma chave monetária."""
    with caplog.at_level(logging.INFO, logger=_TRIBUTARIO_LOGGER):
        emit_telemetry_for_section(
            regime="lucro_presumido",
            has_complete_profile=True,
            missing_fields=[],
            trigger_codes=["T3", "T4"],
        )
    for row in _extract_records(caplog.records):
        hit = _row_contains_forbidden(row)
        assert hit is None, f"chave {hit[0]!r} contém substring monetária proibida {hit[1]!r}"
