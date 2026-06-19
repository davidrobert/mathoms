---
id: ADR-007
type: adr
title: "Fernet app-level para criptografia"
status: Decidido
phase: "F4→F7"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 007"]
tags:
  - area/auth
  - status/decidido
  - type/adr
size_lines: 11
---

# ADR-007 — Fernet app-level para criptografia

**Status:** Decidido (F4→F7)

**Decisão:** Fernet symmetric encryption em app-level. Consistente em vault de senhas (F2), CPFs (F3), API keys LLM (F4), e dados sensíveis adicionais (F7).

Alternativas descartadas: pgcrypto (DB-level, menos portável), AES manual (propenso a erros).

**Consequências críticas:** Ver [D60](#adr-060--fernet-dual-key-para-secret-rotation) sobre rotação. **Perder a FERNET_KEY = perder todos os dados encriptados.**
