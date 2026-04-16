# CLAUDE.md — Financas Familia Pipeline

## Projeto

Pipeline de consolidação financeira da família Ferreira Campos. Processa documentos financeiros (PDFs, XLSX, CSVs, imagens) através de etapas sequenciais (E0→E7), gerando um relatório HTML unificado.

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
  e6/                  Submódulos E6 extraídos (sanitize.py, validate.py)
dev/                 Dev-tooling (commit helper, pre-commit hooks) — NÃO é produto
  commit.py            Wrapper git com guardrails (substitui o antigo e_save.py)
  check_forbidden_paths.py  Hook que bloqueia paths sensíveis no staging
  validate_commit_msg.py    Hook commit-msg que valida prefixo
  e2/                  Módulo E2 modular (common, registry, validation, banks/)
  e2/banks/            Parsers por banco (c6bank, itau, santander, bradesco, etc.)
  e6_regen.py          Utilitário: injeta melhorias visuais em relatório existente
  codegen_report_layout.py  Gera TS + Pydantic a partir do report_layout.yaml
data/                Documentos financeiros originais — NÃO versionado
  financial_statements/  Extratos e faturas (PDFs, CSVs, XLS)
  income_tax_br/         Declarações IRPF e informes de rendimentos
  income_tax_us/         Documentos fiscais EUA (placeholder)
  real_estate/           Dados de imóveis
  vehicles/              Dados de veículos (placeholder)
inbox/               Área de entrada de novos documentos — NÃO versionado
inbox_processed/     Documentos já processados pelo E0 — NÃO versionado
processed/           Artefatos intermediários do pipeline
  E2_extracts/         JSONs extraídos (E2) + baseline_patrimonial (E1.5, por convenção)
  E3_reconciled/       JSONs reconciliados (E3)
  E4_unified/          JSONs categorizados e unificados (E4)
  E5_analysis/         JSON de análise financeira (E5)
  E7_review/           Template de review e cross-validation (E7)
output/              Relatório HTML final (E6)
logs/                Logs operacionais permanentes
members/             Dados de membros (E1)
life_plan/           Metas e plano de vida
docs/                Documentação técnica de scripts e planos de correção
tests/               Testes unitários (pytest) — pipeline CLI
backend/             Aplicação web (FastAPI + React)
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


| Etapa       | Tipo    | Script                 | O que faz                                         |
| ----------- | ------- | ---------------------- | ------------------------------------------------- |
| E0-unlock   | Det.    | `e0_unlock.py`         | Desbloqueia PDFs/ZIPs protegidos por senha        |
| E0-audit    | Det.    | `e0_audit.py`          | Auditoria de integridade pré-pipeline             |
| E0-route    | Det.    | `e0_route.py`          | Renomeia e roteia documentos do inbox (LLM fallback: timeout 30s, 3 retries) |
| E1          | **LLM** | —                      | Extrai dados pessoais de membros                  |
| E1.5        | **LLM** | —                      | Consolida baseline patrimonial (IRPF)             |
| E1.5c       | Det.    | `e15_consolidate.py`   | Enriquece baseline com chaves consolidadas        |
| E2          | Det.    | `e2_extract.py`        | Extrai transações de extratos/faturas (unificado) |
| E2-llm      | **LLM** | —                      | Extrai investimentos/IRPF sem parser determin.    |
| E3          | Det.    | `e3_reconcile.py`      | Reconcilia e deduplica transações                 |
| E4          | Det.    | `e4_categorize.py`     | Categoriza receitas/despesas                      |
| E5          | Det.    | `e5_analyze.py`        | Cálculos financeiros (patrimônio, score, fluxo)   |
| E5.N        | Det.    | `e5n_narrativas.py`    | Narrativas textuais sobre os dados                |
| E6          | Det.    | `e6_render.py`         | Exporta HTML standalone (ADR-078; render primário é React nativo) |
| E7-crossval | Det.    | `e7_review.py`         | Cross-validation determinística (14 checks)       |
| E7-review   | **LLM** | —                      | Review holístico com persona (preenche template)  |
| E7-apply    | Det.    | `e7_review.py --apply` | Aplica refinamentos do review ao E5 JSON          |


**Det.** = determinístico (script Python). **LLM** = requer processamento por modelo de linguagem.

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

### Git e commits

- **NUNCA** comite automaticamente — só quando o usuário pedir explicitamente.
- **Proteção é responsabilidade do `pre-commit`**, não do caminho do commit. Instalar uma vez:
  `pip install pre-commit && pre-commit install --install-hooks && pre-commit install --hook-type commit-msg`.
  A partir daí, tanto `git commit` direto quanto `dev/commit.py` passam pelos mesmos guardrails
  (paths proibidos, prefixo de mensagem, segredos, etc.).
- `dev/commit.py` é **atalho opcional** (dev-tooling), não obrigatório. Use quando quiser
  dry-run, push automático e mensagens validadas num único comando. Está em `dev/` — não em
  `scripts/` — justamente para não confundir com etapas do pipeline.
- **Paths nunca commitados** (enforçados por `dev/check_forbidden_paths.py` e pelo hook):
  `storage/`, `data/`, `inbox/`, `inbox_processed/`, `_scratch/`, `.env`, `.env.test`,
  `fin.db`, `config/passwords.txt`, qualquer `*.db`/`*.sqlite`.
- Prefixos aceitos de mensagem (ver `dev/validate_commit_msg.py` para lista completa):
  - Produto web: `feat:`, `fix:`, `refactor:`, `perf:`, `test:`, `chore:`, `backend:`,
    `frontend:`, `api:`, `db:`, `infra:`, `ci:`, `docs:`, `update:`.
  - Com escopo: `feat(api): ...`, `fix(backend/storage): ...`.
  - Legacy (mantidos por compat com histórico): `pipeline:`, `config:`, `E1:`...`E7:`,
    `E-reset:`, `pre-reset:`.

### Dados sensíveis

- `data/`, `inbox/`, `inbox_processed/` contêm documentos financeiros pessoais — estão no `.gitignore`.
- `config/passwords.txt` contém senhas de PDFs — está no `.gitignore`.
- Nunca exponha CPFs, valores monetários reais ou dados pessoais em commits, logs ou outputs de console.

### Fontes de verdade

- **Definições:** `config/definitions.md` — membros, instituições, categorias, regras especiais.
- **Parâmetros:** `config/pipeline.json` — configuração operacional (inclui `report_version`).
- **Membros:** `config/family_members.json` — dados cadastrais canônicos.
- **Histórico:** `_archive/manual_operacao_v6.1.md` — manual legado do pipeline CLI (arquivado, referência histórica).

Em caso de dúvida sobre como o pipeline funciona, consulte os scripts, configs e docstrings antes de agir.

### Classificação de documentos — duas vias

Existem **dois caminhos de classificação** no projeto:

1. **CLI (pipeline):** `scripts/e0_route.py` — classifica por **regex no nome do arquivo**. Usado pelas etapas E0 do pipeline CLI (`python scripts/e0_route.py`). Camada 2: LLM fallback se regex não casa.

2. **Web (upload):** `backend/app/services/content_classifier.py` + `document_processor.py` — classifica por **regex no conteúdo extraído** (primeiras páginas do PDF, primeiras linhas do CSV/XLSX). **Filename é ignorado** — bancos exportam arquivos com nomes arbitrários. Pipeline: content-regex → LLM fallback (confidence < 0.8) → `needs_review=true` (confidence < 0.7).

   - Requer `anthropic` SDK + `ANTHROPIC_API_KEY` no env do backend para o LLM fallback.
   - Sem a key, degrada silenciosamente para só regex (precision menor, docs ambíguos ficam `needs_review=true`).
   - `_map_doc_type()` em `document_processor.py` mapeia códigos de tipo (ex: `faturaunique`, `extratocontabrl`) para a enum `DocumentType` via prefixo semântico.

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
- `scripts/e6/` contém submódulos extraídos de `e6_render.py`: `sanitize.py` (formato monetário) e `validate.py` (19 checks V1-V19).
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

- `**baseline_patrimonial-1.5_consolidated.json` em `E2_extracts/`**: artefato E1.5 que vive em E2_extracts por ser input direto do E3/E4/E5. Documentado no manual.
- **Sufixos de `processed/` dirs**: `E2_extracts` (substantivo), `E3_reconciled` (particípio), `E4_unified` (particípio), `E5_analysis` (substantivo), `E7_review` (substantivo) — padrão misto aceito, não renomear.
- `**report_layout.yaml`**: único YAML no projeto. Justificado por extensos comentários inline que seriam perdidos em JSON.
- `**inbox_processed/**`: sem prefixo `_` (diferente de `_archive/`, `_scratch/`) porque semanticamente é parte do fluxo de dados, não um diretório auxiliar.
- **Período sentinel `999999`**: usado em faturas de cartão cujo período não pôde ser determinado. Propaga de E0→E2→E3.
- `**config/schemas/**`: contém 5 schemas de dados — `baseline_patrimonial.schema.json` (E1.5), `e2_extract.schema.json` (E2), `e4_unified.schema.json` (E4), `e5_analysis.schema.json` (E5), `pipeline.schema.json` (pipeline.json). Validação de dados controlada por `pipeline.json` → `schema_validation.enabled` (modo warn ou strict).
- **Logs**: nomes em lowercase com prefixo de etapa quando aplicável (ex: `e1_5_execution_report.txt`, `qa_log.md`).

