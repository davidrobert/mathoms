---
id: PLAN-cat-learning-loop
type: plan
title: "Categorization Learning Loop — promoção de override de transação para regra"
status: draft
sprint_origem: A12
sprint_atual: A12
sprints_envolvidas: ["A12"]
created_at: "2026-05-10"
last_review: "2026-05-10"
adrs_canonical:
  - "[[ADR-186]]"
tags:
  - type/plan
  - area/categorization
  - area/pipeline
  - area/methodology
  - sprint/a12
  - status/draft
---

# Plano canônico — Categorization Learning Loop

> Plano multi-fase para implementar a promoção de override de transação
> em regra de categorização persistida. Decisão arquitetural em
> [[ADR-186]]. **Pré-requisito externo:** [[ADR-187]] (mês fechado),
> implementado isoladamente em [[A11.report-publication]] e mergeado em
> `main` antes de iniciar P2 desta lane.

## Origem

Sessão 2026-05-10 — usuário (CEO) identificou gap: edição de categoria
em `/transactions` não propaga para `/config → Categorias`. Co-design
com `financial-planner` + `product-designer` produziu modelo híbrido
C-light + D-forte (toast + side-panel + inbox de sugestões), com
invariantes não-negociáveis:

1. Override manual é **sticky** — regra nunca atropela edição manual.
2. Mês fechado é **imutável** — re-categorização retroativa só em
   meses sem `report_publication` viva (entregue por
   [[A11.report-publication]]).
3. Conflito de regras é **determinístico** — `priority` explícito +
   `len(keyword)` desc como tiebreaker.

Review `product-manager` (mesma sessão) determinou: **mover lane para
A12** (A11 sobrecarregada com PLATFORM_REVIEW + COMPETITIVE_PIERRE +
DOC_REORG), **promover ADR-186 a lane standalone em A11** (reusabilidade
+ desacopla risco), **cortar P5/P6 do MVP** (V2 pós-tração), **adicionar
gate dogfood entre P3 e P4**.

## Objetivo

Após este plano, ao editar categoria de uma transação em `/transactions`,
o usuário pode promover a edição para regra persistida que:

- Re-categoriza transações similares **futuras** automaticamente.
- Re-categoriza transações **passadas em meses não-publicados** sem
  override manual.
- Aparece em `/config → Categorias → Regras promovidas` com botão
  "Reverter regra".
- É auditável (origem rastreável: `origin_override_id`,
  `created_at`, `source`).
- KPIs de saúde: ratio learned_rule/manual_override; revert_rate;
  time-to-rule.

## Não-objetivos (MVP V1)

- ML/LLM para extração de keyword. Highlight-to-extract + heurística
  determinística é suficiente.
- Auto-publish de mês fechado (mantém manual em V1 — ver
  [[A11.report-publication]]).
- Badge de confiança por regra ("aplicada 47×, revertida 2× — 95%").
  V2 após coletar dados.
- Migração de `WorkspaceCategoryOverride.keywords_override` para o novo
  modelo. Mantém ambos; pipeline E4 mergeia (D5 da [[ADR-186]]).
- **Inbox de sugestões pendentes** (`/config → Categorias` sub-tab)
  e **detector offline em background**: cortados do MVP por review
  PM. Razão: dogfood não precisa de inbox auto-curado; voltam em V2 se
  feature provar tração.
- **Alertas SRE de saúde de regra:** prematuros sem dados de uso real.
  V2.

## Pré-requisito externo

[[A11.report-publication]] ([[ADR-187]]) — DEVE mergear em `main` antes
de iniciar **P2 (Pipeline E4)** desta lane. P1 (Schema) pode rodar em
paralelo com a impl de A11.report-publication.

Track: [report-publication-impl](../../sprint/A11/tracks/report-publication-impl.md) ✅ ready em A11.

## Fases (MVP V1)

| Fase | Track | Owner | Dependências | Esforço |
|---|---|---|---|---|
| **P1** | Schema: `transaction_overrides.source` + `categorization_rules` | data-engineer | A12 abrir | 2d eng |
| **P2** | Pipeline E4: `CategorizationRulesV2` + ordem de match + paridade | senior-cto + data-engineer | P1 ✅ + [[A11.report-publication]] ✅ | 3d eng |
| **P3** | Backend API: preview + commit + revert + telemetria mínima (4 contadores) | senior-cto | P2 ✅ | 3d eng |
| **Gate** | **Dogfood validation** (CLI/admin no workspace do CEO) | CEO + product-manager | P3 ✅ | 0,5d + 7d wall-clock |
| **P4** | Frontend `/transactions`: toast + side-panel + highlight-to-extract | product-designer (design) + frontend (impl) | Gate dogfood ✅ | 4d eng |

**Total estimado MVP V1:** 12,5d eng (cortado de 19d original).
**Wall-clock realista:** 2-3 semanas + 1 semana dogfood = 3-4 semanas
total.

### P1 — Schema base (transaction_overrides + categorization_rules)

**Track:** `cat-learning-loop-p1-schema.md` (criado quando A12 abrir)

Entrega:

- Migration: `transaction_overrides ADD COLUMN source VARCHAR(20) NOT
  NULL DEFAULT 'manual'`. Backfill: existentes = `'manual'`.
- Migration: cria tabela `categorization_rules` (ver [[ADR-186]] §D3).
- Coluna `rule_id` em `transaction_overrides` (FK NULL para
  `categorization_rules.id`).
- Models SQLAlchemy + repos.
- Schema `pydantic`: `CategorizationRuleCreate`,
  `CategorizationRuleResponse`.

**Gate de saída:** Alembic up/down testado, paridade de fixture
existente verificada (zero comportamento quebrado), goldens E4 passam
inalterados (ainda sem novas regras).

### P2 — Pipeline E4 (CategorizationRulesV2)

**Track:** `cat-learning-loop-p2-pipeline.md` (criado quando P1 mergear)

Entrega:

- `CategorizationRulesV2` em `pipeline/domain/services/categorization_service.py`
  (value object frozen com `template_keywords` + `learned_rules`).
- `LearnedRule` dataclass + sort estável `(priority desc, len(keyword) desc, created_at asc)`.
- Adapter em `pipeline/domain/services/e4_categorizer_adapter.py` lê
  `categorization_rules` do workspace e popula `LearnedRule`.
- Quando regra casa, cria/atualiza `TransactionOverride(source="rule",
  rule_id=...)` para auditoria.
- Teste de paridade: workspace sem regras → comportamento idêntico ao
  legado. Workspace com regras → ordem de match correta + conflito
  resolvido por priority.

**Gate de saída:** goldens E4 verdes, paridade legacy garantida em CI,
benchmark de match ≤2× tempo atual em workspace com 100 regras (sanity).

### P3 — Backend API + telemetria mínima

**Track:** `cat-learning-loop-p3-backend-api.md` (criado quando P2 mergear)

Entrega:

- `POST /workspaces/{ws}/categorization/rules/preview` — body:
  `{keyword, target_category, period_window?}`. Retorna:
  `{matches_total, matches_in_closed_months, matches_with_manual_override,
    matches_by_month: {...}, matches_by_origin_category: {...}, conflicts: [...]}`.
  **Não persiste**.
- `POST /workspaces/{ws}/categorization/rules` — cria regra + aplica
  (cria `TransactionOverride(source="rule")` para todos os matches em
  meses não-fechados sem override manual).
- `DELETE /workspaces/{ws}/categorization/rules/{id}` — desabilita
  regra + remove `TransactionOverride(source="rule", rule_id=...)`.
- `GET /workspaces/{ws}/categorization/rules` — lista paginada com
  contadores `applied_count` / `revert_count`.
- `POST /workspaces/{ws}/categorization/rules/{id}/disable` —
  desabilita sem remover (toggle enabled).
- **Telemetria mínima inline** (4 contadores `mathoms.categorization.*`):
  `transactions_categorized_total{source}`, `rules_applied_total`,
  `rules_reverted_total`, `time_to_rule_seconds`. Sem alertas SRE no
  MVP — só métricas para validar adoção.

**Hard limit MVP:** soft warning em UI ao chegar em **50 regras** por
workspace; hard cap configurável em **200 regras** (default). Excede →
endpoint POST retorna 409.

**Gate de saída:** snapshot OpenAPI atualizado ([[ADR-109]]), testes
integration cobrindo preview + apply + revert + conflito + cap.

### Gate dogfood — entre P3 e P4

**Owner:** CEO + `product-manager`. **Custo:** 0,5d setup + 7d wall-clock.

Antes de investir 4d em UX polida (P4 frontend), validar adoção e
qualidade da feature **com versão mínima de admin/CLI** no workspace do
CEO:

**Setup (0,5d):**

- Endpoint admin/CLI no backend para criar regra direto via API
  (curl/script). Sem UI.
- CEO conecta workspace pessoal real.

**Critério de aceite (medido em 7d wall-clock):**

- ≥5 regras criadas que persistam (não revertidas no mesmo dia).
- `revert_rate ≤ 30%` agregado.
- Pelo menos 3 regras geraram ≥3 matches retroativos cada.
- CEO reporta subjetivamente: "vou usar isso?" → SIM com confiança.

**Falha → AÇÃO:**

- `revert_rate > 30%` → extração de keyword é o problema; pausar P4,
  reabrir UX sessão `product-designer` para repensar tokenização.
- <3 regras úteis em 7d → sinal de adoção zero; pausar P4, reabrir
  problema com `product-manager` (talvez feature deva morrer).
- "Não vou usar" subjetivo → kill switch antes de gastar 4d frontend.

### P4 — Frontend `/transactions` UX

**Track:** `cat-learning-loop-p4-frontend-edit.md` (criado quando P3
mergear)

Entrega:

- Toast não-bloqueante após save de override (microcopy:
  "Categoria atualizada. {N} transações similares? **Revisar** ·
  Dispensar"). Dispensável com "Não sugerir mais nesta sessão"
  (localStorage `cat_rule_suggest_dismissed_session`).
- Side-panel direito 480px (desktop) / full-screen (mobile) com:
  - Header: keyword editável + categoria destino + contador.
  - Highlight-to-extract sobre `description` (Range API + `<mark>`).
  - Live preview: contador, heatmap mensal pequeno (meses fechados em
    cinza não-clickável), diff agrupado por categoria de origem.
  - Linhas com `TransactionOverride(source="manual")` aparecem
    opt-out por padrão com badge "Editado manualmente — manter".
  - Warning de conflito (substring/superstring) com acknowledgement
    obrigatório.
- Banner persistente em transações categorizadas por regra:
  "Categorizada por regra '...' · Editar regra · Desvincular".
- A11y: trap-focus, ESC fecha, screen-reader anuncia contadores.
- Testes E2E `@critical`: criar regra → verificar 47 tx mudam →
  reverter → verificar restauração com manual intacto.

**Gate de saída:** review `product-designer` + `gherkin/playwright`
verde + golden screenshot.

## V2 (pós-tração — fora do MVP)

Cortados do MVP por review `product-manager` 2026-05-10. Voltam em
sprint posterior **se MVP provar tração** (≥30% de adoção em
workspaces ativos + revert_rate baixo + feedback positivo dogfood):

### V2.A — Frontend `/config → Categorias`: Regras promovidas + Sugestões

> **Pré-condição estrutural (PM review 2026-05-10):** `CategoriesTab.tsx`
> deve estar com **tabs/subnav extensíveis** (array configurável de
> `{id, label, content}`) entregue na W4 da [PLAN-category-overrides-ux](../CATEGORY_OVERRIDES_UX/_README.md)
> — coordenação documentada no [track W4 §Coordenação cross-lane](../../sprint/A11/tracks/category-overrides-ui-refactor.md).
> Se hook estrutural **não** existe quando V2 promover (ex.: a tab nasceu
> flat por engano e o gate de aceitação não pegou), somar **+1d eng** ao
> custo desta fase para refactor da estrutura antes de adicionar a
> sub-tab.

- Sub-tab "Regras promovidas" em `CategoriesTab.tsx`: lista paginada
  com `keyword`, `target_category`, `applied_count`, `revert_count`,
  origem; botão "Reverter regra"; botão "Pausar".
- Sub-tab "Sugestões pendentes" (consumida pelo V2.B detector offline).
- Indicador visual de mês fechado no relatório refinado (badge no
  header da seção mensal — refinamento do banner mínimo entregue por
  [[A11.report-publication]]).

### V2.B — Detector offline de candidatos

- Job `detect_rule_candidates` (Celery beat, diário). Agrupa overrides
  por `(target_category, normalized_token)` (maior n-grama estável,
  ≥3 ocorrências distintas em 90d) → tabela `rule_suggestions`.
- Consumido pela sub-tab V2.A "Sugestões pendentes" (aprovar em lote).

### V2.C — Telemetria avançada + alertas SRE

- Histogramas + dashboards Grafana dedicados.
- Alertas:
  - `manual_override_rate < 1% por 30d` → over-fitting investigar.
  - `revert_rate > 20% por rule_id` → extração ruim, revisar UX.
- Badge de confiança por regra ("aplicada 47×, revertida 2× — 95%").

**Decisão de promoção V1→V2:** revisão `product-manager` + dados de
`mathoms.categorization.*` após 60d de MVP em produção. Critério hard:
`learned_rule` ratio ≥ 20%, revert_rate ≤ 15%, ≥10 workspaces com regra
promovida.

## Trade-offs aceitos

1. **ADR-186 desacoplado em lane standalone (A11).** Custo: dependência
   externa explícita pra A12. Ganho: mês fechado é reusável (Decision/
   IRPF/cenários), não bloqueia ADR-185 fora de seu mérito metodológico,
   reduz risco cruzado de slippage.
2. **Tabela `categorization_rules` separada de
   `WorkspaceCategoryOverride.keywords_override`.** Custo: pipeline E4
   lê duas fontes. Ganho: separação semântica clara (override editorial
   vs. regra aprendida), auditabilidade, prioridade explícita.
3. **`TransactionOverride(source="rule")` por aplicação de regra.**
   Custo: linhas a mais no DB (≈ N transações × M regras). Ganho:
   reverter é reversível e atômico; manual fica intocado por design.
4. **Manual mode V1 para publicar mês.** Custo: usuário esquece de
   publicar → re-categorização retroativa muda gráfico antigo. Ganho:
   previsibilidade + simplicidade. V2 endereça auto-publish.
5. **Não migra `keywords_override` legacy.** Custo: 2 caminhos no E4.
   Ganho: zero risco de quebrar workspaces produtivos.
6. **MVP corta P5 inbox + P6 detector offline (V2).** Custo: usuário
   pode "perder" sugestões em workspace gigante sem inbox. Ganho: -7d
   eng, -1 perfil SRE, kill switch antes de gastar UX polida sem
   tração comprovada.
7. **Hard cap 200 regras + soft warning 50.** Custo: workspace power-user
   bate o cap. Ganho: protege usuário comum de criar 500 regras
   conflitantes que matam debug.
8. **Gate dogfood antes do P4.** Custo: +7d wall-clock. Ganho: kill
   switch real antes de investir 4d em UX bonita pra feature sem
   adoção.

## Métricas de sucesso (KPI)

**Norte de saúde MVP (instrumentado em P3):**

- **Adoção dogfood (gate, semana 1 pós-P3):** CEO cria ≥5 regras
  persistentes, revert_rate ≤ 30%, ≥3 regras com ≥3 matches retroativos.
- **Saúde steady-state (60d pós-P4):**
  - `% transações categorizadas por learned_rule`: V1 mira ≥20% (V2
    mira ≥30%); medido em workspaces ativos.
  - `% manual_override`: cai naturalmente após onboarding mas **não
    vai a zero** — métrica de calibração; alerta de over-fitting fica
    em V2.C.
  - `revert_rate` agregado < 15% (V2 mira < 10%).
- **Adoção produto (proxy frontend):**
  - ≥40% dos workspaces ativos cria ≥1 regra em 30d pós-P4.
  - `time_to_rule` mediano < 7d desde primeiro override.

**Goodhart guardrail:** "subir % learned_rule" sozinho NÃO é métrica
de valor — pode subir por over-fitting silencioso. Sempre acoplado a
revert_rate baixo e manual_override saudável.

## Critérios de paridade obrigatória

- Workspace sem regras promovidas → comportamento E4 **idêntico** ao
  legado (goldens passam inalterados em P2).
- `TransactionOverride(source="manual")` existente → preservado
  intocado quando qualquer regra é criada/aplicada.
- Mês com `report_publication` viva (entregue por
  [[A11.report-publication]]) → re-categorização retroativa recusada
  (testado em P3).

## Handoffs e revisão

- **`senior-cto`:** revisa P1 (schema), P2 (contrato pipeline), P3 (API)
  antes do PR estrutural de cada fase.
- **`data-engineer`:** revisa migration P1, paridade goldens E4 em P2.
- **`product-designer`:** desenha mocks finais P4 (side-panel, heatmap,
  banner, badges); review pré-impl.
- **`product-manager`:** curador deste plano; opera o **gate dogfood**
  entre P3 e P4 com o CEO; decide promoção V1→V2 após 60d em produção.
- **`financial-planner`:** consultar se invariante de mês fechado
  precisar de ajuste em casos extremos (ex.: cliente pede re-cálculo
  retroativo explícito).

## Status atual

- [[ADR-186]] **Proposto** — aguarda revisão senior-cto + data-engineer
  (no PR de P1 ou anterior).
- [[ADR-187]] **Proposto** — aguarda revisão senior-cto + data-engineer
  em [[A11.report-publication]] (lane separada, sprint A11).
- A11 lane: [[A11.report-publication]] + track
  [report-publication-impl](../../sprint/A11/tracks/report-publication-impl.md)
  ✅ ready.
- A12 lane: [[A12.cat-learning-loop]] candidate (sprint abre quando A11
  fechar).
- P1-P4 tracks de A12: criados ao abrir A12.

## Conclusão / arquivamento

Quando MVP V1 (P1-P4 + gate dogfood) mergear em `main` com gates verdes:

1. Atualizar `status: done` no frontmatter deste plano (V1 entregue).
2. Decidir após 60d steady-state: promover V2 ou manter cortado.
3. Quando V2 (se houver) também mergear, OU quando decisão for
   "manter como V1 final":
   - `git mv docs/plan/CAT_LEARNING_LOOP/_README.md
     docs/archive/CAT_LEARNING_LOOP-YYYY-MM-DD.md`.
   - Adicionar entrada em `docs/archive/README.md` com data, motivo
     ("feature shipped — V1" ou "feature shipped + V2"), substituído
     por: nenhum.
   - Flippar [[ADR-186]] para `status: Decidido (A12)`.
