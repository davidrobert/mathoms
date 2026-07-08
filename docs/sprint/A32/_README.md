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

## Gate l7 — resultado do re-run (2026-07-08)

Procedimento executado após merge de l1–l6 (worker celery reiniciado no
`main` atual; backup do DB em `_scratch/mathoms-pre-a32l7-gate.db`):

1. `dev/reextract_stale_e2_llm.py --created-before 2026-07-06 --execute`
   — 11 artifacts invalidados, 11 docs re-enfileirados, zero LLM.
2. **Run gate `70551e68`** (full, `skip_llm=false`): 18 stages
   completed; 10 docs re-extraídos sob contrato `1.4.0`
   (`prompt_version` consultável, ADR-311); o 11º
   (`c05bd7bd_bankofamerica`) passou a ser coberto pelo parser
   determinístico — zero pendência LLM.
3. **Run 2 `ebbba19c`** (KR4): zero re-extração E2-llm (idempotência
   ADR-080 intacta), zero stage falho.
4. Custo LLM total do gate ≈ US$ 2,6; julho fechou em US$ 14,20 do cap
   US$ 20 (ADR-173).

### Before/after por code

| Code | Baseline `d1732edd` (07/07) | Gate `70551e68` (08/07) | Run 2 `ebbba19c` |
|---|---|---|---|
| `extract.missing_required_field` | 11 | **0** | **0** |
| `dedup.sentinel_period` | 7 | **0** | **0** |
| `domain.anachronic_transaction` | 1 | **0** | **0** |
| `domain.balance_gap` | 30 | **0** | **0** |
| `domain.temporal_gap` | 9 | **0** | **0** |

Run independente do owner na manhã de 08/07 (`8df60139`, pré-gate,
artifacts stale lidos via fallback l2) também fechou com **zero
reasons** — confirmação independente dos fixes de leitura.

### Classificação 1-a-1 dos 39 warnings removidos (KR2)

**Zero gaps genuínos** — 39/39 falsos positivos, em 4 famílias:

- **F1 — fatura na cadeia de saldo** (ADR-310 §2, 11 itens):
  `balance_gap` santander `faturaunique` ×4 (202508/202509/202510/202604),
  c6bank `faturacarbon` ×5 (séries 2023/2025), links fatura↔extrato
  santander ×2 (`dfef4315`/`f41be9d6`).
- **F2 — tipos de conta fundidos na chave** (ADR-310 §1, 7 itens):
  bradesco poupança→CC (`351eda8d` balance + `cabaa2e6` temporal),
  c6bank extratoconta pares ×4 (`397f158e`/`9f432f82`/`4e11dead`/
  `87c77fc9`), c6bank temporal `4e11dead`.
- **F3 — cascata de docs dropados** (l1/l2, 8 itens): itaú
  extratoconta `balance_gap` ×4 + `temporal_gap` ×2 (buracos abertos
  pelos docs itaú `cdbdetalhes`/`investimentosposicao` dropados no
  baseline por mismatch de vocabulário); binance `2384a3c2` temporal.
- **F4 — período corrompido 2100/1899** (l3, 3 itens): c6bank
  `faturacarbon` `temporal_gap` ×3 — as faturas com `data_vencimento`
  clampada em 2100 abriam buracos gigantes na própria série (a série de
  faturas segue validada pelo `TemporalGapDetector` em cadeia própria).
- **+10 `balance_gap` não-individualizáveis** — o baseline persistiu só
  20/30 itens (cap `_ISSUE_CAP_PER_CODE=20`); os 10 truncados têm a
  mesma assinatura de cadeia `banco/-/BRL` e foram verificados por
  exaustão: o gate emite zero `balance_gap` em todas as cadeias.
- **Ressalva nomeada (anti-Goodhart, para triagem KR3):** o
  `temporal_gap` do rico (`95b3d36e`) era comparação entre dois
  agrupamentos com identidade de conta distinta (um dos extratos não
  tem número de conta extraído) — falso positivo sob a chave canônica.
  **Se** o owner confirmar que são a mesma conta, existe buraco genuíno
  abr–jun/2026 hoje não sinalizado (chave por número precisaria de
  fallback quando o número não extrai) → abrir issue.

### Conservação de sinal (manifesto)

- Diffs `dev/golden_diff.py` valor-a-valor em `_scratch/` (valores
  reais nunca commitados — padrão A28 `gf_dogfood_diff`):
  `golden_diff_a32l7.md` (baseline→gate: deltas refletem as correções —
  CDBs fora das transações, períodos de fatura corretos) e
  `golden_diff_morning_vs_gate.md` (manhã→gate: 120/194 deltas são
  `if_monte_carlo` — ruído de simulação; restante é recalibração da
  re-extração v1.4.0).
- **Contagens estruturais do E5 idênticas** manhã↔gate (15 posições
  31/12, 8 classes, 4 imóveis, 3 apólices, 86 itens de consumo, 8
  fontes de receita…) — nenhuma entidade financeira perdida ou criada.

### Status dos KRs

- **KR1 ✅** — 19 → 0 nos dois runs.
- **KR2 ✅** — 39 warnings classificados 1-a-1; zero genuínos; 1
  ressalva nomeada (rico) encaminhada à triagem.
- **KR4 ✅** — golden de paridade + teste de tombstone verdes em CI;
  segundo re-run consecutivo sem novos reasons de nenhum code coberto.
- **KR3 ⏳** — triagem do owner na tela pós-l6 pendente (única pendência
  da sprint).

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
