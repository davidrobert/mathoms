> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# CHANGELOG_RECENT — entregas recentes

Janela de 14 dias a partir da última entrega registrada (2026-06-12). 14 entries entre 2026-05-29 e 2026-06-12.

## 2026-06-12 (1 entries)

- [[CHG-2026-06-12-REMOVE-HISTORICO-CICLOS]] — Remove card 'Histórico de Ciclos' do Apêndice E do relatório React — duplicata single-pair do data.changelog (ADR-148) já exibido via SectionSnapshotDiff, com rótulo enganoso em apêndice forward-looking. Backlog W5 (série temporal multi-ciclo de KPIs) registrado no plano SNAPSHOT_CHANGELOG_V3 para a lacuna metodológica real.

## 2026-06-09 (2 entries)

- [[CHG-2026-06-09-BACKEND-CAT-LEGACY-SUNSET]] — backend(a12): sunset do CRUD legado /config/categories em 2 PRs ordenados (lane [[A12.cat-legacy-sunset]])
- [[CHG-2026-06-09-FEAT-AUTH-REFRESH-TOKENS]] — W3-T03 (SR-002): refresh tokens httpOnly com family revocation — rotação com

## 2026-06-08 (2 entries)

- [[CHG-2026-06-08-A23-L2]] — Substrato de golden number-level (dev/golden_diff.py + snapshot do view-model + (lane [[A23.l2]])
- [[CHG-2026-06-08-A23-L3]] — K4 natural_key v2 (moeda+direction, cents int via Decimal) como campo de contrato E2 (lane [[A23.l3]])

## 2026-06-03 (1 entries)

- [[CHG-2026-06-03-A23-L1]] — Gate F0 do plano Data Lineage fechado — 4 ADR Decididas (ADR-278/279/280/281) (lane [[A23.l1]])

## 2026-05-30 (1 entries)

- [[CHG-2026-05-30-A21-L7L8-LGPD]] — LGPD Art.37 (auditoria de acesso) + Art.18 (retenção enforçada). Reusa (lane [[A21.l7]])

## 2026-05-29 (7 entries)

- [[CHG-2026-05-29-A20-L1-BACKEND-MULTISTAGE]] — A20.L1 — Dockerfile backend multi-stage com dual target (runtime / (lane [[A20.l1]])
- [[CHG-2026-05-29-A20-L2-SHA-PINNING]] — A20.L2 — SHA pinning de todas as bases por digest do índice multi-arch (lane [[A20.l2]])
- [[CHG-2026-05-29-A20-L3-PIPELINE-SERVICE-HARDENING]] — A20.L3 — pipeline-service non-root (P0.4) + healthcheck por service (D4). (lane [[A20.l3]])
- [[CHG-2026-05-29-A20-L6-COMPOSE-DEV]] — A20.L6 — docker-compose.dev.yml unificado (D1+D2). Stack dev completa em (lane [[A20.l6]])
- [[CHG-2026-05-29-A20-L7-MAKEFILE-ONBOARDING]] — A20.L7 — Makefile dev-*-docker + SETUP.md "Onboarding em <5min" (D3+D5). (lane [[A20.l7]])
- [[CHG-2026-05-29-A20-L8-POSTGRES-DRIVER]] — A20.L8 — swap do driver sync legado psycopg2-binary → psycopg[binary] v3 (lane [[A20.l8]])
- [[CHG-2026-05-29-ADR-238-DATA-ADESAO-NAO-HARDFAIL]] — fix(adr-238): data_adesao deixa de ser hard-fail em previdência regressiva.

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
