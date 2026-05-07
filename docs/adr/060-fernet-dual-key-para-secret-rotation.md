---
id: ADR-060
type: adr
title: "Fernet dual-key para secret rotation"
status: Decidido
phase: "F7"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 060"]
tags:
  - area/auth
  - area/security
  - status/decidido
  - type/adr
size_lines: 15
---

# ADR-060 — Fernet dual-key para secret rotation

**Status:** Decidido (F7)

**Decisão:** Dual-key rotation:
1. Gerar nova key
2. Configurar `FERNET_KEYS=new,old` (Fernet aceita lista)
3. Re-encrypt dados em background (Celery task)
4. Remover key antiga

Documentado no Runbook.

**⚠️ Nota de operação:** `FERNET_KEY` precisa estar persistida em `.env` (nunca gerar nova sem rotação). Ver [SETUP.md](SETUP.md).
