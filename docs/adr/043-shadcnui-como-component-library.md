---
id: ADR-043
type: adr
title: "shadcn/ui como component library"
status: Decidido
phase: "F4.5"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 043"]
tags:
  - area/frontend
  - status/decidido
  - type/adr
size_lines: 34
amended_at: ["2026-08-06"]
---

# ADR-043 — shadcn/ui como component library

**Status:** Decidido (F4.5)

> **Correção de stack (2026-08-06):** os primitivos hoje vêm de
> `@base-ui/react`, não do Radix. A escolha de shadcn + Tailwind permanece; o
> que mudou foi a biblioteca de primitivos por baixo dela. Ver §Emenda.

**Decisão:** shadcn/ui (Radix primitives + Tailwind).

Alternativas descartadas: MUI (opinião forte), Ant Design (visual Chinese-first), custom (reinventar a roda).

## Emenda 2026-08-06 — a stack real é `@base-ui/react`

O texto acima descreve uma stack que o repo não usa mais. `frontend/package.json`
depende de `@base-ui/react`, e os ~23 primitivos em `frontend/src/components/ui/`
importam dele; [ARCHITECTURE.md §stack](../reference/ARCHITECTURE.md) já registra
"base-ui/react + shadcn". A migração nunca teve ADR própria — esta emenda
corrige o registro, não reconstrói o rationale de uma decisão que ninguém
documentou.

**Por que isso não é detalhe de arqueologia.** Os wrappers shadcn foram
portados assumindo o comportamento do Radix, e onde o base-ui diverge no
*default* — não na assinatura de tipo — o resultado é bug silencioso: compila,
monta, e só a tela mostra o erro. Caso concreto: `Select.Value` resolve o
rótulo sozinho no Radix, mas no base-ui só quando o `Root` recebe `items`. Como
`Select` era alias direto do `Root`, nenhum call-site passava `items` e ~15
selects imprimiam o `value` cru (uuid, slug) em vez do rótulo, por meses, sem
teste vermelho. Corrigido no PR #1238.

**Consequência operacional:** ao portar ou revisar wrapper shadcn deste repo,
não trate o typecheck como prova — leia o `.d.ts` do primitivo base-ui e o
código de resolução para achar props que o Radix inferia e o base-ui exige.
