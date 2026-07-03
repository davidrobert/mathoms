<!-- F5.D — ADR-182 / DOC_REORG_PLAN F5 — 2026-05-07 -->
<!-- Migrado de docs/ROADMAP.md (deletado em F5). Apenas overview evergreen das fases F0-F11; status por fase vive em docs/_MOC/SPRINTS-active.md (sprint atual) + docs/sprint/<X>/_README.md (sprints encerradas) + docs/_MOC/_generated/CHANGELOG_RECENT.md (entregas recentes). -->

# PHASES — visão geral das fases F0-F11 (evergreen)

> Este documento é **estável**: descreve o escopo *projetado* das 12 fases do produto.
>
> Para **status corrente** (qual fase está sendo executada, lanes prontas para pickup):
> consulte [`docs/_MOC/SPRINTS-active.md`](../_MOC/SPRINTS-active.md) (editorial) e
> [`docs/_MOC/_generated/SPRINT_CURRENT.md`](../_MOC/_generated/SPRINT_CURRENT.md) (auto).

## Visão geral das fases

| Fase    | Nome                     | Status       | Entrega principal                                                                              |
| ------- | ------------------------ | ------------ | ---------------------------------------------------------------------------------------------- |
| **0**   | Desacoplar Core          | ✅ Concluída  | Pipeline como package Python importável + contexto injetável                                   |
| **1**   | Backend API + Auth       | ✅ Concluída  | Login/registro + API de relatórios + Frontend MVP                                              |
| **2**   | Upload + Pipeline Web    | ✅ Concluída  | Upload + unlock/classify auto + pipeline pseudo-async                                          |
| **3**   | Configuração via UI      | ✅ Concluída  | Config editável via UI + materialização + import/export JSON                                   |
| **4**   | Automação LLM            | ✅ Concluída  | LiteLLM+Instructor, BYOK, Premium E2E, review manual, tier                                     |
| **4.5** | Design System Foundation | ✅ Concluída  | Tailwind v4 @theme, Geist fonts, shadcn/ui, 7 compostos financeiros                            |
| **5**   | Task Queue + Async       | ✅ Concluída  | Celery+Redis, WS+polling, cancel stage-boundary, concurrency                                   |
| **6**   | Frontend Profissional    | ✅ Concluída  | Dashboard, Transaction Explorer, Report React, Dark mode, Notifications                        |
| **6.5** | Testing & Hardening (FE+BE) | ✅ Concluída | Vitest + RTL + MSW + Playwright — **438 tests** (94 backend + 344 frontend) em ~25s. Hardening fintech (axe 0 critical, property-based BRL, visual reg. infra, resilience, security smoke, CPF mod-11+lint PII, error boundary, focus mgmt). Backend hardening (6 serializers round-trip, alembic guardrails, golden pipeline, concurrency). Multi-tenant isolation (27 tests, 0 leaks). WS real com fakeredis. Anti-regression bank (24 tests). Test infrastructure completa (factories, isolation, docker-compose.test, synthetic PDFs, pipeline mock fixtures, MSW lint, LLM mock). CI GH Actions (7 jobs). SMOKE_TEST.md 70+ checks. 7 ADRs novas (062-064, 067-071). |
| **7**   | Produção + LGPD + Ops    | 🔶 Em curso (5/6 lanes ✅; falta F7-c CI/CD-observabilidade) | VPS+Docker+Traefik ✅, LGPD completo ✅, auth flows (email verify/pwd reset/brute-force) ✅, prompt injection defense, operational readiness (DR testado, business metrics, incident comms, LLM cost cap) ✅, CI/CD 🔶, dogfood validado ✅ — lanes em `docs/sprint/F7/lanes/` |
| **8**   | Goals & Tasks + Cutover CLI→Web | ✅ Concluída | Goals versionados (IF + APORTE_MENSAL + DOLARIZACAO + ALOCACAO_ALVO + PLANNING_CONTEXT em F8.5), Tasks como entidade de 1ª classe (CRUD + dependencies + suggestions + attachments + progress%), Pipeline adapter (DB→JSON), Feature flags, Worker beat, Snapshot imutável no relatório, Celery beat diário scan-deadlines. **~146 testes, 7 ADRs (072-075, 077, 079), 5 migrations, 20 tenant models, 9 services, ~42 endpoints, 10 componentes React, 11 rotas frontend**. Cutover reversível via feature flags. ADR-072/073/074/075/077/079. |
| **9**   | Relatório Nativo React + Workspace Sharing + Design System | ✅ Concluída | **Relatório:** render React nativo (18 seções, 13 cards, 8 charts Recharts, deep-links, scroll-spy, print CSS A4, PDF Playwright). _E6 standalone (exportador HTML) descontinuado em 2026-04 via [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)._ **Design System:** tokens.json → CSS unificado (ADR-076), codegen YAML→TS/Pydantic. **Sharing:** 3 roles, convites SHA-256/TTL 72h, forced logout, viewer banner, workspace switcher. **113 testes novos (56 BE + 23 FE + 20 tokens + 14 codegen), 3 ADRs (076-078), 3 migrations.** |
| **10**  | Growth & Aquisição | ☐ Futuro (pós-GA) | Landing, SEO, billing, digest — ver § F10 |
| **11**  | Confiança, transparência, excelência de relatório | ☐ Beta → GA | Origem dos dados, LLM/needs_review, premissas, hierarquia numérica, print/PDF consultoria, mental model plano × mês — ver § F11 |

**Épicos transversais (não são fases numeradas):** [P2 classificação de documentos](../archive/BACKLOG-pre-shim-2026-05-07.md#p2--unificação-da-classificação-de-documentos) (motor); **P0/P1 motor canônico** (§ *Motor canônico e pipeline* abaixo) concluído; expansão incremental de goldens/PDF continua junto a **7D.1**.

---

---

### F10 — Growth & Aquisição (pós-launch, Futuro)

Adiado conscientemente: são features de **aquisição / marketing** que não fazem sentido no estágio dogfood/beta. Incluídas para referência futura.

| Prioridade | Item | Notas |
| --- | --- | --- |
| P1 | Landing page + onboarding wizard + guided tour | Depende de pesquisa com usuários beta |
| P2 | PWA (service worker, install, offline seguro) | Segurança e superfície de dados sensíveis |
| P2 | SEO / Open Graph / sitemap | Depende de landing |
| P1 | Email digest notifications | Requer serviço de e-mail + templates |
| P1 | Demo mode (workspace fictício read-only) | Também útil a **F11** (onboarding sem medo) |
| P1 | Billing real (Stripe) | BYOK cobre Premium até GA |
| P2 | Report comparison (side-by-side, deltas) | Requer histórico de relatórios no uso real |

**Command palette / atalhos:** entregue em produto (**F11.8**): **⌘K** / Ctrl+K + modal **?** — ver [BACKLOG pré-shim (histórico)](../archive/BACKLOG-pre-shim-2026-05-07.md#f118--command-palette--atalhos).

---

### F11 — Confiança, transparência e excelência de relatório (beta → GA)

Objetivo: **baixa fricção cognitiva**, **confiança em dados e em LLM**, e **entrega visual digna de consultoria** — sem substituir F7 (produção) nem o epic de **classificação unificada** (P2 no backlog).

| # | Tema | Entregas resumidas | Prio |
| --- | --- | --- | --- |
| F11.1 | **Mental model: “vida financeira” × “relatório deste mês”** | Rotas e IA claras: `/plano` e metas = configuração de longo prazo; fluxo Documentos → Pipeline → Relatório = ciclo mensal. Copy, navegação primária/secundária, empty states que não misturam os dois modos. | P1 |
| F11.2 | **Hierarquia de números** | Padrão único de tipografia e alinhamento (KPI, tabelas, gráficos, relatório): decimais BRL, sinal de fluxo, escala em eixos; auditoria Dashboard + Transaction Explorer + Report React + tokens. | P1 |
| F11.3 | **Print / PDF como entregável de consultoria** | Refino de `@media print`, capa, margens A4, quebras de página, fontes embed/sistema; export PDF/HTML com aparência “documento para terceiros”; checklist de QA visual. | P1 |
| F11.4 | **Transparência: origem da informação** | Por seção ou bloco: qual documento / período / estágio alimenta o número (linhagem resumida; link para Documentos ou run quando aplicável). | P1 |
| F11.5 | **Transparência: `needs_review` e trilha LLM** | Linguagem consistente: quando o dado é inferido, revisão humana pendente, ou validado; CTAs para revisão; sem jargão de estágio E* na UI (ADR-068). | P0 |
| F11.6 | **Metadados de premissas (metas + relatório)** | Campos ou bloco explícito: taxas, inflação, horizonte, cenário base; **F11.6b:** snapshot persistido (`premissas_snapshot_json` + API / merge no `/data`) para comparar mês a mês. | P1 |
| F11.7 | **Número ↔ regra** | Tooltips ou painel “Como calculamos”: ligação do KPI ao motor (ex.: FV de anuidade na meta IF); glossário mínimo. | P1 |
| F11.8 | **Command palette / atalhos** | `cmdk` (ou equivalente): busca de rotas, ações (novo upload, rodar pipeline); atalhos documentados e não conflitantes com o browser. | P2 |

Detalhamento por task (histórico): **[BACKLOG pré-shim §F11](../archive/BACKLOG-pre-shim-2026-05-07.md#f11--confiança-transparência-e-excelência-de-relatório-beta--ga)**.

**Sprint B (2026-04-17):** F11.5 (banner `needs_review`, notas LLM por etapa, sem códigos E* na linha de etapa; rótulo de toque E2 sem “E2” na UI), F11.4b–c (`ReportSourceStrip` + período/gerado em), fatia de F11.2 (eixos/tooltips do dashboard com `tabular-nums`).

**Sprint C (2026-04-17):** F11.4a no nível do relatório — `pipeline_run_id` na API, link e deep link para Pipeline; F11.2a — `tabular-nums` / `font-mono` em Transactions (tabela + paginação) e hero do relatório nativo.

**Sprint D (2026-04-17):** P2.5 (telemetria de classificação); conclusão F11.4a agregada (`source_document_ids` / `_report_lineage`); F11.2b; F11.7 + F11.6c; F11.3c checklist + F11.3a/b em progresso; F11.1 nav + empty states + [COPY_GUIDELINES](COPY_GUIDELINES.md); F11.8 cmdk. **Atualização:** F11.6b (snapshot de premissas no relatório) e leva inicial **7D.1 / 7D.2** (testes unitários de borda E0/E3/E4/E7 e E5/E5N/E6). Próximo: F11.6a (premissas nas metas na UI), linhagem por seção se necessário, golden F11.7c.

**Ordem sugerida (histórico):** F11.5 → F11.4 → F11.2 → F11.7 → F11.6 → F11.3 → F11.1 → F11.8 — **Sprint D** executou o tail desta fila + P2.5.

---

## Métricas de sucesso por fase

Política de cobertura (Python backend + pipeline):

| Fase     | Meta line | Meta branch | Foco                                                                         |
| -------- | --------- | ----------- | ---------------------------------------------------------------------------- |
| F0       | ~30%      | —           | ✅ Regressão golden files                                                     |
| F1       | ~40%      | —           | ✅ Auth endpoints, JWT                                                        |
| F2       | ~55%      | ~40%        | ✅ Upload, vault, pipeline execution. **CI gate ativado**                    |
| F3       | ~65%      | ~50%        | ✅ CRUD config, materialização                                               |
| F4       | ~75%      | ~60%        | ✅ LLM service (mocks), validators, retry, tier detection                    |
| F4.5     | ~75%      | ~60%        | Frontend-only. Zero Python novo                                              |
| F5       | ~85%      | ~70%        | ✅ Task queue, async execution, WebSocket, cancelamento                      |
| F6       | ~90%      | ~80%        | Edge cases restantes, error paths                                            |
| F6.5     | ~90%      | ~80%        | ✅ **438 tests** (94 backend + 344 frontend). lib/ ≥80% (utils/format/export/usePipelineWS 97-100%). Multi-tenant 0 leaks. 24 anti-regression tests. |
| F7       | **≥95%**  | **≥85%**    | Gap-fill scripts legados + CI coverage gate                                  |

---

## Riscos e mitigações

| #   | Risco                                          | Impacto   | Probab.         | Status    | Mitigação                                                                                 |
| --- | ---------------------------------------------- | --------- | --------------- | --------- | ----------------------------------------------------------------------------------------- |
| R1  | Refactoring quebra pipeline                    | Alto      | ~~Média~~ Baixa | ✅ Mitigado | 136 tests + `_init_config()` pattern                                                      |
| R2  | LLM output inconsistente                       | Alto      | ~~Alta~~ Média  | ✅ Parcial  | Instructor + Pydantic + validators + needs_review workflow (F4)                            |
| R3  | Custo de LLM por run inviável                  | Médio     | Baixa           | ✅ Mitigado | BYOK (F4). Token tracking + cost estimation                                               |
| R4  | Dados sensíveis vazam                          | Crítico   | Baixa           | ⏳ F7       | Fernet at-rest (parcial). HTTPS + audit log + LGPD em F7                                  |
| R5  | Parsers quebram com mudança de layout          | Alto      | Alta            | ⚠️ Ativo   | Testes golden files. Alertas de parsing error. LLM fallback (E2-llm) em F4                |
| R6  | Escopo cresce demais                           | Alto      | Alta            | ⚠️ Ativo   | P0 por sprint. Cortar P2. Itens de F8 adiados explicitamente                              |
| R7  | Complexidade E5/E6 dificulta refactoring       | Médio     | Alta            | ✅ Mitigado | "Wrap, Don't Rewrite" strategy. Lógica interna inalterada                                 |
| R8  | FERNET_KEY perdida entre restarts              | Alto      | Resolvido       | ✅ Mitigado | Persistência em `.env`. Procedimento documentado em SETUP.md                              |
| R9  | Dogfood reta para beta sem bugs bloqueantes    | Médio     | Média           | ⏳ F7       | 2+ semanas de dogfood obrigatórias. 5+ pipeline runs 100% success                         |
| R10 | Serializers DB→pipeline perdem campos silenciosamente (BUG-015 class) | Alto | ~~Alta~~ Baixa | ✅ F6.5E | Round-trip tests para 6 serializers + golden file pipeline + 4 tests anti-regressão BUG-015 |
| R11 | Migration aplicada em DB errada por cwd ambíguo | Alto    | ~~Média~~ Baixa | ✅ F6.5E   | Caminho absoluto em alembic.ini (%(here)s) + guard em env.py rejeita SQLite relativo + doc SETUP.md |
| R12 | LLM BYOK consome budget do user descontroladamente | Médio  | Alta            | ⏳ F7E      | Cost cap mensal por workspace + toast 80%/95% + hard stop 100%                            |
| R13 | Pipeline run "running" para sempre (worker morto) | Médio  | Média           | ⏳ F7E      | Heartbeat + Celery beat detector marca como failed >1h sem heartbeat                       |
| R14 | Prompt injection em PDF malicioso vaza dados via LLM | Alto | Baixa-Média    | ⏳ F7B      | Sanitização texto extraído + allowlist output + fixture PDF adversarial                   |
| R15 | FERNET_KEY perdida em prod = todos os secrets ilegíveis | Crítico | Baixa         | ⏳ F7E      | Backup criptografado off-site (1Password vault) + procedure testado em staging            |
| R16 | Backup Hetzner perdido junto com DC (incêndio/falha) | Crítico | Muito baixa    | ⏳ F7E      | Off-site backup S3/B2 BR + restore drill quarterly                                        |
| R17 | GA bloqueado por falta de email verify/password reset | Alto | Certa          | ⏳ F7B      | Auth flows completos em 7B.11-13 antes do Beta abrir                                       |
| R18 | Multi-tenant data leak entre workspaces (endpoint esquece filtro) | Crítico | ~~Média~~ Baixa | ✅ F6.5B | 27 tests paramétricos cobrem 9 domínios de endpoints — 0 vazamentos confirmados |
| R19 | 250+ tests viram débito técnico sem infra de teste sustentável | Alto | ~~Alta~~ Baixa | ✅ F6.5F | 438 tests sustentados por factories (backend+FE) + DB isolation + MSW sync + TESTING.md + CODEOWNERS |

---

## Sprint transversal A6 — Migração infra+domínio (pós-F9)

**ADRs formalizadoras**: 097-111 em [DECISIONS.md](../DECISIONS.md) ·
**Arquitetura alvo + motivação**: [ARCHITECTURE §17](ARCHITECTURE.md).

**Status, sessões e diagrama de ondas paralelas do Sprint A6
(histórico)**: [BACKLOG pré-shim §Sprint A6](../archive/BACKLOG-pre-shim-2026-05-07.md#sprint-a6--migração-infradomínio-plano-transversal);
sprint corrente em [SPRINT_CURRENT.md](../_MOC/_generated/SPRINT_CURRENT.md).
PHASES cobre apenas a visão de fases e timeline macro — não duplique
status de sessão aqui (vira drift).

**Sprint corrente — NÃO snapshot aqui (vira drift).** A sprint atual e as lanes
prontas vivem na fonte canônica auto-gerada: [`docs/_MOC/_generated/SPRINT_CURRENT.md`](../_MOC/_generated/SPRINT_CURRENT.md)
+ visão editorial [`docs/_MOC/SPRINTS-active.md`](../_MOC/SPRINTS-active.md). Confirme
sempre com `git worktree list` + `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
O histórico de fases timeless (caminho crítico, dependências entre fases) segue abaixo.

**Após A6**: sprints dedicados §15 (LGPD) e §16 (Observabilidade) —
incorporados ao escopo de F7 (Produção + LGPD + Ops).

---

## DOCS-REVIEW — Saúde da documentação (pós-revisão multi-agente 2026-04-24)

Revisão coordenada por 4 agentes (senior-cto, product-designer, financial-planner, general-purpose) em 2026-04-24 produziu ~20 achados priorizados. **Batch 1** (hotfix — ADR-078/079 duplicados → 125/126, ADR-119/120 registradas, ROADMAP+BACKLOG sincronizados, contagens ARCHITECTURE alinhadas) foi entregue em `af8dce7`. **Batches 2 e 3** ficam como trabalho futuro em [BACKLOG pré-shim §DOCS-REVIEW (histórico)](../archive/BACKLOG-pre-shim-2026-05-07.md#docs-review--followups-da-revisão-multi-agente-2026-04-24) — não bloqueiam F7, mas precisam acontecer antes de Beta fechado para saúde sustentável da doc.

- **Batch 2 — reescrita** (15 itens): FORMULAS completo, COPY_GUIDELINES expandido, TOC em DECISIONS, shapes TS em REPORT_PREMIUM_GAPS, Quickstart LLM, Guia DDD, TESTING completo, design token governance, spec mobile, a11y checklist.
- **Batch 3 — ADRs + correções de domínio** (12 itens): ADR-Processo formal, ADR-ScoringParams, ADR-MoneyDTOs (finaliza A6g.3b), ADR-AlocaçãoAlvo, fix Cerbasi `categorias_futuro`, reserva de emergência só líquidos, dívida boa×ruim, RebalancingAdvisor, YoC real, cobertura de seguros, auto-gen contagens ARCHITECTURE.

**Ordem sugerida de ataque:** (1) batch3.4 processo de ADR → (2) batch2.8 shapes TS → (3) batch3.1/3.5/3.6 regras de domínio antes de GA → (4) batch3.2 Money DTOs → (5) demais em paralelo. Ver tabela completa no BACKLOG.

---

## Timeline geral estimada

| Período              | Milestone                                        |
| -------------------- | ------------------------------------------------ |
| Q1 2026              | F0-F4 ✅ (Core → LLM)                            |
| Q2 2026 (Abr)        | F4.5, F5, F6, F6.5, F8, F9 ✅ — feature-complete pré-produção + **Plano transversal A5a-A5e concluído** (Fase 8 do plano de migração infra+domínio) |
| Q2-Q3 2026 (Mai-Jul) | **Sprint A6** (A5f · A6a-c · A6b.5 · A6-human) → cutover DB validado + teste humano + bridge removido → **A6d/A6e/A6f em paralelo** |
| Q3 2026              | F7 (Produção + LGPD + Ops, integrando §15 LGPD + §16 Observabilidade do plano) → Dogfood → Beta fechado |
| Q3-Q4 2026           | Beta → F11 (confiança / transparência) → preparação GA + F10 (Growth) |
| 2027+                | GA + features de growth                          |

---

## Como priorizamos

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para próxima fase ou sprint.

Ver [SPRINT_CURRENT.md](../_MOC/_generated/SPRINT_CURRENT.md) + [SPRINTS-active.md](../_MOC/SPRINTS-active.md) para priorização detalhada por lane.
