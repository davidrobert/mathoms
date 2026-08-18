"""Parâmetros de amostragem das chamadas de extração ([[A40.l66]] cauda).

Claim honesto: isto **reduz variância**, não torna a extração idempotente. Duas
razões medidas, ambas de fora do nosso controle:

- `temperature=0.0` não é determinismo — é o modo da distribuição, e o provider
  segue livre para variar entre execuções;
- `seed` **não é suportado** por `anthropic/claude-sonnet-4-6`, o provider
  default (`litellm.get_supported_openai_params` não o lista), e o cliente roda
  com `litellm.drop_params = True`: o kwarg é descartado antes da API. Em
  `openai/*` ele chega. Passamos assim mesmo porque o custo é zero e o ganho
  aparece no dia em que o provider mudar — mas o gate que exige o kwarg fecha
  **sintaxe**, não determinismo.
"""

from __future__ import annotations

#: Modo da distribuição. Cache de extração exige 0.0 ([[ADR-307]]).
EXTRACTION_TEMPERATURE = 0.0

#: Constante — variar o seed entre runs derrotaria o propósito.
EXTRACTION_SEED = 20260818
