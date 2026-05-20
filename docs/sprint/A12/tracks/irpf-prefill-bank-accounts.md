---
id: TRACK-irpf-prefill-bank-accounts
type: track
title: "Track IRPF pre-fill V1 — contas bancárias (2 PRs sequenciais)"
sprint: A12
lane: "[[A12.irpf-prefill-bank-accounts]]"
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/backend
  - area/frontend
---

# Track IRPF pre-fill V1 — 2 PRs sequenciais

> **Lane:** [[A12.irpf-prefill-bank-accounts]] · **ADR canônica:** [[ADR-229]]
> · **Branch prefix:** `agent/irpf-prefill-bank-accounts-pr<N>/*`
> · **Pré-requisito externo:** Sprint A13 deve estar `current` (lane deferred — `status: planned`)
> · **Supervisão obrigatória:** **product-designer** revisa PR2 (UI cards + diff modal + a11y); **senior-cto** revisa PR1 (endpoint + use case + boundary pipeline↔backend); **data-engineer** revisa migration (PR1).

## Briefing (1 frase)

Executar os 2 PRs sequenciais de [[ADR-229]] — endpoint `suggestions-from-irpf` lendo artifact E1 + UI cards inline com diff modal de conflito IRPF↔manual + dismissals + a11y.

## Por que ler [[ADR-229]] antes de codar

ADR-229 é o plano: §Decisão lista as 7 mudanças coordenadas (source_tier promoção pelo clique humano, conflito IRPF↔manual com diff inline, tabela dismissals, endpoint genérico, saldo timeline metadata, UI cards inline, omissão fiscal V2-deferred). §Follow-ups V2 delimita escopo (V1 só código 61; membros/imóveis/investimentos reutilizam pattern). §Riscos mapeia mitigações enforçadas em código. **Não duplique conteúdo da ADR neste track.**

## PR1 — Backend (~1d)

**Migration nova** `<rev>_irpf_prefill_dismissals_and_snapshots.py`:

```python
def upgrade():
    op.create_table(
        "workspace_irpf_suggestion_dismissals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36),
                  sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("irpf_year", sa.Integer(), nullable=False),
        sa.Column("institution_code", sa.String(50), nullable=False),
        sa.Column("account_number_norm", sa.String(30), nullable=True),
        sa.Column("member_key", sa.String(50), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("workspace_id", "irpf_year", "institution_code",
                            "account_number_norm", name="uq_workspace_irpf_dismissal"),
    )
    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(sa.Column("irpf_snapshots", sa.JSON(), nullable=True))
```

**Endpoint** `backend/app/api/family_members.py`:

```python
@router.get("/members/suggestions-from-irpf", response_model=SuggestionsFromIrpfResponse)
async def get_suggestions_from_irpf(...) -> SuggestionsFromIrpfResponse:
    return await get_irpf_suggestions(workspace_id=workspace.id, repo=repo, store=store)
```

**Use case** `backend/app/application/family_member/get_irpf_suggestions.py` — puro com fakes; lê artifact E1 via store injetado, parseia `contas[]`, classifica como `new` ou `partial_collision`, filtra dismissals.

**DTOs** `backend/app/schemas/dto/family_member/response.py`:
- `IrpfSuggestionItem`
- `SuggestionsFromIrpfResponse`

**Telemetria** `pipeline/domain/services/account_resolver.py` já emite log estruturado; adicionar 4 eventos novos em `backend/app/api/family_members.py` (handler do endpoint):
- `mathoms.irpf_suggestions.shown` (count + irpf_year)

E após "Adicionar" (POST `/members/{id}/accounts`) detectar via DTO se origem é IRPF (campo `_origem_irpf: bool` no command, opcional):
- `mathoms.irpf_suggestions.accepted` (match_kind + irpf_year)

E em endpoint dismissal:
- `mathoms.irpf_suggestions.dismissed` (irpf_year)

Re-add detection (sugestão dismissed mesma key recriada como BankAccount): pós-create, query dismissals — se match, emite:
- `mathoms.irpf_suggestions.dismissed_then_re_added` (irpf_year — sinal precisão LLM)

**OpenAPI snapshot**: `make update-openapi-snapshot`.

**Tests novos** `backend/tests/test_irpf_suggestions_use_case.py`:
- 5 cases: sem artifact E1 → suggestions=[], todos new, todos com partial_collision, todos dismissed, mix
- Idempotência: re-upload mesmo IRPF ano-base não duplica
- Multi-ano: IRPF 2025 + 2024 carregados → timeline ordenada

**Validação:**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_irpf_suggestions_use_case.py -q
pytest backend/tests -q
make update-openapi-snapshot && git diff docs/reference/api/v1/openapi.json | head
pre-commit run --all-files
```

**Commit:** `feat(api): ADR-229 PR1 — endpoint suggestions-from-irpf + migration dismissals`

## PR2 — UI cards + diff modal + dogfood (~1d)

**API client** `frontend/src/lib/api/config.ts`:

```typescript
export interface IrpfSuggestion {
  institution_code: string;
  institution_label: string;
  account_type: string;
  agency?: string | null;
  account_number_raw?: string | null;
  account_number_norm?: string | null;
  member_key: string;
  member_full_name: string;
  cpf_titular_masked?: string | null;
  irpf_year: number;
  match_kind: "new" | "partial_collision";
  collision_with_account_id?: string | null;
}

export async function listIrpfSuggestions(workspaceId: string): Promise<{...}>;
export async function dismissIrpfSuggestion(workspaceId: string, ...): Promise<void>;
```

**UI** `frontend/src/app/(app)/config/MembersTab.tsx`:

- Carrega sugestões no `useEffect` paralelo ao `listMembers`.
- Renderiza grupo "Encontradas no seu IRPF YYYY" no fim de cada card de membro (filtrado por `member_key`).
- Card de sugestão (novo componente `_IrpfSuggestionCard.tsx`):
  - Background `var(--surface-subtle)`, badge `IRPF YYYY` em `var(--semantic-info)`.
  - CTA primário "Adicionar" verde.
  - Match parcial: badge âmbar + texto "Possível duplicata de…"
  - Botão X "Descartar".

**Diff modal** `_IrpfDiffModal.tsx` (novo componente):
- 2 colunas: "IRPF YYYY" vs "Você cadastrou".
- 2 CTAs: "Mesma conta (mantém manual)" + "Contas diferentes (cria as duas)".
- "Mesma conta" → `PATCH /accounts/{collision_with_account_id}` com `_irpf_history` aditivo no metadata.
- "Contas diferentes" → `POST /accounts` com `_origem_irpf: true`.

**Animação** pós-add: card migra do grupo de sugestões para o grupo de cadastrados (respeita `prefers-reduced-motion`).

**Toast** pós-add: `Conta {bank} {num} adicionada · Origem: IRPF {year} · Desfazer` (10s).

**A11y**:
- Cards `tabIndex={0}`, focus visible.
- Badge `aria-label="Sugestão do IRPF {year}"`.
- Toast `role="status"`.

**Mobile**: cards stackam, buttons full-width.

**Dogfood** com 3 famílias antes de roll-out 100%:
- Métrica: tempo médio cadastro completo < 2min (vs >10min manual).
- Feedback qualitativo: copy clara? Confiança IRPF? Falso-positivo?

**Tests E2E** `frontend/tests/components/MembersTab.irpfPrefill.test.tsx`:
- 3 cases: sugestão new aceita, sugestão partial → merge no diff modal, sugestão partial → cria separadas, dismiss + toast undo.

**Flip ADR-229:** `Proposto → Decidido (A13.irpf-prefill-bank-accounts)`.

**Validação:**

```bash
cd frontend && npm test -- --run
cd frontend && npm run test:e2e -- --grep "@irpf-prefill"
pytest backend/tests -q  # regressão
pre-commit run --all-files
```

**Commit:** `feat(frontend): ADR-229 PR2 — UI cards IRPF + diff modal + dogfood`

## Decisões já tomadas ([[ADR-229]] §Alternativas)

- **Source_tier promovido pelo clique humano** (não cria tier novo) — clique = tier 5.
- **Match parcial → card âmbar + diff modal** quando "Adicionar" — não mescla silenciosamente.
- **Saldo IRPF em coluna timeline `irpf_snapshots`** — não pre-fill no "saldo current".
- **Omissão fiscal silenciosa em V1** — V2 banner soft sem telemetria (LGPD).
- **V1 só código 61** (contas bancárias) — V2 reutiliza pattern para membros/imóveis/investimentos.
- **Cards inline no fim da lista** — não banner, não modal one-time.

## Ligações

- ADR canônica: [[ADR-229]] (Proposto)
- Lane: [[A12.irpf-prefill-bank-accounts]] (deferred → A13)
- Pré-requisito interno: [[ADR-226]] (mergeada em main)
- Pré-requisito externo: Sprint A13 `current`
- Relacionado: [[ADR-127]] (E1 extract_members), [[ADR-146]] (source_tier), [[ADR-157]] (E1.6 IRPF full — V2 imóveis), [[ADR-097]] (boundary pipeline↔backend), [[ADR-102]] (response_model)
