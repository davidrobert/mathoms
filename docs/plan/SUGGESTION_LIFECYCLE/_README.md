---
id: PLAN-suggestion-lifecycle
type: plan
title: Ciclo de vida de sugestões do Parecer no /acao — supersede, thesis_key, valores determinísticos
status: in_progress
created_at: 2026-06-12
sprint_origem: A25
sprint_atual: A42
sprints_envolvidas: [A25, A42]
adrs_canonical:
  - "[[ADR-290]]"
  - "[[ADR-378]]"
tags:
  - type/plan
  - status/in-progress
  - area/llm
  - area/backend
  - area/produto
---

# Ciclo de vida de sugestões do Parecer no `/acao` — supersede, thesis_key, valores determinísticos

> **Origem:** auditoria 2026-06-12 do workspace dogfood: 158 sugestões
> Pendentes acumuladas em 12 runs do pipeline (06/mai→12/jun). Diagnóstico
> co-assinado por `financial-planner` e `prompt-engineer`; plano revisado por
> `product-manager`, `data-engineer` e `information-architect` (3 pareceres
> incorporados em 2026-06-12).
>
> **Relação com planos existentes:** estende o aterrissado em
> [PLANNER_REVIEW](../../archive/PLANNER_REVIEW-2026-07-09.md) (Atos 1-6 entregues); **não** reabre ADR-199..208 —
> corrige dívida de ciclo de vida do aggregate `Suggestion` que [[ADR-269]]
> resolveu apenas para `task_suggestions`.

## 1. Diagnóstico (resumo)

1. **Acúmulo monotônico** — `_persist_suggestions_from_artifact`
   (`backend/app/services/planner_review_persistence.py:224-241`) insere se
   `dedup_key` inédito; **nunca supersede** pendentes de runs anteriores.
   `_existing_dedup_keys` (L131) protege apenas retry do mesmo run (mesmo gap
   que ADR-269 descreveu e corrigiu para `task_suggestions`).
2. **Dedup key frágil** — `compute_suggestion_dedup_key`
   (`backend/app/services/parecer_finalization.py:36`) =
   `sha256(ws | ancora_metodologica | acao[:100])`. LLM re-redige a ação a cada
   run → chave nova → near-duplicates coexistem (5 variantes de "reserva de
   emergência", 8 de "exposição internacional 10-15%").
3. **Valores monetários não-determinísticos** — reserva citada como R$ 224k /
   250k / 250-300k / 260-520k / 270-540k entre runs. O E5 **já computa** o valor
   exato (`reserva_emergencia_calculator.py:113-114` → `nivel_6_meses` /
   `nivel_12_meses`); o prompt não obriga passthrough e a validação ADR-279
   (regra 11) checa existência do `evidencia_path`, não igualdade do valor.
4. **Sem cap ativo cliente-facing** — 158 pendentes (11 danger, 104 warning,
   46 info); metodologias (Cerbasi/AUVP/Perini) convergem em poucas ações
   ativas, máx. 2 danger (invariante R3 da persona já diz "max 2 P0").
5. **O vazamento atinge 3 superfícies, não só o `/acao`** — as pendentes são
   consultadas **live** (`status=Pendente`) também dentro do relatório:
   cards "Promover para ação" por seção (`SuggestionCalloutInline`,
   `frontend/src/components/report/sections/SuggestionCallout.tsx:79` —
   ~~S3 sozinha renderiza 71 cards hoje~~ **correção 2026-08-12: falso — o
   inline só é montado em S2 e S7; os 71 pendentes de S3 nunca tiveram
   hospedeiro inline**, ver §Deferimentos datados 2026-08-12) e a seção
   "Próximos passos" (`SuggestionCalloutSummary`, mesma file L157 — lista
   todas as 158 cross-section), ambas sem cap. A seção "Plano de Ação" do relatório
   (`PlanoDeAcaoSection`) renderiza o aggregate `decisions` (ADR-136), **não**
   `suggestions` — 3 linhas no dogfood, fora do escopo deste plano.

**Dois caps em camadas distintas (não confundir):**

- **Cap de geração** (prompt, F3): máx. 3 sugestões por horizonte temporal,
  as de maior impacto (schema mantém ≤5 como hard cap).
- **Cap de display** (inbox `/acao`, F3): ≤ 12 itens **acionáveis**
  (danger + warning), com ≤ 2 danger; `info` colapsado por default e
  **fora** do cap (referência, não fila de trabalho).

## 2. KRs (critérios de sucesso do plano)

- **KR1 — Idempotência por tese:** 3 runs consecutivos sobre o mesmo E5 (mesmo
  `e5_content_hash`) produzem o **mesmo conjunto** de teses Pendentes; zero
  pares de pendentes com mesma tese e redação/valor divergente.
- **KR2 — Precisão de valor:** valor monetário citado em sugestão = escalar
  resolvido do payload E5 (tolerância de arredondamento a milhar); eval golden
  ≥98% match; divergência → `needs_review`.
- **KR3 — Carga cognitiva (steady-state):** ~~inbox ativo do `/acao` ≤ 12
  itens acionáveis~~ → **recalibrado na F5 (2026-08-11):** ≤12 vira teto de
  segurança (passava verde com 11 itens indistinguíveis); o alvo é **≤3
  acionáveis, teto 5**, com táticas/estratégicas visíveis fora do cap e
  `info` colapsado. Danger segue ≤2. (Meta one-shot de backfill dogfood
  158 → ≤14 vive no aceite de F4.)
- **KR4 — Observabilidade:** todo run loga `suggestions_created`,
  `suggestions_superseded`, `skipped_dismiss`, `near_dup_candidates`;
  acúmulo vira drift detectável, não surpresa. **Instrumentado em F1**, no
  mesmo PR do supersede (mudança arriscada não voa cega).
- **KR5 — Utilidade (guardrail, não target):** taxa
  `(Aceita+Modificada)/(Aceita+Modificada+Descartada)` de sugestões
  `kind=parecer` não regride após F3; supersede automático **não** conta como
  Descartada. Dogfood n=1 → sinal qualitativo; vira target numérico no beta.
  Previne Goodhart do KR3 (atingir ≤12 suprimindo sugestões boas).

## 3. Fases

### F0 — ADR Proposto (gate de abertura; nenhuma lane abre antes)

[[ADR-290]] criada como `Proposto` no mesmo PR deste plano. Decisões travadas
B1–B7 (thesis_key, status `Superseded`, proteção fiduciária, janela dismiss,
separação de ciclos, idempotência run-level, contrato API). Flippa para
`Decidido` no merge do PR de F1.

**Correção de premissa (achado `data-engineer`):** `uq_sugagg_ws_dedup_status`
é UNIQUE **full** de 3 colunas, não parcial como afirma o docstring do modelo.
**Não** criar UNIQUE/índice único sobre `thesis_key` — unicidade de tese é
garantida pela lógica de supersede no service. Docstring mentiroso corrigido
em commit separado.

### F1 — Estancar o acúmulo (backend + migration + telemetria)

> ✅ **Código entregue** (branch `agent/sug-lifecycle-f1/20260612-1630`):
> migration `adr290supersede`, `compute_suggestion_thesis_key`,
> service `backend/app/services/suggestion_supersede.py`, telemetria KR4,
> 10 testes de supersede + 3 de migration. ADR-290 flippada para
> `Decidido (A25)` no mesmo PR. **Pendente:** gate de estabilidade ≥90%
> (2 runs reais no dogfood — medição pós-merge).

- Migration Alembic reversível: `thesis_key` (nullable, btree não-unique
  `(workspace_id, thesis_key)`), `superseded_at`, `superseded_by_run_id`.
  Sem `NOT NULL`, sem backfill na migration. Test com
  `pytestmark = pytest.mark.migration`.
- `parecer_finalization`: computar `thesis_key` ao lado do `dedup_key`;
  `_build_suggestion` persiste na escrita. Campo-fonte ausente →
  `thesis_key = NULL` → linha fica fora do supersede (fallback seguro).
- `planner_review_persistence.persist_planner_review`: supersede **após** o
  guard `_find_existing_review` (idempotência run-level já existente; não
  reimplementar `new_keys` de `task_suggestions`). Predicado B3 + defesa
  `superseded_by_run_id != run_atual`.
- `VALID_SUGGESTION_AGGREGATE_STATUSES += {'Superseded'}` (capitalizado);
  `make update-openapi-snapshot` (provável no-op; comitar se diff); confirmar
  guard de `modify_suggestion`.
- **Telemetria no mesmo PR:** 4 contadores do KR4 em log estruturado
  (namespace `mathoms.pipeline.planner_review_persistence`).
- **Gate de estabilidade da chave (mede R1 aqui, não só em F2):**
  `thesis_key` reaparece idêntico em 2 runs para ≥90% das teses; abaixo
  disso, F1 não passa e `action_slug` é antecipada.
  > **Status em 2026-08-11:** gate **permanece aberto**. A F5 remove a
  > dependência do supersede em relação à chave (a expiração é ortogonal),
  > mas **não fecha o gate** — ele é transferido para a F6, agora com o
  > instrumento certo: reaparição não enxerga colisão, e a colisão
  > intra-run foi medida em 2 num run real.

### F2 — Valores determinísticos no parecer (prompt + validação)

> ✅ **Código entregue** (branch `agent/sug-lifecycle-f2/20260612-1750`):
> PROMPT_VERSION 1.4.0 (regras 12 passthrough + 13 cap de geração), hints
> imperativos nos 2 manifests de seção, manifest 1.4 (invalida cache),
> whitelist de faixa legítima + contadores `money_tokens_total`/
> `range_in_scalar_count` no validador ADR-279, eval determinístico
> `TestValorDeterministicoF2`. **Nota (prompt-engineer):** truncamento
> determinístico do cap 3/horizonte fica em F3; gate ≥98% de match é
> operacional (telemetria em runs reais), não pytest.

- `config/prompts/parecer_planejador.yaml`: hints imperativos — citar
  **exatamente** `$.reserva_emergencia.nivel_6_meses`/`nivel_12_meses` (e
  análogos), nunca faixa/arredondamento próprio. Bump `PROMPT_VERSION` 1.4.0.
- Reforçar regra 11 (ADR-279): quando `evidencia_path` resolve escalar
  numérico, o `R$` da prosa deve bater (tolerância milhar) → senão
  `needs_review`. Whitelist de campos-faixa legítimos (mitiga falsos
  positivos, R3).
- Eval golden: fixture sintética PII-zero derivada do caso dogfood;
  gate de regressão; mede também FP rate do validador.

### F3 — Cap + priorização cliente-facing (prompt + UI)

> ✅ **Código entregue** (branch `agent/sug-lifecycle-f3/20260612-1830`):
> helper `frontend/src/lib/suggestionOrdering.ts` (severidade → gate
> metodológico → sem-valor antes → impacto desc; mapeamento seção/categoria
> → gate validado com `financial-planner`), InboxTab com cap de 12
> acionáveis + disclosures (overflow e `info`, padrão `DisclosureToggle`
> com aria-expanded), deep-link `?section=`, cards inline ≤3/seção,
> "Próximos passos" só acionáveis (copy do `product-designer`), e
> truncamento determinístico do cap de geração (3/horizonte, P0 protegido)
> em `finalize_output`. Nota PD aceita: confiança não reordena
> silenciosamente — não persiste no aggregate; desempate é created_at.

- Prompt (cap de geração): "máx. 3 sugestões por horizonte, as de maior
  impacto; não preencha slots com variantes da mesma ação".
- Ordering `/acao` (InboxTab; cap de display): severidade (danger sempre topo,
  não filtrável) → gate metodológico (proteção/liquidez → dívida → alocação →
  renda → fiscal) → impacto (`amount_brl_cents`) × peso de confiança; esforço
  só desempate; `info` colapsado por default e fora do cap.
- **Superfícies do relatório (mesma lane):** `SuggestionCalloutInline`
  (cards "Promover para ação" por seção) e `SuggestionCalloutSummary`
  ("Próximos passos") aplicam o **mesmo** ordering + colapso de `info`;
  cap de display por superfície (ex.: ≤3 cards inline por seção com
  "ver todas em /acao"; "Próximos passos" mostra só acionáveis ordenadas).
  F1/F4 já reduzem o volume na fonte (queries são live em
  `status=Pendente`); aqui é hierarquia, não dados.
- Gatilho `product-designer` na lane de UI (copy + hierarquia + colapso),
  cobrindo `/acao` **e** as duas superfícies do relatório.

### F4 — Backfill dogfood (heurístico) — depende de F1

> ✅ **Entregue + aplicado** (#626 + follow-up #627): service
> `backend/app/services/internal_ops/suggestion_backfill.py` (workspace
> obrigatório, dry-run default, audit em apply, skip de `created_at` >
> início) + runbook + 8 testes. Dry-run heurístico no dogfood achou **0
> duplicatas** (LLM re-redige títulos a cada run) → owner aprovou modo
> `latest_batch` ("último parecer vence") em 2026-06-12. **Apply
> executado:** 165 → 7 Pendentes (5 acionáveis, 0 danger; aceite ≤14 ✓),
> 158 Superseded soft.

- **Reescopo (achado `data-engineer`):** linhas antigas não armazenam
  `tema_canonico`/`ancora_metodologica` nem `pipeline_run_id` confiável
  (`report_id` é FK opcional `SET NULL`) → **não é possível recomputar
  thesis_key determinístico**. Backfill é **reconciliação heurística**
  (`section_id` + título normalizado): agrupar pendentes, manter a mais
  recente, superseder o resto. Estado determinístico-limpo vale só para runs
  pós-F1.
- Script service-layer padrão `internal_ops`: `workspace_id` **obrigatório**
  (sem default "todos"), `--apply` explícito (default dry-run), relatório de
  agrupamento `(grupo → mantém / supersede)` para revisão humana antes do
  apply. Rollback: `Superseded` é soft (re-promovível por SQL).
- Concorrência: rodar em janela sem pipeline ativo no workspace (ou skip de
  `created_at` > início do backfill). Documentar no runbook curto.

### F5 — Expiração por parecer-fonte + horizonte + consolidação de superfícies (A42)

> **Origem:** medição do dogfood em 2026-08-11, 8 semanas e 26 runs após a
> F4. Diagnóstico co-assinado por `product-designer` (UX das duas listas) e
> `financial-planner` (volume e risco fiduciário); desenho revisado por
> `senior-cto` (guards B-1/B-2, escopo do índice parcial, sequência de PRs).
> Canônica: [[ADR-378]] + emenda datada em [[ADR-290]].

**O que a medição mostrou** — 15 Pendentes (11 warning, 4 info, 0 danger):

1. 7 são de 2026-06-12 com `thesis_key = NULL` — **imunes a supersede por
   construção** (fallback B1). Citam valores de junho contra o E5 de agosto:
   risco fiduciário classificado como bloqueante.
2. 3 pendentes de um mesmo run dividem `thesis_key` sendo teses distintas —
   a chave não discrimina, e o gate da F1 (reaparição ≥90%) não enxerga
   colisão.
3. O horizonte (`execucao`/`tatica`/`estrategica`) era descartado na
   persistência: o inbox tratava "faça agora" e "considere em 3 anos" como
   equivalentes — causa estrutural das 11 acionáveis.
4. O relatório renderizava o inbox **inteiro e live** ("Próximos passos")
   dentro de um documento-snapshot, somando até 4 superfícies de ação
   concorrentes na mesma página.

**Entregas (4 PRs, nesta ordem — migration antes de comportamento):**

- **PR-A (docs):** [[ADR-378]] `Proposto` + emenda datada em [[ADR-290]] +
  esta §F5.
- **PR-B1 (migration):** `horizon` + `pipeline_run_id` (FK `SET NULL`) + FK
  em `superseded_by_run_id` + swap do UNIQUE full pelo índice parcial
  `uq_sugagg_ws_dedup_ativa`; teste de migration assere que o recreate do
  batch preserva as 3 FKs de saída com `ondelete` correto.
- **PR-B2 (lógica):** expiração por parecer-fonte com guard de `outcome`,
  dup-check sobre status ativos, telemetria ampliada. [[ADR-378]] flippa para
  `Decidido`.
- **PR-C (relatório):** "Próximos passos" vira bloco de fechamento (contagem
  + 1 CTA, sem lista); `SuggestionCalloutInline` filtra
  `report_id === reportId` — snapshot deixa de vazar estado live.
- **PR-D (inbox `/acao`):** grupos "Decidir agora" (≤3) / "Nesta rodada" /
  "Agendadas" (táticas + estratégicas, fora do cap) / "Informativas"; data no
  card; `<MonetaryValue/>`; tokens semânticos no lugar de Tailwind literal;
  chips da `ActionStatusBar` clicáveis.

**Aceite por PR:**

- **B1:** upgrade cria colunas + índice parcial com `WHERE` sobre os 3 status
  ativos; 2 `Superseded` de mesma `dedup_key` coexistem; 2ª `Pendente` de
  mesma key viola; FKs preservadas; downgrade dedup-a e restaura o full
  unique (destrutivo-documentado).
- **B2:** run entregue expira tudo do run anterior **inclusive
  `thesis_key NULL`**; run `retido` e artifact vazio não expiram nada;
  reafirmação re-entra com `rationale` novo; `Aceita` nunca expira; ordem
  expirar→inserir sobrevive a `no_autoflush`; contadores KR4 batem
  (`pending_after` incluído).
- **C:** `/reports/[id]` renderiza ≤2 blocos que pedem ação (parecer + plano);
  zero sugestão com `report_id ≠ reportId`; Summary sem `<li>`.
- **D:** grupo de foco com ≤3 itens; acionável = `horizon` ∉
  {`tatica`,`estrategica`} (gate falha **aberto** para `NULL`); nada
  inalcançável em >1 clique (KR5).
- **Transversal:** o dogfood só limpa com um run entregue (ou
  `suggestion_backfill --apply` em `latest_batch`) — código mergeado não é
  inbox limpo; a ação one-shot faz parte do done da lane.

**KR3 recalibrado:** "≤12 acionáveis" era lido como alvo e passava verde com
11 itens indistinguíveis. Vira **teto de segurança**; o alvo de steady-state
é **≤3 acionáveis (teto 5)**, obtido pelo gate de horizonte, não por
supressão — KR5 continua sendo o anti-Goodhart, e expiração de D1 **não**
conta como Descartada.

### F6 — `action_slug` de vocabulário fechado (gatilho disparado, não hipótese)

Deixou de ser "Later condicional" em 2026-08-11: a colisão intra-run foi
**medida em 2** num run real ([[ADR-378]] §D5). `thesis_key` continua
governando a janela de dismiss (B4) — logo, com chave grossa, descartar uma
tese silencia as vizinhas por 90 dias. Escopo: vocabulário fechado por seção
no schema do parecer, bump de `PROMPT_VERSION`, eval golden de estabilidade,
e gate hard "duas teses distintas sob a mesma chave no mesmo run". Depende de
`prompt-engineer` (prompt + eval). Enquanto F6 não abre, a supressão por
janela é logada item a item para deixar rastro auditável.

### Deferimentos datados (2026-08-11)

- **Dedup cross-aggregate `Suggestion` ↔ `Decision`** — sugestão equivalente a
  uma `Decision` `Pendente` deveria entrar como atualização de `D0x`, não como
  item novo (par observado no dogfood: "Categorizar as despesas sem
  identificação" vs. `D03`). Fora do escopo da F5 porque exige política de
  equivalência semântica; o contador `skipped_dup` mede a pressão real.
  Retomar quando `skipped_dup` for consistentemente > 0 ou ao abrir F6.
- **Re-apresentação de `Decision` estagnada** — decisões `Pendente` há >90
  dias (3 no dogfood, desde maio) deveriam ser reafirmadas com medição de
  aderência ou supersedidas explicitamente pelo parecer seguinte. Depende de
  F6 para não gerar mais ruído com identidade fraca.
- **Unificação do léxico de prioridade** — parecer diz P0/P1/P2
  (Urgente/Importante/Oportunidade), callout diz danger/warning/info; o mesmo
  item recebe dois rótulos na mesma página. É decisão de terminologia:
  registrar em `COPY_GUIDELINES` §2.2 **antes** de mexer em `PRIORIDADE_TONE`
  e `SEVERITY_VARIANTS`.
- **Timeline de histórico de pareceres** ("recomendava X em mai/26, atualizado
  para Y em ago/26") — auditoria fiduciária fora do inbox; `superseded_by_run_id`
  + `pipeline_run_id` (F5) são o substrato que ela vai consumir.

### Deferimentos datados (2026-08-12 — verificação da sessão S6/FP-010)

- **`SuggestionCalloutInline` montado em 2 de 12 seções habilitadas (S2, S7)**
  — o caso vivo é a **S3**: 2 regras determinísticas ativas
  (`alocacao_fora_alvo`, `concentracao_instituicao`) e nenhum hospedeiro
  inline; a sugestão aparece só no "Próximos passos" e no `/acao`. A premissa
  original do achado (S9, via sugestão de seguros do #1379) **venceu** — a
  regra foi removida em FP-010 ([[ADR-161]] §Emenda) e hoje nenhuma regra
  determinística emite S9. Decidir cobertura é decisão de produto por seção
  (`product-designer` + `financial-planner`), não varredura mecânica — a
  afirmação de [[ADR-199]] de que o cross-linking "é automático nas seções
  fonte" foi corrigida por emenda em 2026-08-12. P2.
- **`GATE_BY_SECTION` (`suggestionOrdering.ts`) não tem gate de sincronia
  mapa↔layout** — habilitar seção nova no YAML manda as sugestões dela,
  silenciosamente, para o `GATE_DEFAULT`. Reenunciado após verificação: o
  default 6 é **deliberado, documentado e pinado por teste**
  (`suggestionOrdering.test.ts` asserta `S_parecer → 6`); "falha aberta" do
  enunciado original estava invertido — o default manda para o **fim** da
  fila e a severidade precede o gate. O gate tri-camada de vocabulário
  (`tests/unit/pipeline/test_suggestion_rules.py`) para na borda
  Python/JSON-schema e não alcança o mapa TS. A única ausência com substância
  é **S4** (Real Estate — hoje ranqueia atrás de fiscal); S10/S_parecer/
  plano_de_acao são síntese/meta, fim da fila é defensável. P3.

## 4. Dependências e paralelismo

```
F0 (ADR-290 Proposto) ──► F1 (migration + supersede + telemetria + gate de chave) ──► F4 (backfill heurístico)
                     └──► F2 (paralela a F1; toca prompt/schema LLM, não DB)
F1 + F2 ──► F3 (cap de geração entra junto de F2; ordering UI depois de F1)
F1..F4 dogfood medido (2026-08-11) ──► F5 (ADR-378: expiração + horizonte + superfícies)
F5: PR-A (docs) ──► PR-B1 (migration) ──► PR-B2 (lógica) ──► PR-D (inbox)
                                     └──► PR-C (relatório; paralelo a B, arquivos disjuntos)
F5 + colisão medida ──► F6 (action_slug + gate hard de colisão)
```

**Ordem B1 → B2 é de deploy, não estética:** se a lógica de D2 subir antes da
constraint nova, a primeira reemissão de texto já supersedido levanta
`IntegrityError`, `_safe_persist` faz rollback e o parecer inteiro se perde
(artifact órfão). Constraint primeiro, comportamento depois.

## 5. Riscos

- **R1** — `tema_canonico`/`ancora_metodologica` instáveis entre runs →
  thesis_key fura como o dedup atual. Mitigação: **gate de estabilidade ≥90%
  em F1** (não espera F2); fallback estrutural = `action_slug` (Later).
- **R2** — supersede agressivo apaga sugestão que o usuário ia aceitar.
  Mitigação: `Superseded` é soft/recuperável; B3 protege aceitas; telemetria
  de `suggestions_superseded` no mesmo PR (F1).
- **R3** — validador de igualdade de valor gera falsos `needs_review`
  (formatação pt-BR, faixas legítimas). Mitigação: tolerância a milhar +
  whitelist de campos-faixa; eval golden mede FP rate.
- **R4** — backfill em produção multi-tenant. Mitigação: `workspace_id`
  obrigatório, dry-run default, relatório revisado antes do `--apply`,
  começa no dogfood.

## 6. Critérios de aceite (gate de done por fase)

Regra geral: fase concluída = PR mergeado em `main` com CI verde
(F1/F3/F4 tocam código — exceção docs-only não se aplica).

- **F0:** ADR-290 mergeada como `Proposto`; B1–B7 travados. ✦ entregue no PR
  deste plano.
- **F1:** 2 chamadas de `persist_planner_review` para o **mesmo** run não
  supersedem nada na 2ª (guard run-level); 2 runs **diferentes** sobre mesmo
  E5 → 2º supersede teses obsoletas, mantém reaparecidas, `count(Pendente)`
  não cresce; sugestão com `accepted_decision_id` nunca vira `Superseded`;
  `origin='deterministic'` intocado; migration reversível testada; 4
  contadores logados; gate de estabilidade ≥90% medido e aprovado.
- **F2:** eval golden ≥98% match de valor; zero faixa inventada para campos
  escalares; FP rate do validador medido; `PROMPT_VERSION` 1.4.0 com
  telemetria por versão.
- **F3:** parecer novo emite ≤3/horizonte; **teste de snapshot do ordering**
  com fixture multi-severidade (danger no topo independente de filtro);
  `info` colapsado e fora do cap; cards inline do relatório ≤3 por seção
  com link "ver todas"; "Próximos passos" usa o mesmo ordering do `/acao`.
- **F4:** dry-run aprovado + relatório de diff revisado antes do apply;
  dogfood 158 → ≤14 pendentes acionáveis; rollback documentado; runbook
  curto do backfill.
- **Transversal (KR5):** taxa de aceitação instrumentada e não-regredida
  após F3 (sinal qualitativo em dogfood).

## 7. Lanes

Lanes serão abertas em `docs/sprint/A25/lanes/` (ou sprint seguinte, a
critério do PM) após o merge deste plano + ADR-290. Mapeamento previsto:

| Lane (prevista) | Fase | Escopo | Branch slug |
| --- | --- | --- | --- |
| `suggestion-supersede` | F1 | migration + supersede + telemetria + gate de chave | `sug-supersede-*` |
| `parecer-valores-deterministicos` | F2 | prompt 1.4.0 + validador igualdade + eval golden | `parecer-valores-*` |
| `acao-inbox-cap-ordering` | F3 | cap de geração + ordering/colapso UI (`/acao` + cards inline e "Próximos passos" do relatório) | `acao-ordering-*` |
| `suggestion-backfill-dogfood` | F4 | script internal_ops + runbook + apply dogfood | `sug-backfill-*` |
