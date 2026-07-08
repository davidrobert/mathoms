---
id: ADR-185
type: adr
title: "Política de edição e evolução de overrides de `category_templates`"
status: Decidido
phase: A11.cat-overrides
date: "2026-05-10"
decided_at: "2026-05-10"
relates_to:
  - "[[ADR-091]]"
  - "[[ADR-097]]"
  - "[[ADR-110]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
supersedes: []
superseded_by: []
aliases: ["ADR 185", "Category overrides policy"]
tags:
  - area/categorization
  - area/backend
  - phase/a11
  - status/decidido
  - type/adr
---

> Esta ADR suplementa [[ADR-137]] (catalog + override resolver para
> `categorization` e `institutions`), fechando políticas que ficaram em
> aberto: política de evolução v1→v2 do template, escopo do que é
> overridable, semântica de cache invalidation, profundidade do audit, e
> contrato de teste de migration pending. Decisões originadas em discussão
> 2026-05-10 entre dono + `product-designer` + `data-engineer` +
> `product-manager`, formando entrada do plano `PLAN-category-overrides-ux`
> ([docs/plan/CATEGORY_OVERRIDES_UX/_README.md](../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md)).

## Contexto

A7.3 (ADR-137) introduziu duas tabelas — `category_templates` (taxonomia
global versionada) e `workspace_category_overrides` (diff per-workspace)
— com merge no read via `CategoryResolver`
([backend/app/services/category_resolver.py](../../backend/app/services/category_resolver.py)).
Template v1 foi seedado em
[backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py](../../backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py)
com 24 categorias (16 expense + 8 income) + 1 row de metadata auxiliar.

ADR-137 ficou silenciosa em 5 pontos que viraram decisão pendente quando
abrimos a feature de UX de edição:

1. **Evolução v1→v2 do template.** Override aponta por `template_key`
   string. Se v2 muda/remove keys, override fica órfão silenciosamente —
   resolver ignora. Quem decide a política?
2. **Escopo do que é overridable.** Hoje `WorkspaceCategoryOverride`
   permite editar `label`, `keywords`, `monthly_cap_brl_cents`, `disabled`.
   Custom categories (fora do template) e metadata auxiliar
   (`pj_source_mapping`, `internal_transfer_patterns`,
   `clt_source_mapping`, `one_time_income_*`,
   `qa_investigation_patterns` — armazenados em
   `category_templates.metadata_json` da row reservada
   `__categorization_metadata__`) ficaram fora.
3. **Cache invalidation no fluxo de upsert/delete.** Bug latente:
   `WorkspaceCategoryOverrideRepository.upsert/delete`
   ([backend/app/repositories/workspace_category_override_repository.py](../../backend/app/repositories/workspace_category_override_repository.py))
   **não invalida** `category_cache`
   ([backend/app/services/storage/category_cache.py](../../backend/app/services/storage/category_cache.py))
   após commit. TTL é 86400s (24h) — em prod, edição de override fica
   stale por até 24h no E4 sem invalidação ativa.
4. **Audit mínimo.** Sem coluna de quem editou; padrão Decision A7.2a
   (event-sourced) seria caro pra MVP.
5. **Teste de migration v1→v2.** Não há fixture; primeira release v2
   vira incidente.

## Decisão

### §1 Política v1→v2 do template — sem `template_version_pinned`

Override referencia `template_key` por string; resolver lê o template
`latest_template_version` ativo (auto-derivado da maior versão em
`category_templates`). **Não introduzir** coluna
`template_version_pinned` em `WorkspaceCategoryOverride`.

Migrations futuras (Alembic) que publicam template v2 codificam
explicitamente:

| Caso | Ação na migration de seed v2 |
|------|------------------------------|
| `key` preservada (mesma identidade conceitual) | Override sobrevive intacto. Sem ação. |
| `key` removida (categoria deixou de existir) | `UPDATE workspace_category_overrides SET disabled=TRUE, metadata_json=jsonb_set(metadata_json, '{deprecated_in_version}', '2'::jsonb) WHERE template_key='<removida>'` |
| `key` renomeada (mesma identidade, slug novo) | `UPDATE workspace_category_overrides SET template_key='<novo>' WHERE template_key='<velho>'` |

**Invariante (proibido):** mudança **semântica** de uma key sem rename é
proibida (ex.: "investimentos" passa a incluir cripto sem renomear). Quem
escreve a migration de v2 declara explicitamente preserve/rename/disable;
mudança sem rename é violação editorial e **deve ser bloqueada em PR
review** por `senior-cto` + `data-engineer`.

**Por quê sem pin:** pin congela override no v1 e cada release de
template vira cutover N×workspaces. UX explica "atualizar override" e os
usuários ignoram. Vira N taxonomias coexistindo na base — métricas
comparativas entre famílias ficam ruidosas (Alimentação v1 ≠ Alimentação
v2 em keywords/cap). Quebra o pressuposto do ADR-137 de **template
global como fonte de verdade única**.

**Trade-off aceito:** workspace que overridou "Alimentação" em v1 não
recebe novas keywords default em v2 — o override é "minha lista
completa". Mitigação: UI sinaliza desatualização via `AlertCircle` quando
`template_version_used < latest_template_version` (sem CTA agora; CTA
"ver o que mudou e mesclar" entra junto com v2).

### §2 Escopo do que é overridable na V1

**Dentro:**

- `label` — string até 120 chars (substitui o default).
- `keywords` — `JSON list[str]` que **substitui** o `default_keywords`
  inteiro (não merge). UI reconstrói diff client-side para apresentar
  como "herdada · adicionada · removida-em-accordion".
- `monthly_cap_brl_cents` — `BigInteger` (ADR-090), nullable.
- `disabled` — `bool`, default `false`. Categoria desabilitada some da
  UI mas não é apagada (preserva slot pra futuras transações se
  reabilitada).

**Fora (V1 — não bloquear ADR-185):**

- **Custom categories** (categoria nova fora do template) — futura
  tabela `workspace_custom_categories` com schema espelhado parcial
  (key own-namespaced, label, keywords, monthly_cap, parent_key opcional).
  Resolver concatena template + overrides + custom. Adiada para ADR
  Proposta separada quando virar prioridade.
- **Override de metadata auxiliar**
  (`pj_source_mapping`, `clt_source_mapping`,
  `internal_transfer_patterns`, `one_time_income_keywords`,
  `one_time_income_categories`, `qa_investigation_patterns`) — vivem
  hoje em `category_templates.metadata_json` da row reservada
  `__categorization_metadata__`. Caso de uso real (PJ adicionar
  empresa em `pj_source_mapping`) resolve com **nova tabela**
  `workspace_income_source_mapping(workspace_id, pattern, source_type,
  member_key)`, não com extensão de `WorkspaceCategoryOverride`.

**Dívida documentada:** a row `__categorization_metadata__` no
`category_templates` é hack — mistura "lista de categorias" com
"configuração global de pipeline". Quando a primeira feature de override
de metadata aterrissar, isolar em tabela própria
`categorization_metadata` antes que mais código ancore no hack.

### §3 Cache invalidation no application layer (não no repo)

**Padrão write-through, ADR-097-compliant:**

- Repository (`WorkspaceCategoryOverrideRepository`) fica **thin** —
  zero `category_cache` import.
- Toda mutação atravessa `CategoryOverrideService`
  (`backend/app/application/categorization/category_override_service.py`)
  que recebe `CategoryOverrideConfig` (value object frozen, ADR-097 D3),
  orquestra: chama repo → commit → `category_cache.invalidate(workspace_id)`
  → log estruturado `mathoms.app.category_override.*` (ADR-110).
- Falha de invalidação **loga warning, não falha o write**. TTL é
  safety-net longo (86400s / 24h em `_RESOLVED_TTL_SECONDS`) — invariante
  de correção é write-through invalidation pós-commit. Janela aceita:
  stale ≤ 100 ms entre commit e cache cleared.
- API endpoints
  ([backend/app/api/category_overrides.py](../../backend/app/api/category_overrides.py))
  consomem o service, não o repo direto.

**Por quê service e não repo:** repo conhecer cache vira camada errada
(ADR-097: services com value object orquestram I/O, repos são CRUD
puros). Além disso, futuras invariantes de domínio (ex.: "label novo
não pode ser igual a outra categoria do mesmo workspace") vivem no
service, não no repo.

**Read-after-write garantido pela API:** PUT/POST/DELETE retornam o
`CategoryListResponse` resolved-after-write — caller consome a response
direto, não relê via GET. Race entre commit e invalidação cache fica
oculta para a UI.

### §4 Audit mínimo — `updated_by_user_id` no schema, nada mais

Adicionar em `WorkspaceCategoryOverride`:

- `updated_by_user_id` — `String(36)`, FK `users.id`, **nullable**,
  `on_delete=SET NULL`. Sem default; popula daqui pra frente nos
  handlers que têm `current_user`. Sem backfill.

**Não adicionar (V1):**

- `update_reason` (free text) — tipicamente preenchido em branco e
  atrapalha o form.
- Tabela `workspace_category_override_history` event-sourced (padrão
  Decision A7.2a) — overkill para MVP. Quando consultor profissional
  pedir audit completo, vira ADR Proposta separada.

`updated_at` automático via SQLAlchemy `onupdate=func.now()` já existe.

### §5 Teste de migration v1→v2 pending

Adicionar `backend/tests/test_category_template_v2_migration.py` com
`@pytest.mark.skip(reason="v2 ainda não publicada")`. 3 fixtures
canônicos:

| Fixture | Setup | Asserção |
|---------|-------|----------|
| `preserve` | template v1 com key `alimentacao`; workspace W1 com override em `alimentacao`; v2 mantém key | Override de W1 sobrevive intacto. |
| `rename` | template v1 com key `melhoria_reforma`; workspace W2 com override; v2 renomeia para `casa_e_reforma` (UPDATE explícito na migration) | Override de W2 aponta para `casa_e_reforma` após migration. |
| `remove` | template v1 com key `obsoleta`; workspace W3 com override; v2 remove key | Override de W3 fica `disabled=true` + `metadata_json.deprecated_in_version=2`. |

Quando v2 for publicada, remover `@pytest.mark.skip` e CI roda. Falha
sinaliza que a migration de seed v2 violou a política §1.

## Consequências

**Positivas:**

- Workspace novo vê 24 categorias default sem ação adicional (gap atual
  da UI fica fechado em W4).
- Bug de cache invalidation em prod fica resolvido (W1).
- Política v1→v2 explícita e codificada — sem dependência de operação
  manual para "atualizar override".
- Schema permanece estável (1 coluna nullable adicionada, zero
  refactoring de existentes).

**Negativas / aceitas:**

- Workspace que overridou keywords não recebe novas keywords default
  do template em v2 — trade-off documentado, mitigado por sinal visual.
- Mudança semântica de key sem rename vira violação editorial
  (gate humano em PR review, não automatizável).
- `__categorization_metadata__` continua como hack — débito explícito,
  isolamento em tabela própria adia para quando virar dor.

**Reversibilidade:**

- Coluna `updated_by_user_id` é nullable e isolada — `alembic
  downgrade -1` reverte sem perda.
- `CategoryOverrideService` é camada nova; remoção volta ao estado
  pré-W1 (com bug de cache).
- Política §1 vira jurisprudência operacional — invariante de PR
  review, não invariante mecânica.

## Alternativas consideradas

### A1. `template_version_pinned` no override (rejeitada — §1)

Override carrega versão do template em que foi criado; resolver lê
template **da versão pinada**. Atualização para v2 vira ação explícita
do usuário ("atualizar override").

**Rejeitada porque:** cria N taxonomias coexistindo, fragmenta métricas,
viola pressuposto do ADR-137 ("template global como fonte de verdade").
Cada release de template vira cutover por workspace.

### A2. `keywords_added` + `keywords_removed` (aditivo) em vez de `keywords_override` substituição (rejeitada — §2)

Override armazena delta. Resolver computa
`default ∪ added \ removed`.

**Rejeitada porque:** dobra complexidade do resolver, cria edge case
"default removido em v2 que estava em `keywords_added` por engano".
Trade-off não justifica para 24 categorias com edição esparsa. UX
absorve a perda via diff client-side (apresenta "minha lista" como se
fosse aditiva, mas storage é flat).

### A3. Cache invalidation no repo (rejeitada — §3)

Repo conhece e chama `category_cache.invalidate()`.

**Rejeitada porque:** viola ADR-097 (camada errada — repo é CRUD puro,
service orquestra). Bloqueia futura adição de invariantes de domínio
(ex.: validação cross-categoria).

### A4. Tabela `workspace_category_override_history` event-sourced (rejeitada — §4)

Toda mutação grava evento (`UpsertedOverride`, `DisabledOverride`,
`ResetOverride`) com payload completo + actor.

**Rejeitada para V1 porque:** overkill antes de validação de uso real.
`updated_by_user_id` cobre 90% dos casos ("quem mudou?"); audit
completo entra quando consultor profissional pedir.

## Critério de aceite (desta ADR)

- [x] ADR-185 publicada em `docs/adr/185-politica-de-overrides-de-categoria.md`
      com `status: Decidido`, `phase: A11.cat-overrides`, `date: '2026-05-10'`,
      `decided_at: '2026-05-10'`.
- [x] Wikilink bidirecional: ADR-185 ↔ ADR-137 (frontmatter `relates_to`).
- [x] `pre-commit run --all-files` verde (frontmatter, filename↔id, links,
      anchors, formato).
- [x] PR de implementação (W1+W2+W4 do plano) referencia ADR-185 nos
      bodies; status flippado para `Decidido (Sprint A11.cat-overrides)` no
      merge da W4 (lane completa).

## Histórico

- **2026-05-10 · Proposto.** Discussão entre dono + `product-designer` +
  `data-engineer` + `product-manager` originou as 5 decisões pendentes
  herdadas de ADR-137.
- **2026-05-10 · Decidido (Sprint A11.cat-overrides).** Após W1 (PR #187,
  cache invalidation), W2 (PR #186, schema delta + DTO), W3 (PR #182,
  ADR Proposto), W4 fecha a feature V1 com UI moderna; flip pós-merge.

## Ligações

- Plano canônico: [PLAN-category-overrides-ux](../archive/CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md)
- ADR raiz suplementada: [[ADR-137]] — catalog + override resolver
- ADRs relacionadas:
  - [[ADR-091]] — rules-as-code (política como código)
  - [[ADR-097]] — services com value object (ISP)
  - [[ADR-110]] — logging estruturado JSON
  - [[ADR-143]] — methodology = code (rules co-localizados)
