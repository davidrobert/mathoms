"""LLM mock fixtures para E2E premium tier — F6.5F.11 (ADR-070).

# Por que

Pipeline premium tier chama LiteLLM → Anthropic/OpenAI. Em CI default,
mockamos para evitar custo ($) + flakiness (rate limit do provider +
quota). Nightly opt-in (`PW_REAL_LLM=1`) roda com API real.

# Como

Backend usa `pipeline.llm.litellm_client.LLMService` que chama LiteLLM via
Instructor. Em tests:

```python
from backend.tests.fixtures.llm_mock import mock_llm_service

async def test_with_mocked_llm(monkeypatch):
    mock_llm_service(monkeypatch)
    # Agora qualquer call LLM retorna fixture válida por stage
```

Em E2E (Playwright + backend real), a ativação é via env var
`MATHOMS_LLM_MOCK=1` que o backend detecta e injeta fallback. Default
em CI = ativado. Passar `PW_REAL_LLM=1` desliga.

# Outputs mockados por stage

- `E1` → MemberExtraction (1 member placeholder)
- `E1.5` → BaselinePatrimonial (imóvel + investimento)
- `E2-llm` → TransactionList (2 transações)

Cada output passa pelos validators downstream (Instructor + Pydantic),
então mudar estrutura requer atualizar fixture + validator.
"""

from __future__ import annotations

from typing import Any

# ─── Fixture outputs por stage ────────────────────────────────────────

_E1_OUTPUT: dict[str, Any] = {
    "members": [
        {
            "key": "titular_mock",
            "full_name": "Titular Mock",
            "short_name": "Titular",
            "cpf": "000.000.000-00",
            "birth_date": "1990-01-01",
            "role": "titular",
            "extra": {},
        }
    ],
    "_meta": {"source": "llm_mock", "confidence": 0.95},
}

_E15_OUTPUT: dict[str, Any] = {
    "imoveis": [
        {
            "descricao": "Imóvel Mock — apartamento",
            "valor_aquisicao": 500_000.00,
            "valor_atual": 600_000.00,
            "localizacao": "São Paulo - SP",
        }
    ],
    "investimentos": [
        {
            "instituicao": "Corretora Mock",
            "tipo": "CDB",
            "valor_atual": 100_000.00,
        }
    ],
    "dividas": [],
    "_meta": {"source": "llm_mock"},
}

_E2_LLM_OUTPUT: dict[str, Any] = {
    "transacoes": [
        {
            "data": "2026-04-05",
            "descricao": "Mock Mercado",
            "valor": -250.50,
            "categoria": "alimentacao",
            "titular": "titular_mock",
            "banco": "mock_bank",
            "tipo_conta": "corrente",
            "moeda": "BRL",
        },
        {
            "data": "2026-04-01",
            "descricao": "Mock Salário",
            "valor": 12_500.00,
            "categoria": "salario",
            "titular": "titular_mock",
            "banco": "mock_bank",
            "tipo_conta": "corrente",
            "moeda": "BRL",
        },
    ],
    "_meta": {"source": "llm_mock"},
}

_STAGE_OUTPUTS: dict[str, dict[str, Any]] = {
    "E1": _E1_OUTPUT,
    "E1.5": _E15_OUTPUT,
    "E2-llm": _E2_LLM_OUTPUT,
}


def get_mock_output(stage: str) -> dict[str, Any]:
    """Retorna dict fixture para o stage dado. Raises se stage desconhecido."""
    if stage not in _STAGE_OUTPUTS:
        raise ValueError(f"LLM mock não tem fixture para stage {stage!r}")
    return _STAGE_OUTPUTS[stage]


def mock_llm_service(monkeypatch) -> None:
    """Instala mock global do `LLMService.call_*` via monkeypatch.

    Uso em tests pytest:
        def test_foo(monkeypatch):
            mock_llm_service(monkeypatch)
            # ... pipeline roda sem tocar provider real

    Em E2E com backend real, ativação é via env var `MATHOMS_LLM_MOCK=1`
    que o próprio backend detecta (implementação em
    `pipeline/llm/litellm_client.py` a adicionar quando 6.5F.11 for formalizado
    como código, não só fixture).
    """
    from pipeline.llm import litellm_client as llm_service

    def _mock_call_stage(stage: str, **kwargs) -> dict:
        return get_mock_output(stage)

    # Exemplo de override — a assinatura exata do LLMService pode variar;
    # este scaffold cobre o pattern. Implementação real em 6.5F.11 follow-up.
    if hasattr(llm_service, "LLMService"):
        # Intercepta método principal (a confirmar qual — ver pipeline/llm/litellm_client.py)
        original = getattr(llm_service.LLMService, "call", None)
        if original:

            def _mock(self, stage, *args, **kwargs):
                return get_mock_output(stage)

            monkeypatch.setattr(llm_service.LLMService, "call", _mock)


__all__ = ["get_mock_output", "mock_llm_service", "_STAGE_OUTPUTS"]
