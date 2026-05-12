> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — últimos 14 dias

66 entries entre 2026-04-29 e 2026-05-12.

## 2026-05-12 (5 entries)

- [[CHG-2026-05-12-FEAT-AUVP-THRESHOLD-PGBL-VARIANT]] — feat(report): threshold AUVP modula variante visual do card (lane [[TRACK-auvp-threshold-pgbl-variant]])
- [[CHG-2026-05-12-FEAT-IRPF-OTIMIZACAO-CARDS-REVIVAL]] — feat(report): reativa cards Dependentes Declarados + Dedutíveis (lane [[TRACK-irpf-otimizacao-cards-revival]])
- [[CHG-2026-05-12-FEAT-REPORT-S9-EXPANSION]] — feat(report): S9 expandida — 4 cards + bubble re-enquadrado (lane [[A11.w5]])
- [[CHG-2026-05-12-FEAT-S9-PROTECTION-CALCULATORS]] — feat(domain): 4 calculators determinísticos protection + auto-inferência (lane [[A11.w5]])
- [[CHG-2026-05-12-TEST-S9-GOLDENS-CLOSE-TRACK]] — test(report): reset goldens E5 + paridade narrativa S9 (ADR-192, S9-T06) (lane [[A11.w5]])

## 2026-05-11 (8 entries)

- [[CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-BACKEND]] — feat(api): backend API completo do learning loop — preview, commit, (lane [[A12.cat-learning-loop]])
- [[CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-FRONTEND]] — feat(frontend): P4 learning loop UI mínima (toast + modal + badge) + (lane [[A12.cat-learning-loop]])
- [[CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-PIPELINE]] — feat(pipeline): CategorizationRulesV2 com ordem de match estável, (lane [[A12.cat-learning-loop]])
- [[CHG-2026-05-11-FEAT-FRONTEND-RENTABILIDADE]] — feat(frontend): card Rentabilidade rebrandeado — TRS efetiva full-width + KPI hero (lane [[A11.w5]])
- [[CHG-2026-05-11-FEAT-PIPELINE-RENTABILIDADE]] — feat(pipeline): card Rentabilidade — TRS efetiva enriquecida + cobertura (lane [[A11.w5]])
- [[CHG-2026-05-11-FEAT-REPORT]] — feat(report): PGBL diagnóstico tipificado em 4 estados substitui métrica (lane [[TRACK-pgbl-card-diagnostico]])
- [[CHG-2026-05-11-FEAT-REPORT-ALOCACAO]] — feat(report): card AlocacaoAtualVsAlvoCard substitui 3 cards S3 (Fase A (lane [[A12.alocacao-v2]])
- [[CHG-2026-05-11-FEAT-S9-PROTECTION-AGGREGATE]] — feat(backend): Protection aggregate + ProtectionBundle skeleton (ADR-192 (lane [[A11.w5]])

## 2026-05-10 (2 entries)

- [[CHG-2026-05-10-FEAT-CAT-LEARNING-LOOP-SCHEMA]] — feat(db): tabela categorization_rules + transaction_overrides.source/rule_id — (lane [[A12.cat-learning-loop]])
- [[CHG-2026-05-10-FEAT-REPORT-PUBLICATION]] — feat(report): conceito de mês fechado imutável — tabela report_publications, (lane [[A11.report-publication]])

## 2026-05-07 (14 entries)

- [[CHG-2026-05-07-A10-1]] — A10.1 ✅. - **A10.1 ✅** Dead-data deletion + ADR-168 cleanup narrativas órfãs. (lane [[A10.1]])
- [[CHG-2026-05-07-A10-2]] — A10.2 ✅. - **A10.2 ✅** Rules-as-code consolidation (ADR-177 → `Decidido (Sprint A10.2)`). (lane [[A10.2]])
- [[CHG-2026-05-07-A10-3]] — A10.3 ✅. - **A10.3 ✅** Decision schema extension (ADR-179 → `Decidido (Sprint A10.3)`). (lane [[A10.3]])
- [[CHG-2026-05-07-A10-4]] — A10.4 ✅. - **A10.4 ✅** `Risk` aggregate (ADR-178 → `Decidido (Sprint A10.4)`). (lane [[A10.4]])
- [[CHG-2026-05-07-A10-5]] — A10.5 ✅. - **A10.5 ✅** Top5 + Bubble como projeção (charts_narrator switch). (lane [[A10.5]])
- [[CHG-2026-05-07-A10-6]] — A10.6 ✅. - **A10.6 ✅** Pipeline cutover via `StageConfig.config_store` extendido (ADR-180 → `Decidido (Sprint A10.6)`). (lane [[A10.6]])
- [[CHG-2026-05-07-A10-7]] — A10.7 ✅. - **A10.7 ✅** Seed refactor + `Workspace.business_profile_json` (Sprint A10.7). (lane [[A10.7]])
- [[CHG-2026-05-07-A10-8]] — A10.8 ✅. - **A10.8 ✅** Cutover final + `forbidden_paths` (ADR-181 → `Decidido (Sprint A10.8)`). (lane [[A10.8]])
- [[CHG-2026-05-07-A7-5]] — Direção E — Onda 2 + Onda 3: redesign de interfaces (2026-04-28/29). - **Direção E — Onda 2 + Onda 3: redesign de interfaces (2026-04-28/29):** Brainstorm convergiu em Direção E (refinada por product-designer + financial-planner). (lane [[A7.5]])
- [[CHG-2026-05-07-ADR-177]] — ADR-177. - **ADR-177** Proposto — Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`).
- [[CHG-2026-05-07-ADR-178]] — ADR-178. - **ADR-178** Proposto — `Risk` aggregate workspace-scoped.
- [[CHG-2026-05-07-ADR-179]] — ADR-179. - **ADR-179** Proposto — `Decision` aggregate — extensão de schema (`impact_1y/10y_brl_cents`, `horizon`, `priority`).
- [[CHG-2026-05-07-ADR-180]] — ADR-180. - **ADR-180** Proposto — `goals.json` cutover final via `StageConfig.config_store` extendido.
- [[CHG-2026-05-07-ADR-181]] — ADR-181. - **ADR-181** Proposto — `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py`.

## 2026-05-06 (14 entries)

- [[CHG-2026-05-06-A8-4]] — refactor(report,frontend,config): A8.4 PR4 — remoção do Modo USA inteiro (ADR-168) (2026-05-06). - **refactor(report,frontend,config): A8.4 PR4 — remoção do Modo USA inteiro (ADR-168) (2026-05-06):** Modo USA do relatório (U1 Mudança EUA F1/F2 + U2 Green Ca (lane [[A8.4]])
- [[CHG-2026-05-06-A8-4-1]] — chore(docs,config): A8.4 PR5 — limpeza editorial final de copy USA-related (2026-05-06). - **chore(docs,config): A8.4 PR5 — limpeza editorial final de copy USA-related (2026-05-06):** Limpeza editorial de strings família-específicas em docs de spec/ (lane [[A8.4]])
- [[CHG-2026-05-06-A8-4-2]] — refactor(pipeline): A8.4 PR2 — eligibility gate + analyzer reduzido a 1 cenário (ADR-167) (2026-05-06). - **refactor(pipeline): A8.4 PR2 — eligibility gate + analyzer reduzido a 1 cenário (ADR-167) (2026-05-06):** `CenariosConjugeAnalyzer` reduzido de 3 cenários f (lane [[A8.4]])
- [[CHG-2026-05-06-A8-4-3]] — refactor(pipeline,backend,frontend): A8.4 PR1 — schema estável `cenarios_conjuge` no payload E5 (ADR-166) (2026-05-06). - **refactor(pipeline,backend,frontend): A8.4 PR1 — schema estável `cenarios_conjuge` no payload E5 (ADR-166) (2026-05-06):** Chave do bloco "Cenários do cônjug (lane [[A8.4]])
- [[CHG-2026-05-06-A8-4-4]] — docs(plan): A8.4 Cenários de Estresse — plano canônico + lane no BACKLOG (2026-05-06). - **docs(plan): A8.4 Cenários de Estresse — plano canônico + lane no BACKLOG (2026-05-06):** [docs/plan/CENARIOS_ESTRESSE/_README.md](plan/CENARIOS_ESTRESSE/_README.md) entregu (lane [[A8.4]])
- [[CHG-2026-05-06-DOCS-DECISIONS]] — docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06). - **docs(decisions,plan): ADR backfill Wave 1 + CLAUDE.md sync (W1-T03 + W1-T06 · 2026-05-06):** Backfill de 6 ADRs `Proposto` — ADR-170 (refresh tokens family-
- [[CHG-2026-05-06-FEAT-FRONTEND]] — feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06). - **feat(frontend): CSS gate + tokens fantasma corrigidos (W1-T01 · 2026-05-06):** Onda 1 do `plan/PLATFORM_REVIEW/_README.md` — fecha cluster PD-001/002/005/023.
- [[CHG-2026-05-06-FEAT-SCHEMAS]] — feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06). - **feat(schemas): cenarios_conjuge formal em e5_analysis.schema (W1-T08 · 2026-05-06):** Fecha gap deixado por ADR-166 — `CenariosConjugeAnalyzer.to_legacy_dic
- [[CHG-2026-05-06-FIX-BACKEND]] — fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06). - **fix(backend): PDF semaphore (BB-009) + SECRET_KEY fail-fast prod (SR-022 · 2026-05-06):** W1-T04 + W1-T05 do PLATFORM_REVIEW_PLAN.
- [[CHG-2026-05-06-FIX-DOCUMENTS]] — fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06). - **fix(documents): "Sem extrato" enganoso em investment_report misclassificado (2026-05-06):** Filename `itau_extratoconta_*.xls` cujo conteúdo é Posição de In
- [[CHG-2026-05-06-FIX-PIPELINE]] — fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06). - **fix(pipeline): regras suggestion dormentes + carry-trade endividamento (W1-T02 + W1-T07 · 2026-05-06):** Findings FP-001/2/3/9 do platform review.
- [[CHG-2026-05-06-FIX-PIPELINE-1]] — fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06). - **fix(pipeline): modo incremental respeitado por stages globais E1 (ADR-169 · 2026-05-06):** Antes: clicar "Processar somente novos" reprocessava todas as dec
- [[CHG-2026-05-06-PR77]] — refactor(report): _find_top_asset usa fonte canônica top_ativos + schema E5 declara contrato (2026-05-06). - **refactor(report): _find_top_asset usa fonte canônica top_ativos + schema E5 declara contrato (2026-05-06):** Cleanup pós-PR #77.
- [[CHG-2026-05-06-PR87]] — refactor(report): _extract_top_institutions usa fonte canônica + schema E5 ganha instituicoes_por_membro/n_imoveis_total (2026-05-06). - **refactor(report): _extract_top_institutions usa fonte canônica + schema E5 ganha instituicoes_por_membro/n_imoveis_total (2026-05-06):** Cleanup pós-PR #87.

## 2026-05-05 (11 entries)

- [[CHG-2026-05-05-A8-3]] — feat(report): Lane A8.3 — TRS efetiva + carteira de renda em S7 (2026-05-05). - **feat(report): Lane A8.3 — TRS efetiva + carteira de renda em S7 (2026-05-05):** Independência Financeira agora confronta **TRS meta** (5%/4% — D15) com **TR (lane [[A8.3]])
- [[CHG-2026-05-05-F9-3]] — feat(db): F9.3 — Alembic stage rename migration validada (ADR-093) (2026-05-05). - **feat(db): F9.3 — Alembic stage rename migration validada (ADR-093) (2026-05-05):** `q5r6s7t8u9v0_rename_stage_identifiers.py` sincronizado com `STAGE_RENAME (lane [[F9.3]])
- [[CHG-2026-05-05-FEAT-DB]] — feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05). - **feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05):** Migration final após 7 dias de validação pós-M2 (2026-04-29).
- [[CHG-2026-05-05-FEAT-PIPELINE]] — feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05). - **feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05):** Simulação estocástica de Independência Financeira com 3 percentis.
- [[CHG-2026-05-05-PR46]] — refactor(pipeline): deprecate calculators.py (2026-05-05). - **refactor(pipeline): deprecate calculators.py (2026-05-05):** PR [#46](https://github.com/davidrobert/mathoms/pull/46).
- [[CHG-2026-05-05-PR47]] — fix(backend): canonical stage names em artifact_reader (2026-05-05). - **fix(backend): canonical stage names em artifact_reader (2026-05-05):** `dashboard_service.py` usava `"E5"` (legado) em vez de `"analyze_finances"`; `transac
- [[CHG-2026-05-05-PR48]] — test(e2e): fix stale selectors em vault e config-round-trip (2026-05-05). - **test(e2e): fix stale selectors em vault e config-round-trip (2026-05-05):** PR [#48](https://github.com/davidrobert/mathoms/pull/48).
- [[CHG-2026-05-05-PR49]] — feat(frontend): FreeTierSkippedBanner no pipeline monitor (2026-05-05). - **feat(frontend): FreeTierSkippedBanner no pipeline monitor (2026-05-05):** PR [#49](https://github.com/davidrobert/mathoms/pull/49).
- [[CHG-2026-05-05-PR50]] — refactor(backend): decompose content_classifier monolith (2026-05-05). - **refactor(backend): decompose content_classifier monolith (2026-05-05):** Módulo `content_classifier.py` com 727 LOC decomposto em 3 módulos focados sem alte
- [[CHG-2026-05-05-PR51]] — feat(ui): Onda 9 — design system polish + mobile (2026-05-05). - **feat(ui): Onda 9 — design system polish + mobile (2026-05-05):** Unificação de 3 primitivos de design system + 2 fixes de produto + ergonomia mobile.
- [[CHG-2026-05-05-PR56]] — feat(db): M3 drop _legacy_kanban_items + _legacy_report_notes (ADR-154) (2026-05-05). - **feat(db): M3 drop _legacy_kanban_items + _legacy_report_notes (ADR-154) (2026-05-05):** PR [#56](https://github.com/davidrobert/mathoms/pull/56).

## 2026-05-04 (2 entries)

- [[CHG-2026-05-04-A10-FEAT-SUGGESTIONS-DEC]] — feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04). - **feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04):** Fecha 6 gaps identificados na revisão de produto 2026-04-29: - **#1 (ADR-161):*
- [[CHG-2026-05-04-FEAT-API]] — feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04). - **feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04):** Endpoints `POST /api/v1/me/data-export`, `GET /me/data-expo

## 2026-04-30 (3 entries)

- [[CHG-2026-04-30-A8-2]] — test(pipeline): IRPF full schema goldens — A8.2 sub-lane (2026-04-30). - **test(pipeline): IRPF full schema goldens — A8.2 sub-lane (2026-04-30):** 3 fixtures sintéticas (`tests/fixtures/llm_golden/e16_irpf_full_{completo,simplific (lane [[A8.2]])
- [[CHG-2026-04-30-FEAT-PIPELINE]] — feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30). - **feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30):** novo stage paralelo a `extract_baseline` que captura **todo** o co
- [[CHG-2026-04-30-FEAT-REPORT]] — feat(report): seções IRPF no relatório premium — UI lane (2026-04-30). - **feat(report): seções IRPF no relatório premium — UI lane (2026-04-30):** materializa os 6 KPIs do `IRPFAnalyzer` (já em produção via E5 try-read) em duas se

## 2026-04-29 (7 entries)

- [[CHG-2026-04-29-A10-DIRE-O-E-DASHBOARD-A]] — Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29). - **Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29):** Cumpre a agenda da Direção E original que declarou "/dashboard será absorvido
- [[CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-KANB]] — Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29). - **Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29):** Onda 1 da Direção E entregue como migration **M1 additive**
- [[CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-M2-S]] — Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29). - **Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29):** M2 da Onda 1 entregue como **estratégia conservadora** — RENAME + endpoints 410 Gone em
- [[CHG-2026-04-29-A10-DIRE-O-E-ONDA-4-ONDA]] — Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29). - **Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29):** **Onda 4 entregue (`/plano` executive summary):** novos componentes em
- [[CHG-2026-04-29-A10-DIRE-O-E-ONDA-7-BLOQ]] — Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29). - **Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29):** os 5 fixes da [track_onda_7_p0_blockers.md](agent_prompts/track_onda_7_p0_blockers.md) entregu
- [[CHG-2026-04-29-A10-DIRE-O-E-P-S-REVIS-O]] — Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29). - **Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29):** Revisão completa das interfaces consolidadas (Plano + Ação + Relatório) executada com
- [[CHG-2026-04-29-FIX-SUGGESTIONS]] — fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29). - **fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29):** rodar o pipeline completo deixava `/acao` Inbox e `SuggestionCallout` do relat

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
