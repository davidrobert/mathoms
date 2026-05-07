# `goals.json` MIGRATED — Sprint A10 (2026-05-07)

> Arquivo originalmente em `_archive/pre-f8-cutover-2026-04-15/config/goals.json`.
> Sprint A10 fechou cutover em 8 PRs (#104, #107, #108, #113, #116, #117, #118, #119).
> Arquivo deletado em A10.8 (esta lane). ADR-077 §"Contrato de cutover" fechado.
>
> Para arqueologia do conteúdo original, leia o git: `git show
> a59312a^:_archive/pre-f8-cutover-2026-04-15/config/goals.json` (commit
> imediatamente anterior à abertura da Sprint A10) ou versão pré-arquivamento
> em `git show <commit-pré-F8.4>:config/goals.json`.

## Sprint A10 — entrega resumida

| Onda | Lanes | Outcome |
|---|---|---|
| W0 | A10.0 | 5 ADRs (ADR-177..181) propostas em batch (PR #104) |
| W1 | A10.1, A10.2 | Dead-data ADR-168 deletada + rules-as-code consolidation |
| W2 | A10.3, A10.4, A10.7 | `Decision` schema extension + `Risk` aggregate + Seed refactor |
| W3 | A10.5, A10.6 | Top5/Bubble projections + Pipeline cutover (`GoalsBundle`) |
| W4 | A10.8 | Cleanup final + `forbidden_paths` (esta lane) |

## Mapa de migração — 22 chaves

Tipo metodológico (FP): **[U]**niversal · **[C]**liente · **[D]**erivada ·
**[H]**istórica/dead · **[M]**etodológica · **[O]**peracional.

| Chave original | Tipo | Destino | Lane | Commit-merge |
|---|---|---|---|---|
| `aportes` | C | Goal type `APORTE_MENSAL` (DTO `AporteGoalInputs`) | F8.4 (pré-A10) | — |
| `independencia_financeira` | C | Goal type `INDEPENDENCIA_FINANCEIRA` (DTO `IFGoalInputs`) | F8.1 (pré-A10) | — |
| `dolarizacao` | C | Goal type `DOLARIZACAO` | F8.4 (pré-A10) | — |
| `alocacao_alvo` | C | Goal type `ALOCACAO_ALVO` | F8.4 (pré-A10) | — |
| `decisoes_prioritarias` | D | Projeção do `Decision` aggregate (ADR-179 schema extension) | A10.3 + A10.5 | `ae934f8` + `e7df21f` |
| `top5_decisoes` | D | Projeção do `Decision` aggregate ordenada por `impact_1y_brl_cents DESC NULLS LAST` | A10.3 + A10.5 | `ae934f8` + `e7df21f` |
| `riscos_prioritarios` | C+U | Aggregate `Risk` (ADR-178) — bubble chart S9 vira projeção | A10.4 + A10.5 | `e325119` + `e7df21f` |
| `seguros` (`vida_term_min/max`) | U+C | Slot `SEGUROS` em `GoalsBundle` (ADR-180); Goal type dedicado em sprint posterior | A10.6 | `856735d` |
| `tributario` (`contador`, `regime`, `holding_prazo`) | C | `Workspace.business_profile_json` (Pydantic `BusinessProfile`) | A10.7 | `4b2f97b` |
| `tetos_orcamentarios` | C | **DELETADO** — ressurreita em sprint dedicada quando UI de orçamento entrar | A10.1 | `6c97349` |
| `viagens.teto_anual` | C | **DELETADO** (idem `tetos_orcamentarios`) | A10.1 | `6c97349` |
| `imoveis.yield_potencial_pct_min/max` | U | Rules-as-code: `pipeline/domain/services/methodology_constants.py::YIELD_POTENCIAL_FII_BR_PCT_MIN/MAX` | A10.2 | `1125ba5` |
| `thresholds.imovel_pct_patrimonio_ideal` | U | Rules-as-code: `IMOVEL_PCT_PATRIMONIO_IDEAL` | A10.2 | `1125ba5` |
| `thresholds.equity_pct_alvo_min/max` | U/C | Rules-as-code: `EQUITY_PCT_ALVO_DEFAULT_MIN/MAX` (override por cliente em sprint posterior via Goal `ALOCACAO_ALVO`) | A10.2 | `1125ba5` |
| `simulacao.aporte_reduzido_fator: 0.66` | U | Rules-as-code: `APORTE_REDUZIDO_FATOR_CONJUGE` em `cenarios_conjuge_analyzer.py` | A10.2 | `1125ba5` |
| `stress_test_imovel_queda_pct: 20` | U | Rules-as-code: `STRESS_TEST_IMOVEL_QUEDA_PCT` | A10.2 | `1125ba5` |
| `dashboard.aporte_match_keywords` | O | Constante `_APORTE_MATCH_KEYWORDS` em `backend/app/services/task_progress_service.py` | A10.2 | `1125ba5` |
| `dashboard.category_labels` | O | i18n no frontend (follow-up Sprint A11+) | A10.2 (preparada) | — |
| `dashboard.{thresholds,cycle_thresholds,...}` | O | Rules-as-code (ou deletadas se zero leitor) | A10.2 | `1125ba5` |
| `referencias.{livros,ferramentas,contatos_templates}` | M+C | Frontend estático (follow-up Sprint A11+ quando `/sobre` ou `/metodologia` entrar) | A10.2 (preparada) | — |
| `calendario_fallback[]` | O+M | Rules-as-code (após filtragem USA-only por ADR-168) | A10.2 | `1125ba5` |
| `fase_f1f2`, `mariana_eua`, `nclex_*`, `investimentos_blocos`, `aportes_destinos_detalhados` | H/D | **DELETADAS** — ADR-168 cleanup débito | A10.1 | `6c97349` |

## Fechamento

- **ADR-077 §"Contrato de cutover"** — checkbox `100% dos campos lidos pelo E5/E5.N/E6` ✅ fechado por ADR-180 (Sprint A10.6) + ADR-181 (Sprint A10.8).
- **ADR-180** (StageConfig bundle) → `Decidido (Sprint A10.6)`.
- **ADR-181** (cleanup final) → `Decidido (Sprint A10.8)`.

`config/goals.json` agora é path proibido em `dev/check_forbidden_paths.py` —
recriação acidental bloqueada por hook `pre-commit` (defesa em profundidade
junto com paths bloqueados desde Sprint A7).
