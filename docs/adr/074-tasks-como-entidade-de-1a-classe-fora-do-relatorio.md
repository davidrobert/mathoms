---
id: ADR-074
type: adr
title: "Tasks como entidade de 1ª classe (fora do relatório)"
status: Decidido
phase: "F8"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 074"]
tags:
  - area/multitenancy
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 56
---

# ADR-074 — Tasks como entidade de 1ª classe (fora do relatório)

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.2 — Plano de Ação

**Contexto:** Hoje a "checklist de tarefas" vive em [config/tarefas.md](config/tarefas.md) como markdown versionado no git, parseado deterministicamente pelo E5, enriquecido pelo E5.N (LLM), e renderizado no relatório HTML final pelo E6. Esse fluxo é elegante para o pipeline batch, mas **impossibilita execução interativa**:
- Usuário não consegue marcar "feito" sem editar markdown e rodar pipeline de novo.
- Não há notificação de prazo (ex: IPTU 30/04 é time-bomb).
- Sem anexos de comprovante, sem conexão com transações, sem histórico estruturado.
- Sugestões do E5.N ficam em `tarefas_sugeridas[]` que o usuário precisa copiar/colar manualmente.
- Relatório vira poluído de operacional — deveria ser estratégico (foto do momento).

No modelo multi-família, cada workspace tem seu próprio backlog com dinâmica distinta — um arquivo compartilhado no repo não escala.

**Alternativas consideradas:**
- (A) **Manter `tarefas.md` por workspace** (um arquivo por tenant no storage local).
  - ❌ Rejeitada: não resolve execução interativa; arquivo compartilhado entre pipeline e UI gera race; sem audit/versionamento/anexos.
- (B) **Tabela `tasks` como entidade de 1ª classe + `task_suggestions` queue + `task_attachments`**.
  - ✅ **Escolhida**: resolve todos os problemas. `tarefas.md` vira *export* gerado on-demand (compat pipeline legado).
- (C) **Integrar com Todoist/Things/Linear via OAuth**.
  - ❌ Rejeitada: acopla produto a SaaS externo, perde ligação semântica com dados financeiros (task↔transaction↔goal), e LGPD + contexto fintech exigem dados sob controle.

**Decisão:**
1. **Tabelas novas**: `tasks`, `task_suggestions`, `task_attachments` (reusa padrão do vault para anexos).
2. **`Task` preserva `number int` único por workspace** — mantém a ref `#5` do `tarefas.md` atual, crítica para rastreabilidade em commits, ADRs e narrativas do E5.N.
3. **`Task.deadline`** é modelado com `deadline_kind Enum("HARD_DATE", "MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED")` + `deadline_date Date|NULL` + `deadline_label str|NULL`. Acomoda os padrões do MD atual ("Abr/2026", "30/04/2026", "Antes EUA", "T3/26").
4. **`Task.status`** com transições validadas: `pending → in_progress | done | cancelled | blocked`; `blocked → pending | cancelled`; `done` e `cancelled` são terminais (exigem `unarchive` explícito para reabrir). Enforcer em `task_service.transition_status`.
5. **Dependências explícitas** via `parent_task_id` — UI bloqueia marcar como `done` se parent estiver pendente (regra do `enforce_dependency_rule`). Migração inicial infere dependências a partir das Notas do `tarefas.md` (ex: "#19 depende de #18").
6. **E5.N escreve em `task_suggestions`** (não mais em `tarefas_sugeridas[]` do JSON). Sugestão contém `proposed_payload JSONB` com estrutura idêntica à `Task`. Usuário aprova 1-click → cria `Task` + marca suggestion como `approved`. Queue aparece em `/plano-de-acao/sugestoes` com badge contador.
7. **Relatório lê snapshot imutável** — no momento da geração do relatório (E6), o serviço copia o estado atual de `tasks` para `report.snapshot_json`. O relatório renderiza a partir do snapshot, não do DB live. Garante que "relatório de 15/abr/2026" sempre mostra o que estava pendente naquele dia.
8. **Export `GET /tasks/export.md`** — gera `tarefas.md` on-demand a partir do DB, preservando formato atual. Usado durante transição para scripts legados que ainda esperam o arquivo.
9. **Migração one-shot do `tarefas.md` de Ferreira Campos** — importer em `backend/app/scripts/seed_tasks_ferreira_campos.py` parseia o MD, cria tasks preservando `number` (1..43, com `#2` e `#12` como `status=done`), categorias, prioridades, status, ref. Notas com dependência ("#19 depende de #18") são parsed e materializadas em `parent_task_id`.
10. **Novos workspaces recebem templates genéricos** (não dados do workspace dogfood) — 10-12 tarefas essenciais comuns a qualquer família (contratar seguro vida, consultar CPA expatriado se aplicável, etc.) com `created_from='seed'`. Usuário pode aceitar, editar, ou descartar no onboarding.
11. **Integração Task↔Transaction↔Goal (F8.3)** — `related_transaction_id` e `related_goal_id` opcionais. UI usa para mostrar "% executado" (tarefa "Aporte R$20k/mês" lê aportes do mês atual agregados por `aporte_match_keywords` do `goals.json`).
12. **Remoção do `tarefas.md` do repo** acontece em F8.4 (cutover final) — até lá, arquivo permanece como seed/fallback.

**Consequências:**
- ✅ Execução interativa real — marca feito, anexa comprovante, recebe notificação
- ✅ Relatório volta a ser estratégico (snapshot imutável) — operacional fica no módulo próprio
- ✅ Sugestões do E5.N viram fluxo de aprovação UI, não copy-paste em markdown
- ✅ Dependências explícitas destravam UX ("cadeado" em task bloqueada)
- ✅ Audit log natural de transições
- ✅ Multi-tenant desde o dia 1 via [ADR-072](#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família)
- ⚠️ Pipeline E5 precisa refatorar leitura — de parser MD para `task_service.list_tasks(workspace_id)` via adapter. Contrato JSON preservado.
- ⚠️ Novas tarefas criadas via UI precisam de `number` — incrementa `max(number) + 1` por workspace (lock em transação para evitar race)
- ❌ Sem sync bidirecional com Google Tasks / Todoist — aceito (débito; pode ser adicionado sem quebrar modelo)

**Implementação inicial (F8.2):**
- Models + migrations
- Services (`task_service`, `task_suggestion_service`) com transições validadas
- Endpoints documentados no plano
- Rota frontend `/plano-de-acao` + drawer + sugestões
- Widget `UpcomingTasksWidget` no dashboard (`deadline_date <= today + 7d` e `status in (pending, in_progress)`)
- Importer one-shot + testes de paridade (MD inicial vs. DB pós-import)
- Feature flag `tasks_v2_enabled` (workspace-level)
