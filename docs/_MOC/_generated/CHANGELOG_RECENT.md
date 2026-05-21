> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — últimos 14 dias

40 entries entre 2026-05-07 e 2026-05-21.

## 2026-05-21 (2 entries)

- [[CHG-2026-05-21-FEAT-ADR-236-P1-BUSINESS-PROFILE]] — feat(adr-236 P1): BusinessProfile expandido com 4 campos A16 + admin (lane [[TRACK-a16-adr236-tributario-pj-cascata]])
- [[CHG-2026-05-21-FEAT-ADR-236-P2-CLASSIFIER-PJ-IRPF]] — feat(adr-236 P2): classifier E4 com 5 labels PJ-side + leitor IRPF (lane [[TRACK-a16-adr236-tributario-pj-cascata]])

## 2026-05-20 (3 entries)

- [[CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO]] — feat: Sprint A15 — FU-3 imóvel financiado (ADR-227 Decidido). Cria agregado
- [[CHG-2026-05-20-FEAT-ADR-235-NU-PROPRIETARIO]] — feat(adr-235): adiciona classification `nu_proprietario` ao enum — (lane [[TRACK-a16-adr235-nu-proprietario-flip]])
- [[CHG-2026-05-20-FEAT-BACKEND-SECURITY-HEADERS]] — feat(backend): security headers + CORS strict no FastAPI (ADR-232). Middleware (lane [[A11.w2]])

## 2026-05-15 (1 entries)

- [[CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN]] — refactor(decisions): Decision.code passa a ser server-generated com (lane [[A12.decision-code-autogen]])

## 2026-05-14 (2 entries)

- [[CHG-2026-05-14-FEAT-PLANNER-ATO6-TELEMETRIA-CUTOVER]] — feat(planner): Ato 6 (último) — telemetria M4 + cross-provider weekly + (lane [[A12.planner-review-ato6]])
- [[CHG-2026-05-14-REFACTOR-REMOVE-REVIEW-FINANCES]] — refactor(pipeline): remove stage `review_finances` (E7-review) + dependente (lane [[A12.planner-review-cleanup]])

## 2026-05-12 (8 entries)

- [[CHG-2026-05-12-FEAT-AUVP-THRESHOLD-PGBL-VARIANT]] — feat(report): threshold AUVP modula variante visual do card (lane [[TRACK-auvp-threshold-pgbl-variant]])
- [[CHG-2026-05-12-FEAT-IRPF-OTIMIZACAO-CARDS-REVIVAL]] — feat(report): reativa cards Dependentes Declarados + Dedutíveis (lane [[TRACK-irpf-otimizacao-cards-revival]])
- [[CHG-2026-05-12-FEAT-IRPF-SIMPLIFICADO-COMPONENTES-PGD-MIR]] — feat(frontend): Estado 2 (modelo_simplificado) do
- [[CHG-2026-05-12-FEAT-PGBL-CARDS-RECONCILIATION]] — feat(frontend): reconciliação dos cards PGBL S7×IRPF — Card A
- [[CHG-2026-05-12-FEAT-REPORT-S9-EXPANSION]] — feat(report): S9 expandida — 4 cards + bubble re-enquadrado (lane [[A11.w5]])
- [[CHG-2026-05-12-FEAT-S9-PROTECTION-CALCULATORS]] — feat(domain): 4 calculators determinísticos protection + auto-inferência (lane [[A11.w5]])
- [[CHG-2026-05-12-FIX-IRPF-DEDUTIVEIS-CHIP-REGIME]] — fix(frontend): chip "Espaço de R$ X" no card Dedutíveis Aplicados vira (lane [[TRACK-irpf-otimizacao-cards-revival]])
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

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
