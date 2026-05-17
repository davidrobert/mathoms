---
id: ADR-182
type: adr
title: "Vault de documentação operacional Obsidian-friendly em `docs/`"
status: Decidido
phase: A11.5
date: "2026-05-07"
relates_to: ["[[ADR-076]]", "[[ADR-109]]", "[[ADR-114]]", "[[ADR-143]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 182"]
tags:
  - area/auth
  - area/docs
  - area/persistence
  - phase/a11-5
  - status/decidido
  - type/adr
size_lines: 66
---

# ADR-182 — Vault de documentação operacional Obsidian-friendly em `docs/`

**Status:** Decidido (Sprint A11.5) • **Data:** 2026-05-07 • **Relaciona** [ADR-076](#adr-076--design-tokens-unificados-site--relatório), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a), [ADR-114](#adr-114--enforcement-automatizado-de-code-style-gates-imediatos--progressivos-a6g6), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76).

**Contexto:** A documentação operacional cresceu para ~24k linhas distribuídas em 70+ arquivos. Métricas medidas (2026-05-07): `DECISIONS.md` 8.973 linhas / 175 ADRs (~155k tokens), `CHANGELOG.md` 6.923 linhas (~130k tokens), `BACKLOG.md` 2.358 linhas (~47k tokens), 57 tracks em `agent_prompts/` (~12k linhas) com ~30 linhas de "regras inegociáveis" duplicadas em cada um, 7 `<TOPIC>_PLAN.md` (~4k linhas), `CLAUDE.md` 1.011 linhas injetadas em **toda** sessão LLM.

Drift confirmado entre 4 fontes: `ROADMAP.md` linha 6 diz "Sprint A7 entregue", `BACKLOG.md` linha 9 diz "Direção E em curso", `CHANGELOG.md` linha 9 diz "Sprint A10 Wave 1", `README.md` linha 5 idem. Status duplicado em 3-4 lugares com horas de atraso entre updates. Cabeçalhos de tracks repetem invariantes do `CLAUDE.md` (~1.700 linhas duplicadas em 57 arquivos) e driftam silenciosamente quando ADRs canônicas mudam.

Custo de tokens medido por operação típica (cenário "agente pega lane, executa"): adicionar lane no BACKLOG ≈ 50k lidos; atualizar status de lane ≈ 80k (precisa cross-checar 2-3 fontes); adicionar entrada no CHANGELOG ≈ 130k (lê arquivo gigante para inserir bullet); descobrir lanes prontas ≈ 56k. LLM consome 30-200k tokens em queries de leitura/listagem antes de produzir uma linha.

Brainstorm local em `_scratch/doc-reorg-brainstorm-cto.md` (lente estrutural) e `_scratch/doc-reorg-brainstorm-data.md` (lente de consumo por LLM, retornado inline) avaliou 4 modelos arquiteturais. Recomendação convergente: vault Obsidian-friendly com notas atômicas + frontmatter YAML + índices materializados.

**Decisão:** Reorganizar documentação operacional como vault Obsidian-friendly **em `docs/` (raiz preservada)**, com:

1. **Notas atômicas com frontmatter YAML** por tipo: `adr`, `lane`, `plan`, `changelog-entry`, `track`, `domain-rule`. Filename = ID estável (`adr/090-decimal-money.md`, `sprint/A10/lanes/A10-2-rules-as-code.md`).
2. **IDs estáveis** com regex validada por gate: `ADR-NNN`, `<sprint>.<num>[<letra>]`, `PLAN-<slug>`, `CHG-YYYY-MM-DD-<scope>`, `TRACK-<slug>`, `RULE-<slug>`.
3. **Wikilinks `[[X]]`** dentro da vault (graph view + backlinks); markdown links em `CLAUDE.md`, `README.md` e PRs externos (rendering GitHub).
4. **Tags hierárquicas** consultáveis sem plugin: `type/`, `area/`, `sprint/`, `status/`, `priority/`, `methodology/`.
5. **Índices em duas camadas** com separação física rígida:
   - `docs/_MOC/_generated/` — índices auto-regenerados por `dev/build_doc_index.py` (INDEX, ADR_INDEX, SPRINT_CURRENT, CHANGELOG_RECENT, ROADMAP, PLAN_PROGRESS). Snapshot test bloqueia drift.
   - `docs/_MOC/` — índices editoriais manuais (`00-INDEX.md` entry-point, `SPRINTS-active.md` overview narrativo, `PLANS-active.md` curating de status).
6. **Plano e Sprint ortogonais via frontmatter**: lane tem `sprint: A10` (FK obrigatória) e `plan: PLAN-X` (FK opcional). Índice gerado `PLAN_PROGRESS.md` agrega lanes por plano.
7. **Dataview opt-in** — vault funciona sem ele; aceita como aceleração.
8. **`CLAUDE.md` permanece na raiz fora da vault**, mas perde tabelas de status (Sprint A7/A10/Direção E) e §Hotspots; passa a apontar para paths estáveis (`docs/_MOC/_generated/SPRINT_CURRENT.md`) cujo conteúdo é dinâmico.
9. **`README.md`, `ROADMAP.md`, `PRODUCT.md` ajustados:**
   - `README.md`: remove status duplicado (linha 5); aponta para `docs/_MOC/_generated/ROADMAP.md`.
   - `ROADMAP.md`: deletado (cabeçalho narrativo é deadcode); tabela "Visão geral das fases F0-F11" migra para `docs/reference/PHASES.md` (evergreen).
   - `PRODUCT.md`: move para `docs/reference/PRODUCT.md`.
10. **Codegen idempotente com snapshot test** seguindo padrão consolidado em ADR-076 (design tokens YAML→TS) e ADR-109 (OpenAPI snapshot). Pre-commit + CI.
11. **Schema validation** com JSON Schema em `docs/_schemas/note-*.schema.json`, alinhado com `config/schemas/*.schema.json` existente.

Migração em 5 fases sequenciais (~26-28h em ~3 dias calendário), detalhada no [plano DOC_REORG arquivado](../archive/DOC_REORG_PLAN-2026-05-07.md). Janelas de pausa explícitas para fases 2 (split DECISIONS, ~24h) e 4 (split BACKLOG, ~24-48h).

**Alternativas consideradas:**

1. **Vault em pasta nova `vault/`** — quebra ~50 paths hardcoded em CLAUDE.md, scripts `dev/`, GitHub workflows, prompts em sessões antigas. Custo de migração desproporcional ao ganho conceitual. **Rejeitada.**
2. **Mega-arquivos com frontmatter inline** (Modelo B do brainstorm CTO) — mantém DECISIONS/BACKLOG/CHANGELOG, adiciona frontmatter por seção, índice gerado. Não resolve nenhuma das 5 sobreposições diagnosticadas; vault Obsidian fica funcional só com Dataview (viola requisito explícito); ROI negativo. **Rejeitada.**
3. **Zettelkasten radical** (Modelo C — ~400 notas atômicas, invariantes do CLAUDE.md viram zettels) — arquiteturalmente mais elegante, mas custo de migração 50-70h + disciplina contínua de hygiene Zettelkasten que time de 1-3 devs não sustenta. **Rejeitada.**
4. **Hub-and-spoke / dual-source** (Modelo D — mantém mega-arquivos como source-of-truth, gera vault zettel por codegen) — duplica fonte de verdade, drift duplo, edição humana descartada na vault gerada. **Rejeitada.**
5. **Adicionar SQLite layer** (M4 do data-engineer — `docs/_MOC/_generated/notes.sqlite` para queries grafo/agregação) — útil para queries cross-cutting (ex.: "ADRs sobre auth superseded em 2025-2026"); ganho marginal vs complexidade extra. **Adiada para sprint posterior** quando aparecer demanda concreta.

**Trade-offs explícitos:**

- **Ganho de tokens (estimado por benchmark de 6 queries):** queries comuns (status de sprint, lanes prontas, o-que-mudou-na-semana) reduzem 90-99%; deep-dive cross-ADR reduz 40-50% sem SQLite. Ordem de magnitude validada nos 2 brainstorms.
- **Janela de migração:** ~28h em ~3 dias calendário; pausas obrigatórias 24-48h em hotspots durante Fases 2 e 4.
- **Volume de arquivos:** +250 arquivos em `docs/` (175 adr/ + ~70 lanes + 7 plans + ~40 outros). `ls` CLI fica menos amigável; mitigação: tags hierárquicas + Obsidian + MOCs.
- **Wikilinks `[[X]]` não renderizam clicáveis no GitHub.** Mitigação: convenção mista — wikilinks dentro da vault, markdown links em CLAUDE.md/README/PRs (consumo externo).
- **Disciplina contínua:** frontmatter sempre populado, status sempre atualizado. Gates protegem ~80% (schema, links, supersedure, stale detector); ~20% depende de cultura.
- **Compatibilidade externa:** shims em `DECISIONS.md`, `BACKLOG.md`, `CHANGELOG.md` preservam paths hardcoded em PRs antigos, prompts em sessões anteriores e referências externas.

**Critério de aceite (gate de promoção `Proposto` → `Decidido`):**

- [ ] Plano executivo DOC_REORG revisado e aprovado pelo usuário.
- [ ] Fase 1 entregue: schemas JSON em `docs/_schemas/`, `dev/build_doc_index.py`, `dev/validate_frontmatter.py`, `dev/check_doc_links.py`, ADR exemplo migrada com gates verdes.
- [ ] Fases 2-5 entregues conforme plano DOC_REORG com critério de aceite mensurável por fase.
- [ ] Snapshot test `tests/test_doc_indexes_snapshot.py` verde (índices em `_MOC/_generated/` regenerados sem drift).
- [ ] Token-cost-benchmark roda em CI: queries Q2/Q3/Q7 do brainstorm (lanes prontas, o-que-mudou-na-semana, sprint atual) reduzem ≥90%. Baseline e meta documentados em `tests/benchmarks/doc_token_cost.json`.
- [ ] Vault abre no Obsidian out-of-the-box: smoke test manual confirma graph view, backlinks, painel de tags, busca por path/tag funcionando sem plugin obrigatório (Dataview opcional).
- [ ] CLAUDE.md §"Onde procurar contexto adicional" atualizado com novos paths estáveis; §Hotspots removido (não há mais hotspots de 6k linhas).
- [ ] `README.md`, `PRODUCT.md`, `ROADMAP.md` ajustados conforme decisão item 9.
- [ ] Drift zero entre status de sprint: única fonte é `docs/sprint/<current>/_README.md` (frontmatter `status`); demais fontes derivam.
- [ ] Product-manager review da UX final da vault (graph view, taxonomia de tags, onboarding) antes de promoção a `Decidido`.

**Plano de implementação:** [DOC_REORG_PLAN-2026-05-07.md](../archive/DOC_REORG_PLAN-2026-05-07.md).
