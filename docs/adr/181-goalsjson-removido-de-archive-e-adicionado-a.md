---
id: ADR-181
type: adr
title: "`goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py`"
status: Decidido
phase: "Sprint A10.8"
date: "2026-05-06"
relates_to: ["[[ADR-077]]", "[[ADR-180]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 181"]
tags:
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 56
---

# ADR-181 — `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py`

**Status:** Decidido (Sprint A10.8) • **Data:** 2026-05-06 • **Data de decisão:** 2026-05-07 • **Relaciona** [ADR-077](#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web), [ADR-180](#adr-180--goalsjson-cutover-final-via-stageconfigconfig_store-extendido). **Origem:** Sprint A10 W0 — `archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §6.2` (arquivado em [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md](archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md)).

**Contexto:** Após ADR-180 fechar a leitura runtime de `goals.json`, o arquivo arquivado `_archive/pre-f8-cutover-2026-04-15/config/goals.json` perde valor referencial — todas as 22 chaves migraram para `Decision`/`Risk` aggregates, rules-as-code (ADR-177), Goal types existentes ou foram deletadas como dead-data (ADR-168 cleanup). Manter o arquivo arquivado convida confusão: futuro engenheiro abrindo `_archive/` pode pensar que é referência viva. A semântica correta é cleanup final + bloqueio de recriação acidental no path original.

ADR-077 (Sprint A7) bloqueou 5 arquivos `config/*.json` migrados via `dev/check_forbidden_paths.py`. `goals.json` é o último desse cluster — fechá-lo encerra Sprint A10 e o débito de Sprint A7.

**Decisão:** No PR final da Sprint A10 (lane A10.8):

1. **Deletar** `_archive/pre-f8-cutover-2026-04-15/config/goals.json` (`git rm`).
2. **Substituir** por `_archive/pre-f8-cutover-2026-04-15/config/goals.json.MIGRATED.md` documentando o **mapa chave→destino** das 22 chaves (formato similar ao [ADR-168 banner em ADR-117](#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)).
3. **Adicionar** `config/goals.json` (path original) a `dev/check_forbidden_paths.py` — hook bloqueia recriação acidental.
4. **Não criar** novo Goal type `BUDGET_CEILING` (delete `tetos_orcamentarios` + `viagens.teto_anual` em A10.1 sem replacement; ressurreita em sprint dedicada quando UI de orçamento entrar).

`goals.json.MIGRATED.md` formato esperado:

```markdown
# goals.json — mapa de migração (Sprint A10, 2026-05-XX)

Arquivo arquivado em F8.4 (2026-04-15), runtime materialization removida em A10.6 (ADR-180), arquivo deletado em A10.8 (esta).

## Mapa chave → destino

| Chave do legado | Destino | ADR/Lane |
|---|---|---|
| `aportes` | Goal type `APORTE_MENSAL` | F8.4 (existente) |
| `independencia_financeira` | Goal type `INDEPENDENCIA_FINANCEIRA` | F8.1 (existente) |
| ... (22 entries totais) ... |
```

**Alternativas consideradas:**

1. **Manter `_archive/.../goals.json` como referência histórica** — a referência histórica é o conteúdo do arquivo na revisão git da F8.4 (`git show <commit>:config/goals.json`); manter cópia em `_archive/` duplica histórico e convida confusão.
2. **Criar Goal type `BUDGET_CEILING` agora** — sem UI de orçamento concreta, abstração prematura (CLAUDE.md §Code style: "três linhas similares > abstração prematura"). Ressurreita quando feature materializar.
3. **Deletar + bloquear path + escrever `MIGRATED.md` (escolhida)** — cleanup completo; rastro mínimo necessário; bloqueio impede recriação acidental.

**Trade-offs explícitos:**

- **Ganho:** Sprint A10 fechada com cleanup final; ADR-077 checkbox marcado; futuro engenheiro vê `MIGRATED.md` quando procura `goals.json` no `_archive/` e entende o que aconteceu.
- **Custo:** ~0.5d (PR de cleanup com mapa documentado).
- **Risco:** baixo. Nenhum leitor vivo após A10.6 (validado pelo gate empírico ADR-180).

**Critério de aceite:**

- [ ] `_archive/pre-f8-cutover-2026-04-15/config/goals.json` deletado via `git rm`.
- [ ] `_archive/pre-f8-cutover-2026-04-15/config/goals.json.MIGRATED.md` criado com mapa de 22 chaves → destinos.
- [ ] `config/goals.json` adicionado a `dev/check_forbidden_paths.py`.
- [ ] Hook `pre-commit` bloqueia tentativa de criar `config/goals.json` (validado por test).
- [ ] ADR-077 checkbox "100% dos campos lidos pelo E5/E5.N/E6" marcado ✅ + linha "Fechado por ADR-180" adicionada.
- [ ] ADR-180 vira `Decidido (Sprint A10)`; ADR-181 idem.
- [ ] Sprint A10 status global em BACKLOG marcado ✅.

**Plano de implementação:** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md §6.2](archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (lane A10.8).
