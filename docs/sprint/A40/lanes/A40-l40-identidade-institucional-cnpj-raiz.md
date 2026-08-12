---
id: A40.l40
type: lane
title: "Identidade institucional por CNPJ-raiz: o matcher informe↔extrato casa 0 de 6 por nome livre"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l40-identidade-institucional-cnpj-raiz
adrs:
  - "[[ADR-137]]"
  - "[[ADR-238]]"
  - "[[ADR-384]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
  - area/db
---

# A40.l40 — `identidade-institucional-cnpj-raiz`

> **Aberta em 2026-08-11.** Co-design `data-engineer` (vetos estruturantes) +
> `senior-cto` (enquadramento: **resolução** de identidade, não invariante de
> valor). Quarta ocorrência da classe "identidade por nome livre quebra"
> ([[ADR-246]] imóvel em comunhão; [[ADR-255]] sufixo PIX; membro por CPF).

## Problema

`_banco_match` ([informe_extrato_override.py:121-127](../../../../pipeline/domain/services/informe_extrato_override.py))
procura o token do banco na **descrição da conta** — "Conta Corrente - Ag 9652
Conta 0004397-8" não contém "itau" e nunca casa, embora cada entry de informe
carregue `cnpj_emissor`. No dogfood, 0 de 6 entries casam. O catálogo
(`institution_catalog`) não tem CNPJ.

## Entregável

1. **ADR Proposto** (identidade institucional): chave canônica =
   `institution_catalog.code`; CNPJ-**raiz** (8 dígitos) como resolvedor de
   maior precedência; cascata `cnpj_raiz → token de nome → needs_review`
   (nunca substituição total); conta ≠ instituição.
2. Coluna `cnpj_raiz String(8) NULL` + index não-único + CHECK `^\d{8}$` —
   **duas** migrations (`batch_alter_table` DDL + seed de dados idempotente
   por `code`, padrão `adr238informes1`). Precedente: `asset_catalog.cnpj` +
   seed YAML versionado.
3. Propagação a `pipeline/` via `InstitutionEntry.cnpj_raiz` +
   `WorkspaceContext.institution_catalog_provider` (**não** via
   `StageConfig.institutions` — via morta). Mapa `{raiz: code}` entra em
   `apply_informe_override` como parâmetro tipado ([[ADR-089]]/[[ADR-097]] D2).
4. Cache do resolver: chave versionada (`institution_catalog:global:v2`) +
   `invalidate_catalog()` com caller real de deploy — sem isso o matcher
   nasce inerte por até 30 dias (TTL do payload antigo).

**Vetado nesta lane** (`data-engineer`): CNPJ completo de 14 dígitos com
UNIQUE (falha estreita e silenciosa); `metadata_json` (sem constraint, sem
índice); perna agência/conta (não existe nos schemas de origem — lane de
extração + `prompt-engineer` se necessário).

## Critério de aceite

- Teste do resolvedor com as três representações que quebram hoje:
  `"btg pactual"`, `"btgpactual"`, `"Conta Corrente - Ag 9652..." +
  cnpj_emissor`.
- No dogfood, Itaú CC e Wise BRL passam a casar por CNPJ-raiz (hoje 0/6).
- Migrations verdes em SQLite online **e** `--sql` offline; teste com
  `pytestmark = pytest.mark.migration`; CHECK exercitado com valor inválido.
- Teste de cache: payload antigo não é servido após bump de chave; falha
  aberta para o DB, nunca mapa vazio silencioso.
- Gate: todo `code` com `category ∈ {bank, broker, exchange}` tem
  `cnpj_raiz`, verificado sobre as migrations (não sobre `create_all`).
