---
id: A36.l5
type: lane
title: "Estreitar `except` largos em cripto (vault) e validação financeira (baseline)"
sprint: A36
status: planned
priority: P1
branch_slug: a36-l5-narrow-broad-excepts
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/backend
  - area/pipeline
---

# A36.l5 — `narrow-broad-excepts` (QUAL-01 · QUAL-02)

> **Tiers separados (revisão 2026-07-10):** **QUAL-02** (baseline) = **P1** —
> correctness de dado financeiro observável; **QUAL-01** (vault) = **P2** —
> baixa frequência, mas toca feature BYOK paga. Executáveis juntas (mesma S) ou
> separadas.

## Problema

Dois `except` capturam `Exception` genérica em caminhos que decidem coisas
**criptográficas/financeiras** — um erro real de programação/encoding vira
`None`/`continue` silencioso.

- **QUAL-02 (P1)** — `pipeline/domain/services/baseline_validator.py:141`:
  `except Exception: continue` após `Money.of(str(saldo_raw), "BRL")`. Uma conta
  cujo saldo não parseia **escapa da reconciliação baseline↔extrato do E3** sem
  log de qual/porquê.
  **Correção de escopo (revisão 2026-07-10):** o `baseline_validator` é consumido
  **só** pela reconciliação E3 (`e3_reconciler_adapter.py:316,465` +
  `reconcile_transactions.py`) — **não** pela construção do patrimônio líquido
  (E1.5/E1.5c **não** o importam). Então o `continue` **não dropa a conta do
  patrimônio** (como a descrição original dizia); ele **cega o alarme**: a
  divergência genuína extrato×IRPF daquela conta **não gera `BaselineDiffWarning`**.
  Severidade **média** (silencia um controle de qualidade de dado), não perda de
  net worth. Ainda vale corrigir: hoje é perda *silenciosa*; o fix a torna
  *observável*. E esse drop é **invisível a qualquer gate downstream** — nem o E7
  (A36.l3) o pega, porque a conta simplesmente não entra na reconciliação.
- **QUAL-01 (P2)** — `backend/app/services/security/vault.py` (`decrypt` ~`:63`,
  `needs_rotation` ~`:73`): `except (InvalidToken, Exception): return None`. O
  `Exception` é **redundante** (subsume `InvalidToken`) e **mascara** falha real.
  Uma chave BYOK cujo ciphertext corrompeu vira `None` sem sinal — a análise
  Premium (paga) degrada sem o usuário saber.

## Escopo

### QUAL-02 · `baseline_validator.py` (P1)

1. Trocar `except Exception` por **`except (InvalidOperation, ValueError)`** —
   com `from decimal import InvalidOperation`.
   > **Pegadinha crítica (verificada):** `Money.of` recebe sempre `str(...)` e
   > moeda hardcoded `"BRL"` → o único erro real do caminho é
   > `Decimal("lixo").quantize(...)` → **`decimal.InvalidOperation`**, que herda de
   > `ArithmeticError`, **NÃO de `ValueError`**. Logo `except ValueError` sozinho
   > **não pega nada** — o defeito continuaria e o teste de aceite passaria
   > capturando zero. `InvalidOperation` é o load-bearing; `ValueError` é
   > belt-and-suspenders (path de currency + forward-compat). `TypeError` fica de
   > fora (não dispara com `str()`; se disparar é bug que deve propagar).
2. **Logar `WARNING`** (não debug — é perda de dado financeiro sem rede
   downstream), estruturado: **banco + ano + membro, nunca o valor do saldo**
   (§sigilo). O log deve ser acionável de volta à extração E1.5 (saldo malformado
   no baseline é quase sempre defeito de extração).
3. **Emitir um `ReviewReason`** (o value object já existe no módulo; reusar
   `domain_baseline_divergence` ou criar `domain_baseline_parse_failed`) — para o
   descarte virar sinal visível no mesmo canal do resto do E3, não um log que
   ninguém lê. (A escalada a `needs_review` no boundary do E1.5 é P2, gated por
   *medição*: aterrisse o log, veja se ocorre em prod, só então wire.)

### QUAL-01 · `vault.py` (P2)

1. Trocar `except (InvalidToken, Exception)` por `except InvalidToken` nos dois
   métodos; qualquer outra exceção **propaga**. `logger.warning` estruturado
   (sem valor, sem ciphertext) antes de propagar.
   > **Nota de disponibilidade (verificada):** o risco de regressão é quase nulo
   > — `InvalidToken` do Fernet já cobre chave errada (rotação), token adulterado
   > **e base64 malformado** (embrulha `binascii.Error`). Então ciphertext
   > legitimamente corrompido **continua** virando `None`. O branch `Exception`
   > só pegava hoje bugs de programação (`TypeError`, `None` adiante) que você
   > **quer** que estourem.
2. **Decidir o failure-mode no call-site BYOK, não no primitivo:** se a leitura
   de chave BYOK falhar, isso é degradação/`needs_review` visível ao usuário —
   **não** trocar `None` silencioso por 500 mudo. (Copy fica com `product-designer`.)

**Fora de escopo:** os `except Exception: pass` best-effort de progresso
(QUAL-06) — baixa, P2 separado.

## Critérios de aceite

- **QUAL-02:** conta com `saldo` presente que falha o parse gera log `WARNING`
  estruturado (banco+ano+membro, sem valor) **+ `ReviewReason`**, nunca `continue`
  mudo. Teste com saldo que gere **`InvalidOperation` real** (ex.: `"N/D"`,
  `"1.234,56"`, `""`) — não um `ValueError` que mascararia o no-op.
- **QUAL-01:** `vault.decrypt` só engole `InvalidToken`; ciphertext genuinamente
  não-Fernet (ex.: `None`/tipo errado) **propaga** (teste unitário). Falha de
  chave BYOK aflora ao usuário, não vira `None` mudo nem 500.
- Nenhum valor de saldo/PII/ciphertext nos logs.

**Esforço:** S (ambas). **Origem:** auditoria r4 (QUAL-01, QUAL-02).
