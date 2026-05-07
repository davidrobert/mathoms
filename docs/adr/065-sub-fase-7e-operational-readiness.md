---
id: ADR-065
type: adr
title: "Sub-fase 7E Operational Readiness"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 065"]
tags:
  - type/adr
  - status/decidido
size_lines: 37
---

# ADR-065 — Sub-fase 7E Operational Readiness

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** A versão original da F7 cobria deploy (7A), security/LGPD (7B), CI/observabilidade (7C) e quality gate (7D). Faltam concerns operacionais que só aparecem **depois** que o produto está rodando com usuários:

1. **Pipeline runs órfãs:** Celery worker morre → run fica `"running"` para sempre → user vê spinner eterno
2. **Disaster recovery não testado:** 7A.10 menciona backup mas sem restore drill, RPO/RTO não declarados, backup mora no mesmo DC do Hetzner (incêndio = perda total)
3. **FERNET_KEY recovery:** ADR-060 menciona dual-key mas sem procedure testado
4. **Observabilidade só captura erros:** Sentry vê crashes; nada vê "0 reports nas últimas 24h" = produto silenciosamente quebrado
5. **Comunicação durante incidente:** sem template, sem status page público, sem support runbook
6. **LLM cost runaway:** BYOK não isenta de monitoring; user pode estourar próprio budget sem perceber, e nós não sabemos
7. **API key inválida** crasha mid-pipeline com 500 em vez de validar antes

**Alternativas consideradas:**
- (A) Distribuir essas tasks entre 7A/7B/7C/7D — risco de virar P2 e ser cortado
- (B) Empurrar para pós-launch — significa primeiro incidente sem ferramentas para responder
- (C) **[escolhida]** Sub-fase dedicada 7E, ~2 semanas, executada após 7D mas **antes** do dogfood

**Decisão:** Criar sub-fase **7E — Operational Readiness** com 14 tasks organizadas em 5 grupos:
- **7E.A Pipeline operacional:** stuck-run detector
- **7E.B Disaster recovery:** restore drill, RPO/RTO, off-site backup, FERNET recovery
- **7E.C Observabilidade de negócio:** status page, business metrics, SLOs/SLAs
- **7E.D Comunicação de incidentes:** templates de comms, support runbook
- **7E.E LLM cost runaway protection:** cost cap, dashboard, API key validation, fallback model

**Consequências:**
- ✅ Beta começa com ferramentas para responder ao primeiro incidente
- ✅ Off-site backup elimina risco de perda total em falha de DC
- ✅ Pipeline runs órfãs viram tickets, não experiências silenciosamente quebradas
- ✅ Cost cap protege user de queimar próprio budget BYOK
- ✅ Status page + comms templates = comunicação profissional desde dia 1
- ⚠️ Prazo de F7 +2 semanas (6-8 → 8-10 semanas, sem contar dogfood)
- ⚠️ Off-site backup adiciona custo (~$1-3/mo S3 BR ou Backblaze B2)
- ❌ MFA fica para F8 (decisão deliberada — ver ADR-066)
