---
id: ADR-229
type: adr
title: "Pre-fill UI a partir de IRPF — pattern genérico `artifact → suggestion endpoint → card`; V1 contas bancárias"
status: Decidido
phase: A13.irpf-prefill-bank-accounts
date: "2026-05-20"
relates_to:
  - "[[ADR-127]]"
  - "[[ADR-146]]"
  - "[[ADR-157]]"
  - "[[ADR-226]]"
  - "[[ADR-097]]"
  - "[[ADR-102]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 228"
  - "IRPF pre-fill"
  - "suggestions-from-irpf"
tags:
  - area/methodology
  - area/persistence
  - area/backend
  - area/frontend
  - methodology/cerbasi
  - methodology/perini
  - methodology/auvp
  - phase/a13
  - status/decidido
  - type/adr
---

## Contexto

Pós [[ADR-226]] (decidida 2026-05-19), `/config` → Membros tem 4 campos por conta bancária (banco + tipo + agência + número). Família multi-membro típica × 4 bancos cada = ~12 contas digitadas à mão. Formulário longo, propenso a typo, é onde usuário desiste no onboarding.

A informação **já existe no Mathoms**: stage E1 ([[ADR-127]] `extract_members`) processa IRPF via LLM e grava artifact `members-1b_unified.json` com `contas[]` populado (pós-PR3 [[ADR-226]] §3). Schema do dict:

```json
{
  "members": [...],
  "contas": [
    {"member_key": "david", "institution_code": "itau",
     "account_number_norm": "123456", "account_number_raw": "12345-6",
     "account_type": "extratoconta", "agency": "1234", "is_joint": false}
  ]
}
```

A UI **não usa esse dado**. Pre-fill resolveria ~80% da fricção de cadastro para ICP que entrega IRPF (cenário comum: alta renda PJ/CLT que já declara IRPF anual).

## Decisão

Adotar **pattern genérico `artifact LLM → suggestion endpoint → UI card de pre-fill`** com 6 mudanças coordenadas. V1 cobre só contas bancárias (IRPF Ficha de Bens e Direitos código 61); membros/imóveis/investimentos são V2 follow-up reutilizando o mesmo pattern.

### 1. Source_tier promovido pelo clique humano (não cria tier novo)

[[ADR-146]] já define hierarquia: tier 1 (LLM raw) ... tier 5 (editorial). Decisão (co-design `financial-planner` 2026-05-20):

- Artifact E1 cru (extração LLM) = tier 1 default.
- **Clique do usuário em "Adicionar"** no card de sugestão = promoção para tier 5 (editorial).
- O clique humano é o que muda o tier, não a origem do dado.

Não criar tier intermediário (2/3) para IRPF. Adicionaria complexidade sem ganho — tier já decidido por `account_type` + `institution.parser` quando `source_tier IS NULL` ([[ADR-146]] §default Mathoms).

### 2. Conflito IRPF ↔ cadastro manual: filtro estrito + alerta âmbar + diff inline

Co-design 2026-05-20:

| Cenário | UI |
|---|---|
| Match exato `(institution_code, account_number_norm)` em cadastro existente | **Filtra no endpoint** — sugestão não aparece. |
| Match parcial: mesmo banco + titular, número diferente | Card com **badge âmbar** + texto "Possível duplicata de Itaú 98765 — confira antes de adicionar". |
| Sem match | Card normal verde "Adicionar 1-clique". |

Quando usuário clica "Adicionar" em card **âmbar**, abre modal de diff:

```
IRPF 2024 declara:        Você cadastrou:
  Itaú · Ag 1234            Itaú · Ag 1234
  Conta 12345-6             Conta 98765-0
  Titular David             Titular David

Estas são a mesma conta?
[ Mesma conta (mantém número manual) ]  [ Contas diferentes (cria as duas) ]
```

- "Mesma conta": **merge** — mantém número manual (tier 5 vence); grava IRPF como `irpf_history[]` no metadado da conta para audit-trail (AUVP Diagrama).
- "Contas diferentes": cria nova `BankAccount` com `account_number_norm` da sugestão; presume troca de conta (ex.: David trocou Itaú em mai/2025).

Sem diff inline, usuário **acumula lixo** após 2-3 anos de IRPFs (Cerbasi: diagnóstico íntegro perde força).

### 3. Tabela `workspace_irpf_suggestion_dismissals`

Persistência de descarte por workspace × irpf_year × `(institution_code, account_number_norm)`:

```sql
CREATE TABLE workspace_irpf_suggestion_dismissals (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  irpf_year INT NOT NULL,                  -- ano-base IRPF (declaração 2025 = ano-base 2024)
  institution_code VARCHAR(50) NOT NULL,
  account_number_norm VARCHAR(30) NULL,    -- digits-only ([[ADR-226]] §1)
  member_key VARCHAR(50) NULL,             -- contexto, opcional
  dismissed_at TIMESTAMPTZ NOT NULL,
  created_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT uq_workspace_irpf_dismissal
    UNIQUE (workspace_id, irpf_year, institution_code, account_number_norm)
);
```

Endpoint filtra dismissals ao retornar sugestões. Re-upload IRPF do **mesmo ano-base** não ressuscita dismissed (key `irpf_year` no UNIQUE).

### 4. Endpoint genérico `GET /workspaces/{ws}/family-members/suggestions-from-irpf`

Response tipado ([[ADR-102]] R18):

```python
class IrpfSuggestionItem(BaseModel):
    institution_code: str
    institution_label: str            # display name resolvido via institution_catalog
    account_type: str
    agency: Optional[str]
    account_number_raw: Optional[str]
    account_number_norm: Optional[str]
    member_key: str
    member_full_name: str              # resolved
    cpf_titular_masked: Optional[str]  # CPF do titular IRPF, mascarado (***.123.456-**)
    irpf_year: int
    match_kind: Literal["new", "partial_collision"]
    collision_with_account_id: Optional[str]  # quando partial — id da conta possivelmente duplicada


class SuggestionsFromIrpfResponse(BaseModel):
    irpf_year: int
    processed_at: datetime
    suggestions: list[IrpfSuggestionItem]
    total_filtered_exact_match: int     # contas IRPF já cadastradas (não vão para UI)
    total_dismissed: int                # dismissed previamente
```

Backend lê artifact E1 mais recente (`store.read("E1", "members")`), parseia `contas[]`, aplica filtros:

1. Match exato com cadastro existente → não inclui.
2. Match parcial → inclui com `match_kind="partial_collision"`.
3. Já dismissed → não inclui.
4. Sem match nem dismissed → inclui com `match_kind="new"`.

### 5. Saldo declarado IRPF como timeline anual (não pre-fill no "saldo current")

IRPF declara saldo em 31/dez do ano-base. Não usar para popular `saldo_atual`. Mas há valor pedagógico (Cerbasi snapshot anual + AUVP audit-trail patrimonial):

- Coluna nova `BankAccount.irpf_snapshots: JSONB` com `{2022: {saldo_brl: X, irpf_processed_at: ts}, 2023: {...}, 2024: {...}}`.
- Aba "Snapshots IRPF" no card detalhado da conta — timeline ordenada por ano.
- Quando E1 reprocessa IRPF novo ano-base, adiciona entrada (não sobrescreve anteriores).

V1 V0: só armazena, não renderiza. Renderização na UI fica em V2 (escopo separado).

### 6. UI: cards inline + descarte + sunset por uso real

Co-design `product-designer` 2026-05-20:

**Localização**: `/config` → Membros, no fim da lista de contas, dentro do card de cada membro (separado por divisor sutil).

**Cabeçalho do grupo**: "Encontradas no seu IRPF 2024 · processado em 12/03/2025" — atribui ao próprio usuário ("você declarou"), reduz percepção invasiva.

**Card de sugestão**:

```
┌─────────────────────────────────────────────────┐
│ [IRPF 2024]   Itaú · Ag 1234 · Conta 12345-6   │
│ Titular CPF ***.123.456-**                     │
│ [+ Adicionar]                  [✕ Descartar]   │
└─────────────────────────────────────────────────┘
```

- Background `var(--surface-subtle)` (cadastrados usam `--surface-elevated`).
- Badge "IRPF 2024" em `var(--semantic-info)`.
- CTA primário "Adicionar" verde; secundário ghost "Descartar".
- Animação: pós-add, card migra para grupo de cadastrados (respeita `prefers-reduced-motion`).

**Match parcial âmbar**:

```
┌─────────────────────────────────────────────────┐
│ [IRPF 2024]   Itaú · Ag 1234 · Conta 12345-6   │
│ ⚠ Possível duplicata de Itaú 98765-0           │
│ [+ Adicionar]                  [✕ Descartar]   │
└─────────────────────────────────────────────────┘
```

Clicar "Adicionar" abre modal de diff (§2).

**Descarte**: X individual → toast "Sugestão descartada · Desfazer" (5s). Persiste em `workspace_irpf_suggestion_dismissals`.

**Pós-add**:
- Toast "Conta Itaú 12345-6 adicionada · Origem: IRPF 2024 · Desfazer" (10s).
- Badge "IRPF" sutil na conta cadastrada **enquanto** `source_tier=5` AND sem transações reconciliadas. Some quando há transações (validada por uso real).
- Modal de edição da conta mostra campo "Origem: IRPF 2024" read-only + link "Como isso foi detectado?" → tooltip.

**A11y**:
- Cards navegáveis por teclado, badge com `aria-label="Sugestão do IRPF 2024"`.
- Toast com `role="status"`.
- Mobile: cards stackam, buttons full-width.

### 7. Detecção de omissão fiscal: V1 silenciosa, V2 banner soft

`financial-planner` apontou (Cerbasi + Perini): conta presente em extratos E2/E3 mas ausente do IRPF é sinal relevante (omissão patrimonial mina diagnóstico; renda passiva subdeclarada é problema fiscal).

Mas hard alert é invasivo (Mathoms julgando declaração) e tem **risco LGPD reputacional** se vazar telemetria "Mathoms detecta sonegação".

**V1**: silencioso. Zero detecção de omissão. Zero telemetria sobre essa dimensão.

**V2 (ADR follow-up)**: banner soft "Conta detectada nos extratos não consta no IRPF 2024: BTG 78910. Comum em conta aberta após 31/12/2024. Confirmar?" — descritivo, não acusatório. Telemetria mantém zero.

## Alternativas consideradas

- **(B) Source tier novo (2 ou 3) para IRPF**. Rejeitada: complexidade sem ganho operacional (FP 2026-05-20). Clique humano promove tier 1→5 é mais simples e correto semanticamente.
- **(C) Auto-mesclar conflito IRPF↔manual sem diff**. Rejeitada: usuário não vê o conflito acontecer (PD 2026-05-20). Diff modal expõe trade-off para decisão.
- **(D) Criar duas contas silenciosamente em qualquer conflito**. Rejeitada: acumula lixo após 2-3 IRPFs (FP). Match exato filtra; match parcial vira diff.
- **(E) Banner one-time no top da página**. Rejeitada: modal one-time é hostil (PD), perde info. Cards inline no fim da lista mantém contexto.
- **(F) Pre-fill no campo "Saldo atual"**. Rejeitada: dado defasado 6-18 meses (Perini); contamina decisão IF presente. Snapshots vão em coluna timeline separada.
- **(G) Alertar omissão fiscal em V1**. Rejeitada: invasivo + risco LGPD reputacional. V2 com banner soft se sinal de demanda aparecer.
- **(H) Implementar V1 com escopo completo (contas + membros + imóveis + investimentos)**. Rejeitada: escopo cresce 4×. V1 só código 61; pattern genérico documentado para V2.

## Consequências

**Positivas**

- ✅ Onboarding de família com IRPF: tempo médio cadastro < 2min (vs >10min manual) — gate de teste.
- ✅ `account_number_norm` discriminador vem populado por default → ambiguidade ADR-226 dissolve sem usuário precisar saber por quê.
- ✅ Pattern reutilizável: V2 reutiliza endpoint structure + UI card + dismissals table para membros/imóveis/investimentos.
- ✅ Audit-trail patrimonial via `irpf_snapshots` (Cerbasi snapshot anual + AUVP Diagrama).
- ✅ Source_tier policy simples: clique humano = tier 5, sem proliferação de tiers intermediários.
- ✅ Diff inline expõe conflito IRPF↔manual sem mesclar silenciosamente; usuário decide (Cerbasi diagnóstico íntegro).

**Negativas**

- ⚠️ Coluna `BankAccount.irpf_snapshots: JSONB` adiciona surface schema. Mitigação: opcional, V1 V0 só armazena (sem renderização).
- ⚠️ Tabela `workspace_irpf_suggestion_dismissals` adiciona surface schema. Mitigação: única responsabilidade clara; reutilizada por V2 (suggestion dismissals genéricas).
- ⚠️ UI complexity: cards inline + match âmbar + diff modal + toasts. Mitigação: PD aprovou; A11y + mobile cobertos.
- ⚠️ LLM falso-positivo descoberto após "Adicionar". Mitigação: badge "IRPF" sunset por uso real + toast com Undo 10s + telemetria `dismissed_then_re_added`.

**Riscos**

| Risco | P | Mitigação |
|---|---|---|
| Usuário cadastra sugestão errada e nunca descobre | P1 | Badge "IRPF" sutil pós-add com sunset por uso real; toast Undo 10s; campo "Origem: IRPF 2024" read-only no modal de edição. |
| Falsa duplicação de conta em diff modal (usuário confuso) | P2 | UX testada com 3 famílias dogfood antes de roll-out 100%. |
| `irpf_snapshots` JSONB cresce indefinido | P3 | Cap em 5 anos mais recentes (V1 V0); cleanup automático em V2. |
| Telemetria de "omissão detectada" vazar (LGPD) | P0 | V1 não detecta; V2 explícito sem telemetria. |
| Privacy: CPF mascarado em UI mas raw no artifact E1 | P1 | Artifact já é workspace-scoped + criptografado em DB (ADR-097). UI nunca renderiza CPF cru. |
| Re-extração LLM cara não-óbvia para usuário | P2 | Sem refresh button; novo IRPF dispara reprocessamento automático. |
| Workspace dogfood com IRPF antigo mostra sugestões obsoletas | P2 | Cabeçalho "IRPF 2024 · processado em 12/03/2025" explícita ano-base. |

## Gates

- **Migration Alembic** nova: `workspace_irpf_suggestion_dismissals` + `bank_accounts.irpf_snapshots JSONB NULL`. Downgrade reversível.
- **Endpoint** `GET .../suggestions-from-irpf` com `response_model=SuggestionsFromIrpfResponse` ([[ADR-102]] R18). `make update-openapi-snapshot` commitado.
- **Use case** `get_irpf_suggestions(workspace_id, repo, artifact_store)` puro em `backend/app/application/family_member/`, com fakes para tests.
- **Diff modal** modal-shape testado em `tests/components/MembersTab.diff.test.tsx` (3 cases: novo, match parcial → merge, match parcial → criar separadas).
- **Tests novos**: `tests/unit/backend/test_irpf_suggestions_use_case.py` (5 cases incluindo idempotência re-upload mesmo ano-base), `tests/e2e/test_irpf_prefill_flow.test.ts` (fluxo completo onboarding com IRPF mock).
- **Telemetria** estruturada em `backend/app/core/logging.py`:
  - `mathoms.irpf_suggestions.shown` (event + count + irpf_year)
  - `mathoms.irpf_suggestions.accepted` (event + match_kind + irpf_year)
  - `mathoms.irpf_suggestions.dismissed` (event + irpf_year)
  - `mathoms.irpf_suggestions.dismissed_then_re_added` (event + irpf_year — sinal precisão LLM)
  - **Zero telemetria sobre "omissão fiscal"** (LGPD).
- **A11y AAA**: cards teclado-navegáveis, badge `aria-label`, toast `role="status"`, contraste verificado.
- **Mobile**: cards stackam, buttons full-width, toast bottom-sheet.
- **Dogfood com 3 famílias**: tempo médio cadastro < 2min (vs >10min manual) — métrica de validação.
- **Idempotência**: re-upload do mesmo IRPF ano-base não cria novos cards.
- **Multi-ano**: IRPF 2025 + 2024 carregados produzem timeline ordenada, sem duplicar conta no mesmo ano.

## Implementação

Lane **`A13.irpf-prefill-bank-accounts`** planejada para Sprint A13 (futura — abre quando A11 fechar e A12 virar `current`). ~2d eng total em ~1 semana calendário.

| # | PR | Effort | Gate principal |
|---|---|---|---|
| 1 | **PR1** — Migration + endpoint + use case + telemetria base | ~1d | Backend tests verdes; OpenAPI snapshot atualizado |
| 2 | **PR2** — UI cards + diff modal + dismissals + a11y + dogfood | ~1d | E2E flow verde; tempo médio cadastro < 2min em 3 famílias dogfood |

Lane standalone — não bloqueia outras lanes A13. Flip ADR-229 → `Decidido (A13.irpf-prefill-bank-accounts)` no merge do PR2.

## Follow-ups V2 (fora do escopo V1)

- **Códigos IRPF 31/32/41/45/47/49**: ações, FIIs, CDB, Tesouro, fundos, previdência. Reutilizam pattern `artifact → suggestion → card`.
- **Sugestão de membros**: E1 também extrai família. Onboarding multi-membro trivial.
- **Sugestão de imóveis**: E1.6 ([[ADR-157]]) + property_identity ([[ADR-215]]) já geram dado. Reutiliza.
- **Banner soft de omissão fiscal**: descritivo, não-acusatório, zero telemetria.
- **Renderização de timeline `irpf_snapshots` no card da conta**: V1 só armazena; V2 expõe na UI.
- **Suggestion dismissals genérico**: tabela `workspace_suggestion_dismissals` (não-IRPF-específica) quando segundos consumidores chegarem.

## Referências

- [[ADR-127]] — E1 `extract_members` (fonte do artifact com `contas[]`).
- [[ADR-146]] — `source_tier` hierarchy (clique humano = tier 5).
- [[ADR-157]] — E1.6 `extract_irpf_full` (V2 imóveis).
- [[ADR-226]] — Bank account → member disambiguation (account_number como discriminador; UI in-app UNIQUE; FAQ produto).
- [[ADR-097]] — Boundary pipeline↔backend (use case lê artifact via store injetado).
- [[ADR-102]] — `response_model` explícito.
- Co-design 2026-05-20: `product-designer` (UX cards + diff inline + badge sunset + a11y + copy "você declarou"), `financial-planner` (Cerbasi/Perini/AUVP — IRPF como timeline anual + diff vs mesclagem silenciosa + zero telemetria omissão fiscal LGPD).
- Diagnóstico: pós-lane A12.bank-account-disambig fechar, sessão David Robert 2026-05-20 — "ROI alto: reduz 80% fricção cadastro para ICP que entrega IRPF".

## Status — Decidido (A13.irpf-prefill-bank-accounts)

Lane completa em 2 PRs sequenciais:

- **PR1** ([#345](https://github.com/davidrobert/mathoms/pull/345)) — Migration `workspace_irpf_suggestion_dismissals` + coluna `bank_accounts.irpf_snapshots` + endpoint `GET /members/suggestions-from-irpf` + endpoint `POST /members/irpf-dismissals` + use case puro com `IrpfArtifactSourceProtocol` (boundary ADR-097) + DTOs + telemetria estruturada `mathoms.irpf_suggestions.*` (4 eventos, zero LGPD) + 10 testes verde.
- **PR2** — UI cards inline em `MembersTab` (componentes `_IrpfSuggestionCard`, `_IrpfDiffModal`, `_MemberIrpfSection`) + a11y AAA + mobile responsive + toasts Sonner + integração com `BankAccountCreateCommand.origem_irpf` para emissão de telemetria + flip ADR + FAQ produto. Gateada por feature flag `irpf_prefill_enabled` (default OFF) — dogfood com 3 famílias acontece em paralelo, ativação posterior.

**V1 V0 scope concluído.** V2 follow-ups (renderização de `irpf_snapshots` timeline, sugestões de membros/imóveis/investimentos via mesmo pattern, banner soft de omissão fiscal, tabela `workspace_suggestion_dismissals` genérica) ficam para ADRs futuras quando segundos consumidores chegarem.
