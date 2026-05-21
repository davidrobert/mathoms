---
id: CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO
type: changelog-entry
date: "2026-05-20"
sprint: A15
adrs:
  - "[[ADR-227]]"
  - "[[ADR-234]]"
tags:
  - type/changelog-entry
  - sprint/a15
  - area/backend
  - area/pipeline
  - area/frontend
  - area/methodology
summary: |
  feat: Sprint A15 — FU-3 imóvel financiado (ADR-227 Decidido). Cria agregado
  Debt persistido + property_market_value versionada, calculator usa líquido
  econômico no investivel_efetivo preservando bruto na tabela (D3), API REST
  CRUD + 7 endpoints, frontend cutover end-to-end (MarketValueInline, batch
  review, nudge S4, drill-down panel, staleness badge). Resolve 2 bugs
  silenciosos em produção: patrimônio bruto defasado e IF mal-calibrado.
---

# Sprint A15 — FU-3 imóvel financiado (ADR-227 Decidido)

Sprint dedicada (origem 2026-05-19) ao último follow-up out-of-scope do Sprint
A12 ([[ADR-215]] §Follow-ups). Resolveu 2 bugs silenciosos em produção:

1. **Patrimônio bruto defasado** — `_split_imoveis` usava `valor_brl` IRPF
   (custo histórico). Apto declarado R$ 800k em 2018, R$ 1,2M hoje → tabela
   mostrava 800k. Agora resolver cascade `valor_mercado || valor_irpf` reflete
   realidade quando o usuário declara.
2. **IF mal-calibrado** — `investivel_efetivo` usava `valor_irpf` no numerador
   quando `imoveis_no_if=true` e cat_2 era locado. Agora usa líquido
   econômico `max(0, valor_efetivo − saldo_devedor)` por imóvel gerador.

## O que entrou (6 PRs)

| PR | Onda | Conteúdo |
|---|---|---|
| [#371](https://github.com/davidrobert/mathoms/pull/371) | Bootstrap | ADR-234 (`paused` vocab) + flip A11/A12→paused, A15→current |
| [#372](https://github.com/davidrobert/mathoms/pull/372) | 1 — Schema | Migration Alembic + models `Debt`/`PropertyMarketValue` + repos + DTOs + 36 testes |
| [#373](https://github.com/davidrobert/mathoms/pull/373) | 2 — Backfill | `dev/backfill_debt_from_baseline.py` idempotente; 7 testes integration |
| [#374](https://github.com/davidrobert/mathoms/pull/374) | 3 — Calculator | Resolver puro + `RealEstateValuationContext` + adapter (2 SELECTs/workspace) + `DebtVsIrpfDeclaracaoConflict` warning |
| [#375](https://github.com/davidrobert/mathoms/pull/375) | 4 — API | 7 endpoints REST (CRUD Debt + Append-only PMV + supersede) + OpenAPI snapshot |
| [#376](https://github.com/davidrobert/mathoms/pull/376) | 5a — Frontend foundation | API clients + DebtForm/List + tela `/imoveis/financiamentos-review` |
| [#378](https://github.com/davidrobert/mathoms/pull/378) | 5b — Frontend inline | `MarketValueInline` em MembersTab + nudge S4 `RealEstateYieldCard` |
| 5c (este) | 5c — Frontend finish | `RealEstateBreakdownPanel` + `MarketValueStaleness` + E2E + flip ADR-227 + changelog |

## Decisões canônicas

- **`Debt` agregado persistido do zero** — não existia em DB; modela 6 tipos
  (financiamento_imobiliario, consignado, cdc, cartao_rotativo, rotativo,
  outro) desde V1. Schema evolution de enum é caro depois.
- **FK `Debt.property_id ON DELETE RESTRICT`** — órfão silencioso é bug
  invisível em fintech; UX explícita "desvincule antes" vence bug silencioso.
- **`property_market_value` append-only** — correção é nova row +
  `supersede()`; preserva auditoria.
- **Líquido econômico só em `investivel_efetivo`** — tabela cat_2 preserva
  bruto (invariante "categoria = ativo bruto, passivo = bucket separado"
  consistente com cat_1 e veículos). Drill-down expõe breakdown.
- **TTL sem fallback automático** — após 12m, badge visual de staleness;
  fonte nunca trocada automaticamente ([[ADR-223]] §Riscos anti-padrão).
- **Sem heurística de atribuição Debt→property** — falso-positivo garantido
  com >1 imóvel; usuário linka via UI batch review.

## Métricas pós-deploy (telemetria instrumentada)

- `mathoms.real_estate.valor_mercado.declarations_count` — incrementa em
  POST `/property-market-values`.
- `mathoms.real_estate.debt.link_to_property_rate` — % de Debt com
  `property_id NOT NULL`.
- `mathoms.real_estate.kpi_delta_pre_post_cutover` — `Δ` em patrimônio bruto
  + `investivel_efetivo` por workspace na primeira semana.

## Cutover operacional

1. Migration `adr227debt1` aplicada via deploy → tabelas existem.
2. Backfill por workspace via `dev/backfill_debt_from_baseline.py --apply`
   ([runbook §10](../../../reference/RUNBOOK.md#10-backfill-de-debt-adr-227-d6--sprint-a15-onda-2)).
3. Workspace dogfood (5@5.com) primeiro; produção 1 workspace por vez.
4. Frontend revela tela `/imoveis/financiamentos-review` para batch review
   de Debts migradas com `needs_review=true`.

## Referências

- ADR canônica: [[ADR-227]] (Decidido em A15)
- Plano: [PLAN-imovel-financiado](../../../archive/IMOVEL_FINANCIADO-2026-05-20.md)
  (arquivar após esta sprint)
- Sprint MOC: [[MOC-sprint-a15]]
- Origem do débito: [[ADR-215]] §Follow-ups
