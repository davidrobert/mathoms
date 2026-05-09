---
id: ADR-005
type: adr
title: "VPS Hetzner para produção"
status: Proposto
phase: "F7"
date: "2026-04-14"
relates_to:
  - "[[ADR-058]]"
  - "[[ADR-108]]"
  - "[[ADR-184]]"
supersedes: []
superseded_by: []
aliases: ["ADR 005"]
tags:
  - area/ops
  - status/proposto
  - type/adr
size_lines: 17
---

# ADR-005 — VPS Hetzner para produção

**Status:** Proposto (F7) • **Data:** 2026-04-14 • **Revisado:** 2026-05-09

> **Status atual (2026-05-09):** sugestão forte, ainda não provisionada e
> sob revisão. Originalmente registrada como `Decidido` em F7, mas como o
> hosting nunca foi provisionado e nenhum backend Mathoms está em produção,
> o status volta a `Proposto` para refletir a realidade. A decisão definitiva
> de hosting de backend será fixada em ADR futura quando o primeiro backend
> for promovido a produção (gatilho: backend Python `api.mathoms.ai` ir ao
> ar **ou** mailto: começar a derrubar conversão da landing — ver
> [[ADR-184]] §"Decisão futura"). Hetzner CX32 + Docker Compose continua
> como melhor opção sob avaliação, mas alternativas (Cloud Run, Fly.io,
> Railway) podem ser reabertas no momento da decisão.

**Contexto:** Onde hospedar em produção? VPS, Railway, Fly.io, AWS?

**Sugestão atual:** Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose.

**Consequências (se confirmada):**
- ✅ Custo baixo (~$10/mo total incluindo domínio)
- ✅ Controle total do stack
- ✅ Upgradeable para Railway/Fly.io se virar SaaS
- ⚠️ Nós gerenciamos OS updates, security patches

Ver [[ADR-058]] para sizing rationale e [[ADR-108]] §5 para topology DNS
proposta.
