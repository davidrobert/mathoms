---
id: TRACK-pipeline-review-screen
type: track
title: "Track Pipeline Review — Tela de revisão real (caminho B)"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track Pipeline Review — Tela de revisão real (caminho B)

> **Lane ID:** pipeline-review-screen
> **Branch prefix:** `agent/pipeline-review-screen/*`
> **Depende de:** nada (toca frontend + dois ajustes pequenos no contrato API). Pode ser feito antes ou depois de A; **substitui** A.
> **Conflita com:** [track_pipeline_review_quick_unblock.md](track_pipeline_review_quick_unblock.md) — **mutuamente exclusivo** com A. Se A já foi mergeado, esta lane também **remove** a auto-approve loop em `handleResume` (substitui pela ação explícita do usuário).
> **Onda:** independente / produto premium
> **ADR:** **obrigatória** — abrir ADR nova *"Pipeline review screen — UI de aprovação/edição de stage_reviews"*. Documenta:
> - Decisão de tornar revisão **explícita** vs. implícita (caminho A).
> - Editor JSON adotado (Monaco vs. textarea-com-validação).
> - Política de retenção de `original_output_json` + `edited_output_json` (já está no schema; documentar uso).
> - Fluxo de "rejeitar review" se for adicionado (hoje schema não tem `rejected`; decidir).
> **Supervisão:** **G4 (`product-designer`)** **obrigatório** (densidade de informação, hierarquia, estado vazio, copy de erros). **G2 (`data-engineer`)** se adicionar status novo no enum `StageReviewStatus`. **G0 (`financial-planner`)** opcional para decidir o que mostrar como "campo crítico" em outputs IRPF/E1.5/E1.6 (capacidade PGBL, dependentes, valores monetários).

> **Objetivo (1 frase):** entregar a UI que o backend já suporta — listar `StageReview` pendentes, mostrar `original_output_json` + `validation_errors`, permitir aprovar ou editar antes de retomar o run.

---

## Por que esta lane

### Contexto

O backend tem fluxo human-in-the-loop completo desde a Phase 4 do schema inicial ([alembic/versions/a1b2c3d4e5f6_phase4_llm_config_stage_review.py](../../backend/alembic/versions/a1b2c3d4e5f6_phase4_llm_config_stage_review.py)):

- Tabela `stage_reviews` ([backend/app/models/stage_review.py](../../backend/app/models/stage_review.py)) com `status: pending|approved|edited`, `original_output_json`, `edited_output_json`, `validation_errors`, `reviewer_notes`.
- Endpoints REST ([backend/app/api/pipeline.py:118-139](../../backend/app/api/pipeline.py:118)):
  - `GET /workspaces/{ws}/pipeline/runs/{run}/reviews` → list.
  - `POST /workspaces/{ws}/pipeline/runs/{run}/reviews/{review_id}` body `{action: "approve"|"edit", edited_output_json?, reviewer_notes?}`.
- Use cases prontos ([backend/app/application/pipeline_run/action_review.py](../../backend/app/application/pipeline_run/action_review.py), [resume_run.py](../../backend/app/application/pipeline_run/resume_run.py)). Resume só é aceito quando `count(stage_reviews where status=pending) == 0`.
- Helpers TS prontos ([frontend/src/lib/api/pipeline.ts:138-152](../../frontend/src/lib/api/pipeline.ts:138)).
- **Nenhum componente da UI consome esses endpoints** — `NeedsReviewCard` ([frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx](../../frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx)) só renderiza um banner com botão que vai direto para `/resume` (e bate em 409).

Esta lane fecha esse gap.

### Stages com `is_llm=True` que podem cair em `needs_review`

Lista atualizada em [pipeline/stage_spec.py](../../pipeline/stage_spec.py):

- E1 — `extract_documents`
- E1.5 — `consolidate_baseline`
- **E1.6 — `extract_irpf_full`** (gatilho que motivou esta lane)
- E2-llm — variantes LLM de `extract_statements`
- (qualquer outro stage com `is_llm=True` registrado — verificar `STAGE_REGISTRY`)

A UI deve **não assumir** estrutura específica do `original_output_json` por stage — tratar como JSON genérico, com hint visual quando campos importantes (decimais, datas) aparecem. Tipagem específica por stage pode vir em follow-up.

---

## Regras inegociáveis

1. **Tokens, nada de hex literal** ([ADR-076](../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)): cores via `var(--brand-*)`, `var(--surface-*)`, `var(--semantic-*)`. Estado de erro de schema é `--semantic-warning`, **não** `--semantic-loss` (não é falha catastrófica; é dado para revisão).
2. **`<MonetaryValue/>`** ([frontend/src/components/report/MonetaryValue.tsx](../../frontend/src/components/report/MonetaryValue.tsx)) para qualquer BRL renderizado em destaque. Em editor JSON, valores ficam como string crua (formato wire) — não formatar na borda do editor.
3. **Sem `any`** ([CLAUDE.md §Code style › Tipos](../../CLAUDE.md)). `unknown` para conteúdo do JSON, narrow no boundary.
4. **Sem mock de DB** em testes ([CLAUDE.md §Testes](../../CLAUDE.md)). E2E real Playwright + Vitest com fakes nomeados em `frontend/src/test/fakes/`.
5. **Acessibilidade WCAG 2.1 AA** — keyboard nav no editor, contraste, screen reader labels nos campos do JSON tree, `aria-invalid` quando edição ainda não validou.
6. **Pipeline core não toca** — esta lane é só frontend + 1 ajuste de contrato (ver §C abaixo).
7. **Idempotência** — reaprovar um review já aprovado retorna 409 do backend ([action_review.py:26](../../backend/app/application/pipeline_run/action_review.py:26)). UI trata como warning ("Já processado") e atualiza estado local.
8. **Edição não valida client-side** — o usuário pode salvar um JSON que continua falhando schema; o backend aceita `edited_output_json` arbitrário e o pipeline downstream re-valida. Mostrar warning *"Edição não validada — schema só será re-checado quando o pipeline retomar"* mas **permitir salvar mesmo assim**.

---

## Entregáveis

### A. Tipos TS estritos em `frontend/src/lib/api/pipeline.ts`

(Igual ao caminho A — se A foi mergeado, já está feito; reaproveitar.)

```ts
export type StageReviewStatus = "pending" | "approved" | "edited";

export interface StageReviewResponse {
  id: string;
  pipeline_run_id: string;
  stage: string;
  status: StageReviewStatus;
  original_output_json: Record<string, unknown> | null;
  edited_output_json: Record<string, unknown> | null;
  validation_errors: string | null;
  reviewer_notes: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface StageReviewActionRequest {
  action: "approve" | "edit";
  edited_output_json?: Record<string, unknown>;
  reviewer_notes?: string;
}
```

`listStageReviews` e `submitStageReview` retornam tipos nominais (não `unknown[]`).

### B. Rota `/pipeline/runs/[runId]/reviews`

Estrutura:

```
frontend/src/app/(app)/pipeline/runs/[runId]/reviews/
├── page.tsx                              # lista
├── [reviewId]/
│   └── page.tsx                          # detalhe + ações
└── _components/
    ├── ReviewListItem.tsx
    ├── ReviewDetailHeader.tsx
    ├── ValidationErrorsPanel.tsx
    ├── JsonViewer.tsx                    # read-only tree
    ├── JsonEditor.tsx                    # editable
    └── ReviewActions.tsx                 # Aprovar / Editar / Cancelar
```

#### `/pipeline/runs/[runId]/reviews` — lista

- Header: *"Revisões pendentes — Run <abreviado>"*.
- Se `pendingReviews.length === 0` e run.status === "completed/running" → redireciona para `/pipeline`.
- Cada item: stage (nome humano via `stageName(...)`), `created_at`, badge de status, primeiros 80 chars de `validation_errors`. Click abre detalhe.

#### `/pipeline/runs/[runId]/reviews/[reviewId]` — detalhe

Layout em duas colunas (desktop, single column mobile):

- **Esquerda — original**: `JsonViewer` mostrando `original_output_json` em tree colapsável. Highlight em campos referenciados em `validation_errors` (parse heurístico — extrair `$.path` ou `field_name` da string, melhor esforço; se não conseguir parse, sem highlight).
- **Direita — ações**:
  - `ValidationErrorsPanel`: lista os erros (split de `validation_errors` por `\n`), cada um clicável → scroll para campo no viewer (se highlight bateu).
  - Textarea opcional `Notas do revisor` (`reviewer_notes`).
  - Botões:
    - **Aprovar como está** (`action: "approve"`)
    - **Editar e aprovar** → abre `JsonEditor` (tree-style editor ou Monaco — decidir com G4) pré-preenchido com `original_output_json`. Submit envia `action: "edit"` + `edited_output_json`.
    - **Voltar** (cancela edição local).
- Após sucesso → toast + redireciona para a lista. Quando lista esvaziar (todos aprovados/editados), redireciona para `/pipeline` com flash *"Revisões concluídas. Pipeline retomado."* — frontend chama `resumePipelineRun` automaticamente.

### C. `NeedsReviewCard` vira ponteiro para a tela

Substituir o botão "Aprovar e Continuar" do [NeedsReviewCard.tsx](../../frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx) por:

- Title: *"<N> revisão(ões) pendente(s) na etapa <stage>"*.
- Texto: *"O resultado automático precisa ser conferido antes de seguir. Abra a revisão para ver os erros e decidir se aprova ou edita o output."*
- Botão primário: **"Revisar agora"** → `router.push('/pipeline/runs/{runId}/reviews')`.
- Botão secundário: **"Cancelar execução"**.

`handleResume` em [page.tsx](../../frontend/src/app/(app)/pipeline/page.tsx) **deixa de existir** — retomada agora é consequência implícita de aprovar todos os reviews via tela dedicada. Se o caminho A foi mergeado antes desta lane, **remova** a auto-approve loop.

### D. Editor JSON

**Decisão entre 2 opções (a definir com G4):**

- **(D1) `<textarea>` + `JSON.parse` no submit + `react-error-boundary`** — zero deps, 30 LOC, sem syntax highlight. Para edição rápida basta. **Recomendado para v1.**
- **(D2) `@monaco-editor/react`** — IDE-grade, syntax highlight, formatação. Bundle ~300KB extra. Justifica se houver expectativa de edições densas.

**Default**: D1 com syntax-highlighting via `<pre>` ou lib leve (`prismjs` se já estiver no bundle). Se G4 priorizar UX rica, escalar para D2 + ADR de bundle size.

### E. Estados de loading/erro/vazio

- **Loading lista**: skeleton (3 cards).
- **Erro carregamento**: card de erro com botão *"Tentar de novo"*.
- **Vazio**: estado *"Nenhuma revisão pendente."* + link de volta para `/pipeline`.
- **Concorrência**: outro agente/aba já aprovou → 409 *"Review já processado"* → UI faz refetch e mostra estado atual; toast informativo, não erro.

### F. Testes

- **Vitest** (`frontend/src/app/(app)/pipeline/runs/[runId]/reviews/__tests__/`):
  - lista renderiza pending vs já aprovados.
  - detalhe carrega `original_output_json` no viewer.
  - submit aprovar chama `submitStageReview` com `action:"approve"`.
  - submit editar serializa edição válida; bloqueia submit se JSON inválido.
  - 409 em concorrência → estado atualizado, toast informativo.
- **Playwright** (`frontend/e2e/pipeline-review-screen.spec.ts`, marcar `@critical`):
  - Seed: run em `needs_review` com 2 reviews pending.
  - Navega `/pipeline` → click "Revisar agora" → assert lista com 2 itens.
  - Aprova primeiro → contador desce para 1.
  - Edita segundo (modifica 1 campo do JSON) → submete → assert run volta a `running`/`completed`.
  - Volta para `/pipeline` → não há mais card `needs_review`.

### G. ADR

`docs/DECISIONS.md` ganha ADR nova (próximo número livre — confira em [docs/DECISIONS.md ToC](../DECISIONS.md)). Conteúdo mínimo:

- **Contexto**: backend já tem fluxo de review desde Phase 4; UI estava incompleta; A foi stop-gap.
- **Decisão**: revisão explícita (lista + detalhe + editor) substitui aprovação implícita.
- **Alternativas consideradas**: (i) caminho A permanente; (ii) editor inline no `NeedsReviewCard`; (iii) Monaco vs textarea.
- **Consequências**: usuário precisa de ≥1 click extra; outputs editados ficam rastreáveis em `edited_output_json`.
- **Reversibilidade**: alta — basta voltar `NeedsReviewCard` para auto-approve.
- Rodar gates de ADR ([CLAUDE.md §ADRs](../../CLAUDE.md)):
  ```bash
  python3 dev/check_adr_anchors.py
  python3 dev/build_adr_toc.py --inline
  python3 dev/validate_adr_format.py
  ```

### H. (opcional) Endpoint `GET /reviews/{review_id}`

Hoje o frontend precisa carregar a lista inteira para encontrar 1 review. Adicionar:

```python
@router.get("/runs/{run_id}/reviews/{review_id}", response_model=StageReviewResponse)
async def get_review(...): ...
```

Se adicionar, atualizar `make update-openapi-snapshot` ([ADR-109](../DECISIONS.md#adr-109)) e commitar o diff.

**Decisão**: adicionar é higiênico, mas não bloqueia. Lista cacheada em React Query/state local resolve. Default: **não adicionar** nesta lane.

---

## Gate

```bash
cd frontend
npm test -- --run                          # vitest
npm run test:e2e -- --grep review-screen   # playwright @critical
cd ..

pre-commit run --all-files

# Backend pode não mudar; se mudou (caso H):
pytest backend/tests -q
make update-openapi-snapshot
```

---

## Sequência

```bash
git fetch origin
git checkout -b agent/pipeline-review-screen/$(date +%Y%m%d-%H%M)

# Implementação iterativa (commits por entregável):
# 1. Tipos pipeline.ts                         → commit "refactor(pipeline-api): tipos StageReview*"
# 2. Rota lista (page.tsx)                     → commit "feat(pipeline): tela de revisões pendentes"
# 3. Rota detalhe + JsonViewer                 → commit "feat(pipeline): detalhe de StageReview"
# 4. Editor (D1)                               → commit "feat(pipeline): editor JSON em StageReview"
# 5. NeedsReviewCard vira ponteiro             → commit "refactor(pipeline): NeedsReviewCard → router.push"
# 6. handleResume removido (se A foi mergeado) → commit "refactor(pipeline): remove auto-approve A"
# 7. Vitest                                    → commit "test(pipeline): cobertura UI de StageReview"
# 8. Playwright                                → commit "test(e2e): pipeline-review-screen @critical"
# 9. ADR                                       → commit "docs: ADR-NNN — pipeline review screen"

cd frontend && npm test -- --run && cd ..
pre-commit run --all-files

# Pre-push drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && (cd frontend && npm test -- --run) && cd ..

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] `/pipeline/runs/[runId]/reviews` lista todos `StageReview` do run.
- [ ] `/pipeline/runs/[runId]/reviews/[reviewId]` mostra `original_output_json`, `validation_errors`, e ações.
- [ ] **Aprovar como está** funciona (POST com `action: "approve"`).
- [ ] **Editar e aprovar** funciona (POST com `action: "edit"` + `edited_output_json`).
- [ ] Após aprovar/editar todos os pending, frontend chama `resumePipelineRun` automaticamente e redireciona para `/pipeline`.
- [ ] `NeedsReviewCard` virou ponteiro para a tela (nada de aprovação implícita).
- [ ] Se A foi mergeado, a auto-approve loop em `handleResume` foi removida.
- [ ] Concorrência (409) tratada como estado atualizado + toast informativo, não erro.
- [ ] Tipos: zero `any` adicionado; `StageReviewResponse[]` substitui `unknown[]`.
- [ ] WCAG AA: contraste, keyboard nav, `aria-invalid` em editor.
- [ ] Vitest verde; Playwright `@critical` verde.
- [ ] ADR aberta + 3 gates verdes (anchors, ToC, format).
- [ ] Sign-off **`product-designer`** registrado no PR (screenshots de lista, detalhe, editor, estado vazio).
- [ ] Sign-off **`data-engineer`** se enum `StageReviewStatus` ganhou valor novo (não previsto neste escopo, mas se acontecer).

---

## Anti-padrões

- ❌ Não esconda `validation_errors` numa modal — usuário precisa ver junto do JSON.
- ❌ Não pré-valide `edited_output_json` contra schema no client. Re-validação é responsabilidade do pipeline downstream (ADR-097).
- ❌ Não duplique a lógica de revisão dentro do `NeedsReviewCard`. Tela dedicada é a fonte única.
- ❌ Não chame `resumePipelineRun` enquanto houver pending — backend recusa. Só chame quando contagem zerar.
- ❌ Não importe Monaco se ficar com D1 — bundle inflado sem justificativa é débito.
- ❌ Não adicione `rejected` no enum `StageReviewStatus` sem ADR específica + sign-off `data-engineer`. Hoje só existe `pending|approved|edited`.
- ❌ Não toque em `pipeline/**/*.py` (boundary, [CLAUDE.md §Pipeline não importa framework](../../CLAUDE.md)).
- ❌ Não use cor literal nem `Intl.NumberFormat` inline para BRL.

---

## Pós-merge / follow-ups possíveis

1. **Tipagem por stage**: hoje `original_output_json` é `Record<string, unknown>`. Em follow-up, gerar tipos a partir de `config/schemas/*.schema.json` (codegen estilo [ADR-076](../DECISIONS.md#adr-076)) e narrow no detalhe por `review.stage`.
2. **Diff visual**: quando `edited_output_json` foi aplicado, mostrar diff lado a lado com `original_output_json` no histórico.
3. **`rejected` status**: discutir com `financial-planner` — usuário pode "rejeitar" um review e marcar o run como falho? Hoje só pode aprovar (com ou sem edit).
4. **Métricas LLMOps**: contar % de reviews aprovados vs editados por stage — sinal de qualidade do prompt LLM. Provavelmente vira lane separada (FinOps + LLMOps).

---

## Referências

- [ADR-076 — Design tokens unificados site + relatório](../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)
- [ADR-097 — Validação de stages LLM e dataclasses tipadas](../DECISIONS.md#adr-097)
- [ADR-109 — `response_model` explícito + OpenAPI snapshot](../DECISIONS.md#adr-109)
- [ADR-157 — Schema IRPF completo (extract_irpf_full)](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)
- [Backend `action_review` use case](../../backend/app/application/pipeline_run/action_review.py)
- [Backend `resume_run` use case](../../backend/app/application/pipeline_run/resume_run.py)
- [Backend pipeline router](../../backend/app/api/pipeline.py)
- [Frontend API helpers](../../frontend/src/lib/api/pipeline.ts)
- [Frontend `NeedsReviewCard`](../../frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx)
- Lane antecessora (caminho A, opcional): [track_pipeline_review_quick_unblock.md](track_pipeline_review_quick_unblock.md)
