> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# Índice geral da vault

| id | type | status | sprint | título | path |
| --- | --- | --- | --- | --- | --- |
| ADR-001 | adr | Decidido |  | SQLAlchemy 2.0 como ORM | `adr/001-sqlalchemy-20-como-orm.md` |
| ADR-002 | adr | Decidido |  | Filesystem local para storage | `adr/002-filesystem-local-para-storage.md` |
| ADR-003 | adr | Decidido |  | JWT custom para auth | `adr/003-jwt-custom-para-auth.md` |
| ADR-005 | adr | Decidido |  | VPS Hetzner para produção | `adr/005-vps-hetzner-para-producao.md` |
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
| ADR-058 | adr | Decidido |  | VPS CX32 para sizing | `adr/058-vps-cx32-para-sizing.md` |
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
| ADR-121 | adr | Decidido |  | Typography base 13px com override configurável | `adr/121-typography-base-13px-com-override-configuravel.md` |
| ADR-122 | adr | Decidido |  | `chart_conclusions` e `section_summaries` em modo híbrido (template + LLM) | `adr/122-chart-conclusions-e-section-summaries-em-modo.md` |
| ADR-123 | adr | Decidido |  | Notas (T6) e Kanban (T3) persistidos no backend | `adr/123-notas-t6-e-kanban-t3-persistidos-no-backend.md` |
| ADR-124 | adr | Decidido |  | `scripts/e6_render.py` aposentado em favor de SSR standalone do Next | `adr/124-scriptse6-renderpy-aposentado-em-favor-de-ssr.md` |
| ADR-125 | adr | Decidido |  | Workspace sharing: convites, viewer role, forced logout | `adr/125-workspace-sharing-convites-viewer-role-forced.md` |
| ADR-126 | adr | Decidido |  | Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO) | `adr/126-multi-tenant-goals-completos-aporte-mensal.md` |
| ADR-127 | adr | Decidido |  | E1 members persiste via ArtifactStore | `adr/127-e1-members-persiste-via-artifactstore.md` |
| ADR-128 | adr | Decidido |  | E7-review-llm lê/escreve via `ArtifactStore` | `adr/128-e7-review-llm-leescreve-via-artifactstore.md` |
| ADR-129 | adr | Decidido |  | Descontinuação completa do renderer HTML server-side | `adr/129-descontinuacao-completa-do-renderer-html-server.md` |
| ADR-130 | adr | Proposto |  | Internacionalização com `next-intl` + persistência em `users.locale` | `adr/130-internacionalizacao-com-next-intl-persistencia.md` |
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
| ADR-141 | adr | Roadmap |  | Goal alocação-alvo schema v2 (7 classes AUVP) | `adr/141-goal-alocacao-alvo-schema-v2-7-classes-auvp.md` |
| ADR-142 | adr | Decidido |  | Toggle `imoveis_no_if` em `pipeline.json` + invariante anti-dupla-contagem | `adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md` |
| ADR-143 | adr | Decidido |  | `docs/methodology/` é rules-as-code (Sprint A7.6) | `adr/143-docsmethodology-e-rules-as-code-sprint-a76.md` |
| ADR-144 | adr | Decidido |  | `section_summaries` LLM-driven em E5 com cache + fallback determinístico (v2.9) | `adr/144-section-summaries-llm-driven-em-e5-com-cache.md` |
| ADR-145 | adr | Decidido |  | 7 categorias canonical da composição patrimonial | `adr/145-7-categorias-canonical-da-composicao-patrimonial.md` |
| ADR-146 | adr | Decidido |  | E3 source hierarchy + `BankAccount.source_tier` schema | `adr/146-e3-source-hierarchy-bankaccountsource-tier-schema.md` |
| ADR-147 | adr | Decidido |  | Milhas: valuation methodology universal + storage workspace-scoped | `adr/147-milhas-valuation-methodology-universal-storage.md` |
| ADR-148 | adr | Decidido |  | `SnapshotChangelogBuilder`: comparações mês-a-mês de relatório | `adr/148-snapshotchangelogbuilder-comparacoes-mes-a-mes.md` |
| ADR-149 | adr | Decidido |  | `config/report_layout.yaml` permanece como asset de produto (Sprint A8.0) | `adr/149-configreport-layoutyaml-permanece-como-asset-de.md` |
| ADR-150 | adr | Roadmap |  | Estratégia de port Go do `pipeline-service`: Caminho 1 (shell-only via subprocess) como default deferido para Roadmap | `adr/150-estrategia-de-port-go-do-pipeline-service.md` |
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
| ADR-170 | adr | Proposto |  | Refresh tokens com httpOnly cookie e family-based revocation | `adr/170-refresh-tokens-com-httponly-cookie-e-family.md` |
| ADR-171 | adr | Proposto |  | Fernet rotation operacionalizada via MultiFernet | `adr/171-fernet-rotation-operacionalizada-via-multifernet.md` |
| ADR-172 | adr | Proposto |  | Stuck-runs detector via heartbeat + Celery beat | `adr/172-stuck-runs-detector-via-heartbeat-celery-beat.md` |
| ADR-173 | adr | Proposto |  | LLM budget hard-stop + LLMCallLog populada universal | `adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md` |
| ADR-174 | adr | Proposto |  | Off-site backup criptografado em Cloudflare R2 + restore drill | `adr/174-off-site-backup-criptografado-em-cloudflare-r2.md` |
| ADR-175 | adr | Proposto |  | Prompt injection defense em camadas (sanitize + system clause + Pydantic strict) | `adr/175-prompt-injection-defense-em-camadas-sanitize.md` |
| ADR-176 | adr | Proposto |  | Chave estável `cenarios_conjuge` no bloco de narrativas E5.N | `adr/176-chave-estavel-cenarios-conjuge-no-bloco-de.md` |
| ADR-177 | adr | Decidido |  | Thresholds e referências metodológicas como código (rules-as-code consolidation `goals.json`) | `adr/177-thresholds-e-referencias-metodologicas-como.md` |
| ADR-178 | adr | Decidido |  | `Risk` aggregate workspace-scoped | `adr/178-risk-aggregate-workspace-scoped.md` |
| ADR-179 | adr | Decidido |  | `Decision` aggregate — extensão de schema (`impact_1y/10y`, `horizon`, `priority`) | `adr/179-decision-aggregate-extensao-de-schema-impact.md` |
| ADR-180 | adr | Decidido |  | `goals.json` cutover final via `StageConfig.config_store` extendido | `adr/180-goalsjson-cutover-final-via-stageconfigconfig.md` |
| ADR-181 | adr | Decidido |  | `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py` | `adr/181-goalsjson-removido-de-archive-e-adicionado-a.md` |
| ADR-182 | adr | Proposto |  | Vault de documentação operacional Obsidian-friendly em `docs/` | `adr/182-vault-de-documentacao-operacional-obsidian.md` |
