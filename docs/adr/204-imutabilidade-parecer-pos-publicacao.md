---
id: ADR-204
type: adr
title: "Imutabilidade do parecer pós-publicação (estende ADR-187)"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-131]]"
  - "[[ADR-136]]"
  - "[[ADR-144]]"
  - "[[ADR-187]]"
  - "[[ADR-199]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 204"
  - "Parecer imutável pós-publicação"
  - "Snapshot parecer mês fechado"
tags:
  - area/llm
  - area/report
  - area/methodology
  - phase/a11
  - status/proposto
  - type/adr
---

# ADR-204 — Imutabilidade do parecer pós-publicação (estende ADR-187)

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- [[ADR-187]] estabelece "relatório publicado é imutável — conceito de mês fechado". Tabela `report_publications` materializa o evento de publicação com `published_at` + `immutable_hash`. Mês fechado bloqueia re-categorização retroativa e qualquer mudança em dado consolidado.
- O parecer ([[ADR-199]]) é **derivado** do snapshot E5 do relatório. Sem extensão explícita da imutabilidade ao parecer, surgem cenários problemáticos:
  - **Cliente premium contesta parecer** ("o parecer de janeiro recomendou X, agora recomenda Y; mudaram de ideia?"). Sem snapshot, impossível responder com a versão exata vista pelo cliente.
  - **LLM provider deprecate model** ([[ADR-144]] CTO-G1 — persona drift). Re-geração silenciosa produz output diferente; cliente não sabe.
  - **Persona evolui** ([[ADR-201]] bump). Re-gerar parecer antigo com persona nova distorce histórico metodológico — auditor CFP não consegue reconstituir o "porquê" da recomendação original.
  - **Auditoria CVM/LGPD/contestação legal:** sem hash imutável + lineage congelado, defesa fica em "we don't know exactly what was shown".
- Plano canônico `docs/plan/PLANNER_REVIEW/_README.md` Premissa 6 (sigilo §13) + risco crítico PD1 (sigilo vazando) implicam parecer auditável; sem imutabilidade, auditoria é teatro.

## Alternativas consideradas

1. **Sem imutabilidade — parecer regenera livre.** Pró: simples. Contra: viola contrato implícito "o que vi não muda sozinho" ([[ADR-187]] §"Por que isso importa"); auditoria impossível; produto premium perde confiança. **Rejeitada.**
2. **Imutabilidade só do PDF exportado** (cliente baixa, fica com snapshot local). Pró: zero infra. Contra: usuário web continua vendo mutação a cada re-gen; "parecer no app diferente do PDF" quebra mental model. **Rejeitada.**
3. **Imutabilidade in-band** (flag `is_published_immutable` no aggregate, sem mecanismo de supersede). Pró: leve. Contra: bloqueia legitimamente caso "cliente pede regeneração com mais dados" ([[ADR-187]] V2 contempla "edição quente" antes de fechar); sem chain de supersedure, perde rastreabilidade. **Rejeitada.**
4. **Imutabilidade via chain de supersedure event-sourced** (estende [[ADR-187]] ao parecer; pareceres antigos viram `Superseded`, novos viram `Publicado`). Pró: paridade total com modelo já validado em [[ADR-187]]; auditoria 100% rastreável; permite regeneração legítima (não bloqueia, só registra); pattern reusa [[ADR-136]] Decision aggregate. **Aceita.**

## Decisão

Estender [[ADR-187]] explicitamente ao aggregate `PlannerReview` ([[ADR-199]]) via **lifecycle + supersedure chain**.

### D1. Lifecycle estendido com gate de publicação

Estados em ordem ([[ADR-199]] §D2):

1. **`Pendente`** — stage agendado, sem artifact.
2. **`Gerado`** — LLM emitiu output válido; artifact escrito; **mutável** (re-run sobrescreve).
3. **`Publicado`** — evento explícito; congelado; chave de supersedure ativa. **Quem publica:** quando `report_publications` da [[ADR-187]] entrega `published_at` para o `period_yyyymm` do parecer, o parecer correspondente flippa automaticamente `Gerado → Publicado` (trigger ou serviço).
4. **`Superseded`** — re-run subsequente após publicação cria **novo aggregate** com `supersedes_id` apontando para anterior; aggregate anterior flippa para `Superseded`.

### D2. Imutabilidade na transição `Gerado → Publicado`

- Hash SHA-256 do conteúdo do artifact persistido no aggregate (campo `immutable_hash`, paridade com [[ADR-187]] §D1).
- `published_at: TIMESTAMPTZ` registrado.
- Qualquer tentativa de re-write no mesmo `pipeline_artifacts` row é bloqueada por trigger: status `Publicado` → write rejeitada com `PreconditionFailedError` (HTTP 412).
- Re-geração legítima cria **novo artifact** (novo `id`, novo `pipeline_run_id`), com `supersedes_id` apontando para o anterior; antigo flippa para `Superseded` no mesmo commit.

### D3. Chain de supersedure preservada eternamente

- **Não deleta pareceres `Superseded`.** Lifecycle [[ADR-131]] preserva.
- Permite reconstrução temporal: "mostre o parecer que o cliente Y viu em DD/MM/YYYY" = SELECT no parecer cujo `published_at <= DD/MM/YYYY` e (`superseded_at IS NULL OR superseded_at > DD/MM/YYYY`).
- Política de retenção: indefinida na V1 — pareceres `Superseded` retidos eternamente. Reavaliada quando volume `pipeline_artifacts` exigir (estimativa 30KB/parecer × 12/ano × N workspaces; ~360MB/ano por 1k workspaces).

### D4. Cache Redis separado de artifact (fonte de verdade)

- Cache Redis ([[ADR-144]] pattern) é **otimização de runtime**, não fonte de verdade. Pode ser invalidado/expirado livre.
- `pipeline_artifacts` é fonte de verdade. Mesmo após `superseded_by`, o artifact físico permanece.
- Hash imutável do parecer publicado é validado **contra o artifact**, não contra o cache. Cache hit serve o conteúdo; falha de hash check vs artifact → cache invalidado.

### D5. UI deve declarar snapshot explicitamente

- Componente `<ParecerHeroDiagnostico>` (Ato 5 do plano) inclui badge **"Snapshot dos dados em DD/MM/YYYY · publicado em DD/MM/YYYY"**.
- Tooltip explicativo: "Este parecer reflete a foto do seu patrimônio em DD/MM. Recálculos posteriores geram pareceres novos sem alterar este."
- Mitiga risco PD18 ("parecer LLM muda de ideia entre rodadas").

### D6. Re-geração legítima — quem decide

- **`Gerado` (não publicado):** re-gera livre (mutável).
- **`Publicado`:** re-geração só via:
  - (a) Usuário premium clica "Regenerar parecer" no UI (cria novo aggregate, antigo vira `Superseded`). Rate-limited a 3/workspace/dia (D-0.5 do plano).
  - (b) Cron/event que detecta `e5_artifact_id` foi `Superseded` por re-run de E5 (cascata): novo parecer gerado automaticamente; antigo vira `Superseded`. Logs explícitos.
- Nunca silencioso: cada criação de parecer logada em `mathoms.pipeline.parecer_planejador` com `parent_supersede_id`.

### D7. PDF imutável usa hash do parecer publicado

- Renderer Playwright (PDF, [[ADR-187]] §Critério de aceite) injeta `immutable_hash` no metadata do PDF (PDF info field).
- Cliente que arquiva PDF tem rastreabilidade: hash no PDF deve casar com hash no DB para o `published_at` correspondente. Defesa contra "cliente alega ter recebido PDF X mas DB diz Y".

## Consequências

**Positivas:**
- Auditoria total: cada parecer visto pelo cliente é reconstruível com lineage completo (persona_hash + manifest_version + schema_version + model_id + e5_artifact_id + immutable_hash).
- Confiança preservada: cliente que reabre relatório vê **mesmo parecer**; mudança = evento explícito, não silencioso.
- Conforme CVM/LGPD/disputa legal: snapshot fiduciário do que foi entregue.
- Reusa modelo já validado [[ADR-187]] — zero invenção de pattern novo.
- Compatível com `Decision` aggregate ([[ADR-136]]): supersedure event-sourced é o padrão do repo.

**Negativas / trade-offs aceitos:**
- Volume de `pipeline_artifacts` cresce com cada supersede (não delete). Estimativa: ~360MB/ano por 1k workspaces — gerenciável. Retention policy reavaliada quando justificar.
- Migration Alembic adiciona colunas (`immutable_hash`, `published_at`, `supersedes_id`, `superseded_at`) no aggregate `planner_review` (ou mapping equivalente em `pipeline_artifacts._meta`).
- UX: usuário não-premium pode ficar confuso com badge "publicado em" — mitigação no copy ([[ADR-208]] gating mostra ou não).
- Cascade quando E5 é regenerado: lógica de "regerar parecer automaticamente?" exige decisão de produto (default: sim, com log).

**Riscos mitigados:**
- **PD18 (parecer muda de ideia entre rodadas):** snapshot imutável + badge UI.
- **Persona drift entre modelos (CTO-G1):** `persona_hash` + `model_id` persistidos.
- **Disputa CVM/LGPD:** lineage congelado.
- **Cliente arquiva PDF inconsistente com web:** hash no PDF metadata cross-check com DB.

## Implementação

- **Track(s) do plano:** estende T-10 (`planner-aggregate-model`) e T-11 (`planner-migration-alembic`) do Ato 3.
- **Files touched (Ato 3):**
  - `backend/app/models/planner_review.py` — colunas `immutable_hash`, `published_at`, `supersedes_id`, `superseded_at`
  - Alembic migration — adiciona colunas + trigger de imutabilidade
  - `backend/app/services/report_publication.py` — hook que flippa `Gerado → Publicado` para parecer correspondente
  - `backend/app/services/pdf_renderer.py` — injeta hash no PDF metadata (futuro Ato 5)
- **Critério de aceite:**
  - Estado `Publicado` rejeita write no mesmo `pipeline_artifacts` row (teste).
  - Re-geração cria novo aggregate com `supersedes_id` (teste).
  - SELECT temporal funciona: "parecer ativo em DD/MM" retorna 1 row consistente (teste).
  - Hash no PDF metadata bate com hash no DB (teste E2E).
- **Gates CI:** `pytest backend/tests/test_planner_review_immutability.py`, OpenAPI snapshot consistente.

**Decisão pendente para outros especialistas:**
- **Cascade automática quando E5 regenera?** (default sim; mas pode produzir burst de pareceres em re-run em massa) — `data-engineer` decide em conjunto com observability budget.
- **Política de retenção pareceres `Superseded`** — `data-engineer` reavalia em volume real.
- **Rate limit exato (3/workspace/dia)** — confirmar com `sre-devops` (FinOps) em [[ADR-208]] pricing.
