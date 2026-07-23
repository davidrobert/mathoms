---
id: ADR-342
type: adr
title: "Gate anti-silêncio no E2: escalação de extração vazia/parcial com contrato de read-path"
status: Decidido
date: "2026-07-22"
phase: A38.l3
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
---

# ADR-342 — Gate anti-silêncio no E2 (escalação + read-path)

**Status:** Decidido (A38.l3) · **Data:** 2026-07-22 · **Lane:** [[A38.l3]] (P0)

## Contexto

A certificação de parse de 2026-07-22 ([[A38]]) provou que o E2 aceita
extração vazia ou parcial como artefato válido: `validate_extrato_result`
apenas **anota** "0 transações" em `notas` e `validate_fatura_result` seta
`parse_quality` sem escalar — o artefato entra no `DBArtifactStore` e o
pipeline consome como verdade. Casos reais: consolidado Santander com 0 tx
"ok"; `parse_itau` capturando ~50% das linhas do layout 2026 com conservação
de saldo estourada em silêncio. Perda silenciosa de dados corrompe fluxo,
patrimônio e todos os KPIs derivados sem nenhum sinal ao usuário.

O painel do sprint (data-engineer) demonstrou que **flippar
`requires_llm_fallback` no validador não basta**: os stages E2 são
workspace-scoped no store (`list_keys`/`read` fazem fallback para runs
anteriores), o pickup do E2-llm decide "processado" por mera existência de
key, e o dedup do E3 dá precedência a `extract_statements` — um artefato
**parcial de run anterior** ressuscita e derrota a escalação.

## Decisão

1. **Contrato de escalação único (extrato E fatura):**
   - Extrato: 0 tx com texto substancial, ou conservação global quebrada
     (`|saldo_inicial + Σtx − saldo_final| > 0` em cents) ⇒
     `requires_llm_fallback=True` (E2-llm one-shot); se o E2-llm também não
     extrair ⇒ `needs_review` no Document. Dois passos sempre — o E2-llm lê
     texto completo e recupera docs que a detecção de tabela perde.
   - Fatura: 0 lançamentos, ou `total_fatura` ausente/divergente do
     Σ lançamentos ⇒ mesmo caminho.
   - Moeda indeterminada ⇒ escala; parser nunca assume BRL como default
     silencioso.
   - Exceção: extrato sem movimentação (0 tx + saldo presente + nota
     explícita do parser) não escala.
2. **Gate de conservação só onde o saldo é observado.** No-op quando saldo
   ausente, ambíguo ou **derivado** (Wise/Rico derivam
   `saldo_inicial = saldo_final − Σtx` — check tautológico). Allowlist por
   banco; conceito de saldo ambíguo escala com razão `saldo_nao_reconciliavel`,
   distinta de conservação quebrada. Forma per-dia é assert de fixture (dev),
   nunca gate de produção. Tolerância sempre zero em cents onde roda.
3. **Invariante de read-path:** por `(workspace, key)`, no máximo **um**
   artefato não-fallback vivo entre `extract_statements`/`extract_invoices`
   e `extract_with_llm`. Três mudanças-companheiras:
   a. escalação grava **stub superseding** (`requires_llm_fallback=True`,
      `transacoes: []`, razão estruturada) na key determinística do run
      atual — o parcial de run anterior é marcado superseded;
   b. pickup do E2-llm trata key cujo único artefato vivo é stub como
      **não-processada** (hoje checa só existência de key);
   c. dedup do E3 **não reivindica** key cujo artefato do stage é stub.
4. **Normalização de key única** entre writers determinístico e LLM (hoje
   `_artifact_key_for_file` ≠ `_e2_extract_stem` para filename com
   espaço/>80 chars ⇒ duplicação no E3).
5. **Telemetria sem schema change:** razão estruturada via
   `ReviewReason`/`ReviewReasonCode` (códigos novos, ex.:
   `extract.incomplete_conservation`, `extract.saldo_nao_reconciliavel`);
   flag e razão são top-level aditivos no artefato (`e2_extract` já é
   `additionalProperties: true` no top-level; nada entra em `$defs/transacao`).
6. **Rollout WARN→HARD por banco.** WARN global primeiro (emite razão e
   conta; não escala) → falso-positivo = 0 no corpus local + goldens →
   flip HARD por banco via allowlist. **Itaú só flippa HARD com [[A38.l2]]
   shipped** (senão todo extrato Itaú escala para o LLM).
7. **Cura de parciais já gravados:** full re-run por workspace dogfood
   (runbook); sem script de backfill — o re-run já é necessário pós-l2.

## Consequências

- Docs que hoje "passam" vazios entram em `needs_review` até
  [[A38.l2]]/[[A38.l4]]/[[A38.l8]] aterrissarem — decisão do sprint:
  corretude > cobertura (número parcial com cara de certo é o pior modo de
  falha; escalação é honesta e recuperável).
- Escalação tem custo LLM (tier premium), one-shot por doc, sem retry loop.
- **Follow-up explícito (fora de A38, candidato A39+):** propagação E2→E5 do
  estado de escalação — conta-período com input escalado deveria
  suprimir/badgear KPIs derivados no relatório em vez de renderizá-los com
  cara certificada. Sem isso, o artefato deixa de ser "ok" mas o relatório
  ainda renderiza derivados sobre base parcial.

## Alternativas rejeitadas

- **`needs_review` direto sem passar pelo E2-llm:** joga fora recuperação
  automática que já funciona (o LLM lê texto completo) e regride docs que o
  fallback atende hoje.
- **Tolerância monetária no gate (ex.: R$ 10):** reabre a porta do silêncio —
  uma transação perdida abaixo da tolerância volta a passar; zero em cents
  onde a semântica fecha, no-op onde não fecha.
- **Backfill dedicado de parciais:** overkill para blast radius dogfood;
  full re-run resolve e já é exigido pela correção do parser.
