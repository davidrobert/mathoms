---
id: ADR-025
type: adr
title: "BYOK (Bring Your Own Key)"
status: Decidido
phase: "F4"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 025"]
tags:
  - area/auth
  - status/decidido
  - type/adr
size_lines: 13
---

# ADR-025 — BYOK (Bring Your Own Key)

**Status:** Decidido (F4) — **Estratégica**

**Decisão:** User fornece sua própria API key. Zero custo para plataforma.

**Consequências:**
- ✅ Modelo de negócio viável sem billing
- ✅ User controla custos e provedor
- ❌ Onboarding fricciona (user precisa criar conta no provedor)
- ❌ Plataforma não lucra direto com uso do LLM
