# Documentos arquivados

Documentos históricos preservados para referência. **Não são fonte de verdade operacional** — para isso consulte os documentos ativos em `docs/`.

---

## cutover-2026-05-14.md

Runbook canônico do cutover `MATHOMS_USE_DB_ARTIFACTS=true` (ADR-118, 2026-04-23) — procedure de cutover por workspace + métricas Prometheus + alertas + rollback flip-flag.

**Arquivado em:** 2026-05-14

**Substituído por:** [`../reference/runbooks/pipeline_rollback.md`](../reference/runbooks/pipeline_rollback.md) — runbook DB-only pós-ADR-212 PR4 (snapshot DB pré-deploy + revert PR + migration downgrade).

**Quando consultar:** apenas para contexto histórico do cutover original. Pós-ADR-212 PR4, `MATHOMS_USE_DB_ARTIFACTS` foi removido de settings e a coluna `workspaces.use_db_artifacts_override` foi dropada; flip-flag não é mais um caminho de rollback válido.

---

## PRODUCT_PLAN-2026-04-15.md

Documento único original (~390KB, 4052 linhas) que combinava visão, arquitetura, backlog, sprints, decisões técnicas, riscos e log de progresso em um único arquivo.

**Arquivado em:** 2026-04-15

**Substituído por:**
- **[../PRODUCT.md](../PRODUCT.md)** — visão, valor, público
- **[../ARCHITECTURE.md](../ARCHITECTURE.md)** — stack, modelo de dados, fluxos
- **[../SETUP.md](../SETUP.md)** — setup local
- **[../ROADMAP.md](../ROADMAP.md)** — fases, milestones
- **[../BACKLOG.md](../BACKLOG.md)** — tasks detalhadas
- **[../DECISIONS.md](../DECISIONS.md)** — ADRs
- **[../CHANGELOG.md](../CHANGELOG.md)** — log de entregas

**Quando consultar:** apenas para contexto histórico ou arqueologia de decisões. Conteúdo migrado e atualizado nos arquivos acima.

---

## CONFIG_CUTOVER_PLAN-2026-04-27.md

Plano canônico da Sprint A7 — cutover de `config/*.json|md|yaml` para DB
multi-tenant + tabelas globais versionadas. 11 seções, 7 lanes (A7.0
ConfigStore protocol → A7.5 cleanup final), supervisão CTO em 4 gates.

**Arquivado em:** 2026-04-27 (Sprint A7 ✅ entregue mesmo dia da abertura)

**Substituído por:** ADRs 134–138 + 143/145/146/147 em
[../DECISIONS.md](../DECISIONS.md), entrada Sprint A7 em
[../CHANGELOG.md](../CHANGELOG.md), seção §Fontes de verdade no
[../../CLAUDE.md](../../CLAUDE.md).

**Quando consultar:** rationale histórico de decisões arquiteturais
(catalog+override, event-sourced Decision, versionamento temporal de
séries fiscais), ondas paralelas com supervisão CTO, ou genealogia de
bridges (`FileConfigStore`, `materialize_config`) já removidos.

---

## GOALS_JSON_CUTOVER_PLAN-2026-05-07.md

Plano canônico da Sprint A10 — cutover final do último frente de
`config/*.json` → DB-first iniciada em A7. 10 seções, 9 lanes em 4 ondas,
5 ADRs propostos (ADR-177 a ADR-181), supervisão CTO em 4 gates.

**Arquivado em:** 2026-05-07 (Sprint A10 ✅ entregue — 9/9 lanes em `main`
no mesmo ciclo de pickup, fechando débito de 7 meses do checkbox ADR-077
§"Contrato de cutover").

**Substituído por:** ADRs 177–181 em [../DECISIONS.md](../DECISIONS.md),
entrada Sprint A10 (Waves 0-4) em [../CHANGELOG.md](../CHANGELOG.md),
gate `config/goals.json` em `dev/check_forbidden_paths.py`, e
`_archive/pre-f8-cutover-2026-04-15/config/goals.json.MIGRATED.md` com
mapa das 22 chaves → destinos.

**Quando consultar:** rationale histórico do inventário decisional de 22
chaves, design de `GoalsBundle` TypedDict, dependências entre ondas, ou
arqueologia do débito de 7 meses sobre cobertura `goals.json`.

---

## CATEGORY_OVERRIDES_UX_PLAN-2026-05-10.md

Plano canônico da Sprint A11.cat-overrides-ux — V1 da UX de overrides de
categoria (24 default-only, template v1 ADR-137). 4 ondas em paralelo
(cache fix → schema delta → ADR Proposto → UI refactor), 1 ADR canônica
(ADR-185), corrigia tela vazia em workspace novo + bug latente de cache
stale (300s TTL).

**Arquivado em:** 2026-05-10 (Sprint A11.cat-overrides-ux ✅ entregue —
4/4 PRs em `main` no mesmo ciclo, fechando gap entre endpoints
`/config/category-overrides/*` modernos e UI legacy `/config/categories`).

**Substituído por:** [ADR-185](../adr/185-categorization-template-versioning-overrides.md)
(`Decidido (A11.cat-overrides)`), PR #187 (W1 cache invalidation), PR #186
(W2 schema delta `updated_by_user_id`), PR #182 (W3 ADR-185 Proposto),
PR #189 (W4 UI refactor + flip ADR-185 para Decidido).

**Quando consultar:** rationale histórico da política v1→v2 sem
`template_version_pinned` (migrations codificam preserve/rename/disable),
escopo 24 default-only com não-objetivos (custom categories, audit
event-sourced, sunset legacy endpoint), diff client-side de keywords em
3 estados, hook estrutural de tabs extensíveis para V2.A do learning loop.

---

## DOC_REORG_PLAN-2026-05-07.md

Plano canônico da reorganização documental (ADR-182). 5 fases em ~3 dias
calendário, atomização de DECISIONS.md (175 ADRs), BACKLOG.md (35 lanes
+ 18 sprint MOCs), CHANGELOG.md (167 entries), tracks (62) e plans (6),
com gates pre-commit + snapshot test + benchmark de tokens.

**Arquivado em:** 2026-05-07

**Substituído por:**
- **[../adr/](../adr/)** + [../_MOC/_generated/ADR_INDEX.md](../_MOC/_generated/ADR_INDEX.md) (ADRs atomizadas, índice agrupado por categoria/status)
- **[../sprint/](../sprint/)** + [../_MOC/SPRINTS-active.md](../_MOC/SPRINTS-active.md) + [../_MOC/_generated/SPRINT_CURRENT.md](../_MOC/_generated/SPRINT_CURRENT.md) (lanes/tracks/changelog por sprint)
- **[../plan/](../plan/)** + [../_MOC/PLANS-active.md](../_MOC/PLANS-active.md) (planos canônicos abertos)
- **[../reference/PHASES.md](../reference/PHASES.md)** + [../reference/PRODUCT.md](../reference/PRODUCT.md) (docs estáveis)

**Quando consultar:** rationale histórico das 5 fases, decisões de granularidade (lanes per-H3 vs per-table; changelog per-bullet vs per-PR), gaps conhecidos (F4.A.followup), trade-offs aceitos.

**Métricas finais:**
- DECISIONS.md: 9040 → 219 linhas (−97.6%)
- BACKLOG.md: 2358 → 49 linhas (−97.9%)
- CHANGELOG.md: 6923 → ~50 linhas (−99.3%)
- Notas atômicas: 0 → ~445 (175 adr + 6 plan + 62 track + 35 lane + 167 changelog)
- Token-cost-benchmark Q1/Q2/Q5/Q6: redução ≥97%; Q3/Q4 cai com F5.

---

## IMOVEL_FINANCIADO-2026-05-20.md

Plano canônico do FU-3 imóvel financiado ([[ADR-227]]). Sprint A15 dedicada
(2026-05-19 → 2026-05-20), 5 ondas sequenciais + bootstrap + 3 sub-PRs de
frontend = **8 PRs entregues em ~6h**. Resolveu 2 bugs silenciosos em
produção (patrimônio bruto defasado + IF mal-calibrado): cria agregado
`Debt` persistido do zero, `property_market_value` versionada append-only,
calculator com líquido econômico em `investivel_efetivo` preservando
bruto na tabela ([[ADR-227]] §D3), 7 endpoints REST CRUD, frontend cutover
end-to-end (MarketValueInline, batch review, nudge S4, drill-down panel,
staleness badge).

**Arquivado em:** 2026-05-20

**Substituído por:**
- [[ADR-227]] (Decidido em A15) — fonte de verdade da decisão arquitetural.
- [docs/sprint/A15/_README.md](../sprint/A15/_README.md) — MOC da sprint
  (status: done).
- [docs/sprint/A15/changelog/CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO.md](../sprint/A15/changelog/CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO.md)
  — changelog consolidado.
- [docs/reference/RUNBOOK.md §10](../reference/RUNBOOK.md) — runbook
  operacional de backfill.

**Quando consultar:** rationale histórico do co-design 2026-05-19 (4
agentes em paralelo), alternativas A-G consideradas (Onda 0 PR de
bootstrap), invariantes não-negociáveis enumerados antes da execução.

**PRs entregues:**
[#371](https://github.com/davidrobert/mathoms/pull/371) bootstrap ·
[#372](https://github.com/davidrobert/mathoms/pull/372) schema/models ·
[#373](https://github.com/davidrobert/mathoms/pull/373) backfill ·
[#374](https://github.com/davidrobert/mathoms/pull/374) calculator ·
[#375](https://github.com/davidrobert/mathoms/pull/375) API ·
[#376](https://github.com/davidrobert/mathoms/pull/376) FE foundation ·
[#378](https://github.com/davidrobert/mathoms/pull/378) FE inline +
nudge · [#379](https://github.com/davidrobert/mathoms/pull/379) FE
drill-down + flip Decidido.

## SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md

Conteúdo específico do gate A6b.5→A6c ([[ADR-103]]) extraído de
`docs/reference/SMOKE_TEST_HUMAN.md`: §4.7 (cutover disco↔DB, mecanismos
removidos por [[ADR-212]]), formato de decisão A6c e troubleshooting do
`compare_disk_vs_db`. Gate executado e aprovado em 2026-04/05.

**Arquivado em:** 2026-07-03 (audit-vault r6 F03, decisão do owner).
**Substituído por:** [docs/reference/SMOKE_TEST_HUMAN.md](../reference/SMOKE_TEST_HUMAN.md)
— runbook vivo (checks gerais + §4.9 + registro de snapshots).
