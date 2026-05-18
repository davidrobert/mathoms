---
id: PLAN-market-rates-ingestion
type: plan
title: Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto
status: draft
sprint_origem: A12
sprint_atual: A12
sprints_envolvidas: [A12]
created_at: "2026-05-18"
last_review: "2026-05-18"
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-221]]"
tags:
  - type/plan
  - status/draft
  - area/backend
  - area/persistence
  - area/pipeline
  - phase/a12
---

# Ingestão de market rates dirigida por catálogo

> **Origem:** sessão 2026-05-18 — durante revisão do card S4 do relatório
> (`RealEstateYieldCard`, mergeado em [#301](https://github.com/davidrobert/mathoms/pull/301))
> ficou evidente que CDI/NTN-B/IFIX no DB estão como **snapshot único de
> 2026-05-15** ([#294](https://github.com/davidrobert/mathoms/pull/294)).
> Workspace dogfood gera relatório **semanalmente**; durante 3 das 4
> semanas o card mostra dado vencido. Forward-only quebra a promessa de
> reproducibilidade da [[ADR-135]] — `passive_income_calculator` chama
> `get_market_rate("USD/BRL", 2023-06-15)` e bate em vazio (snapshot
> mais antigo é 2024-01-01).
>
> **Co-design:** sessão 2026-05-18 com `data-engineer` convergiu em
> arquitetura **catalog-driven** com backfill 5y e cron daily. Decisões
> de produto (cadência, granularidade, fonte) e schema do catalog +
> estratégia de backfill consolidadas em [[ADR-221]] `Proposto`.
>
> **ADR canônica:** [[ADR-221]] — `Proposto` (2026-05-18). Referencia
> [[ADR-135]] (modelo de leitura, `Decidido`) sem supersedure: 135 define
> **como ler** `market_rates`, 221 define **como popular**. Gate
> obrigatório por CLAUDE.md §"Política operacional — ADR Proposto antes
> de PR P0/P1".
>
> **Não bloqueia / não é bloqueado por:** plano [PLAN-s4-real-estate-enrichment](../S4_REAL_ESTATE_ENRICHMENT/_README.md)
> (✅ done; consome `market_rates` no estado atual com gracefule
> degradation). Card S4 funciona com snapshot único; este plano destrava
> dado fresco + histórico.

---

## Status

| Onda | Status | PR | Notas |
|---|---|---|---|
| W1 — Bacen SGS + catalog + Beat task forward (USD/BRL + CDI) | 📋 ready | — | Migration catalog, adapter Bacen, Redis lock, seed inicial, hook invalidação cache. |
| W2 — Backfill async + Tesouro Direto (EUR/BRL, NTN-B, IFIX) | 📋 ready | — | Task assíncrona com checkpoint; adapter TD via `external_data_cache`. Flippa ADR-221 → `Decidido`. |
| W3 — Admin UI no console interno (ADR-116) | 📋 next | — | CRUD catalog + botão forçar refresh + painel health. Pós-MVP, pré-GA multi-tenant. |
| W4 — Observabilidade + alertas (SRE review) | 📋 next | — | Counter/gauge + alerta `last_ingested_age_seconds > 86400`. |

---

## Tese central

> Durante a janela de uso semanal do relatório (dogfood + pós-dogfood
> multi-tenant), benchmarks financeiros precisam refletir realidade do
> dia em que o relatório é gerado, **e** períodos passados precisam
> re-renderizar com a rate vigente naquela data. Snapshot único quebra
> ambos. Catalog-driven com cron daily e backfill 5y resolve sem trocar
> contrato de leitura ([[ADR-135]]) e sem multiplicar migrations por pair.

ADR-221 fixa **o que** muda arquiteturalmente. Este plano fixa **como**
implementar — em 4 ondas com gates explícitos. W1 e W2 destravam
produção; W3 e W4 são gate pré-GA.

---

## Pré-requisitos bloqueantes

| # | Bloqueio | Origem | Impacto se não resolvido |
|---|---|---|---|
| PR-1 | [[ADR-221]] mergeada como `Proposto` | CLAUDE.md §"Política operacional" | PR de implementação sem ADR fere a regra. **Esta sessão.** |
| PR-2 | Celery Beat rodando em produção | `backend/app/worker.py:52` (3 tasks ativas) | Sem Beat, cron daily não tem onde rodar. **✅ existe.** |
| PR-3 | Redis disponível para lock (D7 da ADR) + cache (D5) | `backend/app/services/fiscal_cache.py` | Sem Redis, dedup multi-worker degrada para "best effort"; cache continua falhando aberto. **✅ existe.** |
| PR-4 | `market_rates` table com schema [[ADR-135]] | Sprint A7 | Modelo de escrita assume tabela existente. **✅ produção.** |

Todos os pré-requisitos exceto PR-1 já estão em produção. PR-1 é
entregue nesta sessão junto deste plano.

---

## W1 — Bacen SGS + catalog + forward daily

**Objetivo:** entregar caminho fim-a-fim do menor escopo possível para
validar arquitetura: catalog + 1 provider + 1 task forward, com USD/BRL
e CDI (os pairs com maior impacto imediato no produto).

**Entregáveis:**

1. Migration Alembic `add_market_rate_source_catalog.py` com
   `op.execute("SET lock_timeout = '5s'")` e downgrade reversível.
2. Migration Alembic `add_external_data_cache.py` separada (preparada
   para W2, sem consumer em W1).
3. Models SQLAlchemy:
   - `backend/app/models/market_rate_source_catalog.py`
   - `backend/app/models/external_data_cache.py`
4. Repositories:
   - `backend/app/repositories/market_rate_source_catalog_repository.py`
5. Provider registry:
   - `backend/app/services/market_rates/providers/__init__.py` (registry)
   - `backend/app/services/market_rates/providers/base.py` (Protocol)
   - `backend/app/services/market_rates/providers/bacen_sgs.py` (adapter)
6. Service de ingestão:
   - `backend/app/services/market_rates/ingestion.py` —
     itera catalog `status='active'`, chama adapter, UPSERT em
     `market_rates`, publica eventos `market_rate.published`.
7. Celery task:
   - `backend/app/tasks/market_rates_sync.py::ingest_forward_market_rates`
     com Redis lock (ADR-221 D7).
8. Beat schedule entry em `backend/app/worker.py`:
   ```python
   "market-rates-forward-daily": {
       "task": "fin.market_rates.ingest_forward",
       "schedule": 86400.0,  # diário
   },
   ```
9. Hook de invalidação de cache (ADR-221 D5) em
   `backend/app/services/fiscal_cache.py`:
   ```python
   def on_market_rate_published(pair: str, observed_at: date) -> None:
       for offset in range(8):
           invalidate_market_rate(pair, observed_at + timedelta(days=offset))
   ```
10. Seed inicial em `dev/seed_market_rate_catalog.py` (idempotente):
    - USD/BRL → provider `bacen_sgs`, série `1`, `backfill_from='2021-05-18'`
    - CDI → provider `bacen_sgs`, série `12`, `backfill_from='2021-05-18'`
    - Status inicial `pending` (W2 transiciona para `backfilling` → `active`)
11. Registro em
    [`docs/reference/STATELESS_AUDIT.md`](../../reference/STATELESS_AUDIT.md)
    §2 para o Redis lock.

**Testes:**

- Unit: registry rejeita provider desconhecido; range validation skipa
  fora de bounds.
- Integration: golden de extração contra fixture Bacen capturada
  (`tests/fixtures/bacen_sgs_cdi_2026-04.json`). CI não bate network.
- Integration: re-run idempotente — segunda execução não cria rows
  duplicadas, UPSERT só toca onde `rate` ou `source` diferente.
- Integration: Redis lock dedup — 2 invocações concorrentes,
  segunda retorna `{"skipped": True}`.
- Integration: hook de invalidação remove cache em janela [D, D+7].

**Gate de saída:**

- Migration aplicada em dev sem erro.
- `ingest_forward_market_rates()` em dev (vs Bacen real) puxa CDI do
  dia, grava 1 row, publica 1 evento.
- `passive_income_calculator.get_market_rate("USD/BRL", date.today())`
  retorna rate fresca.
- Suíte completa verde local + CI.
- ADR-221 referenciada no commit body do PR.

**Duração estimada:** 2-3 dias.

**Owner:** orquestrador. Sem review obrigatória de subagente
(`data-engineer` já co-designou o schema; review se PR ficar grande).

---

## W2 — Backfill async + Tesouro Direto

**Objetivo:** completar cobertura de pairs (EUR/BRL, NTN-B, IFIX) +
backfill 5y para os 5 pairs, fechando a promessa de reproducibilidade
da [[ADR-135]]. Flippa ADR-221 para `Decidido (A12)` ao mergear.

**Entregáveis:**

1. Task assíncrona:
   `backend/app/tasks/market_rates_sync.py::backfill_market_rates(catalog_row_id)`
   — processa chunks de 90 dias, atualiza `backfilled_through`,
   transita `pending → backfilling → active`.
2. Trigger:
   - Manual via `dev/trigger_market_rate_backfill.py <catalog_id>` para
     v1 (admin UI vem em W3).
   - Automático ao criar catalog row com `backfill_from` definido
     (post-insert hook? ou explicit dispatch no service de admin? —
     decidir no PR; preferência: explicit dispatch para evitar magic).
3. Adapter Tesouro Direto:
   - `backend/app/services/market_rates/providers/tesouro_direto.py`
   - Usa `external_data_cache` para o CSV consolidado (~80MB; TTL 24h).
   - Parser extrai linhas por `vencimento` declarado em
     `provider_config.vencimento`.
4. Lifecycle task:
   `backend/app/tasks/market_rates_sync.py::external_data_cache_janitor`
   — Beat daily, deleta rows com `expires_at < NOW() - INTERVAL '7 days'`.
5. Seed adicional em `dev/seed_market_rate_catalog.py`:
   - EUR/BRL → provider `bacen_sgs`, série `21619`
   - NTNB_REAL_10Y → provider `tesouro_direto_csv`, `provider_config:
     {"vencimento":"15/05/2035","tipo":"NTNB"}`
   - IFIX_YIELD_12M → escolha de fonte aberta no PR
     (Bacen não publica direto; opções: scraping FundsExplorer ou
     compute do índice cotação no mesmo CSV TD; **decidir no PR W2**).
6. Backfill execution em produção:
   - Trigger para 5 catalog rows com `backfill_from='2021-05-18'`.
   - Aguarda `status='active'` em todas (5 × ~30s ≈ 3min).
   - Validação: `SELECT pair, MIN(observed_at), MAX(observed_at),
     COUNT(*) FROM market_rates GROUP BY pair` — esperado ~1.250 dias
     úteis cobertos por pair em 5 anos.

**Testes:**

- Integration: backfill resume — interrupção mid-chunk, retomada não
  duplica nem perde dado.
- Integration: TD adapter usa cache — segunda chamada no mesmo dia não
  rebaixa CSV.
- Integration: `passive_income_calculator.get_market_rate("USD/BRL",
  2023-06-15)` retorna a rate de 2023-06-15 (fim do bug latente).
- Golden: payload E5 com workspace contendo holdings dolarizadas em
  período histórico produz mesma conversão em re-runs.

**Gate de saída:**

- 5 pairs com `status='active'` em produção.
- Backfill 5y validado por pair (counts, ranges, sem gaps suspeitos).
- ADR-221 flipada para `Decidido (A12)` no PR final.
- Plano transita para `in_progress` (W3/W4 pendentes).

**Duração estimada:** 3-4 dias.

**Owner:** orquestrador. Review pré-merge: `data-engineer` para
validação de backfill (idempotência, validação de gaps, `external_data_cache`).

---

## W3 — Admin UI no console interno (ADR-116)

**Objetivo:** dar ferramenta operacional para o time interno gerenciar
catalog sem precisar de PR/SQL direto. Pré-GA multi-tenant.

**Entregáveis:**

1. Endpoint admin em `backend/app/api/internal/market_rates_catalog.py`:
   - `GET /internal/market-rates/catalog` — lista com filtros
     `status`/`provider`/`pair`.
   - `POST /internal/market-rates/catalog` — cria row (validação de
     provider via registry).
   - `PATCH /internal/market-rates/catalog/{id}` — pausa/retorna,
     ajusta `backfill_from`.
   - `POST /internal/market-rates/catalog/{id}/backfill` — dispara
     backfill assíncrono.
   - `POST /internal/market-rates/catalog/{id}/refresh` — dispara
     ingest forward adhoc para `(pair, today)`.
2. Frontend admin (console interno, [[ADR-116]] track):
   - Tabela catalog rows com filtros + sort.
   - Modal de edição com validação client-side.
   - Painel de health por pair: `last_ingested_at`,
     `last_ingested_observed`, `failure_count`, `last_error`.
   - Botão "forçar refresh" + "iniciar backfill".
3. Audit log:
   - Toda operação admin em market_rate_source_catalog grava
     `AuditAction.market_rate_catalog_mutated` com diff.

**Gate de saída:**

- Operador interno cria/pausa pair sem PR/SQL.
- Health panel reflete estado real (auto-refresh 30s).
- Audit log completo dos últimos 30d acessível.

**Duração estimada:** 3-4 dias.

**Owner:** orquestrador + `product-designer` (review UX se ficar
não-trivial; provavelmente skipa por ser admin-only).

---

## W4 — Observabilidade + alertas

**Objetivo:** instrumentar para que falhas de ingestão sejam visíveis
antes de o card S4 mostrar dado stale para o usuário final.

**Entregáveis:**

1. Métricas em `backend/app/services/market_rates/ingestion.py`:
   - Counter `mathoms.market_rates.ingest{pair,provider,status=ok|skip|fail}`
   - Histogram `mathoms.market_rates.ingest.duration_seconds{provider}`
   - Gauge `mathoms.market_rates.last_ingested_age_seconds{pair}`
2. Alertas:
   - `last_ingested_age_seconds{pair} > 86400 AND status='active'`
     → P2 (Bacen down ou catalog `paused` esquecido).
   - `failure_count{pair} > 5 in 24h` → P3 (degradação intermitente).
   - `status='paused'` por >24h → P3 (catalog row órfã).
3. Dashboard (Grafana ou equivalente):
   - Última observed_at por pair (linha temporal).
   - Volume de requests Bacen + taxa de erro.
   - Tamanho de `external_data_cache` (lifecycle saudável).
4. Runbook `docs/reference/runbooks/market_rates_ingestion.md`:
   - Sintoma → diagnóstico → ação para cada alerta.
   - Procedimento para troca de série NTN-B (alvo móvel, ADR-221 D1).

**Gate de saída:**

- Métricas emitidas em prod.
- Pelo menos 1 alerta exercitado manualmente (pausar pair, esperar
  >24h em dev, validar disparo).
- Runbook revisado por `sre-devops`.

**Duração estimada:** 2 dias.

**Owner:** orquestrador + `sre-devops` (review obrigatório).

---

## Dependências entre ondas

```
W1 (Bacen + catalog + forward daily)
  ↓
W2 (backfill async + TD) → flippa ADR-221 para Decidido
  ↓
W3 (admin UI)  ─┬─ paralelizáveis após W2
W4 (observability) ─┘
```

W1 e W2 destravam consumo de produção (card S4 com dado fresco +
histórico). W3 e W4 são gate pré-GA multi-tenant; podem ir em paralelo
após W2.

---

## Riscos consolidados

| Risco | Probabilidade | Mitigação | Owner |
|---|---|---|---|
| Bacen SGS rate-limit em backfill 5y dispara 429 | Baixa-média | Pacing 2s/req + retry exponencial 429/5xx (3 tentativas). Backfill sequencial limita concorrência. | W1/W2 |
| Schema drift de Bacen entre dev e prod | Baixa | Adapter testa shape no response; drift = `status='paused'` + CRITICAL. Drift histórico Bacen ≈ 1×/ano. | W1 |
| CSV Tesouro Direto muda formato | Média (já mudou em 2020) | Parser por `version` interno + `BacenSchemaDriftError`/`TesouroSchemaDriftError`; pausa adapter, exige humano. | W2 |
| Backfill mid-chunk crash deixa dado parcial | Baixa | UNIQUE `(pair, observed_at)` + `backfilled_through` checkpoint. Retomada idempotente. | W2 |
| Bacen down >36h sem alerta | Média | `last_ingested_age_seconds > 86400` alerta P2 (W4). Antes de W4, monitoramento manual. | W4 |
| IFIX fonte aberta indecidida na W2 | Média | Decidir no PR W2: opções FundsExplorer scrape (ToS frágil), compute B3 público, ou pular IFIX pré-GA. Card S4 já funciona sem IFIX (alerta degrade). | W2 |
| Coluna `workspace_id` sem teste exercitando o path | Baixa | 1 teste integration com dado sintético workspace override desde W1. | W1 |
| NTN-B 10y alvo móvel — `effective_to` esquecido | Baixa-média | Runbook W4 + alerta `duration < 8y` no painel admin. Decisão do planejador ([[ADR-208]]). | W4 |
| Custo cognitivo do `external_data_cache` vs payload pequeno do Bacen | Baixa | Tabela só é populada por adapters que precisam (TD); Bacen escreve direto em `market_rates`. | W2 |

---

## Critério de "concluído" (definition of done)

Plano transita para `done` quando:

1. ADR-221 mergeada como `Proposto` em W1 e flippada para
   `Decidido (A12)` em W2.
2. 5 pairs com `status='active'` em produção, backfilled 5y.
3. `passive_income_calculator.get_market_rate(...)` resolve para
   qualquer data ∈ [2021-05-18, hoje].
4. Card S4 em produção exibe benchmarks frescos a cada execução
   semanal de relatório (validado em workspace dogfood).
5. Admin UI permite operação sem SQL/PR (W3).
6. Alertas exercitados, runbook publicado (W4).
7. Entry no `docs/CHANGELOG.md` (A12).

**Não conta como done:**

- W1+W2 mergeados mas backfill não executado em prod — fica
  `in_progress` até `SELECT MIN(observed_at) FROM market_rates WHERE
  pair='CDI'` retornar data de 2021.
- W3/W4 pendentes não impedem `in_progress → mostly_done` mas impedem
  `done` antes de GA multi-tenant.

---

## Referências cruzadas

- [[ADR-221]] — decisão canônica (catalog + backfill + UPSERT + Redis lock)
- [[ADR-135]] — modelo de leitura de `market_rates` (referenciada, não superseded)
- [[ADR-111]] — stateless rigoroso (Redis lock para Beat dedup)
- [[ADR-134]] — ConfigStore (precedente de override por workspace)
- [[ADR-148]] — snapshot changelog (auditoria de rate usada no relatório)
- [[ADR-116]] — console interno (W3)
- [[ADR-212]] — DBArtifactStore (precedente de hook validation)
- [[ADR-216]] — cap rate líquido (consumer de CDI/NTN-B/IFIX no card S4)
- Co-design: `data-engineer` (sessão 2026-05-18 — schema do catalog +
  estratégia de backfill + invalidação de cache + `external_data_cache`)
