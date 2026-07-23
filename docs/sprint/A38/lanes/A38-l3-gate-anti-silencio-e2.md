---
id: A38.l3
type: lane
title: "Gate anti-silêncio no E2: 0 tx ou conservação quebrada nunca vira artefato 'ok' (ADR Proposto)"
sprint: A38
status: open
priority: P0
branch_slug: a38-l3-gate-anti-silencio-e2
adrs: []
depends_on: []
parallel_with: ["[[A38.l2]]"]
tags:
  - type/lane
  - sprint/a38
  - status/open
  - priority/p0
  - area/pipeline
  - area/dados
---

# A38.l3 — `gate-anti-silencio-e2` (achado #2)

## Problema (evidência verificada 2026-07-22)

`scripts/e2/validation.py::validate_extrato_result` detecta "0 transações
extraídas de PDF com N chars" mas apenas **anota** o ERROR em `notas` — o
artefato segue válido, entra no `DBArtifactStore` e o pipeline consome um
extrato vazio como se fosse verdade. Caso real do corpus: consolidado
Santander → `parse_santander_conta` → 0 tx → artefato "ok". Pior: extração
**parcial** (caso [[A38.l2]]: 50% das linhas) não é detectada por nenhum
check — não existe validação de conservação no E2.

## Escopo

- **ADR `Proposto` antes do PR de implementação** (muda invariante de contrato
  entre E2 e consumidores — política do repo). A ADR fixa o contrato de
  escalação:
  - **0 tx com texto substancial** (PDF com camada de texto ≥ limiar) ⇒
    `requires_llm_fallback=True` (doc vai ao E2-llm, one-shot, sem retry loop)
    e, se o E2-llm também não extrair, `needs_review` no Document.
  - **Conservação quebrada** (quando `saldo_inicial`+`saldo_final` presentes:
    `|saldo_inicial + Σtx − saldo_final| > 0` em cents) ⇒ mesmo caminho.
  - **Exceção legítima**: extrato sem movimentação (0 tx + saldo presente +
    nota explícita do parser, caso Wise "saldo estável") **não** escala.
  - Telemetria: razão da escalação em campo estruturado (não só nota), para o
    harness [[A38.l1]] e o console interno contarem ocorrências.
- Implementação em `validate_extrato_result` + `process_file`
  (`scripts/extract_bank_documents.py`), reusando o contrato
  `requires_llm_fallback` existente — sem mudança no schema `e2_extract`
  (validar premissa na ADR; se precisar de campo novo, é additive).
- Fixtures: extrato 0-tx com texto substancial; extrato com conservação
  quebrada; extrato legítimo sem movimentação (não escala).

## Critério de aceite

- Unit vermelho→verde para os 3 fixtures acima.
- Corpus local (harness [[A38.l1]]): consolidado Santander **escala** (nunca
  mais 0-tx "ok"); extratos Wise sem movimentação **não** escalam (KR-C).
- Nenhum falso-positivo na suíte/goldens existentes (extratos legítimos das
  fixtures atuais continuam sem flag).
- ADR flippada para `Decidido (A38)` no merge do PR de implementação.

## Risco

Médio: muda comportamento de ingestão por design — docs que hoje "passam"
vazios entram em `needs_review` até [[A38.l2]]/[[A38.l4]]/[[A38.l8]]
aterrissarem (decisão do sprint: corretude > cobertura). Escalação tem custo
LLM (tier premium): one-shot por doc, mesmo contrato atual — sem retry.
