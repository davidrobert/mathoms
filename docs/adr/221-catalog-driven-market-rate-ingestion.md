---
id: ADR-221
type: adr
title: "Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto"
status: Proposto
phase: A12
date: "2026-05-18"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-111]]"
  - "[[ADR-116]]"
  - "[[ADR-134]]"
  - "[[ADR-135]]"
  - "[[ADR-143]]"
  - "[[ADR-148]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases: ["ADR 221", "catalog-driven-market-rate-ingestion", "market-rates-catalog"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - phase/a12
  - status/proposto
  - type/adr
---

## Contexto

[[ADR-135]] (Sprint A7, `Decidido`) definiu o **modelo de leitura** de
séries fiscais e câmbio — schema `market_rates(pair, observed_at)` UNIQUE,
regra "última cotação conhecida ≤ data", cache Redis com invalidação por
evento `market_rate.published`. Deixou explicitamente em aberto: **como
e por quem a tabela é populada e atualizada**, com a única diretiva de
que "atualização é operação de produto (admin/ops UI em F7F-Local), não
git commit".

Hoje, 7 meses depois, o estado real é:

- **5 pairs** ativos: `USD/BRL`, `EUR/BRL` (2 snapshots cada, bootstrap
  2024-01-01 + atualização 2026-04-27), `CDI`, `NTNB_REAL_10Y`,
  `IFIX_YIELD_12M` (1 snapshot cada, 2026-05-15 via [[ADR-216]] PR #294).
- **Cobertura temporal pobre.** Card S4 do relatório (`RealEstateYieldCard`,
  mergeado em [#301](https://github.com/davidrobert/mathoms/pull/301))
  exibe spread vs CDI/NTN-B/IFIX com números **fixos de 2026-05-15** —
  até alguém abrir migration nova.
- **Bug de reprodutibilidade latente.** [[ADR-135]] promete que relatório
  de qualquer período re-renderiza com parâmetros vigentes. Mas
  `passive_income_calculator.py::get_market_rate("USD/BRL", 2023-06-15)`
  retorna **nada/erro** — snapshot mais antigo é 2024-01-01. Qualquer
  workspace que suba extratos de 2023 hoje gera conversão silenciosamente
  errada ou crash.
- **Ingestão externa é greenfield.** Backend não tem precedente de pull
  periódico de API externa; `httpx` aparece só em `pipeline_client.py`
  (chamada interna). Mas **Celery Beat já roda em produção**
  (`backend/app/worker.py:52`, 3 tasks: `scan_deadlines`,
  `expire_data_exports`, `process_user_deletions`).

Decisões de produto já cravadas em sessão 2026-05-18 (não revisitar):

1. **Cadência de leitura** durante dogfood: relatório gerado
   **semanalmente**. Pós-dogfood: qualquer dia.
2. **Granularidade do snapshot**: **diário no cron** (Bacen publica diário;
   custo marginal zero).
3. **Scheduler**: **Celery Beat**, alinhado com as 3 tasks existentes.
4. **Fonte primária**: **Bacen SGS** (REST público) + **Tesouro Direto
   CSV**. Feed pago (Bloomberg/Refinitiv) descartado pré-PMF.
5. **Backfill 5 anos** para os 5 pairs ativos (motivação: retenção
   fiscal BR 5y; reproducibilidade ADR-135; narrativas BR ancoram em
   2020-2022).

Esta ADR define o **modelo de ingestão** que materializa essas decisões
sem multiplicar migrations por pair e sem hardcodar "qual série puxar de
onde" no código.

## Decisão

### D1 — Tabela `market_rate_source_catalog` dirige ingestão declarativamente

```sql
CREATE TABLE market_rate_source_catalog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair TEXT NOT NULL,                        -- "USD/BRL", "CDI", "NTNB_REAL_10Y"
  provider TEXT NOT NULL,                    -- "bacen_sgs" | "tesouro_direto_csv"
  provider_series_id TEXT NOT NULL,          -- "12" (Bacen) | "NTNB_20350515" (TD)
  provider_config JSONB NOT NULL DEFAULT '{}',  -- query params, parser hints, unit
  unit TEXT NOT NULL,                        -- "rate_decimal" | "rate_percent_annual" | "price_brl"
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','backfilling','active','paused','retired')),
  backfill_from DATE,                        -- alvo histórico; NULL = só forward
  backfilled_through DATE,                   -- checkpoint do backfill
  last_ingested_at TIMESTAMPTZ,              -- última run forward bem-sucedida
  last_ingested_observed DATE,               -- última observed_at gravada
  failure_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  effective_from DATE NOT NULL DEFAULT '1900-01-01',
  effective_to DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (pair, workspace_id, provider, provider_series_id, effective_from)
);

-- Apenas uma fonte global vigente por pair
CREATE UNIQUE INDEX market_rate_source_catalog_pair_global_active
  ON market_rate_source_catalog (pair)
  WHERE workspace_id IS NULL AND status = 'active' AND effective_to IS NULL;

CREATE INDEX market_rate_source_catalog_active
  ON market_rate_source_catalog (status)
  WHERE status IN ('pending','backfilling','active');

CREATE INDEX market_rate_source_catalog_workspace_pair
  ON market_rate_source_catalog (workspace_id, pair)
  WHERE workspace_id IS NOT NULL;
```

**Decisões cravadas:**

- **`provider` text-livre** (não enum SQL). Adicionar provider novo é
  row + adapter Python — sem migration. Validação em registry
  `backend/app/services/market_rates/providers/__init__.py`
  (`PROVIDERS: dict[str, Provider]`); INSERT em provider desconhecido
  falha no service layer com erro tipado, não no DB. Rejeitada
  alternativa de PG enum porque cada add seria migration + lock.
- **`provider_config jsonb`** captura idiossincrasia (Bacen:
  `{"format":"json"}`; TD: `{"vencimento":"15/05/2035","tipo":"NTNB"}`).
  Mantém schema estável; complexidade fica no adapter por provider.
- **`status` + `backfilled_through` separados.** Lifecycle:
  `pending` (row criada) → `backfilling` (job assíncrono rodando) →
  `active` (`backfilled_through ≥ backfill_from` ou `backfill_from IS NULL`)
  → `paused`/`retired` ops. Beat task forward só consulta
  `WHERE status = 'active'`. Rejeitada alternativa de `active boolean`
  puro porque colapsaria a distinção entre "ainda fazendo backfill" e
  "operando steady-state".
- **`effective_from`/`effective_to` para supersedure temporal.** NTN-B
  "10y" é alvo móvel: hoje aponta `NTNB_20350515` (~9.5y); em 2027 vira
  `NTNB_20400515`. Versionar via FK temporal preserva histórico de qual
  série gerou qual rate. **Troca da série de referência não é
  automatizada** — vira processo ops com alerta `duration < 8y`
  (decisão do planejador, [[ADR-208]]).
- **Multi-tenancy preparado, não implementado no MVP.** Coluna
  `workspace_id NULL = global`; row com `workspace_id` faz override por
  `(pair)`. Lookup canônico: `COALESCE(workspace_override, global)`.
  Precedente em [[ADR-134]]. MVP só usa `NULL = global`; primeiro
  cliente HNW pedindo benchmark privado destrava o caminho sem migration.

### D2 — Idempotência: UPSERT com guard, sem histórico de revisão

```sql
INSERT INTO market_rates (pair, rate, observed_at, source)
VALUES (?, ?, ?, ?)
ON CONFLICT (pair, observed_at) DO UPDATE
SET rate = EXCLUDED.rate, source = EXCLUDED.source
WHERE market_rates.source IS DISTINCT FROM EXCLUDED.source
   OR market_rates.rate IS DISTINCT FROM EXCLUDED.rate;
```

Bacen revisa PTAX raramente, mas quando revisa, sobrescrever é certo —
todos os consumers assumem "última cotação conhecida" ([[ADR-135]]).
**Histórico de revisão não vai pra `market_rates`** — auditoria já mora
em `pipeline_artifacts` (snapshot da rate usada no relatório, [[ADR-148]]).
Adicionar `market_rate_revisions` é aditivo se compliance pedir depois.
Rejeitada alternativa de coluna `revision_of` self-FK porque custo
cognitivo alto pré-PMF e sem caso de uso atual.

### D3 — Backfill: chunks de 90 dias, sequencial, checkpoint via `backfilled_through`

- **Chunks de 90 dias.** Limite prático do Bacen SGS por request.
  Processa chunk, commit, `UPDATE market_rate_source_catalog SET
  backfilled_through = chunk.end_date WHERE id = ?`. Crash retoma do
  checkpoint via `WHERE backfilled_through < backfill_from`.
- **Sequencial, não paralelo.** 5 pairs × ~21 chunks/pair = ~105 chunks
  total, ~30s/pair sequencial. Rejeitada Celery chord/group porque
  paralelizar elimina race em `backfilled_through` por custo desprezível
  em segundos absolutos.
- **Idempotência puro via UNIQUE `(pair, observed_at)`** + checkpoint
  como cinto-suspensório. Re-run sobre chunk já gravado é no-op por D2.

### D4 — Validação durante backfill: skip+log, não abort

- **Range plausível por pair** (`provider_config.range_min/max`).
  Defaults v1: `USD/BRL ∈ [1.0, 20.0]`, `EUR/BRL ∈ [1.0, 25.0]`,
  `CDI ∈ [0.0, 50.0]`, `NTNB_REAL_10Y ∈ [-2.0, 20.0]`,
  `IFIX_YIELD_12M ∈ [0.0, 30.0]`. Fora do range: pula + WARN +
  `failure_count++`.
- **Salto >10% em 1 dia útil**: WARN não-bloqueante. Pode ser real (Real
  teve dia de +12% em 1999, COVID 2020).
- **Source mismatch** (catalog declara `bacen_sgs`, row já gravada por
  outro adapter para mesma data): UPSERT preserva o mais recente, mas
  loga WARN com diff. Sinal de bug, não de dado ruim.
- **Schema drift de fonte**: adapter testa shape do response
  (`if not isinstance(payload[0].get("valor"), str): raise
  BacenSchemaDriftError`). Drift = CRITICAL, pausa catalog row
  (`status='paused'`), não tenta adivinhar. Drift acontece <1×/ano e
  exige humano. Rejeitada alternativa de versionar adapter por
  `date_range` por overengineering.

### D5 — Cache invalidation com janela de 7 dias

Hook após cada UPSERT bem-sucedido publica evento
`market_rate.published(pair, observed_at)`. Consumer invalida:

```python
def on_market_rate_published(pair: str, observed_at: date) -> None:
    for offset in range(8):  # D, D+1, ..., D+7
        invalidate_market_rate(pair, observed_at + timedelta(days=offset))
```

**Por que janela de 7d e não só `(pair, D)` exato:** `get_market_rate`
faz fallback "última conhecida ≤ data" ([[ADR-135]]). Se relatório
consultou `(CDI, 2026-03-10)` e cache resolveu para a rate de
`2026-03-08` (sexta), e Bacen depois publica retroativamente
`2026-03-10`, o cache exato de `(CDI, 2026-03-10)` aponta pra rate
antiga. Invalidar `[D, D+7]` cobre a janela típica de fallback (final de
semana + feriado prolongado). Custo: 8 DELs/evento; trivial em Redis.

### D6 — Tabela `external_data_cache` para payloads brutos de fonte

Tesouro Direto publica um **CSV único consolidado** de ~80MB com todo
histórico (`PrecoTaxaTesouroDireto.csv`). Sem cache de payload bruto,
adapter rebaixaria 80MB/pair/dia.

```sql
CREATE TABLE external_data_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  cache_key TEXT NOT NULL,                   -- ex: "tesouro_direto/precotaxa.csv"
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  content_hash TEXT NOT NULL,                -- SHA-256 do payload
  payload BYTEA NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE (provider, cache_key, fetched_at)
);

CREATE INDEX external_data_cache_lookup
  ON external_data_cache (provider, cache_key, fetched_at DESC);
```

TTL default 24h. Lifecycle: cron limpa `WHERE expires_at < NOW() -
INTERVAL '7 days'`. **Não confundir com `pipeline_artifacts`** — aquele
é payload de pipeline por workspace; este é cache de fonte externa,
global e descartável. Rejeitada alternativa de S3/bucket porque
Postgres já é deploy-target obrigatório e volume é desprezível (1
linha/dia × 80MB × 7d = ~560MB; vacuum gerencia).

### D7 — Beat dedup multi-worker via Redis lock

Celery Beat schedules são single-instance hoje, mas Beat HA é caminho
inevitável pré-PMF (uptime). Solução padrão alinhada com [[ADR-111]]:

```python
@celery_app.task(name="fin.market_rates.ingest_forward")
def ingest_forward_market_rates() -> dict[str, Any]:
    redis = get_redis_safe()
    if redis is None or not redis.set(
        "market_rates:tick:lock", "1", ex=300, nx=True
    ):
        logger.info("market_rates.ingest_forward: skipping (held)")
        return {"skipped": True}
    try:
        return _do_ingest_forward()
    finally:
        redis.delete("market_rates:tick:lock")
```

Padrão já usado em `invitation_service`. TTL 5min cobre run completa
(~10s de margem ampla). Rejeitada alternativa de SQL advisory lock
porque obriga conexão persistente durante a task; Redis é mais simples
e já é dependência de cache.

### D8 — Normalização (CDI nominal → líquido) fica no adapter, não no catalog

`market_rates` grava o que Bacen publica (`unit='rate_percent_annual'`
para CDI nominal a.a.). `real_estate_adapter.py::fetch_benchmarks`
continua aplicando IR 17,5% no call-site. **Por quê:** normalização é
regra de produto que varia por workspace (PJ tem alíquota efetiva
diferente), não de fonte. Catalog com `normalization_rule_id` apontando
para outra tabela complica sem caso de uso atual. Quando virar
multi-regra, vira ADR separada alinhada com [[ADR-143]] (rules-as-code).

## Custos & Trade-offs

- **Storage:** 5 pairs × 5y × ~250 dias úteis ≈ 6.250 rows iniciais +
  ~1.250 rows/ano steady-state. Trivial. `external_data_cache` ≈ 560MB
  rotativos.
- **Bacen SGS rate-limit não documentado.** Anedoticamente ~50 req/min
  antes de 429. Backfill 5y sequencial fica em ~105 chunks total —
  passa em ~3min com pacing 2s/req. Forward daily: 5 reqs, irrelevante.
  Adapter precisa retry com backoff exponencial em 429/5xx (mitigação:
  3 tentativas com 2h/6h/24h, alinhado com D4).
- **Governance contínua de catalog rows.** Mudança de pair (deprecar
  IFIX, trocar NTN-B 10y para 2040) é operação manual com PR. Sem isso,
  catalog envelhece silenciosamente. Aceito: precedente em [[ADR-135]]
  já institui que atualização de série é operação de produto.
- **Multi-tenancy preparada mas zero linha de teste em MVP.** Risco de
  rot — coluna nunca exercitada pode quebrar quando o primeiro override
  entrar. Mitigação: 1 teste de integração exercita o path
  `COALESCE(workspace, global)` desde o início, mesmo com dado sintético.
- **Falha de Bacen >36h não tem retry agressivo.** Backoff 2h/6h/24h
  significa que se Bacen ficar 2 dias down, `last_ingested_age_seconds`
  fica em ~48h até próximo tick. Aceito: alerta gauge no SRE cobre
  detecção (D9 deferred a ondas posteriores).

## Alternativas consideradas

- **Snapshot por migration (status quo).** Cada novo pair = nova
  migration; cada update = nova migration. Não escala; vira "ADR ignorada
  por design".
- **GitHub Actions cron em vez de Celery Beat.** Funciona mas: (a) sem
  retry nativo padronizado, (b) secrets/env management fora do app,
  (c) sem precedente no repo. Rejeitada por consistência operacional.
- **Botão admin manual no console interno ([[ADR-116]]).** Considerado
  para v0 mas frágil — dogfood já é semanal; esquecer de clicar =
  card stale silenciosa. Botão entra na onda 3 do plano como
  **complemento** ao cron, para casos de "forçar refresh" ou onboarding
  de pair novo.
- **Feed pago (Bloomberg/Refinitiv/TradingView).** $$/mês alto, cobertura
  ampla; descartado pré-PMF. Reabrir quando aparecer pair que só feed
  pago tem (índices corporativos privados).
- **Tabela única `market_rates` com colunas `provider`/`provider_series_id`
  (sem catalog separado).** Acoplaria observação (row de rate) à
  declaração de fonte (qual série existir). Catalog separado deixa
  declarar "vou puxar isso" antes de ter dado e gerenciar lifecycle do
  pair (paused/retired) sem mexer em rows de rate.
- **Sourceing on-demand (lazy pull quando pipeline lê e cache miss).**
  Acopla latência de relatório à disponibilidade do Bacen; primeira
  execução do dia paga round-trip; falha de Bacen quebra geração de
  relatório. Cron + cache desacopla. Rejeitada.

## Implementação

PR fundacional **(W1)** — Bacen SGS only, USD/BRL + CDI:

- Migration Alembic `add_market_rate_source_catalog.py` com
  `op.execute("SET lock_timeout = '5s'")`; downgrade reversível
  (drop tabela + index; rows em `market_rates` permanecem intactas).
- Migration Alembic `add_external_data_cache.py` separada (D6); pode ir
  no mesmo PR mas committada como diff distinto.
- `backend/app/models/market_rate_source_catalog.py` (SQLAlchemy) +
  `backend/app/models/external_data_cache.py` + repos.
- `backend/app/services/market_rates/providers/__init__.py` — registry
  `PROVIDERS: dict[str, Provider]`.
- `backend/app/services/market_rates/providers/bacen_sgs.py` — adapter
  Bacen com shape-check, retry 429/5xx, range validation.
- `backend/app/services/market_rates/ingestion.py` — service que itera
  catalog `status='active'` e chama adapter por pair; publica eventos
  `market_rate.published` por row.
- `backend/app/tasks/market_rates_sync.py` —
  `ingest_forward_market_rates` (daily) + Redis lock D7.
- `backend/app/worker.py` — adicionar entry no `beat_schedule`:
  `"market-rates-forward-daily": {"task": "fin.market_rates.ingest_forward",
  "schedule": 86400.0}`.
- Seed inicial em `dev/seed_market_rate_catalog.py` (idempotente):
  cria 2 catalog rows (USD/BRL → série Bacen 1, CDI → série Bacen 12),
  `status='pending'`, `backfill_from='2021-05-18'`.
- Hook de invalidação de cache (D5) em
  `backend/app/services/fiscal_cache.py`.
- Registro em [`docs/reference/STATELESS_AUDIT.md`](../reference/STATELESS_AUDIT.md)
  §2 para o Redis lock.
- Testes: golden de extração contra fixture Bacen capturada (não bate
  network em CI); teste de idempotência (re-run não duplica); teste de
  Redis lock dedup.

PR **(W2)** — Backfill async + Tesouro Direto:

- `backend/app/tasks/market_rates_sync.py::backfill_market_rates` —
  task assíncrona que processa catalog `status='backfilling'` em chunks.
- `backend/app/services/market_rates/providers/tesouro_direto.py` —
  adapter que usa `external_data_cache` para o CSV de 80MB.
- Lifecycle task `external_data_cache_janitor` (Celery Beat daily).
- Seed adicional para `EUR/BRL`, `NTNB_REAL_10Y`, `IFIX_YIELD_12M`.

PR **(W3)** — Admin UI no console interno ([[ADR-116]]):

- CRUD de catalog rows.
- Botão "forçar refresh" por pair (dispara `ingest_forward` adhoc).
- Painel de health (`last_ingested_at`, `failure_count`, `last_error`).

PR **(W4)** — Observabilidade:

- Counter `mathoms.market_rates.ingest{pair,provider,status}`.
- Gauge `mathoms.market_rates.last_ingested_age_seconds{pair}`.
- Alerta `last_ingested_age_seconds{pair} > 86400 AND status='active'`
  → escalonamento ops.
- Review `sre-devops` antes de merge.

**Dependências:**

- W1 destrava produção do card S4 com dado fresco (USD/BRL fixa o bug
  latente do `passive_income_calculator`; CDI dá benchmark fresco).
- W2 destrava cobertura completa do card S4 (NTN-B + IFIX) com história.
- W3 e W4 são pós-MVP — não bloqueiam consumo, mas são gate pré-GA
  multi-tenant.

## Critério de aceite

- [ ] Catalog table criada com migration reversível; downgrade preserva
      `market_rates`.
- [ ] Adapter Bacen SGS faz pull + UPSERT idempotente (re-run não muda
      `market_rates`).
- [ ] Redis lock impede dupla execução em workers concorrentes.
- [ ] Backfill 5y processa chunks de 90 dias com checkpoint via
      `backfilled_through`; crash mid-backfill retoma sem perda nem
      duplicação.
- [ ] Range validation skipa rates fora de bounds + incrementa
      `failure_count` + log WARN.
- [ ] Schema drift de Bacen pausa catalog row (`status='paused'`) +
      log CRITICAL.
- [ ] Cache Redis invalida janela `[D, D+7]` após cada UPSERT.
- [ ] `external_data_cache` deduplica CSV TD; janitor expira >7d.
- [ ] `passive_income_calculator.get_market_rate("USD/BRL", 2023-06-15)`
      retorna a rate de 2023-06-15 (resolução do bug latente).
- [ ] `dev/check_pipeline_boundaries.py` continua verde (adapters em
      `backend/app/services/market_rates/`, task em `backend/app/tasks/`,
      zero import de `fastapi`/`celery`/`sqlalchemy` em `pipeline/`).
- [ ] Plano canônico [`docs/plan/MARKET_RATES_INGESTION/_README.md`](../plan/MARKET_RATES_INGESTION/_README.md)
      sincronizado com as ondas executadas; flippa esta ADR para
      `Decidido (A12)` no PR que fecha W2.
