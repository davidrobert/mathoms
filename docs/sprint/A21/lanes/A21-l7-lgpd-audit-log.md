---
id: A21.l7
type: lane
title: "LGPD Art.37 — audit log de acesso a dado sensível"
sprint: A21
plan: PLAN-launch-trust
status: shipped
priority: P0
branch_slug: a21-l7-lgpd-audit-log
depends_on: []
parallel_with:
  - "[[A21.l8]]"
adrs:
  - "[[ADR-275]]"
tags:
  - type/lane
  - sprint/a21
  - status/shipped
  - priority/p0
  - area/seguranca
---

# A21.l7 — LGPD Art.37 audit log de acesso a dado sensível

> **Plano:** [[PLAN-launch-trust]] §F2-G2 (lane OWNED — gap que nenhuma wave do PLATFORM_REVIEW cobre).
> **⚠️ ADR Proposto antes do PR** (modelo de dados + política de segurança).

## Contexto

Obrigação legal (LGPD Art.37): registrar **quem acessou** dado sensível
(CPF / financeiro) **de quem** e **quando**. Sem isto, o launch é não-conforme
para cliente brasileiro. Não está em nenhuma wave do PLATFORM_REVIEW.

## Escopo

- Modelo de dados de audit log (append-only) — acesso a CPF/valores/conteúdo
  financeiro por ator, workspace, recurso, timestamp.
- Hook no boundary de leitura de dado sensível (não logar o **valor**, só o
  **acesso** — respeitar regra anti-PII do repo).
- Retenção e consulta (quem/quando/o quê).

## Critério de aceite

- Audit log grava acesso a dado sensível, testado (A21-KR6, parte 1).
- Zero PII no próprio log (só metadados de acesso).

## Dependências

- **Sem deps** — pickup imediato. Paralela a l8.
- **ADR Proposto** antes do PR.
- Puro código/schema — **sem passo humano, sem deploy em prod**.
