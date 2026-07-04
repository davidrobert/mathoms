---
id: ADR-062
type: adr
title: "Frontend testing em fase dedicada (6.5)"
status: Decidido
date: "2026-04-14"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-063]]", "[[ADR-064]]"]
aliases: ["ADR 062"]
tags:
  - area/ops
  - area/security
  - area/testing
  - status/decidido
  - type/adr
size_lines: 19
---

# ADR-062 — Frontend testing em fase dedicada (6.5)

**Status:** Decidido • **Data:** 2026-04-14

> **Nota (2026-04-15):** parcialmente superseded por
> [ADR-064](#adr-064--backend-hardening-em-sub-fase-65e) — escopo
> estendido para incluir backend hardening como sub-fase 6.5E.

**Contexto:** Versão anterior do plano tinha setup de testes frontend dentro de F7 misturado com Docker, LGPD, CI/CD, dogfood.

**Decisão:** Fase 6.5 dedicada (2 semanas). Vitest + RTL + MSW + Playwright.

**Rationale:**
- Testes ficavam no final do critical path do launch
- Pressão de "ship" empurrava testes para P2
- Bugs frontend descobertos em produção custam 10x mais
- Separar garante que testes são pré-requisito do deploy
