---
id: A38.l3
type: lane
title: "Gate anti-silêncio no E2: 0 tx ou conservação quebrada nunca vira artefato 'ok' (ADR Proposto)"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1025
priority: P0
branch_slug: a38-l3-gate-anti-silencio-e2
adrs: ["[[ADR-342]]"]
depends_on: []
parallel_with: ["[[A38.l2]]"]
tags:
  - type/lane
  - sprint/a38
  - status/shipped
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
check — não existe validação de conservação no E2. E o painel confirmou que
`validate_fatura_result` tem o **mesmo defeito** no lado do cartão: seta
`parse_quality` mas só anota; o cross-check Σ×total fica inerte quando
`total_fatura=None` (exatamente o caso [[A38.l7]]).

## Escopo

- **ADR `Proposto` antes do PR de implementação** (muda invariante de contrato
  entre E2 e consumidores — política do repo). A ADR fixa **um contrato de
  escalação único para extrato E fatura** (decisão do painel — endurecer só
  conta corrente deixaria o cartão silenciosamente parcial):
  - **0 tx com texto substancial** (camada de texto ≥ limiar) ⇒
    `requires_llm_fallback=True` (doc vai ao E2-llm, one-shot, sem retry
    loop) e, se o E2-llm também não extrair, `needs_review` no Document.
    Manter os **dois passos** (não pular direto p/ review): o E2-llm lê texto
    completo e recupera docs que a detecção de tabela perde.
  - **Conservação quebrada** (extrato): forma **global**
    `|saldo_inicial + Σtx − saldo_final| > 0` em cents ⇒ mesmo caminho.
    O gate **só roda onde o saldo é observado** — é **no-op** quando saldo
    ausente, ambíguo ou **derivado** (Wise/Rico derivam
    `saldo_inicial = saldo_final − Σtx`; o check seria tautológico).
    Allowlist por banco; conceito de saldo ambíguo escala com razão
    `saldo não reconciliável`, nunca "conservação quebrada". Per-dia fica
    como assert de fixture (dev), não gate de produção.
  - **Fatura**: 0 lançamentos, ou `total_fatura` ausente/divergente do
    Σ lançamentos ⇒ mesmo caminho de escalação.
  - **Moeda indeterminada escala** — parser que não determina moeda por
    conteúdo/nome nunca assume BRL como default silencioso (compõe com
    [[A38.l6]]).
  - **Exceção legítima**: extrato sem movimentação (0 tx + saldo presente +
    nota explícita do parser) **não** escala.
  - Telemetria: razão estruturada via `ReviewReason`/`ReviewReasonCode`
    (códigos novos, ex.: `extract.incomplete_conservation`) — já mascara
    valores e alimenta console + harness [[A38.l1]]. **Zero mudança no
    schema `e2_extract`** (flag + razão são top-level aditivos; `$defs/
    transacao` é `additionalProperties: false` — nada entra na transação).
- **Contrato de read-path (achado crítico do painel/data-engineer)** — o flag
  de escrita sozinho é **no-op no estado estacionário**, porque os stages E2
  são workspace-scoped (`list_keys`/`read` enxergam runs anteriores) e um
  artefato **parcial de run anterior** ressuscita pelo fallback do store. A
  ADR fixa o invariante: **por (workspace, key), no máximo um artefato
  não-fallback vivo entre `extract_statements`/`extract_invoices` e
  `extract_with_llm`**, com 3 mudanças-companheiras:
  1. escalação **grava stub superseding** (`requires_llm_fallback=True`,
     `transacoes: []`, razão) na key determinística do run atual — o parcial
     antigo é marcado superseded;
  2. pickup do E2-llm (`_find_unprocessed_docs`) trata key cujo único
     artefato vivo é stub como **não-processada** (hoje checa só existência);
  3. dedup do E3 (`e3_reconciler_adapter`) **não reivindica** key cujo
     artefato do stage é stub — senão o stub em `extract_statements` bloqueia
     o full do `extract_with_llm`.
  - **Normalização de key única** entre os dois writers (hoje
    `_artifact_key_for_file` ≠ `_e2_extract_stem` p/ filename com espaço/
    >80 chars → duplicação no E3) — pinar uma derivação compartilhada.
- **Rollout do gate de conservação**: WARN global primeiro (emite razão, conta
  no harness/telemetria, não escala) → medir falso-positivo = 0 no corpus +
  goldens → flip HARD **por banco** via allowlist. **Flip HARD do Itaú só
  com [[A38.l2]] shipped** (senão todo extrato Itaú escala p/ LLM).
- **Cura de parciais já gravados** (runs dogfood anteriores): full re-run por
  workspace como passo de runbook — sem script de backfill (blast radius é
  dogfood; o re-run já é necessário pós-l2).
- Fixtures: extrato 0-tx com texto substancial; conservação quebrada
  (saldo observado); extrato sem movimentação (não escala); fatura sem total.

## Critério de aceite

- Unit vermelho→verde para os 4 fixtures acima.
- **Teste de integração com `InMemoryArtifactStore`**: (a) parcial de run
  anterior + escalação no run atual ⇒ E3 lê o **full** do E2-llm, zero
  duplicata; (b) stub não é reivindicado pelo dedup do E3 nem pula o pickup
  do E2-llm; (c) key com espaço/>80 chars não duplica.
- Corpus local (harness [[A38.l1]]): consolidado Santander **escala** (nunca
  mais 0-tx "ok"); extratos sem movimentação **não** escalam (KR-C).
- Suíte golden completa em WARN com falso-positivo = 0 antes de qualquer
  flip HARD; gate no-op comprovado para parsers de saldo derivado (Wise/Rico).
- ADR flippada para `Decidido (A38)` no merge do PR de implementação.

## Risco

Médio-alto (é a lane de contrato do sprint): muda comportamento de ingestão
por design — docs que hoje "passam" vazios entram em `needs_review` até
[[A38.l2]]/[[A38.l4]]/[[A38.l8]] aterrissarem (decisão do sprint: corretude >
cobertura). Escalação tem custo LLM (tier premium): one-shot por doc, sem
retry. Follow-up sinalizado pelo painel (fora do escopo desta lane, registrar
na ADR): propagação E2→E5 do estado de escalação — conta-período com input
escalado deveria suprimir/badgear KPIs derivados no relatório em vez de
renderizá-los com cara certificada.
