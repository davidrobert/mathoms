---
id: ADR-224
type: adr
title: "`asset_catalog` + `lastro_moeda` per-ativo (catalog global + override per-workspace)"
status: Decidido
phase: A12
date: "2026-05-19"
decided_at: "2026-05-19"
relates_to:
  - "[[ADR-193]]"
  - "[[ADR-137]]"
  - "[[ADR-186]]"
  - "[[ADR-215]]"
  - "[[ADR-102]]"
  - "[[ADR-109]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 224"
  - "asset_catalog lastro_moeda"
  - "FU-2 exposicao cambial V2"
amended_at:
  - "2026-07-27"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/report
  - methodology/perini
  - methodology/auvp
  - phase/a12
  - status/decidido
  - type/adr
---

> **Emenda 2026-07-27 (RV2-08):** documenta o contrato de campos da posição E4 —
> valor canônico `valor_atual`, ticker canônico `ticker_norm`, sem campo `classe`.
> V1 e V2 liam `valor`/`ticker` inexistentes → exposição cambial zerava ativos
> internacionais (no-op silencioso desta ADR). Conformance; ver §Emenda ao final.

## Contexto

Sprint A12 entregou MVP V1 do Card "Exposição Cambial" (#322, Bloco G plan/RESIDENCIA_E_USO) via bucket `"Internacional"` em [[ADR-193]]. [`pipeline/domain/services/exposicao_cambial_analyzer.py`](../../pipeline/domain/services/exposicao_cambial_analyzer.py) agrega: `sum(caixa moeda ≠ BRL) + sum(posicao onde classify_asset.bucket == "Internacional")`. Footnote conhecida no card: "ETFs e fundos com lastro internacional não computados — em desenvolvimento".

**Limitação metodológica.** ICP do Mathoms é PJ alta renda BR. Esse perfil tipicamente tem:

- **ETFs B3 com lastro USD**: IVVB11 (S&P 500), BIVB11 (Treasury US Bonds), BIVA11 (VEA developed markets), NASD11 (Nasdaq-100), ACWI11 (MSCI ACWI), HASH11, SPXI11, IVVD11.
- **Fundos globais regulados CVM**: BTG Pactual Global, XP Global Equity, Itaú Global Dinâmico, Bradesco Global.
- **BDRs**: rastreiam ADRs/papéis estrangeiros — lastro USD genérico.
- **Stablecoins**: USDT, USDC, DAI — lastro USD efetivo.

Todos negociados em BRL na B3 mas com **lastro econômico USD**. Para "exposição cambial real" (proteção contra desvalorização BRL), o que importa é o lastro econômico do ativo, não a moeda de negociação. Hoje todos caem em buckets BR ("Outros", "Ações BR", "Fundos") porque [[ADR-193]] taxonomia classifica por categoria de produto, não por lastro econômico.

**Auditoria adjacente do schema.** [`backend/app/models/category_template.py`](../../backend/app/models/category_template.py) é **categorization tree** — rotula categoria (`acoes_br`, `fiis`, `internacional`), não ativos específicos. Adicionar `lastro_moeda` em `category_template` força a regra "todo ativo dessa categoria tem esse lastro" — quebra no momento que fundo X tem 70% USD / 30% BRL hedgeado (MIXED). Lastro é propriedade do **ativo específico** (ticker/CNPJ/keyword), não da categoria.

**[[ADR-215]] §6 é jurisprudência direta**: "Não invalida E5 inteiro ao trocar classificação". Mesmo argumento aqui — catalog ganha row pra novo ETF, usuário declara override, não pode invalidar E5 do workspace. Materializar lastro em E5 quebra idempotência.

## Decisão

Adotar **seis mudanças coordenadas** que materializam `lastro_moeda` como dado de ativo (não de categoria):

### 1. Tabela nova `asset_catalog` (não estender `category_template`)

```sql
CREATE TABLE asset_catalog (
  id UUID PRIMARY KEY,
  catalog_version INTEGER NOT NULL DEFAULT 1,
  ticker VARCHAR(12) NULL,              -- IVVB11, BIVB11 (preferido quando existe)
  cnpj VARCHAR(20) NULL,                -- fundo CVM 14 dígitos sem mask
  match_keyword VARCHAR(200) NULL,      -- fallback regex/substring sobre descricao
  asset_class VARCHAR(40) NOT NULL,     -- enum compartilhado com asset_classifier.BUCKETS
  lastro_moeda VARCHAR(8) NOT NULL,     -- 'BRL'|'USD'|'EUR'|'MIXED'|'OTHER'
  lastro_source VARCHAR(20) NOT NULL,   -- 'catalog'|'inferred'|'user_declared'
  notes TEXT NULL,                      -- link CVM, regulamento — auditoria humana
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT chk_lastro_moeda CHECK (lastro_moeda IN ('BRL','USD','EUR','MIXED','OTHER')),
  CONSTRAINT chk_match_at_least_one CHECK (
    ticker IS NOT NULL OR cnpj IS NOT NULL OR match_keyword IS NOT NULL
  )
);
CREATE UNIQUE INDEX uq_asset_catalog_ticker
  ON asset_catalog (catalog_version, ticker) WHERE ticker IS NOT NULL;
CREATE UNIQUE INDEX uq_asset_catalog_cnpj
  ON asset_catalog (catalog_version, cnpj) WHERE cnpj IS NOT NULL;
```

Pattern espelha `institution_catalog` (ADR-137 família). `catalog_version` permite bump v2/v3 sem rename de rows (consistente com `template_version` de [[ADR-137]] §"nunca rename de key").

**Por que não JSONB `lastro_metadata` de cara**: perde tipagem + perde index/CHECK. Forward-compat para `lastro_pct_breakdown` (fundos hedgeados): adiciona-se `lastro_metadata JSONB NULL` aditivo só quando MIXED real aparecer no ICP. YAGNI.

### 2. Override per-workspace em tabela separada

```sql
CREATE TABLE workspace_asset_overrides (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  asset_match_key VARCHAR(200) NOT NULL,   -- ticker|cnpj|descricao normalizada
  match_kind VARCHAR(20) NOT NULL,         -- 'ticker'|'cnpj'|'description'
  lastro_moeda VARCHAR(8) NOT NULL,
  override_source VARCHAR(20) NOT NULL,    -- 'user_manual'|'reconciliation'
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT uq_ws_asset_override UNIQUE (workspace_id, match_kind, asset_match_key),
  CONSTRAINT chk_ws_lastro CHECK (lastro_moeda IN ('BRL','USD','EUR','MIXED','OTHER'))
);
```

Espelha [[ADR-215]] §2 (`workspace_property_overrides`) — diff vs catalog global, FK no workspace, sticky por unique key. **Não estende** `workspace_category_overrides` porque `template_key` aponta para categoria, não ativo (confunde domínios).

Cria-se agora vazia; pattern consagrado, custo marginal. Resolver tem fallback gracioso quando tabela vazia (catalog global vence).

### 3. Seed YAML versionado executado via `op.execute` (atomic deploy)

Lista canônica V1 vive em `config/asset_catalog_seed_v1.yaml` (versionado). Migration estrutural lê o YAML e executa SQL INSERT via `op.execute` no mesmo upgrade — 1 deploy = 1 migration + 1 seed atomic.

Updates futuros viram nova migration `bump_asset_catalog_v2.py` inserindo `catalog_version=2`. Pattern análogo a `a5b6c7d8e9f0_seed_category_template_v1.py` (ADR-137 wave).

**Lista canônica V1 inicial** (financial-planner co-design 2026-05-19):

| Categoria | Cobertura | `lastro_moeda` |
|---|---|---|
| ETFs B3 USD | IVVB11, BIVB11, BIVA11, NASD11, ACWI11, HASH11, SPXI11, IVVD11, WRLD11 | USD |
| Fundos globais CVM | BTG Pactual Global, XP Global, Itaú Global Dinâmico, Bradesco Global (match por keyword) | USD |
| BDRs | Match por suffix ticker `34`/`35` (BDRs nivel I/II) | USD |
| Stablecoins | USDT, USDC, DAI | USD |

EUR mínimo na V1 (raro no ICP); entra quando aparecer demanda. Outros ativos sem match no catalog → fallback determinístico por categoria (`Internacional` → USD; resto → BRL).

### 4. Critério `MIXED` determinístico

`MIXED` = ativo com exposição declarada/conhecida a 2+ moedas onde **nenhuma** representa ≥70% do lastro econômico:

- Fundo "30% hedged USD, 70% RF BRL" → **BRL** (70% atinge cutoff).
- Fundo "50% S&P 500 + 50% Ibovespa" → **MIXED**.
- Fundo global multi-currency (US 50% + Europa 30% + Ásia 20%) → **USD** (USD domina ≥50%, sem outra moeda comparável; tratar como USD-dominante).

Cutoff 70% > 50% porque 50/50 é raríssimo na prática; quase todo fundo "mixed" tem dominância clara.

### 5. Read-time resolve em service-layer (não materializa em E5)

[[ADR-215]] §6 jurisprudência: catalog ganha row pra novo ETF, usuário declara override, não pode invalidar E5. Solução:

**Novo endpoint** `GET /v1/workspaces/{ws}/cards/exposicao-cambial` (response_model tipado por [[ADR-102]] R18):

1. Lê posições da última run E5 (artifact `analyze_finances`).
2. Lê `asset_catalog` (cacheable em Redis com TTL longo — invalida em seed novo) + `workspace_asset_overrides` (cacheable per-workspace, invalida em write).
3. Computa `exposicao_cambial = sum(caixa moeda ≠ BRL) + sum(posicao onde lastro_resolved(ativo) ≠ BRL)`.
4. Retorna `{ total_brl, breakdown_by_moeda, ativos_contribuintes, source_run_id, computed_at }`.

`lastro_resolved(ativo)`: **override per-workspace** > catalog match (ticker > cnpj > keyword) > fallback por categoria. Função pura em `backend/app/services/lastro_resolver.py`, testável isoladamente.

Card frontend chama o endpoint. **Não fetch direto do E5 artifact** — service-layer faz o join. Schema E5 intacto (goldens E5 verdes sem ajuste).

### 6. KPI honesto: 3 colunas no card (BRL / USD / Não-Classificada)

`exposicao_cambial.por_moeda` ganha 3ª bucket "Não-Classificada" agregando `MIXED + NULL`. KPI canônico:

```
% exposição USD = USD_explícito / (BRL_explícito + USD_explícito)   # exclui MIXED+NULL do denominador
```

Honesto: usuário vê "65% USD" e "12% não-classificado" separados. Tooltip "lastro não declarado" + CTA inline "Declarar lastro" → dropdown (BRL/USD/EUR/MIXED) → salva override imediato.

**Faixa recomendada ICP** (financial-planner co-design 2026-05-19): **20-30% USD** sobre investível efetivo (excluindo reserva de emergência). Abaixo de 10% = sub-diversificado; acima de 50% = sobre-exposto sem justificativa metodológica (meta em USD, residência futura). Render visual faixa, não número único; orientar, não prescrever.

Tooltip honesto adicional: "Esta análise considera apenas seu patrimônio investido. Sua exposição cambial real pode ser maior se sua receita ou empresa tem dependência de USD."

## Alternativas consideradas

- **(B) Coluna `lastro_moeda` em `category_template`.** Descartada — categoria != ativo; força "todo ativo dessa categoria tem esse lastro", quebra para MIXED.
- **(C) Estender `workspace_category_overrides` com `lastro_moeda_override`.** Descartada — `template_key` aponta para categoria, não ativo; confunde domínios.
- **(D) Materializar `exposicao_cambial` em E5 payload.** Descartada — invalida E5 ao mudar catalog/override (jurisprudência [[ADR-215]] §6).
- **(E) JSONB `lastro_metadata` desde V1.** Descartada — over-engineering; perde index/CHECK; YAGNI até MIXED real aparecer.
- **(F) LLM inferring `lastro_moeda` para ativos NULL.** Descartada para V1 — V3 quando volume justificar custo; hoje catalog humano-curado + override resolve >95% do ICP dogfood.
- **(G) Excluir ativos NULL da exposição cambial.** Descartada — subestimar é mais danoso que transparência; "Não-Classificada" + CTA preserva honestidade metodológica.

## Consequências

**Positivas:**
- ✅ ICP PJ alta renda passa a ver exposição cambial **real** (IVVB11 contado).
- ✅ Card V2 fecha gap metodológico documentado em footnote V1 (#322).
- ✅ Override per-workspace destrava fundo estruturado / FIP / offshore — usuário não fica refém do catalog global.
- ✅ Read-time resolve elimina stale by design (catalog atual + overrides atuais sempre vencem; sem re-runs massivos).
- ✅ Schema E5 intacto — goldens não regridem.
- ✅ Pattern arquitetural consistente com [[ADR-215]] (write em DB + read-time + override-per-workspace + catalog versionado).

**Negativas:**
- ⚠️ Tabela nova adiciona surface schema (`asset_catalog` + `workspace_asset_overrides` + seed v1). Custo de manutenção do catalog humano-curado quando novo ETF popular emerge.
- ⚠️ V1 não cobre EUR — early dogfood tudo USD; EUR entra quando demanda aparecer.
- ⚠️ Override per-workspace adiciona uma 2ª fonte de verdade. Mitigação: priority order documentado (override > catalog match > fallback categoria).

**Riscos:**

| Risco | Mitigação |
|---|---|
| Catalog seed humano-curado fica stale (novo ETF lançado, não no catalog) | `lastro_source='catalog'` + processo de bump v2 documentado em runbook; usuário tem override como fallback imediato. |
| Workspace com 30% ativos em "Não-Classificada" gera card "inútil" | UX inline "Declarar lastro" + override gravado em 1 clique resolve; financial-planner argumenta transparência > falsa precisão. |
| Cache de `asset_catalog` em Redis fica stale após bump v2 | Invalidação em deploy (TTL longo + flush manual no runbook); pattern análogo a `category_cache.invalidate_resolved_categories`. |
| Workspace dogfood `5@5.com` tem IVVB11 catalogado com lastro `USD` mas usuário discorda | Override per-workspace resolve em 1 clique; UI permite o flow. |
| Read-time resolve adiciona ~50ms latência no Card | Cacheable em Redis 1h; latência aceita para card de relatório (não path crítico). |

## Gates

- **Migration Alembic** `<rev>_create_asset_catalog_and_overrides.py` cria 2 tabelas + seed v1 via `op.execute` do YAML; downgrade dropa as tabelas (FK CASCADE no workspace cuida do resto).
- **Seed YAML** `config/asset_catalog_seed_v1.yaml` versionado; smoke test em `dev/check_asset_catalog_seed.py` valida integridade (todos ETFs B3 USD listados, sem duplicatas).
- **`lastro_resolver.resolve(asset)`** puro, ≤20 linhas, tested isoladamente com 6 cases: ticker hit, cnpj hit, keyword hit, override per-workspace, fallback por categoria, OTHER explicit.
- **Endpoint** `GET /v1/workspaces/{ws}/cards/exposicao-cambial` com `response_model=ExposicaoCambialResponse` ([[ADR-102]] R18); snapshot OpenAPI commitado ([[ADR-109]]).
- **Schema novo** `config/schemas/exposicao_cambial.schema.json` strict mode no CI.
- **Goldens E5/E6** verdes (schema E5 intacto; analyzer existente preservado, novo endpoint é layer acima).
- **Cache Redis** para catalog (TTL 1h, invalida em deploy de seed v2) + per-workspace overrides (invalida em write — segue `category_cache.invalidate_resolved_categories`).
- **Integration test** `backend/tests/integration/test_exposicao_cambial_resolver.py`: workspace com IVVB11 + USD em Wise + override `user_manual` em fundo X → `exposicao_cambial` bate centavo.
- **Frontend** Card V2 consome novo endpoint; remove footnote V1 "em desenvolvimento"; UI inline "Declarar lastro" com dropdown; faixa visual 20-30% recomendada.
- **Telemetria** mínima: `lastro_override.set_total{lastro_moeda, source}`, `exposicao_cambial.card_view_total`.

## Implementação

Entregue end-to-end em **Sprint A12** (5 PRs sequenciais):

- **#325** PR-A — schema: tabela `asset_catalog` (catalog global versionado) + `workspace_asset_overrides` (diff per-workspace, pattern [[ADR-215]]) + seed v1 atomic (21 ativos canônicos: 9 ETFs B3 USD + 4 famílias fundos CVM + 5 top BDRs + 3 stablecoins).
- **#326** PR-B — service-layer: `backend/app/services/lastro_resolver.py` puro (priority override > ticker > cnpj > keyword > fallback por asset_class) + endpoint `GET /v1/workspaces/{ws}/cards/exposicao-cambial` (read-time service-layer, schema E5 intacto). 19 tests.
- **#327** PR-C — CRUD overrides: POST/DELETE/GET `/overrides` (sticky pattern ADR-215) + frontend api client TypeScript em `frontend/src/lib/api/exposicaoCambial.ts`. 7 tests.
- **#328** PR-D — frontend foundations: hook `useExposicaoCambialV2(workspaceId)` SWR-style com `declare`/`remove` refetch automático. 11 tests Vitest.
- **#330** PR-E — Card V2 UI: `ExposicaoCambialCard` consome hook quando recebe `workspaceId`; section "Ativos contribuintes" com badges por `lastro_source`; `LastroDeclareDropdown` inline. Wire-up via `WorkspaceProvider` context em `S1PatrimonioSection`. 4 tests Vitest.

**Defer (não-bloqueante):** telemetria client-side + Playwright `@critical` adiados — projeto sem padrão de events frontend ainda; Playwright env precisa setup. Total: 26 tests backend + 15 tests frontend + OpenAPI snapshot atualizado.

## Referências

- [[ADR-193]] — taxonomia canônica classes de ativo no E5 (bucket "Internacional" é base do MVP V1)
- [[ADR-137]] — catalog + override resolver para categorization (pattern espelhado)
- [[ADR-186]] — override sticky pattern (mesma família de decisão)
- [[ADR-215]] — `workspace_property_overrides` (pattern direto: override DB-first, read-time, não invalida payload upstream)
- [[ADR-102]] R18 — `response_model` explícito
- [[ADR-109]] — snapshot OpenAPI
- Co-design 2026-05-19: `financial-planner` (lista canônica V1 + critério MIXED + faixa 20-30% USD ICP), `data-engineer` (schema asset_catalog nova + seed YAML via op.execute + override pattern ADR-215 + read-time service-layer + cache strategy)

## Emenda — contrato de campos da posição E4 (2026-07-27, RV2-08)

O binding de campos assumido em §5 não batia com o output real do consolidador de
investimentos (`investments_consolidator.py`). Posições de `investimentos_atuais.dados`
carregam: **valor canônico** = `valor_atual` (não `valor`/`valor_31_12_ano_base`, que só
existem em posições baseline-shaped legadas); **ticker canônico** = `ticker_norm` (não
`ticker`/`codigo`); e **sem campo `classe`** — o fallback categórico é derivado read-time
via `classify_asset` (last-resort, depois de catalog/override/ticker/cnpj/keyword).

Consequência do binding errado (pré-emenda): tanto o V1 (`exposicao_cambial_analyzer.py`,
instant-render no E5) quanto o V2 (`exposicao_cambial_v2.py`, autoritativo) liam 0 para
toda posição e o match de catalog nunca disparava → a iniciativa desta ADR (computar
ETFs/fundos com lastro USD) ficava no-op silencioso, com `exposicao_cambial.total_brl`
igual ao total só-caixa.

**Correção (conformance, não reabre a decisão):** value-chain `valor_atual → valor_total
→ valor → valor_31_12_ano_base` e ticker-chain `ticker_norm → ticker → codigo` nos dois
analyzers; fallback de classe via `classify_asset`. V2 permanece a fonte de verdade (§5);
tornar o número autoritativo no PDF server-side (wire de `workspaceId` no render) é
follow-up rastreado em [[PLAN-pipeline-review-r2]] (RV2-08). Regressão:
`tests/unit/pipeline/test_exposicao_cambial_analyzer.py::test_rv2_08_ativo_le_valor_atual_nao_zero`
+ `backend/tests/test_exposicao_cambial_v2_binding.py`.
