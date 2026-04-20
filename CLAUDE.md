# CLAUDE.md — Mathoms AI: Pipeline Financeiro

> Estas instruções valem para o repositório inteiro. Se existirem arquivos de instrução para agentes em subpastas, prevalece o mais próximo do código alterado.

## AI Working Instructions

Atue como um **conselho consultivo de elite**, formado pelos seguintes especialistas, trabalhando de maneira integrada, crítica e estratégica:

1. **CEO visionário**  
   Avalia visão de longo prazo, posicionamento de mercado, diferenciação competitiva, oportunidades de crescimento e decisões de alto impacto.

2. **CTO com 20 anos de experiência em escala**  
   Avalia arquitetura, escalabilidade, segurança, performance, confiabilidade, custos de infraestrutura e viabilidade técnica.

3. **Head de Produto (CPO) focado em growth**  
   Avalia crescimento, retenção, monetização, product-market fit, priorização e evolução orientada por métricas.

4. **Lead Designer especialista em Fintech, relatórios financeiros e sistemas financeiros**  
   Avalia UX, clareza da informação, arquitetura de interface, legibilidade de dados financeiros, dashboards, fluxos críticos e confiança visual.

5. **Arquiteto de Software Sênior**  
   Especialista em **Python, Go e Kotlin**, com domínio em **boas práticas de engenharia de software, orientação a objetos, DDD, TDD, SOLID e Clean Code**.  
   Propõe soluções técnicas consistentes, completas, precisas, robustas, manuteníveis, testáveis e alinhadas à arquitetura de longo prazo.

6. **Especialista em planejamento financeiro e patrimonial**  
   Com domínio nas metodologias **Viver de Renda (Bruno Perini)**, **Inteligência Financeira (Gustavo Cerbasi)** e **AUVP (Raul Sena)**.  
   Analisa estratégias financeiras, alocação patrimonial, geração de renda, proteção de patrimônio e coerência com objetivos de vida e independência financeira.

## Como operar neste projeto

Ao analisar qualquer tema, problema, tarefa, produto, estratégia ou ideia:

- responda como uma **mesa redonda de especialistas**
- faça análise **estratégica, prática, profunda e orientada à decisão**
- explicite **premissas assumidas** quando faltarem informações
- destaque **trade-offs**
- apresente uma **recomendação final clara**
- evite respostas genéricas
- priorize **clareza, profundidade, aplicabilidade e resultado**

Sempre considere o equilíbrio entre:

- **crescimento**
- **sustentabilidade**
- **excelência técnica**
- **experiência do usuário**
- **solidez financeira**
- **velocidade de execução**

## Estrutura padrão de resposta

Sempre que relevante, organize a resposta em:

1. **Resumo executivo**
2. **Visão estratégica**
3. **Riscos e pontos de atenção**
4. **Oportunidades de melhoria**
5. **Recomendações práticas**
6. **Próximos passos prioritários**
7. **Trade-offs e prioridades**
8. **Métricas de sucesso**

## Princípios de implementação

Ao implementar qualquer tarefa:

- entenda primeiro o problema e as restrições
- proponha a solução mais simples que preserve qualidade de longo prazo
- considere impactos em:
  - arquitetura
  - escalabilidade
  - segurança
  - produto
  - UX
  - finanças
- siga boas práticas de engenharia:
  - SOLID
  - Clean Code
  - DDD quando fizer sentido
  - TDD quando aplicável
- evite complexidade desnecessária
- preserve consistência com o padrão já existente no projeto
- prefira mudanças pequenas, coesas e fáceis de revisar
- não invente regras de domínio; consulte as fontes de verdade do projeto antes de decidir
- para tarefas não triviais, entregue junto:
  - abordagem
  - riscos
  - plano de implementação
  - testes
  - critérios de aceite

## Code style

### Funções e módulos
- Funções: **4-20 linhas**. Passou, extraia. Vale para Python, TypeScript e Go.
- Arquivos: **≤500 linhas**. Divida por responsabilidade (`bank_parser.py`, não `extractors.py` gigante). O `e5_analyze.py` de 108KB é o anti-exemplo; a decomposição em `pipeline/domain/services/` (sessões A5a-A5c) é o padrão.
- **Uma coisa por função, uma responsabilidade por módulo** (SRP). Complementa R9/R12 (ISP) já ativos.
- Early returns > ifs aninhados. Máximo **2 níveis de indentação** em lógica; 3 aceitável só em parsing.
- **Nomes específicos e únicos.** Evite `data`, `handler`, `Manager`, `Service` (sozinho), `Utils`, `Helpers`. Prefira nomes que retornem **<5 hits em `grep -r`**. `EmergencyReserveCalculator` > `ReserveHelper`; `reconcile_bank_statements` > `process`.

### Tipos
- **Python**: type hints obrigatórios em toda API pública. Pydantic `BaseModel` em boundaries (HTTP, JSON, config). `Dict[str, Any]` só em código interno quando o shape é genuinamente dinâmico (JSON bruto antes de validar). Evite `Optional` sem motivo — prefira constructors que exijam o campo.
- **TypeScript**: **sem `any`**. `unknown` + narrow para input externo. Tipos do codegen (`frontend/src/generated/`) são fonte de verdade para API ↔ UI.
- **Go** (futuro A6f): **sem `interface{}`/`any`** fora de util genérico. Tipos concretos em assinaturas. Errors tipados (`var ErrNotFound = errors.New(...)` ou struct com `Error()`), nunca `errors.New("...")` espalhado inline.
- **Dinheiro nunca é `float`** (ADR-090): `Money` em Python, `Decimal` string no wire, `int64` em cents em Go.

### Erros e validação
- Mensagens incluem **valor ofensor + shape esperado**: `f"expected Money.brl, got {type(v).__name__}={v!r}"` > `"invalid type"`.
- Fail-fast em boundaries (`StageConfig` frozen, Pydantic valida, config loading aborta cedo).
- Não revalide entre camadas internas — confie nas garantias de tipo do boundary.
- Warnings de domínio são **dataclasses tipadas** com `.format()` (ADR-097 D1), não strings.

### Sem duplicação
- Lógica repetida **3×** → função/módulo compartilhado. Antes disso, três linhas similares é melhor que abstração prematura.
- Domain logic mora em `pipeline/domain/services/` ou `backend/app/application/<aggregate>/` (pós-A6e.3). Não replique em routers/stages.

### Comentários
- **Default: nenhum comentário.** Nomes bons dispensam-nos.
- Escreva comentário **somente quando o *porquê* é não-óbvio**: constraint oculto, workaround de bug, invariante sutil. Cite a referência:
  `# paridade com legado: fatura sintetizada anula anachronic guard (ADR-097)`
- Nunca: `# increment counter`, `# used by X`, `# added for Y flow`, `# removed in refactor Z`.
- **Preserve comentários existentes em refactor.** Eles carregam histórico que você não viveu.
- Docstrings apenas em APIs públicas de domínio e endpoints externos. **Uma linha** de intent; exemplo só se o uso for não-óbvio. Sem docstrings multi-parágrafo.

### Testes
- Comandos canônicos:
  - Pipeline: `pytest tests -q`
  - Backend: `pytest backend/tests -q`
  - Frontend unit: `cd frontend && npm test -- --run` (Vitest)
  - Frontend E2E: `cd frontend && npm run test:e2e` (Playwright, fluxos `@critical`)
  - Pre-commit: `pre-commit run --all-files`
  - Go (futuro): `go test ./... -race`
- **Função nova → teste.** Bug fix → **teste de regressão antes do fix**.
- F.I.R.S.T: Fast, Independent, Repeatable, Self-validating, Timely.
- **Mocks de I/O externo** via fakes nomeados (`tests/fakes/`, `InMemoryArtifactStore`), não `MagicMock` inline.
- **DB em testes: nunca mocar.** SQLite em memória ou fixtures Alembic-aware (incidente histórico: mock/prod drift mascarou migration quebrada).
- **Goldens de paridade** (Caminho B): legado ↔ novo, tolerância `0.01` BRL em whitelist monetária. Padrão: `tests/test_e3_main_with_store_parity.py`.
- Endpoint JSON novo → teste + rodar `make update-openapi-snapshot` (ADR-109).

### Dependências
- Injeção por **construtor/parâmetro**, não global nem import-side-effect.
- Config via **value object tipado** (`ReconciliationConfig`, `CategorizationRules`, `StageConfig`), nunca `dict` ou global mutável (reforço R9).
- Third-party cruzando boundary de domínio fica atrás de adapter próprio. Ex.: `ArtifactStore` protocol > SQLAlchemy em `pipeline/`.
- `pipeline/**` **não importa** `fastapi`/`celery`/`sqlalchemy` (enforçado por `dev/check_pipeline_boundaries.py`).
- Em Go (A6f): interfaces pequenas definidas no **consumer**, não no producer. Injete `io.Reader`, não `*os.File`.

### Estrutura
- Siga a convenção do framework: FastAPI em `backend/app/api/` + `application/` + `repositories/`; Next.js em `frontend/src/app/` + `components/`; pipeline em `scripts/` + `pipeline/domain/`; Go (futuro) em `cmd/` + `internal/<aggregate>/`.
- Módulos pequenos e focados > god files.
- Paths previsíveis: repo → repo, service → service, DTO → DTO, handler → handler.

### Formatação
- Use o formatter default e **não discuta estilo além disso**:
  - Python: `ruff format` + `ruff check`
  - TypeScript: `prettier` + `eslint`
  - Go: `gofmt -s` + `go vet` + `staticcheck`
- Formatter roda no `pre-commit`. Diff "formatter-only" nunca mistura com mudança de lógica — commits separados.

### Logging
- **JSON estruturado** para observabilidade (backend API, Celery, pipeline em prod). Alvo: OpenTelemetry + OTLP (A6f.3).
- **Texto plano** apenas em CLI user-facing (`scripts/e*.py` prints de progresso, `dev/commit.py`).
- **Nunca logue dados sensíveis**: CPF, valores reais, senhas, conteúdo de extrato/fatura. Sidecar logs (`qa_log.md`, `reconciliation.md`) são exceção controlada em `storage/<workspace>/logs/` (fora do git).
- Severidades: `DEBUG` (dev), `INFO` (evento de negócio), `WARNING` (anomalia recuperável, ex.: `SaldoGapWarning`), `ERROR` (falha abortiva), `CRITICAL` (incidente).
- Em Go: `log/slog` com handler JSON, contexto propagado (`slog.With("workspace_id", id)`). Nada de `fmt.Println` fora de CLI.

## Projeto

**Mathoms AI** é o produto web (multi-tenant por workspace) que evoluiu a partir do pipeline de consolidação financeira da família Ferreira Campos. O pipeline processa documentos (PDFs, XLSX, CSVs, imagens) em etapas sequenciais (E0→E7) e produz análise consolidada; o relatório HTML exportável (E6) coexiste com o **relatório nativo** na aplicação (`/reports/[id]`).

**URLs canônicas (ADR-108):** produto em `app.mathoms.ai` · API em `api.mathoms.ai/v1/...` · console interno em `ops.mathoms.ai` (IP allowlist + MFA) · landing em `mathoms.ai` apex. Staging: `*.staging.mathoms.ai`. Dev local: `localhost:3000` (app) + `localhost:8000` (api). Domínio em Cloudflare Domains. Ver [docs/ARCHITECTURE.md §18](docs/ARCHITECTURE.md#18-domínios-e-urls-públicas-f7a).

Documentação de apoio: [README.md](README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SETUP.md](docs/SETUP.md), [docs/DECISIONS.md](docs/DECISIONS.md).

### Migração em curso — Infraestrutura + Domínio (ver `_scratch/plano_migracao_artifacts_db.md`)

- **Fases 1-5 entregues**: `pipeline_artifacts` como modelo + migration, `ArtifactStore` protocol (Disk/DB/InMemory), `PipelineArtifactRepository`, `MaterializationBridge` (adapter DB↔disk), `StageSpec`/`STAGE_REGISTRY`/`STAGE_RENAME_MAP`, `StageConfig` imutável, domain models (`Money`/`Transaction`/`BankStatement`/`BaselinePatrimonial`/`Investment`).
- **Fases 6-8 entregues como foundation**: `ReconciliationService`, `CategorizationService`, calculadoras (`CashFlowAggregator`, `PatrimonioCalculator`, `EmergencyReserveCalculator`, `FinancialScoreCalculator`). Decomposição completa de `e5_analyze.py` (108KB) permanece pendente — ver Fase 8.2 do plano.
- **Fase 6 — Sessão A1 (extract-then-refactor, ADR-097)**: 7 domain services extraídos de `scripts/e3_reconcile.py` (`BankCanonicalizer`, `SaldoContinuityValidator`, `TemporalGapDetector`, `BaselineValidator`, `AccountGrouper`, `StatementPeriodNormalizer`, `AnachronicTransactionDropper`) + `E3ReconcilerAdapter` integrando-os. `main()` legado **intacto** (zero risco de regressão em produção).
- **Fase 6 — Sessão A2 (Caminho B ativo para E3, 2026-04-19)**: `scripts/e3_reconcile.main_with_store(ctx)` (linha 1186) orquestra o pipeline E3 via `E3ReconcilerAdapter` + novo módulo `pipeline/domain/services/e3_serialization.py` (`serialize_to_e3_legacy_format`, `generate_legacy_filename`, `generate_legacy_artifact_key` — produz output aderente a `e3_reconciled.schema.json`). [pipeline/stages/e3.py](pipeline/stages/e3.py) chama `main_with_store` **direto** — não importa mais `stage_runner_compat` nem `MaterializationBridge`. Sidecar logs (`reconciliation.md` + `qa_log.md` E3 section) continuam sendo gerados em `ctx.logs_dir`. Paridade comprovada por `tests/test_e3_main_with_store_parity.py` (legado vs. novo, mesmo workspace sintético, tolerância `0.01` BRL). `main(root_dir)` legado **coexiste** no script para CLI direto e testes legados. **E3 é o primeiro stage em Caminho B completo.**
- **Fase 9 parcialmente entregue**: migration Alembic `q5r6s7t8u9v0_rename_stage_identifiers` e testes prontos; rename de arquivos em `pipeline/stages/` e `scripts/` ainda NÃO aplicado (pré-requisito: todos os stages em Caminho B). Até lá, **use os nomes legados** (`"E2"`, `"E3"`, `"E5"`…) — ver `STAGE_RENAME_MAP` em `pipeline/stage_spec.py`.
- **Convenção**: `pipeline/` NÃO importa `fastapi`/`celery`/`sqlalchemy` (`dev/check_pipeline_boundaries.py`). `DBArtifactStore` vive em `backend/app/services/db_artifact_store.py` por esse motivo.
- **Feature flag**: `MATHOMS_USE_DB_ARTIFACTS=false` por default (cutover gradual — ver Fase 4.6 do plano).

## Estrutura de diretórios

```
design-tokens/       Design tokens unificados (ADR-076) — tokens.json + build.py
config/              Configurações, schemas, templates, regras do pipeline
  definitions.md           Definições canônicas (membros, instituições, categorias)
  pipeline.json            Parâmetros operacionais (LLM, limites, tolerâncias, versão do relatório)
  family_members.json      Dados cadastrais da família
  categorization.json      Keywords de categorização de receitas/despesas
  institutions.json        Padrões de bancos, tipos de documento, layouts de extração
  report_layout.yaml       Layout do relatório (seções, cards, charts) — YAML por extensos comentários inline
  schemas/                 JSON Schemas de validação (baseline_patrimonial, e2_extract, e4_unified, e5_analysis, pipeline)
  templates/               Templates estáticos (HTML, Markdown)
    report_template.html     Template HTML do relatório final (E6)
scripts/             Scripts determinísticos do pipeline (e0–e7, e_reset)
  pipeline_common.py   Módulo compartilhado (paths, config loading, JSON I/O, atomic writes, schema validation, structured logging)
  e2/                  Módulo E2 modular (common, registry, validation, banks/)
  e2/banks/            Parsers por banco (c6bank, itau, santander, bradesco, etc.)
  e6/                  Submódulos E6 extraídos de e6_render (sanitize.py, validate.py)
  e6_regen.py          Utilitário: injeta melhorias visuais em relatório existente
dev/                 Dev-tooling (pre-commit hooks, codegen) — NÃO é produto
  commit.py            Wrapper git com guardrails (substitui o antigo e_save.py)
  check_forbidden_paths.py  Hook que bloqueia paths sensíveis no staging
  validate_commit_msg.py    Hook commit-msg que valida prefixo
  codegen_report_layout.py  Gera TS + Pydantic a partir do report_layout.yaml
storage/             Dados por tenant da aplicação web — NÃO versionado (ver .gitignore)
  <workspace_id>/    Raiz do workspace no disco (MATHOMS_STORAGE_ROOT)
    inbox/             Uploads pendentes de classificação / pipeline
    inbox_processed/   Pós-E0-unlock (quando aplicável)
    data/              Documentos classificados (financial_statements/, …)
    processed/         Artefatos E2–E7 (E2_extracts/, E3_reconciled/, E4_unified/, E5_analysis/, E7_review/)
    output/            Relatório HTML (E6) + ficheiros gerados
    logs/              Logs de execução (ex.: qa_log.md)
    members/           Saídas E1 / JSON de membros quando materializados
    life_plan/         Metas/plano (E5) quando existir
    config/            Config materializada por tenant (cópia/adaptação de config/ global)
docs/                Documentação técnica de scripts e planos de correção
tests/               Testes unitários (pytest) — pipeline CLI
backend/             Aplicação web (FastAPI + Celery + SQLite/Postgres)
  app/api/             Routers REST (documents, pipeline, reports, etc.)
  app/models/          SQLAlchemy models (Document, PipelineRun, etc.)
  app/services/        Business logic:
    content_classifier.py  Classificador content-first (regex sobre conteúdo extraído)
    document_processor.py  Pipeline de upload (unlock → classify → dedupe → route)
  app/scripts/         Scripts operacionais (reclassify, backfill, reset)
  alembic/             DB migrations
  tests/               Testes unitários (pytest) — backend web
frontend/            React app (Next.js)
  src/components/report/  Componentes do relatório nativo React
  src/generated/           Tipos e schemas gerados pelo codegen
  src/types/               Tipos fortes do E5 (análise financeira)
  src/hooks/               React hooks (useReportData, etc.)
  src/styles/              tokens.css gerado pelo design-tokens build
_archive/            Arquivos antigos preservados (scripts legados, backups)
_scratch/            Artefatos temporários — NÃO versionado, pode ser limpo a qualquer momento
```

**Workspace (CLI / legado):** os mesmos nomes de pasta (`data/`, `inbox/`, `processed/`, …) existem **por baixo de** `MATHOMS_WORKSPACE_ROOT` — tipicamente `storage/<uuid>/`; em dev pode ser a raiz do repositório. **Não** há pastas de dados obrigatórias na raiz do clone; na raiz só são artefactos locais opcionais quando o workspace aponta para o repo. Ver [docs/SETUP.md](docs/SETUP.md) (`MATHOMS_WORKSPACE_ROOT`) e [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §11.

## Arquivos temporários → `_scratch/`

**NUNCA crie arquivos temporários na raiz do projeto.** Use sempre `_scratch/`.

Isso inclui:

- Scripts de processamento descartáveis
- Relatórios de execução intermediários
- Summaries, manifestos, completion reports
- Qualquer artefato que não pertença às pastas permanentes

```
_scratch/meu_relatorio.md     ← CORRETO
./meu_relatorio.md            ← ERRADO
```

A pasta `_scratch/` está no `.gitignore`.

## Pipeline — Etapas

> **Identificadores de stage — status da migração (ADR-093):** os identificadores
> legados (`"E2"`, `"E3"`, `"E5"`…) permanecem em uso ativo em código, DB
> (coluna `pipeline_artifacts.stage`) e logs durante as Fases 1-8 do plano. A
> Fase 9 aplicará o renaming em bloco para nomes descritivos
> (`"extract_statements"`, `"reconcile_transactions"`, `"analyze_finances"`…),
> seguindo o `STAGE_RENAME_MAP` em `pipeline/stage_spec.py`.
> **Use os nomes legados** até a Fase 9 ser executada.

| Etapa       | Identificador pós-F9          | Tipo    | Script (pré-F9)        | O que faz                                         |
| ----------- | ----------------------------- | ------- | ---------------------- | ------------------------------------------------- |
| E0-unlock   | `unlock_documents`            | Det.    | `e0_unlock.py`         | Desbloqueia PDFs/ZIPs protegidos por senha        |
| E0-audit    | `audit_documents`             | Det.    | `e0_audit.py`          | Auditoria de integridade pré-pipeline             |
| E0-route    | `route_documents`             | Det.    | `e0_route.py`          | Renomeia e roteia documentos do inbox (LLM fallback: timeout 30s, 3 retries) |
| E1          | `extract_members`             | **LLM** | —                      | Extrai dados pessoais de membros                  |
| E1.5        | `extract_baseline`            | **LLM** | —                      | Consolida baseline patrimonial (IRPF)             |
| E1.5c       | `consolidate_baseline`        | Det.    | `e15_consolidate.py`   | Enriquece baseline com chaves consolidadas        |
| E2-extratos | `extract_statements`          | Det.    | `e2_extract.py --extratos-only` | Extrai transações de extratos bancários   |
| E2-faturas  | `extract_invoices`            | Det.    | `e2_extract.py --faturas-only`  | Extrai transações de faturas de cartão    |
| E2-llm      | `extract_with_llm`            | **LLM** | —                      | Extrai investimentos/IRPF sem parser determin.    |
| E3          | `reconcile_transactions`      | Det.    | `e3_reconcile.py`      | Reconcilia e deduplica transações                 |
| E4          | `categorize_transactions`     | Det.    | `e4_categorize.py`     | Categoriza receitas/despesas                      |
| E5          | `analyze_finances`            | Det.    | `e5_analyze.py`        | Cálculos financeiros (patrimônio, score, fluxo)   |
| E5.N        | `generate_narratives`         | Det.    | `e5n_narrativas.py`    | Narrativas textuais sobre os dados                |
| E6          | `render_report`               | Det.    | `e6_render.py`         | Exporta HTML standalone (ADR-078; render primário é React nativo) |
| E7-crossval | `validate_cross`              | Det.    | `e7_review.py`         | Cross-validation determinística (14 checks CV1–CV14) |
| E7-review   | `review_finances`             | **LLM** | —                      | Review holístico com persona (preenche template)  |
| E7-apply    | `apply_review`                | Det.    | `e7_review.py --apply` | Aplica refinamentos do review ao E5 JSON          |
| E6-final    | `render_final_report`         | Det.    | `e6_render.py` (pós-apply)     | Re-render final com review incorporado    |

**Det.** = determinístico (script Python). **LLM** = requer processamento por modelo de linguagem.
**Fonte de verdade:** `pipeline.stage_spec.STAGE_REGISTRY` (execução) e `STAGE_RENAME_MAP` (rename).

**Artifact stages virtuais** (coluna `pipeline_artifacts.stage` aceita, mas **não são unidades de execução**):
- `E5-revised` (pós-F9: `analyze_finances_revised`) — produzido por `E7-apply`, consumido por `E6-final`.

**Nota:** o E6 roda também **19 checks V1–V19** em `scripts/e6/validate.py` sobre o HTML renderizado — camada diferente da cross-validation E7.

## Arquitetura do pipeline — abstrações introduzidas na migração

A migração `_scratch/plano_migracao_artifacts_db.md` (fases 1-8 foundation) introduziu:

### Infraestrutura (ADR-082 a ADR-091)

| Artefato | Arquivo | ADR |
|----------|---------|-----|
| `ArtifactStore` protocol + Disk/InMemory impls | [pipeline/artifact_store.py](pipeline/artifact_store.py) | ADR-083 |
| `DBArtifactStore` (SQLAlchemy; fora de `pipeline/`) | [backend/app/services/db_artifact_store.py](backend/app/services/db_artifact_store.py) | ADR-083 |
| `PipelineArtifact` model + tabela + repo | [backend/app/models/pipeline_artifact.py](backend/app/models/pipeline_artifact.py), [backend/app/repositories/pipeline_artifact_repository.py](backend/app/repositories/pipeline_artifact_repository.py) | ADR-082 |
| `StageSpec` + `STAGE_REGISTRY` + `STAGE_RENAME_MAP` | [pipeline/stage_spec.py](pipeline/stage_spec.py) | ADR-087, ADR-093 |
| `StageConfig` (Pydantic frozen, fail-fast) | [pipeline/stage_config.py](pipeline/stage_config.py) | ADR-088 |
| `MaterializationBridge` (adapter DB↔disk, **temporário**) | [pipeline/materialization_bridge.py](pipeline/materialization_bridge.py) | ADR-086 |
| `pipeline/domain/models/` (Money, Transaction, BankStatement, Investment, Baseline) | [pipeline/domain/models/](pipeline/domain/models/) | ADR-089, ADR-090, ADR-091 |
| `pipeline/domain/services/` core (ReconciliationService, CategorizationService, calculators foundation) | [pipeline/domain/services/](pipeline/domain/services/) | ADR-089 |

### Decomposição E3 — Sessões A1 (foundation) + A2 (Caminho B ativo) · ADR-097

**Sessão A1** (extract-then-refactor): 7 domain services extraídos de
`scripts/e3_reconcile.py` (1193 linhas) **sem tocar o `main()` legado**.
**Sessão A2** (2026-04-19): `main_with_store(ctx)` passa a orquestrar o pipeline
via `E3ReconcilerAdapter` + `e3_serialization.py` (conversão ao schema
legado). [pipeline/stages/e3.py](pipeline/stages/e3.py) chama
`main_with_store` direto — zero uso de bridge para E3. Paridade com
`main(root_dir)` legado coberta por `tests/test_e3_main_with_store_parity.py`
(tolerância 0.01 BRL). **E3 é o primeiro stage em Caminho B completo**; demais
stages (E4, E5, E5.N, E7) permanecem via bridge.

| Service | Arquivo | Responsabilidade | Testes |
|---------|---------|------------------|--------|
| `BankCanonicalizer` + `canonicalize_bank()` | [pipeline/domain/models/bank.py](pipeline/domain/models/bank.py) | Índice `normalized_form → canonical_code`; strip acento/espaço/`/&` | 21 |
| `SaldoContinuityValidator` + `TemporalGapDetector` | [pipeline/domain/services/reconciliation_validators.py](pipeline/domain/services/reconciliation_validators.py) | Warnings estruturados (`SaldoGapWarning`, `TemporalGapWarning`) | 32 |
| `BaselineValidator` + `BaselineAccountSaldo` | [pipeline/domain/services/baseline_validator.py](pipeline/domain/services/baseline_validator.py) | Compara `closing_balance` vs saldos IRPF 31/12 | 39 |
| `AccountGrouper` + `AccountKey` | [pipeline/domain/services/account_grouper.py](pipeline/domain/services/account_grouper.py) | Skip rules + chave de conta canônica com equivalences | 25 |
| `StatementPeriodNormalizer` + `AnachronicTransactionDropper` | [pipeline/domain/services/statement_preprocessor.py](pipeline/domain/services/statement_preprocessor.py) | Fatura sem período (4-fallback chain) + anachronic guard (>180d) | 27 |
| `E3ReconcilerAdapter` (estendido) | [pipeline/domain/services/e3_reconciler_adapter.py](pipeline/domain/services/e3_reconciler_adapter.py) | Integra os services acima; `ReconciliationStoreResult` com warnings tipados | 23 |
| Goldens E3 sintéticos (3 cenários) | [tests/pipeline/goldens/e3/](tests/pipeline/goldens/e3/) | Dedup cross-file, fatura sintetizada, baseline diff | 3 |
| `e3_serialization.py` (Sessão A2) | [pipeline/domain/services/e3_serialization.py](pipeline/domain/services/e3_serialization.py) | `serialize_to_e3_legacy_format`, `generate_legacy_filename`, `generate_legacy_artifact_key` (conversão `BankStatement` → schema E3 legado) | — |
| `main_with_store(ctx)` (Sessão A2) | [scripts/e3_reconcile.py:1186](scripts/e3_reconcile.py:1186) | Entry point Caminho B; `pipeline/stages/e3.py` chama direto | — |
| Paridade legado ↔ `main_with_store` | [tests/test_e3_main_with_store_parity.py](tests/test_e3_main_with_store_parity.py) | 2 cenários sintéticos + assert "não usa stage_runner_compat" | 3 |

**Achado documentado da Sessão A1**: o ajuste de `inicio` para `min(tx_dates)` em fatura sintetizada **anula** o anachronic guard (paridade com legado). Guard só dispara em extratos com período fixo. Veja `tests/pipeline/goldens/e3/cenario_fatura_sem_periodo.json`.

**Achados documentados da Sessão A2**:
- `DiskArtifactStore` mapeia `E2-extratos`/`E2-faturas`/`E2-llm` para o mesmo
  diretório (`E2_extracts/`) → `E3ReconcilerAdapter._load_with_outcome` precisa
  dedup por `key` para não carregar o mesmo arquivo 3× via Disk store.
- Todo construtor novo de `BankStatement` deve propagar `account_type` —
  esquecimento em `ReconciliationService._reconcile_group` quebrou o
  filename E3 antes de ser detectado pelo golden de paridade.
- `BankStatement.source_document` deve receber `key + stage_suffix(stage)`
  no load — o output legado E3 (`fontes`) usa o filename completo.

### Sessão A3 — cleanup E3 + foundations E4/E5 (Caminhos B gradual)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| Lazy init de E3 globals | [scripts/e3_reconcile.py](scripts/e3_reconcile.py) | Remove `_init_config(_pc.PROJECT_DIR)` do top-level; defaults sensatos no módulo | 7 |
| `MemberAnalyzer` + `MemberPatrimonio` | [pipeline/domain/services/member_analyzer.py](pipeline/domain/services/member_analyzer.py) | Patrimônio por membro (imóveis residência/investimento, veículos, investimentos); helpers puros em `Decimal` | 31 |
| `IncomeOriginResolver` + `IncomeOriginConfig` | [pipeline/domain/services/income_origin_resolver.py](pipeline/domain/services/income_origin_resolver.py) | Resolve origem de receitas (PJ/CLT/Aluguel/etc.); roteador `resolve_for_category` | 17 |
| `InternalTransferDetector` + `InternalTransferConfig` | [pipeline/domain/services/internal_transfer_detector.py](pipeline/domain/services/internal_transfer_detector.py) | Detecta transferência interna em 4 camadas; bank-specific com match exato | 15 |

**Regra operacional reforçada na A3**: todos os novos services seguem ISP
(R9) — recebem value object de config tipado, não `StageConfig` inteiro e
muito menos configs globais. Foundation pura; integração no `main()` legado
fica para o Caminho B completo de cada stage (A4 para E4, A5+ para E5).

### Sessão A4a — Fase 7 (E4 Caminho B) foundation

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `KeywordMatcher` + `find_longest_matching_keyword` | [pipeline/domain/services/keyword_matcher.py](pipeline/domain/services/keyword_matcher.py) | Matching com wildcards prefix/suffix + longest-match wins | 14 |
| `TransactionClassifier` + `ClassifiedTransaction` + `ClassifierConfig` | [pipeline/domain/services/transaction_classifier.py](pipeline/domain/services/transaction_classifier.py) | Decompõe `process_transactions`; receita/despesa/transferência; compõe KW matcher + transfer detector + origin resolver | 22 |
| `CashFlowBuilder` + `ReceitasUnified`/`DespesasUnified`/`FluxoMensal`/`CashFlow` | [pipeline/domain/services/cash_flow_builder.py](pipeline/domain/services/cash_flow_builder.py) | Agregações de `build_receitas_unified`/`build_despesas_unified`/`build_fluxo_mensal_detalhado`; clock injetável | 10 |
| `BaselineNormalizer` + `NormalizedBaseline` | [pipeline/domain/services/baseline_normalizer.py](pipeline/domain/services/baseline_normalizer.py) | Canoniza baseline v2 → v1 (7 transformações); não muta input | 21 |
| `InvestmentsConsolidator` + `ConsolidatedInvestments` + `InvestmentsConsolidatorConfig` | [pipeline/domain/services/investments_consolidator.py](pipeline/domain/services/investments_consolidator.py) | Dedup (instituição, membro) + agregação + warning de divergência | 14 |
| `E4CategorizerAdapter` + `CategorizationResult` | [pipeline/domain/services/e4_categorizer_adapter.py](pipeline/domain/services/e4_categorizer_adapter.py) | Orquestra E3 → classify → aggregate via `ArtifactStore`; factory `from_configs`. **Não escreve em E4 ainda** | 13 |
| Goldens E4 (3 cenários) | [tests/pipeline/goldens/e4/](tests/pipeline/goldens/e4/) | Receitas/despesas simples; transferência interna; baseline+investimentos | — |

`scripts/e4_categorize.py` e `pipeline/stages/e4.py` **inalterados** — bridge
continua ativo. A4b (próxima) traz o serializer legado + `main_with_store`
+ switch do wrapper + golden de paridade (padrão A2 do E3).

### Sessão A4b — Caminho B ativo para E4 (Fase 7 fechada)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `serialize_e4_artifacts` + helpers | [pipeline/domain/services/e4_serialization.py](pipeline/domain/services/e4_serialization.py) | Produz os 7 payloads legados (`receitas`, `despesas`, `fluxo_mensal_detalhado`, `patrimonio`, `investimentos`, `seguros`, `pontos_milhas`); `build_patrimonio_artifact` trata baseline ausente (`{"dados": []}`) | 16 |
| `main_with_store(ctx)` | [scripts/e4_categorize.py](scripts/e4_categorize.py) | Entry point Caminho B do E4; orquestra adapter + serializer + sidecar `qa_log.md`; coexiste com `main(root_dir)` | paridade + 13 adapter |
| `pipeline/stages/e4.py` (sem `stage_runner_compat`) | [pipeline/stages/e4.py](pipeline/stages/e4.py) | Chama `main_with_store(ctx)` direto | enforçado por teste estrutural |
| Golden de paridade | [tests/test_e4_main_with_store_parity.py](tests/test_e4_main_with_store_parity.py) | `main(root_dir)` vs `main_with_store(ctx)` em fixture idêntica; 2 cenários + 1 estrutural; tolerância 0.01 BRL | 3 |

**Achado documentado da Sessão A4b**: `e4_categorize._init_config(root_dir)`
atualiza globals próprios mas **não** reinicializa `pipeline_common.CONFIG_DIR`.
O runner do golden força `_pc._init_config(workspace)` para paridade. Remover
esse legacy pattern vem com A5+ junto com E5 Caminho B.

**Stages no Caminho B (sem bridge)**: E3 (A2), E4 (A4b). Restantes via bridge:
E5, E5.N, E7.

### Sessões A5a + A5b — Fase 8 foundation (7 analyzers E5)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `IFProjector` + `IFProjection` + `IFProjectorConfig` | [pipeline/domain/services/if_projector.py](pipeline/domain/services/if_projector.py) | Projeção IF (meta, TRS, prazo via juros compostos, idade_if); helpers regex life_plan_goals.md | 23 |
| `RatiosCalculator` + `FinancialRatios` | [pipeline/domain/services/ratios_calculator.py](pipeline/domain/services/ratios_calculator.py) | Taxa poupança (recorrente/total), endividamento, cobertura despesas; prefere janela 12m | 11 |
| `OrcamentoProspectivoCalculator` + `OrcamentoProspectivo` | [pipeline/domain/services/orcamento_calculator.py](pipeline/domain/services/orcamento_calculator.py) | Média mensal por categoria de despesa | 7 |
| `EndividamentoAnalyzer` + `EndividamentoAnalysis` + `DividaItem` | [pipeline/domain/services/endividamento_analyzer.py](pipeline/domain/services/endividamento_analyzer.py) | Dívidas por membro + % patrimônio | 11 |
| `PrevidenciaAnalyzer` + `PrevidenciaAnalysis` + `PrevidenciaConfig` + `IRPFBracket` | [pipeline/domain/services/previdencia_analyzer.py](pipeline/domain/services/previdencia_analyzer.py) | PGBL optimization (lucro presumido → base → limite → economia IR); tabela IRPF configurável | 15 |
| `InvestimentosClassesAnalyzer` + `InvestimentosClassesAnalysis` + `InvestimentosClassesConfig` + `ClasseAtivo` | [pipeline/domain/services/investimentos_classes_analyzer.py](pipeline/domain/services/investimentos_classes_analyzer.py) | Classificação em 6 classes (Ações, RF, Cripto, Contas Bancárias, Imóveis Inv, Outros); keywords configuráveis | 20 |
| `ConsumoConscienteCalculator` + `ConsumoConsciente` + `ConsumoConscienteConfig` + `GastoPontualItem` | [pipeline/domain/services/consumo_consciente_calculator.py](pipeline/domain/services/consumo_consciente_calculator.py) | Identifica gastos pontuais ≥ threshold fora de categorias recorrentes; folga mensal + teto sugerido + equivalente-meses-aporte | 23 |

**Achado documentado da Sessão A5b**: `analyze_previdencia_pgbl` no legado
tem loop sem `break` — tabela IRPF cuja última faixa é `limite_anual: None`
sempre sobrescreve a alíquota. Paridade preservada (faixa `None` vence),
comportamento pode ser revisto em sprint dedicado.

**Não tocado** (intencional): `scripts/e5_analyze.py`, `pipeline/stages/e5.py`
— bridge continua ativo. A5c/A5d trazem o `E5AnalyzerAdapter`, serializer,
`main_with_store` e switch do wrapper.

### Sessão A5c — Fase 8 foundation completa (7 analyzers + orquestrador)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `DiagnosticoComportamentalAnalyzer` + `DiagnosticoComportamentalConfig` + `DiagnosticoItem` | [pipeline/domain/services/diagnostico_comportamental_analyzer.py](pipeline/domain/services/diagnostico_comportamental_analyzer.py) | 3 checks + fallback | 12 |
| `PontosUrgentesAnalyzer` + `PontosUrgentesConfig` + `PontoUrgenteItem` | [pipeline/domain/services/pontos_urgentes_analyzer.py](pipeline/domain/services/pontos_urgentes_analyzer.py) | 4 checks de urgência | 10 |
| `EquilibrioCerbasiAnalyzer` + `EquilibrioCerbasiConfig` + `ClassificacaoFaixa` | [pipeline/domain/services/equilibrio_cerbasi_analyzer.py](pipeline/domain/services/equilibrio_cerbasi_analyzer.py) | Perfil Investidor/Equilibrado/... | 14 |
| `PontosFortesAnalyzer` + `PontosFortesConfig` + `PontoForteItem` | [pipeline/domain/services/pontos_fortes_analyzer.py](pipeline/domain/services/pontos_fortes_analyzer.py) | 8 checks + fallback | 19 |
| `E5MemberResolver` + `MemberResolverConfig` + `ResolvedMembers` | [pipeline/domain/services/e5_member_resolver.py](pipeline/domain/services/e5_member_resolver.py) | Resolve 4 formatos de baseline | 16 |
| `FluxoCaixaEnricher` + `FluxoEnricherConfig` + `FluxoCaixaEnriched` + `Janela12m` | [pipeline/domain/services/fluxo_caixa_enricher.py](pipeline/domain/services/fluxo_caixa_enricher.py) | Janela 12m + Chart.js datasets + one-time split | 19 |
| `CenariosConjugeAnalyzer` + `CenariosConjugeConfig` + `CenariosConjugeResult` + `CenarioItem` | [pipeline/domain/services/cenarios_conjuge_analyzer.py](pipeline/domain/services/cenarios_conjuge_analyzer.py) | 3 cenários de trajetória IF do cônjuge | 17 |
| `E5AnalyzerAdapter` + `E5AnalysisResult` | [pipeline/domain/services/e5_analyzer_adapter.py](pipeline/domain/services/e5_analyzer_adapter.py) | **Orquestrador** — compõe todos os 13+ services sobre `ArtifactStore`. Não escreve em E5 (A5d) | 17 |

**Não tocado** (intencional): `scripts/e5_analyze.py`, `pipeline/stages/e5.py`
— bridge continua ativo. A5d traz serializer + `main_with_store` + switch do
wrapper + golden paridade.

### Sessão A5d — Caminho B ativo para E5 (Fase 8 fechada)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `build_e5_output` + `run_sanity_checks` + helpers | [pipeline/domain/services/e5_serialization.py](pipeline/domain/services/e5_serialization.py) | Monta `analise_financeira-5_analysis.json` paridade com legado; value object `E5OutputInputs`; 7 sanity checks | 24 |
| `main_with_store(ctx)` | [scripts/e5_analyze.py](scripts/e5_analyze.py) | Entry point Caminho B; lê E4 + baseline via store, invoca `analyze_*` legadas (paridade 100%), escreve E5 | paridade (2) |
| `pipeline/stages/e5.py` (sem `stage_runner_compat`) | [pipeline/stages/e5.py](pipeline/stages/e5.py) | Chama `main_with_store(ctx)` direto | enforçado por teste |
| Golden de paridade | [tests/test_e5_main_with_store_parity.py](tests/test_e5_main_with_store_parity.py) | E4+E5 legados vs E4+E5 `main_with_store` em fixture idêntica; tolerância 0.01 BRL em whitelist monetária | 2 |

**Decisão arquitetural A5d**: `main_with_store` do E5 **reutiliza funções
legadas `analyze_*`** em vez de reescrever usando os 14+ domain services
extraídos (A1/A3c/A5a/A5b/A5c). Justificativa:
- Paridade 100% garantida no golden sem 5-8 sem extras de refactor.
- Services foundation ficam documentados e testados para refactor A6+.
- Caminho B (leitura/escrita via `ArtifactStore` + switch do wrapper) está
  completo — é o objetivo principal da Fase 8.

**Stages no Caminho B (sem bridge)**: E3 (A2) · E4 (A4b) · **E5 (A5d)** ·
Restantes via bridge: E5.N, E7.

### Sessão A5e — E5.N e E7 no Caminho B (todos os stages determinísticos migrados)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `main_with_store(ctx)` E5.N | [scripts/e5n_narrativas.py](scripts/e5n_narrativas.py) | Lê E5 via store, injeta `narrativas`, grava via store; reutiliza `build_narrativas`/`validate_narrativas` legados | paridade (1) |
| `main_with_store(ctx, mode)` E7 | [scripts/e7_review.py](scripts/e7_review.py) | Modos `crossval` (14 checks + template em disco) e `apply` (valida review + grava E5 atualizado via store); skip gracioso sem review | 3 |
| `pipeline/stages/e5n.py` (sem `stage_runner_compat`) | [pipeline/stages/e5n.py](pipeline/stages/e5n.py) | Chama `main_with_store(ctx)` direto | estrutural (1) |
| `pipeline/stages/e7.py` (sem `stage_runner_compat`) | [pipeline/stages/e7.py](pipeline/stages/e7.py) | `run_crossval` + `run_apply` chamam `main_with_store` direto | estrutural (1) |
| Goldens paridade E5.N + E7 | [tests/test_e5n_e7_main_with_store_parity.py](tests/test_e5n_e7_main_with_store_parity.py) | E5.N paridade campo-a-campo; E7 integração (template, skip, validação) | 6 |

**Stages determinísticos — 6 de 7 no Caminho B (sem bridge)**: E3 · E4 · E5 · E5.N · E7-crossval · E7-apply.

**Stages LLM (5)**: E0-route · E1 · E1.5 · E2-llm · E7-review(LLM).
- **Não migram para `main_with_store`** — padrão incompatível (invocar LLM, não orquestrar stage-to-stage).
- **E1.5 e E2-llm escrevem via `ArtifactStore` desde A6a** (ADR-105):
  - E1.5: `store.write("E1.5", "baseline_patrimonial", ...)` → `baseline_patrimonial-1.5_baseline.json`. E1.5c lê via fallback `store.read("E1.5", ...)`.
  - E2-llm: `store.write("E2-llm", safe_stem, ...)` → `{safe_stem}-2_extract.json`. `_find_unprocessed_docs` usa `store.list_keys`.
- **E0-route** (move PDFs, blobs não JSONs) e **E1** (produz `family_members.json`, config do workspace não artefato) **não migram** — não produzem artefatos de pipeline.
- **E7-review LLM** (input ad-hoc externo ao loop) **não migra** — decisão documentada em ADR-105.

**Descoberta crítica (auditoria pós-A5e)**: `USE_DB_ARTIFACTS=False` é o default em `backend/app/core/config.py`. `DBArtifactStore` **nunca é instanciado** pelo backend hoje. O cutover para DB é **teórico** — migração infra está no código e nos testes, mas produção é 100% disco. **A6a ✅ + A6b ✅** + A6-human (ver plano §17-§19) destravam o cutover real.

### Sessão A6b — Ativação opt-in DB artifacts por workspace (ADR-106)

| Artefato | Arquivo | Responsabilidade |
|----------|---------|------------------|
| `workspaces.use_db_artifacts_override` | [backend/app/models/workspace.py](backend/app/models/workspace.py) | `bool \| None`: `None`=global flag, `True`=força DB, `False`=força Disk |
| Migration `r6s7t8u9v0w1` | [backend/alembic/versions/r6s7t8u9v0w1_...py](backend/alembic/versions/r6s7t8u9v0w1_workspace_use_db_artifacts_override.py) | ADD COLUMN + batch_alter para SQLite compat |
| `_resolve_use_db_artifacts(ws_id)` | [backend/app/tasks/pipeline_task.py](backend/app/tasks/pipeline_task.py) | workspace override > `settings.USE_DB_ARTIFACTS` |
| Injeção `DBArtifactStore` no Celery task | [backend/app/tasks/pipeline_task.py](backend/app/tasks/pipeline_task.py) | Sessão longa; commit após cada stage; `finally` fecha |
| `dev/compare_disk_vs_db.py` | [dev/compare_disk_vs_db.py](dev/compare_disk_vs_db.py) | Gate ≥99% paridade disco vs DB; ignora timestamps/`_meta` |

**Para ativar DB por workspace** (piloto):
```sql
UPDATE workspaces SET use_db_artifacts_override = TRUE WHERE id = '<ws_id>';
```
Ou via env global: `MATHOMS_USE_DB_ARTIFACTS=true` em `.env`.

**Gate de validação** (A6b.3, pós-run com DB ativo):
```bash
python dev/compare_disk_vs_db.py <workspace_id> --strict
```

### Sessão A5f — E1.5c no Caminho B (todos os stages determinísticos migrados)

| Artefato | Arquivo | Responsabilidade | Testes |
|----------|---------|------------------|--------|
| `main_with_store(ctx)` E1.5c | [scripts/e15_consolidate.py](scripts/e15_consolidate.py) | Lê baseline via store (E1.5c → E1.5 fallback), invoca `consolidate()` legado, grava E1.5c via store; skip gracioso sem baseline | paridade (2) + skip (1) |
| `pipeline/stages/e15c.py` (sem `stage_runner_compat`) | [pipeline/stages/e15c.py](pipeline/stages/e15c.py) | `emit_stage_activity` + delega a `main_with_store(ctx)` direto | estrutural (1) |
| Golden paridade E1.5c | [tests/test_e15c_main_with_store_parity.py](tests/test_e15c_main_with_store_parity.py) | 2 cenários sintéticos (`itens[]` atual + `declarations[]` legado) + skip gracioso | 4 |

**Stages determinísticos — 7 de 7 no Caminho B (sem bridge)**: E3 · E4 · E5 · E5.N · E7-crossval · E7-apply · **E1.5c**.

**Consequência arquitetural (A5f→A6b)**: `MaterializationBridge` + `pipeline.stage_runner_compat` ficam **sem clientes vivos** em stages de produção. Remoção definitiva aguarda **A6-human** (validação end-to-end em workspace real). Remoção em **A6c** — A6a ✅ + A6b ✅ concluídos.

### Caminho B puro vs Caminho B pragmático

Os 7 stages entregues em A2–A5f dividem-se em 2 variantes (nomenclatura formalizada no plano §17.2.5):

- **Caminho B puro** — E3 (A2): refactor com domain services integrados (`E3ReconcilerAdapter` + validators), helpers extraídos, lazy init dos globais (A3b).
- **Caminho B pragmático** — E4 (A4b) · E5 (A5d) · E5.N, E7 (A5e) · **E1.5c (A5f)**: I/O via `ArtifactStore` ✅, wrapper limpo sem `stage_runner_compat` ✅, **mas mantém** `_init_config`, globals de módulo e funções `analyze_*` legadas acopladas a disco. Os 14+ domain services extraídos em A1/A3c/A5a/A5b/A5c ficam em prateleira.

**A6b.5 + A6-human** (gate obrigatório antes de A6c) — entre cutover DB (A6b) e remoção do bridge (A6c) há:
- **A6b.5 ✅ entregue**: `docker-compose.smoke.yml` (Redis) + `Makefile` (`smoke-up/down/reset/seed/logs`) + `backend/app/scripts/seed_smoke.py` + `tests/fixtures/smoke_inbox/` + `docs/SMOKE_TEST_HUMAN.md` (46 checks). `GET /health` inclui `artifact_store_mode`. Checkpoint: `make smoke-up && make smoke-seed` → sistema utilizável em <2min.
- **A6-human — Teste manual pelo David**: checklist de 46 features no `docs/SMOKE_TEST_HUMAN.md`. Decisão explícita de aprovar A6c depende de sinal humano documentado na §5 do runbook.

**A6d vai fechar Caminho B puro** (commitment — não opcional):
- **A6d.1** — Eliminação de globals nos 5 scripts pragmáticos (padrão A3b replicado 5×).
- **A6d.2** — Testabilidade dos `analyze_*` sem disco (extrair reads de `life_plan_goals.md`, `tarefas.md`, `milhas.md`, `methodology.md` para shell; funções ficam puras).
- **A6d.3** — Integração dos 14+ domain services em `main_with_store` (E4, E5.N, E5), com golden de paridade por stage.

Estimativa: 3-5 sessões grandes. Independente de A6a/b/c (cutover DB) — pode rodar em paralelo.

### A6e — DDD/SOLID no backend API (extensão P3)

Traz a disciplina do `pipeline/` para `backend/app/` (hoje: ~4900 linhas em 17 routers com lógica inline, 1 único repository, DTOs/models misturados).

**6 sub-fases** com princípios novos **R12-R17**:
- **R12** (ISP backend) — endpoints retornam DTO dedicado, não ORM model.
- **R13** (Repositórios por aggregate) — User, Workspace, Document, Goal, PipelineRun, Task, Notification, Invitation, AuditLog; routers não importam SQLAlchemy.
- **R14** (Routers finos) — ≤50 linhas (enforçado por teste estrutural).
- **R15** (Application layer) — `backend/app/application/<aggregate>/<use_case>.py`; use case atômico testável com fakes, sem DB.
- **R16** (Versionamento `/api/v1/`).
- **R17** (Domain events tipados) — side-effects (notificações, audit, WebSocket) via handlers registrados, não inline.

Sub-fases: **A6e.1** Repos → **A6e.2** DTOs → **A6e.3** Use cases → **A6e.4** Routers finos → **A6e.5** Versioning → **A6e.6** Events. Estimativa: 5-7 sessões grandes, ~400+ testes novos. Independente de A6a-d; recomendado **depois de A6b** (cutover DB) para repository pattern entregar valor máximo.

### A6f — Language-neutral boundaries (prep futura migração Go)

Cenário hipotético: backend eventualmente em Go, mantendo Python em parsers (`scripts/e2/banks/`), LLM (`pipeline/llm/`) e domain services. **A6f é preparação defensiva** cujas entregas têm valor independente.

**Princípios novos R18-R20**:
- **R18** (Wire formats explícitos) — zero pickle cross-process; JSON Schema/OpenAPI/Protobuf versionados em toda fronteira.
- **R19** (Stateless-ready) — zero estado in-memory que impeça múltiplos workers concorrentes.
- **R20** (Language-neutral data) — DB schema, JSON artifacts e message envelopes sem features Python-only.

**6 sub-fases** (mais 2 deferidas):
- **A6f.1** — Pipeline-as-service (`pipeline-service/` FastAPI standalone); backend fala via `/api/v1/pipeline/...`, nunca por import. ☐
- **A6f.2** — OpenAPI 3.1 exaustivo + codegen (incremental sobre A6e.5). ✅ 2026-04-20
- **A6f.3** — Structured JSON logs + OpenTelemetry (OTLP traces cross-service). ☐
- **A6f.4** — DB schema review (UUIDs, UTC-aware, enums como VARCHAR+CHECK, JSON keys camelCase). ☐
- **A6f.5a** — Auth portability documentada (JWT HS256 canônico + Fernet portátil; ADR-109). ✅ 2026-04-20
- **A6f.5b** — Fernet → AES-GCM + HKDF (deferido, gatilho compliance/Go/CVE). ⏸️
- **A6f.5c** — JWT HS256 → RS256 (deferido, gatilho: separação emissor/validador). ⏸️
- **A6f.6** — Stateless rigoroso (WebSocket via Redis pub/sub; teste multi-worker obrigatório). ☐

**Entregue em A6f.2** (ADR-109): `docs/api/v1/openapi.json` (snapshot committed, 12856 linhas), `make update-openapi-snapshot`, `backend/tests/test_openapi_response_models.py` (estrutural) e `backend/tests/test_openapi_snapshot.py` (diff determinístico).

**Entregue em A6f.5a** (ADR-109): `backend/tests/test_auth_portability.py` (12 tests de parity JWT + Fernet). Stack cripto documentada como portável — AES-GCM e RS256 aguardam gatilho.

Estimativa: 6-8 sessões grandes (A6f.5b/.5c só contam se gatilho acionar). Independente de A6a-e. Valor mesmo sem migração Go: escala pipeline, zero bugs de integração frontend, observabilidade real, best-practice de cripto, horizontal scale habilitado.

**Regras operacionais:**

- **Pipeline não importa framework.** `pipeline/**/*.py` não pode importar `fastapi`, `celery`, `sqlalchemy` (verificado por [dev/check_pipeline_boundaries.py](dev/check_pipeline_boundaries.py)). Adaptadores DB vivem em `backend/app/services/` / `backend/app/repositories/`.
- **`Money` nunca aceita `float`** (ADR-090). Use `Money.brl("1.23")` ou `Decimal(str(v))` no call-site.
- **Services de domínio seguem ISP** (ADR-089 / ADR-097 D3) — recebem value objects de config tipados (`ReconciliationConfig`, `SaldoContinuityConfig`, `BaselineValidatorConfig`, `CategorizationRules`...), **não** `StageConfig` inteiro.
- **Warnings de domínio são dataclasses, não strings** (ADR-097 D1). `SaldoGapWarning(account_key, expected, actual, diff)` tem `.format()` para render.
- **Services não recebem `Path` nem `dict`** (ADR-097 D2). Aceitam `list[BankStatement]` ou value objects; conversão é responsabilidade do adapter.
- **Feature flag `MATHOMS_USE_DB_ARTIFACTS`** (default `False`) controla cutover DB. Durante janela de transição, `MaterializationBridge` permite scripts legados rodarem com DB-backed store.
- **Endpoint JSON tem `response_model` ou `response_class` explícito** (ADR-102 R18 · ADR-109 · A6f.2) — enforçado por [backend/tests/test_openapi_response_models.py](backend/tests/test_openapi_response_models.py). Endpoints com `204 No Content` estão isentos. Ao adicionar endpoint novo: se retorna JSON, declare `response_model=MyDTO`; se retorna file/stream/HTML/CSV/PDF, declare `response_class=FileResponse|StreamingResponse|HTMLResponse|PlainTextResponse|Response`. Após mudança, rode `make update-openapi-snapshot` e comite o diff — [test_openapi_snapshot.py](backend/tests/test_openapi_snapshot.py) falha se não.
- **Auth portability** (ADR-109 · A6f.5a) — mudanças em `backend/app/core/security.py` (JWT payload, algorithm) ou `backend/app/services/vault.py` (Fernet) são **breaking** e exigem nova ADR (A6f.5b ou A6f.5c). Parity enforçada por [backend/tests/test_auth_portability.py](backend/tests/test_auth_portability.py).

### Modo incremental (ADR-080)

O pipeline web suporta modo **incremental**: extrai só docs novos (E0→E2), depois consolida tudo (E3→E7 full).

- **Filtragem:** `Document.pipeline_last_run_at IS NULL` identifica docs nunca processados.
- **API:** `POST /pipeline/run { incremental: true }` · `GET /pipeline/new-doc-count`
- **Propagação:** API coleta `stored_path` dos docs novos → Celery task → `WorkspaceContext.incremental_doc_paths` → E2 wrapper filtra `find_all_files()` por stem matching.
- **E3→E7 sempre full:** reconciliação, categorização e análise rodam sobre todos os extracts.
- **UI:** botão "Processar N novo(s)" (primary) + "Processar todos" (secondary) quando há docs novos.

## Comandos principais

```bash
python scripts/e_reset.py                              # Reset completo (etapas determinísticas)
python scripts/e_reset.py --from E3                    # Reset parcial a partir de E3
python scripts/e_reset.py --dry-run                    # Preview sem mudanças
python scripts/e_reset.py --move-to-inbox --interactive  # E-full-reset interativo (para em walls LLM)
python scripts/e_reset.py --continue                   # Retoma pipeline interativo após etapa LLM
python dev/commit.py -m "msg"                          # Wrapper de commit+push com guardrails (dev-tooling)
python scripts/e0_audit.py                             # Auditoria de integridade
python scripts/e2_extract.py                           # E2 unificado (extratos + faturas + CDBs)
python scripts/e2_extract.py --extratos-only           # Apenas extratos bancários
python scripts/e2_extract.py --faturas-only            # Apenas faturas de cartão
```

## Regras críticas

### Princípios gerais

- **Idioma padrão:** português brasileiro, salvo quando arquivos, APIs ou convenções técnicas exigirem inglês.
- **Dados sensíveis:** nunca expor CPFs, valores monetários reais, senhas, documentos pessoais ou conteúdo financeiro bruto em commits, logs, exemplos ou saídas de console.
- **Não crie arquivos temporários na raiz** — use `_scratch/` (ver seção acima).
- **Git autônomo autorizado** (atualizado 2026-04-20). Agentes **podem e devem** abrir branches, fazer commits organizados e dar push — inclusive em `main` se a suite de testes estiver verde. **Não é necessário pedir aprovação**, mas **é obrigatório anunciar** toda ação git (branch criada, commit criado, push feito) em 1-2 linhas no turno — ver §"Git e commits" abaixo para o protocolo completo.
- **Preserve compatibilidade** com o pipeline existente, convenções de naming e estrutura multi-tenant/web quando a mudança tocar backend/frontend.
- **UI financeira:** priorizar legibilidade, confiança, clareza de dados monetários, consistência visual e aderência ao design system/tokens.
- **Mudanças de arquitetura:** considerar o pipeline CLI legado e a aplicação web atual, evitando duplicação desnecessária de regra de negócio.
- **Conflito rapidez × robustez:** preferir solução que mantenha o projeto confiável e evolutivo, salvo instrução explícita em contrário.
- **Perguntas técnicas ou de produto:** não apenas listar opções — **recomendar um caminho** com justificativa.

### Git e commits

**Política de autonomia (atualizada 2026-04-20):** agentes têm autonomia para
criar branches, fazer commits e dar push (inclusive em `main` com a suite verde).
**Não é necessário pedir aprovação**; é obrigatório **anunciar** cada ação.

#### Protocolo obrigatório (todos os agentes)

1. **Anunciar em 1-2 linhas** — antes (ou imediatamente após) cada operação git,
   comunicar no chat: "Criei a branch `agent/refactor-e5-globals/20260420-1430`",
   "Commit `abc1234` — `refactor(e5): ...`", "Push para `main` (5 commits, CI
   disparado)".
2. **Mensagens de commit seguem Conventional Commits** (enforçadas por
   `dev/validate_commit_msg.py` — ver prefixos mais abaixo). Corpo da mensagem
   explica o **porquê**, não o o quê. Referenciar ADR ou sessão A6 quando
   aplicável (ex.: `(ADR-108)`, `(A6d.1)`).
3. **Commits pequenos e coesos** — 1 mudança lógica por commit. Nunca misturar
   refactor com feature. Se o diff passou de ~300 linhas ou toca 3+ camadas
   (backend/frontend/pipeline), **quebre** em commits sequenciais.
4. **Gate de testes antes do push** — obrigatório executar **ANTES** de
   `git push` (local, não confiar só no CI):

   ```bash
   pre-commit run --all-files           # hooks de lint/PII/paths/msg
   pytest backend/tests -q              # backend
   pytest tests -q                      # pipeline
   # se tocou frontend/:
   cd frontend && npm test -- --run     # Vitest
   # se tocou fluxos @critical:
   cd frontend && npm run test:e2e      # Playwright (lento — opt-in)
   ```

   **Se qualquer teste falha → não faz push.** Corrige antes. Dev/commit.py
   tem `--dry-run` útil para validar tudo antes de commitar.

#### Múltiplos agentes simultâneos (coordenação)

Vários agentes podem estar trabalhando em paralelo no mesmo repo **e no mesmo
working tree local**. Regras abaixo evitam perda de trabalho e conflitos.

##### Protocolo de início de sessão (OBRIGATÓRIO)

Executar **antes** de qualquer edit/write/commit. Quatro comandos:

```bash
git fetch origin                                    # sincroniza refs remotos
git status                                          # fotografa working tree
git log --oneline origin/main..HEAD -10             # commits locais ainda não-pushed
git log --oneline -10 -- CLAUDE.md                  # mudanças recentes em CLAUDE.md
git reflog | head -5                                # resets recentes (sinal de concorrência)
```

Então:

- **Se `git status` mostra arquivos modificados** — eles pertencem a outro
  agente ou sessão anterior. **NÃO edite** esses arquivos sem antes
  identificar o dono. Opções: (a) trabalhe em arquivos disjuntos; (b) se
  precisa tocar os mesmos, anuncie no chat e coordene com o usuário;
  (c) `git stash push -- <arquivos>` se vai mexer e restaurar depois.
- **Se CLAUDE.md mudou nos últimos commits** — releia a seção relevante
  antes de agir. A política pode ter sido atualizada.
- **Se a branch atual não é `main` nem `agent/*`** — investigue. Pode ser
  branch de outro agente que não foi mergeada.
- **Se reflog mostra `reset: moving to HEAD` recente** — outro agente fez
  reset destrutivo. Considere trabalhar em `git worktree add ../fin-<slug>`
  isolado (working tree novo, branch própria) se o trabalho é longo.

5. **Cada agente trabalha em sua própria branch** — nunca editar direto em
   `main` local. Naming convencional:
   - `agent/<slug-kebab>/<yyyyMMdd-HHmm>` — ex.: `agent/a6d1-globals-e4/20260420-1430`
   - Slug descritivo curto (≤40 chars). Timestamp evita colisão entre agentes.
   - **Criar a branch antes da primeira edição**, não depois. Edits em
     `main` local podem ser destruídos por `git reset --hard` de outro agente.
6. **Antes do push para `main`**: **sempre** `git fetch origin && git rebase
   origin/main` na branch do trabalho. Resolver conflitos localmente. Rodar
   suíte de testes **depois** do rebase (não antes). Se a suíte quebra
   pós-rebase → investigar e corrigir antes de push.
7. **Fast-forward only** para `main` — `git push origin main` só deve ter
   sucesso se você está fast-forward (o rebase do item 6 garante isso).
   Se `push` falhar por non-fast-forward, **não force** — refaça o rebase.
8. **Nunca dois agentes escrevendo no mesmo arquivo ao mesmo tempo**.
   Antes de começar, o agente deve:
   - `git fetch origin && git log origin/main --oneline -10` para ver
     atividade recente.
   - Se outro agente acabou de commitar no arquivo que você vai tocar,
     considere esperar ou coordenar com o usuário.

##### Cadência de commit (defensivo contra resets)

Um agente que acumula horas de trabalho no working tree está **uma
distração de perder tudo**. Reset acidental, outro agente dando
`git reset`, fechamento da sessão sem aviso — todos destroem working tree.
Commits são baratos e salvam.

- **Commite a cada marco atômico** (ex.: "criou repo", "criou DTOs",
  "refatorou endpoint"). Cada commit é um *anchor* que sobrevive a
  `git reset --hard HEAD` (só morre em `reset HEAD~N` com N>0).
- **Trabalhe em sua branch** (§5). Outro agente fazendo `reset` em `main`
  não toca seus commits da sua branch.
- **Se vai pausar, delegar, ou fechar a sessão** — commit antes, mesmo que
  seja WIP (`chore(wip): ponto de parada A6e.3 — use cases pendentes`).
  Push opcional; o commit local já é seguro.
- **Regra de bolso**: se `git diff --stat` já passa de ~150 linhas sem
  commit, faça commit agora.

##### Hotspots de documentação (CHANGELOG.md / BACKLOG.md / DECISIONS.md)

Esses três arquivos são editados por praticamente toda sessão de trabalho
— colisão entre agentes é garantida se todos concorrem no mesmo arquivo.

- **Commite docs separado do código** (commit dedicado `docs(<slice>): ...`).
  Diminui a janela em que o arquivo está uncommitted.
- **Commite docs por último na sessão**, depois do push dos commits de código
  (se possível). Reduz a chance de outro agente adicionar conteúdo
  concorrente no mesmo arquivo.
- **Se achar conflito ao dar `git stash pop` nesses arquivos** — resolva
  mantendo **todas** as adições (seus e dos outros agentes). Nunca descarte
  conteúdo alheio: cada bloco pertence a alguém e precisa continuar no
  histórico.
- **Não edite `CLAUDE.md` em paralelo com outro agente.** Se precisar,
  anuncie no chat antes e faça edit + commit atômico (≤5 min).

#### O que continua proibido (segurança, não autonomia)

9. **Nunca** `git push --force` ou `--force-with-lease` em `main`. Em
   branches de feature próprias, aceitável para limpar histórico antes do
   push inicial.
10. **Nunca** `git commit --no-verify` ou skip de hooks — os hooks existem
    para bloquear dados sensíveis. Se um hook falha legitimamente, **corrija
    a causa**; nunca bypasse.
11. **Nunca** `git commit --amend` em commits já pushados. Para corrigir,
    crie novo commit (`fix:` ou `chore: correct X`).
12. **Nunca** `git reset --hard` em branch compartilhada, **incluindo `main`
    local quando outros agentes podem estar ativos no mesmo working tree**.
    Reset no main local é aceitável **apenas** se você for o único agente
    rodando (verifique no chat antes). Caso contrário, seu reset apaga o
    working tree de outros agentes. Para ressincronizar com remoto sem
    destruir, prefira `git pull --ff-only origin main` — falha seguramente
    se houver divergência.
13. **Nunca** `git config` — NÃO alterar configuração global/local do git.
14. **Paths proibidos no staging** (enforçados por `dev/check_forbidden_paths.py`):
    `storage/`, `data/`, `inbox/`, `inbox_processed/`, `_scratch/`, `.env`,
    `.env.test`, `mathoms.db`, `config/passwords.txt`, qualquer `*.db`/`*.sqlite`.
    Hook bloqueia antes do commit.
15. **Dados sensíveis** — segue regra geral (§"Princípios gerais" acima):
    nunca commit CPFs, valores reais, senhas, conteúdo financeiro bruto,
    mesmo em docstrings ou fixtures.

#### Ferramentas de commit

16. **Proteção é responsabilidade do `pre-commit`**, não do caminho do
    commit. Instalar uma vez:
    `pip install pre-commit && pre-commit install --install-hooks && pre-commit install --hook-type commit-msg`.
    A partir daí, tanto `git commit` direto quanto `dev/commit.py` passam
    pelos mesmos guardrails.
17. `dev/commit.py` é **atalho opcional** com `--dry-run`, push integrado e
    validação de mensagem num comando só. Está em `dev/` — não em `scripts/`
    — justamente para não confundir com etapas do pipeline.

#### Prefixos aceitos de mensagem

Ver `dev/validate_commit_msg.py` para lista completa (regex `^(feat|fix|refactor|...)(\(.+\))?:`).

- **Produto web**: `feat:`, `fix:`, `refactor:`, `perf:`, `test:`, `chore:`,
  `backend:`, `frontend:`, `api:`, `db:`, `infra:`, `ci:`, `docs:`, `update:`.
- **Com escopo**: `feat(api): ...`, `fix(backend/storage): ...`,
  `refactor(e5): eliminate globals (A6d.1)`.
- **Legacy** (mantidos por compat com histórico): `pipeline:`, `config:`,
  `E1:`...`E7:`, `E-reset:`, `pre-reset:`.

#### Se CI quebra após push para main

Push local verde mas CI vermelho acontece (diferença de ambiente, pipeline lento,
flaky test). Protocolo:
1. **Anuncie imediatamente** — "CI quebrou no commit `abc1234` (job X). Investigando."
2. **Fix-forward** (novo commit que corrige) é preferível a revert. Se a
   correção é trivial (<10 min), fixe na mesma branch e push novamente.
3. **Revert** se a correção vai demorar — `git revert abc1234` + push. Deixa
   `main` verde. Depois crie branch nova para a correção real.
4. **Nunca** deixe `main` quebrada overnight sem comunicar.

### Dados sensíveis

- `data/`, `inbox/`, `inbox_processed/` contêm documentos financeiros pessoais — estão no `.gitignore`.
- `config/passwords.txt` contém senhas de PDFs — está no `.gitignore`.
- Nunca exponha CPFs, valores monetários reais ou dados pessoais em commits, logs ou outputs de console.

### Fontes de verdade

Consulte antes de inferir regras de domínio ou layout:

| Recurso | Função |
| ------- | ------ |
| `config/definitions.md` | Membros, instituições, categorias, regras especiais |
| `config/pipeline.json` | Parâmetros operacionais (inclui `report_version`, schema validation) |
| `config/family_members.json` | Dados cadastrais canônicos |
| `config/institutions.json` | Padrões de bancos e tipos de documento |
| `config/categorization.json` | Keywords de categorização |
| `config/report_layout.yaml` | Seções e componentes do relatório (com comentários inline) |
| `config/schemas/*.schema.json` | Contratos JSON por etapa |

- **Manual histórico (referência):** `_archive/manual_operacao_v6.1.md` — pipeline CLI legado.

Em caso de dúvida sobre como o pipeline funciona, consulte os scripts, configs e docstrings antes de agir.

### Classificação de documentos — duas vias

**Classificação unificada (P2, ADR-081):** o núcleo está em `backend/app/services/document_classification.py` (`classify_document`, `ClassificationResult`). Upload web, `POST /documents/reclassify` e `e0_route.route_file` (quando o pacote `backend` está importável) usam o **mesmo** fluxo: regex sobre **conteúdo** extraído → LLM opcional (confidence < 0,8) → `needs_review` se confidence < 0,7.

1. **E0-route (`scripts/e0_route.py`):** com backend disponível, chama `classify_document` (content-first, nome ignorado). **Sem** backend (CLI isolado), fallback legado: regex no **nome do arquivo** + LLM.

2. **Web (upload):** `document_processor.process_uploaded_document` chama o mesmo `classify_document` após unlock; `content_classifier.py` é a camada regex sobre o preview.

   - Requer `anthropic` SDK + `ANTHROPIC_API_KEY` no env do backend para o LLM fallback.
   - Sem a key, degrada para só regex (docs ambíguos tendem a `needs_review=true`).
   - `map_e0_doc_type_to_document_type()` mapeia códigos E0 (ex.: `faturaunique`, `extratocontabrl`) para a enum `DocumentType`.

### Dedupe de uploads

- **Exato:** SHA-256 do conteúdo → partial unique index `(workspace_id, content_hash)`. Mesmo arquivo = bloqueado.
- **Fuzzy:** se `(doc_type, bank_code, period)` já existe com hash diferente → `possible_duplicate_of_id` aponta para o existente + `needs_review=true`. Não bloqueia; UI mostra para o usuário decidir.

### Design System (ADR-076 · F9)

- **Fonte de verdade**: `design-tokens/tokens.json` — gera CSS para Next.js e para E6 standalone via `python3 design-tokens/build.py`.
- **Codegen do layout**: `config/report_layout.yaml` → `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py` via `python3 dev/codegen_report_layout.py`.
- **Fontes**: Plus Jakarta Sans (display), Inter (body), JetBrains Mono (monetário). Carregadas via `next/font/google` no `layout.tsx` — **não redefinir no CSS**.
- **Relatório nativo**: `frontend/src/components/report/` contém o render React. `e6_render.py` é exportador standalone (email, backup). O render primário é a rota `/reports/[id]`.
- **Cores**: nunca usar hex literal no frontend — sempre `var(--brand-*)`, `var(--surface-*)`, `var(--semantic-*)` dos tokens gerados.
- **Valores monetários**: sempre com `<MonetaryValue/>` (font-mono + tabular-nums).

### Convenções de código

- Scripts em `scripts/` seguem o padrão `eN_nome.py` (e0, e2, e3...). Exceção: `pipeline_common.py` (módulo compartilhado — paths, config, JSON I/O, schema validation) e `e6_regen.py` (utilitário visual).
- E0 scripts (`e0_unlock.py`, `e0_audit.py`, `e0_route.py`) importam paths e config de `pipeline_common.py` via `import scripts.pipeline_common as _pc`.
- `scripts/e6/` contém submódulos extraídos de `e6_render.py`: `sanitize.py` (formato monetário) e `validate.py` (19 checks V1–V19 no HTML).
- Parsers de E2 ficam em `scripts/e2/banks/<banco>.py` — um módulo por banco.
- Novo banco = novo arquivo em `scripts/e2/banks/`, com lista `PARSERS` exportada.
- Valores monetários em BRL usam formato brasileiro: `1.234,56` nos documentos, `1234.56` (float) nos JSONs.
- Idioma do projeto: português brasileiro. Nomes de arquivo de config e diretórios podem usar inglês por convenção técnica.

### Convenções de naming de artefatos

Sufixos de etapa por fase do pipeline:

| Sufixo              | Etapa               | Exemplo                                                 |
| ------------------- | ------------------- | ------------------------------------------------------- |
| `-0_original`       | E0 (roteamento)     | `c6bank_extratoconta_202601-0_original.csv`             |
| `-1a_extract`       | E1 (extração LLM)   | `david_curriculo-1a_extract.json`                       |
| `-1b_unified`       | E1 (unificação)     | `members-1b_unified.json`                               |
| `-1c_enriched`      | E1 (enriquecimento) | `members-1c_enriched.md`                                |
| `-1.5_consolidated` | E1.5 (baseline)     | `baseline_patrimonial-1.5_consolidated.json`            |
| `-2_extract`        | E2 (extração)       | `itau_extratoconta_202601_202604-2_extract.json`        |
| `-3_reconciled`     | E3 (reconciliação)  | `itau_extratoconta_BRL_202212_202604-3_reconciled.json` |
| `-4_unified`        | E4 (categorização)  | `despesas-4_unified.json`                               |
| `-5_analysis`       | E5 (análise)        | `analise_financeira-5_analysis.json`                    |

Nomes de banco em filenames seguem o código canônico de `institutions.json` (ex: `bankofamerica`, `btgpactual`, `c6bank`, `itau` — sem espaços, sem acentos).

### Convenções aceitas (decisões de design)

- **`baseline_patrimonial-1.5_consolidated.json` em `E2_extracts/`:** artefato E1.5 que vive em E2_extracts por ser input direto do E3/E4/E5. Documentado no manual.
- **Sufixos de `processed/` dirs:** `E2_extracts` (substantivo), `E3_reconciled` (particípio), `E4_unified` (particípio), `E5_analysis` (substantivo), `E7_review` (substantivo) — padrão misto aceito, não renomear.
- **`report_layout.yaml`:** único YAML no projeto. Justificado por extensos comentários inline que seriam perdidos em JSON.
- **`inbox_processed/`:** sem prefixo `_` (diferente de `_archive/`, `_scratch/`) porque semanticamente é parte do fluxo de dados, não um diretório auxiliar.
- **Período sentinel `999999`:** usado em faturas de cartão cujo período não pôde ser determinado. Propaga de E0→E2→E3.
- **`config/schemas/`:** contém 5 schemas de dados — `baseline_patrimonial.schema.json` (E1.5), `e2_extract.schema.json` (E2), `e4_unified.schema.json` (E4), `e5_analysis.schema.json` (E5), `pipeline.schema.json` (pipeline.json). Validação de dados controlada por `pipeline.json` → `schema_validation.enabled` (modo warn ou strict).
- **Logs:** nomes em lowercase com prefixo de etapa quando aplicável (ex: `e1_5_execution_report.txt`, `qa_log.md`).
