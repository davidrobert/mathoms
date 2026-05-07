---
id: ADR-003
type: adr
title: "JWT custom para auth"
status: Decidido
phase: "F1"
date: "2026-04-13"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 003"]
tags:
  - area/auth
  - status/decidido
  - type/adr
size_lines: 15
---

# ADR-003 — JWT custom para auth

**Status:** Decidido (F1) • **Data:** 2026-04-13

**Contexto:** Auth provider? Custom JWT, Auth.js, Clerk, Auth0?

**Decisão:** Custom JWT (`python-jose` + `bcrypt`).

**Consequências:**
- ✅ Sem vendor lock-in
- ✅ Zero custo
- ⚠️ Nós somos responsáveis por segurança (hashing, rotation)
- Nota: bcrypt 4.x direto, sem passlib (passlib quebra com bcrypt 4.x API)
