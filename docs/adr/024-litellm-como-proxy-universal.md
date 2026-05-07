---
id: ADR-024
type: adr
title: "LiteLLM como proxy universal"
status: Decidido
phase: "F4"
date: "1970-01-01"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 024"]
tags:
  - area/llm
  - status/decidido
  - type/adr
size_lines: 12
---

# ADR-024 — LiteLLM como proxy universal

**Status:** Decidido (F4)

**Decisão:** LiteLLM como camada de abstração para 100+ LLM providers.

**Consequências:**
- ✅ Anthropic, OpenAI, Ollama local, etc. via mesma interface
- ✅ User escolhe provedor (BYOK)
- ⚠️ Dependência adicional
