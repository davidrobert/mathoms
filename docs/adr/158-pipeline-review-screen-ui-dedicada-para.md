---
id: ADR-158
type: adr
title: "Pipeline review screen — UI dedicada para aprovar/editar `StageReview`"
status: Decidido
phase: "Sprint A8 · Lane pipeline-review-screen"
date: "2026-05-02"
relates_to: ["[[ADR-076]]", "[[ADR-097]]", "[[ADR-157]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 158"]
tags:
  - area/frontend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 57
---

# ADR-158 — Pipeline review screen — UI dedicada para aprovar/editar `StageReview`

**Status:** Decidido (Sprint A8 · Lane pipeline-review-screen) • **Data:** 2026-05-02 • **Relaciona** [ADR-076](#adr-076--design-tokens-unificados-site--relatório), [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy), [ADR-157](#adr-157--schema-irpf-completo-stage-extract_irpf_full).

**Contexto:** O backend tem fluxo human-in-the-loop completo desde a Phase 4 do schema inicial — tabela `stage_reviews` (`pending|approved|edited`, `original_output_json`, `edited_output_json`, `validation_errors`, `reviewer_notes`), endpoints REST `GET /reviews` e `POST /reviews/{id}` (action `approve|edit`), use cases `action_review` + `resume_run` (este recusa retomada se `count(stage_reviews where status=pending) > 0`). Helpers TS já existiam em `lib/api/pipeline.ts` mas com tipo `unknown[]` e payload incorreto (`edited_output`/`notes` em vez de `edited_output_json`/`reviewer_notes`). **Nenhum componente da UI consumia esses endpoints** — `NeedsReviewCard` só renderizava banner com botão que ia direto para `/resume` e batia em 409 sempre que havia review pending. Stage `extract_irpf_full` (ADR-157) é o gatilho que tornou esse gap bloqueante: declarações IRPF caem em `needs_review` por validação de schema strict, e não havia caminho de UI para o usuário consertar.

Alternativas avaliadas:

1. **Caminho A — quick-unblock (auto-approve loop)**: `handleResume` em `/pipeline` chama `submitStageReview` com `action:"approve"` para cada pending e depois `resumePipelineRun`. Implementação ~1h, zero rota nova, descarta `validation_errors` sem mostrar ao usuário, perde a chance de editar. Aceitável como stop-gap de horas até esta lane mergear, perigoso como solução permanente (esconde dados úteis).
2. **Editor inline no `NeedsReviewCard`**: expande o card para mostrar JSON + erros + botões. Polui página `/pipeline` (já densa); navegação para múltiplos reviews fica truncada; mistura overview do run com detalhe de cada review. Dropping.
3. **Tela dedicada `/pipeline/runs/[runId]/reviews`** (escolhida): rota com lista + detalhe, viewer read-only para `original_output_json`, editor JSON simples para `edited_output_json`, painel de `validation_errors`, ações `approve`/`edit`. `NeedsReviewCard` vira ponteiro (botão "Revisar agora" → `router.push`). Retomada automática quando `count(pending)==0` (ADR-097/contrato backend).
4. **Editor JSON — Monaco vs textarea**: Monaco (`@monaco-editor/react`) é IDE-grade com syntax highlight + formatação; bundle ~300KB extra. Textarea + `JSON.parse` no submit é ~30 LOC, zero deps, sem syntax highlight. Para v1, edição é eventual (1×/ano em IRPF típico) e o JSON é pequeno (~80 campos no `extract_irpf_full`). **Decisão D1 (textarea)**; D2 (Monaco) só se sign-off `product-designer` exigir UX rica — abrir ADR adicional para bundle size nesse caso.

**Decisão:** Adotar (3) com editor D1. Rota `/pipeline/runs/[runId]/reviews` (lista) e `/pipeline/runs/[runId]/reviews/[reviewId]` (detalhe). `NeedsReviewCard` vira ponteiro com contagem de pendentes + CTA "Revisar agora" + CTA secundário "Cancelar execução". `handleResume` em `/pipeline/page.tsx` é **removido** — retomada agora é consequência implícita de aprovar/editar todas as revisões pendentes (`useReviewList` chama `resumePipelineRun` automaticamente quando `count(pending)==0`). Tipos TS estritos (`StageReviewResponse`, `StageReviewActionRequest`) substituem `unknown[]` em `lib/api/pipeline.ts`.

**Sub-decisões:**

1. **Sem validação client-side contra schema** — ADR-097 deixa explícito que validação de output é responsabilidade do pipeline downstream. Editor só verifica se é JSON parseável (objeto não-array). UI exibe warning *"Edição não validada — schema só será re-checado quando o pipeline retomar"*. Re-validação acontece no rerun do stage com o `edited_output_json` aplicado.
2. **Concorrência (409)** — backend retorna 409 se outro agente/aba já aprovou o review. UI trata como **info toast** + refetch + atualiza estado local (review aparece como `approved`/`edited`, painel de ações é substituído por "Esta revisão já foi processada"). Não é erro do usuário; não há toast vermelho.
3. **Highlight de campos com erro no viewer** — heurística `extractPath()` extrai `field`, `'name'`, `$.path.field` ou `name:` de cada linha de `validation_errors`; viewer marca linhas do JSON formatado que casam com aqueles paths via `bg-alert/10`. Falsos negativos toleráveis (highlight é hint visual, não load-bearing). Tipagem específica por stage fica como follow-up (codegen a partir de `config/schemas/*.schema.json`).
4. **Status enum imutável** — UI cobre `pending|approved|edited`. Adicionar `rejected` (reprovar review e marcar run como falho) requer ADR específica + sign-off `data-engineer` (mudança de enum DB). Hoje, "rejeitar" se faz cancelando o run.
5. **Tokens semânticos** — pending usa `--semantic-alert` / `text-alert` / `bg-alert/10` (ADR-076); erro de carga usa `text-loss`. `NeedsReviewCard` migra de `border-warning/50 text-warning` para `border-alert/50 text-alert`. Sem hex literal.
6. **Endpoint `GET /reviews/{id}` não adicionado** — frontend resolve com lista cacheada em state (`listStageReviews` → `find(id)`). Custo: 1 request a mais por entrada no detalhe quando vindo de deep link. Aceitável; não bloqueante. Adicionar fica higiênico, deixado como follow-up.

**Consequências:**

- ✅ `validation_errors` ficam visíveis e clicáveis — usuário entende **por que** o stage caiu em review e o que precisa corrigir.
- ✅ `edited_output_json` rastreável — backend já persiste; UI agora exercita o caminho.
- ✅ Concorrência multi-aba/multi-agente é tratada graciosamente, sem login fantasma de erros.
- ✅ Tipagem nominal substitui `unknown[]` — boundary API↔UI fica TS-safe; refactor backend quebra TS antes de produção.
- ✅ Reversibilidade alta — basta reverter o card para auto-approve para voltar ao caminho A.
- ⚠️ Usuário precisa de ≥1 click extra (Revisar agora → ação) vs. caminho A — aceito como custo do "fail explicit" sobre "fail silent".
- ⚠️ Editor D1 (textarea) não tem syntax highlight — rich UX só com D2 (Monaco) + ADR de bundle size, ainda não justificada.
- ⚠️ Tipagem de `original_output_json` é `Record<string, unknown>` — narrow por stage fica como follow-up (codegen).
- ❌ Cenário Playwright @critical completo (seed run em `needs_review` + 2 reviews pending + aprovar/editar/resume) **não entregue** nesta lane — depende de helper `seedNeedsReviewRun` no e2e suite que ainda não existe. Spec original aceita follow-up.
- ❌ Endpoint `GET /reviews/{id}` não adicionado — UI lista inteira cacheada resolve, ainda assim deep link recarrega `[N reviews]` por entrada.

**Referências de código:**

- `frontend/src/app/(app)/pipeline/runs/[runId]/reviews/page.tsx` — rota lista.
- `frontend/src/app/(app)/pipeline/runs/[runId]/reviews/[reviewId]/page.tsx` — rota detalhe.
- `frontend/src/app/(app)/pipeline/runs/[runId]/reviews/_components/` — `JsonViewer`, `JsonEditor`, `ReviewActions`, `ReviewDetailHeader`, `ReviewListItem`, `ValidationErrorsPanel`, `useReviewList`.
- `frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx` — ponteiro pós-refactor.
- `frontend/src/app/(app)/pipeline/page.tsx` — `handleResume` removido; `pendingReviewCount` derivado de `listStageReviews`.
- `frontend/src/lib/api/pipeline.ts` — `StageReviewStatus`, `StageReviewResponse`, `StageReviewActionRequest`, `listStageReviews`, `submitStageReview`.
- `frontend/tests/pages/pipeline-reviews.test.tsx` — Vitest cobertura.
- `frontend/tests/e2e/pipeline-review-screen.spec.ts` — Playwright smoke (cenário completo é follow-up).

**Follow-ups:**

1. Tipagem por stage (codegen a partir de `config/schemas/*.schema.json`).
2. Diff visual entre `original_output_json` e `edited_output_json` no histórico.
3. Cenário Playwright completo + helper `seedNeedsReviewRun`.
4. Endpoint `GET /reviews/{id}` (e `make update-openapi-snapshot`) — higiênico, não bloqueante.
5. Métricas LLMOps: % approved vs edited por stage (lane separada com `sre-devops`/FinOps).
