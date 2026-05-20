---
id: TRACK-a15-fu3-onda5-frontend
type: track
title: "Track A15 FU-3 Onda 5 — Frontend: form, batch review, drill-down card"
sprint: A15
plan: PLAN-imovel-financiado
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: product-designer
tags:
  - type/track
  - sprint/a15
  - status/ready
  - area/frontend
  - area/ux
  - area/relatorio
---

# Track A15 FU-3 Onda 5 — Frontend cutover

> **Lane:** Sprint A15 · **Plano canônico:**
> [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 5
> · **ADR canônica:** [[ADR-227]] §D3 (apresentação dual) + §D5 (TTL soft)
> · **Branch prefix:** `agent/a15-fu3-onda5-frontend/*`
> · **Pré-requisito externo:** Onda 4 mergeada (endpoints CRUD prontos) + Onda 3 mergeada (payload E5 com `source_valor`/`saldo_devedor_brl`).
> · **Última onda — fecha sprint.** Após merge, abrir PR de cleanup flippando [[ADR-227]] `Proposto → Decidido (A15)`.

## Briefing

UI completa para cutover end-to-end ([[ADR-227]] §D3 apresentação dual + §D5 TTL soft). Cinco peças coordenadas:

1. **Subseção `MarketValueInline` em MembersTab** — campo `valor_mercado` + `valuation_date` opcional por imóvel locado/comercial (filtra por `classification` de ADR-215). Salva via POST `/property-market-values` (append-only — cada save cria entry).

2. **Nudge contextual em `RealEstateYieldCard` (S4)** — banner discreto quando `Δ valor_mercado vs valor_irpf > 15%` E `imoveis_no_if=true` E `classification ∈ {locado, comercial}`. Copy não-infantil: "Yield calculado sobre valor declarado no IRPF (R$ 800k). Se o valor de mercado mudou, atualize para refletir retorno real." CTA leva à MembersTab subseção.

3. **`RealEstateBreakdownPanel`** (drill-down card) — modal/sidesheet ao clicar em row da tabela de patrimônio. Mostra `Valor IRPF | Valor Mercado | Saldo Devedor | Líquido Econômico` em colunas, com `<MonetaryValue/>` tabular-nums (JetBrains Mono). Headers Plus Jakarta Sans. Footnote explicando metodologia (cat_2 bruto na tabela, líquido em IF) para acomodar invariante ADR-227 §D3.

4. **Página `/imoveis/financiamentos-review`** — tabela com Debts `needs_review=true`, dropdown por linha pra atribuir property_id (consome GET `/debts?needs_review=true` + PATCH `/debts/{id}`). Bulk action "Não vincular a imóvel" (PATCH em batch com `property_id=null` + `needs_review=false`). Pattern reuso: `DocumentReviewQueue` se existir.

5. **Form Debt completo (`DebtForm`)** com `percentual_atribuicao_imovel` condicional — input só aparece quando property selecionada tem `cotitulares.length > 1` (cobre co-propriedade familiar com debt no nome de 1 cônjuge).

**Telemetria de adoção** instrumentada nesta onda:
- `mathoms.real_estate.valor_mercado.declarations_count` — incrementa em POST `/property-market-values`.
- `mathoms.real_estate.debt.link_to_property_rate` — % de Debt com `property_id NOT NULL`.
- `mathoms.real_estate.kpi_delta_pre_post_cutover` — `Δ` em patrimônio bruto + `investivel_efetivo` por workspace (calculado em comparação com snapshot pré-deploy).

**Staleness badge** ([[ADR-227]] §D5 — soft TTL):
- 0-12m: sem badge.
- 12-24m: `<Badge variant="warning">` "atualizado há N meses" + nudge contextual.
- >24m: `<Badge variant="critical">` + nudge mais visível.

## Critério de aceite (do plano §Onda 5)

- [ ] **`MarketValueInline`** em `frontend/src/components/members/MarketValueInline.tsx`:
  - Renderiza apenas para imóveis com `classification ∈ {locado, comercial}` (filter via override DB).
  - Form com `valor_mercado_brl` (`<MonetaryInput/>`) + `valuation_date` (DatePicker, default today).
  - POST `/v1/workspaces/{ws_id}/property-market-values` no submit.
  - Lista valores anteriores (GET) com botão "marcar como erro" (PATCH supersede).
- [ ] **Nudge em `RealEstateYieldCard`** (`frontend/src/components/report/cards/RealEstateYieldCard.tsx`):
  - Condicional `Δ >15% AND imoveis_no_if AND classification ∈ {locado, comercial}`.
  - Copy + CTA para MembersTab.
  - Banner usa `var(--semantic-info)` ou `var(--semantic-warning)` conforme delta.
- [ ] **`RealEstateBreakdownPanel`** (`frontend/src/components/report/RealEstateBreakdownPanel.tsx`):
  - Modal/sidesheet com 4 colunas (`Valor IRPF | Valor Mercado | Saldo Devedor | Líquido`).
  - Mobile (<md): accordion com `Líquido` como header + 3 valores no detalhe.
  - `<MonetaryValue/>` tabular-nums; sem hex literal (apenas `var(--*)`).
  - Footnote explicando metodologia.
- [ ] **Tela `/imoveis/financiamentos-review`** (`frontend/src/app/imoveis/financiamentos-review/page.tsx`):
  - Lista Debts com `needs_review=true`.
  - Dropdown por linha com imóveis do workspace.
  - Bulk action "Não vincular a imóvel".
  - Empty state quando 0 pendentes.
- [ ] **`DebtForm`** (`frontend/src/components/debts/DebtForm.tsx`):
  - Campos: `tipo`, `descricao`, `saldo_devedor_brl`, `parcela_mensal_brl`, `taxa_juros_aa`, `prazo_meses_restantes`, `data_contratacao`, `family_member_id`, `property_id`, `percentual_atribuicao_imovel`.
  - `percentual_atribuicao_imovel` aparece **somente quando** property tem `>1 cotitular` (default 100%, range 0-100).
- [ ] **Telemetria** instrumentada via `frontend/src/lib/telemetry.ts` (ou equivalente).
- [ ] **Badge staleness** componente em `frontend/src/components/report/MarketValueStaleness.tsx`.
- [ ] **E2E Playwright** `@property-finance` (CLAUDE.md §Test suite):
  - Fluxo crítico: declarar valor_mercado → vincular Debt → ver patrimônio + IF atualizados.
  - Batch review: criar Debt via API, abrir review page, atribuir property, verificar removida da lista.
- [ ] **Unit Vitest + a11y** nos componentes novos.
- [ ] `cd frontend && npm test -- --run` verde.
- [ ] `cd frontend && npm run test:e2e` verde (perfil `@critical` inclui `@property-finance`).
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

**Novos:**

- `frontend/src/components/members/MarketValueInline.tsx`
- `frontend/src/components/report/RealEstateBreakdownPanel.tsx`
- `frontend/src/components/report/MarketValueStaleness.tsx`
- `frontend/src/components/debts/DebtForm.tsx`
- `frontend/src/components/debts/DebtList.tsx`
- `frontend/src/app/imoveis/financiamentos-review/page.tsx`
- `frontend/src/lib/api/debts.ts` (client API tipado)
- `frontend/src/lib/api/property-market-values.ts`
- `frontend/tests/components/MarketValueInline.test.tsx`
- `frontend/tests/components/RealEstateBreakdownPanel.test.tsx`
- `frontend/tests/components/DebtForm.test.tsx`
- `frontend/e2e/property-finance/declarar-valor-mercado.spec.ts` (`@property-finance` `@critical`)
- `frontend/e2e/property-finance/batch-review.spec.ts` (`@property-finance`)

**Editados:**

- `frontend/src/components/members/MembersTab.tsx` — incluir `MarketValueInline`.
- `frontend/src/components/report/cards/RealEstateYieldCard.tsx` — nudge contextual.
- `frontend/src/components/report/PatrimonioTable.tsx` (ou equivalente) — onClick row → abrir `RealEstateBreakdownPanel`.
- `frontend/src/generated/*` — codegen atualizado pós-OpenAPI snapshot bump.

## Decisões já fechadas (do co-design 2026-05-19 — `product-designer`)

- **Combinação (C)+(B) sem pop-up** — subseção sempre disponível em MembersTab + nudge contextual no card S4 quando delta material. **Não pop-up pós-classificação** — viola JTBD (usuário entrou pra classificar, não avaliar).
- **Soft TTL** — badge visual de staleness; nunca trocar fonte automaticamente ([[ADR-223]] anti-padrão).
- **Dropdown explícito** para linkagem Debt↔property — sem heurística (Nielsen #3 user control).
- **Coluna extra na tabela patrimônio + card drill-down** (Bloomberg/private banking padrão) — densidade alta calibrada para ICP HENRY/UHNW. Mobile colapsa em accordion.
- **Líquido como primário não foi adotado** — `financial-planner` venceu: bruto na tabela (preserva invariante categoria=ativo bruto, passivo=bucket separado). Drill-down expõe breakdown.
- **`percentual_atribuicao_imovel` condicional** — input só quando `cotitulares > 1`; default 100% silencioso. Documentar como "rateio simples — para split complexo, edite manualmente".
- **Tela batch review dedicada** (`/imoveis/financiamentos-review`) — não dialog modal; é fluxo de admin pós-migration.
- **Sem hex literal** — todos os componentes usam `var(--*)` ou tokens do design system ([[ADR-076]]).

## Testes (comandos exatos)

```bash
# Frontend unit
cd frontend && npm test -- --run

# E2E perfil property-finance
cd frontend && npm run test:e2e -- --grep "@property-finance"

# E2E perfil completo (pré-merge)
cd frontend && npm run test:e2e

# Snapshot visual (relatório nativo) — caso card S4 mude com nudge
cd frontend && npm run test:visual

# A11y
cd frontend && npm run test:a11y

# Pre-commit
pre-commit run --all-files
```

## Riscos

- **R1** — Mudança visível em KPIs pós-cutover sem aviso. **Mitigação:** banner explicativo no relatório pós-deploy ("Atualizamos o cálculo de patrimônio para considerar valor de mercado e dívidas vinculadas. Saiba mais."); telemetria mede `Δ` por workspace.
- **R2** — Suíte E2E lenta com `@property-finance` adicionado ao perfil `@critical`. **Mitigação:** marca específica permite rodar isoladamente; perfil completo só em pre-merge gate.
- **R3** — Codegen `frontend/src/generated/` desincronizado se OpenAPI snapshot (Onda 4) não foi atualizado. **Mitigação:** `npm run codegen` no setup do PR; pre-commit hook detecta drift.
- **R4** — `percentual_atribuicao_imovel` condicional pode esconder input legítimo se `cotitulares` for fetched assíncronamente. **Mitigação:** loader state explícito; só renderiza form quando dado carregado.
- **R5** — Batch review com 50+ Debts em workspace antigo: paginação obrigatória. **Mitigação:** dropdown lazy-load se >20 Debts; bulk action por página.
- **R6** — Mobile UX da coluna extra pode quebrar tabela patrimônio existente. **Mitigação:** breakpoint accordion em <md já consagrado; test responsivo em Playwright.

## Ligações

- Plano canônico: [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 5
- ADR canônica: [[ADR-227]] §D3 + §D5
- Sprint MOC: [[MOC-sprint-a15]]
- Onda 1 (pré-req): [a15-fu3-onda1-schema](a15-fu3-onda1-schema.md)
- Onda 3 (pré-req): [a15-fu3-onda3-calculator](a15-fu3-onda3-calculator.md) — payload E5 com `source_valor`
- Onda 4 (pré-req): [a15-fu3-onda4-api](a15-fu3-onda4-api.md) — endpoints consumidos
- ADRs relacionados: [[ADR-076]] (design system + codegen), [[ADR-129]] (renderer único React), [[ADR-208]] (gating Free/Premium — drill-down provavelmente Premium)
- Pattern reuso: `RealEstateYieldCard` (consumidor downstream do nudge), `MembersTab` (subseção sibling à classificação ADR-215), padrão `DocumentReviewQueue` se existir (batch review).
- DoD da sprint: após merge, abrir PR de cleanup flippando [[ADR-227]] `Proposto → Decidido (A15)` + changelog entry em `docs/sprint/A15/changelog/`.
