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
