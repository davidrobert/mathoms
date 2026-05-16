<!-- F2.E shim — ADR-182 / DOC_REORG_PLAN F2 — 2026-05-07 -->

# DECISIONS — Architectural Decision Records

> **Este arquivo é um shim. Não altere decisão aqui.** As ADRs vivem agora como notas atômicas em
> [`docs/adr/`](adr/) (uma por arquivo), com frontmatter validado por
> JSON Schema (`docs/_schemas/note-adr.schema.json`).
>
> **Para LLMs:** navegue por [_MOC/_generated/ADR_INDEX.md](_MOC/_generated/ADR_INDEX.md)
> (auto-gerado por `dev/build_doc_index.py`, agrupado por categoria + status).
> Só use este shim para instruções de criação ou anchors históricos.

## Como criar uma ADR nova

1. Crie `docs/adr/NNN-<slug>.md` (NNN = 3 dígitos zero-padded, próximo número livre).
2. Frontmatter obrigatório: `id` (`ADR-NNN`), `type: adr`, `title`, `status` (`Decidido` | `Proposto` | `Roadmap`), `date` (string ISO, com aspas).
3. Tags: `type/adr`, `status/<status-lowercase>`, opcional `area/<dominio>`, `phase/<fase>`.
4. Body: contexto → decisão → consequências (ver [ADR-182](adr/182-vault-de-documentacao-operacional-obsidian.md) para o contrato da vault).
5. Validação: `python3 dev/validate_frontmatter.py docs/adr/NNN-<slug>.md`.
6. Regenere índice: `python3 dev/build_doc_index.py --inline`.

## Política operacional

- ADR `Proposto` antes de PR P0/P1 com escopo arquitetural (modelo de DB, contrato API, fornecedor externo, política de segurança, mudança em invariante crítico). PR de implementação flippa para `Decidido (Sprint XX.Y)` no merge.
- Supersedure bidirecional: ADR-Y supersede ADR-X → declare `supersedes: ["[[ADR-X]]"]` em Y E `superseded_by: ["[[ADR-Y]]"]` em X.
- Tamanho > 150 linhas (`size_lines` no frontmatter, gerado por `dev/build_doc_index.py`) exige justificativa explícita ou split.

## Gates de validação

```bash
python3 dev/validate_frontmatter.py        # frontmatter contra schemas
python3 dev/check_doc_filename_id.py       # filename ↔ id
python3 dev/check_doc_links.py             # wikilinks resolvem
python3 dev/check_adr_anchors.py           # anchors históricos + slug
python3 dev/build_doc_index.py --check     # _generated/ sincronizado
```

Pre-commit já cobre todos automaticamente.

---

## Âncoras históricas

PRs antigos linkam `docs/DECISIONS.md#adr-NNN-...` (slug GitHub Slugger). Os anchors abaixo preservam clickability — cada um pode ser linkado de qualquer lugar e navega aqui. Para ler o conteúdo da ADR, consulte o link correspondente em `docs/adr/`.

<a id="adr-001--sqlalchemy-20-como-orm"></a> [ADR-001](adr/001-sqlalchemy-20-como-orm.md)
<a id="adr-002--filesystem-local-para-storage"></a> [ADR-002](adr/002-filesystem-local-para-storage.md)
<a id="adr-003--jwt-custom-para-auth"></a> [ADR-003](adr/003-jwt-custom-para-auth.md)
<a id="adr-005--vps-hetzner-para-produção"></a> [ADR-005](adr/005-vps-hetzner-para-producao.md)
<a id="adr-006--monorepo"></a> [ADR-006](adr/006-monorepo.md)
<a id="adr-013--wrap-dont-rewrite-pattern"></a> [ADR-013](adr/013-wrap-dont-rewrite-pattern.md)
<a id="adr-014--threading-para-execução-background"></a> [ADR-014](adr/014-threading-para-execucao-background.md)
<a id="adr-015--vault-por-workspace"></a> [ADR-015](adr/015-vault-por-workspace.md)
<a id="adr-016--e0-route-automático-no-upload"></a> [ADR-016](adr/016-e0-route-automatico-no-upload.md)
<a id="adr-017--sync-session-em-background-threads"></a> [ADR-017](adr/017-sync-session-em-background-threads.md)
<a id="adr-018--config_dir-override-em-for_tenant"></a> [ADR-018](adr/018-config-dir-override-em-for-tenant.md)
<a id="adr-019--storage_root-via-env-var"></a> [ADR-019](adr/019-storage-root-via-env-var.md)
<a id="adr-020--materializar-config-em-disco"></a> [ADR-020](adr/020-materializar-config-em-disco.md)
<a id="adr-021--5-configs-editáveis"></a> [ADR-021](adr/021-5-configs-editaveis.md)
<a id="adr-022--fallback-seletivo-de-config"></a> [ADR-022](adr/022-fallback-seletivo-de-config.md)
<a id="adr-023--importexport-json-de-config"></a> [ADR-023](adr/023-importexport-json-de-config.md)
<a id="adr-024--litellm-como-proxy-universal"></a> [ADR-024](adr/024-litellm-como-proxy-universal.md)
<a id="adr-025--byok-bring-your-own-key"></a> [ADR-025](adr/025-byok-bring-your-own-key.md)
<a id="adr-026--instructor--pydantic-para-structured-output"></a> [ADR-026](adr/026-instructor-pydantic-para-structured-output.md)
<a id="adr-027--retry--needs_review-em-falha-de-validação"></a> [ADR-027](adr/027-retry-needs-review-em-falha-de-validacao.md)
<a id="adr-028--e7-full-scope-na-fase-4"></a> [ADR-028](adr/028-e7-full-scope-na-fase-4.md)
<a id="adr-029--alembic-para-migrations"></a> [ADR-029](adr/029-tq-celery-redis.md)
<a id="adr-029-tq--celery--redis"></a> [ADR-029-TQ](adr/029-tq-celery-redis.md)
<a id="adr-030--cancelamento-cooperativo-via-threadingevent"></a> [ADR-030](adr/030-cancelamento-cooperativo-via-threadingevent.md)
<a id="adr-030-ws--websocket--polling-fallback"></a> [ADR-030-WS](adr/030-ws-websocket-polling-fallback.md)
<a id="adr-031--redis-para-queue--pubsub"></a> [ADR-031](adr/031-redis-para-queue-pubsub.md)
<a id="adr-032--cancel-stage-boundary"></a> [ADR-032](adr/032-cancel-stage-boundary.md)
<a id="adr-033--react-components-para-report"></a> [ADR-033](adr/033-react-components-para-report.md)
<a id="adr-034--dashboard-completo-com-alertas"></a> [ADR-034](adr/034-dashboard-completo-com-alertas.md)
<a id="adr-035--media-print-para-pdf-export"></a> [ADR-035](adr/035-media-print-para-pdf-export.md)
<a id="adr-037--recharts-para-charts"></a> [ADR-037](adr/037-recharts-para-charts.md)
<a id="adr-038--docker-volume-para-storage-prod"></a> [ADR-038](adr/038-docker-volume-para-storage-prod.md)
<a id="adr-039--dual-db-sqlite-dev--postgresql-prod"></a> [ADR-039](adr/039-dual-db-sqlite-dev-postgresql-prod.md)
<a id="adr-040--billing-adiado-para-pós-launch"></a> [ADR-040](adr/040-billing-adiado-para-pos-launch.md)
<a id="adr-041--traefik-como-reverse-proxy"></a> [ADR-041](adr/041-traefik-como-reverse-proxy.md)
<a id="adr-042--design-system-antes-da-fase-5"></a> [ADR-042](adr/042-design-system-antes-da-fase-5.md)
<a id="adr-043--shadcnui-como-component-library"></a> [ADR-043](adr/043-shadcnui-como-component-library.md)
<a id="adr-050--tailwind-v4-theme-inline"></a> [ADR-050](adr/050-tailwind-v4-theme-inline.md)
<a id="adr-051--geist-fonts"></a> [ADR-051](adr/051-geist-fonts.md)
<a id="adr-052--lucide-react-para-ícones"></a> [ADR-052](adr/052-lucide-react-para-icones.md)
<a id="adr-053--intl-nativo-para-datas"></a> [ADR-053](adr/053-intl-nativo-para-datas.md)
<a id="adr-054--migração-incremental-de-pages"></a> [ADR-054](adr/054-migracao-incremental-de-pages.md)
<a id="adr-044--transaction-explorer-como-core"></a> [ADR-044](adr/044-transaction-explorer-como-core.md)
<a id="adr-045--data-lineage-via-tooltip"></a> [ADR-045](adr/045-data-lineage-via-tooltip.md)
<a id="adr-046--responsivo-sem-pwa-obrigatório"></a> [ADR-046](adr/046-responsivo-sem-pwa-obrigatorio.md)
<a id="adr-047--category-override-em-vez-de-reconciliação-ui"></a> [ADR-047](adr/047-category-override-em-vez-de-reconciliacao-ui.md)
<a id="adr-007--fernet-app-level-para-criptografia"></a> [ADR-007](adr/007-fernet-app-level-para-criptografia.md)
<a id="adr-055--coverage-target-85-line--95-new-code"></a> [ADR-055](adr/055-coverage-target-85-line-95-new-code.md)
<a id="adr-056--rolling-restart-em-vez-de-blue-green"></a> [ADR-056](adr/056-rolling-restart-em-vez-de-blue-green.md)
<a id="adr-057--jwt-15min--refresh-7d"></a> [ADR-057](adr/057-jwt-15min-refresh-7d.md)
<a id="adr-058--vps-cx32-para-sizing"></a> [ADR-058](adr/058-vps-cx32-para-sizing.md)
<a id="adr-059--docker-image-cve-scan-no-ci"></a> [ADR-059](adr/059-docker-image-cve-scan-no-ci.md)
<a id="adr-060--fernet-dual-key-para-secret-rotation"></a> [ADR-060](adr/060-fernet-dual-key-para-secret-rotation.md)
<a id="adr-061--telemetria-privacy-first"></a> [ADR-061](adr/061-telemetria-privacy-first.md)
<a id="adr-062--frontend-testing-em-fase-dedicada-65"></a> [ADR-062](adr/062-frontend-testing-em-fase-dedicada-65.md)
<a id="adr-063--hardening-fintech-em-sub-fase-65d"></a> [ADR-063](adr/063-hardening-fintech-em-sub-fase-65d.md)
<a id="adr-064--backend-hardening-em-sub-fase-65e"></a> [ADR-064](adr/064-backend-hardening-em-sub-fase-65e.md)
<a id="adr-065--sub-fase-7e-operational-readiness"></a> [ADR-065](adr/065-sub-fase-7e-operational-readiness.md)
<a id="adr-066--auth-flows-completos-e-prompt-injection-em-7b-bloqueadores-de-beta"></a> [ADR-066](adr/066-auth-flows-completos-e-prompt-injection-em-7b.md)
<a id="adr-067--test-infrastructure-em-sub-fase-65f"></a> [ADR-067](adr/067-test-infrastructure-em-sub-fase-65f.md)
<a id="adr-068--códigos-internos-do-pipeline-nunca-vazam-na-ui"></a> [ADR-068](adr/068-codigos-internos-do-pipeline-nunca-vazam-na-ui.md)
<a id="adr-069--msw-sync-strategy-manual--lint-ci-não-codegen"></a> [ADR-069](adr/069-msw-sync-strategy-manual-lint-ci-nao-codegen.md)
<a id="adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in"></a> [ADR-070](adr/070-premium-llm-e2e-mock-default-nightly-real-opt-in.md)
<a id="adr-071--playwright-workspace-isolation-email-unique-por-worker"></a> [ADR-071](adr/071-playwright-workspace-isolation-email-unique-por.md)
<a id="adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família"></a> [ADR-072](adr/072-multi-tenancy-workspace-id-scoping-explicito.md)
<a id="adr-073--goals-como-entidade-versionada-não-config-estático"></a> [ADR-073](adr/073-goals-como-entidade-versionada-nao-config-estatico.md)
<a id="adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório"></a> [ADR-074](adr/074-tasks-como-entidade-de-1a-classe-fora-do-relatorio.md)
<a id="adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters"></a> [ADR-075](adr/075-cutover-cli-web-estrategia-de-transicao-faseada.md)
<a id="adr-076--design-tokens-unificados-site--relatório"></a> [ADR-076](adr/076-design-tokens-unificados-site-relatorio.md)
<a id="adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web"></a> [ADR-077](adr/077-pipeline-adapter-como-contrato-de-cutover-cli-web.md)
<a id="adr-078--render-nativo-react--e6-como-exportador-standalone"></a> [ADR-078](adr/078-render-nativo-react-e6-como-exportador-standalone.md)
<a id="adr-125--workspace-sharing-convites-viewer-role-forced-logout"></a> [ADR-125](adr/125-workspace-sharing-convites-viewer-role-forced.md)
<a id="adr-079--content-first-classification-no-upload-web"></a> [ADR-079](adr/079-content-first-classification-no-upload-web.md)
<a id="adr-080--pipeline-incremental-extrair-só-docs-novos-consolidar-full"></a> [ADR-080](adr/080-pipeline-incremental-extrair-so-docs-novos.md)
<a id="adr-126--multi-tenant-goals-completos-aporte_mensal-dolarizacao-alocacao_alvo"></a> [ADR-126](adr/126-multi-tenant-goals-completos-aporte-mensal.md)
<a id="adr-127--e1-members-persiste-via-artifactstore"></a> [ADR-127](adr/127-e1-members-persiste-via-artifactstore.md)
<a id="adr-081--classificação-de-documentos-unificada-p2"></a> [ADR-081](adr/081-classificacao-de-documentos-unificada-p2.md)
<a id="adr-082--pipelineartifact-artefatos-computacionais-no-banco"></a> [ADR-082](adr/082-pipelineartifact-artefatos-computacionais-no-banco.md)
<a id="adr-083--artifactstore-abstração-de-io-para-artefatos"></a> [ADR-083](adr/083-artifactstore-abstracao-de-io-para-artefatos.md)
<a id="adr-084--content-addressed-uploads"></a> [ADR-084](adr/084-content-addressed-uploads.md)
<a id="adr-085--eliminar-materialização-de-config-em-disco"></a> [ADR-085](adr/085-eliminar-materializacao-de-config-em-disco.md)
<a id="adr-086--materializationbridge-adapter-temporário"></a> [ADR-086](adr/086-materializationbridge-adapter-temporario.md)
<a id="adr-087--stagespec-dependências-declarativas"></a> [ADR-087](adr/087-stagespec-dependencias-declarativas.md)
<a id="adr-088--stageconfig-configuração-imutável-por-parâmetro"></a> [ADR-088](adr/088-stageconfig-configuracao-imutavel-por-parametro.md)
<a id="adr-089--pipelinedomain-camada-de-domínio-isolada-de-io"></a> [ADR-089](adr/089-pipelinedomain-camada-de-dominio-isolada-de-io.md)
<a id="adr-090--decimal-para-valores-monetários"></a> [ADR-090](adr/090-decimal-money.md)
<a id="adr-091--pydantic-para-domain-objects-com-coleções"></a> [ADR-091](adr/091-pydantic-para-domain-objects-com-colecoes.md)
<a id="adr-092--renomear-scripts-para-nomes-descritivos-de-domínio"></a> [ADR-092](adr/092-renomear-scripts-para-nomes-descritivos-de-dominio.md)
<a id="adr-093--rename-completo-de-identificadores-de-stage-opção-a"></a> [ADR-093](adr/093-rename-completo-de-identificadores-de-stage.md)
<a id="adr-094--report-single-active-vs-versionado"></a> [ADR-094](adr/094-report-single-active-vs-versionado.md)
<a id="adr-095--segurança-de-content_json-lgpd"></a> [ADR-095](adr/095-seguranca-de-content-json-lgpd.md)
<a id="adr-096--observabilidade-de-cutover"></a> [ADR-096](adr/096-observabilidade-de-cutover.md)
<a id="adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy"></a> [ADR-097](adr/097-extract-then-refactor-estrategia-de-decomposicao.md)
<a id="adr-098--caminho-b-pragmático-vs-puro-nomenclatura-oficial"></a> [ADR-098](adr/098-caminho-b-pragmatico-vs-puro-nomenclatura-oficial.md)
<a id="adr-099--reuse-de-analyze_-legadas-em-main_with_store-decisão-de-a5da5e"></a> [ADR-099](adr/099-reuse-de-analyze-legadas-em-main-with-store.md)
<a id="adr-100--a6d-commitment-fechar-caminho-b-puro-nos-5-stages-pragmáticos"></a> [ADR-100](adr/100-a6d-commitment-fechar-caminho-b-puro-nos-5.md)
<a id="adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e"></a> [ADR-101](adr/101-principios-r12-r17-dddsolid-no-backend-api-a6e.md)
<a id="adr-102--princípios-r18-r20-language-neutral-boundaries-a6f"></a> [ADR-102](adr/102-principios-r18-r20-language-neutral-boundaries-a6f.md)
<a id="adr-103--teste-manual-como-gate-antes-de-remoção-do-bridge-a6b5--a6-human"></a> [ADR-103](adr/103-teste-manual-como-gate-antes-de-remocao-do.md)
<a id="adr-104--e15c-em-caminho-b-pragmático-sessão-a5f"></a> [ADR-104](adr/104-e15c-em-caminho-b-pragmatico-sessao-a5f.md)
<a id="adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a"></a> [ADR-105](adr/105-llm-stages-escrevem-via-artifactstore-e1-e-e7.md)
<a id="adr-106--opt-in-db-artifacts-por-workspace--dbartifactstore-no-celery-task-a6b"></a> [ADR-106](adr/106-opt-in-db-artifacts-por-workspace.md)
<a id="adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2"></a> [ADR-107](adr/107-remocao-de-materializationbridge-e-stage-runner.md)
<a id="adr-108--estratégia-de-subdomínios-mathomsai--cloudflare-dns"></a> [ADR-108](adr/108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md)
<a id="adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a"></a> [ADR-109](adr/109-auth-portability-jwt-hs256-fernet-documentados.md)
<a id="adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3"></a> [ADR-110](adr/110-structured-json-logging-opentelemetry-bootstrap.md)
<a id="adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6"></a> [ADR-111](adr/111-stateless-rigoroso-padrao-e-gate-empirico-a6f6.md)
<a id="adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1"></a> [ADR-112](adr/112-pipeline-as-service-http-boundary-para-execucao.md)
<a id="adr-113--convenções-go-golangciyml--ci--skeleton-a6g7"></a> [ADR-113](adr/113-convencoes-go-golangciyml-ci-skeleton-a6g7.md)
<a id="adr-114--enforcement-automatizado-de-code-style-gates-imediatos--progressivos-a6g6"></a> [ADR-114](adr/114-enforcement-automatizado-de-code-style-gates.md)
<a id="adr-115--domain-events-tipados-arquitetura-e-boundaries-a6eevents"></a> [ADR-115](adr/115-domain-events-tipados-arquitetura-e-boundaries.md)
<a id="adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local"></a> [ADR-116](adr/116-f7f-local-stack-next-separada-anonimizacao.md)
<a id="adr-118--flip-do-default-mathoms_use_db_artifacts-para-true"></a> [ADR-118](adr/118-flip-do-default-mathoms-use-db-artifacts-para-true.md)
<a id="adr-119--contrato-livestep-para-progresso-de-etapas-do-pipeline"></a> [ADR-119](adr/119-contrato-livestep-para-progresso-de-etapas-do.md)
<a id="adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco"></a> [ADR-120](adr/120-readers-user-facing-consultam-artifactstore-db.md)
<a id="adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml"></a> [ADR-117](adr/117-report-premium-ui-baseline-paridade-com-exemplo.md)
<a id="adr-121--typography-base-13px-com-override-configurável"></a> [ADR-121](adr/121-typography-base-13px-com-override-configuravel.md)
<a id="adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm"></a> [ADR-122](adr/122-chart-conclusions-e-section-summaries-em-modo.md)
<a id="adr-123--notas-t6-e-kanban-t3-persistidos-no-backend"></a> [ADR-123](adr/123-notas-t6-e-kanban-t3-persistidos-no-backend.md)
<a id="adr-124--scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next"></a> [ADR-124](adr/124-scriptse6-renderpy-aposentado-em-favor-de-ssr.md)
<a id="adr-128--e7-review-llm-lêescreve-via-artifactstore"></a> [ADR-128](adr/128-e7-review-llm-leescreve-via-artifactstore.md)
<a id="adr-129--descontinuação-completa-do-renderer-html-server-side"></a> [ADR-129](adr/129-descontinuacao-completa-do-renderer-html-server.md)
<a id="adr-130--internacionalização-com-next-intl--persistência-em-userslocale"></a> [ADR-130](adr/130-internacionalizacao-com-next-intl-persistencia.md)
<a id="adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path"></a> [ADR-131](adr/131-report-referencia-pipeline-artifact-por-fk-drop.md)
<a id="adr-132--lifecycle-scoping-de-pipeline_artifacts-workspace-vs-run"></a> [ADR-132](adr/132-lifecycle-scoping-de-pipeline-artifacts.md)
<a id="adr-133--transferencias_internas-modelado-em-transfer_configs-workspace-scoped"></a> [ADR-133](adr/133-transferencias-internas-modelado-em-transfer.md)
<a id="adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend"></a> [ADR-134](adr/134-configstore-protocolo-de-leitura-tipado-pipeline.md)
<a id="adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio"></a> [ADR-135](adr/135-versionamento-temporal-de-series-fiscais-e-cambio.md)
<a id="adr-136--decision-aggregate-event-sourced-com-supersede-chain"></a> [ADR-136](adr/136-decision-aggregate-event-sourced-com-supersede.md)
<a id="adr-137--catalog--override-resolver-para-categorization-e-institutions"></a> [ADR-137](adr/137-catalog-override-resolver-para-categorization-e.md)
<a id="adr-138--protocolo-de-supervisão-cto-para-sprint-a7"></a> [ADR-138](adr/138-protocolo-de-supervisao-cto-para-sprint-a7.md)
<a id="adr-139--finalização-migração-rechartschartjs-em-reports"></a> [ADR-139](adr/139-finalizacao-migracao-rechartschartjs-em-reports.md)
<a id="adr-140--goal-if-schema-v2-renda-passiva-atual--if-meta-líquida"></a> [ADR-140](adr/140-goal-if-schema-v2-renda-passiva-atual-if-meta.md)
<a id="adr-141--goal-alocação-alvo-schema-v2-7-classes-auvp"></a> [ADR-141](adr/141-goal-alocacao-alvo-schema-v2-7-classes-auvp.md)
<a id="adr-142--toggle-imoveis_no_if-em-pipelinejson--invariante-anti-dupla-contagem"></a> [ADR-142](adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md)
<a id="adr-143--docsmethodology-é-rules-as-code-sprint-a76"></a> [ADR-143](adr/143-docsmethodology-e-rules-as-code-sprint-a76.md)
<a id="adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29"></a> [ADR-144](adr/144-section-summaries-llm-driven-em-e5-com-cache.md)
<a id="adr-145--7-categorias-canonical-da-composição-patrimonial"></a> [ADR-145](adr/145-7-categorias-canonical-da-composicao-patrimonial.md)
<a id="adr-146--e3-source-hierarchy--bankaccountsource_tier-schema"></a> [ADR-146](adr/146-e3-source-hierarchy-bankaccountsource-tier-schema.md)
<a id="adr-147--milhas-valuation-methodology-universal--storage-workspace-scoped"></a> [ADR-147](adr/147-milhas-valuation-methodology-universal-storage.md)
<a id="adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório"></a> [ADR-148](adr/148-snapshotchangelogbuilder-comparacoes-mes-a-mes.md)
<a id="adr-149--configreport_layoutyaml-permanece-como-asset-de-produto-sprint-a80"></a> [ADR-149](adr/149-configreport-layoutyaml-permanece-como-asset-de.md)
<a id="adr-150--estratégia-de-port-go-do-pipeline-service-caminho-1-shell-only-via-subprocess-como-default-deferido-para-roadmap"></a> [ADR-150](adr/150-estrategia-de-port-go-do-pipeline-service.md)
<a id="adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces"></a> [ADR-151](adr/151-remocao-do-modo-tatico-do-relatorio-direcao-e-do.md)
<a id="adr-152--plano-de-acao-renomeada-para-acao-com-tabs-direção-e--onda-6"></a> [ADR-152](adr/152-plano-de-acao-renomeada-para-acao-com-tabs.md)
<a id="adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples"></a> [ADR-153](adr/153-suggestion-aggregate-direcao-e-onda-5-proposal.md)
<a id="adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1"></a> [ADR-154](adr/154-fusao-kanbanitem-em-task-migracao-reportnotes.md)
<a id="adr-155--dashboard-absorvido-por-plano-direção-e-consolidação"></a> [ADR-155](adr/155-dashboard-absorvido-por-plano-direcao-e.md)
<a id="adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7"></a> [ADR-156](adr/156-patrimonio-em-plano-e-single-source-via.md)
<a id="adr-157--schema-irpf-completo-stage-extract_irpf_full"></a> [ADR-157](adr/157-schema-irpf-completo-stage-extract-irpf-full.md)
<a id="adr-158--pipeline-review-screen--ui-dedicada-para-aprovareditar-stagereview"></a> [ADR-158](adr/158-pipeline-review-screen-ui-dedicada-para.md)
<a id="adr-159--aggregator-banking-br-open-finance--adiar-adoção-até-gatilhos-materializarem"></a> [ADR-159](adr/159-aggregator-banking-br-open-finance-adiar-adocao.md)
<a id="adr-160--eficiência-tributária-imóvel-direto-vs-fii-no-relatório-premium-roadmap"></a> [ADR-160](adr/160-eficiencia-tributaria-imovel-direto-vs-fii-no.md)
<a id="adr-161--regras-canônicas-de-suggestion-v2-cerbasiauvpperini-completos"></a> [ADR-161](adr/161-regras-canonicas-de-suggestion-v2.md)
<a id="adr-162--decisions-como-event-projection-sobre-goals"></a> [ADR-162](adr/162-decisions-como-event-projection-sobre-goals.md)
<a id="adr-163--decision-congela-context_snapshot-ao-aceitar-suggestion"></a> [ADR-163](adr/163-decision-congela-context-snapshot-ao-aceitar.md)
<a id="adr-164--carteira-de-renda-e-taxa-de-retirada-efetiva"></a> [ADR-164](adr/164-carteira-de-renda-e-taxa-de-retirada-efetiva.md)
<a id="adr-165--validationissue-estruturado-em-validationresult-e-stagereview"></a> [ADR-165](adr/165-validationissue-estruturado-em-validationresult.md)
<a id="adr-166--schema-estável-cenarios_conjuge-no-payload-e5"></a> [ADR-166](adr/166-schema-estavel-cenarios-conjuge-no-payload-e5.md)
<a id="adr-167--eligibility-gate-de-cenário-do-cônjuge-no-domain-service"></a> [ADR-167](adr/167-eligibility-gate-de-cenario-do-conjuge-no-domain.md)
<a id="adr-168--remoção-do-modo-usa-do-relatório"></a> [ADR-168](adr/168-remocao-do-modo-usa-do-relatorio.md)
<a id="adr-169--modo-incremental-estendido-aos-stages-globais-e1"></a> [ADR-169](adr/169-modo-incremental-estendido-aos-stages-globais-e1.md)
<a id="adr-170--refresh-tokens-com-httponly-cookie-e-family-based-revocation"></a> [ADR-170](adr/170-refresh-tokens-com-httponly-cookie-e-family.md)
<a id="adr-171--fernet-rotation-operacionalizada-via-multifernet"></a> [ADR-171](adr/171-fernet-rotation-operacionalizada-via-multifernet.md)
<a id="adr-172--stuck-runs-detector-via-heartbeat--celery-beat"></a> [ADR-172](adr/172-stuck-runs-detector-via-heartbeat-celery-beat.md)
<a id="adr-173--llm-budget-hard-stop--llmcalllog-populada-universal"></a> [ADR-173](adr/173-llm-budget-hard-stop-llmcalllog-populada-universal.md)
<a id="adr-174--off-site-backup-criptografado-em-cloudflare-r2--restore-drill"></a> [ADR-174](adr/174-off-site-backup-criptografado-em-cloudflare-r2.md)
<a id="adr-175--prompt-injection-defense-em-camadas-sanitize--system-clause--pydantic-strict"></a> [ADR-175](adr/175-prompt-injection-defense-em-camadas-sanitize.md)
<a id="adr-176--chave-estável-cenarios_conjuge-no-bloco-de-narrativas-e5n"></a> [ADR-176](adr/176-chave-estavel-cenarios-conjuge-no-bloco-de.md)
<a id="adr-177--thresholds-e-referências-metodológicas-como-código-rules-as-code-consolidation-goalsjson"></a> [ADR-177](adr/177-thresholds-e-referencias-metodologicas-como.md)
<a id="adr-178--risk-aggregate-workspace-scoped"></a> [ADR-178](adr/178-risk-aggregate-workspace-scoped.md)
<a id="adr-179--decision-aggregate--extensão-de-schema-impact_1y10y-horizon-priority"></a> [ADR-179](adr/179-decision-aggregate-extensao-de-schema-impact.md)
<a id="adr-180--goalsjson-cutover-final-via-stageconfigconfig_store-extendido"></a> [ADR-180](adr/180-goalsjson-cutover-final-via-stageconfigconfig.md)
<a id="adr-181--goalsjson-removido-de-_archive-e-adicionado-a-devcheck_forbidden_pathspy"></a> [ADR-181](adr/181-goalsjson-removido-de-archive-e-adicionado-a.md)
<a id="adr-182--vault-de-documentação-operacional-obsidian-friendly-em-docs"></a> [ADR-182](adr/182-vault-de-documentacao-operacional-obsidian.md)
<a id="adr-192--protection-aggregate--protectionbundle-seção-9-riscos-e-proteção"></a> [ADR-192](adr/192-protection-aggregate-protectionbundle-secao-9.md)
