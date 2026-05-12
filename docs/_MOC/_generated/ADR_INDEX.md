> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# ADR_INDEX — Índice de Architectural Decision Records

Volta para [`00-INDEX`](../00-INDEX.md).

191 ADRs (ADR-001 a ADR-198) em [`docs/adr/`](../../adr/).

## Sumário por status

- **Decidido**: 168
- **Proposto**: 19
- **Roadmap**: 4

## Fundação

### Decidido (5)

- [[ADR-001]] — SQLAlchemy 2.0 como ORM · phase F1
- [[ADR-002]] — Filesystem local para storage · phase F2
- [[ADR-003]] — JWT custom para auth · phase F1
- [[ADR-006]] — Monorepo · phase F0
- [[ADR-013]] — "Wrap, Don't Rewrite" pattern · phase F0

### Proposto (1)

- [[ADR-005]] — VPS Hetzner para produção · phase F7

## Persistência

### Decidido (3)

- [[ADR-029]] — Alembic para migrations · phase F2
- [[ADR-038]] — Docker volume para storage prod · phase F7
- [[ADR-039]] — Dual DB: SQLite (dev) + PostgreSQL (prod) · phase F7

### Proposto (1)

- [[ADR-171]] — Fernet rotation operacionalizada via MultiFernet

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

### Decidido (5)

- [[ADR-024]] — LiteLLM como proxy universal · phase F4
- [[ADR-025]] — BYOK (Bring Your Own Key) · phase F4
- [[ADR-026]] — Instructor + Pydantic para structured output · phase F4
- [[ADR-027]] — Retry → needs_review em falha de validação · phase F4
- [[ADR-028]] — E7 full scope na Fase 4 · phase F4

## Task Queue

### Decidido (3)

- [[ADR-029-TQ]] — Celery + Redis · phase F5
- [[ADR-031]] — Redis para queue + pub/sub · phase F5
- [[ADR-032]] — Cancel stage-boundary · phase F5

### Proposto (1)

- [[ADR-172]] — Stuck-runs detector via heartbeat + Celery beat

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

### Decidido (11)

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

### Proposto (1)

- [[ADR-058]] — VPS CX32 para sizing · phase F7

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
- [[ADR-128]] — E7-review-llm lê/escreve via `ArtifactStore` · phase A6-cleanup
- [[ADR-129]] — Descontinuação completa do renderer HTML server-side

## Pipeline DDD/SOLID + Infra+Domínio (Sprint A6)

### Decidido (34)

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

## Decisões metodológicas pós-auditoria (Roadmap v2)

### Decidido (1)

- [[ADR-142]] — Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem

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

### Proposto (1)

- [[ADR-170]] — Refresh tokens com httpOnly cookie e family-based revocation

## backend

### Decidido (5)

- [[ADR-153]] — `Suggestion` aggregate (Direção E · Onda 5): proposal imutável + state machine simples · phase Direção E · Onda 5
- [[ADR-154]] — Fusão `KanbanItem` em `Task` + migração `ReportNotes` para `WorkspaceNotes` (Direção E · Onda 1) · phase Direção E · Onda 1 · M1+M2
- [[ADR-162]] — Decisions como event projection sobre Goals · phase Onda 8
- [[ADR-167]] — Eligibility gate de cenário do cônjuge no domain service · phase A8.4 PR2
- [[ADR-192]] — `Protection` aggregate + `ProtectionBundle` (Seção 9 — Riscos e Proteção) · phase Sprint A11.W5

### Proposto (1)

- [[ADR-175]] — Prompt injection defense em camadas (sanitize + system clause + Pydantic strict)

## categorization

### Decidido (3)

- [[ADR-185]] — Política de edição e evolução de overrides de `category_templates` · phase A11.cat-overrides
- [[ADR-186]] — Promoção de override de transação para regra de categorização (learning loop) · phase A12.P2
- [[ADR-188]] — Evolução de schema e semântica do learning loop em P3 (soft-delete, partial unique, revert_count split) · phase A12.P3

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

### Proposto (1)

- [[ADR-173]] — LLM budget hard-stop + LLMCallLog populada universal

## marketing

### Proposto (2)

- [[ADR-183]] — Pilares narrativos da landing — reposicionamento Mathoms 2026 (Fase 4.B COMPETITIVE_PIERRE) · phase A11
- [[ADR-184]] — Stack da landing estática (Hugo + CF Pages) · phase A11

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

### Proposto (1)

- [[ADR-174]] — Off-site backup criptografado em Cloudflare R2 + restore drill

## persistence

### Decidido (1)

- [[ADR-163]] — Decision congela `context_snapshot` ao aceitar Suggestion · phase Onda 8

## pipeline

### Decidido (1)

- [[ADR-161]] — Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos) · phase Onda 8

### Proposto (1)

- [[ADR-193]] — Taxonomia canônica de classes de ativo no E5 (10 buckets)

## report

### Decidido (1)

- [[ADR-191]] — Card Rentabilidade do relatório expõe TRS efetiva — não retorno total · phase A11.W5

### Proposto (2)

- [[ADR-187]] — Relatório publicado é imutável — conceito de mês fechado · phase A11
- [[ADR-190]] — Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica · phase A11

## Outras

### Decidido (1)

- [[ADR-182]] — Vault de documentação operacional Obsidian-friendly em `docs/` · phase A11.5

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
