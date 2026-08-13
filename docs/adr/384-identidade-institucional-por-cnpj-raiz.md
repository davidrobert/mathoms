---
id: ADR-384
type: adr
title: "Identidade institucional resolve por CNPJ-raiz para o code do catálogo — nome livre vira fallback"
status: Decidido
phase: A40.l40
date: "2026-08-12"
relates_to:
  - "[[ADR-137]]"
  - "[[ADR-238]]"
  - "[[ADR-081]]"
  - "[[ADR-246]]"
  - "[[ADR-255]]"
  - "[[ADR-382]]"
supersedes: []
superseded_by: []
aliases: ["ADR 384", "cnpj_raiz", "identidade institucional"]
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/pipeline
  - area/db
---

# ADR-384 — Identidade institucional por CNPJ-raiz

## Contexto

O matcher informe↔extrato (`_banco_match`) procura o token do banco na
**descrição da conta** — "Conta Corrente - Ag 9652 Conta 0004397-8" não
contém "itau" e nunca casa, embora cada entry carregue `cnpj_emissor`. No
dogfood, **0 de 6** entries casam. É a quarta ocorrência da classe
"identidade por nome livre quebra" ([[ADR-246]] imóvel em comunhão;
[[ADR-255]] sufixo PIX; membro por CPF). O `institution_catalog` não tem
CNPJ; a denylist deletada pela [[ADR-376]] quebrou pelo mesmo mecanismo
("btg pactual" ≠ `btgpactual`).

Isto é problema de **resolução** (N representações → 1 código canônico),
não de invariante de valor imutável (o enquadramento `codigo_rfb` não se
aplica: o valor no catálogo pode estar errado e precisa de correção).

## Decisão

1. **Chave canônica continua `institution_catalog.code`** (normalizado:
   lowercase ASCII sem espaço — é o que mata "btg pactual"). Conta ≠
   instituição: matcher de conta nunca compara token de banco com descrição
   de conta.
2. **CNPJ-raiz como resolvedor de maior precedência.** Coluna
   `cnpj_raiz String(8) NULL` no `institution_catalog` + index
   **não-único** + CHECK `^\d{8}$`. Raiz de 8 dígitos, não CNPJ completo:
   banco tem N estabelecimentos e um match exato de 14 dígitos falha
   estreito e silencioso na maioria dos informes (veto `data-engineer`).
   Colisão de raiz (holding × banco coexistem no catálogo) resolve por
   `category` no matcher, não por constraint.
3. **Cascata de resolução** (padrão [[ADR-081]] aplicado a matching
   determinístico): `cnpj_raiz` → token de nome (comportamento atual,
   vira fallback) → `needs_review`. Substituição total do token seria
   regressão para entries sem `cnpj_emissor`.
4. **Duas migrations** (padrão `adr238informes1`): DDL via
   `batch_alter_table(copy_from=...)` + seed de dados idempotente por
   `code`. Correção de valor de CNPJ é sempre migration nomeada com motivo
   — nunca upgrade in-place nem endpoint admin.
5. **Propagação a `pipeline/`** via `InstitutionEntry.cnpj_raiz` +
   `WorkspaceContext.institution_catalog_provider` (Protocol no consumer) —
   **não** via `StageConfig.institutions` (a via `_institutions_override`
   emite só `banco_canonical` e é exatamente a que já falhou). O mapa
   `{raiz: code}` entra em `apply_informe_override` como parâmetro tipado
   ([[ADR-089]]/[[ADR-097]] D2).
6. **Cache do resolver versionado** (`institution_catalog:global:v2`) +
   `invalidate_catalog()` com caller real de deploy — sem isso o matcher
   nasce inerte por até 30 dias (TTL do payload antigo, que não conhece a
   coluna nova). Falha aberta para o DB, nunca mapa vazio silencioso.
7. **Fora de escopo:** agência/conta estruturadas (não existem em
   `e3_reconciled` nem em `saldoProduto`, que é `additionalProperties:
   false`) — exigem lane de extração + `prompt-engineer`. Um matcher com
   pernas sempre-`None` é o matcher de uma perna com mais código.

## Consequências

- Lane A40.l40. Aceite: as três representações que quebram hoje
  (`"btg pactual"`, `"btgpactual"`, `"Conta Corrente - Ag 9652..." +
  cnpj_emissor`) resolvem para o mesmo code; no dogfood, Itaú CC e Wise BRL
  passam a casar (hoje 0/6).
- Gate de consistência: todo `code` com `category ∈ {bank, broker,
  exchange}` tem `cnpj_raiz`, verificado **sobre as migrations** (comparar
  DB de teste com o model é auto-referente).
- Migrations verdes em SQLite online e `--sql` offline; teste com
  `pytestmark = pytest.mark.migration`; CHECK exercitado com valor inválido.
- Destrava a visão pareada informe↔extrato ([[ADR-382]] §7) numa lane
  futura.
