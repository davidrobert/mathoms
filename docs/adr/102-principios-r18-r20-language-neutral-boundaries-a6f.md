---
id: ADR-102
type: adr
title: "Princípios R18-R20: language-neutral boundaries (A6f)"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 102"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - phase/a6f
  - status/decidido
  - type/adr
size_lines: 56
---

# ADR-102 — Princípios R18-R20: language-neutral boundaries (A6f)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6f

**Contexto:** Discussão estratégica (2026-04-19) sobre cenário hipotético
plausível: backend eventualmente migrado para Go, mantendo Python em
parsers (`scripts/e2/banks/`), LLM (`pipeline/llm/`) e domain services.

Hoje o backend Python importa funções do pipeline diretamente
(`from scripts.e3_reconcile import main_with_store`) — incompatível com
processos de linguagens diferentes. A fronteira entre backend e pipeline
precisa virar **contrato de rede ou mensageria**.

Alternativas avaliadas (3 categorias):
- **Categoria 1 — "no regret"** (valor independente de Go): pipeline-service
  HTTP, OpenAPI exaustivo, structured logs + OTel, DB schema review, Fernet
  → AES-GCM.
- **Categoria 2 — Go-specific com valor marginal**: contract tests, stateless
  rigoroso, broker neutro (substituir Celery), gRPC.
- **Categoria 3 — not yet**: port de domain services para Go, microserviços.

**Decisão:** Adicionar A6f com Categoria 1 + Categoria 2.4 (stateless
rigoroso). Princípios **R18–R20**:

- **R18 (Wire formats explícitos)** — zero pickle cross-process; JSON Schema/
  OpenAPI/Protobuf versionados em toda fronteira.
- **R19 (Stateless-ready)** — zero estado in-memory que impeça múltiplos
  workers concorrentes.
- **R20 (Language-neutral data)** — DB schema, JSON artifacts e message
  envelopes sem features Python-only.

**NÃO adotado nesta rodada**:
- Broker neutro (Celery mantido) — risco alto, ganho condicionado à Go real.
- gRPC — HTTP JSON + OpenAPI é suficiente para monolito→serviços separados.
- Port de domain services para Go — só durante migração real, não antes.

6 sub-fases (A6f.1 Pipeline-service → A6f.2 OpenAPI → A6f.3 OTel → A6f.4 DB
schema → A6f.5 Auth → A6f.6 Stateless). Estimativa: 6-8 sessões grandes.

**Consequências:**
- ✅ Todas as entregas têm valor independente (escala pipeline, debug real,
  best-practice cripto, horizontal scale).
- ✅ Migração Go futura sem retrabalho grande — fronteiras HTTP + OpenAPI
  prontas.
- ⚠️ Custo operacional em prod: +1 container (`pipeline-service`) +
  OTel collector.
- ⚠️ Fernet → AES-GCM exige data migration (mitigado: pouco PII hoje
  encriptado via Fernet).
- ❌ Adiciona latência HTTP ao pipeline (1 hop extra).

**Relação com A6a-e**: independente. Recomendado depois de A6b (cutover DB)
— pipeline-service precisa de DB como fonte de verdade.

**Artefatos:** [BACKLOG §A6f](../BACKLOG.md#a6f--language-neutral-boundaries-adr-102-r18-r20).
