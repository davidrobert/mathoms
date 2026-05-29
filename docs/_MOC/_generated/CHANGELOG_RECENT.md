> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — últimos 14 dias

24 entries entre 2026-05-15 e 2026-05-29.

## 2026-05-29 (7 entries)

- [[CHG-2026-05-29-A20-L1-BACKEND-MULTISTAGE]] — A20.L1 — Dockerfile backend multi-stage com dual target (runtime / (lane [[A20.l1]])
- [[CHG-2026-05-29-A20-L2-SHA-PINNING]] — A20.L2 — SHA pinning de todas as bases por digest do índice multi-arch (lane [[A20.l2]])
- [[CHG-2026-05-29-A20-L3-PIPELINE-SERVICE-HARDENING]] — A20.L3 — pipeline-service non-root (P0.4) + healthcheck por service (D4). (lane [[A20.l3]])
- [[CHG-2026-05-29-A20-L6-COMPOSE-DEV]] — A20.L6 — docker-compose.dev.yml unificado (D1+D2). Stack dev completa em (lane [[A20.l6]])
- [[CHG-2026-05-29-A20-L7-MAKEFILE-ONBOARDING]] — A20.L7 — Makefile dev-*-docker + SETUP.md "Onboarding em <5min" (D3+D5). (lane [[A20.l7]])
- [[CHG-2026-05-29-A20-L8-POSTGRES-DRIVER]] — A20.L8 — swap do driver sync legado psycopg2-binary → psycopg[binary] v3 (lane [[A20.l8]])
- [[CHG-2026-05-29-ADR-238-DATA-ADESAO-NAO-HARDFAIL]] — fix(adr-238): data_adesao deixa de ser hard-fail em previdência regressiva.

## 2026-05-28 (1 entries)

- [[CHG-2026-05-28-ADR-271-INVEST-DEDUP-SHIPPED]] — feat(adr-271): dedup de investimentos cross-IRPF (cross-year + cross-declarante)

## 2026-05-22 (4 entries)

- [[CHG-2026-05-22-A18-L1-CRLV-SHIPPED]] — feat(adr-239): A18 L1 (CRLV-e + tabela vehicles + reconciliação fuzzy IRPF G02) (lane [[A18.l1]])
- [[CHG-2026-05-22-A18-L2-APOLICE-SHIPPED]] — feat(adr-239): A18 L2 (apólice polimórfica auto/residencial/combinada V1 (lane [[A18.l2]])
- [[CHG-2026-05-22-A18-L3-FIPE-SHIPPED]] — docs(adr-239): A18 L3 (FIPE refresh assíncrono via BrasilAPI) flippada (lane [[A18.l3]])
- [[CHG-2026-05-22-A19-L1-PROTECAO-SHIPPED]] — feat(adr-240): A19 L1 (card S_PROTECAO — 4º pilar AUVP Proteção Patrimonial) (lane [[A19.l1]])

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

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
