---
id: ADR-223
type: adr
title: "Default conservador `imoveis_no_if=false` para workspaces novos + banner contextual"
status: Proposto
phase: A13
date: "2026-05-19"
relates_to:
  - "[[ADR-222]]"
  - "[[ADR-142]]"
  - "[[ADR-215]]"
  - "[[ADR-186]]"
  - "[[ADR-102]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 223"
  - "imoveis-no-if default false"
  - "FU-1 imoveis_no_if conservador"
tags:
  - area/methodology
  - area/persistence
  - area/report
  - area/multitenancy
  - methodology/perini
  - methodology/auvp
  - phase/a13
  - status/proposto
  - type/adr
---

## Contexto

[[ADR-222]] (Decidido 2026-05-19) materializou `imoveis_no_if` como coluna per-workspace com default `true` (retrocompat com `pipeline.json:14` legado). Audit `set_at` + `set_by_user_id` registra signal afirmativo. §Consequências admitiu explicitamente: **"Default `true` na migration é retrocompat com hoje, não metodologicamente correto (Perini default `false`). Mitigação: PR separado pode flip default para workspaces criados após X data (co-design `product-designer`)"**. Esta ADR cumpre o débito.

[[ADR-142]] (Decidido completo) garante que cat_2 só entra em `investivel_efetivo` quando `imoveis_no_if=true` E `classification ∈ {locado, comercial}` (terreno improdutivo / uso pessoal nunca entram). Filtro de classificação **não** equivale a filtro de yield — imóvel `locado` com yield líquido 3% (vacância alta, IPTU pesado, manutenção) ainda entra com toggle=true. Isso superestima `investivel_efetivo` quando o capital está produzindo abaixo da TRS (~3-4% real). Doutrina Perini é explícita: capital que não bate a TRS não é capital de FIRE.

**Motivação metodológica** (co-design financial-planner 2026-05-19, ratifica recomendação de ADR-222):

1. Default silencioso `true` = decisão por omissão. Workspace novo criado via UI hoje herda `true` sem signal afirmativo. Cerbasi: "o usuário precisa entender o que está aceitando".
2. Conservadorismo em fintech é regra: superestimar progresso de FIRE é mais danoso que subestimar — gera falsa sensação de proximidade.
3. `imoveis_no_if=true` deveria ser opt-in com signal afirmativo de **yield > TRS** E **commitment de longo prazo** (capital imobilizado dedicado à IF).

**Workspace dogfood `5@5.com`** flipou explicitamente em 2026-05-18 via fluxo ADR-222 (set_at populado) — decisão consciente, **não tocar**. Demais workspaces existentes hoje têm `set_at IS NULL` (herdado de migration); recebem banner one-time educacional sem flip automático.

## Decisão

Adotar **quatro mudanças coordenadas** que materializam conservadorismo doutrinário:

### 1. Default da coluna vira `false` (`ALTER COLUMN ... SET DEFAULT`)

Migration Alembic apenas muda o **default DDL** da coluna `workspaces.imoveis_no_if`:

```sql
ALTER TABLE workspaces ALTER COLUMN imoveis_no_if SET DEFAULT false;
```

**Não há `UPDATE` em rows existentes** — flip retroativo silencioso quebra confiança (usuário viu KPI X por meses, acordaria com KPI Y diferente). Workspaces novos criados após o cutover nascem com `imoveis_no_if=false` + `set_at=NULL`.

### 2. Banner contextual em `MembersTab` para workspaces NOVOS

Trigger: usuário marca **≥1 imóvel** com `classification ∈ {locado, comercial}` (ADR-215 enum). Banner one-time aparece no topo do `MembersTab`, logo após o card "Residência" e antes da lista de membros — mesma viewport onde o usuário acabou de classificar.

```
┌─────────────────────────────────────────────────────────────┐
│  ⓘ  Contar seus imóveis alugados no cálculo de              │
│     Independência Financeira?                                │
│                                                              │
│     Você marcou {N} imóvel{N>1?'is':''} como investimento.   │
│     Por padrão, deixamos fora do seu Patrimônio Investido — │
│     só faz sentido incluir se o aluguel líquido rende mais  │
│     que ~3% real ao ano (Taxa de Retorno Segura).           │
│                                                              │
│     [ Manter fora ]  [ Incluir no cálculo ]  Decidir depois │
│                                                              │
│     O que é Taxa de Retorno Segura? →                       │
└─────────────────────────────────────────────────────────────┘
```

Três estados:
- **Não respondido + tem ≥1 imóvel qualificado** → banner ativo (dismissible por 30 dias).
- **Respondido (Sim/Não)** → some; vira sub-header em `RealEstateYieldCard`: "Imóveis investimento: [não] contam no Patrimônio Investido · alterar".
- **Não respondido + sem imóveis qualificados** → invisível.

**Por que "Manter fora" como primary:** alinha visualmente com o default conservador recomendado. Usuário que quer incluir tem que escolher conscientemente (signal afirmativo). Ambas opções visíveis com peso equivalente de leitura — não é dark pattern.

**Setting permanente** em `PipelineTab` (ou aba dedicada), acessível a qualquer momento via link "alterar" no `RealEstateYieldCard`. Pattern já existe em ADR-222.

### 3. Workspaces EXISTENTES: banner educacional one-time, sem flip automático

Workspaces com `imoveis_no_if=true` E `set_at IS NULL` (default migrado, sem signal afirmativo) recebem **versão educacional** do banner no primeiro login pós-cutover:

> **"Confirmar como seus imóveis alugados são contabilizados"**
>
> Atualmente, seus {N} imóveis investimento entram no cálculo do seu Patrimônio Investido. Quer manter assim, ou tirá-los? Por padrão hoje recomendamos deixar fora — só inclui se o aluguel líquido rende mais que ~3% real ao ano.

CTAs invertidos visualmente para preservar default atual: `Manter incluindo` (primary) / `Tirar do cálculo` (secondary) / `Decidir depois`. Resposta popula `set_at = now()` + `set_by_user_id` — signal afirmativo persistido.

Workspaces com `set_at NOT NULL` (decisão explícita prévia, ex.: `5@5.com`) **nunca** veem banner. Override do usuário é sagrado.

### 4. Telemetria mínima (3 eventos)

```
imoveis_no_if.banner_shown
  { workspace_id, qualified_properties_count, variant: "new" | "educational",
    trigger_source: "members_tab_post_classification" | "first_login_post_cutover" }

imoveis_no_if.decision_made
  { workspace_id, value: bool, source: "banner" | "settings_page" | "report_link",
    time_since_first_qualified_property_seconds, dismissed_count_before_decision }

imoveis_no_if.value_changed
  { workspace_id, from: bool, to: bool, source: "banner" | "settings_page" | "report_link" }
```

NSM proxy: % de workspaces novos com `set_at IS NOT NULL` dentro de 7d (target: ≥60% dogfood). Guard-rails: onboarding completion (não cai >5pp), regret rate `false → true` em 14d (<15%).

## Alternativas consideradas

- **(B) Card no onboarding antes do primeiro upload de IRPF.** Descartada — `frontend/src/app/onboarding/` não existe (sem fluxo dedicado); pergunta sem contexto (usuário ainda não tem imóveis classificados). Construir ~2 semanas eng para subset <40% da base.
- **(C) Default invisível + badge passivo no relatório.** Descartada — badge passivo é chrome ignorado; financial-planner pediu opt-in com signal afirmativo, não default silencioso.
- **(D) Pergunta dupla literal (P1 yield + P2 commitment 10y) como fluxo modal sequencial.** Descartada — designer apontou que duas perguntas em sequência criam fricção sem ganho proporcional; rationale dupla vira **copy** ("aluguel líquido rende mais que ~3% real" + "capital comprometido com IF") em 1 banner, não 2 telas.
- **(E) Flip retroativo automático em todos workspaces.** Descartada — quebra confiança; usuário viu KPI X por meses não pode acordar com KPI Y sem aviso.

## Consequências

**Positivas:**
- ✅ Doutrina Perini/Cerbasi materializada no produto, não só em doc.
- ✅ Workspaces novos nascem com signal afirmativo capturado em primeiro classificar — concrete, não abstract.
- ✅ Workspaces existentes recebem opt-in retroativo educacional sem flip surpresa.
- ✅ Audit `set_at` distingue "default herdado" (NULL) vs "decisão capturada" (timestamp) — UX honesta.
- ✅ Telemetria valida fit Mathoms × ICP: alto regret `false → true` sinaliza que doutrina default está desalinhada com mental model do PJ alta renda.

**Negativas:**
- ⚠️ Workspaces criados via API headless (sem UI) ficam `false` sem signal afirmativo. Aceito — caso raro hoje (dogfood); telemetria detectaria distorção se aparecer.
- ⚠️ Banner one-time adicional polui MembersTab/dashboard. Mitigação: dismissible 30d; some após resposta.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Migration aplica `ALTER COLUMN ... SET DEFAULT false` mas algum cliente custom criou workspace via SQL direto pós-cutover sem passar pelo handler `workspace.created` (cenário hipotético admin ops) | Migration é DDL idempotente; workspaces SQL-criados herdam novo default. Caso edge: documentado em runbook. |
| Banner aparece para usuário em meio a fluxo de execução, gera fricção | Dismissible 30d; aparece só após user marcar ≥1 imóvel qualificado (signal de relevância); não bloqueia ação. |
| Telemetria N pequeno (early access) → métricas qualitativas, não estatísticas | Aceito; N=5 dogfood sinaliza direção (todo mundo flipou → default desalinhado); revisitar quando N ≥ 50. |

## Gates

- **Migration Alembic** `ALTER COLUMN imoveis_no_if SET DEFAULT false` idempotente up/down; test verifica que workspace pré-existente preserva valor (sem `UPDATE`).
- **Backend** workspace creation handler usa novo default (sem código mudando — default vem do DDL).
- **Frontend**:
  - Banner contextual em `MembersTab` com 3 estados + 3 CTAs + a11y (aria-live, aria-labelledby, reduced-motion).
  - Estado respondido em `RealEstateYieldCard` (sub-header com link "alterar").
  - Setting permanente acessível em `PipelineTab` com anchor `#imoveis-no-if`.
  - Banner educacional one-time para workspaces existentes (variant="educational", trigger="first_login_post_cutover").
- **Telemetria** 3 eventos emitidos (banner_shown, decision_made, value_changed).
- **E2E Playwright `@critical`**:
  - (a) Workspace novo: classifica imóvel locado → banner aparece → clica "Manter fora" → toggle DB = false → reload → banner sumiu → `RealEstateYieldCard` mostra "não contam".
  - (b) Workspace existente: migration preserva valor; primeiro login mostra banner educacional; resposta popula set_at.
- **Goldens E5/E6** não regridem: `progresso_if` em workspace dogfood `5@5.com` (set_at preservado) tem mesmo output pré/pós-merge ([[ADR-142]] invariante).
- **Snapshot OpenAPI** não muda (endpoint PUT já existe em ADR-222).
- **`rule-imoveis-no-if.md`** linha 23 atualizada: substituir "Recomendação metodológica (financial-planner): default conceitual deveria ser `false` ... flip de default fica como follow-up product-designer" por referência a esta ADR (Decidido).

## Implementação

Lane planejada em **Sprint A13** com track próprio (`docs/agent_prompts/track_a13-imoveis-no-if-default-flip.md`). Escopo: migration + telemetria + 1 surface UX (banner D-refinada). PM rationale: pequeno em eng (~1d) mas muda contrato semântico de default; rushar em A12 cauda solta produziria UX rushed. A12 fecha forte com #318-#321 + ADRs Proposto (esta + ADR-224).

## Referências

- [[ADR-222]] — coluna `workspaces.imoveis_no_if` per-workspace + audit (esta ADR cumpre débito de "default conceitual `false` em PR separado")
- [[ADR-142]] — invariante anti-dupla-contagem; runtime filtra cat_2 por classification
- [[ADR-215]] — classification enum em `workspace_property_overrides` (trigger do banner depende de ≥1 imóvel locado/comercial)
- [[ADR-186]] — override sticky pattern (set_at preservado em re-uploads)
- [[ADR-102]] R18 — `response_model` explícito
- Co-design 2026-05-19: `financial-planner` (default conservador + critério yield+commitment + copy TRS), `product-designer` (banner D-refinada + 3 estados + a11y), `product-manager` (timing A13, NSM proxy, risco "ambiguidade default vs explícito")
