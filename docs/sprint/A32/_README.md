---
id: MOC-sprint-a32
type: moc
title: "Sprint A32 — Review de reconciliação confiável: falsos positivos zerados + lifecycle de artifact + a tela diz de quem é o erro"
aliases: ["A32", "Sprint A32"]
sprint_status: current
date: "2026-07-07"
theme: "review-trust"
---

# Sprint A32 — Review de reconciliação confiável

> **Status:** `current` (aberta 2026-07-07). Origem: dogfood do owner
> 2026-07-07 — a run `d1732edd` exibiu **18 errors + 31 warnings** na tela
> de review e o owner reportou "não confiei em nada do que aparece" +
> "interface muito ruim para o usuário final". Investigação em 2 frentes
> (código + dados reais do DB) confirmou: **100% dos 18 errors são defeito
> do produto** (parser/reader/skip-list), não dos documentos do owner — e
> a tela os apresentou como se fossem problema do dado do usuário.
> Co-design 2026-07-07: `senior-cto` + `data-engineer` +
> `financial-planner` + `product-designer` + `prompt-engineer` +
> `product-manager`; revisão de forma/priorização: `product-manager` +
> `information-architect`. ADRs canônicas: [[ADR-310]] (l4) e [[ADR-311]]
> (l5), ambas Proposto na abertura da sprint.

## Diagnóstico (resumo do dossiê 2026-07-07)

A run de 2026-07-07 é a **primeira pós-A28.l8** (PR #786) — as validações
que emitem esses reasons nasceram em 2026-07-06. Os problemas de dado são
antigos; a visibilidade é que é nova. Quatro causas raiz confirmadas:

1. **`extract.missing_required_field` (11×)** — artifacts E2-llm de
   mai/jun gravavam `instituicao`/`tipo_documento`; readers leem
   `banco`/`tipo` (`document.py:162`, `account_grouper.py:145`).
   Artifacts stale nunca são re-extraídos (`extract_with_llm.py:61-87`) e
   2 são órfãos de reclassificação. `documents.bank_code` está **correto**
   no DB para todos os 11.
2. **`dedup.sentinel_period` (7×, datas 2100/1899)** — parsers de fatura
   re-derivam período do filename com regex não-ancorada
   (`santander.py:522`, `c6bank.py:600`) que casa os primeiros 6 dígitos
   do prefixo sha256[:12] (ADR-084); `safe_date` clampa em [1900, 2100].
   `documents.period` está **correto** para os 7.
3. **`domain.anachronic_transaction` (1×)** — guard funcionou como
   projetado sobre input que não deveria estar na reconciliação (órfão
   `cdbdetalhes` furou a skip-list via mismatch `tipo`/`tipo_documento`).
4. **`domain.balance_gap` (21×) + `domain.temporal_gap` (9×)** — chave de
   conta sem `account_type` funde fatura+CC+poupança do mesmo banco numa
   cadeia (`reconciliation_validators.py:84-88`); ordenação com empate
   resolvido por ordem alfabética de hash; cascata dos docs pulados por
   1-2 abrindo buracos falsos nas sequências.

## Baseline (régua dos KRs — formalizada na l1)

| Code | Baseline 2026-07-07 |
|---|---|
| `extract.missing_required_field` | 11 errors |
| `dedup.sentinel_period` | 7 errors |
| `domain.anachronic_transaction` | 1 warning |
| `domain.balance_gap` | 30 warnings |
| `domain.temporal_gap` | 9 warnings |

> **Verificação l1 contra o DB (2026-07-07):** contagens conferidas contra
> `review_reasons.occurrence_count` da run `d1732edd`. `domain.balance_gap`
> corrigido de 21 → 30: a tela exibiu 21 entradas por causa do cap de
> exibição (`_ISSUE_CAP_PER_CODE = 20` em `backend/app/tasks/pipeline_task.py`
> + sentinela "e mais 10 ocorrencia(s)"); o total exato vive em
> `review_reasons`. Os demais codes batem 1:1 com a tela.

## Lanes

| Onda | Lane | Título | Prioridade | Status |
|---|---|---|---|---|
| 0 | [[A32.l1]] | Purga de artifacts E2-llm órfãos + snapshot baseline da run dogfood | P0 | shipped (#825) |
| 1 | [[A32.l2]] | Contrato E2-LLM: `tipo` no writer + fallback nos readers + golden de paridade derivado + gate strict CI-only | P0 | shipped (#826) |
| 1 | [[A32.l3]] | Parser de fatura: período do routing/DB, nunca re-derivado do filename inteiro | P0 | shipped (#823) |
| 2 | [[A32.l4]] | Chave canônica de conta na continuidade de saldo + ordenação determinística ([[ADR-310]]) | P1 | shipped (#829) |
| 2 | [[A32.l5]] | Lifecycle de artifact E2: tombstone na reclassificação + versão de extração consultável ([[ADR-311]]) | P1 | shipped (#837) |
| 3 | [[A32.l6]] | Review UX: identidade legível + selo de natureza + copy sem contradição + agrupamento por documento | P1 | shipped (#841/#843/#845) |
| 4 | [[A32.l7]] | Gate: re-run dogfood instrumentado + classificação genuíno-vs-falso + triagem do owner | P0 | open |

Dependências: l4 ← l2+l3 · l5 ← l1 · l6 ← l2..l5 · l7 ← l1..l6.
ADR-310 e ADR-311 abrem como Proposto **no kickoff** (docs-only), em
paralelo à onda 1 — a política P0/P1 exige ADR antes do PR de impl, não
antes de tudo.

## KR

- **KR1** — Re-run da run dogfood `d1732edd` pós-ondas 0-2: os **19
  errors/warnings de causa-produto zeram** (11 `missing_required_field`
  → 0 · 7 `sentinel_period` → 0 · 1 `anachronic_transaction` → 0),
  medido contra o baseline acima.
- **KR2** — `balance_gap`/`temporal_gap` caem para **apenas gaps
  genuínos**, com manifesto `dev/golden_diff.py` valor-a-valor (padrão
  A23.l2) provando que cada delta removido é falso positivo, não perda de
  sinal. Os 9 `temporal_gap` são classificados **1 a 1** (genuíno vs
  cascata) — nunca removidos em bloco.
- **KR3 (triagem dogfood do owner — sinal de confiança, não métrica
  estatística; n=1)** — na tela pós-l6: ≥90% dos cards com natureza e
  ação compreendidas sem abrir "Detalhes técnicos"; distinção "meu dado
  errado vs. produto leu errado" correta em 100%; zero hash sha256 cru
  visível no corpo de card. Cards não compreendidos viram **issues
  nomeadas** (anti-Goodhart), não só percentual.
- **KR4** — Anti-recorrência: golden de paridade writer↔schema↔reader
  **derivado** (não hardcoded) verde em CI; teste de tombstone na
  reclassificação verde; **segundo re-run consecutivo** no dogfood sem
  novos reasons dos codes cobertos por l2/l3/l4 (e por l5, se a lane
  entregar a versão consultável — ver cláusula de recuo na l5).

## Decisões do owner (2026-07-07)

- **Q1 — 11 artifacts stale:** híbrido. Re-run E3 determinístico (grátis)
  no gate **e** re-extração LLM completa dos 11 após l2 (contrato novo),
  via script dirigido da l5. Custo LLM aceito pelo owner (cap ADR-173).
- **Q2 — schema strict:** **CI-only nesta sprint** (gate de teste sobre
  corpus sintético na l2); runtime segue `warn`. Nota do painel: strict
  não teria pego o P1 — writer LLM valida contra `e2_llm_artifact.schema.json`.
- **Q3 — ações por card:** MVP `ver documento` + `dispensar` na l6;
  endpoint "reprocessar documento" fica para a sprint seguinte (l6
  entrega só a spec do contrato).
- **Q4 — warnings não-bloqueantes:** **selo de natureza** na review
  principal ("provável leitura nossa" vs "confira seu documento"), sem
  aba separada. Financial-planner vetou promovê-los a bloqueantes.

## Fora de escopo (Later, nomeado)

- Flip global `schema_validation` warn→strict em runtime — observar
  dogfood limpo primeiro; CI-only nesta sprint (Q2).
- Lineage forward/reverso, `SourceAdapter`/`SourceRef` e filtro por
  `SourceRef.kind` — plano [[PLAN-data-lineage|DATA_LINEAGE]] (ADR-278–281);
  l4/l5 declaram fronteira e alimentam o plano.
- Re-extração retroativa fleet-wide de outros workspaces — só o dogfood
  nesta sprint; demais sob demanda via script dirigido da l5.
- Endpoint "reprocessar documento" UX-triggerable + form tipado de
  correção + micro-estados pós-ação — sprint seguinte de review UX.
- `E2Artifact` BaseModel com aliases PT-BR substituindo o dict
  hand-rolled de `_output_to_e2_json` — follow-up com ADR própria.
- Janela anacrônica por doc_type + balde de exclusões quantificado no
  relatório — follow-up com `financial-planner`; nem estreitar nem
  alargar o global de 180d nesta sprint.
- Re-extração automática em bump de `PROMPT_VERSION` — l5 entrega só o
  mecanismo dirigido; política automática é decisão de custo do owner.
- Invariante própria de continuidade de fatura (fatura_n paga vs
  fatura_n+1 aberta) — produto futuro; nesta sprint fatura apenas sai da
  cadeia de conta.
