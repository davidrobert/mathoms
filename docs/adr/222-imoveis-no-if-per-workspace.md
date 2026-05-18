---
id: ADR-222
type: adr
title: "Toggle `imoveis_no_if` migra de `pipeline.json` global para coluna `workspaces.imoveis_no_if`"
status: Proposto
phase: A12
date: "2026-05-18"
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-215]]"
  - "[[ADR-219]]"
  - "[[ADR-134]]"
  - "[[ADR-186]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 222"
  - "imoveis_no_if per-workspace"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/multitenancy
  - methodology/perini
  - phase/a12
  - status/proposto
  - type/adr
---

## Contexto

[[ADR-142]] (Decidido 2026-04-27) fixou o invariante anti-dupla-contagem para `progresso_if`: quando `imoveis_no_if=true`, `cat_2` entra em `investivel_efetivo` E `renda_passiva_atual_mensal_brl` deve excluir aluguéis (já contados como capital). §Consequências admitiu explicitamente: **"Por workspace do toggle é hoje promessa de doc, não realidade. Fica catalogado como débito"**. Hoje o toggle vive em [`config/pipeline.json:14`](../../config/pipeline.json) global; auditoria 2026-05-18 confirmou que **não há consumer runtime do toggle** (grep só retorna helper legado em `dev/_adr_categories_legacy.py`).

[[ADR-215]] §Follow-ups reitera o débito. O caminho correto agora é DB-first: coluna em `workspaces` com pattern análogo a `residencia_status` (ADR-215 P1) — ambos são estado tripartite/binário per-workspace que muda decisão visível no relatório.

**Motivação metodológica:** workspace dogfood `5@5.com` tem yield líquido de imóveis ~6% > TRS 5%, faz sentido `true`. Workspace random com yield 3% (vacância) ou só residência principal deveria poder ser `false`. Sem per-workspace, [[ADR-142]] sem runtime + Bloco B desta sprint (`investivel_efetivo`) só faz sentido para um workspace.

## Decisão

Adotar **três mudanças coordenadas** que materializam o toggle como dado de workspace:

### 1. Coluna direta em `workspaces` + 2 colunas de auditoria mínima

```sql
ALTER TABLE workspaces
  ADD COLUMN imoveis_no_if BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN imoveis_no_if_set_at TIMESTAMPTZ NULL,
  ADD COLUMN imoveis_no_if_set_by_user_id VARCHAR(36) NULL
    REFERENCES users(id) ON DELETE SET NULL;
```

**Por que coluna direta (não JSONB nem tabela lateral):**
- Pattern espelha `workspaces.residencia_status` (ADR-215 P1) — consistência interna.
- JSONB para 1 bool é over-engineering (perde tipagem, perde index trivial).
- Tabela lateral `workspace_settings(workspace_id, key, value)` custa JOIN em todo carregamento de `WorkspaceContext` por 1 toggle de UX.
- Não há roadmap visível de 3+ toggles per-workspace nos próximos 6 meses; se vier 3º, promove-se a tabela lateral migrando os 3 juntos.

**Por que `set_at` + `set_by_user_id` (e não YAGNI total):**
- Toggle afeta `progresso_if` (KPI central do relatório). Planejador certificado (B2B2C, futuro) vai perguntar "quando essa família mudou pra `true`?". Sem audit, fica forense por log/WAL — possível mas caro.
- Custo: 2 colunas nullable, sem index (raras leituras). Gain: rastreabilidade fiduciária.
- **Não** adicionar `explicitly_set BOOLEAN` separado — `set_at IS NULL` já distingue "default migrado" (NULL) de "escolha explícita" (timestamp). YAGNI vence.

### 2. Default `true` na migration (retrocompat)

`pipeline.json:14` hoje é `true`; default coluna `true` preserva comportamento. Migration **não** lê `pipeline.json` em runtime — acoplamento ruim, quebra reprodutibilidade (mesma revision em ambiente com pipeline.json diferente geraria estado diferente).

**Default conceitual para workspaces criados via UI no futuro** pode ser flipado para `false` em PR separado (recomendação metodológica de `financial-planner`: conservadorismo Perini default `false`; dogfood vira opt-in explícito). Decisão de UX fica para ADR futura com co-design `product-designer` — fora do escopo desta ADR.

### 3. `WorkspaceContext.imoveis_no_if` (lazy resolver) + cleanup `pipeline.json:14`

`WorkspaceContext` ganha property `imoveis_no_if: bool` que reads from the loaded `Workspace` row. Sites de leitura runtime (Bloco B desta sprint — `PatrimonioCalculator` que computa `investivel_efetivo`) consomem **apenas** via context — `pipeline.json:14` é deletado em PR2 imediato (mesma sprint), evitando 2 fontes de verdade.

Endpoint `PATCH /workspaces/{ws}` parcial (pattern existente; `monthly_llm_budget_usd`, `business_profile_json`, `rule_cap_override`, `residencia_status` já usam) aceita `imoveis_no_if: bool`; handler popula `set_at = now()` e `set_by_user_id = current_user.id`. `response_model` explícito ([[ADR-102]] R18) + `make update-openapi-snapshot`.

## Alternativas consideradas

- **(B) `workspaces.settings JSONB`** — over-engineering para 1 toggle; perde tipagem SQLAlchemy + index trivial. Reavaliar quando aparecer 3º toggle per-workspace.
- **(C) `workspace_settings(workspace_id, key, value)` lateral** — custa JOIN em todo `WorkspaceContext.load`; vale só quando ≥3 toggles + necessidade de audit per-setting.
- **(D) Override no `ConfigStore` DB-first (ADR-134)** — pesado: ADR-134 modela configs editoriais (categorization, family_members) que têm versionamento/audit; toggle UX simples não tem essa demanda.
- **(E) `explicitly_set BOOLEAN` separado** — redundante com `set_at IS NULL`; YAGNI.
- **(F) Migration lê `pipeline.json` em runtime** — acoplamento ruim, quebra reprodutibilidade de revisions Alembic; default literal `true` é equivalente ao estado atual.

## Consequências

**Positivas:**
- ✅ ADR-142 vira realidade per-workspace — destrava Bloco B desta sprint (runtime de `investivel_efetivo`) para multi-tenant.
- ✅ Pattern consistente com `workspaces.residencia_status` (ADR-215 P1) — sem invenção de novo padrão.
- ✅ Audit `set_at` + `set_by_user_id` rastreia "quem flipou e quando" — útil em disputa com planejador certificado.
- ✅ Endpoint PATCH parcial reusa pattern existente — sem invenção de `/settings` ou similar.
- ✅ `pipeline.json:14` removido na sprint — eliminando uma das 2 fontes de verdade.

**Negativas:**
- ⚠️ Crescimento da tabela `workspaces` (já com `monthly_llm_budget_usd`, `business_profile_json`, `rule_cap_override`, `residencia_status`, `use_db_artifacts_override`). Tolerável até ~8-10 colunas; signal de alerta para o futuro: se chegar um 3º toggle, abrir ADR pra promover tabela lateral (`workspace_settings`).
- ⚠️ Default `true` na migration é retrocompat com hoje, **não** metodologicamente correto (Perini default `false`). Mitigação: PR separado pode flip default para workspaces criados após X data (co-design `product-designer`).

**Riscos:**

| Risco | Mitigação |
|---|---|
| Migration aplicada com `pipeline.json:14=false` em ambiente custom drift | Default `true` na migration ignora JSON; runbook explicita que cutover requer revisão manual do toggle em workspaces existentes se admin tinha custom flag |
| Endpoint PATCH expõe toggle sem perfil de risco declarado | Documentado: usuário flipa diretamente; UX deve mostrar implicação ("imóveis entrarão/sairão do investível efetivo"). Decisão fora do escopo desta ADR |
| `set_by_user_id FK` resta órfão se user é hard-deletado | `ON DELETE SET NULL` no FK preserva audit (timestamp) mesmo sem identidade |

## Gates

- **Migration** Alembic idempotente up/down testada; `DB_SCHEMA_REFERENCE.md` regenerado e commitado no mesmo PR.
- **Model** `Workspace` ganha `imoveis_no_if`, `imoveis_no_if_set_at`, `imoveis_no_if_set_by_user_id` typed.
- **`WorkspaceContext.imoveis_no_if`** property + injeção via `pipeline_task._setup_run_context`.
- **Endpoint** `PATCH /workspaces/{ws}` aceita `imoveis_no_if: bool` no body; popula audit automaticamente.
- **`make update-openapi-snapshot`** rodado; teste `backend/tests/test_openapi_snapshot.py` verde.
- **Unit + integration tests:**
  - Migration up/down verde.
  - Endpoint PATCH: 200 + audit fields populados.
  - `WorkspaceContext` lê valor correto.
- **Cutover PR2 (mesma sprint):** delete `pipeline.json:14`, remove campo de `StageConfig` se houver, atualiza `rule-imoveis-no-if.md` linha 23 ("promessa de doc" → "implementado em ADR-222"). Atualiza ADR-142 status para `Decidido (deprecation completo)`.

## Referências

- [[ADR-142]] — Toggle `imoveis_no_if` invariante anti-dupla-contagem (esta ADR cumpre o débito de "per-workspace promessa de doc").
- [[ADR-215]] P1 — `workspaces.residencia_status` (pattern espelhado).
- [[ADR-219]] wave 2 — `EconomicAssumptionsResolver` injetado via `WorkspaceContext` (pattern de leitura per-workspace análogo, embora aqui não precise de resolver dedicado por ser scalar).
- [[ADR-134]] — `ConfigStore` DB-first (rejeitado para este caso por overhead).
- [[ADR-102]] R18 — `response_model` explícito.
- Co-design 2026-05-18: `data-engineer` (schema + 2 cols audit + default true), `senior-cto` (Opção A coluna direta YAGNI, endpoint PATCH parcial, sem `explicitly_set`), `financial-planner` (default conceitual deveria flippar para `false` em followup — registrado como recomendação para PR separado).
