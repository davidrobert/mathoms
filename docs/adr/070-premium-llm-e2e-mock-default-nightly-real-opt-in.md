---
id: ADR-070
type: adr
title: "Premium LLM E2E: mock default + nightly real opt-in"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 070"]
tags:
  - area/llm
  - area/pipeline
  - area/testing
  - status/decidido
  - type/adr
size_lines: 32
---

# ADR-070 — Premium LLM E2E: mock default + nightly real opt-in

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.11

> **Nota de estado (2026-07-04):** `nightly-e2e-real-llm.yml` nunca foi
> criado. O mock-default em PR foi implementado; a validação real-LLM
> vive hoje em `llm-cross-provider-smoke.yml` + `planner-golden-monthly.yml`
> (`.github/workflows/`).

**Contexto:** Pipeline premium tier chama LiteLLM → Anthropic/OpenAI/etc. Em CI, duas estratégias:

1. **Mock LiteLLM:** interceptar chamadas, retornar fixtures pré-computadas. Custo zero, reproduzível.
2. **Real API calls:** anotar chave do provedor em GH secret, chamar API real. Valida comportamento real do provider (rate limit, token counting, etc.).

**Alternativas consideradas:**
- (A) Só real em TODO PR — custo imprevisível ($$$), flaky com rate limits do provider, chave em CI de PRs de contributors externos = risco
- (B) Só mock — perde validação de mudanças no provider API (breaking changes do Anthropic SDK, por exemplo)
- (C) **[escolhida]** Mock default em PR + nightly real opt-in (workflow schedulado)

**Decisão:**
1. **PR checks:** `frontend-e2e` job usa LiteLLM mockado (adapter em `backend/tests/fixtures/llm_mock.py` retorna outputs válidos por stage). Custo $0.
2. **Nightly:** GH Actions scheduled workflow `nightly-e2e-real-llm.yml` (a criar em 6.5F.11 implementação) roda 6.5C.0 com `PW_REAL_LLM=1` + `ANTHROPIC_API_KEY` em secret. Falha → issue automática.
3. **Custo monitorado:** dashboard interno lista token spending do nightly; alerta se >$10/mês.

**Consequências:**
- ✅ PR checks são rápidos + gratuitos
- ✅ Validação de integração real provider é mantida (nightly)
- ✅ Breaking changes do Anthropic SDK pegos em <24h
- ⚠️ Se nightly falha por rate limit do provider, issue gerada pode ser ruído — mitigado por retry + detecção
- ❌ Sem validação de "LLM output shape" em cada PR — aceito (cobertura de validators em pipeline/llm/validators.py)

**Implementação:**
- `backend/tests/fixtures/llm_mock.py`: fixtures por stage (E1, E1.5, E2-llm, E7-review) com JSON válido.
- `.github/workflows/nightly-e2e-real-llm.yml` — scheduled (cron: `0 3 * * *`) rodando só `@critical` em chromium, com `PW_REAL_LLM=1` + ANTHROPIC_API_KEY.
- ADR referencia decisão D11 (pendente): provider pode mudar no futuro, ADR ajusta.
