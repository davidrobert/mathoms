---
id: ADR-186
type: adr
title: "Promoção de override de transação para regra de categorização (learning loop)"
status: Decidido
phase: A12.P2
date: "2026-05-10"
decided_at: "2026-05-11"
relates_to:
  - "[[ADR-047]]"
  - "[[ADR-081]]"
  - "[[ADR-097]]"
  - "[[ADR-134]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-185]]"
  - "[[ADR-188]]"
supersedes: []
superseded_by: []
aliases: ["ADR 186", "Category learning loop", "Override-to-rule promotion"]
tags:
  - area/categorization
  - area/pipeline
  - area/methodology
  - phase/a12
  - status/decidido
  - type/adr
---

> ADR longa (>150 linhas) por design: feature toca pipeline (E4), domínio
> (`WorkspaceCategoryOverride`, `TransactionOverride`), schema (campo novo
> `override_source` + agregado novo `CategorizationRule`), UX (`/transactions`
> + `/config → Categorias`) e invariante temporal (mês fechado). Split
> produziria peças órfãs sem o contrato cruzado.

> **Supersedure parcial (2026-05-11, registrada 2026-07-03 · audit r5):**
> [[ADR-188]] refina §D3 (schema — soft-delete, partial unique, provenance) e
> substitui o `revert_count` único de §D6 (split `revert_transactions` /
> `revert_rules`). Para o contrato vigente desses dois pontos, leia [[ADR-188]];
> o restante desta ADR permanece canônico.

## Contexto

Hoje, no Mathoms, há **duas camadas isoladas** de categorização:

1. **Regras globais** (`/config → Categorias`) — `CategoryTemplate` (taxonomia
   global, [[ADR-137]]) + `WorkspaceCategoryOverride` (diff por workspace:
   adiciona keywords, renomeia, desabilita, ajusta cap). O pipeline E4
   (`pipeline/domain/services/categorization_service.py`) faz match de
   **substring uppercase** entre `keywords` e `transaction.description`.
   Primeira categoria que dá match ganha (não-determinístico em ordem de
   iteração).
2. **Override pontual** (`/transactions`) — usuário edita categoria de uma
   transação → `TransactionOverride(workspace_id, transaction_hash,
   new_category)`. Aplica-se **só àquela transação**. Não afeta categorização
   futura nem similares.

**Gap.** Se o usuário corrige "PAGAMENTO PIX MERCADO PAGO IFOOD" de
"Diversos" para "Alimentação · Delivery" 5×, o sistema continua
categorizando todas as próximas como "Diversos". O usuário razoavelmente
espera que o produto **aprenda**.

**Por que isso importa pro produto Mathoms** (input do `financial-planner`,
sessão 2026-05-10):

- **Cerbasi** — categorização errada **mata** o diagnóstico comportamental.
  A conversa de casal sobre "estilo de vida" não acontece se "iFood" cai
  em "Diversos" por 6 meses. Dano: alto e cumulativo.
- **Perini** — custo de vida mensal é input direto da regra dos 300
  (patrimônio-alvo de IF). Categoria errada distorce custo de vida → distorce
  meta. Dano: médio mas estrutural.
- **AUVP** — neutro em categorização, mas **fecha mês com diagnóstico
  consolidado**. Re-categorizar mês 01 quando aprendo regra no mês 06
  **viola o snapshot do mês fechado**. Esse é o ponto mais sutil.

**Lições de mercado** (Mint, YNAB, Monarch, Copilot Money, Mobills,
Organizze, Quicken):

- **Mint morreu** (entre outras razões) por categorização ruim que **nunca
  aprendia**. Auto-promote silencioso destrói confiança.
- **YNAB** não tem learning, e os fóruns reclamam há anos.
- **Monarch** acerta o tom: edição é silenciosa, "Rules" tem tela própria
  com preview antes/depois.
- **Copilot Money** interrompe demais e irrita.

## Decisão

Adotar **modelo híbrido C + D ("descoberta passiva-primária + ação no
ponto-de-edição")** com invariantes não-negociáveis:

### D1. Modelo de aprendizado: híbrido C-light + D-forte

- **C-light (no momento da edição):** ao salvar override em `/transactions`,
  exibir **toast não-bloqueante** ("Categoria atualizada. 23 transações
  similares? Revisar →"). Click em "Revisar" abre **side-panel** com
  preview e CTA explícito de criar regra. **Nunca modal bloqueante.**
  Dispensável com "Não sugerir mais nesta sessão".
- **D-forte (background):** detector offline (job `detect_rule_candidates`)
  agrupa overrides por `(target_category, normalized_token)` e, quando
  ≥3 overrides distintos batem o mesmo token estável, gera entrada em
  `/config → Categorias → Sugestões pendentes` (badge com contador).
  Aprovação em lote.

**Modos onboarding vs steady-state** — implícitos:

- Durante **onboarding** (primeiros 90 dias OU < 5 overrides/semana),
  toast C aparece com CTA primário "Revisar agora".
- Em **steady-state**, toast C aparece com CTA secundário "Dispensar"
  destacado; D assume protagonismo.

### D2. Invariante temporal: snapshot do mês fechado é imutável

Re-categorização retroativa **só** pode afetar transações:

- (a) **sem `TransactionOverride` manual prévio** (override manual é
  sticky, regra **nunca** atropela edição manual);
- (b) em **meses não-fechados** — i.e., meses sem `report_published_at`
  (artefato E7 entregue/assinado).

Pré-requisito: **introduzir conceito de "mês fechado/relatório publicado"**
no domínio. Hoje não existe. Esse é blocker de design — endereçado em
[ADR-186 Proposto] (separada, escopo: marcar artefato E7 como
`published_at` imutável + Alembic). A presente ADR é gated por aquela.

**Por quê.** Snapshot do mês fechado é contrato de produto: relatório
entregue ao cliente (PDF assinado, conversa do mês) **não pode mudar
sozinho**. Re-categorizar passado em meses fechados quebra confiança e
viola cadência AUVP. Re-categorizar passado em meses **em aberto** é
desejável (corrige custo de vida pra Perini, corrige diagnóstico pra
Cerbasi).

### D3. Schema: distinguir origem do override + persistir provenance da regra

**Mudança 1 — `transaction_overrides`:** adicionar coluna
`source: Literal["manual", "rule"]` NOT NULL DEFAULT `"manual"`. Backfill
existente como `"manual"`. Quando regra promovida re-categoriza uma
transação sem override prévio, **cria `TransactionOverride(source="rule",
new_category=…, rule_id=…)`** — não mexe nos `manual` existentes.

**Mudança 2 — agregado novo `CategorizationRule`** (tabela
`categorization_rules`):

```sql
CREATE TABLE categorization_rules (
  id              UUID PRIMARY KEY,
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  keyword         VARCHAR(255) NOT NULL,        -- substring uppercase, igual E4
  target_category VARCHAR(255) NOT NULL,        -- key do CategoryTemplate
  source          VARCHAR(20)  NOT NULL,        -- 'user_promoted' | 'suggested_approved' | 'imported'
  origin_override_id UUID NULL REFERENCES transaction_overrides(id),  -- audit
  priority        INTEGER NOT NULL DEFAULT 100, -- maior = ganha; default por especificidade len(keyword)
  enabled         BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ NOT NULL,
  UNIQUE (workspace_id, keyword, target_category)
);
CREATE INDEX ix_cat_rules_ws_enabled ON categorization_rules(workspace_id) WHERE enabled = true;
```

**Por que tabela nova vs `WorkspaceCategoryOverride.keywords_override`:**
overrides do template são **diff editorial humano** (renomeia, desabilita
categoria); rules são **derivadas de comportamento** (aprendidas, com
provenance, prioridade explícita, estado enabled/disabled, possíveis
conflitos resolvidos por priority). Misturar os dois quebra a separação
semântica de [[ADR-137]] e dificulta auditoria. **Pipeline E4 lê os
dois e mergeia** — ver D5.

**Soft reference `origin_override_id`** (decisão P1, 2026-05-10):
implementado em P1 sem FK formal por restrição SQLite — FK formal
criaria ciclo com `transaction_overrides.rule_id` que SQLAlchemy/Alembic
não conseguem ordenar em DROP/sort/offline-SQL. Direção viva da relação
é `transaction_overrides.rule_id` (FK formal). `origin_override_id` é
audit-only — soft delete do override original deixa o id zumbi, aceito
porque a regra preserva rastreabilidade da intenção. FK formal opcional
em P3 quando target PG-only ([[ADR-128]]).

**Mudança 3 — coluna `published_at` em `pipeline_artifacts`** (ou tabela
nova `report_publications`): contrato de imutabilidade. Detalhe em
[ADR-186 Proposto].

### D4. UX: highlight-to-extract + preview com heatmap + reversibilidade

Extração de keyword (input do `product-designer`, sessão 2026-05-10):

- **Primary:** highlight-to-extract — usuário arrasta seleção sobre a
  descrição da transação ("PAGAMENTO PIX **MERCADO PAGO IFOOD** 12345"),
  o que fica selecionado vira `keyword`.
- **Pré-preenchimento heurístico:** maior n-grama estável após normalização
  (uppercase + remove dígitos finais + colapsa whitespace) — usuário pode
  ajustar handles da seleção.
- **Live preview:** "47 transações vão casar" atualiza a cada keystroke.
- **Fallback mobile:** chips de N tokens candidatos (sem mouse para drag).

Side-panel (não modal) com 3 zonas:

1. **Header:** keyword + categoria destino + contador "47 transações em 8
   meses (jan/2024 → mar/2026)".
2. **Diff agrupado por categoria de origem** + heatmap mensal pequeno
   (detecta surpresa "vai mexer em mês fechado?" — meses fechados
   aparecem em cinza, **não-clickáveis**).
3. **Exclusões:** linhas com `TransactionOverride(source="manual")` prévio
   aparecem **opt-out por padrão** com badge "Editado manualmente —
   manter".

**Reversibilidade em 3 níveis:**

- (a) Banner persistente na transação: "Categorizada por regra
  'MERCADO PAGO IFOOD'" + link "Editar regra" + "Desvincular esta
  transação" (cria override manual contrário).
- (b) Em `/config → Categorias → Regras promovidas`: cada regra tem
  botão "Reverter regra" → desabilita + remove `TransactionOverride`s
  com `source="rule"` daquela regra (preserva `manual`).
- (c) Audit trail: `categorization_rules.origin_override_id` aponta
  pra origem; histórico fica.

**Conflito de keyword** (substring/superstring de regra existente):
warning amarelo (`var(--semantic-warning)`) inline antes de salvar:
"'MERCADO PAGO IFOOD' contém 'IFOOD' (Alimentação). 12 transações vão
sair de Alimentação para Lazer." Forçar acknowledgement explícito.
Resolução determinística por `priority` (maior ganha; default por
`len(keyword)` desc — mais específico ganha). UI esconde "ordem"
(implementação interna).

### D5. Pipeline E4: contrato + ordem de aplicação

Em E4, `categorize_transactions` consome agora **`CategorizationRulesV2`**
(value object novo, ISP — ADR-097) com:

```python
@dataclass(frozen=True)
class CategorizationRulesV2:
    template_keywords: dict[str, tuple[str, ...]]   # do CategoryTemplate + WorkspaceCategoryOverride.keywords_override
    learned_rules: tuple[LearnedRule, ...]          # do CategorizationRule, sorted by (priority desc, len(keyword) desc)

@dataclass(frozen=True)
class LearnedRule:
    keyword: str          # já uppercase
    target_category: str
    rule_id: str          # pra rastrear no TransactionOverride(source="rule")
```

**Ordem de match em `_categorize_one`:**

1. `learned_rules` (workspace-aprendidas, mais específicas) — primeira
   ganha.
2. Se nenhuma casa, fallback para `template_keywords` (comportamento atual).

`TransactionOverride(source="manual")` continua aplicado **fora do
pipeline** no read-path (`transaction_service.load_transactions`) e
sobrescreve qualquer match do pipeline — invariante atual mantido.

**Determinismo:** sort estável por `(priority desc, len(keyword) desc,
created_at asc)` resolve ambiguidade. ADR fecha o gap atual de
não-determinismo do dict.

### D6. KPI/telemetria de saúde

Métricas mínimas (Prometheus/structured logs `mathoms.categorization.*`):

- `% de transações categorizadas por`: `learned_rule` / `template_keyword`
  / `manual_override` / `uncategorized`. **North star de saúde da
  feature: subir % `learned_rule` sem cair % `manual_override` baixo a
  zero** (sinal de que regras estão ajudando, não atropelando).
- `regra criada / regra revertida` ratio por workspace e período. >20%
  reversão = sinal de extração ruim.
- `time-to-rule` (dias entre primeiro override e regra criada). KPI de
  onboarding.

**V2 (futuro, não nesta ADR):** badge de confiança por regra ("aplicada
47×, revertida 2× — 95%").

## Alternativas consideradas

| # | Opção | Por que rejeitada |
|---|---|---|
| **A** | Auto-promote agressivo: 1ª correção cria regra + recategoriza retroativo. | Lição Mint/Copilot — surpresa silenciosa destrói confiança. Viola "snapshot mês fechado" do AUVP. |
| **B** | Threshold puro (≥N correções → cria regra automática sem aprovação). | Mesma classe de risco que A: usuário descobre regra que nunca aprovou. |
| **C-puro** | Modal bloqueante a cada edição perguntando "aplicar a similares?". | Tortura quem está fazendo limpeza retroativa de 20 transações. Atrito mata edição. |
| **D-puro** | Só inbox de sugestões em `/config`, sem prompt na edição. | Demora a entregar valor; usuário não descobre a feature; YNAB-syndrome. |
| **C+D híbrido escolhido** | Toast leve + side-panel + inbox em background. | Descoberta passiva-primária (Monarch-style) + ação opcional no ponto-de-edição. Equilibra atrito e learning. |

## Consequências

**Positivas:**

- Diagnóstico financeiro confiável ao longo do tempo (Cerbasi/Perini).
- `% manual_override` cai naturalmente após onboarding (sinal de saúde).
- Auditabilidade: cada regra tem origem rastreável; reverter restaura
  estado anterior.
- Determinismo do match (resolve gap atual de ordem do dict).

**Negativas / custos:**

- **Pré-requisito não-trivial:** ADR-186 (mês fechado) precisa ser
  decidida + implementada antes desta ADR sair de Proposto.
- **Migrations Alembic:** `transaction_overrides.source` (backfill),
  `categorization_rules` (nova), `pipeline_artifacts.published_at`
  (separada). Tocando ADR-090 (money não é float) é neutro aqui.
- **Pipeline E4 muda contrato** (`CategorizationRules` →
  `CategorizationRulesV2`) — quebra adapter atual; teste de paridade
  obrigatório.
- **UX nova significativa:** side-panel + inbox + banner persistente.
  Custo design + impl ≈ 5-7d eng frontend + 3d backend + 2d pipeline.

**Riscos & mitigações:**

| Risco | Mitigação |
|---|---|
| Extração de keyword ruim → regras tóxicas. | Highlight-to-extract com user-in-the-loop; live preview obriga ver match antes de salvar. |
| Conflito de regras silencioso. | `priority` explícito + warning de conflito + tiebreaker determinístico. |
| Re-categorização retroativa muda relatório entregue. | Mês fechado é hard-gate (D2). Heatmap mostra cinza pros fechados. |
| Usuário cria regra e esquece — drift de domínio. | Inbox de regras com `last_applied_at`; badge "regra desativada por inatividade" após 6 meses sem novo match. (V2.) |
| % `manual_override` despenca → regras silenciam edições. | KPI monitorado; alerta SRE se `manual_override < 1%` por 30d (sinal de over-fitting). |

## Critério de aceite

- [ ] **ADR-186 (mês fechado) decidida e implementada.** Bloqueia esta.
- [ ] Schema: `transaction_overrides.source` + `categorization_rules`
      criados via Alembic com backfill validado em goldens E4.
- [ ] Pipeline E4 consome `CategorizationRulesV2`; teste de paridade
      legado vs novo passa em fixtures `tests/fixtures/categorization/`.
- [ ] Endpoint `POST /workspaces/{ws}/categorization/rules` (preview +
      commit) com `response_model` explícito ([[ADR-109]]); snapshot
      OpenAPI atualizado.
- [ ] UI `/transactions` toast + side-panel; UI `/config → Categorias →
      Regras promovidas` + Sugestões; banner na transação categorizada
      por regra.
- [ ] Reverter regra restaura estado anterior em teste E2E
      (`@critical`); overrides manuais permanecem intocados.
- [ ] Heatmap mostra meses fechados em cinza não-clickável (visual gate
      de D2).
- [ ] Telemetria `mathoms.categorization.*` instrumentada com 4
      contadores principais (D6).
- [ ] Conflito de keyword bloqueia salvar até acknowledgement (teste
      unitário de UI).

## Handoffs

- `senior-cto` revisa **antes do PR estrutural** (schema novo
  `categorization_rules`, mudança de contrato no E4, ordem de aplicação).
- `data-engineer` revisa **migrations Alembic + backfill + paridade
  goldens E4**.
- `product-designer` revisa **side-panel, banner e heatmap finais**
  (mock pré-impl).
- `product-manager` curador da lane `A11.cat-learning-loop` no plano
  abaixo.
- `sre-devops` revisa **telemetria + alertas** (D6) antes do release.

## Referências

- Input financial-planner sessão 2026-05-10 — diagnóstico de gap +
  recomendação metodológica.
- Input product-designer sessão 2026-05-10 — UX híbrida C-light + D-forte
  + highlight-to-extract.
- [[ADR-047]] — categoria override inline em Transaction Explorer.
- [[ADR-081]] — classificação de documento (modelo content-first +
  fallback LLM, paralelo conceitual).
- [[ADR-097]] — services de domínio recebem value objects de config
  tipados (D5 segue o padrão).
- [[ADR-134]] — ConfigStore DB-first.
- [[ADR-137]] — `category_template` + `workspace_category_overrides`
  (D3 estende sem misturar semântica).
- [[ADR-143]] — methodology = code (regras são domínio enforçável, com
  ADR canônica + docstring co-localizada no service).

## Histórico

- 2026-05-10 — Proposto. Gate triple (financial-planner + product-designer
  + senior-cto) na sessão 2026-05-10.
- 2026-05-10 — P1 implementado em #188 (schema: `categorization_rules` +
  `transaction_overrides.source` + `transaction_overrides.rule_id`; soft-ref
  `origin_override_id` por restrição SQLite — §D3).
- 2026-05-11 — P2 implementado em #194 (pipeline E4: `CategorizationRulesV2`
  + adapter + learning loop com sticky-manual + sticky intra-run + mês
  fechado + counter bump na mesma `Session.flush()`). Flip para Decidido
  pós-gate triple de review (financial-planner + data-engineer + senior-cto).
- P3/P4 (endpoints HTTP + UI `/transactions`) seguem em lanes separadas.
