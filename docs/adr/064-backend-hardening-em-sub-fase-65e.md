---
id: ADR-064
type: adr
title: "Backend hardening em sub-fase 6.5E"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 064"]
tags:
  - type/adr
  - status/decidido
size_lines: 43
---

# ADR-064 — Backend hardening em sub-fase 6.5E

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** O incidente BUG-015 (capa do relatório vazia para workspaces multi-tenant porque `serialize_family_members` perdia `familia.sobrenome` ao sobrescrever o JSON tenant) revelou uma classe inteira de bugs latente:

1. Os serializers (DB → pipeline JSON) são **contratos silenciosos** — sem testes de round-trip, qualquer mudança quebra o pipeline sem que o backend perceba
2. O fallback do `_copy_global` permite que dados do founder vazem para workspaces reais (relacionado a BUG-004)
3. Migrations Alembic rodam contra qualquer DB no `cwd` — possível aplicar migration na DB errada (foi exatamente o que aconteceu durante o fix de BUG-015)
4. `_init_config` é compartilhado entre Celery workers — sem teste de concorrência

F6.5 originalmente cobria só frontend. F7D.1-3 falava em "gap-fill" mas sem foco específico nessas fronteiras.

**Alternativas consideradas:**
- (A) Adicionar tasks soltas em F7D — se diluem entre 30+ outras tarefas, alta chance de cair
- (B) Esperar primeira regressão real em prod — inaceitável para produto financeiro
- (C) **[escolhida]** Sub-fase 6.5E dedicada (~2 dias), antes do deploy para prod

**Decisão:** Criar sub-fase **6.5E — Backend Hardening** com 7 tasks (5 P0 + 2 P1) cobrindo:
- Round-trip tests para os 6 serializers
- Golden file pipeline com PDFs sintéticos (proves zero data leakage)
- Alembic CI guardrails (drift + idempotency + dry-run)
- Fix de cwd-sensitivity em alembic.ini
- Test anti-regressão BUG-015 explícito
- Systemic fix para fallback-leak class
- Concurrency test para `_init_config`

**Critérios de aceite adicionais em F6.5:**
- 6 serializers com round-trip green
- Golden pipeline test com PDFs sintéticos: green
- CI falha em migration drift ou non-idempotent
- BUG-015 coberto por test que falharia se removermos o fix

**Consequências:**
- ✅ Classe BUG-015 eliminada via cobertura sistemática
- ✅ Confiança em mudar serializers no futuro
- ✅ Migrations não podem aplicar na DB errada por acidente
- ✅ Pipeline test golden com dados sintéticos = base reusável para 6.5C.0 E2E
- ⚠️ Prazo de F6.5 +2 dias (2.5 → 3 semanas)
- ⚠️ Manutenção: golden file precisa ser regenerado quando schema do report muda intencionalmente
- ❌ Não cobre todos os edge cases de scripts E5/E6 — ainda fica para 7D.2 gap-fill
