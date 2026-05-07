---
id: ADR-066
type: adr
title: "Auth flows completos e prompt injection em 7B (bloqueadores de beta)"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 066"]
tags:
  - type/adr
  - status/decidido
size_lines: 38
---

# ADR-066 — Auth flows completos e prompt injection em 7B (bloqueadores de beta)

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** F7B original cobria session security (JWT + refresh), audit log e LGPD (termos, exclusão, portabilidade). Faltam fluxos de auth básicos que **bloqueiam GA**:

1. **Email verification** ausente — qualquer um pode registrar `presidente@empresa.com` e receber relatórios financeiros (impersonation)
2. **Password reset** ausente — esqueci minha senha = produto inutilizável, sem recovery
3. **Brute-force lockout** ausente — rate limit de 5/min ainda permite 7200 tentativas/dia
4. **MFA** não está nem no roadmap explícito — fintech bare minimum para GA
5. **Prompt injection no E2-llm/E1.5:** PDFs vêm de usuários; um PDF malicioso pode conter texto invisível instruindo o LLM a vazar dados via campo `notes` ou similar — sem defesa hoje
6. **Terms versioning:** quando termos mudam, LGPD requer consentimento informado; hoje não há mecanismo

**Alternativas consideradas:**
- (A) Empurrar email verify/password reset para F8 — significa que beta fechado roda com auth quebrado
- (B) Implementar tudo só quando necessário — impossível abrir GA sem isso
- (C) **[escolhida]** Adicionar 8 tasks novas em 7B (7B.11-7B.18) cobrindo auth completo, prompt injection e terms versioning. MFA stub via ADR (decidir timing F7 vs F8 separadamente — task 7B.14)

**Decisão:** Expandir F7B com:
- 7B.11 Email verification (P0)
- 7B.12 Password reset completo (P0)
- 7B.13 Brute-force lockout escalonado (P0)
- 7B.14 MFA decision stub + campo `mfa_enabled` migration-ready (P1, decisão de timing em ADR futura)
- 7B.15 Prompt injection defense (P0)
- 7B.16 Terms versioning + re-aceitação (P1)
- 7B.17 Soft-delete period 30d (P1)
- 7B.18 DSAR SLA workflow (P1)

**Consequências:**
- ✅ Beta fechado pode rodar com fluxos de auth reais
- ✅ Caminho claro para GA (não há show-stopper de auth descoberto na hora)
- ✅ Prompt injection defense em produto LLM-augmented = não-negociável para fintech
- ✅ LGPD coberto além do mínimo (terms versioning + DSAR + soft-delete)
- ⚠️ Prazo de F7B +1-2 semanas
- ⚠️ Email transactional precisa ser configurado (provider TBD: Resend? Mailgun? AWS SES? Decisão pendente em D11 a criar)
- ❌ MFA fica como decisão pendente — provavelmente F8, mas migration-safe via stub
