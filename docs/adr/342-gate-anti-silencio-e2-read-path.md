---
id: ADR-342
type: adr
title: "Gate anti-silêncio no E2: escalação de extração vazia/parcial com contrato de read-path"
status: Decidido
date: "2026-07-22"
phase: A38.l3
amended_at: ["2026-07-23"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
---

# ADR-342 — Gate anti-silêncio no E2 (escalação + read-path)

**Status:** Decidido (A38.l3) · **Data:** 2026-07-22 · **Lane:** [[A38.l3]] (P0)

> **Emenda 2026-07-23 ([[A38.l14]]):** a exceção de dormência do §Decisão item 1
> ("nota explícita do parser") era substring-match em `notas` e uma nota parcial
> de mês vazio a derrotava (silenciava extrato com conteúdo). Reescrita para
> **observação estruturada + veredito no gate** (`raw_rows_detected`). Ver
> §Emenda 2026-07-23.
>
> **Emenda 2026-07-23 ([[A38.l12]]):** o contrato de escalação cobre também
> **posição de investimento** (CDB) — Σ posições ≠ total declarado escala
> (`extract.investment_sum_mismatch`). Ver §Emenda 2026-07-23 (A38.l12).
>
> **Emenda 2026-07-23 (checksums E2 — fatura + escopo de investimento):**
> especifica o checksum de **fatura** (Σ transações do escopo == `total_compras`,
> **nunca** `saldo_atual`) como opt-in por parser (`total_lancamentos_conferivel`),
> WARN-first; e estende o checksum de investimento a CDB XLSX/HTML-XLS com o total
> **de escopo igual** ao das linhas (soma em int cents, ADR-090). Ver §Emenda
> 2026-07-23 (checksums E2).

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

## Emenda 2026-07-23 ([[A38.l14]]) — dormência por observação, não por nota

A certificação do workspace 5@5.com achou o buraco: a exceção de dormência do
§Decisão item 1 era `"sem movimentação" in nota` (`validation.py`), e o
`parse_c6bank` emitia essa string descrevendo **meses parciais vazios** de um
extrato C6 Global com 56–199 linhas reais → o gate silenciava o extrato
inteiro. O parser emitia uma **conclusão** e o gate acreditava — a mesma classe
de erro que este gate existe para matar.

**Correção (senior-cto decide; data-engineer + financial-planner):**

- O §Decisão item 1 passa a ler: *"Exceção de dormência (não escala) só quando
  0 tx **e** o parser observou 0 linhas-candidatas (`raw_rows_detected == 0`),
  corroborada por saldo sem mudança onde `conservacao_verificavel`."*
- Parser reporta `raw_rows_detected: int` — **observação** (linhas com data +
  valor, excl. saldo) que o gate transforma em **veredito**, espelhando o
  padrão `conservacao_verificavel` (§Decisão item 2). Rejeitadas: flag
  `conta_dormant` (conclusão frágil, reabre o buraco na próxima variação) e
  gate inferir por saldo (`saldo_ini==saldo_fim` falha em saldo derivado/Wise).
- **Fail-safe:** parser que não reporta (`None`) ⇒ escala; `raw_rows_detected
  > 0` com 0 tx ⇒ escala (viu linhas, converteu zero). Só `== 0` não escala.
- O gate **para de ler `notas`** para decisão de dormência (grep-gate impede
  regressão). A nota "N meses sem movimentação" sobrevive como telemetria.
- **Saldo ≠ fluxo:** dormência é silêncio de *fluxo*, nunca suprime *posição* —
  conta dormante genuína preserva `saldo_final` (bucket cambial + dolarização).
- `raw_rows_detected` declarado no `e2_extract.schema.json` (drift-detection em
  strict). Universo migrado = parsers line-based com dormência legítima
  (c6bank, wise, bankofamerica, santander_conta); XLS/CSV sem reporte
  over-escalam (direção segura) até wiring próprio.

## Emenda 2026-07-23 ([[A38.l12]]) — checksum de posição de investimento

O contrato de escalação passa a cobrir **posição de investimento** (CDB), não só
transações. Os parsers determinísticos de CDB em PDF ([[A38.l12]]:
`parse_itau_cdb_pdf`, `parse_santander_cdb_pdf`) emitem `posicoes` +
`tipo="cdbresumo"` e escalam (`requires_llm_fallback`) quando:

- **0 posições** com conteúdo ⇒ `extract.empty_result`;
- **Σ `posicoes.valor_atual` ≠ total declarado** no documento (cents, tolerância
  zero) ⇒ `extract.investment_sum_mismatch` (código novo no enum
  `ReviewReasonCode` + `review_reason.schema.json`).

É o análogo do gate de conservação (§Decisão item 2) para posição: o documento
declara um total (Santander "CDB Valor total"; Itaú "SALDO FINAL") e a soma das
posições extraídas tem de fechar com ele, senão houve perda parcial silenciosa.

## Emenda 2026-07-23 (checksums E2) — fatura por `total_compras` + escopo de investimento

Refina o contrato de escalação por divergência (§Decisão item 1, "`total_fatura`
divergente do Σ lançamentos") que estava subespecificado. O co-design
(data-engineer + financial-planner) provou que a implementação ingênua fura em
duas direções — falso-fire em fatura correta e falso-pass em total derivado.

**Fatura — checksum contra `total_compras`, nunca `saldo_atual`.** "Total desta
fatura"/`saldo_atual` = `saldo_anterior − pagamentos + Σcompras + encargos/IOF/
anuidade`; para uma fatura **corretamente** parseada `Σtx ≠ saldo_atual` é o
**esperado** (rollover e encargos não são linhas de transação). Comparar contra
`saldo_atual` escalaria quase toda fatura correta. O alvo verdadeiro é o
**subtotal de lançamentos-do-período declarado no doc** ("Lançamentos atuais" /
"Total Despesas no Brasil" = `total_compras`), reconciliado contra a **Σ do
subconjunto de tx de mesmo escopo** (mesma moeda, mesma inclusão de encargos).

- **Opt-in por parser** (análogo a `conservacao_verificavel`): o parser declara
  `total_lancamentos_conferivel = {valor_cents: int, escopo: str}` **só** quando
  leu um subtotal do doc cujo escopo casa exatamente com o subconjunto de tx que
  emite. Sem o sinal ⇒ sem checksum (não é falha).
- **Gate:** `Σ(tx do escopo) == valor_cents` em **int cents, tolerância zero**.
  Divergência ⇒ `extract.fatura_total_mismatch` (código novo no enum
  `ReviewReasonCode` + `review_reason.schema.json`).
- **WARN-first:** o gate emite `warn_reasons` (telemetria), **não** escala, até o
  corpus dogfood provar zero falso-fire por parser; flip HARD por parser
  (§Consequências, rollout por banco). Caminhos que derivam `total_compras` de
  Σtx (tautológicos) **não** setam o sinal.
- **Proibido** comparar contra `saldo_atual`/"Total desta fatura" — documentado
  como armadilha no gate.

**Investimento — escopo do total importa; soma em int cents.** O checksum de
posição (Emenda l12) estende-se a CDB XLSX (`parse_santander_cdb`, total = "Valor
Total" bruto) e HTML-XLS (`parse_itau_cdb_html_xls`, total =
`resumo.saldo_bruto_final`, **não** o SALDO FINAL líquido). O total tem de ter
**escopo igual** ao das linhas (bruto vs bruto); total de conta agregado (inclui
saldos não itemizados) fica em WARN, não HARD. A soma passa a acumular **int
cents por posição** (`Σ round(valor*100)`), não float (ADR-090 — evita drift que
dispara falso-fire com muitas posições). Posição única Itaú PDF (valor = SALDO
FINAL = o próprio total) permanece **sem** sum-checksum (degenerada; já tem o
gate de 0-posição).

## Alternativas rejeitadas

- **`needs_review` direto sem passar pelo E2-llm:** joga fora recuperação
  automática que já funciona (o LLM lê texto completo) e regride docs que o
  fallback atende hoje.
- **Tolerância monetária no gate (ex.: R$ 10):** reabre a porta do silêncio —
  uma transação perdida abaixo da tolerância volta a passar; zero em cents
  onde a semântica fecha, no-op onde não fecha.
- **Backfill dedicado de parciais:** overkill para blast radius dogfood;
  full re-run resolve e já é exigido pela correção do parser.
