---
id: TRACK-category-overrides-ui-refactor
type: track
title: "Track Category Overrides W4 — UI refactor (CategoriesTab + useCategoriesAndMembers)"
sprint: A11
plan: PLAN-category-overrides-ux
status: consumed
created_at: "2026-05-10"
consumed_at: "2026-05-10"
agent_role: product-designer
tags:
  - type/track
  - sprint/a11
  - status/consumed
  - area/categorization
  - area/frontend
  - area/ux
---

# Track Category Overrides W4 — UI refactor

> **Lane ID:** category-overrides-ui-refactor
> **Plano canônico:** [docs/plan/CATEGORY_OVERRIDES_UX/_README.md](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md) §Wave 4
> **Branch prefix:** `agent/category-overrides-ui-refactor/*`
> **Depende de (todos mergeados em main antes de virar Ready for review):**
>
> - W1-T01 ([category-overrides-cache-fix](category-overrides-cache-fix.md)) — sem cache fix, edição da UI fica stale no E4.
> - W2-T01 ([category-overrides-schema-delta](category-overrides-schema-delta.md)) — DTO `template_version_used`/`latest_template_version` consumido pelo `AlertCircle`.
> - W3-T01 ([category-overrides-policy-adr](category-overrides-policy-adr.md)) — CLAUDE.md §"ADR Proposto antes de PR P0/P1".
>
> **Paralelo com:** nenhuma (lock-ordering crítico).

## Briefing

Hoje `../../../../frontend/src/app/(app)/config/CategoriesTab.tsx` consome `/config/categories` (legacy) — workspace novo abre tela vazia. Refatorar para `/config/category-overrides/resolved` (moderno, A7.3 / [ADR-137](../../../adr/137-catalog-override-resolver-para-categorization-e.md)) e expor edição amigável das 24 categorias default.

**Recomendações UX (já consensuadas com `product-designer`):**

- Chips em 3 estados (default/herdada · adicionada · removida-em-accordion) — Set diff client-side.
- Switch "Usar nesta família" (default ON) substitui ícone `Trash2` (mismatch — backend não destrói).
- Reset com toast undo 8s; modal só quando descarta keywords.
- Badge "Personalizada" condicional + filtro header "Apenas personalizadas".
- Sinal v2 desatualizada: ícone `AlertCircle` (`var(--semantic-warning)`) sem CTA — só visual.
- Botão "Adicionar categoria" sai em V1 (custom é feature separada).

## Coordenação cross-lane (PM, 2026-05-10)

**Hook arquitetural reservado para futura V2.A do [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md) §V2.A.** Custo marginal: ≤30min.

A sub-tab "Regras promovidas" (V2.A do learning loop, condicional a sinais de tração ≥30% adoção / revert_rate ≤15% / ≥10 workspaces em 60d) vai morar **na mesma `CategoriesTab.tsx`** que esta W4 está refatorando. Para não pagar refactor estrutural duas vezes:

- A tela deve usar **tabs/subnav extensível** (`<TabsList>` ou equivalente shadcn renderizado a partir de **array configurável** de `{id, label, content}`) — não layout flat hard-coded com 1 lista.
- V1 expõe **1 entrada** ("Categorias", o conteúdo desta W4). V2.A adiciona "Regras promovidas" sem refactor estrutural.
- **Não implementar** a sub-tab nem nenhum estado relacionado a `categorization_rules` — V1 NÃO toca o conceito de regra aprendida (ADR-186 / phase A12).
- Aceitação: code review do `product-designer` + leitura do componente confirmam que adicionar uma 2ª tab daqui 60d é **diff de array**, não refactor de layout.

Justificativa: PM review 2026-05-10 manteve A11.cat-overrides-ux e A12.cat-learning-loop em sprints separadas (gate dogfood do learning loop é kill switch real, A11 sobrecarregada com PLATFORM_REVIEW). Hook estrutural é o único acoplamento positivo entre as duas lanes — barateia retrabalho V2.A condicional sem importar risco da feature experimental.

## Escopo

### Frontend — read path

- `frontend/src/lib/api/config.ts`: nova função `listCategoriesResolved(workspaceId)` → `GET /workspaces/{id}/config/category-overrides/resolved`.
- `useCategoriesAndMembers.ts` (`../../../../frontend/src/app/(app)/transactions/_components/useCategoriesAndMembers.ts`): troca para `listCategoriesResolved`.

### Frontend — write path

- Mutations consomem:
  - `PUT /workspaces/{id}/config/category-overrides/{template_key}` — upsert.
  - `DELETE /workspaces/{id}/config/category-overrides/{template_key}` — disabled.
  - `POST /workspaces/{id}/config/category-overrides/{template_key}/reset` — apaga override.
- Endpoint legacy `/config/categories/{id}` PUT/DELETE/POST deixa de ser chamado.

### Frontend — UI

- `CategoryChipDiff` (novo componente em `frontend/src/components/categories/`): renderiza diff de keywords client-side via Set ops a partir de `default_keywords` + `keywords_override`.
- Substituir `Trash2` (linha ~310 atual) por `Switch` "Usar nesta família" (default ON, `var(--brand-primary)`). Categoria `disabled=true` renderiza com `opacity: 0.5`, continua na lista.
- Remover botão "Adicionar categoria" (linha ~220 atual).
- Badge "Personalizada" no header de cada categoria com override (`var(--surface-muted)` + texto `var(--brand-primary)`); filtro "Apenas personalizadas" no header da tela.
- Modal de confirmação só quando `reset` descarta keywords; toast `Padrão restaurado · Desfazer` 8s.
- `AlertCircle` (`var(--semantic-warning)`) ao lado da categoria quando `template_version_used < latest_template_version`. Tooltip explica em 1 frase, sem CTA.

### Frontend — instrumentação

- Adicionar log estruturado `category_override.created` em `frontend/src/lib/api/config.ts` ou via interceptor. Campos: `workspace_id` (sem PII), `template_key`, `field_changed` (`label`|`cap`|`keywords`|`active`).

### Backend — minimal

- Header `Deprecation: true` em `/config/categories` (1 linha em `backend/app/api/categories.py`) para sinalizar drift; sunset fica em lane futura `A12.cat-legacy-sunset`.

## Critério de aceite

- [ ] Workspace novo → `/config` → CategoriesTab mostra **24 categorias** com labels e keywords default (não tela vazia).
- [ ] Edição de label/cap/keyword/`disabled` persiste via `/category-overrides/{template_key}` e reflete na UI em <1s.
- [ ] Próxima execução E4 vê valor novo em <2s p95 (gate W1).
- [ ] Chips em 3 estados (Set diff client-side via `default_keywords`).
- [ ] Switch "Usar nesta família" substitui `Trash2`; categoria desabilitada com `opacity 0.5` continua visível.
- [ ] Botão "Adicionar categoria" removido em V1.
- [ ] Modal de confirmação **só** quando reset descarta keywords; toast undo 8s.
- [ ] Badge "Personalizada" condicional + filtro header.
- [ ] `AlertCircle` quando `template_version_used < latest_template_version` (W2 entrega o DTO).
- [ ] Evento `category_override.created` logado (sem PII, ADR-110).
- [ ] Header `Deprecation: true` em `/config/categories`.
- [ ] Vitest novo: render workspace novo mostra 24 categorias; render com override mostra badge.
- [ ] Playwright `@critical`: edit cap → save → reload → cap persistido.
- [ ] `dev/check_css_var_references.py` verde (sem `var(--xxx)` fantasma).
- [ ] Tabs/subnav em `CategoriesTab.tsx` renderizados a partir de **array configurável** de `{id, label, content}` (1 entrada em V1) — hook para V2.A do [PLAN-cat-learning-loop](../../../archive/CAT_LEARNING_LOOP-2026-07-08.md). Verificado em code review do `product-designer`.

## Arquivos esperados

- **Editado:** `frontend/src/app/(app)/config/CategoriesTab.tsx`
- **Editado:** `frontend/src/app/(app)/transactions/_components/useCategoriesAndMembers.ts`
- **Editado:** `frontend/src/lib/api/config.ts`
- **Novo:** `frontend/src/components/categories/CategoryChipDiff.tsx`
- **Editado:** `backend/app/api/categories.py` (header `Deprecation`)
- **Novo:** `frontend/src/app/(app)/config/__tests__/CategoriesTab.test.tsx`
- **Novo:** `frontend/e2e/category-overrides.spec.ts` (`@critical`)

## Testes

```bash
cd frontend && npm test -- --run
cd frontend && npm run test:e2e -- --grep @critical
pytest backend/tests/test_categories_api.py -q
pre-commit run --all-files
```

## Riscos

- **R1** — lixeira atual induz expectativa de delete; switch sem migração visual gradual pode confundir power-user. Mitigação: copy de tooltip/modal valida com `product-designer` antes do merge.
- **R2** — Set diff client-side falha em casos de keywords com whitespace/unicode invisível. Mitigação: normalizar (`.trim()`) antes do diff; teste cobre.
- **R3** — endpoint moderno tem performance diferente do legacy (Redis cache miss em workspace novo). Mitigação: medir latência p95 do GET resolved em workspace sem cache; alarme se >300ms.

## Ligações

- Plano: [PLAN-category-overrides-ux](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md)
- ADR canônica: ADR-185 (todos os §, mergeada via W3)
- ADRs relacionadas: [[ADR-076]] (design system), [[ADR-110]] (logging estruturado), [[ADR-137]] (template + override)
