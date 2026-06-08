---
id: PLAN-data-lineage
type: plan
title: "Data Lineage fim-a-fim + Fonte plugável"
status: in_progress
created_at: 2026-06-02
last_review: 2026-06-02
sprint_origem: A23
sprint_atual: A23
sprints_envolvidas: [A23]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-278]]"
  - "[[ADR-279]]"
  - "[[ADR-280]]"
  - "[[ADR-281]]"
tags:
  - type/plan
  - status/draft
  - area/pipeline
  - area/data-lineage
---

# Data Lineage fim-a-fim + Fonte plugável (Extract limpo)

> **Origem:** co-design 2026-06-02 (orquestrador + `senior-cto`, `data-engineer`,
> `product-designer`, `prompt-engineer`, `product-manager`, `information-architect`).
> Revisado por `senior-cto` + `data-engineer` sob corretude/completude/
> consistência/precisão — 8 blockers (B1–B8) consolidados como **gate F0**.
> Veredito: espinha sólida, sem redesenho; correções cirúrgicas no F0 ADR
> antes de abrir lanes.
>
> **Gate F0 fechado (A23.l1, 2026-06-03):** os 4 ADR ([[ADR-278]]–[[ADR-281]])
> estão **`Decidido`** com B1–B8 resolvidos textualmente (B4 como estratégia) +
> emenda [[ADR-146]]. Plano `in_progress`; lanes de implementação (F1+) conformam,
> não reabrem.
>
> **Progresso Onda 1 (F1):** `A23.l2` substrato de golden ✅ (#552, fecha DE-005) ·
> `A23.l3` `dl-f1-natural-key` B3/B4 ✅ (#553). **Restam:** `dl-f1-data-source`,
> `dl-f1-amount-decimal` (B5), `dl-f1-extract-check`, `dl-f1-migration-runbook` (G-e)
> — prompt de orquestração pronto em
> [agent_prompts/orchestrator_a23_onda1_lanes.md](../../agent_prompts/orchestrator_a23_onda1_lanes.md).
> Dívida D6 da l3 tem decisão em [[ADR-282]] (Proposto); implementação no passo 2 de B4.

## Context

Dois problemas, uma raiz comum.

1. **Arqueologia de números.** Validar um número do relatório ou caçar um erro
   hoje exige abrir stage por stage (E0→E7) reconstruindo de onde veio o número.
   Os bugs caros de "número errado" (R$ 811k de patrimônio inflado — dedup;
   [[ADR-271]]/[[ADR-246]]/[[ADR-255]]) são os mais difíceis de rastrear.
   Queremos **lineage automático**: todo número de alto valor consultável até a
   origem (documento/fonte) + transformações (stages/regras).
2. **Fonte acoplada.** A extração de arquivos (PDF/CSV) está entrelaçada com
   lógica de transformação. Em breve integraremos fontes que já entregam dados
   estruturados (Open Finance / agregador / API de corretora / IRPF), que devem
   **substituir ou coexistir** com os arquivos sem reescrever nada downstream.
3. **Legibilidade por LLM.** O lineage não é só para humanos lerem na UI/CLI —
   é **input de 1ª classe para um LLM** (agente de debug dedicado OU o Claude
   Code no repo) saltar de "número errado" → "transformação que o gerou" →
   "função exata a corrigir". Impõe: formato token-eficiente e citável, bridge
   nó→código refactor-safe, sinais de anomalia pré-computados, e diff de
   regressão determinístico.

**A raiz comum:** a *folha* do lineage é a **referência de fonte** (`SourceRef`).
Generalizar a origem de "documento" para "fonte plugável" resolve a opcionalidade
de fonte **e** dá ao lineage uma folha estável. Por isso os dois são **um
plano/família-de-ADR acoplada** — migrar o schema de origem uma vez só.

### O reframe central
**Não adotar um *stage* "Load".** O pipeline já é hexagonal na fonte:
`N adapters → 1 contrato (artefato E2) → pipeline agnóstico`. O
`reconcile_transactions` já lê 3 fontes com um único shape. Um stage Load novo só
adicionaria um nó no `FULL_ORDER` e reabriria "dedup é Load ou Transform?"
(fechado pela [[ADR-276]]). **Adotamos a *disciplina* E-L-T** (aterrissar
registros canônicos; tudo específico-de-fonte no adapter; transforms
source-agnostic e replayáveis) via **`SourceAdapter` (porta) → contrato canônico
→ downstream inalterado**. Um feed Open Finance vira *mais um adapter* escrevendo
o mesmo contrato.

### O que já existe (reusar, não inventar)
- **[[ADR-045]] "Data lineage via tooltip" (Decidido, F6)**: tooltip de UI com
  fonte/banco/data/método; drill-down explicitamente adiado "para o futuro".
  **Este projeto é esse futuro** — a [[ADR-281]] (debug substrate) estende/supersede
  a [[ADR-045]]; o tooltip vira a ponta visível do substrato (renderer humano).
- **K4 hash** (`compute_transaction_hash`, `pipeline/domain/services/_tx_identity.py:100`,
  [[ADR-255]]): chave natural source-independent. Hoje subproduto interno do
  dedup E3. **Promover a campo de contrato** — ⚠️ hoje usa `abs(valor)` sem
  `moeda`/`direction` e ingere `float` (Blocker B3).
- **rules-as-code ([[ADR-143]])**: cada regra = módulo enforcer + docstring +
  ADR. O `rule_ref` formaliza o vínculo via **dict literal eager**
  (`lineage_registry.py`) verificado por gate — não decorator side-effect (B2).
- **`real_estate.componentes_calculo`** (`e5_analysis.schema.json`, [[ADR-216]] D9):
  já é lineage field-level em produção — template a generalizar.
- **`report_lineage.py`**: `lineage_payload` coarse (run → documentos).
  Field-level aninha sob ele.
- **`$defs/evidencia_path`** (`parecer_planejador.schema.json`) + tool
  `get_e5_jsonpath` + whitelist E5: gancho E5→E6 já existe (opcional). É *fechar
  a malha de verificação*, não construir.
- Rastro E0→E3 já existe (`fontes`, `arquivo_origem`, `source_document`, `_source`).

### Critério de corte Extract | Transform (verificável)
> **Extração não pode produzir um campo cujo valor dependa de outro registro, de
> config de domínio do workspace, ou de uma decisão metodológica.** Extração =
> função pura de *uma fonte → seus próprios registros*.

| Caso | file:line | Veredito |
|---|---|---|
| Classificação de tipo de transação (`tipo_lancamento`) | `scripts/e2/banks/c6bank.py:72`, `caixa.py:71` | **Vaza → mover p/ Transform** |
| Normalização de conta (`numero_conta_norm`, [[ADR-226]]) | `scripts/e2/common.py:393` | **Vaza → emitir raw, normalizar na camada canônica/Transform** |
| Hint de categoria ([[ADR-242]]) | `pipeline/llm/schemas/e2_llm_extract.py:18` | **Reclassificar como sinal de fonte** (`origin=llm_extract`) — NÃO deletar (evita 2ª passada LLM) |
| Consolidação + dedup baseline (E1.5c, [[ADR-246]]/[[ADR-271]]) | `scripts/e15_consolidate.py` | **Já é Transform** — rotular o stage + travar no check |
| Classificação de documento (E0) | `document_classification.py:203` | **Extração** (só depende do arquivo) — fica |

---

## Arquitetura (camadas)

### A — Porta de fonte + contrato canônico (`SourceAdapter` / `SourceRef`) → [[ADR-278]]
- **`SourceAdapter` Protocol** + **`SourceRef`** (discriminated union) em
  `pipeline/domain/ports/source.py` *(novo)*: `{kind:"document", document_id}` |
  `{kind:"feed", provider, account_id, sync_id}`.
- **Contrato canônico = artefato E2 endurecido** (não criar `CanonicalLedgerRecord`
  paralelo): `e2_extract.schema.json` v3 com `natural_key` (K4, com `hash_version`)
  **obrigatório** (migração 2-passos nullable→obrigatório se nem todo produtor E2
  emite K4 — B3/B4), `amount` decimal string ([[ADR-090]], ao lado de `valor` na
  janela de migração — B5), `source_ref`, `direction`. Posição de investimento =
  **2º contrato canônico** (chave `tipo|instituicao|descricao_norm`, [[ADR-271]]).
- **Tabela `data_source`** (folha de lineage generalizada — **sem FK polimórfica**):
  `(id, workspace_id FK CASCADE, kind, institution_code, external_account_ref,
  display_name, created_at)`, unique `(workspace_id, kind, institution_code,
  external_account_ref)`. `pipeline_artifacts.data_source_id` nullable FK
  **`ON DELETE SET NULL`**; `document_id` **permanece**.
- **Adapters concretos:** parsers `scripts/e2/banks/*` (file). Cliente Open Finance
  em `backend/app/services/` (fala HTTP/DB — boundary proíbe em `pipeline/`).
  **Adapter de feed real DEFERIDO** (YAGNI; gatilho `build-vs-buy`).
- **Raw landing só para fontes voláteis (API)** (retenção ≥5 anos). Arquivos: o
  `Document` já é o raw — não duplicar.

### B — Extração pura (de-leak) → [[ADR-280]]
- Mover `tipo_lancamento` (regex) dos parsers para Transform. **Auditar
  consumidores antes** (pode ser load-bearing).
- `numero_conta` raw no extract; `numero_conta_norm` na camada canônica/Transform.
- Hint de categoria: manter emissão como `{value, origin:"llm_extract", confidence}`
  (sinal), E4 decide. (Já perto da [[ADR-242]] §D4.)
- Baseline: garantir `extract_baseline`/`extract_irpf_full` puros; rotular
  `consolidate_baseline` (E1.5c) **Transform** + travar no check.
- **Enforcement:** `dev/check_extract_no_domain_imports.py` *(novo)* — extração
  ∌ imports de `category_template`/`*_dedup`/`ConfigStore`. `validate_full_order`
  estendido. Hook pós-write garante `source_ref` válido.

### C — Lineage field-level (declarativo, inline) → [[ADR-279]]
Bloco `_lineage` no topo de `content_json` (cabe via `additionalProperties:true`).
É o **grafo armazenado**; dois renderers projetam dele (humano = §F; LLM = §G).
**Rejeitado `TracedValue`** (reescreveria a aritmética float, arrisca
[[ADR-090]]/[[ADR-111]]). Cada calculador *declara* inputs por campo:

```jsonc
"_lineage": {
  "lineage_version": "1.0",
  "fields": {
    "patrimonio.liquido": {
      "value": "0.00",             // Decimal string; gate compara em cents int
      "label": "Patrimônio líquido",
      "transform": "soma 7 categorias menos dívidas",
      "rule_ref": {"adr":"ADR-145", "ref":"pipeline/domain/services/patrimonio_calculator.py:PatrimonioCalculator.calculate"},
      "edge_type": "formula",      // formula|aggregation|passthrough|override|coalesce|source_leaf|external_feed
      "signals": {"range_check":"ok", "needs_review":false},
      "member_hashes": ["…"],      // K4 sobreviventes pós-dedup; ancorados ao run_id (B8)
      "inputs": [ {"stage":"E4","artifact_key":"patrimonio","field":"composicao.imoveis_investimento"} ]
    }
  }
}
```
Invariantes: zero timestamp/UUID; `inputs` sorted; `value` espelhado (gate em
**cents int**, [[ADR-090]]); ref de input `{stage, artifact_key, field}` (stage
descritivo via `resolve_stage_name`); folha = `data_source_id`/`SourceRef[]`
(lista, multi-fonte — §Q1). `rule_ref` derivado de **dict literal**
(`lineage_registry.py`, B2). Agregados de decisão (~5) carregam **`member_hashes`**
(K4 sobreviventes pós-dedup, ancorados ao `run_id`, §Q3) → resolver faz lookup
puro no mesmo run, gate `check_lineage_sum`. Ataca os 2 saltos cegos: **E4→E5** e
**E5→E6**.

### D — Resolver + índice reverso → [[ADR-279]]
- **`LineageResolver`** (`pipeline/domain/services/lineage_resolver.py`, novo):
  forward, read-only, **stateless** ([[ADR-111]]). `resolve(stage,key,field) →
  tree` até a fonte. Nós `dangling`/`no_lineage`, nunca exceção.
- **Tabela `artifact_lineage_edge`** (derivada/rebuildável via stage terminal
  `materialize_lineage`). DDL: `(id, workspace_id, run_id, src_stage, src_key,
  src_field, dst_stage, dst_key, dst_field, edge_type, rule_ref TEXT,
  source_document_id, data_source_id, winner BOOL)` — `rule_ref` é **coluna TEXT**.
  Índices `(workspace_id, rule_ref)` e `(workspace_id, source_document_id)`.
  **Retenção (B6):** `materialize_lineage` faz `DELETE` cross-run (mantém só
  último(s) run(s)) — [[ADR-241]] já matou o GC implícito. Field-level default;
  row-level **lazy**.

### E — E5→E6 (parecer LLM): citação verificada → [[ADR-279]]
`evidencia_path` **condicional-obrigatório** no validator Pydantic — **não no
JSON Schema** (decisão consciente: a condição "cita número na prosa" exige
semântica que JSON Schema não expressa). Guardrail híbrido de 3 camadas: (1) path
∈ whitelist E5; (2) resolve não-nulo; (3) **match número↔valor**; falha →
`needs_review`. Path de origem exposto no exec context destilado.

### F — Produto: drill-down "por que esse número?"
Progressive disclosure de 3 níveis, régua COPY_GUIDELINES §6.3 (zero jargão de
pipeline na UI cliente):
- **N1 selo**: underline pontilhado no `<MonetaryValue/>` + `aria-label`.
- **N2 popover** "Como chegamos a esse número": 4 verbos 1ª pessoa + contagens —
  **Li** → **Conferi** (dedup como trabalho a favor) → **Classifiquei** →
  **Calculei**.
- **N3 drawer** (fast-follow): fontes (nome amigável + período + data), needs_review
  com badge âmbar. Teto — sem árvore técnica crua.
- Estender `<MonetaryValue/>` com prop opcional `provenance?`. ~6 elegíveis em
  `report_layout.yaml`. Score reusa `ScoreBreakdownTable`.

### G — Substrato de debug para LLM → [[ADR-281]]
- **Bridge nó→código refactor-safe**: **dict literal eager**
  `pipeline/domain/lineage_registry.py` — não decorator import-side-effect
  (banido CLAUDE.md §Dependências; não cabe [[ADR-111]] (a), B2). Refactor-safe
  vem do gate `dev/check_lineage_refs.py` (resolve `module:qualname` por import
  real + ADR existe). Registrar em `STATELESS_AUDIT.md §2`.
- **Renderer LLM**: trace **linearizada** (passos numerados raiz→folha, inputs
  como `#N`, ~30-60 tok/nó). Teto ~1.5k tokens inline; colapsa subárvores sem
  anomalia; **anomaly-first ordering**.
- **`lineage_diff(tree_a, tree_b)`** (puro/stateless): só nós mudados +
  **`first-divergent-leaf`** + propagação anotada.
- **Tools**: `explain_number(field, depth)` · `expand_node` · `trace_source`. Cap
  `max_expand_iterations:6`; whitelist de `field`; audit em `_meta.tool_trace`.
- **Superfície**: core = função de domínio que **Claude Code consome sobre
  goldens** (dia 1). Prod = **MCP read-only no console interno** ([[ADR-116]],
  `workspace_id` obrigatório, **zero mutação** — correção via PR) — **fase
  posterior**.
- **Eval**: injeção determinística de bug (20-30 casos PII-sintético). Métricas:
  `localization_accuracy@node ≥ 85%` (regressão >2% bloqueia), `tokens_to_localization`,
  `tool_iterations_p95`. Temp=0, seed/model pinados.

---

## Decisões das perguntas abertas (Q1–Q3)

### Q1 — Divergência cross-source · **valor divergente NUNCA colapsa silencioso**
- **K4 exact-match (idêntico ao centavo) → colapso silencioso** (sobrevivente
  alfabético por `artifact_key`, [[ADR-255]]).
- **Near-match** (descrição diverge; ou valor; ou data ±1 dia) → não funde
  automaticamente quando o eixo é valor.
- **Dois eixos de precedência** (como o bug R$ 811k nasce): **campo/enriquecimento**
  → estruturado > parseado (feed vence rótulo); **valor monetário** → fonte
  primária legal > conveniência (extrato oficial é a verdade contábil; feed NUNCA
  sobrescreve valor; divergência ≥ R$ 10k → `needs_review`).
- **Mecanismo:** `SourcePrecedencePolicy` value-object ([[ADR-276]] pattern).
  ⚠️ **B1:** `pick_winner` ([[ADR-146]]) desempata por `extracted_at` (timestamp,
  não-determinístico) → F0 substitui por `(tier, kind-priority, alfabético)`.
- **Registro:** `_lineage.signals` do sobrevivente + `DivergenceReviewEntry` +
  folha `SourceRef[]`.
- **Placement: E3** (decidido) — divergência cross-source é conflito factual *com*
  reconciliação de saldo. Separação por `SourceRef.kind`: E4 Camada A ([[ADR-255]])
  = overlap mesmo-kind; E3 = divergência cross-kind. **B7:** `SaldoContinuityValidator`
  filtra por `kind` (só série `document` vira saldo-âncora).

### Q2 — Ordem · **F2 (extração pura) ANTES de F3 (lineage). Consenso unânime.**
F3-sobre-sujo grava refs apontando para fronteira que F2 vai mover → refs órfãs
(ou gate verde-mas-errado) + 2 rebaselines. F2 primeiro = 1 rebaseline. Endurecer
contrato E2 acontece DENTRO de F2 (pré-requisito do `SourceAdapter`).

### Q3 — Granularidade · **member-set capturado na soma, NÃO replay.**
Calculador emite `member_hashes` (K4 que entraram na soma); resolver faz lookup
puro — sem replay-engine (replay sob drift de ruleset [[ADR-186]] é
não-determinístico). **B8:** ancorar lookup ao `run_id` do agregado (não
most-recent — [[ADR-241]] workspace-scoped); `member_hashes` = sobreviventes
pós-dedup. Gate `check_lineage_sum`: `Σ amount[h] == value` (cents int).

---

## Blockers de corretude — gate obrigatório no F0

As revisões `senior-cto` + `data-engineer` convergiram independentemente.
**Nenhuma lane abre antes do F0 resolver B1–B8.** Espinha sólida, sem redesenho.

| # | Blocker | Resolução decidida | ADR |
|---|---------|--------------------|-----|
| **B1** | `pick_winner` desempata por `extracted_at` (timestamp) → não-determinístico | Tie-break = `(tier, kind-priority, alfabético por artifact_key)` ([[ADR-255]]); muda E3 → rebaseline + emenda [[ADR-146]] | [[ADR-278]] + [[ADR-146]] |
| **B2** | `@lineage_rule` decorator = import-side-effect (banido); não cabe [[ADR-111]] (a) | **Dict literal eager** + gate `check_lineage_refs` (import real) | [[ADR-281]] |
| **B3** | K4 usa `abs(valor)` sem `moeda`/`direction` → colisão entrada/saída e BRL/USD | Incluir `moeda`+`direction` no hash, com `natural_key.hash_version` | [[ADR-278]] |
| **B4** | `natural_key` obrigatório não é aditivo se nem todo produtor E2 emite K4 | **Estratégia** decidida no F0 (2-passos nullable→obrigatório); inventário/execução validam em F1 (`dl-f1-natural-key`) | [[ADR-278]] |
| **B5** | Migração `valor`→`amount` incompleta | Inventário de leitores; gate `Decimal(amount)==Decimal(str(valor))`; `compute_transaction_hash` ingere `Decimal`/cents | [[ADR-278]] |
| **B6** | `artifact_lineage_edge` sem retenção ([[ADR-241]] matou GC) | `materialize_lineage` faz `DELETE` cross-run; janela = **último run por workspace (N=1)** | [[ADR-279]] |
| **B7** | Fusão cross-kind no E3 contamina `SaldoContinuityValidator` | Validator filtra por `SourceRef.kind`; feed reconcilia linha, não saldo-âncora | [[ADR-278]] |
| **B8** | `member_hashes` × [[ADR-241]] incremental: most-recent resolve hash errado | Resolver ancora ao `run_id`; `member_hashes` = sobreviventes pós-dedup | [[ADR-279]] |

> **[[ADR-280]]** (critério de corte Extract \| Transform) também é gate F0, mas
> entra por **critério de pureza**, não por blocker numerado — não há `B` que ela
> "resolva"; ela trava o de-leak da F2. **B4** fecha no F0 só como *estratégia*; o
> inventário de produtores E2 roda em F1 (por isso a aditividade de G1 é
> condicional — ver Verificação F1).

Detalhes de migration: `CREATE INDEX CONCURRENTLY` exige `autocommit_block`/
`postgresql_concurrently=True` (fora de transação Alembic); `_lineage` declarado
em `e5_analysis.schema.json` **antes/junto** do flip→strict (PLATFORM_REVIEW
W6-T01).

---

## Ondas, lanes e dependências (sprint A23)

Sequência base `F0 → F1 → F2 → F3` é serial (Q2). F4 paraleliza. F5/F6/F7 fast-follow.

```
F0(G0) ──► F1(G1) ──► F2-discovery(G2) ──► F2-slice1 ──► F3-skeleton(G3) ──► [F5 ∥ F6 ∥ F7]
                 └──► F4-evidencia-path ──────────────────┘ (paralelo, independente)
                                          F2-residual ─────┘ (paralelo a F3)
```

| Onda | Lane | P | Gate |
|------|------|---|------|
| **0 — Gate** | `A23.l1` F0 — 4 ADR `Proposto` ([[ADR-278]]/[[ADR-279]]/[[ADR-280]]/[[ADR-281]]) + emenda [[ADR-146]]. Resolve B1–B3,B5–B8 textualmente; B4 como estratégia (executa em F1) | P0 | **G0:** 4 ADR mergeados; B1–B3,B5–B8 com decisão textual + file:line; B4 com estratégia de migração; [[ADR-280]] (critério de corte) fechado |
| **1 — Contrato aditivo + substrato de golden** | **`dl-f1-golden-substrate`** (P0 · [[A23.l2]] ✅ #552 — `dev/golden_diff.py` valor-a-valor cents int + snapshot do view-model de `/reports/[id]/data` + invariantes de conservação; **fecha DE-005**; ANTES de F2 tocar golden) · `dl-f1-natural-key` (K4+moeda+direction+hash_version, B3/B4 · [[A23.l3]] ✅ #553; **passo 2 gated por [[ADR-282]]** — unificar identidade de `TransactionOverride` no v2 antes do flip de consumo E4, senão orfaniza override em massa) · `dl-f1-data-source` (tabela+coluna+SourceRef) · `dl-f1-amount-decimal` (B5) · `dl-f1-extract-check` · `dl-f1-migration-runbook` (G-e) — 4 restantes em [orchestrator_a23_onda1_lanes.md](../../agent_prompts/orchestrator_a23_onda1_lanes.md) | P0/P1 | **G1:** goldens E3/E4/E5 **+ snapshot do view-model + invariantes de conservação** verdes **sem rebaseline** (aditividade) |
| **2 — De-leak ∥ E5→E6** | `dl-f2-discovery` (gate, blast radius numérico) · `dl-f2-deleak-slice1` (+ **disciplina de rebaseline**: commit isolado + manifesto justificado + 2º revisor) · `dl-f2-deleak-residual` (∥) · `dl-f4-evidencia-path` (∥, independe de F2/F3) | P0/P1 | **G2:** discovery fechado; slice1 rebaselineado verde **com manifesto justificado por valor**; diff de dogfood (dado real, local) sem surpresa |
| **3 — Backbone (skeleton)** | `dl-f3-skeleton-patrimonio` (walking skeleton) · `dl-f3-skeleton-resto` (reserva/despesa/total investido) | P0/P1 | **G3:** ver abaixo |
| **4 — Fast-follow** | `dl-f5-reverso` · `dl-f6-produto-n1n2` · `dl-f7-debug-llm` | P1 | pós-G3 |

**Walking skeleton (G3, critério de "pronto" da 1ª janela):** equipe localiza a
origem do **patrimônio líquido** *sem abrir um único arquivo de stage*, via 1
comando CLI, num run canônico — `check_lineage_sum` prova `Σ amount[member_hashes]
== value` (cents int, incl. caso incremental B8 + tx colapsada por dedup),
`check_lineage_refs` resolve por import real, e rodar o mesmo run 2× produz
`_lineage` byte-idêntico.

**Deferido (YAGNI):** adapter Open Finance real · raw landing genérico · execução
real da `SourcePrecedencePolicy` (desenhada no F0, exercida só com feed; threshold
de materialidade pode passar por `financial-planner` na ativação) · MCP prod do
debug substrate + índice reverso por `rule_ref`.

## KRs

| # | Key Result | Baseline | Meta |
|---|---|---|---|
| **KR1** | `localization_accuracy@node` (suite de injeção de bug) | suite nasce em F7; proxy = 5 bugs históricos | **≥ 85%** (regressão >2% bloqueia) |
| **KR2** | Agregados de decisão com lineage fim-a-fim | 0/6 (só `componentes_calculo`) | **6/6** + `check_lineage_sum` verde |
| **KR3** | `tool_iterations_p95` p/ "número errado → função" | não-instrumentado; cravar tempo de arqueologia manual no kickoff | `tool_iterations_p95 ≤ 6`; inline ≤ 1.5k tokens |

KR mensurável na 1ª janela: **KR2 parcial (1/6 — patrimônio líquido)** + processo
("tempo de localização cai de E0→E5 manual para 1 comando CLI").

---

## Guard-rails de regressão

Consolidado da revisão multi-agente (`senior-cto` + `data-engineer` + `product-designer`
+ `sre-devops` + `product-manager`, 2026-06-03). **Reframe central:** o eixo é
**número vs. pixel**, não "quanto guard-rail". Um snapshot prova `novo ≠ velho`,
nunca `novo == correto` — quando se rebaselina de propósito (F2/F3), o golden vira
tautologia. Daí: **(a)** o número se protege com snapshot de *valor* (cents int)
+ invariantes de conservação que sobrevivem ao rebaseline; **(b)** o pixel é
secundário e flaky — visual snapshot **não** é gate de F2/F3 (não pega R$ 1.200.000
→ R$ 1.200.100, subpixel), só entra na F6 (UI nova).

| # | Guard-rail | P | Onde |
|---|---|---|---|
| **G-a** | Lane `dl-f1-golden-substrate`: `dev/golden_diff.py` (valor-a-valor, cents int, classifica `unchanged\|moved\|value_delta\|new\|removed`, comenta no PR) + snapshot do **view-model** de `/reports/[id]/data` (sintético, determinístico) + asserção de completude `monetary_fields ⊆ snapshot`. **Fecha DE-005.** | P0 | Onda 1, ANTES de F2 |
| **G-b** | Invariantes de conservação por balde (`patrimônio == Σ7categorias − dívidas`, `fluxo == Σreceitas − Σdespesas`, + `check_lineage_sum`) — a "segunda testemunha" que quebra sozinha se o rebaseline cimentar valor errado. | P0 | estende `test_e5_golden_execution` |
| **G-c** | Disciplina de rebaseline: `check_golden_rebaseline_isolation.py` (golden + código de produção no mesmo commit → falha) + manifesto justificando cada `value_delta` (file:line + ADR) + label `golden-rebaseline` + 2º revisor/CODEOWNERS. Goodhart-safe (justifica *por valor*). | P0 | critério de `dl-f2-deleak-slice1` + PR template |
| **G-d** | Snapshot textual de número no render (Vitest, todo PR): ~6 KPIs hero + 6 agregados KR2 com assertion de valor formatado pt-BR (pega "certo no pipeline, errado na tela"). | P0 | F3/F6 |
| **G-e** | Runbook `data_lineage_migrations.md` (4 migrations: `data_source`, `data_source_id`, `artifact_lineage_edge`, 2-fases `amount`/`natural_key`) com janela PITR + rollback por fase + asserção `CONCURRENTLY`/`autocommit_block` no `test_alembic_guardrails`. | P0 | F1 |
| **G-f** | Processo de dogfood: diff de números do relatório do workspace **real** do founder antes/depois de PRs F2/F3 — **local/gitignored** (PII real fora do git/CI). Step no SMOKE_TEST_HUMAN, não pytest. | P1 (processo) | Sprint goal A23 |
| **G-g** | Gate E2E condicional por path: filtro `lineage` no `changes` job; re-armar visual + `@critical` só em `report OR lineage` (emenda [[ADR-210]]); `--retries=2`; informativo-até-estável; **canary pós-merge** (nightly) com visual-full + dogfood golden. | P1 | CI |
| **G-h** | **Visual snapshot NÃO é gate de F2/F3** (ferramenta errada p/ número, flaky em dogfood). Reusar visual só na F6 (UI nova: selo N1/popover N2) com **máscara do selo** (`data-mask-snapshot`) + snapshot isolado do affordance + variante **flag-ON** (não só flag-off). | — (corte + F6) | F6/A24 |

**PR-gate (barato, sempre) ≠ canary pós-merge (caro):** G-a/G-b/G-d e os gates
de cents int rodam em PR; G-g (visual-full + dogfood golden) roda no canary
nightly porque é onde o relatório end-to-end regride sem o gate barato perceber.

---

## Verificação (por fase)
- **F1**: **`dl-f1-golden-substrate` entregue ANTES das demais lanes da onda** —
  `golden_diff` + snapshot do view-model + invariantes de conservação (G-a/G-b);
  golden de paridade K4 — (a) 2 shapes de fonte → mesmo hash, (b) float↔decimal
  de borda (`0.575`) → mesmo hash, (c) entrada R$100 ≠ saída R$100 ≠ USD100 (B3);
  gate `Decimal(amount)==Decimal(str(valor))` (B5); migration dry-run com volume
  de prod (`CREATE INDEX CONCURRENTLY` fora de transação) + **runbook G-e**;
  `tests/test_e{3,4,5}_golden_execution.py` **+ snapshot do view-model + invariantes**
  **verdes sem re-baseline** (só vale se `natural_key` entrar nullable onde produtor
  não emite K4, B4).
- **F2**: rebaseline E2/E3 em commit separado **via `golden_diff` + manifesto
  justificado por valor + label `golden-rebaseline` + 2º revisor** (G-c;
  `check_golden_rebaseline_isolation` falha se golden + código no mesmo commit);
  discovery de consumidores com blast radius numérico antes de mover; **diff de
  dogfood (dado real, local/gitignored) sem surpresa antes do merge** (G-f).
- **F3**: gate `_lineage.value == artifact[field]` em cents int; `check_lineage_sum`
  incl. caso incremental (B8) + tx colapsada por dedup; mesmo run 2× → `_lineage`
  byte-idêntico **(estendido ao snapshot do view-model)**; snapshot textual dos
  KPIs/agregados no render (G-d); CLI resolve patrimônio líquido → fonte.
- **Q1** (quando houver feed): golden mesma tx PDF+feed idênticos → 1 linha,
  `SourceRef[]` com 2 origens; divergentes ≥ R$ 10k → sobrevivente mantém valor do
  extrato oficial + `signals.source_divergence`; golden feed+extrato mesma conta →
  `SaldoGapWarning` count inalterado (B7).
- **F4**: golden estrutural ≥3 negative cases; tokens +<5%; `check_planner_manifest_coverage`.
- **F5**: query reversa "números que dependem da fonte X"; `reback_lineage`
  reconstrói cadeia P0; teste de retenção (2 runs não acumulam edges).
- **F6**: flag off ⇒ relatório === atual **E flag-ON === flag-off exceto máscara do
  selo** (G-h — cobre o estado que o cliente vê, não só o isolamento); selo N1 sob
  `data-mask-snapshot` + snapshot **isolado** do affordance (selo não altera
  baseline/line-height; popover não estoura o card; light+dark); teste de confiança
  5s dogfood (roteiro: dogfooder responde "de onde veio?" em 1 frase sem abrir nada
  técnico); copy gate (4 verbos + zero jargão de pipeline, COPY_GUIDELINES §6.3);
  a11y (aria-label sem jargão, teclado, `Escape`, foco retorna, `prefers-reduced-motion`,
  badge needs_review forma+texto+`--semantic-warning-*`); mobile: N2 desktop-first,
  `<md` degrada para N3 drawer.
- **F7**: `check_lineage_refs` (ref quebrado → falha); golden de `lineage_diff`;
  eval de injeção verde (`localization_accuracy@node ≥85%`).

## Riscos & invariantes
- **F2 é a fase mais arriscada** (toca goldens + [[ADR-246]]/[[ADR-271]]).
  Mitigação: F1 entrega a opcionalidade de fonte mesmo se F2 escorregar; F2 fatiada;
  discovery dimensionado como gate.
- **K4 obrigatório** — sem ele, feed produz tx sem hash → duplicação silenciosa
  (gênero do bug R$ 811k).
- **Dinheiro decimal** ([[ADR-090]]) — migração `valor`→`amount` em 2 fases.
- **Determinismo** — zero timestamp/UUID em `_lineage`; `inputs` sorted; rebaseline
  é mudança de contrato esperada.
- **[[ADR-111]] stateless** — resolver sem cache; tabela reversa via stage terminal.
- **MCP prod cross-tenant** — `workspace_id` obrigatório + read-only + zero mutação.
- **Transparency backfire** (produto) — número final soberano; lineage opt-in;
  linguagem de "conferência" não "estimativa".

## Referências
- Rascunho de co-design (pré-canônico): histórico de decisão em sessão.
- ADRs canônicas: [[ADR-278]] · [[ADR-279]] · [[ADR-280]] · [[ADR-281]] + emenda
  [[ADR-146]]; supersede [[ADR-045]].
- Sprint de execução: [sprint/A23/_README.md](../../sprint/A23/_README.md).
