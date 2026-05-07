---
id: ADR-100
type: adr
title: "A6d commitment: fechar Caminho B puro nos 5 stages pragmáticos"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 100"]
tags:
  - area/pipeline
  - phase/a6d
  - status/decidido
  - type/adr
size_lines: 66
---

# ADR-100 — A6d commitment: fechar Caminho B puro nos 5 stages pragmáticos

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6d
**Supersedes:** nota original de A6d como "opcional" no plano inicial

**Contexto:** ADR-099 deixa explícito que Caminho B pragmático é trade-off
temporário. A questão: converter ou não para puro?

Hoje 14+ domain services estão testados (1200+ testes) mas não invocados.
Custo de manter é baixo (já estáveis); custo de deletar seria perder
trabalho que tem valor arquitetural conhecido. Mas manter sem integrar é
**trabalho morto** — nunca paga seu custo.

Alternativas avaliadas:
- **Opção X** (integrar): executa A6d em 3-5 sessões grandes; fecha Caminho
  B puro; services passam a ser invocados. Valor arquitetural real.
- **Opção Y** (manter em prateleira indefinidamente): custo baixo, valor zero.
- **Opção Z** (deletar services): libera ~3500 linhas, mas perde
  investimento + bloqueia testabilidade futura.

**Decisão:** Executar **Opção X** (A6d) como commitment, não opcional.

Escopo de A6d dividido em 3 sub-fases:

**A6d.1 — Eliminação de globals nos 5 scripts** (padrão A3b replicado em
`e4_categorize`, `e5_analyze`, `e5n_narrativas`, `e7_review`,
`e15_consolidate`). Globais recebem defaults sensatos no módulo;
`_init_config(base_dir)` é opt-in via `main(root_dir=...)`. Teste estrutural
AST bloqueia regressão. ~1 sessão, ~20-30 testes.

**A6d.2 — Testabilidade dos `analyze_*` sem disco**. Extrair reads de
`life_plan_goals.md`, `tarefas.md`, `milhas.md`, `methodology.md` para shell;
funções ficam puras (recebem dict, retornam dict). Critério: `analyze_*`
testáveis com `{dict_input}` sem criar arquivo. ~2 sessões, ~60-80 testes.

**A6d.3 — Integração dos 14+ domain services em `main_with_store`**.
Refactor **por stage** (não big bang):
1. E4: `process_transactions` → composição `TransactionClassifier` +
   `CashFlowBuilder` + `BaselineNormalizer` + `InvestmentsConsolidator` +
   `E4CategorizerAdapter`.
2. E5.N: `build_narrativas` → composição (ou aceitar que E5.N é templating
   e manter legado).
3. E5: 13 `analyze_*` → `E5AnalyzerAdapter` (já existe desde A5c).
Cada refactor preserva golden de paridade. ~2-3 sessões grandes, ~200+ testes.

Ordem: A6d.1 → A6d.2 → A6d.3 (dependências: .2 depende de .1; .3 depende de .1+.2).

**Consequências:**
- ✅ Paga o investimento em foundation (A1/A3c/A5a/A5b/A5c).
- ✅ Testabilidade dos `analyze_*` habilita TDD futuro em mudanças de
  fórmulas financeiras.
- ✅ Elimina thread-unsafety dos globais — worker topology changes
  (gunicorn threads, asyncio pools) deixam de ser risco.
- ⚠️ Estimativa 3-5 sessões grandes — maior sessão continua sendo E5
  (1-2 sessões sozinha).
- ❌ Durante execução de A6d, risco de bug sutil em refactor (mitigado
  por golden de paridade).
- ❌ Bloqueia operacionalmente apenas LGPD/Obs **se** refactor quebrar —
  por isso A6d é independente de A6a-c e de §15/§16.

**Relação com A6a-e**: independente. Pode rodar em paralelo com cutover DB.
§15 (LGPD) e §16 (Observabilidade) não dependem de A6d.

**Artefatos:** [BACKLOG §A6d](BACKLOG.md#a6d--fechar-caminho-b-puro-nos-5-stages-pragmáticos-adr-100).
