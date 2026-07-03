"""Denylist única de PII para logs (ADR-110/ADR-273).

Fonte canônica compartilhada backend↔pipeline — o backend importa daqui
(dependência backend→pipeline, permitida); duplicar a lista causaria drift
entre os dois formatters (condição do co-design sre-devops da ADR-273).
"""

from __future__ import annotations

from typing import Any

#: Campos cujo *valor* é mascarado em qualquer linha de log JSON.
#: Inclui credenciais, PII e valores monetários (CLAUDE.md §"Regras críticas").
#: Match é case-insensitive e cobre substrings (ex.: ``api_key`` cobre ``anthropic_api_key``).
SENSITIVE_FIELD_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cpf",
    "cnpj",
    "value_brl",
    "valor",
    "amount_brl",
    "saldo",
    # ADR-192 — PII de apólice de seguro: número, valor segurado raw,
    # nome do segurado. ``coverage_bucket`` (índice de faixa) é OK.
    "policy_ref",
    "policy_number",
    "coverage_brl",
    "premium_monthly_brl",
    "holder_name",
    # ADR-236 P6 — campos monetários do domínio tributário PJ. Telemetria
    # ``mathoms.tributario.*`` é estritamente categórica (regime, código de
    # trigger, lista de missing_fields). Estes substrings garantem que
    # nenhum caller acidentalmente vaze montante em ``extra=``.
    "receita_bruta",
    "receita_pj",
    "receita_aluguel",
    "pro_labore",
    "lucros_distribuidos",
    "lucro_contabil",
    "folha_pj",
    "folha_anual",
    "das_pago",
    "iss_pago",
    "iss_total",
    "pgbl_base",
    "pgbl_limite",
    "renda_pf",
    "outras_rendas",
    "inss_patronal",
    "inss_empregado",
    "inss_pago",
    "irrf",
    "tributos_federais",
    "carga_total",
    "break_even",
    "razao_social",
    "nome_fantasia",
)

REDACTED_PLACEHOLDER = "***"


def is_sensitive_key(key: str) -> bool:
    """Chave casa (substring, case-insensitive) com a denylist."""
    lowered = key.lower()
    return any(needle in lowered for needle in SENSITIVE_FIELD_SUBSTRINGS)


def redact(value: Any) -> Any:
    """Recursively replace sensitive field values with ``***``.

    Keys are matched against :data:`SENSITIVE_FIELD_SUBSTRINGS` (case-insensitive
    substring). Non-dict/list scalars are returned unchanged — redaction only
    fires when the *key* matches. Strings/numbers/bool at the value level are
    left alone; callers are expected not to put raw secrets into log messages.
    """
    if isinstance(value, dict):
        return {
            k: (REDACTED_PLACEHOLDER if is_sensitive_key(k) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
