---
id: A36.l5
type: lane
title: "Estreitar `except` largos em cripto (vault) e validação financeira (baseline)"
sprint: A36
status: planned
priority: P1
adrs: []
depends_on: []
branch_slug: a36-l5-narrow-broad-excepts
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/backend
  - area/pipeline
---

# A36.l5 — `narrow-broad-excepts` (QUAL-01 · QUAL-02)

## Problema

Dois `except` capturam `Exception` genérica em caminhos que decidem coisas
**criptográficas/financeiras** — um erro real de programação/encoding vira
`None`/`continue` silencioso.

- **QUAL-01** — `backend/app/services/security/vault.py:63`:
  `except (InvalidToken, Exception): return None`. O `decrypt` só deveria
  retornar `None` para **token inválido** (rotação MultiFernet); o `Exception`
  é **redundante e mascara** falha real (ex.: ciphertext corrompido). Uma chave
  BYOK que ficou ilegível vira `None` sem sinal. Mesmo padrão em
  `needs_rotation` (~`:73`).
- **QUAL-02** — `pipeline/domain/services/baseline_validator.py:141`:
  `except Exception: continue` após `Money.of(str(saldo_raw), "BRL")`. Uma conta
  com saldo malformado é **dropada do patrimônio** sem log de qual/porquê —
  perda silenciosa de dado financeiro.

## Escopo

1. `vault.py`: trocar `except (InvalidToken, Exception)` por `except InvalidToken`
   nos dois métodos (`decrypt`, `needs_rotation`); qualquer outra exceção
   **propaga** (bug real aparece). Opcional: `logger.debug` antes de propagar.
2. `baseline_validator.py`: trocar `except Exception` por
   `except (InvalidOperation, ValueError)` e **logar** a conta/ano dropados —
   estruturado, **sem PII** (banco + ano, nunca o valor do saldo).

**Fora de escopo:** os `except Exception: pass` best-effort de progresso
(QUAL-06) — esses são baixa e ficam para P2 separado.

## Critérios de aceite

- `vault.decrypt` só engole `InvalidToken`; um ciphertext corrompido levanta
  erro em vez de virar `None` (teste unitário com ciphertext malformado).
- `baseline_validator` loga toda conta dropada com motivo; nenhuma some
  silenciosamente (teste com saldo malformado assere o log).
- Nenhum valor de saldo/PII aparece nos logs.

**Esforço:** S. **Origem:** auditoria r4 (QUAL-01, QUAL-02).
