---
id: ADR-103
type: adr
title: "Teste manual como gate antes de remoção do bridge (A6b.5 + A6-human)"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 103"]
tags:
  - type/adr
  - status/decidido
size_lines: 54
---

# ADR-103 — Teste manual como gate antes de remoção do bridge (A6b.5 + A6-human)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6b.5/A6-human

**Contexto:** A sequência original do plano era A6b (cutover DB validado
tecnicamente) → A6c (deletar bridge). Na auditoria de 2026-04-19 surgiram
2 pontos críticos:

1. **`USE_DB_ARTIFACTS=False` em produção** — `DBArtifactStore` nunca
   instanciado pelo backend; cutover DB é teórico, validação técnica de A6b
   não garante que **uso real** funciona.
2. **LLM stages escrevem direto em disco** (ADR-099 mitiga parcial, A6a
   resolve) — mesmo após A6a, só teste humano em workflow real valida.

Deletar bridge (A6c) sem teste humano é arriscado: se o pipeline quebrar
em cenário real (ex.: upload de 50 docs com LLM premium, pipeline
incremental), rollback do bridge removido exige revert.

**Decisão:** Adicionar 2 etapas obrigatórias entre A6b e A6c:

**A6b.5 — Preparação para teste humano**:
- `docker-compose.smoke.yml` + `Makefile` smoke-up/seed/reset/logs
- Seed de dados (2 workspaces, 2 users) + fixtures comitadas em
  `tests/fixtures/smoke_inbox/` (extratos, faturas, IRPFs, ambíguos,
  duplicatas, PDF com senha, life plan)
- `docs/reference/SMOKE_TEST_HUMAN.md` exaustivo (setup + matriz features + cenários
  parametrizados + template bug report + troubleshooting)
- Observabilidade mínima (health check, admin console, logs agregados,
  indicador visual "Artifact store: DB/Disk")
- Modo free-tier funcional (sem LLM key → `skipped: true` com banners)

**A6-human — Teste manual pelo David**:
- Checklist de ~70 verificações cobrindo auth, multi-tenancy, documentos,
  pipeline full+incremental, cada stage E0-E7, relatório, goals, cutover
  DB, edge cases.
- Template de bug report inline no runbook.
- Decisão **explícita** de aprovar A6c ou bloquear até correções.

**A6c (deletar bridge) depende de aprovação humana documentada.**

**Consequências:**
- ✅ Remoção do bridge só acontece com confiança real do sistema em uso.
- ✅ Runbook serve como onboarding para novos devs + operação contínua.
- ✅ Fixtures comitadas permitem reprodução de bugs reportados pelo tester.
- ⚠️ Adiciona 1-2 sessões de preparação + janela de teste manual (pode ser
  dias até semanas).
- ⚠️ Custo operacional: manter `docker-compose.smoke.yml` funcional ao longo
  do projeto (CI pode validar).
- ❌ Aceita que A6c (remover bridge) é bloqueado se teste humano revelar
  regressões.

**Artefatos:** [BACKLOG §A6b.5](BACKLOG.md#a6b5--preparação-para-teste-humano-adr-103) + [§A6-human](BACKLOG.md#a6-human--teste-manual-end-to-end-david).
