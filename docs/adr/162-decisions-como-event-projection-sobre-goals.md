---
id: ADR-162
type: adr
title: "Decisions como event projection sobre Goals"
status: Decidido
phase: "Onda 8"
date: "2026-05-04"
relates_to: ["[[ADR-073]]", "[[ADR-136]]", "[[ADR-153]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 162"]
tags:
  - area/backend
  - area/money
  - area/persistence
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 49
---

# ADR-162 — Decisions como event projection sobre Goals

**Status:** Decidido (Onda 8) • **Data:** 2026-05-04 • **Relaciona** [ADR-073](#adr-073--goals-como-entidade-versionada-não-config-estático), [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain), [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples).

**Contexto:** Decisões e Goals vivem em órbitas separadas no produto. Aceitar uma sugestão `trs_desalinhada`, criar `Decision D03 — "Reduzir TRS para 4%"`, marcá-la `Executada` **não atualiza** o Goal IF correspondente — usuário precisa abrir `/plano/metas` e editar o TRS manualmente. Resulta em divergência: Decision diz "TRS=4%", Goal vigente diz "TRS=4.5%", relatório usa Goal e contradiz a Decision exibida.

**Decisão:** Quando uma Decision com `target_field` populado é marcada `Executada`, o use case `mark_executed` dispara automaticamente `goal_service.create_goal_version(...)` na **mesma transação**, criando nova versão do Goal correspondente com `params_json.derived_from_decision_id = <decision.id>`.

**Sub-decisões:**

1. **Schema da Decision** — adicionar 3 campos nullable (migration `e0f1a2b3c4d5_adr162`):
   - `target_field: String(64)` — caminho dot-notation (`goal.if.trs_pct`, `goal.aporte.meta_aporte_mensal_brl`).
   - `target_value: String(64)` — valor decimal/string serializado (parse no use case por `target_value_type`).
   - `target_value_type: String(8)` — `pct` | `brl` | `int` | `str`. Necessário para parsing seguro (BRL vai a Decimal, pct a float).

2. **Mapping `target_field → goal_type + param_path`** vive em `backend/app/services/decision_goal_projection.py` (módulo novo). Tabela centralizada:

   ```python
   PROJECTIONS = {
       "goal.if.trs_pct": ("INDEPENDENCIA_FINANCEIRA", "trs_pct"),
       "goal.if.renda_passiva_mensal_brl": ("INDEPENDENCIA_FINANCEIRA", "renda_passiva_mensal_brl"),
       "goal.aporte.meta_aporte_mensal_brl": ("APORTE_MENSAL", "meta_aporte_mensal_brl"),
       "goal.dolar.meta_usd": ("DOLARIZACAO", "meta_usd"),
       "goal.alocacao": ("ALOCACAO_ALVO", "<full_replace>"),
   }
   ```

3. **Atomicidade:** projeção corre na mesma `db.transaction()` do `mark_executed`. Falha de `create_goal_version` (ex.: validation Pydantic) faz rollback do `Executed` event — Decision continua `Decidido` e usuário vê erro com motivo.

4. **`derived_from_decision_id`** popula `params_json.meta.derived_from_decision_id` (não coluna nova) — preserva schema flexível do Goal e habilita query "histórico de Goals que vieram de Decisions" via JSON query.

5. **`target_field == None` continua funcionando.** Decisions sem target ("decidi conversar com consultor", "manter posição") simplesmente não disparam projection — comportamento legado preservado.

**Consequências:**

- ✅ Decisões finalmente fecham o loop com Goals — usuário aceita Sugestão, marca Executada, relatório seguinte reflete novo TRS sem ação manual.
- ✅ Auditoria completa: `Decision.id` rastreável até Goal version criada via `params_json.meta.derived_from_decision_id`.
- ✅ Preservação de legado: Decisions sem `target_field` continuam terminais; nada quebra.
- ⚠️ Mapping `PROJECTIONS` é tabela pequena mas precisa manutenção quando novos goal types entrarem. Tabela é o ponto explícito de evolução — não há mágica.
- ⚠️ Falha em `create_goal_version` reverte `mark_executed` — usuário pode achar que "marcar executado falhou misteriosamente". UX precisa toast com causa raiz (Pydantic field error).
- ❌ Não suporta projection complexa (ex.: Decision afetando múltiplos Goals). Caso surja, virar event-bus separado — não bloquear MVP.

**Follow-ups:**

1. UI mostra "Decisão D03 → Goal IF v4" no DecisionCard quando expandido (rastreabilidade visual).
2. Goal version novo aparece no histórico em `/plano/metas` com badge "Derivada de D03".
3. Roadmap: webhook/notification quando Goal mudar via Decision (post-action confirmation).
