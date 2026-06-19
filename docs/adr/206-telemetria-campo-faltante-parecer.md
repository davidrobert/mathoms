---
id: ADR-206
type: adr
title: "Telemetria de campo faltante como signal de evolução do manifest (estende ADR-188)"
status: Decidido
phase: "Ato 1 — fundação arquitetural do PLANNER_REVIEW"
date: "2026-05-13"
relates_to:
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-202]]"
  - "[[ADR-203]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 206"
  - "Telemetria campo faltante parecer"
  - "Manifest learning loop"
tags:
  - area/llm
  - area/observability
  - area/pipeline
  - phase/a11
  - status/decidido
  - type/adr
---

# ADR-206 — Telemetria de campo faltante como signal de evolução do manifest (estende ADR-188)

**Status:** Decidido (Ato 1 — fundação arquitetural do PLANNER_REVIEW) • **Data:** 2026-05-13

## Contexto

- Manifest declarativo ([[ADR-200]]) define o exec context **estático** do parecer. Mudança no E5 schema sem mudança no manifest produz drift; coverage gate M1 (em [[ADR-200]] §D3) cobre esse caso quando o campo é referenciado fora.
- **M1 cobre só metade do drift:** detecta `path no manifest mas ausente no E5` (referência morta), **não** detecta `campo novo no E5 que deveria estar no manifest mas não está` (gap empírico). Risco DE no plano canônico: "Telemetria M1 só pega metade do drift" (lista de riscos altos).
- [[ADR-188]] estabelece pattern de **learning loop** como signal de drift (categorização: revert_count semântico split em "regra ruim" vs "abandono"). Pattern: instrumentar evento de usuário/sistema → agregar → input para evolução de contrato.
- Plano canônico §"Ato 6" §"6a Telemetria M4" e §"campos_faltantes_pediria_se_iterasse[]" estabelecem: LLM declara no output quais campos teria pedido se pudesse iterar; agregação semanal → top-10 → ticket "destilar X no manifest v2".

## Alternativas consideradas

1. **Sem telemetria — esperar feedback humano** ("parecer não cita X que eu gostaria"). Pró: zero infra. Contra: feedback ad-hoc, anedótico, atrasado meses. **Rejeitada** — produto sério precisa loop de feedback.
2. **Instrumentar drift só via logs** (`mathoms.pipeline.parecer_planejador` com `field_path` quando LLM emite `campos_faltantes`). Pró: simples; aproveita [[ADR-110]] structured logging. Contra: agregação fica em ELK/Datadog, não em DB; queries cross-workspace tediosas; cap de retention de logs (~30d) limita análise temporal. **Rejeitada parcialmente** — usar como complemento.
3. **Tabela `planner_field_requests`** com agregação por workspace + global. Pró: queries SQL diretas; retention indefinida; cruzamento com outras métricas (custo, satisfação) trivial; pattern já validado em [[ADR-188]] (tabelas de telemetria). Contra: migration Alembic adicional. **Aceita.**
4. **LLM emite só global** (sem associar a workspace). Pró: privacy-friendly por construção. Contra: perde signal "este campo é importante para family-of-workspaces X mas não Y" — workspaces premium podem ter padrão diferente. **Rejeitada parcialmente** — manter workspace_id, mas garantir nenhuma string de valor cliente persiste (só JSONPath, que é estrutural).

## Decisão

Adotar **telemetria de campo faltante via tabela dedicada** `planner_field_requests`, alimentada pelo campo `campos_faltantes_pediria_se_iterasse[]` do output schema ([[ADR-202]]). Estende [[ADR-188]] pattern de learning loop ao domínio LLM.

### D1. Tabela `planner_field_requests`

```sql
CREATE TABLE planner_field_requests (
  id              UUID PRIMARY KEY,
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  parecer_id      UUID NOT NULL REFERENCES pipeline_artifacts(id),
  field_path      VARCHAR(255) NOT NULL,    -- JSONPath subset (manifest DSL)
  reason          VARCHAR(64) NULL,         -- 'path_not_whitelisted' | 'value_null' | 'value_absent' (do tool_trace ADR-203)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (parecer_id, field_path)
);

CREATE INDEX ix_planner_field_requests_field ON planner_field_requests(field_path);
CREATE INDEX ix_planner_field_requests_workspace ON planner_field_requests(workspace_id, created_at);
```

- **Sem coluna `value_snippet`** ou similar — privacy by construction. Só estrutura (JSONPath), nunca conteúdo.
- `parecer_id` permite drill-down: "quais pareceres pediram este campo?" para análise qualitativa.
- `UNIQUE (parecer_id, field_path)` — um parecer não duplica o mesmo path no array.

### D2. Origem dos registros — 2 fontes complementares

**Fonte primária — output schema `campos_faltantes_pediria_se_iterasse[]`:**
- LLM declara explicitamente paths que teria querido ver. Validado por schema ([[ADR-202]] §D7).
- Stage wrapper insere uma row em `planner_field_requests` por path declarado.

**Fonte secundária — tool_trace com `found: false` ([[ADR-203]] §D7):**
- Quando tool `get_e5_jsonpath` retorna `{found: false, path, reason}`, stage também insere row.
- Reason capturado: `path_not_whitelisted`, `value_null`, `value_absent`.
- Fonte secundária pega LLM que **tentou** drill-down, fonte primária pega LLM que **conscientemente declarou** falta.

### D3. Agregação semanal — view materializada

```sql
CREATE MATERIALIZED VIEW planner_field_requests_top AS
SELECT
  field_path,
  COUNT(*) AS total_requests,
  COUNT(DISTINCT workspace_id) AS workspaces_count,
  COUNT(DISTINCT parecer_id) AS pareceres_count,
  MIN(created_at) AS first_seen,
  MAX(created_at) AS last_seen
FROM planner_field_requests
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY field_path
ORDER BY total_requests DESC;
```

- Refresh diário via Celery beat (`refresh_planner_field_requests_top`).
- Dashboard owner: `product-manager` (review semanal — plano §KPIs).

### D4. Triggers de evolução do manifest (M4)

Critérios para abrir ticket "destilar X no manifest v2":

- **Tier 1 (urgente):** `field_path` no top 3 com `total_requests ≥ 50` em 30 dias E `workspaces_count ≥ 10`. Indica gap empírico amplo.
- **Tier 2 (relevante):** top 10 com `total_requests ≥ 20`.
- **Tier 3 (monitorar):** novo path aparecendo (não estava no top 30 prev mês) e crescimento mês-a-mês.

Cada tier dispara workflow diferente:
- Tier 1: `product-manager` cria ticket A12 ou A13 com prioridade P0; `financial-planner` decide se path entra no manifest V2.
- Tier 2: revisão mensal; bump de `manifest_version` para incluir.
- Tier 3: mantém na watchlist.

### D5. Privacy — JSONPath é estrutural, não conteúdo

- JSONPath identifica **localização** no E5 schema (ex.: `$.dependentes_irpf.tasso.idade`). Não persiste valor.
- Mas: `field_path` pode conter **nome de família** se o E5 schema usa nomes como chave (ex.: `tasso` em `$.dependentes_irpf.tasso`). Aceito como semi-PII estrutural, retido com mesmas regras do `e5_analysis.json` (workspace-scoped, deleção em cascade via FK).
- Logs ([[ADR-110]]) **não** persistem `field_path` com nome de família — só hash truncado (`mathoms.pipeline.parecer_planejador` logger com `field_path_hash` em vez de raw).

### D6. Integração com [[ADR-188]] pattern

- [[ADR-188]] estabelece **revert_count split** (regra ruim vs abandono) — semântica distinta para signals distintos.
- Análogo aqui:
  - `campos_faltantes_pediria_se_iterasse[]` (fonte primária) = "LLM **explicitamente** sentiu falta" — signal forte.
  - `tool_trace found:false` (fonte secundária) = "LLM tentou e não conseguiu" — signal médio.
- Coluna `reason` permite agregação separada se análise empírica indicar que signals divergem.

### D7. Stateless compliance

- Stage wrapper insere rows via repository pattern (SQLAlchemy session per request).
- Não há cache em memória de "campos já vistos" — coerente com [[ADR-111]].
- Materialized view refresh é Celery task — não bloqueia stage runtime.

## Consequências

**Positivas:**
- Loop de feedback empírico do produto: manifest evolui guiado por dado, não por suposição.
- Defesa em profundidade contra drift: M1 (coverage gate) + M4 (telemetria) cobrem ambos lados (referência morta + gap empírico).
- Pattern reusa [[ADR-188]] — zero invenção de protocolo de telemetria novo.
- Dashboard semanal serve como input direto do review `product-manager` (plano §KPIs).
- Privacy-by-construction: zero valor cliente persistido na telemetria.

**Negativas / trade-offs aceitos:**
- Migration Alembic adicional para tabela + view materializada + Celery task de refresh.
- LLM pode "abusar" do campo `campos_faltantes_pediria_se_iterasse` emitindo paths excessivos (variedade sintética). Mitigação: schema valida JSONPath format ([[ADR-202]] §D7); cap implícito (resposta inteira tem token limit; LLM não vai emitir 1000 paths).
- Risk de "decisão por dado" sem qualitative review: top campo pode ser pedido por motivo errado. Mitigação: tier 1 dispara review humana, não bump automático de manifest.

**Riscos mitigados:**
- **M1 só pega metade do drift** (risco DE/E inverso no plano): M4 cobre o outro lado.
- **Manifest cristalizado em V1** desatualizado: trigger sistemático para evolução.
- **PII em logs de telemetria:** JSONPath structural + hash em logs.

## Implementação

- **Track(s) do plano:** T-23 (`planner-telemetry-field-requests`).
- **Files touched (Ato 6):**
  - `backend/app/models/planner_field_request.py` — model SQLAlchemy
  - Alembic migration — tabela + view materializada + indexes
  - `backend/app/workers/tasks/refresh_planner_top.py` — Celery beat task
  - `backend/app/services/parecer_orchestrator.py` — insere rows após stage success (em Ato 4 já)
- **Critério de aceite:**
  - Tabela popula com pareceres gerados (teste integration).
  - View materializada refresh roda < 1s em até 100k rows (perf test).
  - Privacy check: nenhum valor cliente em rows (teste regression).
  - Dashboard `product-manager` (planilha ou métrica Prometheus simples) acessível.
- **Gates CI:** `pytest backend/tests/test_planner_field_requests.py`, `dev/check_pii_in_logs.py` (defesa adicional).

**Decisão pendente para outros especialistas:**
- **Critérios exatos de tier 1/2/3** (50/20/aparição) — `product-manager` calibra após 1 mês de dado.
- **Política de retenção `planner_field_requests`** (default: indefinida; reavaliar quando >10M rows) — `data-engineer`.
- **Dashboard ferramenta** (Grafana, Metabase, SQL ad-hoc) — `sre-devops` decide.
