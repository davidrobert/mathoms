---
id: TRACK-category-overrides-policy-adr
type: track
title: "Track Category Overrides W3 — ADR-185 Proposto (política + escopo + invariantes)"
sprint: A11
plan: PLAN-category-overrides-ux
status: consumed
created_at: "2026-05-10"
consumed_at: "2026-05-10"
agent_role: product-manager
tags:
  - type/track
  - sprint/a11
  - status/consumed
  - area/categorization
  - area/adr
---

# Track Category Overrides W3 — ADR-185 Proposto

> **Lane ID:** category-overrides-policy-adr
> **Plano canônico:** [docs/plan/CATEGORY_OVERRIDES_UX/_README.md](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md) §Wave 3
> **Branch prefix:** `agent/category-overrides-policy-adr/*`
> **Depende de:** —
> **Bloqueia:** W4-T01 (CLAUDE.md §"ADR Proposto antes de PR P0/P1")
> **Paralelo com:** W1-T01, W3-T01 (docs-only, fast-track)

## Briefing

ADR-137 ([docs/adr/137-categorization-templates-overrides.md](../../../adr/137-catalog-override-resolver-para-categorization-e.md)) introduziu template + override em A7.3 mas deixou em aberto: política de evolução v1→v2, escopo de overridable, semântica de cache invalidation, audit. ADR-185 fecha esses pontos antes da feature ir pra prod.

**Owner sugerido:** `product-manager` redige o rascunho a partir das decisões já fechadas; `senior-cto` revisa e mergeia (CLAUDE.md §"ADR `Proposto` P0/P1" → senior-cto).

## Escopo da ADR-185

### §1 Política v1→v2 do template

- **Decisão:** override referencia `template_key` por string; resolver lê o template `latest_template_version` ativo. **Sem `template_version_pinned`.**
- **Migration de seed v2 codifica explicitamente:**
  - `key` preservada → override sobrevive intacto.
  - `key` removida → migration faz `UPDATE workspace_category_overrides SET disabled=TRUE, metadata_json={"deprecated_in_version": 2}` para a key removida.
  - `key` renomeada → migration faz `UPDATE ... SET template_key='novo' WHERE template_key='velho'`. Não automatize via heurística.
- **Invariante (proibido):** mudança semântica de uma key sem rename (ex.: "Investimentos" passa a incluir cripto sem renomear) é proibida. Política de release de template fica registrada nesta ADR.

### §2 Escopo do que é overridable

- **V1:** label, keywords, monthly_cap, disabled — para as 24 categorias default em template v1.
- **Fora:** custom categories (futura tabela `workspace_custom_categories`); override de metadata auxiliar `pj_source_mapping`/`clt_source_mapping`/`internal_transfer_patterns`/`one_time_income_*`/`qa_investigation_patterns` (futura tabela `workspace_income_source_mapping` ou similar). Cada uma vira ADR Proposto separada quando virar prioridade.

### §3 Cache invalidation no application layer

- Repository fica thin (zero `category_cache` import).
- `CategoryOverrideService` orquestra: chama repo → commit → `category_cache.invalidate(workspace_id)` → log estruturado.
- Falha de invalidação loga warning, não falha o write (TTL 300s natural cuida).
- Padrão write-through; aceitar staleness <100ms entre commit e cache cleared.

### §4 Audit mínimo

- Coluna `updated_by_user_id` (FK `users.id`, nullable) já no schema (W2).
- **Sem** audit log event-sourced; padrão Decision A7.2a entra só quando consultor profissional pedir.
- `updated_at` automático via SQLAlchemy `onupdate=func.now()`.

### §5 Teste migration v1→v2 pending

- Adicionar `backend/tests/test_category_template_v2_migration.py` com `@pytest.mark.skip(reason="v2 ainda não publicada")`.
- 3 fixtures: preserve (key sobrevive intacta), rename (UPDATE explicit), remove (`disabled=TRUE` + `metadata_json.deprecated_in_version`).
- Quando v2 entrar, remover skip e CI roda.

## Critério de aceite

- [ ] `docs/adr/185-category-overrides-policy.md` publicada com `status: Proposto`, `phase: A11.cat-overrides`, `date: '2026-05-10'`.
- [ ] Frontmatter validado por `dev/validate_frontmatter.py`.
- [ ] Cobre 5 § acima.
- [ ] Wikilink bidirecional: ADR-185 declara `relates_to: [[ADR-137]]`; ADR-137 ganha `relates_to: [[ADR-185]]` no frontmatter.
- [ ] Anchor histórico em `docs/DECISIONS.md` shim (gerar slug com `python3 dev/check_adr_anchors.py --suggest`).
- [ ] `pre-commit run --all-files` verde (frontmatter, filename↔id, links, anchors, formato).

## Arquivos esperados

- **Novo:** `docs/adr/185-category-overrides-policy.md`
- **Editado:** `docs/adr/137-categorization-templates-overrides.md` (frontmatter `relates_to`)
- **Editado:** `docs/DECISIONS.md` (anchor histórico do slug GH)

## Testes

```bash
python3 dev/validate_frontmatter.py
python3 dev/check_doc_filename_id.py
python3 dev/check_doc_links.py
python3 dev/check_adr_anchors.py
python3 dev/build_doc_index.py --check
python3 dev/validate_adr_format.py
pre-commit run --all-files
```

## Riscos

- **R1** — invariante "rename obrigatório em mudança semântica" é difícil de enforçar mecanicamente. Mitigação: ADR registra como regra editorial; PR de v2 do template em revisão obrigatória de `senior-cto` + `data-engineer`.
- **R2** — colisão de número ADR (185) com outro PR em voo. Mitigação: pre-flight `git fetch origin && ls docs/adr/ | tail -5` antes do commit.

## Ligações

- Plano: [PLAN-category-overrides-ux](../../../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md)
- ADR raiz: [[ADR-137]] (suplementada por ADR-185)
- ADRs relacionadas: [[ADR-091]] (rules-as-code), [[ADR-097]] (services com value object), [[ADR-110]] (logging estruturado)
