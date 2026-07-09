---
id: A11.w3
type: lane
title: "Auth + LLM ops + Email (5 tasks)"
sprint: A11
status: shipped
aliases: ["A11.W3"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a11
  - status/shipped
---


# A11.w3 — Auth + LLM ops + Email (5 tasks)

> Migrada de tabela em `## Sprint A11` do BACKLOG (F4.A.followup, ADR-182).

## Contexto da tabela original

- **Onda:** 3 (12d)
- **Depende de:** W2 ✅ (2026-05-20)
- **Plano:** [PLAN §W3](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#wave-3--auth--llm-ops--email-sprint-2-12-dias-dev)

## Status

**4/5 done · 1 owner-gated** (reconciliado 2026-07-08 — fonte por task:
[PLAN Index](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#index)):

- W3-T01 (LLM budget hard-stop + LLMCallLog) ✅ 2026-07-02 ([#718](https://github.com/davidrobert/mathoms/pull/718)) — [[ADR-173]] `Decidido`
- W3-T02 (Email Resend + verify + password reset) ☐ **owner-gated** — aprovação Resend EU + signup/API key + SPF/DKIM/DMARC nos DNS; único item da wave sem código em main
- W3-T03 (JWT 15min + refresh 7d + family revocation) ✅ 2026-06-09 ([#584](https://github.com/davidrobert/mathoms/pull/584)) — [[ADR-170]] `Decidido`
- W3-T04 (Fernet rotation MultiFernet) ✅ 2026-07-02 ([#718](https://github.com/davidrobert/mathoms/pull/718)) — [[ADR-171]] `Decidido`
- W3-T05 (prompt injection defense) ✅ shipped via A21.l6 — [[ADR-175]] `Decidido (A21.l5)`

## Fechamento (closure A11, 2026-07-08)

Lane fechada com a sprint (`done`). O único item restante — W3-T02
(Email Resend) — foi **transferido** para [[PLAN-launch-trust]] §F2
(gate G1 de [[ADR-228]], emenda 2026-07-08); deixou de ser escopo
desta lane.
