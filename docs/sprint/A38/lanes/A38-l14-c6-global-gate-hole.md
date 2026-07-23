---
id: A38.l14
type: lane
title: "Buraco no gate anti-silêncio: nota parcial 'sem movimentação' silencia extrato com conteúdo"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1027
priority: P0
branch_slug: a38-l14-gate-dormancia-observavel
adrs: ["[[ADR-342]]"]
depends_on: ["[[A38.l1]]", "[[A38.l3]]"]
tags:
  - type/lane
  - sprint/a38
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/dados
---

# A38.l14 — `gate-dormancia-observavel` (certificação do workspace 5@5.com, 2026-07-23)

## Problema (certificação empírica 2026-07-23, workspace dogfood inteiro)

A certificação do workspace 5@5.com (160 docs) revelou um **buraco no gate
anti-silêncio da [[ADR-342]]** (recém-mergeado na [[A38.l3]]): a exceção de
dormência ("0 tx + saldo + nota explícita do parser ⇒ não escala", ADR-342
§Decisão item 1) é implementada como **substring-match em texto livre** de
`result["notas"]` — `"sem movimentação" in nota → is_dormant=True`
(`validation.py:79` no ramo CSV, `:107` no PDF).

O `parse_c6bank` emite a nota `"Sem lançamentos no período (N mês(es) sem
movimentação)"` (`c6bank.py:514`) descrevendo
**meses parciais vazios** de um extrato multi-mês que **tem 56–199 linhas
datadas reais**. O gate lê a nota, marca o extrato **inteiro** como dormante
e **não escala** → perda silenciosa. O parser emite uma **conclusão** ("sem
movimentação") cedo demais e o gate acredita — a mesma classe de erro que a
[[A38.l3]] existe para matar, agora dentro do próprio gate.

Vale para **qualquer** banco com nota parcial de mês vazio → é defeito de
contrato, não de um parser.

## Decisão do painel (senior-cto decide; data-engineer + financial-planner)

**Rejeitada a flag `conta_dormant`** (proposta inicial): é uma *conclusão* que
o gate confiaria — reabre o buraco na próxima variação de parser que a setar
com afobação (troca substring frágil por booleano frágil). Rejeitado também
**gate inferir sozinho** `saldo_ini==saldo_fim ∧ n_tx==0`: falha nos bancos de
saldo **derivado** (Wise não seta `saldo_inicial`; ADR-342 §2 já marcou isso)
— uma falha total de parse fica idêntica a dormência.

**Decisão: observação estruturada + veredito no gate** (espelha o padrão
`conservacao_verificavel` da própria ADR-342 — parser atesta **observação**,
gate detém a **política**):

- Parser reporta `raw_rows_detected: int` — linhas que **tentou** converter
  (antes do filtro de data/valor), não linhas datadas quaisquer (evita
  falso-positivo de tabela de saldo diário). Cada parser line-based já itera
  essas linhas.
- **Veredito do gate:** `tx == 0 ∧ raw_rows_detected > 0 ⇒ escala`
  (fingerprint do C6 Global: viu linhas, converteu zero). Exceção de
  dormência (não escala) só quando `tx == 0 ∧ raw_rows_detected == 0`,
  corroborada por saldo sem mudança onde `conservacao_verificavel`.
  **Parser que não reporta ⇒ fail-safe: escala.**
- **Mata o substring-match nos dois ramos** (CSV `validation.py:79-80`,
  PDF `:107`). O gate para de ler `notas` para decisão de dormência.
- Escalação reusa `extract.empty_result` (é semanticamente um resultado
  vazio que deveria ter conteúdo) — **sem código novo, sem schema change no
  contrato de escalação**. `raw_rows_detected` é top-level aditivo; declarar
  como `{"type":"integer"}` no `e2_extract.schema.json` (1 linha) dá
  drift-detection em modo strict — atualizar `test_e2_schema_strict_corpus`.

**Saldo ≠ fluxo (financial-planner — invariante de domínio):** dormência é
sobre silêncio de *fluxo*, nunca suprime a *posição*. Conta dormante genuína
**não escala mas preserva `saldo_final`** → continua no bucket "Caixa + Moeda
Estrangeira", card de exposição cambial e meta de dolarização. Dormante =
"sem fluxo para analisar", nunca "sem ativo".

## Escopo (PR único — contrato + emenda)

- `raw_rows_detected` reportado pelos parsers line-based; os **3 emissores de
  nota de dormência legítima** (BoA `bankofamerica.py:106`, Santander
  `santander.py:207`, Wise `wise.py:154` — todos já sob guarda
  `not transacoes`) reportam `raw_rows_detected=0` honestamente no mesmo PR.
  Universo real = **3 parsers** (a certificação corrigiu a estimativa de ~11).
- Gate: substring → veredito por `raw_rows_detected`; ambos os ramos.
- **Emenda datada à [[ADR-342]]** (`## Emenda 2026-07-23` + `amended_at` +
  blockquote de sinal, protocolo ADR-027): §Decisão item 1 reescrito — "nota
  explícita do parser" → "veredito do gate: 0 tx + `raw_rows_detected`==0 +
  saldo sem mudança onde verificável". Commit **separado** do código
  (docs-first).
- A nota C6 "N meses sem movimentação" **sobrevive como telemetria** (info
  útil), só perde o papel de sinal de controle.

## Critério de aceite

- Matriz de regressão do gate: (a) 0 tx + `raw_rows>0` + conteúdo ⇒ **escala**
  (fingerprint C6 Global, **sem tocar o parser**); (b) 0 tx + `raw_rows==0` +
  saldo estável ⇒ **não escala** (BoA/Santander/Wise dormentes, agora via
  observação); (c) nota parcial "N mês(es) sem movimentação" + `raw_rows>0` ⇒
  **escala** (o incidente); (d) Wise falha derivada (linhas-candidatas, valores
  None) ⇒ **escala** (fecha o buraco de saldo derivado).
- Dormente genuíno **preserva `saldo_final`** no artefato (teste).
- Grep-gate: nenhuma leitura de `notas` como predicado de dormência em
  `validation.py` (teste que falha se `"sem movimenta"`/`"sem lançamento"`
  reaparecer como controle).
- Corpus local (harness [[A38.l1]]): os ~10 C6 Global saem de "0-tx dormante
  silencioso" para **escalação explícita** (a cobertura vem na [[A38.l15]]);
  zero regressão nos parsers que já funcionam (KR-E).
- `raw_rows_detected` no corpus strict; emenda ADR-342 mergeada no PR.

## Risco

Baixo-médio: contrato + 3 parsers reportando um int que já computam. Alta
alavancagem — **este PR sozinho defusa a perda silenciosa do C6 Global**
(vira escalação honesta ao E2-llm/needs_review) sem escrever o parser Global.
É a tese da ADR-342 se cumprindo: corretude antes de cobertura.
