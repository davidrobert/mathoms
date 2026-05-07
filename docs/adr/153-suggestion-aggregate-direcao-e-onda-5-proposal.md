---
id: ADR-153
type: adr
title: "`Suggestion` aggregate (Direção E · Onda 5): proposal imutável + state machine simples"
status: Decidido
phase: "Direção E · Onda 5"
date: "2026-04-29"
relates_to: ["[[ADR-152]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 153"]
tags:
  - type/adr
  - status/decidido
size_lines: 156
---

# ADR-153 — `Suggestion` aggregate (Direção E · Onda 5): proposal imutável + state machine simples

**Status:** Decidido (Direção E · Onda 5) • **Data:** 2026-04-29 •
**Relaciona** [ADR-152](#adr-152--plano-de-acao-renomeada-para-acao-com-tabs-direção-e--onda-6)
(rota `/acao`),
[ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain)
(Decision aggregate),
[ADR-074](#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório)
(Task aggregate),
[ADR-090](#adr-090--decimal-para-valores-monetários) (Money em cents).

**Contexto:** Direção E completa o ritual **relatório → sugere →
usuário decide → vira Decision (+ Task)**. Faltava a peça `Suggestion`
— Onda 4 já entregou `SuggestionsBanner` em `/plano` (stub) e Onda 6
deixou empty state ensinante em `/acao` Inbox aguardando esta.

Decisões de design pendentes (ver track):

1. **Imutabilidade.** Sugestão é proposta determinística do gerador
   E5; o que muda no tempo é o status (Pendente → Aceita/Modificada/
   Descartada). Mudança no conteúdo invalidaria rastreabilidade
   (relatório original "fez tal sugestão"). Decision criada a partir
   da aceitação carrega o que mudou.
2. **Dedup.** Re-rodar pipeline em cima do mesmo workspace não pode
   ressuscitar sugestões já tratadas. Precisa de chave determinística
   que tolere flutuações pequenas (TRS 4,8% → 4,9% é "mesma sugestão";
   4,8% → 6,0% é "novo gatilho").
3. **Cap.** Designer fixou 3-6 sugestões/relatório; muito além disso
   vira ruído.
4. **Origem.** v1 deve ser deterministic ou já incluir LLM?
5. **Tasks geradas no aceitar.** Templates de onde?

**Decisão:**

1. **`Suggestion` é simple aggregate, NÃO event-sourced.** Tabela
   única `suggestions`. Conteúdo (`title`, `rationale`, `severity`,
   `amount_brl_cents`, `kind`, `section_id`) é **imutável** após
   inserção. Apenas `status` (Pendente/Aceita/Modificada/Descartada),
   `dismissed_reason`, `accepted_decision_id`, `dismissed_at`,
   `accepted_at` mutam. Por que não event-sourced: ciclo de vida é
   curto e linear (Pendente → terminal); audit trail caro de manter
   sem benefício real. **Decision aggregate** (ADR-136) é onde o
   audit trail de fato vale a pena.
2. **Dedup via `dedup_key` determinístico.** Hash
   `sha256(workspace_id|kind|amount_bucket)` onde `amount_bucket`
   arredonda valor para o múltiplo de 5 mais próximo (TRS) ou R$1k
   mais próximo (valor monetário) — tolera ruído sem perder gatilhos
   reais. Unique constraint parcial: `(workspace_id, dedup_key)` único
   quando `status IN ('Pendente','Aceita','Modificada')`. Re-gerar
   busca por dedup_key:
   - Já existe Pendente/Aceita/Modificada → **skip silencioso**
     (idempotência).
   - Já existe Descartada com `dismissed_at` < 90 dias atrás →
     **skip** (respeita o "não, obrigado" recente).
   - Já existe Descartada com `dismissed_at` ≥ 90 dias atrás → **insere**
     (revisitar tese ao longo do tempo).
3. **Cap = 6 por re-geração.** Generator ranqueia drafts por
   `severity` (danger > warning > info) → `amount_brl_cents` desc;
   trunca em 6.
4. **v1 determinístico.** 5 gatilhos canônicos: TRS desalinhada
   (>15% acima de TRS conservadora), reserva insuficiente (<6 meses),
   alocação fora do alvo (>10pp), aporte abaixo da meta (<70% nos
   últimos 3 meses), dolarização atrasada (cobertura <meta-15pp).
   LLM em sessão futura (`track_onda_5_llm_suggestions.md`) sob o
   mesmo schema — basta gerar drafts adicionais que respeitem o
   cap+dedup.
5. **Tasks no aceitar — out-of-scope para v1.** Aceitar cria apenas
   uma `Decision` (ADR-136) via use case `accept_suggestion`, com
   `derived_from_suggestion_id` salvo no payload do
   `DecisionCreatedEvent`. Templates de Task vêm depois quando o
   produto pedir; mantém superfície de testes pequena.
6. **Trigger da geração: endpoint dedicado, NÃO hook do pipeline.**
   `POST /workspaces/{ws}/reports/{id}/regenerate-suggestions` lê
   o snapshot E5 do `Report.analysis_artifact`, roda o generator, e
   persiste. Razões:
   - Pipeline (`pipeline/**`) **não pode importar `backend.app.*`**
     (CLAUDE.md). Manter o trigger no backend respeita o boundary.
   - Operação idempotente — re-executável sob demanda (debug, smoke
     test, regerar após mudança nas regras) sem re-rodar todo E5.
   - Generator vive em `pipeline/domain/services/suggestion_generator.py`
     (puro, deterministic, sem I/O); backend importa do pipeline,
     que é a direção permitida.

   > **Nota (2026-04-29):** o trigger original assumia chamada manual
   > do endpoint, o que deixou `/acao` Inbox vazio após cada run
   > completo (nenhum consumidor disparava). A regra **boundary**
   > ("pipeline não importa backend") segue valendo, mas **não veta**
   > disparar do post-processing do Celery worker — `_run_post_processing`
   > já roda dentro de `backend/app/tasks/pipeline_task.py` (backend→backend,
   > boundary intacto). Adicionado `_persist_aggregate_suggestions`
   > sync chamado após `_create_report_from_output` na mesma janela
   > best-effort de `_persist_llm_suggestions` (idempotência mantida via
   > `dedup_key`; falha aqui só gera warning, não aborta o run). O
   > endpoint REST continua disponível como ponto de re-execução manual
   > (debug, smoke test, regerar após mudança nas regras).
7. **Endpoints REST canônicos:**

   ```
   GET    /workspaces/{ws}/suggestions?status=Pendente
   GET    /workspaces/{ws}/suggestions/count?status=Pendente
   GET    /workspaces/{ws}/suggestions/{id}
   POST   /workspaces/{ws}/suggestions/{id}/accept
   POST   /workspaces/{ws}/suggestions/{id}/modify
   POST   /workspaces/{ws}/suggestions/{id}/dismiss
   POST   /workspaces/{ws}/reports/{report_id}/regenerate-suggestions
   ```

   Money em wire = string decimal (ADR-090). Persistência em
   `amount_brl_cents` BIGINT.

**Consequências:**

- ✅ Direção E completa: relatório (callouts inline + agregador) →
  `/acao` Inbox (aceitar/modificar/descartar) → `/plano` (Decisions
  criadas + banner de pendentes).
- ✅ Boundary do pipeline preservado — generator é puro em
  `pipeline/domain/services/`, apenas backend persiste.
- ✅ Idempotência: re-rodar regenerate é seguro; dedup_key impede
  duplicatas.
- ✅ Estende para LLM em onda futura sem mudar schema (campo `kind`
  + `origin: 'deterministic'|'llm'` permite LLM convivendo).
- ⚠️ Janela de "respeitar Descartada" fixa em 90 dias — pode ficar
  apertada/larga conforme uso. Constante em `pipeline/domain/services/
  suggestion_generator.py` (`DISMISS_RESPECT_WINDOW_DAYS = 90`); ajustar
  via PR quando dado real chegar.
- ⚠️ Generator não é invocado automaticamente pelo pipeline. Smoke
  test e teste de paridade chamam o endpoint explicitamente. Gancho
  automático (e.g. ao concluir pipeline run) fica para sessão futura
  se vier demanda.
- ❌ Sem audit trail completo (event-sourced) da Suggestion. Trade-off
  consciente: simplicidade > rastreabilidade redundante (Decision já
  carrega o que importa).

**Referências de código:**

- `backend/app/models/suggestion.py` — model + `VALID_SUGGESTION_*`
  frozensets.
- `backend/alembic/versions/<rev>_adr153_suggestions.py` — migration.
- `backend/app/repositories/suggestion_repository.py` — primitives.
- `backend/app/application/suggestions/` — `create_suggestion`,
  `accept_suggestion`, `modify_suggestion`, `dismiss_suggestion`,
  `list_suggestions`, `count_suggestions`, `get_suggestion`,
  `regenerate_for_report`.
- `backend/app/api/suggestions.py` — router.
- `backend/app/schemas/dto/suggestion/` — DTOs + mapper.
- `pipeline/domain/services/suggestion_generator.py` — regras puras.
- `frontend/src/lib/api/suggestions.ts` — client.
- `frontend/src/hooks/useSuggestions.ts` — hook.
- `frontend/src/components/report/sections/SuggestionCallout.tsx` —
  callout inline + agregador.
- `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx` —
  card de Inbox.
- `frontend/src/app/(app)/plano/_components/useSuggestionsCount.ts`
  (substituído stub Onda 4).
