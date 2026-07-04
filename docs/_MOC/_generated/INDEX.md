> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# Índice geral da vault

| id | type | status | sprint | título | path |
| --- | --- | --- | --- | --- | --- |
| ADR-001 | adr | Decidido |  | SQLAlchemy 2.0 como ORM | `adr/001-sqlalchemy-20-como-orm.md` |
| ADR-002 | adr | Decidido |  | Filesystem local para storage | `adr/002-filesystem-local-para-storage.md` |
| ADR-003 | adr | Decidido |  | JWT custom para auth | `adr/003-jwt-custom-para-auth.md` |
| ADR-005 | adr | Proposto |  | VPS Hetzner para produção | `adr/005-vps-hetzner-para-producao.md` |
| ADR-006 | adr | Decidido |  | Monorepo | `adr/006-monorepo.md` |
| ADR-007 | adr | Decidido |  | Fernet app-level para criptografia | `adr/007-fernet-app-level-para-criptografia.md` |
| ADR-013 | adr | Decidido |  | "Wrap, Don't Rewrite" pattern | `adr/013-wrap-dont-rewrite-pattern.md` |
| ADR-014 | adr | Decidido |  | Threading para execução background | `adr/014-threading-para-execucao-background.md` |
| ADR-015 | adr | Decidido |  | Vault por workspace | `adr/015-vault-por-workspace.md` |
| ADR-016 | adr | Decidido |  | E0-route automático no upload | `adr/016-e0-route-automatico-no-upload.md` |
| ADR-017 | adr | Decidido |  | Sync session em background threads | `adr/017-sync-session-em-background-threads.md` |
| ADR-018 | adr | Decidido |  | `config_dir` override em `for_tenant()` | `adr/018-config-dir-override-em-for-tenant.md` |
| ADR-019 | adr | Decidido |  | `STORAGE_ROOT` via env var | `adr/019-storage-root-via-env-var.md` |
| ADR-020 | adr | Decidido |  | Materializar config em disco | `adr/020-materializar-config-em-disco.md` |
| ADR-021 | adr | Decidido |  | 5 configs editáveis | `adr/021-5-configs-editaveis.md` |
| ADR-022 | adr | Decidido |  | Fallback seletivo de config | `adr/022-fallback-seletivo-de-config.md` |
| ADR-023 | adr | Decidido |  | Import/export JSON de config | `adr/023-importexport-json-de-config.md` |
| ADR-024 | adr | Decidido |  | LiteLLM como proxy universal | `adr/024-litellm-como-proxy-universal.md` |
| ADR-025 | adr | Decidido |  | BYOK (Bring Your Own Key) | `adr/025-byok-bring-your-own-key.md` |
| ADR-026 | adr | Decidido |  | Instructor + Pydantic para structured output | `adr/026-instructor-pydantic-para-structured-output.md` |
| ADR-027 | adr | Decidido |  | Retry → needs_review em falha de validação | `adr/027-retry-needs-review-em-falha-de-validacao.md` |
| ADR-028 | adr | Decidido |  | E7 full scope na Fase 4 | `adr/028-e7-full-scope-na-fase-4.md` |
| ADR-029 | adr | Decidido |  | Alembic para migrations | `adr/029-alembic-para-migrations.md` |
| ADR-029-TQ | adr | Decidido |  | Celery + Redis | `adr/029-tq-celery-redis.md` |
| ADR-030 | adr | Decidido |  | Cancelamento cooperativo via `threading.Event` | `adr/030-cancelamento-cooperativo-via-threadingevent.md` |
| ADR-030-WS | adr | Decidido |  | WebSocket + polling fallback | `adr/030-ws-websocket-polling-fallback.md` |
| ADR-031 | adr | Decidido |  | Redis para queue + pub/sub | `adr/031-redis-para-queue-pubsub.md` |
| ADR-032 | adr | Decidido |  | Cancel stage-boundary | `adr/032-cancel-stage-boundary.md` |
| ADR-033 | adr | Decidido |  | React components para report | `adr/033-react-components-para-report.md` |
| ADR-034 | adr | Decidido |  | Dashboard completo com alertas | `adr/034-dashboard-completo-com-alertas.md` |
| ADR-035 | adr | Decidido |  | `@media print` para PDF export | `adr/035-media-print-para-pdf-export.md` |
| ADR-037 | adr | Decidido |  | Recharts para charts | `adr/037-recharts-para-charts.md` |
| ADR-038 | adr | Decidido |  | Docker volume para storage prod | `adr/038-docker-volume-para-storage-prod.md` |
| ADR-039 | adr | Decidido |  | Dual DB: SQLite (dev) + PostgreSQL (prod) | `adr/039-dual-db-sqlite-dev-postgresql-prod.md` |
| ADR-040 | adr | Decidido |  | Billing adiado para pós-launch | `adr/040-billing-adiado-para-pos-launch.md` |
| ADR-041 | adr | Decidido |  | Traefik como reverse proxy | `adr/041-traefik-como-reverse-proxy.md` |
| ADR-042 | adr | Decidido |  | Design system antes da Fase 5 | `adr/042-design-system-antes-da-fase-5.md` |
| ADR-043 | adr | Decidido |  | shadcn/ui como component library | `adr/043-shadcnui-como-component-library.md` |
| ADR-044 | adr | Decidido |  | Transaction Explorer como core | `adr/044-transaction-explorer-como-core.md` |
| ADR-045 | adr | Decidido |  | Data lineage via tooltip | `adr/045-data-lineage-via-tooltip.md` |
| ADR-046 | adr | Decidido |  | Responsivo sem PWA obrigatório | `adr/046-responsivo-sem-pwa-obrigatorio.md` |
| ADR-047 | adr | Decidido |  | Category override em vez de reconciliação UI | `adr/047-category-override-em-vez-de-reconciliacao-ui.md` |
| ADR-050 | adr | Decidido |  | Tailwind v4 `@theme inline` | `adr/050-tailwind-v4-theme-inline.md` |
| ADR-051 | adr | Decidido |  | Geist fonts | `adr/051-geist-fonts.md` |
| ADR-052 | adr | Decidido |  | Lucide React para ícones | `adr/052-lucide-react-para-icones.md` |
| ADR-053 | adr | Decidido |  | `Intl` nativo para datas | `adr/053-intl-nativo-para-datas.md` |
| ADR-054 | adr | Decidido |  | Migração incremental de pages | `adr/054-migracao-incremental-de-pages.md` |
| ADR-055 | adr | Decidido |  | Coverage target: ≥85% line + ≥95% new code | `adr/055-coverage-target-85-line-95-new-code.md` |
| ADR-056 | adr | Decidido |  | Rolling restart em vez de blue-green | `adr/056-rolling-restart-em-vez-de-blue-green.md` |
| ADR-057 | adr | Decidido |  | JWT 15min + refresh 7d | `adr/057-jwt-15min-refresh-7d.md` |
| ADR-058 | adr | Proposto |  | VPS CX32 para sizing | `adr/058-vps-cx32-para-sizing.md` |
| ADR-059 | adr | Decidido |  | Docker image CVE scan no CI | `adr/059-docker-image-cve-scan-no-ci.md` |
| ADR-060 | adr | Decidido |  | Fernet dual-key para secret rotation | `adr/060-fernet-dual-key-para-secret-rotation.md` |
| ADR-061 | adr | Decidido |  | Telemetria privacy-first | `adr/061-telemetria-privacy-first.md` |
| ADR-062 | adr | Decidido |  | Frontend testing em fase dedicada (6.5) | `adr/062-frontend-testing-em-fase-dedicada-65.md` |
| ADR-063 | adr | Decidido |  | Hardening fintech em sub-fase 6.5D | `adr/063-hardening-fintech-em-sub-fase-65d.md` |
| ADR-064 | adr | Decidido |  | Backend hardening em sub-fase 6.5E | `adr/064-backend-hardening-em-sub-fase-65e.md` |
| ADR-065 | adr | Decidido |  | Sub-fase 7E Operational Readiness | `adr/065-sub-fase-7e-operational-readiness.md` |
| ADR-066 | adr | Decidido |  | Auth flows completos e prompt injection em 7B (bloqueadores de beta) | `adr/066-auth-flows-completos-e-prompt-injection-em-7b.md` |
| ADR-067 | adr | Decidido |  | Test infrastructure em sub-fase 6.5F | `adr/067-test-infrastructure-em-sub-fase-65f.md` |
| ADR-068 | adr | Decidido |  | Códigos internos do pipeline nunca vazam na UI | `adr/068-codigos-internos-do-pipeline-nunca-vazam-na-ui.md` |
| ADR-069 | adr | Decidido |  | MSW sync strategy: manual + lint CI (não codegen) | `adr/069-msw-sync-strategy-manual-lint-ci-nao-codegen.md` |
| ADR-070 | adr | Decidido |  | Premium LLM E2E: mock default + nightly real opt-in | `adr/070-premium-llm-e2e-mock-default-nightly-real-opt-in.md` |
| ADR-071 | adr | Decidido |  | Playwright workspace isolation: email unique por worker | `adr/071-playwright-workspace-isolation-email-unique-por.md` |
| ADR-072 | adr | Decidido |  | Multi-tenancy: `workspace_id` scoping explícito + `WorkspaceMember` para multi-família | `adr/072-multi-tenancy-workspace-id-scoping-explicito.md` |
| ADR-073 | adr | Decidido |  | Goals como entidade versionada (não config estático) | `adr/073-goals-como-entidade-versionada-nao-config-estatico.md` |
| ADR-074 | adr | Decidido |  | Tasks como entidade de 1ª classe (fora do relatório) | `adr/074-tasks-como-entidade-de-1a-classe-fora-do-relatorio.md` |
| ADR-075 | adr | Decidido |  | Cutover CLI → Web: estratégia de transição faseada com adapters | `adr/075-cutover-cli-web-estrategia-de-transicao-faseada.md` |
| ADR-076 | adr | Decidido |  | Design Tokens Unificados Site ↔ Relatório | `adr/076-design-tokens-unificados-site-relatorio.md` |
| ADR-077 | adr | Decidido |  | Pipeline adapter como contrato de cutover (CLI → Web) | `adr/077-pipeline-adapter-como-contrato-de-cutover-cli-web.md` |
| ADR-078 | adr | Decidido |  | Render Nativo React + E6 como Exportador Standalone | `adr/078-render-nativo-react-e6-como-exportador-standalone.md` |
| ADR-079 | adr | Decidido |  | Content-first classification no upload web | `adr/079-content-first-classification-no-upload-web.md` |
| ADR-080 | adr | Decidido |  | Pipeline incremental: extrair só docs novos, consolidar full | `adr/080-pipeline-incremental-extrair-so-docs-novos.md` |
| ADR-081 | adr | Decidido |  | Classificação de documentos unificada (P2) | `adr/081-classificacao-de-documentos-unificada-p2.md` |
| ADR-082 | adr | Decidido |  | PipelineArtifact: artefatos computacionais no banco | `adr/082-pipelineartifact-artefatos-computacionais-no-banco.md` |
| ADR-083 | adr | Decidido |  | ArtifactStore: abstração de I/O para artefatos | `adr/083-artifactstore-abstracao-de-io-para-artefatos.md` |
| ADR-084 | adr | Decidido |  | Content-addressed uploads | `adr/084-content-addressed-uploads.md` |
| ADR-085 | adr | Decidido |  | Eliminar materialização de config em disco | `adr/085-eliminar-materializacao-de-config-em-disco.md` |
| ADR-086 | adr | Decidido |  | MaterializationBridge: adapter temporário | `adr/086-materializationbridge-adapter-temporario.md` |
| ADR-087 | adr | Decidido |  | StageSpec: dependências declarativas | `adr/087-stagespec-dependencias-declarativas.md` |
| ADR-088 | adr | Decidido |  | StageConfig: configuração imutável por parâmetro | `adr/088-stageconfig-configuracao-imutavel-por-parametro.md` |
| ADR-089 | adr | Decidido |  | pipeline/domain/: camada de domínio isolada de I/O | `adr/089-pipelinedomain-camada-de-dominio-isolada-de-io.md` |
| ADR-090 | adr | Decidido |  | Decimal para valores monetários | `adr/090-decimal-money.md` |
| ADR-091 | adr | Decidido |  | Pydantic para domain objects com coleções | `adr/091-pydantic-para-domain-objects-com-colecoes.md` |
| ADR-092 | adr | Proposto |  | Renomear scripts para nomes descritivos de domínio | `adr/092-renomear-scripts-para-nomes-descritivos-de-dominio.md` |
| ADR-093 | adr | Decidido |  | Rename completo de identificadores de stage (Opção A) | `adr/093-rename-completo-de-identificadores-de-stage.md` |
| ADR-094 | adr | Decidido |  | Report: single-active vs. versionado | `adr/094-report-single-active-vs-versionado.md` |
| ADR-095 | adr | Proposto |  | Segurança de `content_json` (LGPD) | `adr/095-seguranca-de-content-json-lgpd.md` |
| ADR-096 | adr | Proposto |  | Observabilidade de cutover | `adr/096-observabilidade-de-cutover.md` |
| ADR-097 | adr | Decidido |  | Extract-then-refactor: estratégia de decomposição de `e3_reconcile.py` | `adr/097-extract-then-refactor-estrategia-de-decomposicao.md` |
| ADR-098 | adr | Decidido |  | Caminho B pragmático vs puro: nomenclatura oficial | `adr/098-caminho-b-pragmatico-vs-puro-nomenclatura-oficial.md` |
| ADR-099 | adr | Decidido |  | Reuse de `analyze_*` legadas em `main_with_store` (decisão de A5d/A5e) | `adr/099-reuse-de-analyze-legadas-em-main-with-store.md` |
| ADR-100 | adr | Decidido |  | A6d commitment: fechar Caminho B puro nos 5 stages pragmáticos | `adr/100-a6d-commitment-fechar-caminho-b-puro-nos-5.md` |
| ADR-101 | adr | Decidido |  | Princípios R12-R17: DDD/SOLID no backend API (A6e) | `adr/101-principios-r12-r17-dddsolid-no-backend-api-a6e.md` |
| ADR-102 | adr | Decidido |  | Princípios R18-R20: language-neutral boundaries (A6f) | `adr/102-principios-r18-r20-language-neutral-boundaries-a6f.md` |
| ADR-103 | adr | Decidido |  | Teste manual como gate antes de remoção do bridge (A6b.5 + A6-human) | `adr/103-teste-manual-como-gate-antes-de-remocao-do.md` |
| ADR-104 | adr | Decidido |  | E1.5c em Caminho B pragmático (Sessão A5f) | `adr/104-e15c-em-caminho-b-pragmatico-sessao-a5f.md` |
| ADR-105 | adr | Decidido |  | LLM stages escrevem via ArtifactStore; E1 e E7-review LLM não migram (A6a) | `adr/105-llm-stages-escrevem-via-artifactstore-e1-e-e7.md` |
| ADR-106 | adr | Decidido |  | Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (A6b) | `adr/106-opt-in-db-artifacts-por-workspace.md` |
| ADR-107 | adr | Decidido |  | Remoção de `MaterializationBridge` e `stage_runner_compat` (A6c.1-2) | `adr/107-remocao-de-materializationbridge-e-stage-runner.md` |
| ADR-108 | adr | Decidido |  | Estratégia de subdomínios `mathoms.ai` + Cloudflare DNS | `adr/108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md` |
| ADR-109 | adr | Decidido |  | Auth portability: JWT HS256 + Fernet documentados como contratos portáveis (A6f.5a) | `adr/109-auth-portability-jwt-hs256-fernet-documentados.md` |
| ADR-110 | adr | Decidido |  | Structured JSON logging + OpenTelemetry bootstrap (A6f.3) | `adr/110-structured-json-logging-opentelemetry-bootstrap.md` |
| ADR-111 | adr | Decidido |  | Stateless-rigoroso: padrão e gate empírico (A6f.6) | `adr/111-stateless-rigoroso-padrao-e-gate-empirico-a6f6.md` |
| ADR-112 | adr | Decidido |  | Pipeline-as-Service: HTTP boundary para execução de stages (A6f.1) | `adr/112-pipeline-as-service-http-boundary-para-execucao.md` |
| ADR-113 | adr | Decidido |  | Convenções Go: `.golangci.yml` + CI + skeleton (A6g.7) | `adr/113-convencoes-go-golangciyml-ci-skeleton-a6g7.md` |
| ADR-114 | adr | Decidido |  | Enforcement automatizado de code style: gates imediatos + progressivos (A6g.6) | `adr/114-enforcement-automatizado-de-code-style-gates.md` |
| ADR-115 | adr | Decidido |  | Domain events tipados: arquitetura e boundaries (A6e.events) | `adr/115-domain-events-tipados-arquitetura-e-boundaries.md` |
| ADR-116 | adr | Decidido |  | F7F-Local: stack Next separada + anonimização default + auth yaml+bcrypt+JWT (F7F-Local) | `adr/116-f7f-local-stack-next-separada-anonimizacao.md` |
| ADR-117 | adr | Decidido |  | Report Premium UI baseline (paridade com EXEMPLO_DE_RELATORIO.html) | `adr/117-report-premium-ui-baseline-paridade-com-exemplo.md` |
| ADR-118 | adr | Decidido |  | Flip do default `MATHOMS_USE_DB_ARTIFACTS` para `True` | `adr/118-flip-do-default-mathoms-use-db-artifacts-para-true.md` |
| ADR-119 | adr | Decidido |  | Contrato `LiveStep` para progresso de etapas do pipeline | `adr/119-contrato-livestep-para-progresso-de-etapas-do.md` |
| ADR-120 | adr | Decidido |  | Readers user-facing consultam `ArtifactStore` (DB-first) com fallback disco | `adr/120-readers-user-facing-consultam-artifactstore-db.md` |
| ADR-121 | adr | Decidido |  | Typography base 13px com override configurável (emendado 2026-04-26: default 16px) | `adr/121-typography-base-13px-com-override-configuravel.md` |
| ADR-122 | adr | Decidido |  | `chart_conclusions` e `section_summaries` em modo híbrido (template + LLM) | `adr/122-chart-conclusions-e-section-summaries-em-modo.md` |
| ADR-123 | adr | Decidido |  | Notas (T6) e Kanban (T3) persistidos no backend | `adr/123-notas-t6-e-kanban-t3-persistidos-no-backend.md` |
| ADR-124 | adr | Decidido |  | `scripts/e6_render.py` aposentado em favor de SSR standalone do Next | `adr/124-scriptse6-renderpy-aposentado-em-favor-de-ssr.md` |
| ADR-125 | adr | Decidido |  | Workspace sharing: convites, viewer role, forced logout | `adr/125-workspace-sharing-convites-viewer-role-forced.md` |
| ADR-126 | adr | Decidido |  | Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO) | `adr/126-multi-tenant-goals-completos-aporte-mensal.md` |
| ADR-127 | adr | Decidido |  | E1 members persiste via ArtifactStore | `adr/127-e1-members-persiste-via-artifactstore.md` |
| ADR-128 | adr | Decidido |  | E7-review-llm lê/escreve via `ArtifactStore` | `adr/128-e7-review-llm-leescreve-via-artifactstore.md` |
| ADR-129 | adr | Decidido |  | Descontinuação completa do renderer HTML server-side | `adr/129-descontinuacao-completa-do-renderer-html-server.md` |
| ADR-130 | adr | Decidido |  | Internacionalização com `next-intl` + persistência em `users.locale` | `adr/130-internacionalizacao-com-next-intl-persistencia.md` |
| ADR-131 | adr | Decidido |  | `Report` referencia `pipeline_artifact` por FK (drop `analysis_json_path`) | `adr/131-report-referencia-pipeline-artifact-por-fk-drop.md` |
| ADR-132 | adr | Decidido |  | Lifecycle scoping de `pipeline_artifacts` (workspace vs run) | `adr/132-lifecycle-scoping-de-pipeline-artifacts.md` |
| ADR-133 | adr | Decidido |  | `transferencias_internas` modelado em `transfer_configs` (workspace-scoped) | `adr/133-transferencias-internas-modelado-em-transfer.md` |
| ADR-134 | adr | Decidido |  | `ConfigStore`: protocolo de leitura tipado (pipeline + backend) | `adr/134-configstore-protocolo-de-leitura-tipado-pipeline.md` |
| ADR-135 | adr | Decidido |  | Versionamento temporal de séries fiscais e câmbio | `adr/135-versionamento-temporal-de-series-fiscais-e-cambio.md` |
| ADR-136 | adr | Decidido |  | `Decision` aggregate event-sourced com supersede chain | `adr/136-decision-aggregate-event-sourced-com-supersede.md` |
| ADR-137 | adr | Decidido |  | Catalog + override resolver para `categorization` e `institutions` | `adr/137-catalog-override-resolver-para-categorization-e.md` |
| ADR-138 | adr | Decidido |  | Protocolo de supervisão CTO para Sprint A7 | `adr/138-protocolo-de-supervisao-cto-para-sprint-a7.md` |
| ADR-139 | adr | Decidido |  | Finalização migração Recharts→Chart.js em /reports/** | `adr/139-finalizacao-migracao-rechartschartjs-em-reports.md` |
| ADR-140 | adr | Roadmap |  | Goal IF schema v2 (renda passiva atual + IF meta líquida) | `adr/140-goal-if-schema-v2-renda-passiva-atual-if-meta.md` |
| ADR-141 | adr | Decidido |  | Goal alocação-alvo schema v2 (7 classes AUVP) | `adr/141-goal-alocacao-alvo-schema-v2-7-classes-auvp.md` |
| ADR-142 | adr | Decidido |  | Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem | `adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md` |
| ADR-143 | adr | Decidido |  | `docs/methodology/` é rules-as-code (Sprint A7.6) | `adr/143-docsmethodology-e-rules-as-code-sprint-a76.md` |
| ADR-144 | adr | Decidido |  | `section_summaries` LLM-driven em E5 com cache + fallback determinístico (v2.9) | `adr/144-section-summaries-llm-driven-em-e5-com-cache.md` |
| ADR-145 | adr | Decidido |  | 7 categorias canonical da composição patrimonial | `adr/145-7-categorias-canonical-da-composicao-patrimonial.md` |
| ADR-146 | adr | Decidido |  | E3 source hierarchy + `BankAccount.source_tier` schema | `adr/146-e3-source-hierarchy-bankaccountsource-tier-schema.md` |
| ADR-147 | adr | Decidido |  | Milhas: valuation methodology universal + storage workspace-scoped | `adr/147-milhas-valuation-methodology-universal-storage.md` |
| ADR-148 | adr | Decidido |  | `SnapshotChangelogBuilder`: comparações mês-a-mês de relatório | `adr/148-snapshotchangelogbuilder-comparacoes-mes-a-mes.md` |
| ADR-149 | adr | Decidido |  | `config/report_layout.yaml` permanece como asset de produto (Sprint A8.0) | `adr/149-configreport-layoutyaml-permanece-como-asset-de.md` |
| ADR-150 | adr | Decidido |  | Estratégia de port Go do `pipeline-service`: Caminho 1 (shell-only via subprocess) como default deferido para Roadmap | `adr/150-estrategia-de-port-go-do-pipeline-service.md` |
| ADR-151 | adr | Decidido |  | Remoção do Modo Tático do relatório (Direção E do redesign de interfaces) | `adr/151-remocao-do-modo-tatico-do-relatorio-direcao-e-do.md` |
| ADR-152 | adr | Decidido |  | `/plano-de-acao` renomeada para `/acao` com tabs (Direção E · Onda 6) | `adr/152-plano-de-acao-renomeada-para-acao-com-tabs.md` |
| ADR-153 | adr | Decidido |  | `Suggestion` aggregate (Direção E · Onda 5): proposal imutável + state machine simples | `adr/153-suggestion-aggregate-direcao-e-onda-5-proposal.md` |
| ADR-154 | adr | Decidido |  | Fusão `KanbanItem` em `Task` + migração `ReportNotes` para `WorkspaceNotes` (Direção E · Onda 1) | `adr/154-fusao-kanbanitem-em-task-migracao-reportnotes.md` |
| ADR-155 | adr | Decidido |  | `/dashboard` absorvido por `/plano` (Direção E consolidação) | `adr/155-dashboard-absorvido-por-plano-direcao-e.md` |
| ADR-156 | adr | Decidido |  | Patrimônio em `/plano` é single-source via `patrimonio_snapshot` (Direção E · Onda 7) | `adr/156-patrimonio-em-plano-e-single-source-via.md` |
| ADR-157 | adr | Decidido |  | Schema IRPF completo (stage `extract_irpf_full`) | `adr/157-schema-irpf-completo-stage-extract-irpf-full.md` |
| ADR-158 | adr | Decidido |  | Pipeline review screen — UI dedicada para aprovar/editar `StageReview` | `adr/158-pipeline-review-screen-ui-dedicada-para.md` |
| ADR-159 | adr | Roadmap |  | Aggregator banking BR (Open Finance) — adiar adoção até gatilhos materializarem | `adr/159-aggregator-banking-br-open-finance-adiar-adocao.md` |
| ADR-160 | adr | Roadmap |  | Eficiência tributária imóvel direto vs FII no relatório premium (Roadmap) | `adr/160-eficiencia-tributaria-imovel-direto-vs-fii-no.md` |
| ADR-161 | adr | Decidido |  | Regras canônicas de Suggestion v2 (Cerbasi/AUVP/Perini completos) | `adr/161-regras-canonicas-de-suggestion-v2.md` |
| ADR-162 | adr | Decidido |  | Decisions como event projection sobre Goals | `adr/162-decisions-como-event-projection-sobre-goals.md` |
| ADR-163 | adr | Decidido |  | Decision congela `context_snapshot` ao aceitar Suggestion | `adr/163-decision-congela-context-snapshot-ao-aceitar.md` |
| ADR-164 | adr | Decidido |  | Carteira de renda e taxa de retirada efetiva | `adr/164-carteira-de-renda-e-taxa-de-retirada-efetiva.md` |
| ADR-165 | adr | Decidido |  | `ValidationIssue` estruturado em `ValidationResult` e `StageReview` | `adr/165-validationissue-estruturado-em-validationresult.md` |
| ADR-166 | adr | Decidido |  | Schema estável `cenarios_conjuge` no payload E5 | `adr/166-schema-estavel-cenarios-conjuge-no-payload-e5.md` |
| ADR-167 | adr | Decidido |  | Eligibility gate de cenário do cônjuge no domain service | `adr/167-eligibility-gate-de-cenario-do-conjuge-no-domain.md` |
| ADR-168 | adr | Decidido |  | Remoção do Modo USA do relatório | `adr/168-remocao-do-modo-usa-do-relatorio.md` |
| ADR-169 | adr | Decidido |  | Modo incremental estendido aos stages globais E1 | `adr/169-modo-incremental-estendido-aos-stages-globais-e1.md` |
| ADR-170 | adr | Decidido |  | Refresh tokens com httpOnly cookie e family-based revocation | `adr/170-refresh-tokens-com-httponly-cookie-e-family.md` |
| ADR-171 | adr | Decidido |  | Fernet rotation operacionalizada via MultiFernet | `adr/171-fernet-rotation-operacionalizada-via-multifernet.md` |
| ADR-172 | adr | Decidido |  | Stuck-runs detector via heartbeat + Celery beat | `adr/172-stuck-runs-detector-via-heartbeat-celery-beat.md` |
| ADR-173 | adr | Decidido |  | LLM budget hard-stop + LLMCallLog populada universal | `adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md` |
| ADR-174 | adr | Proposto |  | Off-site backup criptografado em Cloudflare R2 + restore drill | `adr/174-off-site-backup-criptografado-em-cloudflare-r2.md` |
| ADR-175 | adr | Decidido |  | Prompt injection defense em camadas (sanitize + system clause + Pydantic strict) | `adr/175-prompt-injection-defense-em-camadas-sanitize.md` |
| ADR-176 | adr | Decidido |  | Chave estável `cenarios_conjuge` no bloco de narrativas E5.N | `adr/176-chave-estavel-cenarios-conjuge-no-bloco-de.md` |
| ADR-177 | adr | Decidido |  | Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`) | `adr/177-thresholds-e-referencias-metodologicas-como.md` |
| ADR-178 | adr | Decidido |  | `Risk` aggregate workspace-scoped | `adr/178-risk-aggregate-workspace-scoped.md` |
| ADR-179 | adr | Decidido |  | `Decision` aggregate — extensão de schema (`impact_1y/10y`, `horizon`, `priority`) | `adr/179-decision-aggregate-extensao-de-schema-impact.md` |
| ADR-180 | adr | Decidido |  | `goals.json` cutover final via `StageConfig.config_store` extendido | `adr/180-goalsjson-cutover-final-via-stageconfigconfig.md` |
| ADR-181 | adr | Decidido |  | `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py` | `adr/181-goalsjson-removido-de-archive-e-adicionado-a.md` |
| ADR-182 | adr | Decidido |  | Vault de documentação operacional Obsidian-friendly em `docs/` | `adr/182-vault-de-documentacao-operacional-obsidian.md` |
| ADR-183 | adr | Proposto |  | Pilares narrativos da landing — reposicionamento Mathoms 2026 (Fase 4.B COMPETITIVE_PIERRE) | `adr/183-landing-positioning-pillars-2026.md` |
| ADR-184 | adr | Proposto |  | Stack da landing estática (Hugo + CF Pages) | `adr/184-landing-static-stack-2026.md` |
| ADR-185 | adr | Decidido |  | Política de edição e evolução de overrides de `category_templates` | `adr/185-politica-de-overrides-de-categoria.md` |
| ADR-186 | adr | Decidido |  | Promoção de override de transação para regra de categorização (learning loop) | `adr/186-promocao-override-transacao-para-regra-categorizacao.md` |
| ADR-187 | adr | Decidido |  | Relatório publicado é imutável — conceito de mês fechado | `adr/187-relatorio-publicado-imutavel-mes-fechado.md` |
| ADR-188 | adr | Decidido |  | Evolução de schema e semântica do learning loop em P3 (soft-delete, partial unique, revert_count split) | `adr/188-evolucao-schema-e-semantica-learning-loop-p3.md` |
| ADR-189 | adr | Decidido |  | PGBL: diagnóstico tipificado (4 estados) substitui métrica monovalor no card de Otimização Tributária | `adr/189-pgbl-diagnostico-tipificado-substitui-metrica-monovalor.md` |
| ADR-190 | adr | Decidido |  | Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica | `adr/190-snapshot-changelog-v3-metricas-cadencia-decomposicao.md` |
| ADR-191 | adr | Decidido |  | Card Rentabilidade do relatório expõe TRS efetiva — não retorno total | `adr/191-card-rentabilidade-trs-efetiva.md` |
| ADR-192 | adr | Decidido |  | `Protection` aggregate + `ProtectionBundle` (Seção 9 — Riscos e Proteção) | `adr/192-protection-aggregate-protectionbundle-secao-9.md` |
| ADR-193 | adr | Decidido |  | Taxonomia canônica de classes de ativo no E5 (10 buckets) | `adr/193-taxonomia-canonica-classes-de-ativo-no-e5.md` |
| ADR-194 | adr | Decidido |  | Extensão de `irpf_kpis` com `dependentes` e `dedutiveis_aplicados` (reativação de 2 cards em S_IRPF_OTIMIZACAO) | `adr/194-irpf-kpis-dependentes-dedutiveis-extension.md` |
| ADR-195 | adr | Decidido |  | PGBL: threshold AUVP (alíquota efetiva) modula variante visual no estado capacidade_disponivel | `adr/195-pgbl-threshold-auvp-modula-variante.md` |
| ADR-196 | adr | Decidido |  | Reconciliação dos cards PGBL S7 (fluxo PJ inferido) × S_IRPF_OTIMIZACAO (IRPF declarado) por priorização condicional | `adr/196-reconciliacao-cards-pgbl-s7-irpf.md` |
| ADR-197 | adr | Decidido |  | Estado modelo_simplificado expõe componentes elegíveis e redireciona para PGD/MIR (estende ADR-189 §4 Estado 2) | `adr/197-irpf-simplificado-componentes-elegiveis-pgd-mir.md` |
| ADR-198 | adr | Decidido |  | Chip "Espaço de R$ X" condicional ao pgbl_status no card Dedutíveis Aplicados (encerra débito ADR-194 §6.4) | `adr/198-dedutiveis-chip-espaco-condicional-pgbl-status.md` |
| ADR-199 | adr | Decidido |  | Parecer do planejador (E6) supersede review_finances — aggregate PlannerReview event-sourced | `adr/199-parecer-planejador-supersede-review-finances.md` |
| ADR-200 | adr | Decidido |  | Manifest declarativo F5 do exec context — `config/prompts/parecer_planejador.yaml` | `adr/200-manifest-declarativo-parecer-context.md` |
| ADR-201 | adr | Decidido |  | Persona do planejador como rules-as-code — `config/agents/planner_persona.md` | `adr/201-persona-planner-rules-as-code.md` |
| ADR-202 | adr | Decidido |  | Output schema + invariantes do parecer — `parecer_planejador.schema.json` | `adr/202-output-schema-parecer-planejador.md` |
| ADR-203 | adr | Decidido |  | Tool use híbrido + guardrails — drill-down sob demanda no parecer | `adr/203-tool-use-hibrido-drill-down-parecer.md` |
| ADR-204 | adr | Decidido |  | Imutabilidade do parecer pós-publicação (estende ADR-187) | `adr/204-imutabilidade-parecer-pos-publicacao.md` |
| ADR-205 | adr | Decidido |  | Boundary Python/Go — stages LLM permanecem Python; contratos imutáveis | `adr/205-boundary-python-go-stages-llm-permanecem-python.md` |
| ADR-206 | adr | Decidido |  | Telemetria de campo faltante como signal de evolução do manifest (estende ADR-188) | `adr/206-telemetria-campo-faltante-parecer.md` |
| ADR-207 | adr | Decidido |  | Sigilo metodológico no parecer LLM — mapeamento `ancora_metodologica` → `tema_canonico` | `adr/207-sigilo-metodologico-parecer-mapeamento-ancora-tema.md` |
| ADR-208 | adr | Decidido |  | Gating freemium do parecer holístico — Opção B+ (diagnóstico amostra free, plano completo premium) | `adr/208-gating-parecer-holistico-free-vs-premium.md` |
| ADR-209 | adr | Decidido |  | Convenção numérica de percentual no contrato E5 — valor absoluto | `adr/209-convencao-numerica-percentual-absoluto.md` |
| ADR-210 | adr | Decidido |  | Saúde do test suite do CI — gates, telemetria e ciclo de vida | `adr/210-saude-do-test-suite-do-ci.md` |
| ADR-211 | adr | Decidido |  | llm_config e pipeline.json como overrides DB-direto (cutover completo do A7) | `adr/211-llm-config-db-overrides.md` |
| ADR-212 | adr | Decidido |  | Sunset `MATHOMS_USE_DB_ARTIFACTS` + `DiskArtifactStore` + CLI standalone do pipeline | `adr/212-sunset-mathoms-use-db-artifacts-disk-store-cli.md` |
| ADR-213 | adr | Decidido |  | Sunset stage `audit_documents` (e cleanup de `_STAGE_TO_DIR` órfão) | `adr/213-sunset-stage-audit-documents.md` |
| ADR-214 | adr | Decidido |  | `Decision.code` é server-generated com `pg_advisory_xact_lock` | `adr/214-decision-code-server-generated.md` |
| ADR-215 | adr | Decidido |  | Classificação de uso econômico de imóveis via override DB substitui `residencia_principal_keyword` | `adr/215-classificacao-imoveis-override-db-first.md` |
| ADR-216 | adr | Decidido |  | Cap rate líquido como métrica canônica de imóveis de investimento (S4) | `adr/216-cap-rate-liquido-canonico-imoveis.md` |
| ADR-217 | adr | Decidido |  | Score patrimonial canônico — composição, fórmula e ciclo de vida | `adr/217-score-patrimonial-canonico.md` |
| ADR-218 | adr | Proposto |  | Reserva de Emergência — denominador essencial, override por workspace e bandas Cerbasi/Perini | `adr/218-reserva-emergencia-denominador-essencial.md` |
| ADR-219 | adr | Decidido |  | Premissas Econômicas — tabela versionada, override por workspace e snapshot no E5 | `adr/219-premissas-economicas-versionadas.md` |
| ADR-220 | adr | Decidido |  | Impacto estimado em sugestões IF — fluxo anual E patrimônio-alvo separados | `adr/220-impacto-estimado-sugestoes-if.md` |
| ADR-221 | adr | Proposto |  | Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto | `adr/221-catalog-driven-market-rate-ingestion.md` |
| ADR-222 | adr | Decidido |  | Toggle `imoveis_no_if` migra de `pipeline.json` global para coluna `workspaces.imoveis_no_if` | `adr/222-imoveis-no-if-per-workspace.md` |
| ADR-223 | adr | Decidido |  | Default conservador `imoveis_no_if=false` para workspaces novos + banner contextual | `adr/223-flip-default-imoveis-no-if-conservador.md` |
| ADR-224 | adr | Decidido |  | `asset_catalog` + `lastro_moeda` per-ativo (catalog global + override per-workspace) | `adr/224-asset-catalog-lastro-moeda.md` |
| ADR-225 | adr | Decidido |  | Dedup robusto de PropertyIdentity — matrícula/QA como canonical fallback + first-write-wins cross-codigo_rfb | `adr/225-property-identity-dedup-robusto.md` |
| ADR-226 | adr | Decidido |  | Desambiguação conta bancária → membro: `account_number` como discriminador, `account_resolver` puro, `is_joint` reservado para V2 | `adr/226-bank-account-member-disambiguation.md` |
| ADR-227 | adr | Decidido |  | Imóvel financiado: agregado `Debt` persistido + `property_market_value` override; saldo devedor líquido em `investivel_efetivo`, bruto preservado em cat_2 | `adr/227-imovel-financiado-debt-aggregate-valor-mercado.md` |
| ADR-228 | adr | Proposto |  | Operational gates pós-A11: closure code-complete da sprint + drills diferidos para go-live | `adr/228-operational-gates-pos-a11.md` |
| ADR-229 | adr | Decidido |  | Pre-fill UI a partir de IRPF — pattern genérico `artifact → suggestion endpoint → card`; V1 contas bancárias | `adr/229-irpf-prefill-suggestions.md` |
| ADR-230 | adr | Decidido |  | Gates de segurança em CI: Trivy fs + IaC + pip-audit + npm audit + gitleaks + GH secret scanning | `adr/230-security-gates-ci.md` |
| ADR-231 | adr | Decidido |  | Encryption at-rest de PII em pipeline_artifacts via Fernet wrapper (hook em DBArtifactStore) | `adr/231-pii-encryption-pipeline-artifacts.md` |
| ADR-232 | adr | Decidido |  | Security headers + CORS strict no backend FastAPI (CSP report-only, HSTS, HSTS, allowlist explícita) | `adr/232-security-headers-cors-strict.md` |
| ADR-233 | adr | Decidido |  | Formato canônico de PROMPT_VERSION (semver puro) + gate CI de bump | `adr/233-prompt-version-format.md` |
| ADR-234 | adr | Decidido |  | Adicionar `paused` ao vocabulário de `sprint_status` (4º valor) | `adr/234-sprint-status-paused.md` |
| ADR-235 | adr | Decidido |  | Classificação `nu_proprietario`: imóvel em nu-propriedade com usufruto vitalício de terceiro | `adr/235-nu-proprietario-usufruto-vitalicio-de-terceiro.md` |
| ADR-236 | adr | Decidido |  | Tributário PJ — Cascata Fiscal canônica (cálculo por regime, base PGBL real, inputs derivados ≫ declarados) | `adr/236-tributario-pj-cascata-fiscal-canonica.md` |
| ADR-237 | adr | Decidido |  | Cone Monte Carlo de IF inclui aporte mensal (paridade com projeção determinística) | `adr/237-monte-carlo-if-with-pmt.md` |
| ADR-238 | adr | Decidido |  | Ingestão de Informes de Rendimentos anuais avulsos (PGBL/VGBL, financeiro PF/PJ, proventos) — fonte fiscal primária paralela ao E1.6 | `adr/238-ingestao-informes-rendimentos-anuais-avulsos.md` |
| ADR-239 | adr | Decidido |  | Comprovantes de Bem (CRLV) + Apólices de Seguro polimórficas + FIPE refresh assíncrono — Sprint A18 | `adr/239-comprovantes-bens-apolices-fipe.md` |
| ADR-240 | adr | Decidido |  | Card S_PROTECAO no relatório — 4º pilar AUVP entre Reserva e Patrimônio (Sprint A19) | `adr/240-card-protecao-patrimonial-pilar-auvp.md` |
| ADR-241 | adr | Decidido |  | E2 (extratos / faturas / LLM fallback) é workspace-scoped — incremental cumulativo correto | `adr/241-e2-workspace-scoped-em-incremental.md` |
| ADR-242 | adr | Decidido |  | LLM `category_hint` consumido no TransactionClassifier + sentinel `info_fiscal_anual` | `adr/242-llm-category-hint-consumido-no-classifier.md` |
| ADR-243 | adr | Decidido |  | MemberNameResolver — normalizar `membro` extraído pelo LLM em chave canônica do workspace | `adr/243-membername-resolver-canonico.md` |
| ADR-244 | adr | Decidido |  | InvestmentsConsolidator aceita `tipo_documento=informe_rendimentos` como posição | `adr/244-informe-rendimentos-em-investments-consolidator.md` |
| ADR-245 | adr | Decidido |  | `caixa_moeda_estrangeira` cai para baseline IRPF quando E3 não traz USD/EUR | `adr/245-fallback-baseline-irpf-em-caixa-moeda-estrangeira.md` |
| ADR-246 | adr | Decidido |  | Dedup de imóveis co-declarados em IRPFs de titular + cônjuge no consolidador E1.5c | `adr/246-dedup-imoveis-cross-irpf.md` |
| ADR-247 | adr | Decidido |  | Documentação canônica permanece em Markdown; HTML apenas como artefato derivado/efêmero | `adr/247-markdown-canonico-html-apenas-artefato-derivado.md` |
| ADR-248 | adr | Decidido |  | Multi-stage backend Dockerfile com dual target (runtime / playwright) — Sprint A20 | `adr/248-multi-stage-backend-playwright-dual-target.md` |
| ADR-249 | adr | Decidido |  | SHA pinning de imagens base + Dependabot Docker — Sprint A20 | `adr/249-sha-pinning-bases-dependabot-docker.md` |
| ADR-250 | adr | Proposto |  | GHCR como registry de imagens + tagging strategy — Sprint A20 | `adr/250-ghcr-registry-tagging-strategy.md` |
| ADR-251 | adr | Proposto |  | Trivy image scan blocking + SBOM CycloneDX — Sprint A20 | `adr/251-trivy-image-scan-blocking-sbom.md` |
| ADR-252 | adr | Decidido |  | Compose dev unificado + Makefile targets opt-in — Sprint A20 | `adr/252-compose-dev-unificado-makefile-onboarding.md` |
| ADR-253 | adr | Decidido |  | Postgres driver — drop psycopg2 → psycopg v3 (sync) — Sprint A20 | `adr/253-postgres-driver-consolidation.md` |
| ADR-254 | adr | Decidido |  | Python lockfile com hashes — pip-tools vs uv — Sprint A20 | `adr/254-python-lockfile-com-hashes.md` |
| ADR-255 | adr | Decidido |  | Dedup de transações cross-document no pipeline E3→E4 (chave determinística + needs_review) | `adr/255-dedup-transacoes-cross-document.md` |
| ADR-256 | adr | Decidido |  | Stages do pipeline compartilham unit-of-work via `WorkspaceContext.get_artifact_store().session` | `adr/256-uow-stages-pipeline-store-session.md` |
| ADR-259 | adr | Proposto |  | Boundary LLM unificado — Decimal monetário + PII (cpf_present + Fernet + UX decrypt) | `adr/259-boundary-llm-unified.md` |
| ADR-260 | adr | Proposto |  | Telemetria LLM por prompt_version — labels compostos em LLMCallLog SQL + OTLP | `adr/260-llm-telemetry-by-prompt-version.md` |
| ADR-261 | adr | Proposto |  | Política de cache invalidation em bump de PROMPT_VERSION — re-extrair vs. servir stale | `adr/261-llm-cache-invalidation-policy.md` |
| ADR-262 | adr | Decidido |  | Memory confirmation tracking — flag por aggregate de leitura, não enum em Decision (Fase 3.E pré-req) | `adr/262-memory-confirmation-tracking.md` |
| ADR-263 | adr | Decidido |  | Goal type RESERVA_EMERGENCIA — schema versionado por workspace ancorado em INV1 (Fase 3.E pré-req) | `adr/263-goal-reserva-emergencia-schema.md` |
| ADR-264 | adr | Proposto |  | Goal type META_OBJETIVO — schema genérico para metas estruturadas (casa, educação, intercâmbio, aposentadoria do cônjuge) (Fase 3.E pré-req) | `adr/264-goal-meta-objetivo-schema.md` |
| ADR-265 | adr | Decidido |  | Fuzzy lookup de PropertyIdentity por proximidade numérica (extensão ADR-225 Case C) | `adr/265-fuzzy-canonical-property-identity.md` |
| ADR-266 | adr | Decidido |  | Completude tri-state de ano-base IRPF: completo / provisorio / incompleto / mudanca_estrutural | `adr/266-irpf-anobase-completude-tristate.md` |
| ADR-267 | adr | Decidido |  | Identidade canônica de membro do workspace via CPF (não slug-de-nome) | `adr/267-member-identity-cpf-canonical.md` |
| ADR-268 | adr | Decidido |  | Filtro PF vs PJ no Contribuinte do IRPF — rejeitar razão social como nome de membro | `adr/268-contribuinte-pf-vs-pj-filter.md` |
| ADR-269 | adr | Decidido |  | Dedup de TaskSuggestion via soft-supersede + dedup_key normalizado | `adr/269-task-suggestion-dedup-supersede.md` |
| ADR-270 | adr | Decidido |  | Retry de LLM calls — categoria network + cap de timeout | `adr/270-llm-retry-network-category-timeout-cap.md` |
| ADR-271 | adr | Decidido |  | Dedup de investimentos cross-IRPF (cross-year + cross-declarante) no consolidador E1.5c | `adr/271-dedup-investimentos-cross-irpf.md` |
| ADR-272 | adr | Decidido |  | Razão estruturada de needs_review (ReviewReason tipado + tabela review_reasons consultável) | `adr/272-needs-review-razao-estruturada.md` |
| ADR-273 | adr | Decidido |  | Logging estruturado do pipeline (contextvars neutros + bind backend→pipeline + tail bounded) | `adr/273-logging-estruturado-pipeline.md` |
| ADR-274 | adr | Decidido |  | Contrato de ano no consolidador E1.5c→E5: chave de resumo em ano-base 31/12, não exercício | `adr/274-patrimonio-ano-base-vs-exercicio.md` |
| ADR-275 | adr | Decidido |  | Auditoria de acesso + política de retenção LGPD | `adr/275-auditoria-de-acesso-e-retencao-lgpd.md` |
| ADR-276 | adr | Decidido |  | EntityDedupPolicy: contrato comum de dedup de entidades patrimoniais no E1.5c | `adr/276-entity-dedup-policy-contract.md` |
| ADR-277 | adr | Decidido |  | Previdência F1-O4: reconciliação da recomendação PGBL (não dedup de ativo) | `adr/277-previdencia-reconciliacao-recomendacao-pgbl.md` |
| ADR-278 | adr | Decidido |  | SourceAdapter + SourceRef + data_source + contrato canônico E2 v3 | `adr/278-source-adapter-canonical-contract.md` |
| ADR-279 | adr | Decidido |  | Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge | `adr/279-lineage-field-level-reverse-index.md` |
| ADR-280 | adr | Decidido |  | Critério de corte Extract | Transform + check de pureza de extração | `adr/280-extract-transform-cut-criterion.md` |
| ADR-281 | adr | Decidido |  | rule_ref derivado de dict literal + lineage_diff (substrato de debug LLM) | `adr/281-lineage-rule-ref-debug-substrate.md` |
| ADR-282 | adr | Decidido |  | Identidade de TransactionOverride unificada no natural_key v2 (fecha D6 da A23.l3) | `adr/282-override-identity-natural-key-v2.md` |
| ADR-283 | adr | Decidido |  | Float monetário persistido e hardening de boundary de schema (patrimonio_liquido, gate models, E2 items) | `adr/283-float-monetario-persistido-e-hardening-de-boundary.md` |
| ADR-284 | adr | Decidido |  | Schema validation: mode_overrides per-schema, enforcement strict real e telemetria de drift | `adr/284-schema-validation-mode-overrides-per-stage.md` |
| ADR-285 | adr | Proposto |  | backend/app/services/: subpacotes por natureza técnica, nunca por domínio de negócio | `adr/285-services-subpacotes-por-natureza-tecnica.md` |
| ADR-286 | adr | Decidido |  | Contrato dedicado para o artefato E2-llm (e2_llm_artifact.schema.json) + banco aditivo em cdbresumo | `adr/286-contrato-dedicado-artefato-e2-llm.md` |
| ADR-287 | adr | Decidido |  | Flip do dedup E4 para identidade natural_key v2 (passo 2 da B4) | `adr/287-flip-dedup-e4-identidade-v2.md` |
| ADR-288 | adr | Decidido |  | Identificador fiscal ilegível em extração LLM degrada para None determinístico — nunca hard-fail retryable | `adr/288-identificador-fiscal-ilegivel-degrada-para-none-no-boundary-llm.md` |
| ADR-289 | adr | Decidido |  | Catálogo de modelos LLM como fonte única + endpoint GET /llm/models (curado agora, dinâmico depois) | `adr/289-catalogo-modelos-llm-fonte-unica.md` |
| ADR-290 | adr | Decidido |  | Supersede-per-run + thesis_key para Suggestion origin=llm (parecer) — extensão de ADR-269 ao aggregate Suggestion | `adr/290-supersede-per-run-thesis-key-suggestion.md` |
| ADR-291 | adr | Decidido |  | from_stage lê stages run-scoped upstream de um base_run pinado (fallback ADR-291) | `adr/291-from-stage-base-run-fallback.md` |
| ADR-292 | adr | Decidido |  | evidencia_path/field_path inválido → None no boundary do LLM (anti reask storm do parecer) | `adr/292-evidencia-path-boundary-coercion.md` |
| ADR-293 | adr | Decidido |  | Citação de parecer (E6→E5) como edge de lineage por chave natural | `adr/293-parecer-citation-edge-chave-natural.md` |
| ADR-294 | adr | Decidido |  | Coerção no boundary dos reask triggers remanescentes do parecer (prosa truncável + impacto_estimado drop) | `adr/294-parecer-boundary-coercion-prose-impacto.md` |
| ADR-295 | adr | Decidido |  | Enforcement por-item da citação verificada no modo strict (parecer E6) | `adr/295-enforcement-por-item-citacao-strict.md` |
| ADR-296 | adr | Decidido |  | Citação determinística: LLM emite (claim, path, rótulo); pipeline renderiza o valor da folha | `adr/296-citacao-deterministica-render-from-path.md` |
| ADR-297 | adr | Decidido |  | Report idempotente sob redelivery do Celery — índice único parcial + guarda terminal | `adr/297-report-idempotente-redelivery.md` |
| ADR-298 | adr | Decidido |  | Ratchet de estilo: metas decrescentes via save-baseline manual + correção da distribuição de dívida (resposta audit r2) | `adr/298-ratchet-metas-decrescentes-e-distribuicao-de-divida.md` |
| ADR-299 | adr | Decidido |  | SEC-03 procede: requirements.lock congelava 17 CVEs reais — bump aiohttp/starlette/python-multipart/cryptography (resposta audit r2) | `adr/299-sec03-deps-17-cves-procede.md` |
| ADR-300 | adr | Decidido |  | Red lines do parecer: 4ª camada de validação determinística (conselho defensável) | `adr/300-red-lines-parecer-defensavel.md` |
| ADR-301 | adr | Decidido |  | Schema formal de dívidas + dedup cross-IRPF (EntityDedupPolicy) | `adr/301-schema-formal-dividas-dedup-cross-year.md` |
| ADR-302 | adr | Decidido |  | Skill audit-vault — auditoria recorrente de vault como procedimento do loop principal | `adr/302-audit-vault-skill.md` |
| ADR-303 | adr | Decidido |  | Boundary de artefatos do executor remoto (A3.store): pipeline-service injeta DBArtifactStore do backend, sessão-por-stage | `adr/303-boundary-artefatos-executor-remoto-a3store.md` |
| ADR-304 | adr | Decidido |  | KR1 do parecer — pureza monetária da prosa: fix de prompt + doutrina de enforcement | `adr/304-kr1-pureza-monetaria-prosa-parecer.md` |
| ADR-305 | adr | Decidido |  | PGBL: ano-base fiscal único por relatório — irpf_kpis e previdencia_pgbl colapsam no ano-base default (ADR-266) | `adr/305-pgbl-ano-base-fiscal-unico.md` |
| ADR-306 | adr | Decidido |  | Política de base temporal de mensalização no E5 — janela canônica 12m + rótulo de janela por bloco | `adr/306-politica-de-base-temporal-de-mensalizacao-no-e5.md` |
| ARCHIVE-pre-a6 | archive-index |  |  | Histórico pré-Sprint A6 (F6.5 + Bootstrap blocks) | `sprint/_archive_pre_a6/_README.md` |
| CHG-2026-04-12-F0 | changelog-entry |  | F0 |  | `sprint/F0/changelog/CHG-2026-04-12-F0.md` |
| CHG-2026-04-13-F1 | changelog-entry |  | F1 |  | `sprint/F1/changelog/CHG-2026-04-13-F1.md` |
| CHG-2026-04-14-F2 | changelog-entry |  | F2 |  | `sprint/F2/changelog/CHG-2026-04-14-F2.md` |
| CHG-2026-04-14-F3 | changelog-entry |  | F3 |  | `sprint/F3/changelog/CHG-2026-04-14-F3.md` |
| CHG-2026-04-14-F4 | changelog-entry |  | F4 |  | `sprint/F4/changelog/CHG-2026-04-14-F4.md` |
| CHG-2026-04-14-F45 | changelog-entry |  | F4 |  | `sprint/F4/changelog/CHG-2026-04-14-F45.md` |
| CHG-2026-04-14-F5 | changelog-entry |  | F5 |  | `sprint/F5/changelog/CHG-2026-04-14-F5.md` |
| CHG-2026-04-14-F6 | changelog-entry |  | F6 |  | `sprint/F6/changelog/CHG-2026-04-14-F6.md` |
| CHG-2026-04-15-BLOCO-0 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-0.md` |
| CHG-2026-04-15-BLOCO-1 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-1.md` |
| CHG-2026-04-15-BLOCO-2 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-2.md` |
| CHG-2026-04-15-BLOCO-3 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-3.md` |
| CHG-2026-04-15-BLOCO-3-1 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-3-1.md` |
| CHG-2026-04-15-BLOCO-4 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-4.md` |
| CHG-2026-04-15-BLOCO-5 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-5.md` |
| CHG-2026-04-15-BLOCO-6 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-BLOCO-6.md` |
| CHG-2026-04-15-F6-5 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F6-5.md` |
| CHG-2026-04-15-F6-5-1 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F6-5-1.md` |
| CHG-2026-04-15-F65 | changelog-entry |  | F6 |  | `sprint/F6/changelog/CHG-2026-04-15-F65.md` |
| CHG-2026-04-15-F65-10-PAGES-COBERTAS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-10-PAGES-COBERTAS.md` |
| CHG-2026-04-15-F65-102-TESTS-EM-FORMAT | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-102-TESTS-EM-FORMAT.md` |
| CHG-2026-04-15-F65-15-TESTS-EM-USEPIPEL | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-15-TESTS-EM-USEPIPEL.md` |
| CHG-2026-04-15-F65-16-TESTS-EM-EXPORT-T | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-16-TESTS-EM-EXPORT-T.md` |
| CHG-2026-04-15-F65-17-TESTS-EM-API-TS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-17-TESTS-EM-API-TS.md` |
| CHG-2026-04-15-F65-25-E2E-SPECS-PLAYWRI | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-25-E2E-SPECS-PLAYWRI.md` |
| CHG-2026-04-15-F65-438-TESTS-PASSING-EM | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-438-TESTS-PASSING-EM.md` |
| CHG-2026-04-15-F65-8-COMPOSTOS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-8-COMPOSTOS.md` |
| CHG-2026-04-15-F65-9-PLAYWRIGHT-SPECS-2 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-9-PLAYWRIGHT-SPECS-2.md` |
| CHG-2026-04-15-F65-9-TESTS-EM-UTILS-TS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-9-TESTS-EM-UTILS-TS.md` |
| CHG-2026-04-15-F65-ALEMBIC-GUARDRAILS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ALEMBIC-GUARDRAILS.md` |
| CHG-2026-04-15-F65-ANTI-REGRESSION-BANK | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ANTI-REGRESSION-BANK.md` |
| CHG-2026-04-15-F65-ARQUIVOS-CRIADOS-HIG | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ARQUIVOS-CRIADOS-HIG.md` |
| CHG-2026-04-15-F65-AXE-CORE-VITEST-AXE | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-AXE-CORE-VITEST-AXE.md` |
| CHG-2026-04-15-F65-CI-GH-ACTIONS-GITHUB | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-CI-GH-ACTIONS-GITHUB.md` |
| CHG-2026-04-15-F65-CI-REPORTER-EXPANDID | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-CI-REPORTER-EXPANDID.md` |
| CHG-2026-04-15-F65-CONCURRENCY-TEST-MAT | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-CONCURRENCY-TEST-MAT.md` |
| CHG-2026-04-15-F65-CPF-MOD-11-DETERMIN | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-CPF-MOD-11-DETERMIN.md` |
| CHG-2026-04-15-F65-DARK-MODE-INTEGRATIO | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-DARK-MODE-INTEGRATIO.md` |
| CHG-2026-04-15-F65-DOCS-SMOKE-TEST-MD | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-DOCS-SMOKE-TEST-MD.md` |
| CHG-2026-04-15-F65-DOCS-TESTING-MD-EXPA | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-DOCS-TESTING-MD-EXPA.md` |
| CHG-2026-04-15-F65-ERROR-BOUNDARY | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ERROR-BOUNDARY.md` |
| CHG-2026-04-15-F65-FIX-ALEMBIC-CWD-SENS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-FIX-ALEMBIC-CWD-SENS.md` |
| CHG-2026-04-15-F65-FOCUS-MANAGEMENT | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-FOCUS-MANAGEMENT.md` |
| CHG-2026-04-15-F65-FORM-VALIDATION-PARA | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-FORM-VALIDATION-PARA.md` |
| CHG-2026-04-15-F65-GITHUB-CODEOWNERS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-GITHUB-CODEOWNERS.md` |
| CHG-2026-04-15-F65-GOLDEN-FILE-PIPELINE | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-GOLDEN-FILE-PIPELINE.md` |
| CHG-2026-04-15-F65-ISOLATION-PARAM-TRIC | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ISOLATION-PARAM-TRIC.md` |
| CHG-2026-04-15-F65-LLM-MOCK-FIXTURES | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-LLM-MOCK-FIXTURES.md` |
| CHG-2026-04-15-F65-MSW-SYNC-LINT | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-MSW-SYNC-LINT.md` |
| CHG-2026-04-15-F65-PEND-NCIAS-CARREGADA | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-PEND-NCIAS-CARREGADA.md` |
| CHG-2026-04-15-F65-PIPELINE-MOCK-FIXTUR | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-PIPELINE-MOCK-FIXTUR.md` |
| CHG-2026-04-15-F65-PRE-COMMIT-HOOKS | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-PRE-COMMIT-HOOKS.md` |
| CHG-2026-04-15-F65-RESILIENCE | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-RESILIENCE.md` |
| CHG-2026-04-15-F65-RESULTADO-AGREGADO | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-RESULTADO-AGREGADO.md` |
| CHG-2026-04-15-F65-ROUND-TRIP-TESTS-PAR | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-ROUND-TRIP-TESTS-PAR.md` |
| CHG-2026-04-15-F65-SCAFFOLDS-P1 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-SCAFFOLDS-P1.md` |
| CHG-2026-04-15-F65-SECURITY-SMOKE | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-SECURITY-SMOKE.md` |
| CHG-2026-04-15-F65-SYSTEMIC-FALLBACK-LE | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-SYSTEMIC-FALLBACK-LE.md` |
| CHG-2026-04-15-F65-TZ-REGRESSION-6-5B-1 | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-TZ-REGRESSION-6-5B-1.md` |
| CHG-2026-04-15-F65-WEBSOCKET-INTEGRATIO | changelog-entry |  | F65 |  | `sprint/F65/changelog/CHG-2026-04-15-F65-WEBSOCKET-INTEGRATIO.md` |
| CHG-2026-04-15-F8 | changelog-entry |  | F8 |  | `sprint/F8/changelog/CHG-2026-04-15-F8.md` |
| CHG-2026-04-15-F8-BUG-FIXES-2026-04-14 | changelog-entry |  | F8 |  | `sprint/F8/changelog/CHG-2026-04-15-F8-BUG-FIXES-2026-04-14.md` |
| CHG-2026-04-15-F8-BUGS-OPERACIONAIS-CO | changelog-entry |  | F8 |  | `sprint/F8/changelog/CHG-2026-04-15-F8-BUGS-OPERACIONAIS-CO.md` |
| CHG-2026-04-15-F8-DOCUMENTA-O-REORGANI | changelog-entry |  | F8 |  | `sprint/F8/changelog/CHG-2026-04-15-F8-DOCUMENTA-O-REORGANI.md` |
| CHG-2026-04-15-F9 | changelog-entry |  | F9 |  | `sprint/F9/changelog/CHG-2026-04-15-F9.md` |
| CHG-2026-04-24-F9-0 | changelog-entry |  | F9 |  | `sprint/F9/changelog/CHG-2026-04-24-F9-0.md` |
| CHG-2026-04-25-A10-A6G-2B-T3-PIPELINE-S | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-A6G-2B-T3-PIPELINE-S.md` |
| CHG-2026-04-25-A10-A6G-3-R3-BACKEND-SWE | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-A6G-3-R3-BACKEND-SWE.md` |
| CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S.md` |
| CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-1.md` |
| CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-2.md` |
| CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-LIVESTEP-EMIT-S-3.md` |
| CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN.md` |
| CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN-1.md` |
| CHG-2026-04-25-F1-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-F1-1.md` |
| CHG-2026-04-25-F11-2C | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-25-F11-2C.md` |
| CHG-2026-04-25-F9-1 | changelog-entry |  | F9 |  | `sprint/F9/changelog/CHG-2026-04-25-F9-1.md` |
| CHG-2026-04-25-F9-2 | changelog-entry |  | F9 |  | `sprint/F9/changelog/CHG-2026-04-25-F9-2.md` |
| CHG-2026-04-25-F9-2-1 | changelog-entry |  | F9 |  | `sprint/F9/changelog/CHG-2026-04-25-F9-2-1.md` |
| CHG-2026-04-26-A10-CARD-CONSUMO-CONSCIE | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-26-A10-CARD-CONSUMO-CONSCIE.md` |
| CHG-2026-04-26-A10-REPORT-APPEARANCE-ME | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-26-A10-REPORT-APPEARANCE-ME.md` |
| CHG-2026-04-26-A10-REPORT-PREMIUM-UI-V2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-26-A10-REPORT-PREMIUM-UI-V2.md` |
| CHG-2026-04-26-A7-0 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-26-A7-0.md` |
| CHG-2026-04-26-A7-0-1 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-26-A7-0-1.md` |
| CHG-2026-04-26-F12-1E | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-26-F12-1E.md` |
| CHG-2026-04-27-A10-CI-FIX-VITEST-HANG-E | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-CI-FIX-VITEST-HANG-E.md` |
| CHG-2026-04-27-A10-E2E-CRITICAL-D-BITO | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-E2E-CRITICAL-D-BITO.md` |
| CHG-2026-04-27-A10-FIX-CHARTS-BARRAS-PR | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-FIX-CHARTS-BARRAS-PR.md` |
| CHG-2026-04-27-A10-FIX-CHARTS-S2-CORES | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-FIX-CHARTS-S2-CORES.md` |
| CHG-2026-04-27-A10-FIX-CHARTS-S2-EIXO-X | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-FIX-CHARTS-S2-EIXO-X.md` |
| CHG-2026-04-27-A10-REGRESS-O-VISUAL-FIX | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REGRESS-O-VISUAL-FIX.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-1.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-2.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-3.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-4 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-4.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-5 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-5.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-6 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-6.md` |
| CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-7 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-REPORT-PREMIUM-UI-V2-7.md` |
| CHG-2026-04-27-A10-SPEC-MOBILE-DO-RELAT | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-SPEC-MOBILE-DO-RELAT.md` |
| CHG-2026-04-27-A10-TEST-CHARTS-LINT-ANT | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-TEST-CHARTS-LINT-ANT.md` |
| CHG-2026-04-27-A10-V2-10-PDF-VISUAL-DIF | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A10-V2-10-PDF-VISUAL-DIF.md` |
| CHG-2026-04-27-A3-5 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A3-5.md` |
| CHG-2026-04-27-A7-0 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-0.md` |
| CHG-2026-04-27-A7-1 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-1.md` |
| CHG-2026-04-27-A7-2A | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-2A.md` |
| CHG-2026-04-27-A7-2B | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-2B.md` |
| CHG-2026-04-27-A7-3 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-3.md` |
| CHG-2026-04-27-A7-4 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-4.md` |
| CHG-2026-04-27-A7-6 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A7-6.md` |
| CHG-2026-04-27-A7-6-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A7-6-1.md` |
| CHG-2026-04-27-A7-6-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A7-6-2.md` |
| CHG-2026-04-27-A7-6-3 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-6-3.md` |
| CHG-2026-04-27-A7-6-4 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-27-A7-6-4.md` |
| CHG-2026-04-27-A7-6-5 | changelog-entry |  | A7 |  | `sprint/A7/changelog/CHG-2026-04-27-A7-6-5.md` |
| CHG-2026-04-27-A8-0 | changelog-entry |  | A8 |  | `sprint/A8/changelog/CHG-2026-04-27-A8-0.md` |
| CHG-2026-04-29-A10-DIRE-O-E-DASHBOARD-A | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-DASHBOARD-A.md` |
| CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-KANB | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-KANB.md` |
| CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-M2-S | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-ONDA-1-M2-S.md` |
| CHG-2026-04-29-A10-DIRE-O-E-ONDA-4-ONDA | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-ONDA-4-ONDA.md` |
| CHG-2026-04-29-A10-DIRE-O-E-ONDA-7-BLOQ | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-ONDA-7-BLOQ.md` |
| CHG-2026-04-29-A10-DIRE-O-E-P-S-REVIS-O | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-A10-DIRE-O-E-P-S-REVIS-O.md` |
| CHG-2026-04-29-FIX-SUGGESTIONS | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-29-FIX-SUGGESTIONS.md` |
| CHG-2026-04-30-A8-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-30-A8-2.md` |
| CHG-2026-04-30-FEAT-PIPELINE | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-30-FEAT-PIPELINE.md` |
| CHG-2026-04-30-FEAT-REPORT | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-04-30-FEAT-REPORT.md` |
| CHG-2026-05-04-A10-FEAT-SUGGESTIONS-DEC | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-04-A10-FEAT-SUGGESTIONS-DEC.md` |
| CHG-2026-05-04-FEAT-API | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-04-FEAT-API.md` |
| CHG-2026-05-05-A8-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-A8-3.md` |
| CHG-2026-05-05-F9-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-F9-3.md` |
| CHG-2026-05-05-FEAT-DB | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-FEAT-DB.md` |
| CHG-2026-05-05-FEAT-PIPELINE | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-FEAT-PIPELINE.md` |
| CHG-2026-05-05-PR46 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR46.md` |
| CHG-2026-05-05-PR47 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR47.md` |
| CHG-2026-05-05-PR48 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR48.md` |
| CHG-2026-05-05-PR49 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR49.md` |
| CHG-2026-05-05-PR50 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR50.md` |
| CHG-2026-05-05-PR51 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR51.md` |
| CHG-2026-05-05-PR56 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-05-PR56.md` |
| CHG-2026-05-06-A8-4 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-A8-4.md` |
| CHG-2026-05-06-A8-4-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-A8-4-1.md` |
| CHG-2026-05-06-A8-4-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-A8-4-2.md` |
| CHG-2026-05-06-A8-4-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-A8-4-3.md` |
| CHG-2026-05-06-A8-4-4 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-A8-4-4.md` |
| CHG-2026-05-06-DOCS-DECISIONS | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-06-DOCS-DECISIONS.md` |
| CHG-2026-05-06-FEAT-FRONTEND | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-06-FEAT-FRONTEND.md` |
| CHG-2026-05-06-FEAT-SCHEMAS | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-06-FEAT-SCHEMAS.md` |
| CHG-2026-05-06-FIX-BACKEND | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-FIX-BACKEND.md` |
| CHG-2026-05-06-FIX-DOCUMENTS | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-FIX-DOCUMENTS.md` |
| CHG-2026-05-06-FIX-PIPELINE | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-06-FIX-PIPELINE.md` |
| CHG-2026-05-06-FIX-PIPELINE-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-FIX-PIPELINE-1.md` |
| CHG-2026-05-06-PR77 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-PR77.md` |
| CHG-2026-05-06-PR87 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-06-PR87.md` |
| CHG-2026-05-07-A10-1 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-1.md` |
| CHG-2026-05-07-A10-2 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-2.md` |
| CHG-2026-05-07-A10-3 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-3.md` |
| CHG-2026-05-07-A10-4 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-4.md` |
| CHG-2026-05-07-A10-5 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-5.md` |
| CHG-2026-05-07-A10-6 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-6.md` |
| CHG-2026-05-07-A10-7 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-7.md` |
| CHG-2026-05-07-A10-8 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A10-8.md` |
| CHG-2026-05-07-A7-5 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-A7-5.md` |
| CHG-2026-05-07-ADR-177 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-ADR-177.md` |
| CHG-2026-05-07-ADR-178 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-ADR-178.md` |
| CHG-2026-05-07-ADR-179 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-ADR-179.md` |
| CHG-2026-05-07-ADR-180 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-ADR-180.md` |
| CHG-2026-05-07-ADR-181 | changelog-entry |  | A10 |  | `sprint/A10/changelog/CHG-2026-05-07-ADR-181.md` |
| CHG-2026-05-10-FEAT-CAT-LEARNING-LOOP-SCHEMA | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-10-FEAT-CAT-LEARNING-LOOP-SCHEMA.md` |
| CHG-2026-05-10-FEAT-REPORT-PUBLICATION | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-10-FEAT-REPORT-PUBLICATION.md` |
| CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-BACKEND | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-BACKEND.md` |
| CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-FRONTEND | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-FRONTEND.md` |
| CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-PIPELINE | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-11-FEAT-CAT-LEARNING-LOOP-PIPELINE.md` |
| CHG-2026-05-11-FEAT-FRONTEND-RENTABILIDADE | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-11-FEAT-FRONTEND-RENTABILIDADE.md` |
| CHG-2026-05-11-FEAT-PIPELINE-RENTABILIDADE | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-11-FEAT-PIPELINE-RENTABILIDADE.md` |
| CHG-2026-05-11-FEAT-REPORT | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-11-FEAT-REPORT.md` |
| CHG-2026-05-11-FEAT-REPORT-ALOCACAO | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-11-FEAT-REPORT-ALOCACAO.md` |
| CHG-2026-05-11-FEAT-S9-PROTECTION-AGGREGATE | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-11-FEAT-S9-PROTECTION-AGGREGATE.md` |
| CHG-2026-05-12-FEAT-AUVP-THRESHOLD-PGBL-VARIANT | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-12-FEAT-AUVP-THRESHOLD-PGBL-VARIANT.md` |
| CHG-2026-05-12-FEAT-IRPF-OTIMIZACAO-CARDS-REVIVAL | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-12-FEAT-IRPF-OTIMIZACAO-CARDS-REVIVAL.md` |
| CHG-2026-05-12-FEAT-IRPF-SIMPLIFICADO-COMPONENTES-PGD-MIR | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-12-FEAT-IRPF-SIMPLIFICADO-COMPONENTES-PGD-MIR.md` |
| CHG-2026-05-12-FEAT-PGBL-CARDS-RECONCILIATION | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-12-FEAT-PGBL-CARDS-RECONCILIATION.md` |
| CHG-2026-05-12-FEAT-REPORT-S9-EXPANSION | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-12-FEAT-REPORT-S9-EXPANSION.md` |
| CHG-2026-05-12-FEAT-S9-PROTECTION-CALCULATORS | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-12-FEAT-S9-PROTECTION-CALCULATORS.md` |
| CHG-2026-05-12-FIX-IRPF-DEDUTIVEIS-CHIP-REGIME | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-12-FIX-IRPF-DEDUTIVEIS-CHIP-REGIME.md` |
| CHG-2026-05-12-TEST-S9-GOLDENS-CLOSE-TRACK | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-12-TEST-S9-GOLDENS-CLOSE-TRACK.md` |
| CHG-2026-05-14-FEAT-PLANNER-ATO6-TELEMETRIA-CUTOVER | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-14-FEAT-PLANNER-ATO6-TELEMETRIA-CUTOVER.md` |
| CHG-2026-05-14-REFACTOR-REMOVE-REVIEW-FINANCES | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-14-REFACTOR-REMOVE-REVIEW-FINANCES.md` |
| CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-05-15-REFACTOR-DECISION-CODE-AUTOGEN.md` |
| CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO | changelog-entry |  | A15 |  | `sprint/A15/changelog/CHG-2026-05-20-A15-FU3-IMOVEL-FINANCIADO.md` |
| CHG-2026-05-20-FEAT-ADR-235-NU-PROPRIETARIO | changelog-entry |  | A16 |  | `sprint/A16/changelog/CHG-2026-05-20-FEAT-ADR-235-NU-PROPRIETARIO.md` |
| CHG-2026-05-20-FEAT-BACKEND-SECURITY-HEADERS | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-05-20-FEAT-BACKEND-SECURITY-HEADERS.md` |
| CHG-2026-05-21-A17-L1-PREVIDENCIA-SHIPPED | changelog-entry |  | A17 |  | `sprint/A17/changelog/CHG-2026-05-21-A17-L1-PREVIDENCIA-SHIPPED.md` |
| CHG-2026-05-21-DOCS-A17-L3-WISE-ADDED | changelog-entry |  | A17 |  | `sprint/A17/changelog/CHG-2026-05-21-DOCS-A17-L3-WISE-ADDED.md` |
| CHG-2026-05-21-DOCS-ADR-238-PROPOSTO | changelog-entry |  | A17 |  | `sprint/A17/changelog/CHG-2026-05-21-DOCS-ADR-238-PROPOSTO.md` |
| CHG-2026-05-21-DOCS-ADR-239-PROPOSTO | changelog-entry |  | A18 |  | `sprint/A18/changelog/CHG-2026-05-21-DOCS-ADR-239-PROPOSTO.md` |
| CHG-2026-05-21-DOCS-ADR-240-PROPOSTO | changelog-entry |  | A19 |  | `sprint/A19/changelog/CHG-2026-05-21-DOCS-ADR-240-PROPOSTO.md` |
| CHG-2026-05-21-FEAT-ADR-236-P1-BUSINESS-PROFILE | changelog-entry |  | A16 |  | `sprint/A16/changelog/CHG-2026-05-21-FEAT-ADR-236-P1-BUSINESS-PROFILE.md` |
| CHG-2026-05-21-FEAT-ADR-236-P2-CLASSIFIER-PJ-IRPF | changelog-entry |  | A16 |  | `sprint/A16/changelog/CHG-2026-05-21-FEAT-ADR-236-P2-CLASSIFIER-PJ-IRPF.md` |
| CHG-2026-05-21-FEAT-ADR-236-P6-CUTOVER-TELEMETRIA | changelog-entry |  | A16 |  | `sprint/A16/changelog/CHG-2026-05-21-FEAT-ADR-236-P6-CUTOVER-TELEMETRIA.md` |
| CHG-2026-05-22-A18-L1-CRLV-SHIPPED | changelog-entry |  | A18 |  | `sprint/A18/changelog/CHG-2026-05-22-A18-L1-CRLV-SHIPPED.md` |
| CHG-2026-05-22-A18-L2-APOLICE-SHIPPED | changelog-entry |  | A18 |  | `sprint/A18/changelog/CHG-2026-05-22-A18-L2-APOLICE-SHIPPED.md` |
| CHG-2026-05-22-A18-L3-FIPE-SHIPPED | changelog-entry |  | A18 |  | `sprint/A18/changelog/CHG-2026-05-22-A18-L3-FIPE-SHIPPED.md` |
| CHG-2026-05-22-A19-L1-PROTECAO-SHIPPED | changelog-entry |  | A19 |  | `sprint/A19/changelog/CHG-2026-05-22-A19-L1-PROTECAO-SHIPPED.md` |
| CHG-2026-05-28-ADR-271-INVEST-DEDUP-SHIPPED | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-28-ADR-271-INVEST-DEDUP-SHIPPED.md` |
| CHG-2026-05-29-A20-L1-BACKEND-MULTISTAGE | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L1-BACKEND-MULTISTAGE.md` |
| CHG-2026-05-29-A20-L2-SHA-PINNING | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L2-SHA-PINNING.md` |
| CHG-2026-05-29-A20-L3-PIPELINE-SERVICE-HARDENING | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L3-PIPELINE-SERVICE-HARDENING.md` |
| CHG-2026-05-29-A20-L6-COMPOSE-DEV | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L6-COMPOSE-DEV.md` |
| CHG-2026-05-29-A20-L7-MAKEFILE-ONBOARDING | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L7-MAKEFILE-ONBOARDING.md` |
| CHG-2026-05-29-A20-L8-POSTGRES-DRIVER | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-A20-L8-POSTGRES-DRIVER.md` |
| CHG-2026-05-29-ADR-238-DATA-ADESAO-NAO-HARDFAIL | changelog-entry |  | A20 |  | `sprint/A20/changelog/CHG-2026-05-29-ADR-238-DATA-ADESAO-NAO-HARDFAIL.md` |
| CHG-2026-05-30-A21-L7L8-LGPD | changelog-entry |  | A21 |  | `sprint/A21/changelog/CHG-2026-05-30-A21-L7L8-LGPD.md` |
| CHG-2026-06-03-A23-L1 | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-03-A23-L1.md` |
| CHG-2026-06-08-A23-L2 | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-08-A23-L2.md` |
| CHG-2026-06-08-A23-L3 | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-08-A23-L3.md` |
| CHG-2026-06-09-A23-L4-OVERRIDE-NATURAL-KEY-V2 | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-09-A23-L4-OVERRIDE-NATURAL-KEY-V2.md` |
| CHG-2026-06-09-A23-L5-DATA-SOURCE | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-09-A23-L5-DATA-SOURCE.md` |
| CHG-2026-06-09-A23-L6-AMOUNT-DECIMAL | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-09-A23-L6-AMOUNT-DECIMAL.md` |
| CHG-2026-06-09-A23-L7-EXTRACT-CHECK | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-09-A23-L7-EXTRACT-CHECK.md` |
| CHG-2026-06-09-A23-L8-MIGRATION-RUNBOOK | changelog-entry |  | A23 |  | `sprint/A23/changelog/CHG-2026-06-09-A23-L8-MIGRATION-RUNBOOK.md` |
| CHG-2026-06-09-A24-L2-DELEAK-ACCOUNT-NORM | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-09-A24-L2-DELEAK-ACCOUNT-NORM.md` |
| CHG-2026-06-09-A24-L3-DELEAK-TIPO-LANCAMENTO | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-09-A24-L3-DELEAK-TIPO-LANCAMENTO.md` |
| CHG-2026-06-09-BACKEND-CAT-LEGACY-SUNSET | changelog-entry |  | A12 |  | `sprint/A12/changelog/CHG-2026-06-09-BACKEND-CAT-LEGACY-SUNSET.md` |
| CHG-2026-06-09-FEAT-AUTH-REFRESH-TOKENS | changelog-entry |  | A11 |  | `sprint/A11/changelog/CHG-2026-06-09-FEAT-AUTH-REFRESH-TOKENS.md` |
| CHG-2026-06-10-A24-L1-F2-DISCOVERY | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-10-A24-L1-F2-DISCOVERY.md` |
| CHG-2026-06-10-A24-L4-EVIDENCIA-PATH | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-10-A24-L4-EVIDENCIA-PATH.md` |
| CHG-2026-06-10-A24-L5-SKELETON-PATRIMONIO | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-10-A24-L5-SKELETON-PATRIMONIO.md` |
| CHG-2026-06-10-A24-L6-SKELETON-RESTO | changelog-entry |  | A24 |  | `sprint/A24/changelog/CHG-2026-06-10-A24-L6-SKELETON-RESTO.md` |
| CHG-2026-06-10-A25-L3-F5-LINEAGE-REVERSO | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-10-A25-L3-F5-LINEAGE-REVERSO.md` |
| CHG-2026-06-10-A25-L4-F7-DEBUG-LLM | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-10-A25-L4-F7-DEBUG-LLM.md` |
| CHG-2026-06-11-A25-L1-CUTOVER-OVERRIDE-V2 | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-11-A25-L1-CUTOVER-OVERRIDE-V2.md` |
| CHG-2026-06-12-REMOVE-HISTORICO-CICLOS | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-12-REMOVE-HISTORICO-CICLOS.md` |
| CHG-2026-06-12-SUGGESTION-LIFECYCLE-F1-F4 | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-12-SUGGESTION-LIFECYCLE-F1-F4.md` |
| CHG-2026-06-15-A25-L5-F6-PRODUTO-N1N2 | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-15-A25-L5-F6-PRODUTO-N1N2.md` |
| CHG-2026-06-16-A25-L2-DEDUP-E4-FLIP-V2 | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-16-A25-L2-DEDUP-E4-FLIP-V2.md` |
| CHG-2026-06-16-A25-L6-KR2-RESTO | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-16-A25-L6-KR2-RESTO.md` |
| CHG-2026-06-16-A25-L7-EVIDENCIA-STRICT-DECISION | changelog-entry |  | A25 |  | `sprint/A25/changelog/CHG-2026-06-16-A25-L7-EVIDENCIA-STRICT-DECISION.md` |
| CHG-2026-06-18-A26-L1-EVIDENCIA-CATALOGO | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-06-18-A26-L1-EVIDENCIA-CATALOGO.md` |
| CHG-2026-06-18-A26-L6-EVIDENCIA-COVERAGE-KPI | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-06-18-A26-L6-EVIDENCIA-COVERAGE-KPI.md` |
| CHG-2026-06-18-A26-L8-EVIDENCIA-VALUE-MISMATCH | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-06-18-A26-L8-EVIDENCIA-VALUE-MISMATCH.md` |
| CHG-2026-06-19-A26-L7-EVIDENCIA-CATALOG-LISTAS | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-06-19-A26-L7-EVIDENCIA-CATALOG-LISTAS.md` |
| CHG-2026-06-21-A26-L9-CITACAO-DETERMINISTICA | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-06-21-A26-L9-CITACAO-DETERMINISTICA.md` |
| CHG-2026-06-29-A22-L2-RED-LINES | changelog-entry |  | A22 |  | `sprint/A22/changelog/CHG-2026-06-29-A22-L2-RED-LINES.md` |
| CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP | changelog-entry |  | A22 |  | `sprint/A22/changelog/CHG-2026-06-29-A22-L5-DIVIDAS-DEDUP.md` |
| CHG-2026-07-01-A22-L2-RED-LINES-CALIBRATION | changelog-entry |  | A22 |  | `sprint/A22/changelog/CHG-2026-07-01-A22-L2-RED-LINES-CALIBRATION.md` |
| CHG-2026-07-01-A26-L3-DROP-DEDUP-V1-SHIM | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-07-01-A26-L3-DROP-DEDUP-V1-SHIM.md` |
| CHG-2026-07-01-A26-L4-INSTRUMENTACAO-DUALREAD | changelog-entry |  | A26 |  | `sprint/A26/changelog/CHG-2026-07-01-A26-L4-INSTRUMENTACAO-DUALREAD.md` |
| CHG-2026-07-02-A27-L1-EVIDENCIA-LINEAGE-EDGE | changelog-entry |  | A27 |  | `sprint/A27/changelog/CHG-2026-07-02-A27-L1-EVIDENCIA-LINEAGE-EDGE.md` |
| FAQ-bank-account-member | doc |  |  | FAQ — Como o Mathoms decide de qual membro é cada conta | `reference/FAQ_bank_account_member.md` |
| FAQ-cascata-fiscal-pj | doc |  |  | FAQ — Como o Mathoms calcula a cascata fiscal PJ e a base PGBL | `reference/FAQ_cascata_fiscal_pj.md` |
| RULE-alocacao-alvo-7-classes | domain-rule |  |  |  | `reference/rules/rule-alocacao-alvo-7-classes.md` |
| RULE-cenario-conjuge-estresse | domain-rule |  |  |  | `reference/rules/rule-cenario-conjuge-estresse.md` |
| RULE-compliance-risk-us-person | domain-rule |  |  |  | `reference/rules/compliance-risk-us-person.md` |
| RULE-composicao-patrimonial-7-categorias | domain-rule |  |  |  | `reference/rules/rule-composicao-patrimonial-7-categorias.md` |
| RULE-concentracao-imobiliaria | domain-rule |  |  |  | `reference/rules/rule-concentracao-imobiliaria.md` |
| RULE-disability-coverage-gap | domain-rule |  |  |  | `reference/rules/disability-coverage-gap.md` |
| RULE-imoveis-no-if | domain-rule |  |  |  | `reference/rules/rule-imoveis-no-if.md` |
| RULE-independencia-financeira | domain-rule |  |  |  | `reference/rules/rule-independencia-financeira.md` |
| RULE-itcmd-estimated | domain-rule |  |  |  | `reference/rules/itcmd-estimated.md` |
| RULE-life-insurance-coverage | domain-rule |  |  |  | `reference/rules/life-insurance-coverage.md` |
| RULE-trs-efetiva | domain-rule |  |  |  | `reference/rules/rule-trs-efetiva.md` |
| A10.0 | lane | shipped | A10 | ADRs Proposto batch (ADR-177..181) | `sprint/A10/lanes/A10-0-adrs-proposto-batch.md` |
| A10.1 | lane | shipped | A10 | Dead-data deletion + ADR-168 narrativas órfãs | `sprint/A10/lanes/A10-1-dead-data-deletion-adr-168-narrativas-orfas.md` |
| A10.2 | lane | shipped | A10 | Rules-as-code consolidation (ADR-177) | `sprint/A10/lanes/A10-2-rules-as-code-consolidation.md` |
| A10.3 | lane | shipped | A10 | Decision schema extension (ADR-179) | `sprint/A10/lanes/A10-3-decision-schema-extension.md` |
| A10.4 | lane | shipped | A10 | `Risk` aggregate (ADR-178) | `sprint/A10/lanes/A10-4-risk-aggregate.md` |
| A10.5 | lane | shipped | A10 | Top5 + Bubble como projeção (charts_narrator switch) | `sprint/A10/lanes/A10-5-top5-bubble-como-projecao.md` |
| A10.6 | lane | shipped | A10 | Pipeline cutover via `StageConfig.config_store` (ADR-180) | `sprint/A10/lanes/A10-6-pipeline-cutover-via-stageconfig-config-store.md` |
| A10.7 | lane | shipped | A10 | Seed refactor + `tributario` migration | `sprint/A10/lanes/A10-7-seed-refactor-tributario-migration.md` |
| A10.8 | lane | shipped | A10 | Final cutover + `forbidden_paths` (ADR-181) | `sprint/A10/lanes/A10-8-final-cutover-forbidden-paths.md` |
| A11.report-publication | lane | shipped | A11 | Report publication — mês fechado imutável | `sprint/A11/lanes/A11-report-publication-month-closed.md` |
| A11.w1 | lane | shipped | A11 | Hot patches + ADR backfill (8 tasks) | `sprint/A11/lanes/A11-w1-hot-patches-adr-backfill.md` |
| A11.w2 | lane | shipped | A11 | Pipeline + DB hardening (6 tasks) | `sprint/A11/lanes/A11-w2-pipeline-db-hardening.md` |
| A11.w3 | lane | open | A11 | Auth + LLM ops + Email (5 tasks) | `sprint/A11/lanes/A11-w3-auth-llm-ops-email.md` |
| A11.w4 | lane | blocked | A11 | Production readiness (5 tasks) | `sprint/A11/lanes/A11-w4-production-readiness.md` |
| A11.w5 | lane | open | A11 | Frontend + Methodology (5 tasks, paralelo W6) | `sprint/A11/lanes/A11-w5-frontend-methodology.md` |
| A11.w6 | lane | blocked | A11 | Tech debt cleanup (6 tasks) | `sprint/A11/lanes/A11-w6-tech-debt-cleanup.md` |
| A12.alocacao-v2 | lane | open | A12 | Alocação-alvo schema v1→v2 (7 classes AUVP, desvio backend-driven) | `sprint/A12/lanes/A12-alocacao-v2-migration.md` |
| A12.bank-account-disambig | lane | shipped | A12 | Desambiguação conta bancária → membro (multi-membro mesmo banco) | `sprint/A12/lanes/A12-bank-account-disambig-multi-member.md` |
| A12.cat-learning-loop | lane | in_progress | A12 | Categorization Learning Loop — promoção de override em regra | `sprint/A12/lanes/A12-cat-learning-loop-override-to-rule.md` |
| A12.decision-code-autogen | lane | in_progress | A12 | Decision.code server-generated (UX cleanup + race fix) | `sprint/A12/lanes/A12-decision-code-autogen-server-gen.md` |
| A12.irpf-prefill-bank-accounts | lane | planned | A12 | Pre-fill UI a partir de IRPF — V1 contas bancárias (deferred → A13) | `sprint/A12/lanes/A12-irpf-prefill-bank-accounts-deferred-a13.md` |
| A12.sunset-disk-artifact | lane | open | A12 | Sunset DiskArtifactStore + flag MATHOMS_USE_DB_ARTIFACTS + CLI standalone | `sprint/A12/lanes/A12-sunset-disk-artifact-cleanup.md` |
| A17.l1 | lane | shipped | A17 | Informes anuais — L1 previdência privada (PGBL/VGBL, BrasilPrev e seguradoras) | `sprint/A17/lanes/A17-l1-previdencia.md` |
| A17.l2 | lane | shipped | A17 | Informes anuais — L2 financeiro PJ (C6 PJ, Stone, adquirentes) | `sprint/A17/lanes/A17-l2-financeiro-pj.md` |
| A17.l3 | lane | in_progress | A17 | Informes anuais — L3 financeiro PF (6 bancos + XP Investimentos + Wise multi-moeda) | `sprint/A17/lanes/A17-l3-financeiro-pf.md` |
| A17.l4 | lane | in_progress | A17 | Informes anuais — L4 proventos ações (XP Proventos, Itaúsa) | `sprint/A17/lanes/A17-l4-proventos.md` |
| A17.l5 | lane | shipped | A17 | LLM Hardening — W4-T00 seed expandido institution_catalog (alta renda PJ) | `sprint/A17/lanes/A17-l5-llm-institution-seed.md` |
| A17.l6 | lane | shipped | A17 | Bugfix — RECEBIMENTO DE TED engole salário CLT (categorização) | `sprint/A17/lanes/A17-l6-bugfix-ted-receita-clt.md` |
| A18.l1 | lane | shipped | A18 | Comprovantes de Bem — L1 CRLV-e (Certificado de Registro e Licenciamento de Veículo) | `sprint/A18/lanes/A18-l1-crlv.md` |
| A18.l2 | lane | shipped | A18 | Comprovantes de Bem — L2 Apólice de seguro polimórfica (combinada V1, vida/saúde/PJ V2) | `sprint/A18/lanes/A18-l2-apolice.md` |
| A18.l3 | lane | shipped | A18 | Comprovantes de Bem — L3 FIPE refresh assíncrono via BrasilAPI | `sprint/A18/lanes/A18-l3-fipe.md` |
| A19.l1 | lane | shipped | A19 | S_PROTECAO — L1 Card 4º pilar AUVP no relatório (KPIs + 3 subgrupos + reposicionamento) | `sprint/A19/lanes/A19-l1-card-protecao.md` |
| A20.l1 | lane | shipped | A20 | Docker dev↔prod parity — L1 Multi-stage backend + Playwright dual target | `sprint/A20/lanes/A20-l1-backend-multistage.md` |
| A20.l10 | lane | shipped | A20 | Docker dev↔prod parity — L10 Python lockfile com hashes (pip-tools vs uv) | `sprint/A20/lanes/A20-l10-python-lockfile.md` |
| A20.l11 | lane | planned | A20 | LLM Hardening — W1β ADR-090 cadeia e15_baseline (float → Decimal) | `sprint/A20/lanes/A20-l11-llm-w1-beta-adr090.md` |
| A20.l12 | lane | planned | A20 | LLM Hardening — W2 semver puro + goldens fiscais BR + LLMCallLog SQL | `sprint/A20/lanes/A20-l12-llm-w2-versioning-goldens.md` |
| A20.l13 | lane | planned | A20 | LLM Hardening — W3 telemetria OTLP mathoms.llm.* por prompt_version | `sprint/A20/lanes/A20-l13-llm-w3-telemetry.md` |
| A20.l14 | lane | planned | A20 | LLM Hardening — W4 cross-cutting (InstitutionCatalogProvider + RFB YAML) | `sprint/A20/lanes/A20-l14-llm-w4-cross-cutting.md` |
| A20.l15 | lane | planned | A20 | LLM Hardening — W1α LGPD compliance (gate F7 R4 → Beta fechado) | `sprint/A20/lanes/A20-l15-llm-w1-alpha-lgpd.md` |
| A20.l2 | lane | shipped | A20 | Docker dev↔prod parity — L2 SHA pinning de bases + Dependabot Docker | `sprint/A20/lanes/A20-l2-sha-pinning.md` |
| A20.l3 | lane | shipped | A20 | Docker dev↔prod parity — L3 pipeline-service non-root + healthcheck por service | `sprint/A20/lanes/A20-l3-pipeline-service.md` |
| A20.l4 | lane | open | A20 | Docker dev↔prod parity — L4 GHCR push em CI + tagging strategy | `sprint/A20/lanes/A20-l4-ghcr-push.md` |
| A20.l5 | lane | open | A20 | Docker dev↔prod parity — L5 Trivy image scan blocking + SBOM CycloneDX | `sprint/A20/lanes/A20-l5-trivy-sbom.md` |
| A20.l6 | lane | shipped | A20 | Docker dev↔prod parity — L6 docker-compose.dev.yml unificado + cleanup composes legados | `sprint/A20/lanes/A20-l6-compose-dev.md` |
| A20.l7 | lane | shipped | A20 | Docker dev↔prod parity — L7 Makefile targets + SETUP.md revisado | `sprint/A20/lanes/A20-l7-makefile.md` |
| A20.l8 | lane | shipped | A20 | Docker dev↔prod parity — L8 Postgres driver (psycopg2 → psycopg v3 swap) | `sprint/A20/lanes/A20-l8-postgres-driver.md` |
| A20.l9 | lane | blocked | A20 | Docker dev↔prod parity — L9 Smoke E2E em compose (login + relatório + PDF) | `sprint/A20/lanes/A20-l9-smoke-e2e.md` |
| A21.l1 | lane | shipped | A21 | Suíte de invariantes de consolidação INV-1..9 (E1.5c) | `sprint/A21/lanes/A21-l1-consolidation-invariants.md` |
| A21.l2 | lane | shipped | A21 | Golden multi-ano anotado + métrica fn_rate/fp_rate | `sprint/A21/lanes/A21-l2-dedup-golden-metrics.md` |
| A21.l3 | lane | shipped | A21 | Contrato EntityDedup (Protocol + runner compartilhado) | `sprint/A21/lanes/A21-l3-entity-dedup-contract.md` |
| A21.l4 | lane | shipped | A21 | Dedup previdência PGBL/VGBL (ativo × dedução fiscal, cross-axis) | `sprint/A21/lanes/A21-l4-previdencia-dedup.md` |
| A21.l5 | lane | shipped | A21 | Decidir ADR-175 (defesa de injeção LLM em camadas) Proposto→Decidido | `sprint/A21/lanes/A21-l5-adr175-decide.md` |
| A21.l6 | lane | shipped | A21 | W3-T05 — defesa de injeção LLM (4 camadas + adversarial fixtures + telemetria) | `sprint/A21/lanes/A21-l6-prompt-injection-defense.md` |
| A21.l7 | lane | shipped | A21 | LGPD Art.37 — audit log de acesso a dado sensível | `sprint/A21/lanes/A21-l7-lgpd-audit-log.md` |
| A21.l8 | lane | shipped | A21 | LGPD Art.18 — export/deleção (data-subject rights) | `sprint/A21/lanes/A21-l8-lgpd-data-subject-rights.md` |
| A21.l9 | lane | shipped | A21 | Backup/restore mechanism + drill CI-local (subset W4-T01) | `sprint/A21/lanes/A21-l9-backup-restore-drill-ci.md` |
| A22.l1 | lane | shipped | A22 | 24 golden fixtures do Parecer + métrica de eval em CI | `sprint/A22/lanes/A22-l1-parecer-golden-eval.md` |
| A22.l2 | lane | shipped | A22 | Validação em 3 camadas (schema → invariante → 7 red lines hard-block) | `sprint/A22/lanes/A22-l2-validacao-3-camadas-red-lines.md` |
| A22.l3 | lane | shipped | A22 | Fallback needs_review atômico (LLM down → relatório não quebra) | `sprint/A22/lanes/A22-l3-fallback-needs-review-atomico.md` |
| A22.l4 | lane | planned | A22 | Drift detection (3 sinais) + pin de model-snapshot | `sprint/A22/lanes/A22-l4-drift-detection-model-pin.md` |
| A22.l5 | lane | shipped | A22 | Dedup de dívida cross-year (max(ano) + warning) + schema formal de dividas | `sprint/A22/lanes/A22-l5-dedup-divida-cross-year.md` |
| A23.l1 | lane | shipped | A23 | Data Lineage F0 — fechar 4 ADR Proposto + emenda ADR-146 (B1–B8) | `sprint/A23/lanes/A23-l1-data-lineage-f0-adr-gate.md` |
| A23.l2 | lane | shipped | A23 | Data Lineage F1 — substrato de golden (diff tool + view-model snapshot + invariantes) | `sprint/A23/lanes/A23-l2-golden-substrate.md` |
| A23.l3 | lane | shipped | A23 | Data Lineage F1 — K4 natural_key como campo de contrato E2 (B3/B4) | `sprint/A23/lanes/A23-l3-natural-key.md` |
| A23.l4 | lane | shipped | A23 | Data Lineage F1 — alinhar 3º hash (override) ao K4 v2 (D6) | `sprint/A23/lanes/A23-l4-override-hash-k4-parity.md` |
| A23.l5 | lane | shipped | A23 | Data Lineage F1 — fonte plugável (data_source + SourceRef) | `sprint/A23/lanes/A23-l5-data-source.md` |
| A23.l6 | lane | shipped | A23 | Data Lineage F1 — amount decimal ao lado de valor (B5) | `sprint/A23/lanes/A23-l6-amount-decimal.md` |
| A23.l7 | lane | shipped | A23 | Data Lineage F1 — gate de pureza de extração (ADR-280) | `sprint/A23/lanes/A23-l7-extract-check.md` |
| A23.l8 | lane | shipped | A23 | Data Lineage F1 — runbook de migrations + FK DB (G-e) | `sprint/A23/lanes/A23-l8-migration-runbook.md` |
| A24.l1 | lane | shipped | A24 | Data Lineage F2 — discovery do de-leak + substrato de rebaseline endurecido | `sprint/A24/lanes/A24-l1-f2-discovery.md` |
| A24.l2 | lane | shipped | A24 | Data Lineage F2 — de-leak numero_conta_norm (extração emite raw) | `sprint/A24/lanes/A24-l2-deleak-account-norm.md` |
| A24.l3 | lane | shipped | A24 | Data Lineage F2 — de-leak tipo_lancamento (delete do output + contrato) | `sprint/A24/lanes/A24-l3-deleak-tipo-lancamento.md` |
| A24.l4 | lane | shipped | A24 | Data Lineage F4 — evidencia_path: citação verificada E5→E6 no parecer | `sprint/A24/lanes/A24-l4-evidencia-path.md` |
| A24.l5 | lane | shipped | A24 | Data Lineage F3 — walking skeleton: _lineage no patrimônio líquido | `sprint/A24/lanes/A24-l5-skeleton-patrimonio.md` |
| A24.l6 | lane | shipped | A24 | Data Lineage F3 — skeleton resto: reserva, despesa, total investido | `sprint/A24/lanes/A24-l6-skeleton-resto.md` |
| A24.l7 | lane | open | A24 | Schema strict flip — baseline → de-drift de vocabulário → flip E2 (ADR-284) | `sprint/A24/lanes/A24-l7-schema-strict-flip.md` |
| A25.l1 | lane | shipped | A25 | Override v2 — cutover de leitura (A23.l4 slice 4) + gate M2 | `sprint/A25/lanes/A25-l1-a23l4-cutover-override.md` |
| A25.l2 | lane | shipped | A25 | Flip do consumo E4 para identidade v2 (passo 2 da B4) | `sprint/A25/lanes/A25-l2-dedup-e4-flip-v2.md` |
| A25.l3 | lane | shipped | A25 | Data Lineage F5 — edge table artifact_lineage_edge + query reversa | `sprint/A25/lanes/A25-l3-dl-f5-reverso.md` |
| A25.l4 | lane | shipped | A25 | Data Lineage F7 — debug substrate LLM: renderer, lineage_diff, tools, eval | `sprint/A25/lanes/A25-l4-dl-f7-debug-llm.md` |
| A25.l5 | lane | shipped | A25 | Data Lineage F6 — produto N1/N2: selo + popover 'Como chegamos a esse número' | `sprint/A25/lanes/A25-l5-dl-f6-produto-n1n2.md` |
| A25.l6 | lane | shipped | A25 | KR2 6/6 — fluxo_liquido + endividamento.total_dividas + member_hashes reais | `sprint/A25/lanes/A25-l6-kr2-resto.md` |
| A25.l7 | lane | shipped | A25 | Decisão do flip warn→strict do evidencia_path (requisito de done da A25) | `sprint/A25/lanes/A25-l7-evidencia-strict-decision.md` |
| A26.l1 | lane | shipped | A26 | Fix de citação do evidencia_path — catálogo de paths disponíveis + eval golden LLM | `sprint/A26/lanes/A26-l1-evidencia-prompt-catalogo.md` |
| A26.l10 | lane | shipped | A26 | LGPD export — cobertura total das tabelas com dados pessoais (Art.18) | `sprint/A26/lanes/A26-l10-lgpd-export-cobertura.md` |
| A26.l2 | lane | blocked | A26 | Flip evidencia_path warn→strict (gate de segurança binário + budget de needs_review) | `sprint/A26/lanes/A26-l2-evidencia-flip-strict.md` |
| A26.l3 | lane | shipped | A26 | M2-A — drop do shim v1 do dedup (compute_transaction_hash) | `sprint/A26/lanes/A26-l3-drop-dedup-v1-shim.md` |
| A26.l4 | lane | in_progress | A26 | Override v2 ON no default + instrumentação do gate (v2_match_count + query agendada) | `sprint/A26/lanes/A26-l4-override-v2-on-instrumentacao.md` |
| A26.l5 | lane | blocked | A26 | M2-B — drop destrutivo do estado legado de identidade do override (Fase E) | `sprint/A26/lanes/A26-l5-m2-override-drop.md` |
| A26.l6 | lane | shipped | A26 | Telemetria de citação: cobertura (missing_path) vs. correção (value_mismatch) + drift | `sprint/A26/lanes/A26-l6-evidencia-coverage-kpi.md` |
| A26.l7 | lane | shipped | A26 | Catálogo de citação cobre folhas de LISTA (fonte única forward↔reverse) | `sprint/A26/lanes/A26-l7-evidencia-catalog-listas.md` |
| A26.l8 | lane | shipped | A26 | value_mismatch residual: enforcement per-item no strict (path válido, número errado) | `sprint/A26/lanes/A26-l8-evidencia-value-mismatch.md` |
| A26.l9 | lane | shipped | A26 | citação determinística: renderizar valor R$ da folha (path) — value_mismatch → 0 estrutural | `sprint/A26/lanes/A26-l9-citacao-deterministica.md` |
| A27.l1 | lane | shipped | A27 | Citação do parecer (E6→E5) como edge de lineage por chave natural | `sprint/A27/lanes/A27-l1-evidencia-lineage-edge.md` |
| A28.l1 | lane | in_progress | A28 | reserva de emergência conforme FORMULAS.md: custo essencial + liquidez estrita + meses_alvo por perfil | `sprint/A28/lanes/A28-l1-reserva-formula-canonica.md` |
| A28.l10 | lane | shipped | A28 | âncoras do parecer formatadas por tipo (não tudo é R$) + curadoria defensiva de pontos fortes/alertas | `sprint/A28/lanes/A28-l10-ancoras-formatter-curadoria.md` |
| A28.l11 | lane | planned | A28 | guardrails pós-LLM do parecer: confiança rebaixada sob premissa fallback + filtro 3-vias de campos_faltantes | `sprint/A28/lanes/A28-l11-parecer-guardrails-pos-llm.md` |
| A28.l2 | lane | shipped | A28 | TRS efetiva com numerador/denominador do mesmo universo + guardrail de sanidade (ADR-191) | `sprint/A28/lanes/A28-l2-trs-universo-consistente.md` |
| A28.l3 | lane | shipped | A28 | PGBL: regra de ano-base único — uma recomendação por relatório | `sprint/A28/lanes/A28-l3-pgbl-ano-base-unico.md` |
| A28.l4 | lane | shipped | A28 | base de mensalização única: política de janela temporal por família de métrica + Cerbasi coerente | `sprint/A28/lanes/A28-l4-mensalizacao-base-unica.md` |
| A28.l5 | lane | open | A28 | nao_identificado 23% → <5%: regras via Learning Loop + gate de reclassificação do owner | `sprint/A28/lanes/A28-l5-nao-identificado-learning-loop.md` |
| A28.l6 | lane | open | A28 | proteção patrimonial ativada: apólices extraídas fluem para compute_protecao + pontos_urgentes condicional | `sprint/A28/lanes/A28-l6-protecao-apolices-flow.md` |
| A28.l7 | lane | open | A28 | imóveis excluídos: dedup tático na projeção + gate de rotulagem do owner | `sprint/A28/lanes/A28-l7-imoveis-excluidos-dedup.md` |
| A28.l8 | lane | open | A28 | higiene de ingestão: períodos implausíveis (1899/2100) e banco vazio viram needs_review, não artefato silencioso | `sprint/A28/lanes/A28-l8-higiene-ingestao-periodos.md` |
| A28.l9 | lane | planned | A28 | banner agregado de qualidade de dados no relatório + ressalva de fallback no Monte Carlo | `sprint/A28/lanes/A28-l9-report-data-quality-banner.md` |
| A5f | lane | shipped | A6 | E1.5c Caminho B | `sprint/A6/lanes/A5f-e1-5c-caminho-b.md` |
| A6-human | lane | shipped | A6 | Teste manual end-to-end (David) | `sprint/A6/lanes/A6-human-teste-manual-end-to-end.md` |
| A6-readers.dbfirst | lane | shipped | A6 | Readers DB-first com fallback disco | `sprint/A6/lanes/A6-readers-dbfirst-readers-db-first-com-fallback-disco.md` |
| A6-ux.livestep | lane | shipped | A6 | Contrato `LiveStep` | `sprint/A6/lanes/A6-ux-livestep-contrato-livestep.md` |
| A6a | lane | shipped | A6 | LLM stages escrevendo via `ArtifactStore` | `sprint/A6/lanes/A6a-llm-stages-escrevendo-via-artifactstore.md` |
| A6b | lane | shipped | A6 | Ativar `USE_DB_ARTIFACTS=true` + validar end-to-end | `sprint/A6/lanes/A6b-ativar-use-db-artifacts-true-validar-end.md` |
| A6b.5 | lane | shipped | A6 | Preparação para teste humano (ADR-103) | `sprint/A6/lanes/A6b-5-preparacao-para-teste-humano.md` |
| A6b.flip | lane | shipped | A6 | Flip do default global | `sprint/A6/lanes/A6b-flip-flip-do-default-global.md` |
| A6c | lane | shipped | A6 | Deletar bridge + legados | `sprint/A6/lanes/A6c-deletar-bridge-legados.md` |
| A6d | lane | shipped | A6 | Fechar Caminho B puro nos 5 stages pragmáticos (ADR-100) | `sprint/A6/lanes/A6d-fechar-caminho-b-puro-nos-5-stages.md` |
| A6e | lane | in_progress | A6 | DDD/SOLID no backend API (ADR-101, R12-R17) | `sprint/A6/lanes/A6e-ddd-solid-no-backend-api.md` |
| A6f | lane | shipped | A6 | Language-neutral boundaries (ADR-102, R18-R20) | `sprint/A6/lanes/A6f-language-neutral-boundaries.md` |
| A6g | lane | in_progress | A6 | Code Style Sweep (CLAUDE.md §Code style) | `sprint/A6/lanes/A6g-code-style-sweep.md` |
| A7.0 | lane | shipped | A7 | ConfigStore protocol + adapters | `sprint/A7/lanes/A7-0-configstore-protocol-adapters.md` |
| A7.1 | lane | shipped | A7 | Cutover `materialize_config` → ConfigStore | `sprint/A7/lanes/A7-1-cutover-materialize-config-configstore.md` |
| A7.2a | lane | shipped | A7 | Decision aggregate (event-sourced) + migrator + UI Plano de Ação | `sprint/A7/lanes/A7-2a-decision-aggregate-migrator-ui-plano-de-acao.md` |
| A7.2b | lane | shipped | A7 | Tabelas globais `fiscal_parameters` + `market_rates` versionadas | `sprint/A7/lanes/A7-2b-tabelas-globais-fiscal-parameters-market-rates-versionadas.md` |
| A7.3 | lane | shipped | A7 | Catalog + Override resolver (categorization + institutions) | `sprint/A7/lanes/A7-3-catalog-override-resolver.md` |
| A7.4 | lane | shipped | A7 | Metodologia → `docs/methodology/` (4 `.md` movidos) | `sprint/A7/lanes/A7-4-metodologia-docs-methodology.md` |
| A7.5 | lane | shipped | A7 | Cleanup final (deletar `config/` + bridges) | `sprint/A7/lanes/A7-5-cleanup-final.md` |
| A7.6 | lane | shipped | A7 | Rules-as-code (dissolver `docs/methodology/`) | `sprint/A7/lanes/A7-6-rules-as-code.md` |
| A8.0 | lane | shipped | A8 | Follow-ups A7 (3 itens herdados de CTO G4 sign-off) | `sprint/A8/lanes/A8-0-follow-ups-a7.md` |
| A8.1 | lane | planned | A8 | MileageProgram aggregate (DB + API + UI) | `sprint/A8/lanes/A8-1-mileageprogram-aggregate.md` |
| A8.2 | lane | shipped | A8 | IRPF full schema (E1.6 — pipeline + analyzer + E5 wire) | `sprint/A8/lanes/A8-2-irpf-full-schema.md` |
| A8.3 | lane | shipped | A8 | TRS real — Carteira de renda + Taxa de Retirada Sustentável efetiva (S7) | `sprint/A8/lanes/A8-3-trs-real-carteira-de-renda-taxa-de.md` |
| A8.4 | lane | shipped | A8 | Cenários de Estresse — remoção de prototipagem família-específica + APP_C universal | `sprint/A8/lanes/A8-4-cenarios-de-estresse-remocao-de-prototipagem-familia.md` |
| A9.0.6-p2-p3 | lane | shipped | A9 | LGPD self-service + tenancy gate | `sprint/A9/lanes/A9-0-6-p2-p3-lgpd-self-service-tenancy-gate.md` |
| A9.a1 | lane | shipped | A9 | feat Alembic stage rename migration | `sprint/A9/lanes/A9-a1-feat-alembic-stage-rename-migration.md` |
| A9.a2 | lane | shipped | A9 | refactor `content_classifier` | `sprint/A9/lanes/A9-a2-refactor-content-classifier.md` |
| A9.b1 | lane | shipped | A9 | fix canonical stage names em artifact_reader | `sprint/A9/lanes/A9-b1-fix-canonical-stage-names-em-artifact-reader.md` |
| A9.b3 | lane | shipped | A9 | fix stale selectors E2E vault + config-round-trip | `sprint/A9/lanes/A9-b3-fix-stale-selectors-e2e-vault-config-round.md` |
| A9.b5 | lane | shipped | A9 | deprecate `calculators.py` | `sprint/A9/lanes/A9-b5-deprecate-calculators-py.md` |
| A9.b6 | lane | shipped | A9 | feat `FreeTierSkippedBanner` | `sprint/A9/lanes/A9-b6-feat-freetierskippedbanner.md` |
| A9.b7 | lane | shipped | A9 | feat DB M3 drop legacy tables (ADR-154) | `sprint/A9/lanes/A9-b7-feat-db-m3-drop-legacy-tables.md` |
| A9.n3-pr-a | lane | shipped | A9 | feat `IFProjector` v2 Monte Carlo | `sprint/A9/lanes/A9-n3-pr-a-feat-ifprojector-v2-monte-carlo.md` |
| A9.n3-pr-bc | lane | shipped | A9 | feat `IFConeChart` + wire E5 | `sprint/A9/lanes/A9-n3-pr-bc-feat-ifconechart-wire-e5.md` |
| A9.p1 | lane | shipped | A9 | feat Onda 9 design system + mobile | `sprint/A9/lanes/A9-p1-feat-onda-9-design-system-mobile.md` |
| F11.1 | lane | shipped | F11 | Mental model: “vida financeira” × “relatório deste mês” | `sprint/F11/lanes/F11-1-mental-model-vida-financeira-relatorio-deste-mes.md` |
| F11.2 | lane | shipped | F11 | Hierarquia de números | `sprint/F11/lanes/F11-2-hierarquia-de-numeros.md` |
| F11.3 | lane | shipped | F11 | Print / PDF como entregável de consultoria | `sprint/F11/lanes/F11-3-print-pdf-como-entregavel-de-consultoria.md` |
| F11.4 | lane | shipped | F11 | Transparência na UI: origem da informação | `sprint/F11/lanes/F11-4-transparencia-na-ui-origem-da-informacao.md` |
| F11.5 | lane | shipped | F11 | Transparência na UI: `needs_review` e trilha LLM | `sprint/F11/lanes/F11-5-transparencia-na-ui-needs-review-e-trilha.md` |
| F11.6 | lane | shipped | F11 | Metadados de premissas (metas e relatório) | `sprint/F11/lanes/F11-6-metadados-de-premissas.md` |
| F11.7 | lane | in_progress | F11 | Ligação explícita entre número e regra | `sprint/F11/lanes/F11-7-ligacao-explicita-entre-numero-e-regra.md` |
| F11.8 | lane | shipped | F11 | Command palette / atalhos | `sprint/F11/lanes/F11-8-command-palette-atalhos.md` |
| F12.1 | lane | shipped | F12 | Fundação i18n no frontend | `sprint/F12/lanes/F12-1-fundacao-i18n-no-frontend.md` |
| F12.2 | lane | blocked | F12 | Refactor de `format.ts` e `<MonetaryValue/>` | `sprint/F12/lanes/F12-2-refactor-de-format-ts-e-monetaryvalue.md` |
| F12.3 | lane | blocked | F12 | Persistência da escolha (DB + JWT) | `sprint/F12/lanes/F12-3-persistencia-da-escolha.md` |
| F12.4 | lane | blocked | F12 | Codegen do report layout multilíngue | `sprint/F12/lanes/F12-4-codegen-do-report-layout-multilingue.md` |
| F12.5 | lane | blocked | F12 | Backend user-facing strings | `sprint/F12/lanes/F12-5-backend-user-facing-strings.md` |
| F12.6 | lane | blocked | F12 | Tradução do relatório (bulk, paralelizável) | `sprint/F12/lanes/F12-6-traducao-do-relatorio.md` |
| F12.7 | lane | cancelled | F12 | RTL polish (`ar`) — fora do escopo F12 atual | `sprint/F12/lanes/F12-7-rtl-polish-fora-do-escopo-f12-atual.md` |
| F12.8 | lane | blocked | F12 | QA + E2E multi-locale | `sprint/F12/lanes/F12-8-qa-e2e-multi-locale.md` |
| F7.a | lane | shipped | F7 | Docker + Deploy + HTTPS (semana 1-2) | `sprint/F7/lanes/F7-a-docker-deploy-https.md` |
| F7.b | lane | shipped | F7 | Security Hardening + LGPD (semana 2-3) | `sprint/F7/lanes/F7-b-security-hardening-lgpd.md` |
| F7.c | lane | open | F7 | CI/CD + Observabilidade (semana 3-4) | `sprint/F7/lanes/F7-c-ci-cd-observabilidade.md` |
| F7.d | lane | shipped | F7 | Quality Gate + Launch Readiness (semana 4-6 + 2 sem dogfood) | `sprint/F7/lanes/F7-d-quality-gate-launch-readiness.md` |
| F7.e | lane | shipped | F7 | Operational Readiness (semana 6-7, ~2 semanas) | `sprint/F7/lanes/F7-e-operational-readiness.md` |
| F7.f | lane | shipped | F7 | Console interno (operadores) | `sprint/F7/lanes/F7-f-console-interno.md` |
| MARKETING-landing-copy-draft-v1 | marketing-draft | draft |  | Landing copy draft v1 — pilares ADR-183 (Fase 4.B COMPETITIVE_PIERRE) | `_marketing/landing-copy-draft-v1.md` |
| MOC-sprint-a10 | moc |  |  | Sprint A10 — goals.json cutover final | `sprint/A10/_README.md` |
| MOC-sprint-a11 | moc |  |  | Sprint A11 — Platform review execution | `sprint/A11/_README.md` |
| MOC-sprint-a12 | moc |  |  | Sprint A12 — Categorization learning loop + post-A11 follow-up | `sprint/A12/_README.md` |
| MOC-sprint-a15 | moc |  |  | Sprint A15 — FU-3 Imóvel financiado (Debt aggregate + valor_mercado override) | `sprint/A15/_README.md` |
| MOC-sprint-a16 | moc |  |  | Sprint A16 — Flips ADR-235 nu_proprietario + ADR-236 Tributário PJ Cascata Fiscal | `sprint/A16/_README.md` |
| MOC-sprint-a17 | moc |  |  | Sprint A17 — Ingestão de Informes de Rendimentos anuais avulsos (4 ondas) | `sprint/A17/_README.md` |
| MOC-sprint-a18 | moc |  |  | Sprint A18 — Comprovantes de Bem (CRLV) + Apólices polimórficas + FIPE refresh (3 lanes coordenadas) | `sprint/A18/_README.md` |
| MOC-sprint-a19 | moc |  |  | Sprint A19 — Card S_PROTECAO (4º pilar AUVP Proteção Patrimonial) | `sprint/A19/_README.md` |
| MOC-sprint-a20 | moc |  |  | Sprint A20 — Docker dev↔prod parity + P0 production gates | `sprint/A20/_README.md` |
| MOC-sprint-a21 | moc |  |  | Sprint A21 — Launch Trust: número confiável + gates de F3/LGPD abertos | `sprint/A21/_README.md` |
| MOC-sprint-a22 | moc |  |  | Sprint A22 — Launch Trust: Parecer defensável (F3) | `sprint/A22/_README.md` |
| MOC-sprint-a23 | moc |  |  | Sprint A23 — Data Lineage backbone (walking skeleton) | `sprint/A23/_README.md` |
| MOC-sprint-a24 | moc |  |  | Sprint A24 — Data Lineage: extração limpa + walking skeleton | `sprint/A24/_README.md` |
| MOC-sprint-a25 | moc |  |  | Sprint A25 — Data Lineage: reverso + produto N1/N2 + debug LLM | `sprint/A25/_README.md` |
| MOC-sprint-a26 | moc |  |  | Sprint A26 — Data Lineage: consolidação | `sprint/A26/_README.md` |
| MOC-sprint-a27 | moc |  |  | Sprint A27 — Data Lineage Onda 6 (conclusão): citação confiável do parecer, ponta a ponta | `sprint/A27/_README.md` |
| MOC-sprint-a28 | moc |  |  | Sprint A28 — Report Trust: o relatório para de afirmar precisão que os dados não sustentam | `sprint/A28/_README.md` |
| MOC-sprint-a6 | moc |  |  | Sprint A6 — Migração Infra+Domínio | `sprint/A6/_README.md` |
| MOC-sprint-a7 | moc |  |  | Sprint A7 — Config DB Cutover | `sprint/A7/_README.md` |
| MOC-sprint-a8 | moc |  |  | Sprint A8 — Continuação multi-tenant | `sprint/A8/_README.md` |
| MOC-sprint-a9 | moc |  |  | Sprint A9 — Multi-front improvements | `sprint/A9/_README.md` |
| PLAN-cat-learning-loop | plan | done |  | Categorization Learning Loop — promoção de override de transação para regra | `plan/CAT_LEARNING_LOOP/_README.md` |
| PLAN-cenarios-estresse | plan | done |  | Cenários de Estresse — plano canônico | `plan/CENARIOS_ESTRESSE/_README.md` |
| PLAN-competitive-pierre | plan | draft |  | Resposta competitiva — Pierre + ChatGPT Finance (recon, MCP, chat, memories, reposicionamento) | `plan/COMPETITIVE_PIERRE/_README.md` |
| PLAN-data-lineage | plan | in_progress |  | Data Lineage fim-a-fim + Fonte plugável | `plan/DATA_LINEAGE/_README.md` |
| PLAN-go-shell | plan | in_progress |  | Go shell (Caminho 1 da ADR-150) — port do pipeline-service para Go + Python via subprocess | `plan/GO_SHELL/_README.md` |
| PLAN-i18n | plan | paused |  | Internacionalização (i18n) | `plan/I18N/_README.md` |
| PLAN-internal-admin | plan | in_progress |  | Console interno (operadores) — IA-0 a IA-4 | `plan/INTERNAL_ADMIN/_README.md` |
| PLAN-launch-trust | plan | in_progress |  | Launch Trust — três frentes que precisam estar verdes antes de produção | `plan/LAUNCH_TRUST/_README.md` |
| PLAN-llm-prompts-hardening | plan | draft |  | LLM Prompts Hardening — LGPD + ADR-090 + PROMPT_VERSION + telemetria + cross-cutting | `plan/LLM_PROMPTS_HARDENING/_README.md` |
| PLAN-market-rates-ingestion | plan | draft |  | Ingestão de market rates dirigida por catálogo — Bacen SGS + Tesouro Direto | `plan/MARKET_RATES_INGESTION/_README.md` |
| PLAN-p1-structural | plan | paused |  | P1 — Plano estrutural (motor canônico + pipeline offline) | `plan/P1_STRUCTURAL/_README.md` |
| PLAN-planner-review | plan | done |  | Parecer do Planejador (E6) — substituição de review_finances + aterrissagem operacional | `plan/PLANNER_REVIEW/_README.md` |
| PLAN-platform-review | plan | in_progress |  | Platform Review Plan — 2026-05-06 | `plan/PLATFORM_REVIEW/_README.md` |
| PLAN-report-premium | plan | in_progress |  | Elevar `/reports/[id]` ao nível do `EXEMPLO_DE_RELATORIO.html` | `plan/REPORT_PREMIUM/_README.md` |
| PLAN-report-trust | plan | in_progress |  | Report Trust — o relatório não pode afirmar precisão que os dados não sustentam | `plan/REPORT_TRUST/_README.md` |
| PLAN-residencia-e-uso | plan | draft |  | Residência e uso econômico de imóveis — override DB substitui keyword | `plan/RESIDENCIA_E_USO/_README.md` |
| PLAN-s4-real-estate-enrichment | plan | done |  | S4 Real Estate — Enriquecimento do card de yield (cap rate líquido + benchmarks + tabela por imóvel) | `plan/S4_REAL_ESTATE_ENRICHMENT/_README.md` |
| PLAN-snapshot-changelog-v3 | plan | in_progress |  | Snapshot changelog v3 — métricas, cadência, decomposição e direção semântica | `plan/SNAPSHOT_CHANGELOG_V3/_README.md` |
| PLAN-suggestion-lifecycle | plan | in_progress |  | Ciclo de vida de sugestões do Parecer no /acao — supersede, thesis_key, valores determinísticos | `plan/SUGGESTION_LIFECYCLE/_README.md` |
| PLAN-tributario-pj | plan | done |  | Tributário PJ — Cascata Fiscal canônica (modelo de domínio + narrator correto) | `plan/TRIBUTARIO_PJ/_README.md` |
| runbook-python-dependencies | runbook | ativo |  | Runbook — Dependências Python (pip-tools lockfile com hashes) | `reference/runbooks/python_dependencies.md` |
| TRACK-a11-w2-t04-stuck-runs-heartbeat | track | ready | A11 | W2-T04 — Stuck-runs detector + last_heartbeat_at | `sprint/A11/tracks/a11-w2-t04-stuck-runs-heartbeat.md` |
| TRACK-a11-w2-t05-prompt-version-gate | track | ready | A11 | W2-T05 — extract_with_llm incremental + PROMPT_VERSION gate CI | `sprint/A11/tracks/a11-w2-t05-prompt-version-gate.md` |
| TRACK-a11-w2-t06-stage-to-suffix-descriptive | track | ready | A11 | W2-T06 — _STAGE_TO_SUFFIX cobre keys descritivas (paridade legacy ↔ descritivo) | `sprint/A11/tracks/a11-w2-t06-stage-to-suffix-descriptive.md` |
| TRACK-a11-w5-t06-rentabilidade-card | track | consumed | A11 | Card S3 Rentabilidade — rebrand TRS efetiva + enriquecimento + cobertura essencial | `sprint/A11/tracks/a11-w5-t06-rentabilidade-card.md` |
| TRACK-a15-fu3-onda1-schema | track | ready | A15 | Track A15 FU-3 Onda 1 — Schema + repos + models (Debt + property_market_value) | `sprint/A15/tracks/a15-fu3-onda1-schema.md` |
| TRACK-a15-fu3-onda2-backfill | track | ready | A15 | Track A15 FU-3 Onda 2 — Backfill total_dividas → rows Debt + audit log | `sprint/A15/tracks/a15-fu3-onda2-backfill.md` |
| TRACK-a15-fu3-onda3-calculator | track | ready | A15 | Track A15 FU-3 Onda 3 — Calculator + resolver puro + payload E5 | `sprint/A15/tracks/a15-fu3-onda3-calculator.md` |
| TRACK-a15-fu3-onda4-api | track | ready | A15 | Track A15 FU-3 Onda 4 — API endpoints + OpenAPI snapshot | `sprint/A15/tracks/a15-fu3-onda4-api.md` |
| TRACK-a15-fu3-onda5-frontend | track | ready | A15 | Track A15 FU-3 Onda 5 — Frontend: form, batch review, drill-down card | `sprint/A15/tracks/a15-fu3-onda5-frontend.md` |
| TRACK-a16-adr235-nu-proprietario-flip | track | consumed | A16 | Track A16 — Flip ADR-235 `nu_proprietario` para Decidido (migration + call-sites + ADR updates + E6 prompt + CI gate) | `sprint/A16/tracks/a16-adr235-nu-proprietario-flip.md` |
| TRACK-a16-adr236-tributario-pj-cascata | track | consumed | A16 | Track A16 — Tributário PJ Cascata Fiscal: BusinessProfile expandido + calculator + narrator + card UI (6 PRs) | `sprint/A16/tracks/a16-adr236-tributario-pj-cascata.md` |
| TRACK-a17-canonical-fuzzy-adr225 | track | consumed | A17 | Track A17 — Canonical fuzzy para números próximos (extensão ADR-225) | `sprint/A17/tracks/a17-canonical-fuzzy-adr225.md` |
| TRACK-a17-l1-previdencia-privada | track | ready | A17 | Track A17 L1 — Previdência privada (PGBL/VGBL): schema-base + parser LLM + FiscalAnalyzer polimórfico + UI | `sprint/A17/tracks/a17-l1-previdencia-privada.md` |
| TRACK-a17-l2-financeiro-pj | track | ready | A17 | Track A17 L2 — Financeiro PJ (C6 PJ, Stone, adquirentes): sub-schema + InformeQuery integration com ADR-236 | `sprint/A17/tracks/a17-l2-financeiro-pj.md` |
| TRACK-a17-l3-financeiro-pf | track | ready | A17 | Track A17 L3 — Financeiro PF (6 bancos + XP Investimentos + Wise multi-moeda): 4 quadros RFB + snapshot 31/12 + conta no exterior | `sprint/A17/tracks/a17-l3-financeiro-pf.md` |
| TRACK-a17-l4-proventos-acoes | track | ready | A17 | Track A17 L4 — Proventos ações (XP Proventos, Itaúsa): eventos por ativo + yield-on-cost S3 | `sprint/A17/tracks/a17-l4-proventos-acoes.md` |
| TRACK-a18-l1-crlv-veiculos | track | ready | A18 | Track A18 L1 — CRLV-e: tabela canônica vehicles + classifier + stage extract_comprovantes_bens + reconciliação assíncrona | `sprint/A18/tracks/a18-l1-crlv-veiculos.md` |
| TRACK-a18-l2-apolice-seguro | track | ready | A18 | Track A18 L2 — Apólice polimórfica: Discriminated Union bens+coberturas + cascata Haiku→Sonnet + combinada V1 | `sprint/A18/tracks/a18-l2-apolice-seguro.md` |
| TRACK-a18-l3-fipe-refresh | track | ready | A18 | Track A18 L3 — FIPE refresh assíncrono via BrasilAPI: market_rates extension + Celery task + cron anual | `sprint/A18/tracks/a18-l3-fipe-refresh.md` |
| TRACK-a19-l1-card-protecao | track | ready | A19 | Track A19 L1 — Card S_PROTECAO no relatório: ProtecaoAnalyzer + report_layout + componente React + reposicionamento AUVP | `sprint/A19/tracks/a19-l1-card-protecao.md` |
| TRACK-a20-fu-chromium-headless-shell | track | ready | A20 | Track A20.FU — Slim playwright target via chromium-headless-shell | `sprint/A20/tracks/a20-fu-chromium-headless-shell.md` |
| TRACK-a20-l1-backend-multistage | track | consumed | A20 | Track A20.L1 — Backend multi-stage + Playwright dual target | `sprint/A20/tracks/a20-l1-backend-multistage.md` |
| TRACK-a20-l10-python-lockfile | track | consumed | A20 | Track A20.L10 — Python lockfile com hashes (pip-tools vs uv) | `sprint/A20/tracks/a20-l10-python-lockfile.md` |
| TRACK-a20-l4-ghcr-push | track | ready | A20 | Track A20.L4 — GHCR push em CI + tagging strategy | `sprint/A20/tracks/a20-l4-ghcr-push.md` |
| TRACK-a20-l5-trivy-sbom | track | ready | A20 | Track A20.L5 — Trivy image scan blocking + SBOM CycloneDX | `sprint/A20/tracks/a20-l5-trivy-sbom.md` |
| TRACK-a20-l6-compose-dev | track | consumed | A20 | Track A20.L6 — docker-compose.dev.yml unificado + cleanup composes legados | `sprint/A20/tracks/a20-l6-compose-dev.md` |
| TRACK-a20-l9-smoke-e2e | track | ready | A20 | Track A20.L9 — Smoke E2E em compose (gate de fechamento do sprint) | `sprint/A20/tracks/a20-l9-smoke-e2e.md` |
| TRACK-a24-l7-schema-strict-flip | track | ready | A24 | Track A24.l7 — baseline → de-drift vocabulário E2 → flip strict per-schema | `sprint/A24/tracks/a24-l7-schema-strict-flip.md` |
| TRACK-a25-suggestion-lifecycle | track | consumed | A25 | Track A25 — SUGGESTION_LIFECYCLE F1→F4: supersede-per-run, thesis_key, valores determinísticos, cap/ordering, backfill dogfood | `sprint/A25/tracks/a25-suggestion-lifecycle.md` |
| TRACK-a3cli-benchmark | track | consumed |  | Track A3.cli.benchmark — gate empírico de cold start do run-stage (decide se Caminho 2 reabre antes do 1º PR Go) | `plan/GO_SHELL/tracks/a3cli-benchmark.md` |
| TRACK-a3cli-orchestrator-cli | track | consumed |  | Track A3.cli — entry-point CLI run-stage no orchestrator + injeção DBArtifactStore (Fase 1) + OTel TRACEPARENT (Fase 2) | `plan/GO_SHELL/tracks/a3cli-orchestrator-cli.md` |
| TRACK-a6e-events-domain-events | track | consumed | A6 | Track A6e.events — Domain events tipados (ADR-101 R17) | `sprint/A6/tracks/a6e-events-domain-events.md` |
| TRACK-a6e3-use-cases | track | consumed | A6 | Track A6e.3 — Application Layer (use cases) — slice inicial | `sprint/A6/tracks/a6e3-use-cases.md` |
| TRACK-a6e3b-use-cases-rest | track | consumed | A6 | Track A6e.3b — Application layer: ConfigBlob + Document + Task (use cases) | `sprint/A6/tracks/a6e3b-use-cases-rest.md` |
| TRACK-a6e4-thin-routers | track | consumed | A6 | Track A6e.4 — Routers finos (17 routers × ≤50 linhas) | `sprint/A6/tracks/a6e4-thin-routers.md` |
| TRACK-a6e5-v1-prefix | track | consumed | A6 | Track A6e.5 — `/api/v1/` prefix + aliases + OpenAPI versionado | `sprint/A6/tracks/a6e5-v1-prefix.md` |
| TRACK-a6f1-pipeline-service | track | consumed | A6 | Track A6f.1 — Pipeline-as-Service (HTTP boundary) | `sprint/A6/tracks/a6f1-pipeline-service.md` |
| TRACK-a6g-eslint-max-lines-ratchet | track | ready | A6 | Track A6g.RATCHET — max-lines-per-function warn→error com ratchet de disables | `sprint/A6/tracks/a6g-eslint-max-lines-ratchet.md` |
| TRACK-a6g2-pipeline-style-sweep | track | consumed | A6 | Track A6g.2 — Pipeline Code Style Sweep | `sprint/A6/tracks/a6g2-pipeline-style-sweep.md` |
| TRACK-a6g3-backend-style-sweep | track | consumed | A6 | Track A6g.3 — Backend Python code style sweep | `sprint/A6/tracks/a6g3-backend-style-sweep.md` |
| TRACK-a6g3b-decimal-money-migration | track | consumed | A6 | Track A6g.3b — Migração completa `float` → `Decimal` em money DTOs + math | `sprint/A6/tracks/a6g3b-decimal-money-migration.md` |
| TRACK-a6g4-frontend-style-sweep | track | consumed | A6 | Track A6g.4 — Frontend Code Style Sweep | `sprint/A6/tracks/a6g4-frontend-style-sweep.md` |
| TRACK-a6g5-tests-sweep | track | consumed | A6 | Track A6g.5 — Tests Sweep (fakes nomeados + nomes descritivos) | `sprint/A6/tracks/a6g5-tests-sweep.md` |
| TRACK-a6g6-enforcement | track | consumed | A6 | Track A6g.6 — Enforcement automatizado de code style | `sprint/A6/tracks/a6g6-enforcement.md` |
| TRACK-a6g7-go-prep | track | consumed | A6 | Track A6g.7 — Go prep (golangci-lint + CI job + skeleton convention) | `sprint/A6/tracks/a6g7-go-prep.md` |
| TRACK-a7-0-config-store | track | consumed | A7 | Track A7.0 — `ConfigStore` protocol + adapters | `sprint/A7/tracks/a7-0-config-store.md` |
| TRACK-a7-1-cutover-materialize | track | consumed | A7 | Track A7.1 — Cutover `materialize_config` → `ConfigStore` | `sprint/A7/tracks/a7-1-cutover-materialize.md` |
| TRACK-a7-2a-decision-aggregate | track | consumed | A7 | Track A7.2a — `Decision` aggregate (event-sourced) + migrator + tela Plano de Ação | `sprint/A7/tracks/a7-2a-decision-aggregate.md` |
| TRACK-a7-2b-fiscal-market-tables | track | consumed | A7 | Track A7.2b — Tabelas globais `fiscal_parameters` + `market_rates` versionadas | `sprint/A7/tracks/a7-2b-fiscal-market-tables.md` |
| TRACK-a7-3-catalog-override | track | consumed | A7 | Track A7.3 — Catalog + Override resolver (categorization + institutions) | `sprint/A7/tracks/a7-3-catalog-override.md` |
| TRACK-a7-4-methodology-docs | track | consumed | A7 | Track A7.4 — Documentação metodológica → `docs/methodology/` | `sprint/A7/tracks/a7-4-methodology-docs.md` |
| TRACK-a7-5-cleanup | track | consumed | A7 | Track A7.5 — Cleanup final (deletar `config/` + bridges) | `sprint/A7/tracks/a7-5-cleanup.md` |
| TRACK-a7-6-rules-as-code | track | consumed | A7 | Track A7.6 — Rules-as-code: dissolver `docs/methodology/` | `sprint/A7/tracks/a7-6-rules-as-code.md` |
| TRACK-a8-trs-real | track | consumed | A8 | Track — A8 TRS real (renda passiva observada + Taxa de Retirada Sustentável efetiva) | `sprint/A8/tracks/a8-trs-real.md` |
| TRACK-adr272-review-reasons | track | ready | A20 | Track A20 — ReviewReason estruturado (ADR-272) em 4 fases | `sprint/A20/tracks/adr272-review-reasons.md` |
| TRACK-alocacao-v2-7-classes-migration | track | ready | A12 | Track Alocação v2 — migração schema 4→7 classes e desvio backend-driven | `sprint/A12/tracks/alocacao-v2-7-classes-migration.md` |
| TRACK-auvp-threshold-pgbl-variant | track | consumed | A12 | Track AUVP threshold modula variante PGBL (M2 do ADR-189) | `sprint/A12/tracks/auvp-threshold-pgbl-variant.md` |
| TRACK-bank-account-disambig | track | ready | A12 | Track bank-account-disambig — 4 PRs sequenciais (ADR-226) | `sprint/A12/tracks/bank-account-disambig.md` |
| TRACK-cat-learning-loop-p1-schema | track | ready | A12 | Track Cat Learning Loop P1 — Schema (transaction_overrides.source + categorization_rules) | `sprint/A12/tracks/cat-learning-loop-p1-schema.md` |
| TRACK-cat-learning-loop-p2-pipeline | track | ready | A12 | Track Cat Learning Loop P2 — Pipeline E4 (CategorizationRulesV2 + adapter) | `sprint/A12/tracks/cat-learning-loop-p2-pipeline.md` |
| TRACK-cat-learning-loop-p3-backend-api | track | ready | A12 | Track Cat Learning Loop P3 — Backend API + schema evolution | `sprint/A12/tracks/cat-learning-loop-p3-backend-api.md` |
| TRACK-category-overrides-cache-fix | track | consumed | A11 | Track Category Overrides W1 — Cache invalidation + CategoryOverrideService | `sprint/A11/tracks/category-overrides-cache-fix.md` |
| TRACK-category-overrides-policy-adr | track | consumed | A11 | Track Category Overrides W3 — ADR-185 Proposto (política + escopo + invariantes) | `sprint/A11/tracks/category-overrides-policy-adr.md` |
| TRACK-category-overrides-schema-delta | track | consumed | A11 | Track Category Overrides W2 — Schema delta (updated_by_user_id + DTO version fields) | `sprint/A11/tracks/category-overrides-schema-delta.md` |
| TRACK-category-overrides-ui-refactor | track | consumed | A11 | Track Category Overrides W4 — UI refactor (CategoriesTab + useCategoriesAndMembers) | `sprint/A11/tracks/category-overrides-ui-refactor.md` |
| TRACK-citacao-deterministica | track | ready | A27 | Track A26.l9 — citação determinística (LLM emite path+rótulo; pipeline renderiza valor) | `sprint/A27/tracks/citacao-deterministica.md` |
| TRACK-competitor-pierre-poc | track | ready | A11 | Track Competitor POC — Pierre Finance API + MCP benchmark | `sprint/A11/tracks/competitor-pierre-poc.md` |
| TRACK-decision-code-autogen | track | consumed | A12 | Track Decision.code server-generated — PR único cross-cutting | `sprint/A12/tracks/decision-code-autogen.md` |
| TRACK-f1-go-service | track | ready |  | Track F1 — serviço Go pipeline-service-go (Caminho 1): 4 fases, 4 PRs | `plan/GO_SHELL/tracks/f1-go-service.md` |
| TRACK-f7f-local | track | consumed | F7 | Track F7F-Local — Console interno pré-produção (IA-0) | `sprint/F7/tracks/f7f-local.md` |
| TRACK-f9-0-audit | track | consumed | F9 | Track F9.0 — Auditoria de referências aos identificadores legados | `sprint/F9/tracks/f9-0-audit.md` |
| TRACK-f9-1-pipeline-stages-rename | track | consumed | F9 | Track F9.1 — `git mv pipeline/stages/e*.py` → nomes descritivos | `sprint/F9/tracks/f9-1-pipeline-stages-rename.md` |
| TRACK-f9-2-string-literals | track | consumed | F9 | Track F9.2 — Substituir strings literais `"E*"` em código de produção | `sprint/F9/tracks/f9-2-string-literals.md` |
| TRACK-f9-2a-pipeline-core-strings | track | consumed | F9 | Track F9.2a — Strings descritivas em `pipeline/` (resíduo) | `sprint/F9/tracks/f9-2a-pipeline-core-strings.md` |
| TRACK-f9-2b-scripts-strings | track | consumed | F9 | Track F9.2b — Strings descritivas em `scripts/` (excluindo `e_reset.py`) | `sprint/F9/tracks/f9-2b-scripts-strings.md` |
| TRACK-f9-2c-e-reset-deprecation | track | consumed | F9 | Track F9.2c — `scripts/e_reset.py` deprecation warning + flip interno | `sprint/F9/tracks/f9-2c-e-reset-deprecation.md` |
| TRACK-f9-2d-backend-tests | track | consumed | F9 | Track F9.2d — Strings descritivas em `backend/app/` residual + tests não-golden | `sprint/F9/tracks/f9-2d-backend-tests.md` |
| TRACK-f9-2e-closeout | track | consumed | F9 | Track F9.2e — Closeout F9.2 (audit final + docs + destrava F9.3) | `sprint/F9/tracks/f9-2e-closeout.md` |
| TRACK-f9-3-alembic-migration | track | consumed | F9 | Track F9.3 — Alembic migration: rename `pipeline_artifacts.stage` em massa | `sprint/F9/tracks/f9-3-alembic-migration.md` |
| TRACK-f9-4-scripts-rename | track | consumed | F9 | Track F9.4 — `git mv scripts/e*.py` → descritivos + alias CLI compat | `sprint/F9/tracks/f9-4-scripts-rename.md` |
| TRACK-f9-5-guardrail-hardfail | track | consumed | F9 | Track F9.5 — Guardrail hard-fail contra identificadores legados | `sprint/F9/tracks/f9-5-guardrail-hardfail.md` |
| TRACK-f9-6-cleanup | track | consumed | F9 | Track F9.6 — Cleanup final: remover wrappers compat, aliases e globals legados | `sprint/F9/tracks/f9-6-cleanup.md` |
| TRACK-gtm-landing-copy-rewrite | track | ready | A11 | Track GTM Landing Copy Rewrite — Fase 4.B COMPETITIVE_PIERRE (operational skeleton) | `sprint/A11/tracks/gtm-landing-copy-rewrite.md` |
| TRACK-gtm-landing-publish-static | track | ready | A11 | Track GTM Landing Publish Static — PR-D-A Fase 4.B COMPETITIVE_PIERRE | `sprint/A11/tracks/gtm-landing-publish-static.md` |
| TRACK-irpf-full-schema | track | consumed | A11 | Track IRPF Full Schema — extração completa de declaração de IRPF (E1.6) | `sprint/A11/tracks/irpf-full-schema.md` |
| TRACK-irpf-full-schema-cutover | track | consumed | A11 | Track IRPF Full Schema Cutover — flag `MATHOMS_E16_SUPERSEDES_E15_BENS` | `sprint/A11/tracks/irpf-full-schema-cutover.md` |
| TRACK-irpf-full-schema-goldens | track | consumed | A11 | Track IRPF Full Schema Goldens — fixtures + golden tests byte-byte | `sprint/A11/tracks/irpf-full-schema-goldens.md` |
| TRACK-irpf-full-schema-ui | track | consumed | A11 | Track IRPF Full Schema UI — relatório premium consome KPIs do E1.6 | `sprint/A11/tracks/irpf-full-schema-ui.md` |
| TRACK-irpf-otimizacao-cards-revival | track | consumed | A12 | Track IRPF Otimização — reativar cards Dependentes Declarados + Dedutíveis Subutilizados | `sprint/A12/tracks/irpf-otimizacao-cards-revival.md` |
| TRACK-irpf-prefill-bank-accounts | track | ready | A12 | Track IRPF pre-fill V1 — contas bancárias (2 PRs sequenciais) | `sprint/A12/tracks/irpf-prefill-bank-accounts.md` |
| TRACK-onda-1-kanban-task-migration | track | consumed | A11 | Track — Onda 1: Migration `kanban_items` + `report_notes` → `tasks` + `workspace_notes` | `sprint/A11/tracks/onda-1-kanban-task-migration.md` |
| TRACK-onda-10-cross-route-coherence | track | consumed | A11 | Track — Onda 10: coerência cross-rota (/plano · /acao · /reports) | `sprint/A11/tracks/onda-10-cross-route-coherence.md` |
| TRACK-onda-5-suggestion-aggregate | track | consumed | A11 | Track — Onda 5: Suggestion aggregate full-stack (Direção E) | `sprint/A11/tracks/onda-5-suggestion-aggregate.md` |
| TRACK-onda-7-p0-blockers | track | consumed | A11 | Track — Onda 7: bloqueadores P0 da Direção E (pós-revisão de produto) | `sprint/A11/tracks/onda-7-p0-blockers.md` |
| TRACK-onda-8-methodology-coherence | track | consumed | A11 | Track — Onda 8: coerência metodológica (Cerbasi/AUVP/Perini completos) | `sprint/A11/tracks/onda-8-methodology-coherence.md` |
| TRACK-onda-9-design-system-polish | track | consumed | A11 | Track — Onda 9: design system polish + dedup tarefas + mobile | `sprint/A11/tracks/onda-9-design-system-polish.md` |
| TRACK-pgbl-card-diagnostico | track | consumed | A11 | Track PGBL: diagnóstico tipificado (4 estados) substitui métrica monovalor no card | `sprint/A11/tracks/pgbl-card-diagnostico.md` |
| TRACK-pipeline-review-quick-unblock | track | consumed | A11 | Track Pipeline Review — Quick Unblock (caminho A) | `sprint/A11/tracks/pipeline-review-quick-unblock.md` |
| TRACK-pipeline-review-screen | track | consumed | A11 | Track Pipeline Review — Tela de revisão real (caminho B) | `sprint/A11/tracks/pipeline-review-screen.md` |
| TRACK-platform-review | track | consumed | A11 | Track Platform Review — Orquestração Multi-Agent (revisão + plano) | `sprint/A11/tracks/platform-review.md` |
| TRACK-real-estate-efficiency | track | consumed | A11 | Track — Real estate efficiency feature (ADR-160) | `sprint/A11/tracks/real-estate-efficiency.md` |
| TRACK-remove-historico-ciclos-app-e | track | consumed | A25 | Remover card 'Histórico de Ciclos' (Apêndice E) do relatório React | `sprint/A25/tracks/remove-historico-ciclos-app-e.md` |
| TRACK-report-a11y-finalize | track | consumed | A11 | Track Report a11y + Playwright finalize — resíduo F12 do Report Premium | `sprint/A11/tracks/report-a11y-finalize.md` |
| TRACK-report-appearance-menu | track | consumed | A11 | Track Report Appearance Menu — refinement ADR-121 Fase 4 | `sprint/A11/tracks/report-appearance-menu.md` |
| TRACK-report-publication-impl | track | consumed | A11 | Report publication — schema + API + helper (mês fechado imutável) | `sprint/A11/tracks/report-publication-impl.md` |
| TRACK-report-v1-polish | track | consumed | A11 | Track Report Premium v1 polish — resíduo F13 do Report Premium | `sprint/A11/tracks/report-v1-polish.md` |
| TRACK-report-v2 | track | consumed | A11 | Track Report Premium UI v2 — meta-prompt + roadmap de execução | `sprint/A11/tracks/report-v2.md` |
| TRACK-report-v2-changelog-engine | track | consumed | A11 | Track Report v2.D.1 + v2.8 — Snapshot changelog engine + comparisons/changelog ON | `sprint/A11/tracks/report-v2-changelog-engine.md` |
| TRACK-report-v2-charts-ux | track | consumed | A11 | Track Report v2.E — Charts UX (paridade visual final dos charts) | `sprint/A11/tracks/report-v2-charts-ux.md` |
| TRACK-report-v2-t2-aportes | track | consumed | A11 | Track Report v2.4 — T2 Aportes seção real | `sprint/A11/tracks/report-v2-t2-aportes.md` |
| TRACK-s9-riscos-expansion | track | consumed | A11 | Track S9 Riscos e Proteção — Expansão completa (Protection aggregate + ProtectionBundle + 5 blocos UI) | `sprint/A11/tracks/s9-riscos-expansion.md` |
| TRACK-sunset-disk-artifact | track | ready | A12 | Track Sunset DiskArtifactStore — 5 PRs sequenciais (ADR-212) | `sprint/A12/tracks/sunset-disk-artifact.md` |
| TRACK-taxa-divida-numerica | track | ready | A26 | Track — Extração de taxa numérica de dívida (endurece RL-2 de best-effort para hard) | `sprint/A26/tracks/taxa-divida-numerica.md` |
| TRACK-w5t01-a11y | track | consumed | W5 | Track W5-T01 — A11y onda: scope=col + role=progressbar + aria-label charts + reduced-motion | `sprint/W5/tracks/w5t01-a11y.md` |
| TRACK-w5t03-monetary-value | track | consumed | W5 | Track W5-T03 — `<MonetaryValue size="kpi">` migration | `sprint/W5/tracks/w5t03-monetary-value.md` |
| TRACK-w5t04-adr161-enrichment | track | consumed | W5 | Track W5-T04 — FP-004 ADR-161 enrichment (5 sub-PRs paralelos) | `sprint/W5/tracks/w5t04-adr161-enrichment.md` |
| TRACK-w5t05-goal-if-v2 | track | consumed | W5 | Track W5-T05 — Goal IF v2 cutover (3 PRs sequenciais) | `sprint/W5/tracks/w5t05-goal-if-v2.md` |
| TRACK-w6t01-schema-hardening | track | consumed | W6 | Track W6-T01 — Schema hardening (E5 strict + 7 sub-schemas E4 + ADR-090 wire) | `sprint/W6/tracks/w6t01-schema-hardening.md` |
| TRACK-w6t05-artifacts-retention | track | consumed | W6 | Track W6-T05 — Pipeline artifacts retention + cascade-on-delete | `sprint/W6/tracks/w6t05-artifacts-retention.md` |
