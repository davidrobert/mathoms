---
id: MOC-sprint-a6
type: moc
title: Sprint A6 — Migração Infra+Domínio
aliases: ["A6", "Sprint A6"]
---

# Sprint A6 — Migração Infra+Domínio (plano transversal)

> **Status:** done — A6g 100% fechado em 2026-04-25; remanescente A6e.events-followup ⏸ aguarda janela F7.

## Resumo

Plano transversal que migrou infraestrutura (`ArtifactStore` DB-first, pipeline-as-service HTTP, structured logs + OTel, stateless rigoroso) e domínio (DDD/SOLID no backend API com 13 agregados, 60+ use cases, routers finos, domain events) entre 2026-04-19 e 2026-04-25. Inclui Code Style Sweep (A6g) com enforcement automatizado (Ruff, ESLint, AST tests, audit baseline decrescente).

**ADRs canônicas:** 097 (extract-then-refactor), 098 (Caminho B puro vs pragmático), 099, 100 (A6d commitment), 101 (R12-R17 backend DDD/SOLID), 102 (R18-R20 language-neutral), 103 (teste humano como gate), 109 (auth portability), 110 (structured logs + OTel), 111 (stateless rigoroso), 112 (pipeline-as-service), 113 (Go prep), 114 (enforcement code style), 115 (domain events), 118 (flip default `USE_DB_ARTIFACTS=true`), 119 (`LiveStep` contract), 120 (readers DB-first), 127 (E1 migrada para ArtifactStore), 128 (E7-review-llm migrada), 129 (descontinuação completa do renderer HTML server-side).

**Caminho crítico (serial):** A6a → A6b → A6-human (smoke ✅ 2026-04-24) → A6c → A6d → F7A → F7B → F7D+dogfood → GA.

**Testes ao fim da sprint:** 1461 pipeline + 1085 backend + 12 pipeline-service passing (zero regressão).

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes/) (1 arquivo por lane com frontmatter). Tracks operacionais em [`tracks/`](tracks/).

## Waves

Mapa de dependências em [waves.md](waves.md) — 4 ondas serializadas (estrutura → A6e/infra → F7 produção → dogfood/GA).

## Fontes canônicas

- [docs/reference/ARCHITECTURE.md §17](../../ARCHITECTURE.md) — arquitetura alvo pós-A6.
- [docs/reference/TESTING.md](../../TESTING.md) — critérios de aceite por fase.
- [docs/reference/runbooks/cutover.md](../../runbooks/cutover.md) — runbook de cutover.
- [docs/reference/SMOKE_TEST_HUMAN.md](../../SMOKE_TEST_HUMAN.md) — gate humano A6-human.
