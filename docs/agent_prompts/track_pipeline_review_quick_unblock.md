# Track Pipeline Review — Quick Unblock (caminho A)

> **Lane ID:** pipeline-review-quick-unblock
> **Branch prefix:** `agent/pipeline-review-quick-unblock/*`
> **Depende de:** nada (toca só frontend + 1 ajuste opcional de copy)
> **Conflita com:** [track_pipeline_review_screen.md](track_pipeline_review_screen.md) — **mutuamente exclusivo**: A é o stop-gap; B é a versão completa. Se B já está em andamento (`origin/agent/pipeline-review-screen/*` com commit recente), **abandone A**.
> **Onda:** independente / hotfix de UX
> **ADR:** **não obrigatória** — comportamento já está implícito em [ADR-097 D1](../DECISIONS.md#adr-097) (validação LLM com pause). Se a copy for revisada com `product-designer` e mudar a semântica de "aprovar" (ex.: passar a registrar `reviewer_notes` automático), abrir ADR.
> **Supervisão:** **G4 (`product-designer`)** **obrigatório** — copy nova precisa ser honesta e não prometer revisão visual que não existe. **G0 (`financial-planner`)** opcional para o texto que explica o impacto de aprovar dado financeiro com erro de schema.

> **Objetivo (1 frase):** destravar runs presos em `needs_review` aprovando os `StageReview` pendentes implicitamente quando o usuário clica "Aprovar e Continuar", e tornar a copy honesta sobre o que está sendo aprovado.

---

## Por que esta lane

### Sintoma reproduzido

1. Usuário sobe documentos, dispara pipeline.
2. Stage `extract_irpf_full` (E1.6) executa, retorna `success=true` mas com `validation.valid=false` (output do LLM falha JSON Schema).
3. [`backend/app/tasks/pipeline_task.py:845`](../../backend/app/tasks/pipeline_task.py:845) detecta `_has_validation_errors(result)` e chama `_record_stage_needs_review` ([linha 687](../../backend/app/tasks/pipeline_task.py:687)):
   - Cria 1 linha em `stage_reviews` com `status=pending`.
   - Marca `pipeline_runs.status=needs_review`, `paused_at_stage='extract_irpf_full'`.
4. Frontend ([`frontend/src/app/(app)/pipeline/page.tsx:348`](../../frontend/src/app/(app)/pipeline/page.tsx:348)) renderiza [`NeedsReviewCard`](../../frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx) com botão **Aprovar e Continuar**.
5. Click → [`handleResume`](../../frontend/src/app/(app)/pipeline/page.tsx:273) chama `resumePipelineRun` → `POST /workspaces/{ws}/pipeline/runs/{id}/resume`.
6. Backend ([`backend/app/application/pipeline_run/resume_run.py:21-30`](../../backend/app/application/pipeline_run/resume_run.py:21)) recusa: *"Existem reviews pendentes. Aprove ou edite antes de continuar."* → 409 Conflict.
7. Toast de erro. Run permanece travado. **Não há UI para aprovar reviews individuais.**

### Por que isso entrou no projeto

- Schema `stage_reviews` faz parte do design desde a Phase 4 do schema inicial ([alembic/versions/a1b2c3d4e5f6_phase4_llm_config_stage_review.py](../../backend/alembic/versions/a1b2c3d4e5f6_phase4_llm_config_stage_review.py), 2026-04-14). Conceito é human-in-the-loop para LLMOps: pausar antes de empurrar dado mal-validado para o relatório.
- Endpoints `GET /reviews` e `POST /reviews/{id}` existem ([`backend/app/api/pipeline.py:118-139`](../../backend/app/api/pipeline.py:118)) e helpers `listStageReviews`/`submitStageReview` já estão no frontend ([`frontend/src/lib/api/pipeline.ts:138-152`](../../frontend/src/lib/api/pipeline.ts:138)) — **mas nenhum componente os consome**.
- Stage `extract_irpf_full` só foi registrado no orchestrator em 2026-05-01 ([commit `b0024c7`](https://github.com/anthropics/apps)). Antes disso, esse caminho quase nunca disparava em produção. Agora dispara, e o gate ficou exposto.

### Caminho A vs B

- **A (esta lane)** = stop-gap pragmático. Auto-aprova todos os pending reviews quando o usuário clica "Aprovar e Continuar", e ajusta copy para refletir a verdade (não há revisão visual; usuário está aprovando às cegas com aviso de que houve erro de validação). Resolve o bloqueio em ~1h.
- **B** = tela de revisão real (lista StageReviews, mostra `original_output_json` + `validation_errors`, editor para `edited_output_json`, ações Aprovar/Editar). Resolve corretamente, mas exige ~1 dia + sign-off `product-designer` denso.

A é **descartável**: B substitui A por completo. **Se B for entregue**, a lógica de A em `handleResume` deve ser removida (não vale manter dois caminhos).

---

## Regras inegociáveis

1. **Sem mocks de DB**: testes Vitest não precisam tocar backend; teste e2e Playwright (se adicionado) usa o ambiente dev real (CLAUDE.md §Testes).
2. **Tipos estritos**: `submitStageReview` retorna `unknown` hoje; ao consumir o result, narrow ou ignore — **não use `any`**.
3. **Copy honesta**: a UI **não** pode dizer "Revise os resultados antes de aprovar" se não há nada renderizado para revisar. Substituir por copy que (a) avisa que houve falha de validação, (b) lista os campos com erro (vindos de `validation_errors`), (c) deixa claro que aprovar avança com o output como está.
4. **Mensagem de erro útil**: se `submitStageReview` ou `resumePipelineRun` falhar, o toast precisa mostrar a mensagem do backend (`ApiError.detail`), não "Erro ao retomar".
5. **Idempotência**: clicar "Aprovar e Continuar" duas vezes não pode duplicar approve nem 500. Backend já retorna 409 *"Review já processado"* em re-approve ([`action_review.py:26`](../../backend/app/application/pipeline_run/action_review.py:26)) — frontend deve tratar como sucesso silencioso (já aprovado) e prosseguir para `resumePipelineRun`.

---

## Entregáveis

### A. Tipo TS para `StageReview` em `frontend/src/lib/api/pipeline.ts`

`listStageReviews` retorna `unknown[]` hoje. Trocar para tipo nominal:

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

export async function listStageReviews(
  workspaceId: string,
  runId: string
): Promise<StageReviewResponse[]> {
  return apiFetch(`/workspaces/${workspaceId}/pipeline/runs/${runId}/reviews`);
}
```

`submitStageReview` ganha tipo do request body também:

```ts
export interface StageReviewActionRequest {
  action: "approve" | "edit";
  edited_output_json?: Record<string, unknown>;
  reviewer_notes?: string;
}

export async function submitStageReview(
  workspaceId: string,
  runId: string,
  reviewId: string,
  data: StageReviewActionRequest
): Promise<StageReviewResponse> { ... }
```

(Shape backend: [`backend/app/schemas/pipeline.py:50-75`](../../backend/app/schemas/pipeline.py:50).)

### B. `handleResume` aprova pending reviews antes de retomar

Em [`frontend/src/app/(app)/pipeline/page.tsx`](../../frontend/src/app/(app)/pipeline/page.tsx), alterar `handleResume` (linhas 273-285):

```ts
async function handleResume() {
  if (!activeRun) return;
  setResuming(true);
  try {
    // 1. Auto-approve all pending reviews (caminho A: aprovação implícita)
    const reviews = await listStageReviews(workspace.id, activeRun.id);
    const pending = reviews.filter((r) => r.status === "pending");
    for (const r of pending) {
      try {
        await submitStageReview(workspace.id, activeRun.id, r.id, {
          action: "approve",
          reviewer_notes: "Auto-aprovado via 'Aprovar e Continuar'",
        });
      } catch (err) {
        // 409 "Review já processado" → segue (race entre 2 abas)
        if (!(err instanceof ApiError && err.status === 409)) throw err;
      }
    }

    // 2. Resume run
    await resumePipelineRun(workspace.id, activeRun.id);
    toast.success("Pipeline retomado", { duration: 3000 });
    await reload();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.detail : "Erro ao retomar pipeline");
  } finally {
    setResuming(false);
  }
}
```

Imports a adicionar no topo de `page.tsx`: `listStageReviews`, `submitStageReview` de `@/lib/api/pipeline` (`resumePipelineRun` já está importado).

### C. Copy honesta + erros de validação no `NeedsReviewCard`

`NeedsReviewCard` precisa receber as `validation_errors` para mostrar e o `runId` continua suficiente para o `id` âncora.

**Decisão de design (alinhar com G4 antes de codar):**

- Trocar título *"Aguardando sua confirmação"* por *"Erros de validação na etapa <stage>"*.
- Trocar parágrafo *"para que você revise antes de continuar"* por *"O resultado automático teve <N> erro(s) de validação. Você pode aprovar mesmo assim e continuar — o relatório vai usar o output como está — ou cancelar e reprocessar."*
- Adicionar `<details>` (expandido por default se ≤3 erros, colapsado se mais) listando os erros como `<ul>` em `font-mono text-xs`.
- Mudar texto do botão de **"Aprovar e Continuar"** para **"Aprovar mesmo assim e continuar"** — torna o trade-off explícito.
- Manter botão secundário **"Cancelar execução"** que chama `handleCancel` (hoje só existe no `ActiveRunCard`; reaproveitar componente ou duplicar handler local).

**Shape do componente (sugestão; G4 ajusta):**

```tsx
export function NeedsReviewCard({
  runId,
  pausedAtStage,
  pendingReviews,           // novo: StageReviewResponse[] do server
  resuming,
  cancelling,
  onResume,
  onCancel,
}: {
  runId: string;
  pausedAtStage: string | null;
  pendingReviews: StageReviewResponse[];
  resuming: boolean;
  cancelling: boolean;
  onResume: () => void;
  onCancel: () => void;
}) { ... }
```

`page.tsx` precisa carregar `pendingReviews` no mesmo useEffect que faz polling, ou em um `useEffect` dedicado disparado quando `activeRun?.status === "needs_review"`. Cache local em `useState<StageReviewResponse[]>([])`.

### D. Teste Vitest do componente

Adicionar `frontend/src/app/(app)/pipeline/_components/__tests__/NeedsReviewCard.test.tsx`:

- Renderiza título e mensagem.
- Quando `pendingReviews[0].validation_errors` é não-nulo, renderiza lista de erros (split por `\n`).
- Click em "Aprovar mesmo assim" chama `onResume`.
- Botão fica disabled e mostra spinner quando `resuming=true`.
- Click em "Cancelar" chama `onCancel`.

### E. Teste e2e Playwright (opcional, mas recomendado)

`frontend/e2e/pipeline-needs-review.spec.ts` — fluxo `@critical`:

1. Seed: workspace com run em `needs_review` + 1 stage_review pending (provavelmente factory ou hit DB diretamente; seguir padrão dos outros e2e em `frontend/e2e/`).
2. Navegar para `/pipeline`.
3. Assert que card de erro aparece com texto novo.
4. Clicar "Aprovar mesmo assim e continuar".
5. Aguardar toast "Pipeline retomado".
6. Assert que run volta a `running` ou `completed`.

Se for caro montar fixtures, **pule este passo** e marque no PR como follow-up.

---

## Gate

```bash
cd frontend
npm test -- --run                      # vitest verde
npm run test:e2e -- --grep needs-review  # se adicionou e2e
cd ..
pre-commit run --all-files
```

---

## Sequência

```bash
git fetch origin
git checkout -b agent/pipeline-review-quick-unblock/$(date +%Y%m%d-%H%M)

# Implementação:
# 1. Tipos em frontend/src/lib/api/pipeline.ts
# 2. handleResume em frontend/src/app/(app)/pipeline/page.tsx
# 3. Copy + props em NeedsReviewCard.tsx
# 4. Teste Vitest

cd frontend && npm test -- --run && cd ..
pre-commit run --all-files

git add frontend/src/lib/api/pipeline.ts \
        frontend/src/app/\(app\)/pipeline/page.tsx \
        frontend/src/app/\(app\)/pipeline/_components/NeedsReviewCard.tsx \
        frontend/src/app/\(app\)/pipeline/_components/__tests__/

git commit -m "fix(pipeline): destrava needs_review aprovando StageReview implicitamente

Quando a UI mostrava 'Aguardando sua confirmação', o botão 'Aprovar e
Continuar' chamava /resume direto, mas o backend recusa enquanto há
StageReview com status=pending. Como nenhum componente da UI consumia
os endpoints /reviews, runs ficavam presos no estado.

Solução A (stop-gap): handleResume aprova todos os pending reviews via
POST /reviews/{id} {action:approve} antes de chamar /resume. Copy do
NeedsReviewCard reescrita para refletir que aprovação é cega e mostra
validation_errors.

Solução B (tela de revisão real, ADR-pendente) substitui esta lógica."

# Pre-push drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && (cd frontend && npm test -- --run) && cd ..

git push origin HEAD:main
```

---

## Critérios de aceite

- [ ] Run em `needs_review` retoma com sucesso ao clicar o botão (verificado dev local com seed real ou com `extract_irpf_full` rodando contra um IRPF que falhe schema).
- [ ] Card mostra `validation_errors` formatados (lista monoespaçada).
- [ ] Botão renomeado para *"Aprovar mesmo assim e continuar"*.
- [ ] Botão **Cancelar execução** disponível no card e funcional.
- [ ] `submitStageReview` em re-aprovação (409) é tratado como sucesso silencioso.
- [ ] Tipos estritos: zero `any` adicionado, `unknown[]` substituído por `StageReviewResponse[]`.
- [ ] Toast de erro mostra `ApiError.detail` quando backend recusa.
- [ ] Vitest verde; pre-commit verde.
- [ ] Sign-off **`product-designer`** registrado no PR (snippet de copy + screenshot do card).

---

## Anti-padrões

- ❌ Não chame `resumePipelineRun` antes de aprovar reviews — backend recusa.
- ❌ Não esconda o erro do backend no toast com texto genérico ("Erro ao retomar"). Use `ApiError.detail`.
- ❌ Não invente UI de edição de output aqui — isso é escopo de B (`track_pipeline_review_screen.md`).
- ❌ Não mexa em `backend/app/application/pipeline_run/resume_run.py`. O gate de "pending reviews" está correto; a UI é que estava incompleta.
- ❌ Não mude o stage `extract_irpf_full` para parar de gerar `validation_errors` — isso é regra de domínio (ADR-097, ADR-157) e a falha é sinal legítimo de output mal-formado.
- ❌ Não remova a feature flag de tier (`tier == "free"` skip de LLM) nem mexa no fluxo do orchestrator.

---

## Referências

- [ADR-097 — Validação de stages LLM e dataclasses tipadas](../DECISIONS.md#adr-097)
- [ADR-157 — Schema IRPF completo (extract_irpf_full)](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)
- [Backend `resume_run` use case](../../backend/app/application/pipeline_run/resume_run.py)
- [Backend `action_review` use case](../../backend/app/application/pipeline_run/action_review.py)
- [Frontend `NeedsReviewCard`](../../frontend/src/app/(app)/pipeline/_components/NeedsReviewCard.tsx)
- [Frontend `handleResume`](../../frontend/src/app/(app)/pipeline/page.tsx)
- Lane sucessora (caminho B): [track_pipeline_review_screen.md](track_pipeline_review_screen.md)
