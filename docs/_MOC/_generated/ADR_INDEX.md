> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# ADR_INDEX — Índice de Architectural Decision Records

Volta para [`00-INDEX`](../00-INDEX.md).

282 ADRs (ADR-001 a ADR-291) em [`docs/adr/`](../../adr/).

## Sumário por status

- **Decidido**: 214
- **Proposto**: 64
- **Roadmap**: 4

## Fundação

### Decidido (6)

- [[ADR-001]] — SQLAlchemy 2.0 como ORM · phase F1
- [[ADR-002]] — Filesystem local para storage · phase F2
- [[ADR-003]] — JWT custom para auth · phase F1
- [[ADR-006]] — Monorepo · phase F0
- [[ADR-013]] — "Wrap, Don't Rewrite" pattern · phase F0
- [[ADR-231]] — Encryption at-rest de PII em pipeline_artifacts via Fernet wrapper (hook em DBArtifactStore) · phase A11.W2

### Proposto (1)

- [[ADR-005]] — VPS Hetzner para produção · phase F7

## Persistência

### Decidido (3)

- [[ADR-029]] — Alembic para migrations · phase F2
- [[ADR-038]] — Docker volume para storage prod · phase F7
- [[ADR-039]] — Dual DB: SQLite (dev) + PostgreSQL (prod) · phase F7

### Proposto (2)

- [[ADR-171]] — Fernet rotation operacionalizada via MultiFernet
- [[ADR-259]] — Boundary LLM unificado — Decimal monetário + PII (cpf_present + Fernet + UX decrypt) · phase A18.W1α + A20.W1β

## Pipeline

### Decidido (12)

- [[ADR-014]] — Threading para execução background · phase F2
- [[ADR-015]] — Vault por workspace · phase F2
- [[ADR-016]] — E0-route automático no upload · phase F2
- [[ADR-017]] — Sync session em background threads · phase F2
- [[ADR-018]] — `config_dir` override em `for_tenant()` · phase F2
- [[ADR-019]] — `STORAGE_ROOT` via env var · phase F2
- [[ADR-030]] — Cancelamento cooperativo via `threading.Event` · phase F2
- [[ADR-030-WS]] — WebSocket + polling fallback · phase F5
- [[ADR-075]] — Cutover CLI → Web: estratégia de transição faseada com adapters · phase F8
- [[ADR-079]] — Content-first classification no upload web
- [[ADR-080]] — Pipeline incremental: extrair só docs novos, consolidar full · phase F7
- [[ADR-081]] — Classificação de documentos unificada (P2)

## Config (materialização legada)

### Decidido (4)

- [[ADR-020]] — Materializar config em disco · phase F3
- [[ADR-021]] — 5 configs editáveis · phase F3
- [[ADR-022]] — Fallback seletivo de config · phase F3
- [[ADR-023]] — Import/export JSON de config · phase F3

## LLM

### Decidido (6)

- [[ADR-024]] — LiteLLM como proxy universal · phase F4
- [[ADR-025]] — BYOK (Bring Your Own Key) · phase F4
- [[ADR-026]] — Instructor + Pydantic para structured output · phase F4
- [[ADR-027]] — Retry → needs_review em falha de validação · phase F4
- [[ADR-028]] — E7 full scope na Fase 4 · phase F4
- [[ADR-288]] — Identificador fiscal ilegível em extração LLM degrada para None determinístico — nunca hard-fail retryable

### Proposto (1)

- [[ADR-270]] — Retry de LLM calls — categoria network + cap de timeout · phase A17.llm-retry

## Task Queue

### Decidido (4)

- [[ADR-029-TQ]] — Celery + Redis · phase F5
- [[ADR-031]] — Redis para queue + pub/sub · phase F5
- [[ADR-032]] — Cancel stage-boundary · phase F5
- [[ADR-172]] — Stuck-runs detector via heartbeat + Celery beat · phase Sprint A11.W2

## Frontend / Design

### Decidido (16)

- [[ADR-033]] — React components para report · phase F6
- [[ADR-034]] — Dashboard completo com alertas · phase F6
- [[ADR-035]] — `@media print` para PDF export · phase F6
- [[ADR-037]] — Recharts para charts · phase F6
- [[ADR-042]] — Design system antes da Fase 5 · phase F4.5
- [[ADR-043]] — shadcn/ui como component library · phase F4.5
- [[ADR-044]] — Transaction Explorer como core · phase F6
- [[ADR-045]] — Data lineage via tooltip · phase F6
- [[ADR-046]] — Responsivo sem PWA obrigatório · phase F6
- [[ADR-047]] — Category override em vez de reconciliação UI · phase F6
- [[ADR-050]] — Tailwind v4 `@theme inline` · phase F4.5
- [[ADR-051]] — Geist fonts · phase F4.5
- [[ADR-052]] — Lucide React para ícones · phase F4.5
- [[ADR-053]] — `Intl` nativo para datas · phase F4.5
- [[ADR-054]] — Migração incremental de pages · phase F4.5
- [[ADR-139]] — Finalização migração Recharts→Chart.js em /reports/** · phase Onda v2.E concluída

## Produção & Infra (F7)

### Decidido (12)

- [[ADR-007]] — Fernet app-level para criptografia · phase F4→F7
- [[ADR-040]] — Billing adiado para pós-launch · phase F7
- [[ADR-041]] — Traefik como reverse proxy · phase F7
- [[ADR-055]] — Coverage target: ≥85% line + ≥95% new code · phase F7
- [[ADR-056]] — Rolling restart em vez de blue-green · phase F7
- [[ADR-057]] — JWT 15min + refresh 7d · phase F7
- [[ADR-059]] — Docker image CVE scan no CI · phase F7
- [[ADR-060]] — Fernet dual-key para secret rotation · phase F7
- [[ADR-061]] — Telemetria privacy-first · phase F7
- [[ADR-108]] — Estratégia de subdomínios `mathoms.ai` + Cloudflare DNS
- [[ADR-116]] — F7F-Local: stack Next separada + anonimização default + auth yaml+bcrypt+JWT (F7F-Local) · phase F7F-Local
- [[ADR-284]] — Schema validation: mode_overrides per-schema, enforcement strict real e telemetria de drift · phase Débito técnico (A24)

### Proposto (4)

- [[ADR-058]] — VPS CX32 para sizing · phase F7
- [[ADR-206]] — Telemetria de campo faltante como signal de evolução do manifest (estende ADR-188) · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-210]] — Saúde do test suite do CI — gates, telemetria e ciclo de vida · phase Sprint A12 (test health · CI cost)
- [[ADR-260]] — Telemetria LLM por prompt_version — labels compostos em LLMCallLog SQL + OTLP · phase A20.W2 + A20.W3

## Testing

### Decidido (7)

- [[ADR-062]] — Frontend testing em fase dedicada (6.5)
- [[ADR-063]] — Hardening fintech em sub-fase 6.5D
- [[ADR-064]] — Backend hardening em sub-fase 6.5E
- [[ADR-067]] — Test infrastructure em sub-fase 6.5F
- [[ADR-069]] — MSW sync strategy: manual + lint CI (não codegen)
- [[ADR-070]] — Premium LLM E2E: mock default + nightly real opt-in
- [[ADR-071]] — Playwright workspace isolation: email unique por worker

## Operations

### Decidido (2)

- [[ADR-065]] — Sub-fase 7E Operational Readiness
- [[ADR-066]] — Auth flows completos e prompt injection em 7B (bloqueadores de beta)

## UX / Linguagem

### Decidido (1)

- [[ADR-068]] — Códigos internos do pipeline nunca vazam na UI

## Multi-tenancy (F8)

### Decidido (1)

- [[ADR-072]] — Multi-tenancy: `workspace_id` scoping explícito + `WorkspaceMember` para multi-família · phase F8

## Goals & Tasks (F8)

### Decidido (3)

- [[ADR-073]] — Goals como entidade versionada (não config estático) · phase F8
- [[ADR-074]] — Tasks como entidade de 1ª classe (fora do relatório) · phase F8
- [[ADR-077]] — Pipeline adapter como contrato de cutover (CLI → Web) · phase F8.4

## Design System & Render (F9 / Report Premium)

### Decidido (11)

- [[ADR-076]] — Design Tokens Unificados Site ↔ Relatório · phase F9
- [[ADR-078]] — Render Nativo React + E6 como Exportador Standalone · phase F9
- [[ADR-121]] — Typography base 13px com override configurável · phase Fase 0
- [[ADR-122]] — `chart_conclusions` e `section_summaries` em modo híbrido (template + LLM) · phase Fase 0
- [[ADR-123]] — Notas (T6) e Kanban (T3) persistidos no backend · phase Fase 0
- [[ADR-124]] — `scripts/e6_render.py` aposentado em favor de SSR standalone do Next · phase Fase 0
- [[ADR-125]] — Workspace sharing: convites, viewer role, forced logout · phase F9
- [[ADR-126]] — Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO) · phase F8.5
- [[ADR-127]] — E1 members persiste via ArtifactStore
- [[ADR-128]] — E7-review-llm lê/escreve via `ArtifactStore` · phase A6-cleanup (Removed em A12.X — código deletado, superseded por ADR-199)
- [[ADR-129]] — Descontinuação completa do renderer HTML server-side

## Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)

### Decidido (36)

- [[ADR-082]] — PipelineArtifact: artefatos computacionais no banco
- [[ADR-083]] — ArtifactStore: abstração de I/O para artefatos
- [[ADR-084]] — Content-addressed uploads
- [[ADR-085]] — Eliminar materialização de config em disco · phase parcial — implementação na Fase 4
- [[ADR-086]] — MaterializationBridge: adapter temporário
- [[ADR-087]] — StageSpec: dependências declarativas
- [[ADR-088]] — StageConfig: configuração imutável por parâmetro
- [[ADR-089]] — pipeline/domain/: camada de domínio isolada de I/O
- [[ADR-090]] — Decimal para valores monetários · phase F5.2
- [[ADR-091]] — Pydantic para domain objects com coleções
- [[ADR-093]] — Rename completo de identificadores de stage (Opção A) · phase F9 · execução em andamento
- [[ADR-094]] — Report: single-active vs. versionado · phase single-active para F9; evolução planejada
- [[ADR-097]] — Extract-then-refactor: estratégia de decomposição de `e3_reconcile.py`
- [[ADR-098]] — Caminho B pragmático vs puro: nomenclatura oficial
- [[ADR-099]] — Reuse de `analyze_*` legadas em `main_with_store` (decisão de A5d/A5e)
- [[ADR-100]] — A6d commitment: fechar Caminho B puro nos 5 stages pragmáticos
- [[ADR-101]] — Princípios R12-R17: DDD/SOLID no backend API (A6e)
- [[ADR-102]] — Princípios R18-R20: language-neutral boundaries (A6f)
- [[ADR-103]] — Teste manual como gate antes de remoção do bridge (A6b.5 + A6-human)
- [[ADR-104]] — E1.5c em Caminho B pragmático (Sessão A5f) · phase A5f
- [[ADR-105]] — LLM stages escrevem via ArtifactStore; E1 e E7-review LLM não migram (A6a) · phase A6a
- [[ADR-106]] — Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (A6b) · phase A6b
- [[ADR-107]] — Remoção de `MaterializationBridge` e `stage_runner_compat` (A6c.1-2)
- [[ADR-109]] — Auth portability: JWT HS256 + Fernet documentados como contratos portáveis (A6f.5a)
- [[ADR-110]] — Structured JSON logging + OpenTelemetry bootstrap (A6f.3)
- [[ADR-111]] — Stateless-rigoroso: padrão e gate empírico (A6f.6) · phase A6f.6
- [[ADR-112]] — Pipeline-as-Service: HTTP boundary para execução de stages (A6f.1) · phase A6f.1
- [[ADR-113]] — Convenções Go: `.golangci.yml` + CI + skeleton (A6g.7) · phase A6g.7
- [[ADR-114]] — Enforcement automatizado de code style: gates imediatos + progressivos (A6g.6) · phase A6g.6
- [[ADR-115]] — Domain events tipados: arquitetura e boundaries (A6e.events) · phase A6e.events
- [[ADR-117]] — Report Premium UI baseline (paridade com EXEMPLO_DE_RELATORIO.html) · phase Fase 0 do plano
- [[ADR-118]] — Flip do default `MATHOMS_USE_DB_ARTIFACTS` para `True` · phase A6
- [[ADR-119]] — Contrato `LiveStep` para progresso de etapas do pipeline · phase A6-ux
- [[ADR-120]] — Readers user-facing consultam `ArtifactStore` (DB-first) com fallback disco · phase A6
- [[ADR-212]] — Sunset `MATHOMS_USE_DB_ARTIFACTS` + `DiskArtifactStore` + CLI standalone do pipeline · phase A12.sunset-disk-artifact
- [[ADR-275]] — Auditoria de acesso + política de retenção LGPD · phase A21 (l7 + l8)

### Proposto (3)

- [[ADR-092]] — Renomear scripts para nomes descritivos de domínio · phase execução na Fase 9 pós-Caminho B dos stages
- [[ADR-095]] — Segurança de `content_json` (LGPD) · phase execução distribuída em Fases 1-4 do plano
- [[ADR-096]] — Observabilidade de cutover · phase execução paralela à Fase 2

## Internacionalização (F12)

### Proposto (1)

- [[ADR-130]] — Internacionalização com `next-intl` + persistência em `users.locale` · phase F12

## Report Premium (F-pós, ondas v1/v2)

### Decidido (5)

- [[ADR-131]] — `Report` referencia `pipeline_artifact` por FK (drop `analysis_json_path`)
- [[ADR-132]] — Lifecycle scoping de `pipeline_artifacts` (workspace vs run)
- [[ADR-133]] — `transferencias_internas` modelado em `transfer_configs` (workspace-scoped)
- [[ADR-144]] — `section_summaries` LLM-driven em E5 com cache + fallback determinístico (v2.9) · phase Fase 1 — fundação arquitetural; implementação em Fase 2 sob lane v2.9
- [[ADR-148]] — `SnapshotChangelogBuilder`: comparações mês-a-mês de relatório · phase Onda v2.D · v2.D.1

## Sprint A7 — Rules-as-Code & Cutover

### Decidido (9)

- [[ADR-134]] — `ConfigStore`: protocolo de leitura tipado (pipeline + backend) · phase Sprint A7
- [[ADR-135]] — Versionamento temporal de séries fiscais e câmbio · phase Sprint A7
- [[ADR-136]] — `Decision` aggregate event-sourced com supersede chain · phase Sprint A7
- [[ADR-137]] — Catalog + override resolver para `categorization` e `institutions` · phase Sprint A7
- [[ADR-138]] — Protocolo de supervisão CTO para Sprint A7 · phase Sprint A7
- [[ADR-143]] — `docs/methodology/` é rules-as-code (Sprint A7.6) · phase Sprint A7.6 · CTO sign-off 2026-04-27
- [[ADR-145]] — 7 categorias canonical da composição patrimonial · phase Sprint A7.6 · CTO sign-off 2026-04-27
- [[ADR-146]] — E3 source hierarchy + `BankAccount.source_tier` schema · phase Sprint A7.6 · CTO sign-off 2026-04-27
- [[ADR-147]] — Milhas: valuation methodology universal + storage workspace-scoped · phase Sprint A7.6 · CTO sign-off 2026-04-27

### Proposto (1)

- [[ADR-201]] — Persona do planejador como rules-as-code — `config/agents/planner_persona.md` · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW

## Decisões metodológicas pós-auditoria (Roadmap v2)

### Decidido (3)

- [[ADR-142]] — Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem
- [[ADR-222]] — Toggle `imoveis_no_if` migra de `pipeline.json` global para coluna `workspaces.imoveis_no_if` · phase A12
- [[ADR-223]] — Default conservador `imoveis_no_if=false` para workspaces novos + banner contextual · phase A12

### Proposto (1)

- [[ADR-141]] — Goal alocação-alvo schema v2 (7 classes AUVP) · phase A12

### Roadmap (1)

- [[ADR-140]] — Goal IF schema v2 (renda passiva atual + IF meta líquida)

## Sprint A10 — `goals.json` cutover final

### Decidido (5)

- [[ADR-177]] — Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`) · phase Sprint A10.2
- [[ADR-178]] — `Risk` aggregate workspace-scoped · phase Sprint A10.4
- [[ADR-179]] — `Decision` aggregate — extensão de schema (`impact_1y/10y`, `horizon`, `priority`) · phase Sprint A10.3
- [[ADR-180]] — `goals.json` cutover final via `StageConfig.config_store` extendido · phase Sprint A10.6
- [[ADR-181]] — `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py` · phase Sprint A10.8

## auth

### Decidido (1)

- [[ADR-170]] — Refresh tokens com httpOnly cookie e family-based revocation · phase Sprint A11.W3

## backend

### Decidido (11)

- [[ADR-153]] — `Suggestion` aggregate (Direção E · Onda 5): proposal imutável + state machine simples · phase Direção E · Onda 5
- [[ADR-154]] — Fusão `KanbanItem` em `Task` + migração `ReportNotes` para `WorkspaceNotes` (Direção E · Onda 1) · phase Direção E · Onda 1 · M1+M2
- [[ADR-162]] — Decisions como event projection sobre Goals · phase Onda 8
- [[ADR-167]] — Eligibility gate de cenário do cônjuge no domain service · phase A8.4 PR2
- [[ADR-175]] — Prompt injection defense em camadas (sanitize + system clause + Pydantic strict) · phase A21.l5
- [[ADR-192]] — `Protection` aggregate + `ProtectionBundle` (Seção 9 — Riscos e Proteção) · phase Sprint A11.W5
- [[ADR-213]] — Sunset stage `audit_documents` (e cleanup de `_STAGE_TO_DIR` órfão) · phase A12.sunset-audit
- [[ADR-214]] — `Decision.code` é server-generated com `pg_advisory_xact_lock` · phase A12.decision-code-autogen
- [[ADR-283]] — Float monetário persistido e hardening de boundary de schema (patrimonio_liquido, gate models, E2 items) · phase Débito técnico (A12)
- [[ADR-289]] — Catálogo de modelos LLM como fonte única + endpoint GET /llm/models (curado agora, dinâmico depois) · phase F1
- [[ADR-290]] — Supersede-per-run + thesis_key para Suggestion origin=llm (parecer) — extensão de ADR-269 ao aggregate Suggestion · phase A25

### Proposto (4)

- [[ADR-211]] — llm_config e pipeline.json como overrides DB-direto (cutover completo do A7) · phase A12
- [[ADR-221]] — Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto · phase A12
- [[ADR-269]] — Dedup de TaskSuggestion via soft-supersede + dedup_key normalizado · phase A17.task-suggestion-dedup
- [[ADR-285]] — backend/app/services/: subpacotes por natureza técnica, nunca por domínio de negócio · phase Débito técnico

## categorization

### Decidido (3)

- [[ADR-185]] — Política de edição e evolução de overrides de `category_templates` · phase A11.cat-overrides
- [[ADR-186]] — Promoção de override de transação para regra de categorização (learning loop) · phase A12.P2
- [[ADR-188]] — Evolução de schema e semântica do learning loop em P3 (soft-delete, partial unique, revert_count split) · phase A12.P3

## data-lineage

### Decidido (1)

- [[ADR-287]] — Flip do dedup E4 para identidade natural_key v2 (passo 2 da B4) · phase A25 · l2/l6B

### Proposto (1)

- [[ADR-282]] — Identidade de TransactionOverride unificada no natural_key v2 (fecha D6 da A23.l3) · phase A23 · pré-passo-2 B4

## docs

### Decidido (1)

- [[ADR-247]] — Documentação canônica permanece em Markdown; HTML apenas como artefato derivado/efêmero · phase A11

### Proposto (1)

- [[ADR-234]] — Adicionar `paused` ao vocabulário de `sprint_status` (4º valor) · phase A15

## domain

### Proposto (2)

- [[ADR-263]] — Goal type RESERVA_EMERGENCIA — schema versionado por workspace ancorado em INV1 (Fase 3.E pré-req) · phase A17.competitive-pierre-3e-prereq
- [[ADR-264]] — Goal type META_OBJETIVO — schema genérico para metas estruturadas (casa, educação, intercâmbio, aposentadoria do cônjuge) (Fase 3.E pré-req) · phase A17.competitive-pierre-3e-prereq

## frontend

### Decidido (6)

- [[ADR-151]] — Remoção do Modo Tático do relatório (Direção E do redesign de interfaces) · phase Direção E · Onda 3
- [[ADR-152]] — `/plano-de-acao` renomeada para `/acao` com tabs (Direção E · Onda 6) · phase Direção E · Onda 6
- [[ADR-155]] — `/dashboard` absorvido por `/plano` (Direção E consolidação) · phase Direção E · consolidação
- [[ADR-156]] — Patrimônio em `/plano` é single-source via `patrimonio_snapshot` (Direção E · Onda 7) · phase Direção E · Onda 7
- [[ADR-158]] — Pipeline review screen — UI dedicada para aprovar/editar `StageReview` · phase Sprint A8 · Lane pipeline-review-screen
- [[ADR-168]] — Remoção do Modo USA do relatório · phase A8.4 PR4

### Proposto (1)

- [[ADR-176]] — Chave estável `cenarios_conjuge` no bloco de narrativas E5.N

## infra

### Decidido (5)

- [[ADR-248]] — Multi-stage backend Dockerfile com dual target (runtime / playwright) — Sprint A20 · phase A20.L1
- [[ADR-249]] — SHA pinning de imagens base + Dependabot Docker — Sprint A20 · phase A20.l2
- [[ADR-252]] — Compose dev unificado + Makefile targets opt-in — Sprint A20 · phase A20.l3
- [[ADR-253]] — Postgres driver — drop psycopg2 → psycopg v3 (sync) — Sprint A20 · phase A20.l8
- [[ADR-254]] — Python lockfile com hashes — pip-tools vs uv — Sprint A20 · phase A20.l10

### Proposto (2)

- [[ADR-250]] — GHCR como registry de imagens + tagging strategy — Sprint A20 · phase A20.l4
- [[ADR-251]] — Trivy image scan blocking + SBOM CycloneDX — Sprint A20 · phase A20.l5

## irpf

### Decidido (6)

- [[ADR-189]] — PGBL: diagnóstico tipificado (4 estados) substitui métrica monovalor no card de Otimização Tributária · phase A11
- [[ADR-194]] — Extensão de `irpf_kpis` com `dependentes` e `dedutiveis_aplicados` (reativação de 2 cards em S_IRPF_OTIMIZACAO) · phase A12
- [[ADR-195]] — PGBL: threshold AUVP (alíquota efetiva) modula variante visual no estado capacidade_disponivel · phase A12
- [[ADR-196]] — Reconciliação dos cards PGBL S7 (fluxo PJ inferido) × S_IRPF_OTIMIZACAO (IRPF declarado) por priorização condicional · phase A12
- [[ADR-197]] — Estado modelo_simplificado expõe componentes elegíveis e redireciona para PGD/MIR (estende ADR-189 §4 Estado 2) · phase A12
- [[ADR-198]] — Chip "Espaço de R$ X" condicional ao pgbl_status no card Dedutíveis Aplicados (encerra débito ADR-194 §6.4) · phase A12

## llm

### Decidido (4)

- [[ADR-149]] — `config/report_layout.yaml` permanece como asset de produto (Sprint A8.0) · phase Sprint A8.0
- [[ADR-157]] — Schema IRPF completo (stage `extract_irpf_full`) · phase Sprint A8 · Lane irpf-full-schema
- [[ADR-165]] — `ValidationIssue` estruturado em `ValidationResult` e `StageReview`
- [[ADR-169]] — Modo incremental estendido aos stages globais E1

### Proposto (10)

- [[ADR-173]] — LLM budget hard-stop + LLMCallLog populada universal
- [[ADR-199]] — Parecer do planejador (E6) supersede review_finances — aggregate PlannerReview event-sourced · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-200]] — Manifest declarativo F5 do exec context — `config/prompts/parecer_planejador.yaml` · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-202]] — Output schema + invariantes do parecer — `parecer_planejador.schema.json` · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-203]] — Tool use híbrido + guardrails — drill-down sob demanda no parecer · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-204]] — Imutabilidade do parecer pós-publicação (estende ADR-187) · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-205]] — Boundary Python/Go — stages LLM permanecem Python; contratos imutáveis · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-207]] — Sigilo metodológico no parecer LLM — mapeamento `ancora_metodologica` → `tema_canonico` · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-208]] — Gating freemium do parecer holístico — Opção B+ (diagnóstico amostra free, plano completo premium) · phase Ato 1 — fundação arquitetural do PLANNER_REVIEW
- [[ADR-261]] — Política de cache invalidation em bump de PROMPT_VERSION — re-extrair vs. servir stale · phase A20.W2

## marketing

### Proposto (2)

- [[ADR-183]] — Pilares narrativos da landing — reposicionamento Mathoms 2026 (Fase 4.B COMPETITIVE_PIERRE) · phase A11
- [[ADR-184]] — Stack da landing estática (Hugo + CF Pages) · phase A11

## methodology

### Decidido (7)

- [[ADR-215]] — Classificação de uso econômico de imóveis via override DB substitui `residencia_principal_keyword` · phase A12
- [[ADR-224]] — `asset_catalog` + `lastro_moeda` per-ativo (catalog global + override per-workspace) · phase A12
- [[ADR-226]] — Desambiguação conta bancária → membro: `account_number` como discriminador, `account_resolver` puro, `is_joint` reservado para V2 · phase A12.bank-account-disambig
- [[ADR-227]] — Imóvel financiado: agregado `Debt` persistido + `property_market_value` override; saldo devedor líquido em `investivel_efetivo`, bruto preservado em cat_2 · phase A15
- [[ADR-229]] — Pre-fill UI a partir de IRPF — pattern genérico `artifact → suggestion endpoint → card`; V1 contas bancárias · phase A13.irpf-prefill-bank-accounts
- [[ADR-235]] — Classificação `nu_proprietario`: imóvel em nu-propriedade com usufruto vitalício de terceiro · phase A16
- [[ADR-236]] — Tributário PJ — Cascata Fiscal canônica (cálculo por regime, base PGBL real, inputs derivados ≫ declarados) · phase A16.tributario-pj-cascata

## money

### Decidido (1)

- [[ADR-164]] — Carteira de renda e taxa de retirada efetiva · phase A8.3

### Roadmap (1)

- [[ADR-160]] — Eficiência tributária imóvel direto vs FII no relatório premium (Roadmap)

## multitenancy

### Decidido (1)

- [[ADR-166]] — Schema estável `cenarios_conjuge` no payload E5 · phase A8.4

### Roadmap (2)

- [[ADR-150]] — Estratégia de port Go do `pipeline-service`: Caminho 1 (shell-only via subprocess) como default deferido para Roadmap · phase deferido em W6-T06, 2026-05-07
- [[ADR-159]] — Aggregator banking BR (Open Finance) — adiar adoção até gatilhos materializarem

## ops

### Proposto (2)

- [[ADR-174]] — Off-site backup criptografado em Cloudflare R2 + restore drill
- [[ADR-228]] — Operational gates pós-A11: closure code-complete da sprint + drills diferidos para go-live · phase A11

## persistence

### Decidido (3)

- [[ADR-163]] — Decision congela `context_snapshot` ao aceitar Suggestion · phase Onda 8
- [[ADR-225]] — Dedup robusto de PropertyIdentity — matrícula/QA como canonical fallback + first-write-wins cross-codigo_rfb · phase A12
- [[ADR-265]] — Fuzzy lookup de PropertyIdentity por proximidade numérica (extensão ADR-225 Case C) · phase A17.canonical-fuzzy

### Proposto (1)

- [[ADR-262]] — Memory confirmation tracking — flag por aggregate de leitura, não enum em Decision (Fase 3.E pré-req) · phase A17.competitive-pierre-3e-prereq

## pipeline

### Decidido (13)

- [[ADR-161]] — Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos) · phase Onda 8
- [[ADR-237]] — Cone Monte Carlo de IF inclui aporte mensal (paridade com projeção determinística) · phase pos-A15
- [[ADR-238]] — Ingestão de Informes de Rendimentos anuais avulsos (PGBL/VGBL, financeiro PF/PJ, proventos) — fonte fiscal primária paralela ao E1.6 · phase A17.informes-avulsos
- [[ADR-239]] — Comprovantes de Bem (CRLV) + Apólices de Seguro polimórficas + FIPE refresh assíncrono — Sprint A18 · phase A18.l1
- [[ADR-256]] — Stages do pipeline compartilham unit-of-work via `WorkspaceContext.get_artifact_store().session` · phase A19.uow-stages
- [[ADR-271]] — Dedup de investimentos cross-IRPF (cross-year + cross-declarante) no consolidador E1.5c · phase A20.invest-dedup
- [[ADR-272]] — Razão estruturada de needs_review (ReviewReason tipado + tabela review_reasons consultável) · phase A20.failure-diagnostics
- [[ADR-278]] — SourceAdapter + SourceRef + data_source + contrato canônico E2 v3 · phase A23 · F0
- [[ADR-279]] — Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge · phase A23 · F0
- [[ADR-280]] — Critério de corte Extract | Transform + check de pureza de extração · phase A23 · F0
- [[ADR-281]] — rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM) · phase A23 · F0
- [[ADR-286]] — Contrato dedicado para o artefato E2-llm (e2_llm_artifact.schema.json) + banco aditivo em cdbresumo · phase A24.l7
- [[ADR-291]] — from_stage lê stages run-scoped upstream de um base_run pinado (fallback ADR-291) · phase A25 · dogfood

### Proposto (18)

- [[ADR-193]] — Taxonomia canônica de classes de ativo no E5 (10 buckets)
- [[ADR-209]] — Convenção numérica de percentual no contrato E5 — valor absoluto · phase Pré-requisito PR-2 do PLANNER_REVIEW
- [[ADR-219]] — Premissas Econômicas — tabela versionada, override por workspace e snapshot no E5 · phase A12
- [[ADR-233]] — Formato canônico de PROMPT_VERSION (semver puro) + gate CI de bump · phase A11.W2
- [[ADR-241]] — E2 (extratos / faturas / LLM fallback) é workspace-scoped — incremental cumulativo correto · phase A17.incremental-correctness
- [[ADR-242]] — LLM `category_hint` consumido no TransactionClassifier + sentinel `info_fiscal_anual` · phase A17.incremental-correctness
- [[ADR-243]] — MemberNameResolver — normalizar `membro` extraído pelo LLM em chave canônica do workspace · phase A17.incremental-correctness
- [[ADR-244]] — InvestmentsConsolidator aceita `tipo_documento=informe_rendimentos` como posição · phase A17.incremental-correctness
- [[ADR-245]] — `caixa_moeda_estrangeira` cai para baseline IRPF quando E3 não traz USD/EUR · phase A17.incremental-correctness
- [[ADR-246]] — Dedup de imóveis co-declarados em IRPFs de titular + cônjuge no consolidador E1.5c · phase A17.imovel-dedup
- [[ADR-255]] — Dedup de transações cross-document no pipeline E3→E4 (chave determinística + needs_review) · phase A17.tx-dedup-cross-doc
- [[ADR-266]] — Completude tri-state de ano-base IRPF: completo / provisorio / incompleto / mudanca_estrutural · phase A16
- [[ADR-267]] — Identidade canônica de membro do workspace via CPF (não slug-de-nome) · phase A17.member-identity
- [[ADR-268]] — Filtro PF vs PJ no Contribuinte do IRPF — rejeitar razão social como nome de membro · phase A17.member-identity
- [[ADR-273]] — Logging estruturado do pipeline (contextvars neutros + bind backend→pipeline + tail bounded) · phase A20.failure-diagnostics
- [[ADR-274]] — Contrato de ano no consolidador E1.5c→E5: chave de resumo em ano-base 31/12, não exercício · phase A21.patrimonio-ano-base
- [[ADR-276]] — EntityDedupPolicy: contrato comum de dedup de entidades patrimoniais no E1.5c · phase A21.l3
- [[ADR-277]] — Previdência F1-O4: reconciliação da recomendação PGBL (não dedup de ativo) · phase A21.l4

## relatorio

### Proposto (4)

- [[ADR-216]] — Cap rate líquido como métrica canônica de imóveis de investimento (S4) · phase A12
- [[ADR-217]] — Score patrimonial canônico — composição, fórmula e ciclo de vida · phase A12
- [[ADR-218]] — Reserva de Emergência — denominador essencial, override por workspace e bandas Cerbasi/Perini · phase A12
- [[ADR-220]] — Impacto estimado em sugestões IF — fluxo anual E patrimônio-alvo separados · phase A12

## report

### Decidido (2)

- [[ADR-191]] — Card Rentabilidade do relatório expõe TRS efetiva — não retorno total · phase A11.W5
- [[ADR-240]] — Card S_PROTECAO no relatório — 4º pilar AUVP entre Reserva e Patrimônio (Sprint A19) · phase A19.l1

### Proposto (2)

- [[ADR-187]] — Relatório publicado é imutável — conceito de mês fechado · phase A11
- [[ADR-190]] — Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica · phase A11

## security

### Decidido (2)

- [[ADR-230]] — Gates de segurança em CI: Trivy fs + IaC + pip-audit + npm audit + gitleaks + GH secret scanning · phase A11.W2
- [[ADR-232]] — Security headers + CORS strict no backend FastAPI (CSP report-only, HSTS, HSTS, allowlist explícita) · phase A11.W2

## Outras

### Decidido (1)

- [[ADR-182]] — Vault de documentação operacional Obsidian-friendly em `docs/` · phase A11.5

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
