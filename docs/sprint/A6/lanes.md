# Sprint A6 — Lanes (histórico)

> Tabela estática de todas as lanes da Sprint A6. Para detalhe operacional (frontmatter, dependências), ver [`lanes/<id>.md`](lanes/) populado por F4.A.

| ID | Title | Status | Ship date | Onda |
|---|---|---|---|---|
| [[A5f]] | E1.5c Caminho B | shipped | 2026-04-19 | — |
| [[A6a]] | LLM stages escrevendo via `ArtifactStore` | shipped | 2026-04-19 | — |
| [[A6b]] | Ativar `USE_DB_ARTIFACTS=true` + validar end-to-end | shipped | 2026-04-19 | — |
| [[A6b.5]] | Preparação para teste humano (ADR-103) | shipped | 2026-04-19 | — |
| [[A6b.flip]] | Flip do default global (ADR-118) | shipped | 2026-04-23 | — |
| [[A6-ux.livestep]] | Contrato `LiveStep` (ADR-119) | shipped | 2026-04-23 (saga 2026-04-25) | — |
| [[A6-readers.dbfirst]] | Readers DB-first com fallback disco (ADR-120) | shipped | 2026-04-23 | — |
| [[A6-human]] | Teste manual end-to-end (David, 46 checks) | shipped | 2026-04-24 | — |
| [[A6c]] | Deletar bridge + legados | shipped | 2026-04-24 | — |
| [[A6d.1]] | Eliminação de globals nos 5 scripts | shipped | 2026-04-24 | — |
| [[A6d.2]] | Testabilidade dos `analyze_*` sem disco | shipped | 2026-04-20 | — |
| [[A6d.3]] | Integração dos 14+ domain services em `main_with_store` | shipped | 2026-04-20 | — |
| [[A6e.1]] | Repos por aggregate (per-aggregate slice) | shipped | 2026-04-21 | 1 |
| [[A6e.2]] | DTO ↔ Model mapping | shipped | 2026-04-21 | 1 |
| [[A6e.3]] | Application layer (FamilyMember + Category + Goal) | shipped | 2026-04-21 | 2 |
| [[A6e.3b]] | Use cases ConfigBlob + Task + Document | shipped | 2026-04-22 | 2 |
| [[A6e.3c]] | Sweep `dict[str, Any]` → tipado em DTOs não-OPAQUE | shipped | 2026-04-22 | 3 |
| [[A6e.4]] | Routers finos | shipped | 2026-04-22 | 2 |
| [[A6e.5]] | Versionamento `/api/v1/` (ADR-108) | shipped | 2026-04-22 | 2 |
| [[A6e.events]] | Domain events tipados (ADR-115, ex-A6e.6) | shipped | 2026-04-22 | 2 |
| [[A6e.events-migration]] | Migrar `audit_log()` inline → `AuditLogEvent` | shipped | 2026-04-22 | 2 |
| [[A6e.events-followup]] | Ativar flag prod + remover cron | paused | aguarda F7 deploy | 2 |
| [[A6f.1]] | Pipeline-as-service (ADR-112) | shipped | 2026-04-21 | 2 |
| [[A6f.2]] | OpenAPI + codegen | shipped | 2026-04-20 | — |
| [[A6f.3]] | Structured logs JSON + OTel (ADR-110) | shipped | 2026-04-20 | — |
| [[A6f.4]] | DB schema language-neutral | shipped | 2026-04-20 | — |
| [[A6f.5a]] | Auth portability documentada (ADR-109) | shipped | 2026-04-20 | — |
| [[A6f.5b]] | Fernet → AES-GCM (deferido) | paused | — | — |
| [[A6f.5c]] | JWT HS256 → RS256 (deferido) | paused | — | — |
| [[A6f.6]] | Stateless rigoroso (ADR-111) | shipped | 2026-04-20 | — |
| [[A6g.1]] | Auditoria inicial code style | shipped | 2026-04-21 | 1 |
| [[A6g.2]] | Pipeline Python sweep | shipped | 2026-04-21 (T1+T2) / 2026-04-25 (T3 = A6g.2b) | 1 |
| [[A6g.2c]] | Rename `pipeline/llm/service.py` | shipped | 2026-04-22 | 3 |
| [[A6g.3]] | Backend Python sweep (3 rodadas) | shipped | 2026-04-25 | 3 |
| [[A6g.3b]] | Money Decimal migration | shipped | 2026-04-22 | 3+ |
| [[A6g.4]] | Frontend TypeScript sweep | shipped | 2026-04-22 | 1 |
| [[A6g.5]] | Tests sweep | shipped | 2026-04-21 | 2 |
| [[A6g.6]] | Enforcement automatizado (ADR-114) | shipped | 2026-04-22 | 3 |
| [[A6g.6b]] | Sweep ruff + max-lines warn→error | shipped | 2026-04-22 | 3 |
| [[A6g.7]] | Go prep (ADR-113) | shipped | 2026-04-22 | 3 |
| [[F7F-Local]] | Console interno pré-produção (IA-0) | shipped | 2026-04-23 (MVP S1+S2+S3) | 3 (Lane C6) |
| [[F7F-Analyst]] | Superfície do especialista financeiro (IA-0+) | open | — | 3+ (Lane C6, pós-F7F-Local) |
| [[ADR-129-e6-kill]] | Remoção E6 + endpoints HTML | shipped | 2026-04-25 | P1 |
| [[Report-a11y-finalize]] | Resíduo F12 — a11y + Playwright | shipped | 2026-04-25 | P1 |
| [[Report-Premium-v1-polish]] | Resíduo F13 — docs-only | shipped | 2026-04-25 | P2 |
| [[Report-Appearance-Menu]] | Refinement ADR-121 Fase 4 | shipped | 2026-04-26 | — |
| [[Report-mobile-impl]] | D3 do `report-a11y-finalize` (mobile) | open | aguarda priorização | P2 |
| [[Report-Premium-v2]] | Guarda-chuva — 20 sub-lanes em 5 ondas | shipped | 2026-04-27 (ondas A-E concluídas) | — |
| [[F9.0]] | Auditoria stage rename (ADR-093) | shipped | 2026-04-25 | F9 |
| [[F9.1]] | `git mv pipeline/stages/` rename | shipped | 2026-04-25 | F9 |
| [[F9.2]] | Strings literais — sub-lanes 9.2a/b/c/d/e | shipped | 2026-04-25 (T1) / posteriores (sub-lanes) | F9 |
| [[F9.3]] | Alembic migration | shipped | 2026-05-05 | F9 |
| [[F9.4]] | `git mv scripts/` + alias CLI | open | destravada por F9.3 | F9 |
| [[F9.5]] | Guardrail hard-fail | open | depende de F9.4 | F9 |
| [[F9.6]] | Cleanup final | open | depende de F9.5 | F9 |

> Lanes legadas (✅) consumidas a partir de tracks em [`tracks/`](tracks/) ou texto editorial no [BACKLOG legado](../../BACKLOG.md). Migração estrutural em curso (F4.A do plano DOC_REORG).
