# CLAUDE.md — Financas Familia Pipeline

## Projeto

Pipeline de consolidação financeira da família Ferreira Campos. Processa documentos financeiros (PDFs, XLSX, CSVs, imagens) através de etapas sequenciais (E0→E7), gerando um relatório HTML unificado.

## Estrutura de diretórios

```
config/              Configurações, schemas, templates, regras do pipeline
  definitions.md           Definições canônicas (membros, instituições, categorias)
  manual_operacao.md       Manual completo do pipeline (fonte de verdade)
  pipeline.json            Parâmetros operacionais (LLM, limites, tolerâncias)
  family_members.json      Dados cadastrais da família
  categorization.json      Keywords de categorização de receitas/despesas
  institutions.json        Padrões de bancos, tipos de documento, layouts de extração
  report_layout.yaml       Layout do relatório (seções, cards, charts) — YAML por extensos comentários inline
  schemas/                 JSON Schemas de validação (ex: baseline_patrimonial.schema.json)
  templates/               Templates estáticos (HTML, Markdown)
    report_template.html     Template HTML do relatório final (E6)
scripts/             Scripts determinísticos do pipeline (e0–e7, e_reset)
  pipeline_common.py   Módulo compartilhado (paths, config loading, JSON I/O)
dev/                 Dev-tooling (commit helper, pre-commit hooks) — NÃO é produto
  commit.py            Wrapper git com guardrails (substitui o antigo e_save.py)
  check_forbidden_paths.py  Hook que bloqueia paths sensíveis no staging
  validate_commit_msg.py    Hook commit-msg que valida prefixo
  e2/                  Módulo E2 modular (common, registry, validation, banks/)
  e2/banks/            Parsers por banco (c6bank, itau, santander, bradesco, etc.)
  e6_regen.py          Utilitário: injeta melhorias visuais em relatório existente
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
tests/               Testes unitários (pytest)
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
| E0-route    | Det.    | `e0_route.py`          | Renomeia e roteia documentos do inbox             |
| E1          | **LLM** | —                      | Extrai dados pessoais de membros                  |
| E1.5        | **LLM** | —                      | Consolida baseline patrimonial (IRPF)             |
| E1.5c       | Det.    | `e15_consolidate.py`   | Enriquece baseline com chaves consolidadas        |
| E2          | Det.    | `e2_extract.py`        | Extrai transações de extratos/faturas (unificado) |
| E2-llm      | **LLM** | —                      | Extrai investimentos/IRPF sem parser determin.    |
| E3          | Det.    | `e3_reconcile.py`      | Reconcilia e deduplica transações                 |
| E4          | Det.    | `e4_categorize.py`     | Categoriza receitas/despesas                      |
| E5          | Det.    | `e5_analyze.py`        | Cálculos financeiros (patrimônio, score, fluxo)   |
| E5.N        | Det.    | `e5n_narrativas.py`    | Narrativas textuais sobre os dados                |
| E6          | Det.    | `e6_render.py`         | Renderiza relatório HTML                          |
| E7-crossval | Det.    | `e7_review.py`         | Cross-validation determinística (14 checks)       |
| E7-review   | **LLM** | —                      | Review holístico com persona (preenche template)  |
| E7-apply    | Det.    | `e7_review.py --apply` | Aplica refinamentos do review ao E5 JSON          |


**Det.** = determinístico (script Python). **LLM** = requer processamento por modelo de linguagem.

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

- **Manual de operação:** `config/manual_operacao.md` — procedimento completo de cada etapa.
- **Definições:** `config/definitions.md` — membros, instituições, categorias, regras especiais.
- **Parâmetros:** `config/pipeline.json` — configuração operacional.
- **Membros:** `config/family_members.json` — dados cadastrais canônicos.

Em caso de dúvida sobre como o pipeline funciona, consulte esses arquivos antes de agir.

### Convenções de código

- Scripts em `scripts/` seguem o padrão `eN_nome.py` (e0, e2, e3...). Exceção: `pipeline_common.py` (módulo compartilhado) e `e6_regen.py` (utilitário visual).
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
- `**config/schemas/**`: contém apenas `baseline_patrimonial.schema.json`. Schemas adicionais podem ser criados conforme necessidade.
- **Logs**: nomes em lowercase com prefixo de etapa quando aplicável (ex: `e1_5_execution_report.txt`, `qa_log.md`).

