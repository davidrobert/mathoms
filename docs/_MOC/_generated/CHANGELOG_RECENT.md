> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — últimos 14 dias

32 entries entre 2026-05-10 e 2026-05-21.

## 2026-05-21 (8 entries)

- [[CHG-2026-05-21-A17-L1-PREVIDENCIA-SHIPPED]] — feat(adr-238): A17 L1 (previdência privada PGBL/VGBL) entregue em 5 PRs (lane [[A17.l1]])
- [[CHG-2026-05-21-DOCS-A17-L3-WISE-ADDED]] — docs(a17-l3): adiciona Wise (conta multi-moeda no exterior) ao escopo (lane [[A17.l3]])
- [[CHG-2026-05-21-DOCS-ADR-238-PROPOSTO]] — docs(adr-238): Proposto — Ingestão de Informes de Rendimentos anuais (lane [[A17.l1]])
- [[CHG-2026-05-21-DOCS-ADR-239-PROPOSTO]] — docs(adr-239): Proposto — Comprovantes de Bem (CRLV) + Apólices polimórficas (lane [[A18.l1]])
- [[CHG-2026-05-21-DOCS-ADR-240-PROPOSTO]] — docs(adr-240): Proposto — Card S_PROTECAO no relatório como 4º pilar AUVP (lane [[A19.l1]])
- [[CHG-2026-05-21-FEAT-ADR-236-P1-BUSINESS-PROFILE]] — feat(adr-236 P1): BusinessProfile expandido com 4 campos A16 + admin (lane [[TRACK-a16-adr236-tributario-pj-cascata]])
- [[CHG-2026-05-21-FEAT-ADR-236-P2-CLASSIFIER-PJ-IRPF]] — feat(adr-236 P2): classifier E4 com 5 labels PJ-side + leitor IRPF (lane [[TRACK-a16-adr236-tributario-pj-cascata]])
- [[CHG-2026-05-21-FEAT-ADR-236-P6-CUTOVER-TELEMETRIA]] — feat(adr-236 P6): cutover + telemetria LGPD-safe + flip ADR-236 para (lane [[TRACK-a16-adr236-tributario-pj-cascata]])

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

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
