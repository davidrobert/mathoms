---
id: ADR-005
type: adr
title: "VPS Hetzner para produção"
status: Decidido
phase: "F7"
date: "2026-04-14"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 005"]
tags:
  - area/ops
  - status/decidido
  - type/adr
size_lines: 17
---

# ADR-005 — VPS Hetzner para produção

**Status:** Decidido (F7) • **Data:** 2026-04-14

**Contexto:** Onde hospedar em produção? VPS, Railway, Fly.io, AWS?

**Decisão:** Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose.

**Consequências:**
- ✅ Custo baixo (~$10/mo total incluindo domínio)
- ✅ Controle total do stack
- ✅ Upgradeable para Railway/Fly.io se virar SaaS
- ⚠️ Nós gerenciamos OS updates, security patches

Ver [D58](#adr-058--vps-cx32-para-sizing) para sizing rationale.
