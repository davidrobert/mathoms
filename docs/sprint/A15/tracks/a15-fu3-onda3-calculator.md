---
id: TRACK-a15-fu3-onda3-calculator
type: track
title: "Track A15 FU-3 Onda 3 — Calculator + resolver puro + payload E5"
sprint: A15
plan: PLAN-imovel-financiado
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a15
  - status/ready
  - area/pipeline
  - area/methodology
  - area/backend
---

# Track A15 FU-3 Onda 3 — Calculator + resolver puro

> **Lane:** Sprint A15 · **Plano canônico:**
> [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 3
> · **ADR canônica:** [[ADR-227]] §D3 + §D4 + §D5
> · **Branch prefix:** `agent/a15-fu3-onda3-calculator/*`
> · **Pré-requisito externo:** Onda 1 mergeada (tabelas existem) + Onda 2 idealmente rodada em dogfood (`5@5.com`) antes desta Onda
> · **Bloqueia:** Onda 4 (API) — endpoints precisam do resolver + adapter funcionais

## Briefing

Coração da mudança ([[ADR-227]] §D3 — invariante de apresentação + §D4 resolver puro + §D5 TTL sem fallback). Onda 3 finalmente popula o trilho `valor_imovel_origem="mercado"` que existe em [`real_estate_metrics.py`](../../../../pipeline/domain/services/real_estate_metrics.py) (linha 71) desde o plano S4 (PRs #280-#305) mas **nunca foi populado**.

Três peças coordenadas:

1. **Resolver puro module-level** em `pipeline/domain/services/real_estate_valuation_resolver.py` — função pura `resolve_valor_efetivo(property_id, valor_irpf_brl, context, ttl_days=365) -> (Decimal, Literal["mercado","irpf"])`. Cascade: `property_market_value` mais recente (≤12m, sinaliza staleness) || `valor_irpf` (fallback). [[ADR-111]] stateless: sem cache in-memory; lookup vem do dict pré-carregado em `RealEstateValuationContext`.

2. **`RealEstateValuationContext` value object** ([[ADR-097]] D3) — dataclass frozen com `market_values: Mapping[str, MarketValueResolution]`, `debts_by_property: Mapping[str, Decimal]`, `today: date` (determinístico em teste). Adapter `backend/app/services/real_estate_valuation_adapter.py` carrega DB → context com **2 SELECTs por workspace** (DISTINCT ON / ROW_NUMBER pra market_values; GROUP BY property_id pra debts). Repos da Onda 1 expõem queries.

3. **`PatrimonioCalculator` consome via `PatrimonioInputs.valuation_context`** (opcional para retrocompat — workspaces sem `property_market_value` declarado mantêm comportamento atual). [`_compute_investivel_efetivo`](../../../../pipeline/domain/services/patrimonio_calculator.py) usa `max(0, valor_efetivo − saldo_devedor)` por imóvel gerador (locado/comercial). **`_split_imoveis` permanece reportando bruto na tabela de composição** — invariante ADR-227 §D3 (cat_2 bruto, líquido só em `investivel_efetivo`).

Payload E5 ganha campos aditivos: `imoveis.{geradores,nao_geradores}[].source_valor: "mercado"|"irpf"`, `staleness_days: int|null`, `saldo_devedor_brl: Decimal|null`. Schema [`config/schemas/e5_analysis.schema.json`](../../../../config/schemas/e5_analysis.schema.json) bumpa version.

Warning de domínio tipado `DebtVsIrpfDeclaracaoConflict` ([[ADR-097]] D1) emitido quando `soma(per-property) / total_dividas_irpf > 1.1`. Per-property vence agregado IRPF (mais fresco/granular); warning sinaliza inconsistência.

## Critério de aceite (do plano §Onda 3)

- [ ] `pipeline/domain/services/real_estate_valuation_resolver.py`:
  - Função pura `resolve_valor_efetivo(...)` retorna `(Decimal, Literal["mercado","irpf"])`.
  - Sinaliza `staleness_days` no resultado quando `source="mercado"`.
  - Test unit cobrindo: market_value fresh (<12m), market_value stale (>12m, mantém uso + staleness), market_value ausente (fallback irpf), property_id desconhecido (fallback irpf).
- [ ] `pipeline/domain/services/patrimonio_types.py`:
  - `RealEstateValuationContext` dataclass frozen com `market_values`, `debts_by_property`, `today`.
  - `PatrimonioInputs.valuation_context: RealEstateValuationContext | None = None` (opcional).
- [ ] `pipeline/domain/services/patrimonio_calculator.py`:
  - `_compute_investivel_efetivo` usa líquido por imóvel gerador quando `valuation_context` presente.
  - `_split_imoveis` permanece reportando bruto (sem subtrair saldo devedor).
  - Test paridade: workspace sem `valuation_context` → comportamento idêntico ao atual.
  - Test novo: workspace com market_value + debt vinculada → `investivel_efetivo` usa `max(0, valor_mercado − saldo_devedor)`.
- [ ] `backend/app/services/real_estate_valuation_adapter.py`:
  - Carrega `market_values` (1 row por property, mais recente, DISTINCT ON / ROW_NUMBER).
  - Carrega `debts_by_property` (GROUP BY com `percentual_atribuicao_imovel` aplicado).
  - Cap: 2 SELECTs por workspace; integration test mede.
- [ ] Payload E5 aditivo:
  - `imoveis[].source_valor`, `imoveis[].staleness_days`, `imoveis[].saldo_devedor_brl` opcionais.
  - Schema `config/schemas/e5_analysis.schema.json` bumpa version (aditivo, retrocompat).
  - Goldens E5 atualizados (`tests/test_e5_golden_execution.py`).
- [ ] Warning `DebtVsIrpfDeclaracaoConflict` dataclass tipada com `.format()` ([[ADR-097]] D1).
- [ ] `dev/check_pipeline_boundaries.py` verde — resolver em `pipeline/domain/` permanece puro; lookup vem do adapter em `backend/app/services/`.
- [ ] Test integration: deletar `PropertyIdentity` com Debt vinculada → IntegrityError (RESTRICT). Adapter responde com 409 (em Onda 4).
- [ ] `pytest tests -q` + `pytest backend/tests -q` + `pre-commit run --all-files` verdes.

## Arquivos esperados

**Novos:**

- `pipeline/domain/services/real_estate_valuation_resolver.py`
- `backend/app/services/real_estate_valuation_adapter.py`
- `pipeline/domain/services/types/real_estate_valuation_context.py` (ou estender `patrimonio_types.py`)
- `tests/unit/pipeline/test_real_estate_valuation_resolver.py`
- `backend/tests/services/test_real_estate_valuation_adapter.py`
- `tests/test_e5_golden_execution_with_market_value.py` (caso novo)
- `tests/test_e5_golden_execution_fallback_irpf.py` (caso paridade)

**Editados:**

- `pipeline/domain/services/patrimonio_types.py` — `PatrimonioInputs.valuation_context` opcional.
- `pipeline/domain/services/patrimonio_calculator.py` — `_compute_investivel_efetivo` usa líquido.
- `pipeline/domain/services/endividamento_analyzer.py` — gera `DividaItem` por property (não mais hardcoded "Financiamento imobiliário ({nome})").
- `config/schemas/e5_analysis.schema.json` — bump version, campos aditivos.
- `tests/test_e5_golden_execution.py` — goldens atualizados.
- `pipeline/llm/...` (se houver warning ou prompt afetado, raro).

## Decisões já fechadas (do co-design 2026-05-19)

- **Resolver puro module-level** + Protocol opcional no consumer (`senior-cto`) — função em `pipeline/domain/services/` (puro, sem I/O); Protocol em `backend/app/` para teste injetar fake. ADR-111 stateless: sem cache.
- **`RealEstateValuationContext` separado** (não estender `PatrimonioConfig`) (`senior-cto`) — `PatrimonioConfig` é config; `Context` é dado de domínio carregado do DB. ISP preservado.
- **TTL sem fallback automático** ([[ADR-223]] anti-padrão) — após 12m, sistema mantém valor declarado, sinaliza `staleness_days` no payload, frontend (Onda 5) decide badge visual. NÃO troca para `valor_irpf` automaticamente.
- **Per-property vence agregado IRPF** quando ambos existem; warning quando ratio >1.1 (`financial-planner`).
- **Bruto na tabela, líquido em `investivel_efetivo`** ([[ADR-227]] §D3) — preserva invariante "categoria = ativo bruto, passivo = bucket separado". UX dual no relatório (Onda 5).
- **Adapter carrega context em 2 SELECTs por workspace** — pattern read-time service-layer (ADR-215 §6 + ADR-224 §5). Materialização rejeitada (D estava entre alternativas, escolheu C).
- **`DistINCT ON` no Postgres, `ROW_NUMBER` no SQLite** — diferentemente do pattern existente, calculator usa este para evitar carregar histórico completo em memória.
- **`endividamento_analyzer` lê per-property quando existe** — substituir descrição hardcoded "Financiamento imobiliário ({nome})" por iteração sobre Debt vinculadas. Backward compat: workspace sem Debt persistida (Onda 2 não rodada) cai em fallback do `total_dividas` IRPF agregado.
- **Schema E5 aditivo, não breaking** (`data-engineer`) — bump version menor; consumer antigo (frontend pré-Onda 5) ignora campos desconhecidos.

## Testes (comandos exatos)

```bash
# Resolver puro
pytest tests/unit/pipeline/test_real_estate_valuation_resolver.py -v

# Adapter
pytest backend/tests/services/test_real_estate_valuation_adapter.py -v

# Calculator com contexto novo
pytest tests/test_e5_golden_execution_with_market_value.py -v

# Paridade legado (workspace sem context)
pytest tests/test_e5_golden_execution_fallback_irpf.py -v

# Boundary verde
python3 dev/check_pipeline_boundaries.py

# Goldens E5
pytest tests/test_e5_golden_execution.py -q

# Suítes completas
pytest tests -q
pytest backend/tests -q
pre-commit run --all-files
```

## Riscos

- **R1** — Goldens E5 quebram em massa pós-Onda 3 quando workspace dogfood já migrado tem Debt + market_value declarados. **Mitigação:** rodar Onda 2 `--apply` em `5@5.com` ANTES desta onda; goldens atualizam refletindo realidade do dogfood. PR sequencial: backfill (Onda 2 PR-B) → calculator (Onda 3 PR-C). Cutover por workspace via feature flag se goldens crítico.
- **R2** — Adapter carrega context vazio em workspace sem Debt nem market_value → calculator deve aceitar `valuation_context=None` (retrocompat). Test paridade obrigatório.
- **R3** — `percentual_atribuicao_imovel` em SUM com GROUP BY: cálculo é `SUM(saldo_devedor_cents * percentual_atribuicao_imovel / 100)`. Default 100% quando NULL. Aritmética inteira pode truncar; usar Decimal no aggregate ou pre-multiplicar em Python.
- **R4** — Warning `DebtVsIrpfDeclaracaoConflict` emitido em workspaces existentes pode poluir relatório. **Mitigação:** warning é tipado mas só renderiza no card S4 (Onda 5) com badge "atenção"; não bloqueia compute.
- **R5** — Mudança de KPI (patrimônio bruto + IF) visível pós-deploy. **Mitigação:** banner explicativo no relatório pós-cutover; telemetria `mathoms.real_estate.kpi_delta_pre_post_cutover` mede `Δ` por workspace na primeira semana.

## Ligações

- Plano canônico: [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 3
- ADR canônica: [[ADR-227]] §D3 + §D4 + §D5
- Sprint MOC: [[MOC-sprint-a15]]
- Onda 1 (pré-req): [a15-fu3-onda1-schema](a15-fu3-onda1-schema.md)
- Onda 2 (pré-req idealmente rodada antes): [a15-fu3-onda2-backfill](a15-fu3-onda2-backfill.md)
- Onda 4 (próximo): [a15-fu3-onda4-api](a15-fu3-onda4-api.md) — API consome adapter
- ADRs relacionados: [[ADR-097]] (ISP + warning tipado), [[ADR-111]] (stateless), [[ADR-142]] (investivel_efetivo invariante), [[ADR-216]] §D6 (trilho `valor_imovel_origem` que esta onda finalmente popula), [[ADR-223]] (anti-padrão fallback silencioso)
- Pattern reuso: [`real_estate_metrics.py`](../../../../pipeline/domain/services/real_estate_metrics.py) (consumidor downstream do cap rate líquido), [`patrimonio_resolvers.py`](../../../../pipeline/domain/services/patrimonio_resolvers.py) (pattern de resolver)
