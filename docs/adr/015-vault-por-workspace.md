---
id: ADR-015
type: adr
title: "Vault por workspace"
status: Decidido
phase: "F2"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 015"]
tags:
  - area/auth
  - area/docs
  - area/multitenancy
  - status/decidido
  - type/adr
size_lines: 7
---

# ADR-015 — Vault por workspace

**Status:** Decidido (F2)

**Decisão:** Senhas de PDF são armazenadas em um vault por workspace, encriptadas com Fernet. Tentadas automaticamente no upload.
