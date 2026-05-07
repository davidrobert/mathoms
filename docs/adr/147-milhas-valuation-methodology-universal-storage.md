---
id: ADR-147
type: adr
title: "Milhas: valuation methodology universal + storage workspace-scoped"
status: Decidido
phase: "Sprint A7.6 · CTO sign-off 2026-04-27"
date: "2026-04-27"
relates_to: ["[[ADR-143]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 147"]
tags:
  - area/money
  - area/multitenancy
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 42
---

# ADR-147 — Milhas: valuation methodology universal + storage workspace-scoped

**Status:** Decidido (Sprint A7.6 · CTO sign-off 2026-04-27) • **Data:** 2026-04-27 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76).

**Contexto:** O relatório do Mathoms inclui um card "Programas de Milhagem" (Smiles, Latam Pass, Livelo, Atomos, MasterCard Surpreenda, etc.) com saldo de pontos por programa, valor estimado em BRL e regras de expiração. A fonte histórica é `config/milhas.md` (movido para `docs/methodology/` em A7.4) parseado em runtime por `scripts/e5_analyze.py::parse_milhas_md(workspace_root)`.

O arquivo é **duas coisas ao mesmo tempo**: (a) doc humano com método de valuation universal (como avaliar 1 ponto Smiles em campanha vs base), (b) fonte de dados cliente-específica em runtime (saldos de Smiles do David, Latam Pass da Mariana). Anti-padrão clássico: doc + dado misturados em mesmo artefato versionado em git.

ADR-143 elimina `docs/methodology/`. Esta ADR define dois caminhos separados:

Alternativas consideradas para o **dado cliente** (saldos por programa):

- **(α) `storage/<ws>/notes/milhas.md` gitignored, mesmo formato markdown.** `parse_milhas_md` lê do path novo. Migrator one-shot copia conteúdo atual para workspace piloto. **Trade-off:** continua file-based, sem API/UI editável. Drift entre notas humanas e relatório possível.
- **(β) DB entity `MileageProgram(workspace_id, member_id, program_code, balance_points, accumulation_rate, valuation_per_point_cents, expiration_date, notes)`.** API + UI + migrator. Alinhado com pattern de `Decision` (ADR-136) e `FamilyMember`. **Trade-off:** ~2-3 sessões de trabalho extra além de A7.6 (paralelo de A7.2a). Mas é a saída arquitetural correta.
- **(γ) Híbrido escalonado.** A7.6 entrega α (storage notes + bridge); Sprint A8.1 entrega β (DB entity).

**Decisão:** Adotar **(γ)** com escopo claro entre as lanes:

**A7.6 entrega:**
- Universal valuation methodology em docstring na função `parse_milhas_md` (ou no novo módulo refatorado equivalente). Documenta: como precificar 1 ponto Smiles vs Latam Pass vs Livelo (regras genéricas, sem saldos cliente); periodicidade de atualização do método (ad-hoc, não programada).
- Workspace-specific dados (programas + saldos) migram para `<workspace>/storage/<workspace_id>/notes/milhas.md` (gitignored, formato markdown estruturado idêntico ao atual).
- Migrator one-shot `dev/migrate_milhas_to_workspace_storage.py` copia conteúdo atual de `docs/methodology/milhas.md` para o workspace piloto. Idempotente.
- Bridge transitório: `parse_milhas_md` tenta o path novo primeiro; fallback para path antigo + `DeprecationWarning`. Bridge removido em A7.5 cleanup.

**Sprint A8.1 entrega (débito técnico aceito):**
- Schema DB: `MileageProgram` aggregate workspace-scoped + `MileageProgramSnapshot` para histórico de saldos.
- Endpoints CRUD `/v1/workspaces/{id}/mileage-programs`.
- Frontend tela de configuração (substitui edição manual de markdown).
- Migrator de `storage/<ws>/notes/milhas.md` → DB rows.
- `parse_milhas_md` deprecated; novo `load_mileage_programs(ws_id, db)` lê do DB.
- `storage/<ws>/notes/milhas.md` deprecated com warning; removido em A8.x cleanup.

**Consequências:**
- ✅ A7.6 não é bloqueada pelo escopo de modelagem `MileageProgram` (que paralelaria A7.2a Decision em complexidade).
- ✅ Dado cliente sai de git imediatamente (sub-task A7.6 entrega α antes do final da Sprint A7).
- ✅ Método de valuation universal preservado em docstring + ADR — sobrevive a futuras refatorações.
- ✅ A8.1 fica registrado como débito técnico explícito em `docs/BACKLOG.md §Sprint A8` (placeholder aberto em A7.6).
- ⚠️ Janela transitória: workspace piloto edita `storage/<ws>/notes/milhas.md` manualmente. UX para clientes novos requer A8.1 mergeada.
- ⚠️ `storage/<ws>/notes/` é primeiro caminho "notes workspace-scoped" do produto. ADR-147 estabelece o padrão: gitignored, formato livre (markdown), parser específico por categoria de notes, sempre acompanhado de docstring no parser que documenta o schema esperado.
- ❌ Período entre A7.6 e A8.1: dois caminhos de leitura coexistem (path novo prioritário; fallback warned). DeprecationWarning + log estruturado torna o caminho legado discreto mas detectável.
