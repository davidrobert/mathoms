---
id: MOC-sprint-a7
type: moc
title: Sprint A7 — Config DB Cutover
aliases: ["A7", "Sprint A7"]
---

# Sprint A7 — Config DB Cutover (CLI legacy removal)

> **Status:** done — todas as 7 lanes mergeadas em `main` em 2026-04-27 (mesmo dia).

## Resumo

Migração do `config/*` (5 arquivos JSON + decisions.md + 4 docs metodológicos) para DB multi-tenant + tabelas globais versionadas, com remoção das bridges (`materialize_config`, `FileConfigStore`) e deleção dos arquivos legados. Produto roda 100% DB-first via `DBConfigStore` ao final da sprint.

**ADRs canônicas:** [ADR-134](../../DECISIONS.md#adr-134) (`ConfigStore` protocolo), [ADR-135](../../DECISIONS.md#adr-135) (versionamento temporal de séries fiscais e câmbio), [ADR-136](../../DECISIONS.md#adr-136) (`Decision` aggregate event-sourced), [ADR-137](../../DECISIONS.md#adr-137) (catalog/override resolver), [ADR-138](../../DECISIONS.md#adr-138) (protocolo de supervisão CTO), ADR-143/145/146/147 (rules-as-code A7.6).

**Plano canônico (arquivado):** [docs/archive/CONFIG_CUTOVER_PLAN-2026-04-27.md](../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md) — 11 seções, 7 lanes, supervisão CTO.

**Princípios não-negociáveis:** (P1) produto continua funcionando entre ondas; (P2) `pipeline/**` não importa SQLAlchemy/FastAPI; (P3) stateless rigoroso; (P4) money nunca é float; (P5) ADR antes de código; (P6) bridges com prazo de remoção; (P7) reversível via revert.

**Resultado:** 5 arquivos JSON deletados + 4 docs metodológicos saídos em A7.4/A7.6 + decisions.md em A7.2a. `config/report_layout.yaml` permanece como source-of-truth do codegen (débito A8). Próxima sprint: A8 (continuação multi-tenant para entidades cliente-específicas).

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes/). Tracks operacionais em [`tracks/`](tracks/).

## Waves

Mapa de dependências em [waves.md](waves.md) — 4 ondas: Onda 1 (A7.0 fundação) → Onda 2 (cutover paralelizável) → Onda 2.5 (rules-as-code) → Onda 3 (catalog/override) → Onda 4 (cleanup final).

## Fontes canônicas

- [docs/archive/CONFIG_CUTOVER_PLAN-2026-04-27.md](../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md) — plano canônico arquivado.
- [docs/reference/STATELESS_AUDIT.md](../../STATELESS_AUDIT.md) — registro dos globals permitidos (ADR-111).
- [docs/reference/ARCHITECTURE.md §4.1 Domain glossary](../../ARCHITECTURE.md) — índice de regras de domínio (rules-as-code).
