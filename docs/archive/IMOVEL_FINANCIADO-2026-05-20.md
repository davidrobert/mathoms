---
id: PLAN-imovel-financiado
type: plan
title: "Imóvel financiado — agregado Debt persistido + property_market_value override (FU-3 Sprint A12)"
status: done
sprint_origem: A12
sprint_atual: A15
sprints_envolvidas: ["A15"]
created_at: "2026-05-19"
last_review: "2026-05-20"
archived_at: "2026-05-20"
adrs_canonical:
  - "[[ADR-227]]"
tags:
  - type/plan
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/backend
  - area/frontend
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - sprint/a15
  - status/done
---

# Plano canônico — Imóvel financiado (FU-3 do Sprint A12)

> Plano multi-fase para criar agregado `Debt` persistido + tabela
> `property_market_value` versionada + resolver `valor_efetivo` no
> `PatrimonioCalculator`, fechando o último follow-up da Sprint A12
> ([[ADR-215]] §Follow-ups). Decisão arquitetural em [[ADR-227]].

## Origem

Sprint A12 entregou ADR-215/222/223/224/225/226 — classificação por
imóvel + `imoveis_no_if` per-workspace + default conservador. ADR-215
§Follow-ups deixou explícito o débito:

> Imóvel financiado com saldo devedor distorce patrimônio bruto. Fora
> do escopo desta ADR. Follow-up: `valor_mercado` + linkagem
> `saldo_financiamento` ao passivo correspondente. ADR futuro.

Auditoria 2026-05-19 identificou dois bugs silenciosos derivados:

1. **Bug 1** — `patrimonio_calculator._split_imoveis` usa `valor_irpf`
   (custo histórico). Apto declarado em 2018 R$ 800k, mercado hoje
   R$ 1,2M → relatório mostra 800k bruto. Mascara alavancagem.
2. **Bug 2** — Quando `imoveis_no_if=true` (cat_2 locado), `investivel_efetivo`
   usa `valor_irpf` no numerador, mas yield é calculado sobre `valor_mercado`
   no denominador. Capital econômico investido (1,2M − 300k saldo) ≠
   IRPF declarado (800k). `progresso_if` matematicamente errado.

Co-design 2026-05-19 com 4 especialistas em paralelo:

- **`financial-planner`** — invariante de apresentação (cat_2 bruto na
  tabela, líquido apenas em `investivel_efetivo`); TTL sem fallback
  automático; conflito declarativo IRPF↔per-property.
- **`senior-cto`** — boundary Property↔Debt (FK opcional, `ON DELETE RESTRICT`
  contra órfão silencioso); resolver puro module-level com Protocol no
  consumer; `RealEstateValuationContext` separado do `PatrimonioConfig`.
- **`data-engineer`** — schema versionado append-only; backfill em script
  separado da Alembic (`dev/backfill_debt_from_baseline.py` com `--dry-run`);
  partial unique index para idempotência; índices compostos pro calculator.
- **`product-designer`** — subseção em MembersTab + nudge contextual no
  card S4; soft TTL; dropdown explícito (não heurística) para linkagem;
  tela `/imoveis/financiamentos-review` para batch review post-migration;
  `percentual_atribuicao_imovel` para co-propriedade.

## Objetivo

Após este plano:

- Usuário declara `valor_mercado` por imóvel investimento na MembersTab
  (subseção opcional + nudge contextual quando delta >15%).
- Sistema persiste declarações em `property_market_value` versionada,
  com lookup via resolver puro injetado em `PatrimonioInputs`.
- Agregado `Debt` modela todas as classes de passivo (financiamento
  imobiliário, CDC, consignado, cartão rotativo, outros) com FK
  opcional a `PropertyIdentity` (`ON DELETE RESTRICT`).
- `investivel_efetivo` usa líquido econômico
  `max(0, valor_efetivo − saldo_devedor)` por imóvel gerador (locado/comercial)
  quando `imoveis_no_if=true`.
- Tabela de composição patrimonial preserva valor bruto em cat_2;
  drill-down expõe breakdown `Valor IRPF | Valor Mercado | Saldo Devedor | Líquido`.
- Migration extrai `total_dividas` baseline → rows Debt com
  `needs_review=true` (sem heurística de atribuição); UI batch review
  pavimenta limpeza pós-deploy.

## Invariantes não-negociáveis

1. **`saldo_devedor_cents BIGINT`** ([[ADR-090]]) — proibido `float`.
2. **`ON DELETE RESTRICT`** em `Debt.property_id` — órfão silencioso
   é classe inteira de bug em fintech.
3. **`needs_review=true`** em rows de migration — toda Debt extraída
   do baseline IRPF exige confirmação humana antes de afetar
   `investivel_efetivo`.
4. **Heurística nunca atribui Debt a property** — apenas user-driven
   via dropdown explícito.
5. **TTL sem fallback automático** — após 12m, banner persistente;
   sistema mantém valor declarado até user atualizar.
6. **`PatrimonioCalculator` puro** — recebe `RealEstateValuationContext`
   pré-carregado via `PatrimonioInputs`; nenhum I/O ou cache in-memory
   ([[ADR-111]]).
7. **Per-property vence agregado IRPF** quando ambos existem; warning
   de domínio tipado ([[ADR-097]] D1) quando ratio >1.1.

## Pré-requisitos bloqueantes

| # | Bloqueio | Origem | Status |
|---|---|---|---|
| PR-1 | [[ADR-227]] mergeada como `Proposto` | CLAUDE.md §"Política operacional" | ⏳ esta sprint, antes de PR-A |
| PR-2 | [[ADR-215]] em produção (`property_identity` + `WorkspacePropertyOverride`) | A12 | ✅ mergeada em PR [#281](https://github.com/davidrobert/mathoms/pull/281) |
| PR-3 | [[ADR-216]] trilho `valor_imovel_origem` em `real_estate_metrics.py` | A12 | ✅ implementado nos PRs S4 #280-#305; sem código populando `"mercado"` |
| PR-4 | [[ADR-225]] dedup de `PropertyIdentity` consistente | A12 | ✅ mergeada em PR [#333](https://github.com/davidrobert/mathoms/pull/333) |

## Ondas (5 PRs sequenciais, ~10d eng)

### Onda 1 — Schema + repos + models (PR-A)

**Objetivo:** persistência pronta sem mudança de runtime ainda.

**Entregáveis:**

- Migration Alembic `CREATE TABLE debt` + `CREATE TABLE property_market_value`
  (zero UPDATE — backfill é Onda 2).
- Modelos SQLAlchemy em `backend/app/models/debt.py` + extensão de
  `backend/app/models/property_identity.py`.
- Repos em `backend/app/repositories/debt.py` +
  `backend/app/repositories/property_market_value.py`.
- Testes unit cobrindo CRUD + UNIQUE constraints + CHECK constraints +
  partial unique index de migration idempotency.
- `docs/reference/DB_SCHEMA_REFERENCE.md` regenerado.

**Gates:** suíte verde + `pre-commit run --all-files` + migration
`downgrade()` faz DROP limpo (test).

**Estimativa:** ~2d eng.

### Onda 2 — Backfill script + audit log (PR-B)

**Objetivo:** extrair `total_dividas` baseline → rows Debt sem afetar
runtime.

**Entregáveis:**

- `dev/backfill_debt_from_baseline.py` com flags `--workspace-id`,
  `--dry-run` (default), `--apply`.
- Audit em `storage/<workspace>/logs/debt_migration_audit.json`.
- Partial unique index `uq_debt_migration_source` garante re-run safe.
- Test integration com workspace seed: 1ª run dry-run reporta N rows;
  2ª run `--apply` persiste; 3ª run `--apply` é no-op.
- Documentação em `docs/reference/RUNBOOK.md` §"Backfill de Debt".

**Gates:** workspace dogfood `5@5.com` migrado em dry-run + apply;
audit log inspecionado; idempotência verificada.

**Estimativa:** ~1d eng.

### Onda 3 — Calculator + resolver puro (PR-C)

**Objetivo:** runtime usa `valor_efetivo` + líquido em `investivel_efetivo`.

**Entregáveis:**

- `pipeline/domain/services/real_estate_valuation_resolver.py` —
  resolver puro com `RealEstateValuationContext` value object.
- Adapter em `backend/app/services/real_estate_valuation_adapter.py`
  carrega DB → context (2 SELECTs por workspace, `DISTINCT ON` para
  market_values).
- `PatrimonioCalculator` consome `RealEstateValuationContext` via
  `PatrimonioInputs.valuation_context` (opcional para retrocompat).
- `_compute_investivel_efetivo` usa líquido por imóvel gerador.
- Payload E5 ganha `source_valor: "mercado"|"irpf"` + `staleness_days`
  aditivos.
- Schema `config/schemas/e5_analysis.schema.json` bumpa version.
- Goldens E5 atualizados.
- Warning tipado `DebtVsIrpfDeclaracaoConflict` emitido quando ratio >1.1.

**Gates:**

- Test paridade: workspace sem `property_market_value` declarado →
  comportamento idêntico ao atual (fallback `valor_irpf`).
- Test novo: imóvel financiado com market_value declarado + Debt
  vinculada → `investivel_efetivo` usa
  `max(0, valor_mercado − saldo_devedor)`.
- `dev/check_pipeline_boundaries.py` verde.

**Estimativa:** ~3d eng.

### Onda 4 — API endpoints + OpenAPI snapshot (PR-D)

**Objetivo:** CRUD pronto pra UI consumir.

**Entregáveis:**

- `GET /v1/workspaces/{id}/debts` (list)
- `POST /v1/workspaces/{id}/debts` (create)
- `PATCH /v1/debts/{debt_id}` (update — incluindo property_id link)
- `DELETE /v1/debts/{debt_id}` (delete)
- `GET /v1/workspaces/{id}/property-market-values` (list)
- `POST /v1/workspaces/{id}/property-market-values` (create — append-only)
- `PATCH /v1/property-market-values/{id}/supersede` (marca erro)
- DTOs Pydantic + `response_model` explícito ([[ADR-109]] R18).
- Snapshot OpenAPI atualizado (`make update-openapi-snapshot`).
- Test integration para cada endpoint + edge cases (RESTRICT em
  property deletion, percentual_atribuicao bounds).

**Gates:** OpenAPI snapshot diff commitado;
`backend/tests/test_openapi_response_models.py` verde.

**Estimativa:** ~1.5d eng.

### Onda 5 — Frontend: form, batch review, drill-down card (PR-E)

**Objetivo:** UI completa pra cutover end-to-end.

**Entregáveis:**

- Subseção `MarketValueInline` em `MembersTab` — campo `valor_mercado`
  + `valuation_date` por imóvel locado/comercial.
- Nudge contextual em `RealEstateYieldCard` (S4) quando delta >15% E
  `imoveis_no_if=true` E `classification ∈ {locado, comercial}`.
- Componente `RealEstateBreakdownPanel` (drill-down card) — modal/sidesheet
  com `Valor IRPF | Valor Mercado | Saldo Devedor | Líquido Econômico`,
  via `<MonetaryValue/>` tabular-nums.
- Página `/imoveis/financiamentos-review` — tabela de Debts com
  `needs_review=true`, dropdown por linha, bulk action "não vincular
  a imóvel".
- Form Debt com `percentual_atribuicao_imovel` condicional (só quando
  property tem >1 cotitular).
- Test E2E Playwright fluxo crítico (`@critical`): declarar valor_mercado →
  vincular Debt → verificar patrimônio + IF atualizados.
- Test Vitest + a11y nos componentes novos.

**Gates:** `cd frontend && npm test -- --run` + `npm run test:e2e`
verde; snapshots Playwright capturados.

**Estimativa:** ~2.5d eng.

## Coordenação entre ondas

- **Onda 1 → 2**: schema precisa estar mergeado para backfill rodar.
- **Onda 2 → 3**: backfill em dogfood antes do calculator novo evita
  goldens E5 quebrarem.
- **Onda 3 → 4**: API consome `RealEstateValuationContext`, depende
  do resolver.
- **Onda 4 → 5**: frontend consome endpoints; sem PR-D, PR-E não roda.
- **Paralelismo possível:** Onda 1 + 2 em sequência, Onda 3 + 4 em
  paralelo (calc e API independentes do schema mergeado), Onda 5 espera 4.

## Risco e mitigação

| Risco | Mitigação |
|---|---|
| Goldens E5 quebram em massa pós-Onda 3 | Test paridade explícito em workspace sem declaração; cutover por workspace via feature flag se necessário. |
| Workspace existente com `total_dividas` errado | Backfill em dry-run + audit log; usuário revisa antes de affecting runtime via UI batch review. |
| Co-propriedade familiar com debt no nome de 1 cônjuge | `percentual_atribuicao_imovel` opcional; UI exposta só quando cotitulares >1. |
| Mudança visível em KPIs (patrimônio + IF) pós-deploy | Banner explicativo no relatório pós-cutover; telemetria mede `Δ` por workspace para auditar. |
| Suíte E2E lenta após adicionar @critical | Marca específica de FU-3 (`@property-finance`) para CI gate; perfil completo só em pre-merge. |

## Telemetria pós-deploy

- `mathoms.real_estate.valor_mercado.declarations_count` — quantas
  declarações foram feitas por workspace.
- `mathoms.real_estate.debt.link_to_property_rate` — % de Debt com
  `property_id NOT NULL`.
- `mathoms.real_estate.kpi_delta_pre_post_cutover` — `Δ` em
  patrimônio bruto + `investivel_efetivo` por workspace na primeira
  semana pós-deploy.

## Critérios de "concluído" do plano

1. PRs A-E mergeados em `main` com CI verde (CLAUDE.md §"Concluído").
2. ADR-227 flippada `Proposto → Decidido (A15)` em PR de cleanup.
3. Workspace dogfood `5@5.com` migrado + batch review concluído.
4. Goldens E5 atualizados commitados.
5. Snapshot OpenAPI atualizado.
6. `DB_SCHEMA_REFERENCE.md` regenerado.
7. CHANGELOG entry em `docs/CHANGELOG.md`.
8. Smoke test humano em [docs/reference/SMOKE_TEST_HUMAN.md](../../reference/SMOKE_TEST_HUMAN.md)
   atualizado se fluxo novo de declaração entrou no scope.

## Referências

- [[ADR-227]] — decisão arquitetural canônica.
- [[ADR-215]] §Follow-ups — origem do FU-3.
- [[ADR-216]] §D6 — trilho `valor_imovel_origem` já entregue,
  agora populado.
- [[ADR-142]] — invariante anti-dupla-contagem em IF;
  `investivel_efetivo` é o lugar do líquido econômico.
- [[ADR-222]]/[[ADR-223]] — toggle per-workspace + default
  conservador.
- [[ADR-225]] — `codigo_rfb` invariante; Debt.property_id referencia
  UUID interno de `PropertyIdentity`.
- Plan S4 entregue: [PLAN-s4-real-estate-enrichment](../S4_REAL_ESTATE_ENRICHMENT/_README.md).
- Co-design 2026-05-19: 4 agentes em paralelo (financial-planner,
  senior-cto, data-engineer, product-designer); síntese consumida
  pela ADR-227.
