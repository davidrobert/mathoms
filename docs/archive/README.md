# Documentos arquivados

Documentos históricos preservados para referência. **Não são fonte de verdade operacional** — para isso consulte os documentos ativos em `docs/`.

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
