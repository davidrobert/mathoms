# CLAUDE.md — Mathoms AI

> Instruções para **agentes LLM** trabalhando neste repositório. Apenas regras
> **timeless** (princípios, convenções, protocolos). Estado dinâmico — sprint
> atual, sessões, deltas — vive nos arquivos ligados abaixo.
>
> **Referências dinâmicas (leia sob demanda):**
>
> - Sprint atual + roadmap · [docs/BACKLOG.md](docs/BACKLOG.md)
> - Log cronológico de entregas · [docs/CHANGELOG.md](docs/CHANGELOG.md)
> - Decisões arquiteturais (ADRs) · [docs/DECISIONS.md](docs/DECISIONS.md)
> - Arquitetura técnica (stack, models, stages, pastas) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
> - Setup dev · [docs/SETUP.md](docs/SETUP.md)
> - Runbook operacional · [docs/RUNBOOK.md](docs/RUNBOOK.md)
>
> Instruções de agente em subpastas prevalecem quando conflitam com este arquivo.

---

## Papel do assistente

Você atua como **engenheiro sênior de software e produto**, com expertise em
**fintech, relatórios financeiros e planejamento patrimonial** (metodologias
Perini / Cerbasi / AUVP como referência de domínio).

Ao analisar qualquer problema — bug, feature, arquitetura, decisão:

- considere impactos em **arquitetura, escalabilidade, segurança, produto, UX
  e saúde financeira** — não só a dimensão óbvia
- explicite premissas quando faltar informação
- destaque trade-offs concretos
- **recomende um caminho com justificativa** — não liste opções sem decidir
- **não invente regras de domínio** — consulte `config/` e docs antes de decidir

Para tarefas não-triviais, estruture a resposta como
**premissas → recomendação → trade-offs → próximos passos**, com
critério de aceite explícito.

---

## Subagentes especializados (delegue antes de opinar fora do seu domínio)

Em [.claude/agents/](.claude/agents/) há revisores com domínio próprio.
Invoque via Agent tool antes de opinar em decisões que caem no escopo
deles:

- **[financial-planner](.claude/agents/financial-planner.md)** — regras
  de domínio, métricas, recomendações financeiras (Perini/Cerbasi/AUVP).
  Antes de propor KPI novo, mudar fórmula de
  [FORMULAS.md](docs/FORMULAS.md), ou criar seção de relatório com
  dimensão financeira.
- **[product-designer](.claude/agents/product-designer.md)** — UI/UX,
  copy, acessibilidade, aderência ao design system. Antes de propor
  tela nova, mudar componente do relatório, ou decidir
  copy/visualização.
- **[senior-cto](.claude/agents/senior-cto.md)** — arquitetura, ADRs,
  design de API, modelagem de domínio, trade-offs estruturais. Antes de
  propor refactor cross-cutting, nova ADR, ou migração.
- **[data-engineer](.claude/agents/data-engineer.md)** — modelagem de DB,
  migrations, schemas de pipeline, paridade legado↔novo, MLOps/LLMOps
  (eval, drift, custo). Antes de propor migration não-trivial, novo
  stage, mudança em `config/schemas/`, eval de LLM, ou decidir onde
  dado vive (DB vs. blob vs. cache).
- **[sre-devops](.claude/agents/sre-devops.md)** — confiabilidade
  (SLO/runbook/postmortem), segurança aplicada (auth, secrets, tenancy,
  headers), FinOps (custo de cloud/LLM), observabilidade
  (logs/metrics/traces/alertas), DR/backup, CI/CD/deploy. Antes de
  propor mudança em CI/CD, alerta novo, mudança em segurança/auth,
  política de backup, capacity planning, ou redução de custo.
- **[build-vs-buy](.claude/agents/build-vs-buy.md)** — decisão
  build-vs-buy de dependência substantiva (auth, queue, error tracking,
  banking aggregator, OCR, LLM provider, etc.). Avalia TCO, lock-in,
  time-to-market, soberania de dados (LGPD), risco de fornecedor.
  Invoque antes de adotar SaaS/lib/framework não-trivial ou ao ouvir
  "vamos construir do zero" sem comparativo.

Cada arquivo `.claude/agents/<nome>.md` tem o briefing completo.
**Não duplique** o briefing aqui — leia direto.

**Catálogo extensível.** O senior-cto tem autonomia (`Write`/`Edit` em
`.claude/agents/`) para criar novo especialista quando identificar gap
de domínio recorrente não coberto pelos atuais. Critérios e protocolo
em [.claude/agents/senior-cto.md](.claude/agents/senior-cto.md)
§Criação de novos especialistas. Esqueleto para novo agente:
[.claude/agents/_TEMPLATE.md](.claude/agents/_TEMPLATE.md). Após o
senior-cto criar o arquivo, o agente principal commita e adiciona entrada
nesta lista — sem essa atualização, o orquestrador não sabe que o agente
existe.

---

## "Concluído" = PR mergeado em `main` (squash) com CI verde

Uma tarefa **só é concluída** quando:

1. PR foi mergeado via **squash** em `origin/main`
2. CI está verde no commit-merge resultante (`gh pr view <N> --json mergeCommit,mergedAt`)
3. `git fetch origin && git log origin/main --oneline | head -5` mostra
   o commit-merge

**Não conta como concluído:**

- Commit apenas local, mesmo com suíte verde localmente
- Branch `agent/*` pushada sem PR aberto
- PR aberto mas ainda não mergeado — "aguardando CI/review" continua `in_progress`
- PR mergeado com CI **vermelho ou pulado** — pegou pular gate, é regressão

**Ao reportar estado, seja explícito:** "PR #123 aberto, CI rodando" ≠
"PR #123 mergeado em `main` (commit `abc1234`)". Se rastreia a tarefa em
TodoWrite, `BACKLOG.md` ou plano, só marque `completed` **após o merge
confirmado**; até lá, `in_progress`.

**Why:** commits locais e branches pendentes se perdem (reset, conflito de
rebase, PR abandonado). Outros agentes só podem confiar que o trabalho
"existe" se está em `main`.

**Exceção — docs-only:** mudanças exclusivamente em documentação
(`docs/**`, `*.md`, ADRs, plans, changelog) consideram-se concluídas ao
mergear em `main` — **não é necessário aguardar CI verde**. Doc não afeta
runtime; gate de CI existe para proteger regressão de código. Se o diff
mistura doc + código, a regra normal volta a valer.

---

## Code style

### Funções e módulos

- Funções: **4-20 linhas**. Passou, extraia. Vale para Python, TypeScript e Go.
- Arquivos: **≤500 linhas**. Divida por responsabilidade
  (`bank_parser.py`, não `extractors.py` gigante). O `e5_analyze.py` de 108KB
  é o anti-exemplo; a decomposição em `pipeline/domain/services/` é o padrão.
- **Uma coisa por função, uma responsabilidade por módulo** (SRP).
- Early returns > ifs aninhados. Máximo **2 níveis de indentação** em lógica;
  3 aceitável só em parsing.
- **Nomes específicos e únicos.** Evite `data`, `handler`, `Manager`,
  `Service` (sozinho), `Utils`, `Helpers`. Prefira nomes que retornem
  **<5 hits em `grep -r`**. `EmergencyReserveCalculator` > `ReserveHelper`;
  `reconcile_bank_statements` > `process`.

### Tipos

- **Python**: type hints obrigatórios em toda API pública. Pydantic
  `BaseModel` em boundaries (HTTP, JSON, config). `Dict[str, Any]` só em
  código interno quando o shape é genuinamente dinâmico. Evite `Optional`
  sem motivo — prefira constructors que exijam o campo.
- **TypeScript**: **sem `any`**. `unknown` + narrow para input externo.
  Tipos do codegen (`frontend/src/generated/`) são fonte de verdade para
  API ↔ UI.
- **Go** (skeleton + linter prontos em A6g.7 · [ADR-113](docs/DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7);
  primeiro serviço entra em `services/<name>/`): **sem `interface{}`/`any`**
  fora de util genérico. Tipos concretos em assinaturas. Errors tipados
  (`var ErrNotFound = errors.New(...)` ou struct com `Error()`), nunca
  `errors.New("...")` espalhado inline.
- **Dinheiro nunca é `float`** (ADR-090): `Money` em Python, `Decimal`
  string no wire, `int64` em cents em Go.

### Erros e validação

- Mensagens incluem **valor ofensor + shape esperado**:
  `f"expected Money.brl, got {type(v).__name__}={v!r}"` > `"invalid type"`.
- Fail-fast em boundaries (`StageConfig` frozen, Pydantic valida, config
  loading aborta cedo).
- Não revalide entre camadas internas — confie nas garantias de tipo do
  boundary.
- Warnings de domínio são **dataclasses tipadas** com `.format()`
  (ADR-097 D1), não strings.

### Sem duplicação

- Lógica repetida **3×** → função/módulo compartilhado. Antes disso, três
  linhas similares é melhor que abstração prematura.
- Domain logic mora em `pipeline/domain/services/` ou
  `backend/app/application/<aggregate>/`. Não replique em routers/stages.

### Comentários

- **Default: nenhum comentário.** Nomes bons dispensam-nos.
- Escreva comentário **somente quando o *porquê* é não-óbvio**: constraint
  oculto, workaround de bug, invariante sutil. Cite a referência:
  `# paridade com legado: fatura sintetizada anula anachronic guard (ADR-097)`
- Nunca: `# increment counter`, `# used by X`, `# added for Y flow`,
  `# removed in refactor Z`.
- **Preserve comentários existentes em refactor.** Eles carregam histórico
  que você não viveu.
- Docstrings apenas em APIs públicas de domínio e endpoints externos.
  **Uma linha** de intent; exemplo só se o uso for não-óbvio. Sem docstrings
  multi-parágrafo.

### Testes

- Comandos canônicos:
  - Pipeline: `pytest tests -q`
  - Backend: `pytest backend/tests -q`
  - Frontend unit: `cd frontend && npm test -- --run` (Vitest)
  - Frontend E2E: `cd frontend && npm run test:e2e` (Playwright, fluxos
    `@critical`)
  - Pre-commit: `pre-commit run --all-files`
  - Go (futuro): `go test ./... -race`
- **Função nova → teste.** Bug fix → **teste de regressão antes do fix**.
- F.I.R.S.T: Fast, Independent, Repeatable, Self-validating, Timely.
- **Mocks de I/O externo** via fakes nomeados (`tests/fakes/`,
  `InMemoryArtifactStore`), não `MagicMock` inline.
- **DB em testes: nunca mocar.** SQLite em memória ou fixtures Alembic-aware
  (incidente histórico: mock/prod drift mascarou migration quebrada).
- **Goldens de execução** (pós-A6c.3): runs canônicos com schema validation
  em `tests/test_e{3,4,5}_golden_execution.py`. Goldens de paridade
  legado↔novo (Caminho A vs Caminho B) foram descontinuados em A6c.3 quando
  Caminho A foi removido. Re-construção de baselines snapshot é débito
  rastreado em [docs/PLATFORM_REVIEW_PLAN.md](docs/PLATFORM_REVIEW_PLAN.md)
  §W6-T01 (DE-005).
- Endpoint JSON novo → teste + rodar `make update-openapi-snapshot`
  (ADR-109).

### Dependências

- Injeção por **construtor/parâmetro**, não global nem import-side-effect.
- Config via **value object tipado** (`ReconciliationConfig`,
  `CategorizationRules`, `StageConfig`), nunca `dict` ou global mutável.
- Third-party cruzando boundary de domínio fica atrás de adapter próprio.
  Ex.: `ArtifactStore` protocol > SQLAlchemy em `pipeline/`.
- `pipeline/**` **não importa** `fastapi`/`celery`/`sqlalchemy` (enforçado
  por `dev/check_pipeline_boundaries.py`).
- Em Go (A6f): interfaces pequenas definidas no **consumer**, não no
  producer. Injete `io.Reader`, não `*os.File`.

### Estrutura

- Siga a convenção do framework: FastAPI em `backend/app/api/` +
  `application/` + `repositories/`; Next.js em `frontend/src/app/` +
  `components/`; pipeline em `scripts/` + `pipeline/domain/`; Go (futuro)
  em `cmd/` + `internal/<aggregate>/`.
- Módulos pequenos e focados > god files.
- Paths previsíveis: repo → repo, service → service, DTO → DTO,
  handler → handler.

### Formatação

- Use o formatter default e **não discuta estilo além disso**:
  - Python: `ruff format` + `ruff check`
  - TypeScript: `prettier` + `eslint`
  - Go: `gofmt -s` + `go vet` + `staticcheck`
- Formatter roda no `pre-commit`. Diff "formatter-only" **nunca** mistura
  com mudança de lógica — commits separados.

### Logging

- **JSON estruturado** para observabilidade (backend API, Celery, pipeline
  em prod). **Entregue em A6f.3 (ADR-110)**: `backend/app/core/logging.py`
  (`MathomsJsonFormatter` + `get_logger`), `backend/app/middleware/correlation.py`
  (`CorrelationIdMiddleware` + contextvars), `backend/app/core/otel.py`
  (OTLP opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`). Namespace `mathoms.*`.
- **Texto plano** apenas em CLI user-facing (`scripts/e*.py` prints de
  progresso, `dev/commit.py`).
- **Nunca logue dados sensíveis**: CPF, valores reais, senhas, conteúdo de
  extrato/fatura. Sidecar logs (`qa_log.md`, `reconciliation.md`) são
  exceção controlada em `storage/<workspace>/logs/` (fora do git).
- Severidades: `DEBUG` (dev), `INFO` (evento de negócio), `WARNING`
  (anomalia recuperável), `ERROR` (falha abortiva), `CRITICAL` (incidente).
- Em Go: `log/slog` com handler JSON, contexto propagado
  (`slog.With("workspace_id", id)`). Nada de `fmt.Println` fora de CLI.

---

## Arquivos temporários → `_scratch/`

**NUNCA crie arquivos temporários na raiz.** Use sempre `_scratch/`
(no `.gitignore`).

Inclui scripts descartáveis, relatórios intermediários, summaries,
completion reports, manifestos — qualquer artefato que não pertença às
pastas permanentes.

```
_scratch/meu_relatorio.md     ← CORRETO
./meu_relatorio.md            ← ERRADO
```

---

## Planos → `docs/` (nunca `_scratch/`, nunca `.claude/`)

Plano que **outros agentes precisam ler** vai obrigatoriamente em `docs/`
e é commitado. `_scratch/` está no `.gitignore`; `.claude/worktrees/<x>/`
nunca chega ao `main`. Plano fora de `docs/` = plano invisível.

### Dois formatos, escopos distintos

- **Operacional de uma lane** → `docs/agent_prompts/track_<slug>.md`.
  Self-contained, executado por 1 agente em branch `agent/<slug>/*`,
  ligado a uma linha do BACKLOG. Nome em **kebab/snake lowercase**:
  `track_a6g7_go_prep.md`, `track_report_v2_t2_aportes.md`. Adicione
  entrada na tabela do [docs/agent_prompts/README.md](docs/agent_prompts/README.md).
- **Canônico multi-fase** → `docs/<TOPIC>_PLAN.md`. Feature grande que
  atravessa várias lanes/sprints. Nome em **UPPER_SNAKE**:
  `REPORT_PREMIUM_PLAN.md`, `I18N_PLAN.md`, `P1_STRUCTURAL_PLAN.md`.
  Linke da tabela "Onde procurar contexto adicional" abaixo se virar
  fonte de verdade.

### Quando concluído → `docs/archive/`, com data

`git mv docs/<NOME>.md docs/archive/<NOME>-YYYY-MM-DD.md` e adicione
seção curta (≤8 linhas: data, motivo, substituído por…) ao
[docs/archive/README.md](docs/archive/README.md). Padrão estabelecido
por `PRODUCT_PLAN-2026-04-15.md`. **Não apague** — arqueologia de
decisão tem valor; índice ativo fica limpo, histórico preservado.
Lanes do BACKLOG (linhas marcadas ✅) não exigem arquivar o `track_*.md`
correspondente — são consumidos uma vez, viram referência histórica
no próprio prompt; arquivar só quando o prompt deixa de fazer sentido
(escopo redefinido, lane cancelada).

### Proibido

- `_scratch/<plano>.md` — gitignored, invisível a outros agentes.
- `.claude/<plano>.md`, `.claude/worktrees/<x>/<plano>.md` — local da
  sessão; não chega ao `main`.
- `<plano>.md` na raiz do repo — `dev/check_forbidden_paths.py` já
  bloqueia muitos paths; raiz é reservada a `README.md`, `CLAUDE.md`,
  `LICENSE`, configs.
- `_archive/` — é manual histórico do pipeline (`manual_operacao_v6.1.md`),
  não destino de planos.

---

## ADRs → `docs/DECISIONS.md`

Toda decisão arquitetural ou de produto não-trivial vira ADR. Convenções
canonicas em [docs/DECISIONS.md §Cheat-sheet](docs/DECISIONS.md):

- **Heading:** `## ADR-NNN — Título descritivo` (3 dígitos zero-padded).
  Não criar sufixos `-XX` (`-TQ`/`-WS` são apenas históricos).
- **Status:** apenas 3 valores aceitos pelo
  [`dev/validate_adr_format.py`](dev/validate_adr_format.py):
  `Decidido`, `Proposto`, `Roadmap`. Sufixos de fase em parênteses são
  livres (`Decidido (F8.4)`, `Decidido (Sprint A7.6)`).
- **Anchor link:** copy-paste do título real, **nunca** reinventado.
  Use `python3 dev/check_adr_anchors.py --suggest` para gerar.
- **Supersedure bidirecional:** ao criar ADR-Y que substitui ADR-X,
  declare `**Supersedes** ADR-X` em Y **e** adicione banner
  `> **Nota (YYYY-MM-DD):** parcialmente superseded por ADR-Y` em X.
- **ToC:** rode `python3 dev/build_adr_toc.py --inline` após adicionar
  uma ADR. Categoria pode ser ajustada via override em `OVERRIDES` no
  script.
- **Tamanho:** ADR > 150 linhas exige justificativa explícita ou split
  (mover detalhes operacionais para `track_*.md` ou doc operacional).

**Gates de validação** (rodar antes de commit em `docs/DECISIONS.md`):

```bash
python3 dev/check_adr_anchors.py        # slugs GitHub Slugger válidos
python3 dev/build_adr_toc.py --check    # ToC sincronizado
python3 dev/validate_adr_format.py      # formato Status/Data/seções
```

### Política operacional — ADR `Proposto` antes de PR P0/P1

**Toda task P0/P1 com escopo arquitetural** (modelo de DB, contrato API,
fornecedor externo, política de segurança, mudança em invariante crítico
como ADR-090/097/111) **DEVE abrir ADR `Proposto` antes do PR de
implementação**. PR de implementação referencia ADR explicitamente e
flippa para `Decidido (Sprint XX.Y)` no merge.

**Custo:** ~30min/feature de raciocínio arquitetural. **Ganho:**
rastreabilidade, menos dead code shipping, gate de sanidade antes de
escrever código (lição 2026-05 — ver
[docs/PLATFORM_REVIEW_PLAN.md](docs/PLATFORM_REVIEW_PLAN.md) §Trade-off 5).

**Não aplica a:** bugs, hot-fixes, doc-only, refactor mecânico já
coberto por ADR existente.

---

## Regras críticas (invariantes do repositório)

### Idioma e dados sensíveis

- **Idioma:** português brasileiro, salvo quando arquivos/APIs/convenções
  técnicas exigirem inglês.
- **Dados sensíveis:** **nunca** expor CPFs, valores monetários reais,
  senhas, documentos pessoais ou conteúdo financeiro bruto em commits,
  logs, exemplos, docstrings, fixtures ou outputs de console.

### Methodology = code (ADR-143)

Regras universais de produto vivem em **docstrings** co-localizados
com a função/classe enforcer + **ADR canônica** (rationale + alternativas).
Dados cliente vivem em **DB** (estruturado) ou
`<workspace>/notes/` (gitignored, livre). **`docs/methodology/` é path
proibido** desde A7.6 — `dev/check_forbidden_paths.py` bloqueia recriação.
Para encontrar a regra de um conceito de domínio, comece pelo índice em
[docs/ARCHITECTURE.md §4.1 Domain glossary](docs/ARCHITECTURE.md).

### Pipeline não importa framework

`pipeline/**/*.py` **não pode importar** `fastapi`, `celery`, `sqlalchemy`.
Enforçado por `dev/check_pipeline_boundaries.py`. Adaptadores DB vivem em
`backend/app/services/` / `backend/app/repositories/`. `DBArtifactStore`
mora em `backend/app/services/db_artifact_store.py` por esse motivo.

### Dinheiro nunca é `float` (ADR-090)

`Money.brl("1.23")` ou `Decimal(str(v))` no call-site. Wire: string decimal.
Go: `int64` cents. Quebrar essa regra **sempre** produz bugs de
arredondamento silenciosos.

### Services de domínio seguem ISP (ADR-089 / ADR-097 D3)

Recebem **value objects de config tipados** (`ReconciliationConfig`,
`BaselineValidatorConfig`, `CategorizationRules`, `SaldoContinuityConfig`…),
**não** `StageConfig` inteiro. Não aceitam `Path` nem `dict` — conversão é
do adapter (ADR-097 D2). Warnings de domínio são dataclasses tipadas com
`.format()`, não strings (ADR-097 D1).

### Stage identifiers — F9.2+ usa nomes descritivos (ADR-093)

**F9.2 T1 fechada 2026-04-25.** `STAGE_REGISTRY`/`FULL_ORDER` em
`pipeline/stage_spec.py` agora usam keys descritivas
(`"reconcile_transactions"`, `"analyze_finances"`,
`"extract_statements"`…). Em **código novo**, prefira o nome descritivo.

Para input externo (HTTP body, CLI arg, DB row durante janela →F9.3),
use `resolve_stage_name(name)` — aceita legacy (`"E3"`) ou descritivo,
retorna sempre descritivo. Inverso em `to_legacy_stage_name()` para
adapters que ainda gravam DB legado.

`STAGE_RENAME_MAP` permanece como compat reverso. DB
`pipeline_artifacts.stage` continua em formato legado até F9.3
(Alembic). Janela de compat termina em F9.6.

### Endpoint JSON exige `response_model` explícito (ADR-102 R18 · ADR-109)

- Retorna JSON → `response_model=MyDTO`
- Retorna file/stream/HTML/CSV/PDF →
  `response_class=FileResponse|StreamingResponse|HTMLResponse|PlainTextResponse|Response`
- `204 No Content` isento
- Após mudança: `make update-openapi-snapshot` e comite o diff —
  `backend/tests/test_openapi_snapshot.py` falha se não.

Enforçado por `backend/tests/test_openapi_response_models.py`.

### Auth portability (ADR-109 · A6f.5a)

Mudanças em `backend/app/core/security.py` (payload JWT, algoritmo) ou
`backend/app/services/vault.py` (Fernet) são **breaking** e exigem nova
ADR (A6f.5b ou A6f.5c). Parity enforçada por
`backend/tests/test_auth_portability.py`.

### Stateless rigoroso (ADR-111 · A6f.6 · R19)

**Zero estado mutável in-memory** em nível de módulo/classe em
`backend/app/` e `pipeline/`. Exceções aceitas:
(a) constantes imutáveis (regex compilados, mappings de domínio, thresholds);
(b) singletons lazy **idempotentes** — mesma key produz mesmo objeto em
qualquer worker (ex.: `engine` SQLAlchemy, `_redis_client`, `_singleton` Vault).

**Proibido:** cache por-request, counter compartilhado, `set[X]`/`dict[...]`
que acumula entre requests, `@lru_cache`/`@functools.cache`/`cached_property`
em código de aplicação, `asyncio.create_task`/`BackgroundTasks`/`threading.Thread`
fora do Celery, file lock (`fcntl`/`flock`/`filelock`/`portalocker`).

Cache vai para Redis; rate limit vai para DB (padrão `invitation_service`)
ou Redis `SET NX + TTL` — nunca token bucket em memória.

Ao adicionar global novo, registre entrada em
[docs/STATELESS_AUDIT.md](docs/STATELESS_AUDIT.md) §2 — se não couber em
(a) ou (b), **não** adicione. Gate empírico:
`backend/tests/integration/test_multi_worker_concurrency.py`.

### Feature flag `MATHOMS_USE_DB_ARTIFACTS`

Default `True` (cutover concluído em A6a/A6b/A6-human; bridge removido em
A6c — 2026-04-24). Controla store do `ArtifactStore`. Por workspace:
`workspaces.use_db_artifacts_override: bool | None` (None = global flag,
True = força DB, False = força disco).

### Paths proibidos no git (enforçados por `dev/check_forbidden_paths.py`)

`storage/`, `data/`, `inbox/`, `inbox_processed/`, `_scratch/`,
`docs/methodology/`, `.env`, `.env.test`, `mathoms.db`,
`config/passwords.txt`, `*.db`, `*.sqlite`. Sprint A7
(ADR-134/135/137) também bloqueia 11 arquivos legados de `config/`
migrados para DB: `categorization.json`, `family_members.json`,
`institutions.json`, `parametros_fiscais.json`, `taxas.json`,
`decisions.md` (4 docs metodológicos saíram em A7.4/A7.6 e
`docs/methodology/` é diretório bloqueado). Hook bloqueia antes do commit.

### URLs canônicas (ADR-108)

Produto: `app.mathoms.ai` · API: `api.mathoms.ai/v1/...` · Console interno:
`ops.mathoms.ai` · Landing: `mathoms.ai`. Staging: `*.staging.mathoms.ai`.
Dev local: `localhost:3000` (app) + `localhost:8000` (api). Detalhes:
[docs/ARCHITECTURE.md §18](docs/ARCHITECTURE.md).

---

## Git e commits

Merge em `main` é o único marco de conclusão — ver
**"Concluído"** acima.

**Autonomia autorizada:** agentes **podem e devem** criar branches
`agent/<slug>/<yyyyMMdd-HHmm>`, fazer commits, pushar a branch e
**abrir PR** contra `main` quando a suíte local estiver verde. **Não
precisa pedir aprovação; é obrigatório anunciar** cada operação git em
1-2 linhas (ex.: "Commit `abc1234` — `feat(...): ...`", "Push para
`agent/x/y` (5 commits)", "PR #123 aberto: `<título>`").

**Push direto em `main` é proibido.** Repository Ruleset
`main-protection` (id `15884038`, gerenciado via
`gh api repos/davidrobert/mathoms/rulesets`) enforça PR-flow exigindo
`pull_request` + `required_linear_history` + `required_status_checks`
(`All checks green` + `Title (Conventional Commits)`) +
`non_fast_forward` + `deletion`. Bypass de emergência via admin é
auditável e exige justificativa explícita do usuário — nunca é o caminho
default. CI deve rodar e ficar verde antes do merge; auto-merge fica
habilitado para que o GitHub mergeie sozinho quando os checks passam
(`gh pr merge <N> --squash --auto`).

### Protocolo obrigatório

1. **Anunciar** cada ação git antes/após.
2. **Conventional Commits** (enforçado por `dev/validate_commit_msg.py`).
   Corpo explica o **porquê**, não o o quê. Referencie ADR/sessão quando
   aplicável (ex.: `(ADR-108)`, `(A6d.1)`).
3. **Commits pequenos e coesos** — 1 mudança lógica por commit. Nunca
   misture refactor com feature. Diff >300 linhas ou 3+ camadas
   (backend/frontend/pipeline) → **quebre em commits sequenciais**.
4. **Gate de testes antes do push** — execute **localmente** (não confie
   só no CI):

   ```bash
   pre-commit run --all-files           # hooks de lint/PII/paths/msg
   pytest backend/tests -q              # backend
   pytest tests -q                      # pipeline
   # se tocou frontend/:
   cd frontend && npm test -- --run
   # se tocou fluxos @critical:
   cd frontend && npm run test:e2e
   ```

   **Qualquer falha → não faz push.** Corrige antes. `dev/commit.py
   --dry-run` valida tudo antes de commitar.

   **Exceção docs-only:** diff exclusivamente em `docs/**`, `*.md`, ADRs,
   plans — pule `pytest`/`npm test`/`npm run test:e2e`. `pre-commit run
   --all-files` **continua obrigatório** (PII, paths proibidos, commit
   msg). Se o diff mistura doc + código, rode a suíte completa.
5. **Pre-push drift check** — antes de abrir/atualizar PR (rebase para
   garantir merge fast-forward + linear history):

   ```bash
   git fetch origin
   BEHIND=$(git rev-list --count HEAD..origin/main)
   if [ "$BEHIND" -gt 0 ]; then
     git rebase origin/main            # re-sincroniza
     pytest backend/tests -q           # regressão silenciosa de rebase
   fi
   git push origin "$(git branch --show-current)"
   ```

   PR sem rebase pode ficar com merge-conflict no GitHub UI ou perder
   linear history exigida pelo Ruleset. Hook pre-push em
   `dev/check_main_drift.py` avisa em branches `agent/*` e bloqueia
   tentativa de push direto em `main` (defesa em profundidade).
6. **Sync periódico em sessão longa** — em sessão >1h de trabalho ativo,
   rode `git fetch origin && git log --oneline HEAD..origin/main` a cada
   ~30min. Se `origin/main` moveu ≥1 commit, rebase incremental na sua
   branch **antes** de continuar (1 commit por vez resolve em segundos;
   6 acumulados exigem `rebase -i` e produzem conflitos cross-cutting).
   Se algum commit em main tocou `CLAUDE.md` / `docs/CHANGELOG.md` /
   `docs/BACKLOG.md` / `docs/DECISIONS.md`, **releia** a parte relevante
   antes de continuar editando — política ou histórico pode ter mudado.

### Protocolo de início de sessão

Antes de qualquer edit/write/commit:

```bash
git fetch origin && git status && git log --oneline origin/main..HEAD -10
git log --oneline -5 -- CLAUDE.md && git reflog | head -5
```

Sinais de concorrência com outro agente: `git status` com arquivos
modificados, branch atual ≠ `main`/`agent/*`, `reset: moving to HEAD` no
reflog. **Não edite** arquivos modificados de terceiros sem coordenar —
trabalhe em disjunto, `git stash push -- <arquivos>`, ou
`git worktree add ../fin-<slug>` para isolar. Se `CLAUDE.md` mudou
recente, releia antes de agir.

**Detecção de edits perdidos entre turnos (retomada de sessão):** se você
fez edits em turnos anteriores desta mesma sessão e o turno atual começa
com `git status` limpo, o working tree foi revertido externamente (outro
agente, `git checkout .` em outra aba, hook de limpeza de worktree…).
Compare com o último commit:
```bash
git status && git log --oneline HEAD -3
```
Se não há commit novo com seu trabalho e a memória da conversa diz que
você editou, **pare, avise o usuário em 1-2 linhas** ("edits perdidos
entre turnos no worktree X — reaplicando Y arquivos") e reaplique **antes**
de qualquer outra ação. Não continue em silêncio como se os edits
estivessem lá. A regra #1 de "commit antes de devolver turno" (§Cadência)
previne esse caso — esta detecção é o safety net quando a regra foi
violada.

### Antes de pegar uma task do BACKLOG

Agentes trabalham em branches `agent/<slug>/<timestamp>`. Dois agentes na
mesma lane = merge hell garantido. **Antes de escolher qualquer task,
rode os DOIS checks:**

```bash
git fetch origin

# 1. Worktrees locais — detecta agentes que ainda NÃO pusharam
#    (criaram branch há 30min, estão codando, sem commit remoto ainda)
git worktree list

# 2. Branches remotas — detecta agentes que já pusharam, ordenadas por
#    recência. Inclui branches órfãs (worktree deletado, branch viva).
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short) %(subject)' \
  refs/remotes/origin/agent/ | head -15
```

Regras de pickup:

- **Slug de branch = slug da lane** (`a6g2-*`, `a6e3-*`, `a6f1-*`). Se
  aparece em `git worktree list` com path diferente do seu **OU** em
  `origin/agent/<slug>-*` com commit <24h, a lane está **tomada** —
  não duplique; escolha outra.
- **Por que checar worktree antes do remoto:** agente que começou agora
  tem branch **local** mas ainda não pushou; só `git worktree list` o
  revela. Primeiro commit pode demorar 30-60min; nesse intervalo o
  check remoto dá falso-negativo. Em setup multi-worktree (este repo),
  worktrees compartilham `.git/refs/` — `git worktree list` mostra
  agentes rodando em paralelo no mesmo clone.
- **Stale** (>24h sem commit em remoto **E** worktree sem activity
  recente) pode ser retomado — anuncie, faça `git log <branch>` +
  `git diff origin/main...<branch>` para entender onde parou, e
  continue OU abra nova branch (`agent/<slug>/<novo-ts>`) partindo de
  `origin/main`.
- **Sprint atual + lanes abertas**: [docs/BACKLOG.md §Sprint A6](docs/BACKLOG.md)
  tem o diagrama de ondas e a tabela de lanes. Essa é a fonte única;
  ROADMAP aponta para lá. A tabela marca lanes 🚧 ocupadas com o slug
  da branch ativa — mas **não confie só nela**: confirme com os 2
  comandos acima (a tabela pode estar desatualizada).

### Naming de branch

`agent/<slug-kebab>/<yyyyMMdd-HHmm>` — ex.:
`agent/a6d1-globals-e4/20260420-1430`. Slug descritivo curto (≤40 chars).
Timestamp evita colisão entre agentes. **Crie a branch antes da primeira
edição**, não depois — edits em `main` local podem ser destruídos por
`git reset --hard` de outro agente.

**Worktree em `.claude/worktrees/<slug>/` é especialmente perigoso:** a
branch default (`claude/<slug>`) é compartilhada por qualquer sessão
Claude que reabra o mesmo worktree — edits uncommitted podem ser
revertidos entre turnos quando outra sessão/hook mexe no working tree.
Regra: **primeira ação ao entrar num worktree `.claude/worktrees/` é**
```bash
git status  # confirma clean ou entende o que tem
git checkout -b agent/<slug>/<yyyyMMdd-HHmm>
```
antes de qualquer Edit/Write. Isso isola sua linha de trabalho de resets
externos. Se já está numa branch `agent/*`, não recrie — continue nela.

### Cadência de commit (defensiva contra resets)

- **Nunca termine uma resposta com working tree sujo.** Se fez edits e vai
  devolver a palavra ao usuário (pedir confirmação, aguardar decisão,
  entregar resultado pra validação), **commit WIP antes** — mesmo que seja
  `chore(wip): gate A, aguardando aprovação p/ gate B`. A janela de risco
  não é "pausa longa"; é **qualquer gap entre turnos**, porque o turno do
  usuário pode ativar outro agente/aba/hook que toque o worktree. Perder
  edits uncommitted é assimétrico: commit WIP custa 5 segundos, reversão
  custa refazer 20 minutos e quebra confiança. Trade-off aceito: commits
  WIP poluem histórico — squash no merge é barato.
- **Commite a cada marco atômico** (criou repo, criou DTOs, refatorou
  endpoint) — commits sobrevivem a `git reset --hard HEAD` na branch.
- Trabalhe em sua branch (§naming); edits em `main` local podem ser
  destruídos por reset de outro agente.
- Pausando/fechando a sessão → commit antes, mesmo WIP
  (`chore(wip): ponto de parada A6e.3`). Push opcional; commit local já
  é seguro.
- `git diff --stat` >150 linhas sem commit → **commite agora**.

### Abrir PR e mergear em `main`

1. `git fetch origin && git rebase origin/main` na sua branch `agent/*`.
2. Rode a suíte **depois** do rebase (não antes). Quebrou pós-rebase →
   investigue e corrija antes de pushar.
3. `git push origin agent/<slug>/<ts>` — push para sua branch (nunca em `main`).
4. **Abra PR** contra `main`:
   ```bash
   gh pr create --base main --title "<conventional commit>" --body "$(cat <<'EOF'
   ## Sumário
   - …
   ## Como testar
   1. …
   EOF
   )"
   ```
   Template completo em `.github/PULL_REQUEST_TEMPLATE.md` é injetado
   automaticamente; preencha o checklist.
5. **Aguarde CI verde** — job `All checks green` é gate obrigatório.
6. **Habilite auto-merge** (`gh pr merge <N> --squash --auto`) ou peça
   review se PR não-trivial. **Squash é o único método** — preserva
   `main` linear, e commit message vira título do PR (Conventional Commits).
7. Após merge: `git fetch origin && git log -1 origin/main` confirma o
   commit-merge. Em sua máquina: `git checkout main && git pull
   --ff-only && git branch -d agent/<slug>/<ts>` (auto-delete remoto
   também ocorre).

### Hotspots de documentação

`CLAUDE.md`, `CHANGELOG.md`, `BACKLOG.md`, `DECISIONS.md` são editados em
quase toda sessão — colisão entre agentes é garantida se todos concorrem.

**Pre-flight obrigatório antes de tocar qualquer hotspot:**

```bash
git fetch origin
git log -5 --oneline origin/main -- <arquivo>
```

Se o último commit no arquivo é de outro autor/agente e <30min atrás,
**pause**: anuncie no chat ("vou editar CLAUDE.md §X por ~Y min"), espere
2min, então edite + commite + push **no mesmo turno** (janela ≤5min). Se
`git log` mostra atividade recente em 2+ hotspots, outro agente está num
pacote de docs maior — **adie seu edit** para depois do push dele.

Demais regras:

- Commite docs **separado** do código (`docs(<slice>): ...`).
- Commite docs **por último na sessão**, depois do push do código.
- Conflito em `git stash pop` nesses arquivos → resolva **mantendo todas**
  as adições; nunca descarte conteúdo alheio.
- **Não edite CLAUDE.md em paralelo** com outro agente. Anuncie antes,
  edit + commit atômico (≤5 min).

### Proibido

- **`git push origin main`** direto — Repository Ruleset enforça
  PR-flow. Bypass exige autorização explícita do owner; nunca é default.
- **`git push --force`** / `--force-with-lease` em `main`. Em branches
  próprias pré-PR, aceitável para limpar histórico antes de pushar.
- **Merge commits em `main`** — apenas squash-merge é permitido (config
  do repo). Mantém histórico linear.
- **`git commit --no-verify`** ou skip de hooks — hooks bloqueiam dados
  sensíveis. Falhou legitimamente → **corrija a causa**, nunca bypasse.
- **`git commit --amend`** em commits já pushados — crie novo commit
  (`fix:` ou `chore: correct X`).
- **`git reset --hard`** em branch compartilhada, **incluindo `main`
  local quando outros agentes estão ativos no mesmo working tree**. Caso
  contrário, apaga working tree de outros. Para ressincronizar com
  remoto sem destruir, prefira `git pull --ff-only origin main`.
- **`gh pr merge --admin`** ou bypass de Ruleset sem aprovação explícita
  do owner. Mesmo em "fix urgente", abrir PR com label `security`
  + auto-merge é o caminho.
- **`git config`** — não alterar configuração global/local do git.
- **Paths proibidos no staging** — ver "Regras críticas › Paths proibidos".
- **Dados sensíveis** em commits, docstrings ou fixtures.

### Ferramentas

- Proteção é do `pre-commit`, não do caminho do commit. Setup:
  [docs/SETUP.md](docs/SETUP.md). `git commit` direto e `dev/commit.py`
  passam pelos mesmos guardrails.
- `dev/commit.py` é atalho opcional com `--dry-run` + push integrado.
  Vive em `dev/` (não em `scripts/`) para não se confundir com etapas do
  pipeline.

### Rebase com múltiplos commits pendentes

Quando `git rebase origin/main` para numa série de N commits a replay,
**antes de resolver o primeiro conflito**:

```bash
cat .git/rebase-merge/git-rebase-todo
# worktrees: .git/worktrees/<name>/rebase-merge/git-rebase-todo
```

Leia **todos** os commits pendentes (`git show <hash>` se precisar ver
o diff). Se um commit mais à frente na lista já traz o conteúdo que
você ia adicionar numa resolução anterior:

- **Não pré-adicione.** Resolva o conflito atual com o mínimo necessário
  (normalmente mantendo o lado `HEAD` e removendo os marcadores) e deixe
  o commit futuro aplicar o conteúdo dele sozinho.
- **Pré-adicionar produz auto-conflito** — o commit futuro tenta inserir
  o que você já pôs; git vê como divergência e quebra.

Se os commits pendentes têm sobreposição ruim (ex.: C3 duplica C1+C2),
use `git rebase -i` e faça `squash`/`fixup` **antes** de continuar.

### Se CI quebra em PR aberto

1. Investigue o job que falhou — `gh pr checks <N>` lista. Logs em
   `gh run view <run-id> --log-failed`.
2. Reproduza local: pra falha de teste, rode o teste específico; pra
   falha de lint, rode `pre-commit run --all-files`.
3. Fix em novo commit na branch (não rebase em commits pushados —
   `--force-with-lease` em branch agent/* aceitável **se ninguém mais
   abriu PR baseado nela**).
4. Push triggera novo CI run; auto-merge re-avalia.

### Se CI quebra em `main` (após merge de PR)

Sinal raro com Ruleset ativo (`All checks green` é gate), mas pode acontecer
com flaky tests, drift de deps externos ou ambiente.

1. **Anuncie imediatamente** — "CI quebrou em `main` no commit `abc1234`
   (job X). Investigando."
2. **Revert** preferível a fix-forward — `gh pr create` com revert
   commit, mergea rápido. `main` volta a verde, fix real vem em PR
   separado.
3. **Nunca** deixe `main` quebrada overnight sem comunicar.

### Prefixos aceitos de mensagem

Fonte de verdade: `dev/validate_commit_msg.py`. Conventional Commits
padrão (`feat|fix|refactor|perf|test|chore|backend|frontend|api|db|infra|ci|docs|update`)
com escopo opcional — `feat(api): ...`, `refactor(e5): ... (A6d.1)`.
Prefixos legados (`pipeline|config|E1..E7|E-reset|pre-reset`) mantidos
por compat histórica.

---

## Fontes de verdade

Consulte antes de inferir regras de domínio ou layout:

| Recurso                           | Função                                                                    |
| --------------------------------- | ------------------------------------------------------------------------- |
| `docs/ARCHITECTURE.md §4.1 Domain glossary` | Índice de regras de domínio (rules-as-code, ADR-143) — aponta para o módulo enforcer + ADR canônica de cada conceito |
| `config/pipeline.json`            | Parâmetros operacionais (inclui `report_version`, schema validation)      |
| `config/report_layout.yaml`       | Seções e componentes do relatório (com comentários inline) — source-of-truth do codegen `dev/codegen_report_layout.py` (ADR-076) |
| `config/schemas/*.schema.json`    | Contratos JSON por etapa                                                  |
| `pipeline.stage_spec.STAGE_REGISTRY` | Source of truth de execução de stages (+ `STAGE_RENAME_MAP` para F9)   |
| `ConfigStore` protocol (DB-first) | `family_members`, `categorization`, `institutions`, `report_layout`, `transferencias_internas` (Sprint A7.0–A7.5 · ADR-134). Workspace lê via `DBConfigStore` em `WorkspaceContext.config_overrides`. |
| `fiscal_parameters` + `market_rates` (DB) | Tabelas globais versionadas por data — IRPF/PGBL/lucro presumido (ADR-135) e câmbio (USD/BRL, EUR/BRL). Substituiu `parametros_fiscais.json` + `taxas.json` em Sprint A7.2b. |
| `category_template` + `workspace_category_overrides` + `institution_catalog` (DB) | Catalog global versionado + diff por workspace (ADR-137 · A7.3). Substituiu `categorization.json` + `institutions.json` legados. |
| `Decision` aggregate (DB)         | Plano de Ação event-sourced (ADR-136 · A7.2a). Substituiu `decisions.md` editorial. |

**Manual histórico (referência):** `_archive/manual_operacao_v6.1.md` —
pipeline CLI legado.

Em caso de dúvida sobre como o pipeline funciona, consulte scripts,
configs e docstrings antes de agir.

---

## Classificação de documentos — duas vias (ADR-081)

**Classificação unificada (P2):** núcleo em
`backend/app/services/document_classification.py` (`classify_document`,
`ClassificationResult`). Upload web, `POST /documents/reclassify` e
`e0_route.route_file` (quando o pacote `backend` é importável) usam o
**mesmo** fluxo: regex sobre **conteúdo** extraído → LLM opcional
(confidence < 0,8) → `needs_review` se confidence < 0,7.

1. **E0-route (`scripts/e0_route.py`):** com backend disponível, chama
   `classify_document` (content-first, nome ignorado). **Sem** backend
   (CLI isolado), fallback legado: regex no **nome do arquivo** + LLM.
2. **Web (upload):** `document_processor.process_uploaded_document`
   chama `classify_document` após unlock; `content_classifier.py` é a
   camada regex sobre o preview.
   - Requer `anthropic` SDK + `ANTHROPIC_API_KEY` no env do backend para
     o LLM fallback.
   - Sem a key, degrada para só regex (docs ambíguos → `needs_review=true`).
   - `map_e0_doc_type_to_document_type()` mapeia códigos E0 (ex.:
     `faturaunique`, `extratocontabrl`) para a enum `DocumentType`.

---

## Dedupe de uploads

- **Exato:** SHA-256 do conteúdo → partial unique index
  `(workspace_id, content_hash)`. Mesmo arquivo = bloqueado.
- **Fuzzy:** se `(doc_type, bank_code, period)` já existe com hash
  diferente → `possible_duplicate_of_id` aponta para o existente +
  `needs_review=true`. Não bloqueia; UI mostra para o usuário decidir.

---

## Design System (ADR-076 · F9)

- **Fonte de verdade:** `design-tokens/tokens.json` — gera CSS para
  Next.js via `python3 design-tokens/build.py`.
- **Codegen do layout:** `config/report_layout.yaml` →
  `frontend/src/generated/report-layout.ts` +
  `backend/app/generated/report_layout.py` via
  `python3 dev/codegen_report_layout.py`.
- **Fontes:** Plus Jakarta Sans (display), Inter (body), JetBrains Mono
  (monetário). Carregadas via `next/font/google` no `layout.tsx` —
  **não redefinir no CSS**.
- **Relatório nativo:** `frontend/src/components/report/` é o **único**
  renderer (rota `/reports/[id]`). Export server-side é PDF via Playwright
  ([backend/app/services/pdf_renderer.py](backend/app/services/pdf_renderer.py))
  sobre a mesma rota. Não existe renderer HTML server-side — descontinuado
  em [ADR-129](docs/DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
- **Cores:** nunca hex literal no frontend — sempre `var(--brand-*)`,
  `var(--surface-*)`, `var(--semantic-*)`.
- **Valores monetários:** sempre `<MonetaryValue/>` (font-mono +
  tabular-nums).

---

## Convenções de código do pipeline

- Scripts em `scripts/` seguem `eN_nome.py` (e0, e2, e3…). Exceção:
  `pipeline_common.py` (módulo compartilhado — paths, config, JSON I/O,
  atomic writes, schema validation, structured logging).
- Scripts E0 importam paths/config via
  `import scripts.pipeline_common as _pc`.
- Parsers de E2 ficam em `scripts/e2/banks/<banco>.py` — um módulo por
  banco, com lista `PARSERS` exportada. Novo banco = novo arquivo em
  `scripts/e2/banks/`.
- Stage E6 (renderer HTML standalone) foi **removido** em
  [ADR-129](docs/DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).
  `scripts/e6_render.py`, `scripts/e6/`, `scripts/e6_regen.py` e
  `pipeline/stages/e6.py` não existem mais — relatório é só React.
- Valores monetários em BRL usam formato brasileiro (`1.234,56`) nos
  documentos e float (`1234.56`) nos JSONs.

---

## Convenções de naming de artefatos

Sufixos de etapa por fase do pipeline:

| Sufixo              | Etapa               | Exemplo                                                 |
| ------------------- | ------------------- | ------------------------------------------------------- |
| `-0_original`       | E0 (roteamento)     | `c6bank_extratoconta_202601-0_original.csv`             |
| `-1a_extract`       | E1 (extração LLM)   | `david_curriculo-1a_extract.json`                       |
| `-1b_unified`       | E1 (unificação)     | `members-1b_unified.json`                               |
| `-1c_enriched`      | E1 (enriquecimento) | `members-1c_enriched.md`                                |
| `-1.5_consolidated` | E1.5 (baseline)     | `baseline_patrimonial-1.5_consolidated.json`            |
| `-1.6_irpf_full`    | E1.6 (`extract_irpf_full`) | `irpfdeclaracaodavid2024-1.6_irpf_full.json`     |
| `-2_extract`        | E2 (extração)       | `itau_extratoconta_202601_202604-2_extract.json`        |
| `-3_reconciled`     | E3 (reconciliação)  | `itau_extratoconta_BRL_202212_202604-3_reconciled.json` |
| `-4_unified`        | E4 (categorização)  | `despesas-4_unified.json`                               |
| `-5_analysis`       | E5 (análise)        | `analise_financeira-5_analysis.json`                    |

Nomes de banco em filenames seguem o código canônico de
`institutions.json` (ex.: `bankofamerica`, `btgpactual`, `c6bank`,
`itau` — sem espaços, sem acentos).

**Período sentinel `999999`:** usado em faturas de cartão cujo período
não pôde ser determinado. Propaga de E0→E2→E3.

---

## Convenções intencionais (não "arrumar" em refactor)

- `config/report_layout.yaml` — **único YAML** do projeto; justificado por
  extensos comentários inline que seriam perdidos em JSON.
- `baseline_patrimonial-1.5_consolidated.json` vive em `E2_extracts/` —
  input direto do E3/E4/E5; convenção histórica documentada.
- Sufixos mistos nos diretórios `processed/` (`E2_extracts` substantivo,
  `E3_reconciled` particípio, `E4_unified` particípio, `E5_analysis`
  substantivo, `E7_review` substantivo) — padrão aceito, não renomear.
- `inbox_processed/` sem prefixo `_` — é parte do fluxo de dados, não
  diretório auxiliar.
- `config/schemas/` contém 5 schemas de dados (E1.5, E2, E4, E5,
  pipeline). Modo `warn` (default) vs `strict` controlado por
  `pipeline.json → schema_validation.enabled`.

Para outras decisões idiossincráticas, consulte [docs/DECISIONS.md](docs/DECISIONS.md).

---

## Comandos principais

Agente use `--help` nos scripts para descobrir flags. Comandos canônicos
de teste estão em §Code style › Testes. Para ops avançadas (smoke test,
seed, cutover DB, comparação disk↔DB), ver
[docs/RUNBOOK.md](docs/RUNBOOK.md) e
[docs/SMOKE_TEST_HUMAN.md](docs/SMOKE_TEST_HUMAN.md). CLI do pipeline
(`scripts/e0_audit.py`, `scripts/e2_extract.py`, `scripts/e_reset.py`…):
cada script expõe `--help`.

---

## Onde procurar contexto adicional

Conteúdo que **era** duplicado neste arquivo e agora vive em sua fonte
única:

| Pergunta                                            | Onde olhar                                                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Estrutura de diretórios completa (backend/pipeline/frontend/…) | [docs/ARCHITECTURE.md §10](docs/ARCHITECTURE.md)                               |
| Tabela completa de stages + `FULL_ORDER` + `DETERMINISTIC_ORDER` | [docs/ARCHITECTURE.md §7](docs/ARCHITECTURE.md)                              |
| Modo incremental (ADR-080) — API, filtragem, UI     | [docs/ARCHITECTURE.md §7](docs/ARCHITECTURE.md)                                            |
| Arquitetura alvo pós-A6 (migração infra+domínio)    | [docs/ARCHITECTURE.md §17](docs/ARCHITECTURE.md)                                           |
| Sprint atual da migração (A5f, A6a-f, A6-human, A6c, A6d…) | [docs/BACKLOG.md — Sprint A6](docs/BACKLOG.md)                                      |
| Log cronológico de entregas (sessões A1–A6f por data) | [docs/CHANGELOG.md](docs/CHANGELOG.md)                                                   |
| ADRs (001–148+) e rationale de decisões — ToC categorizado no topo, gates em [dev/check_adr_anchors.py](dev/check_adr_anchors.py), [dev/build_adr_toc.py](dev/build_adr_toc.py), [dev/validate_adr_format.py](dev/validate_adr_format.py); cheat-sheet de criação no preâmbulo do arquivo + protocolo em §"ADRs → docs/DECISIONS.md" deste CLAUDE.md | [docs/DECISIONS.md](docs/DECISIONS.md)                       |
| Domínios e URLs públicas (ADR-108)                  | [docs/ARCHITECTURE.md §18](docs/ARCHITECTURE.md)                                           |
| Smoke test humano (gate pré-A6c)                    | [docs/SMOKE_TEST_HUMAN.md](docs/SMOKE_TEST_HUMAN.md)                                       |
| Artefatos de pipeline + schemas                     | [docs/PIPELINE_ARTIFACTS.md](docs/PIPELINE_ARTIFACTS.md)                                   |
| Motor canônico P0/P1                                | [docs/CANONICAL_ENGINE_P0.md](docs/CANONICAL_ENGINE_P0.md)                                 |
| Testes — estratégia e fixtures                      | [docs/TESTING.md](docs/TESTING.md)                                                         |
| Tenancy (multi-workspace)                           | [docs/tenancy.md](docs/tenancy.md)                                                         |
| DB schema de referência (auto-gerado)               | [docs/DB_SCHEMA_REFERENCE.md](docs/DB_SCHEMA_REFERENCE.md)                                 |
| Fluxo de PR (humano + agente) — branch naming, template, gates locais + CI, Dependabot, stale bot | [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) |
| Política de disclosure de vulnerabilidades (LGPD)   | [SECURITY.md](SECURITY.md)                                                                  |
| Plano canônico do shell Report Premium — v1 (10 fases ✅) + v2 §17 (🚧, ondas A-F paralelizadas), paridade React com EXEMPLO_DE_RELATORIO.html, único renderer pós-ADR-129 | [docs/REPORT_PREMIUM_PLAN.md](docs/REPORT_PREMIUM_PLAN.md)                      |
| Cutover final `config/goals.json` (Sprint A10, ✅ entregue 2026-05-07) — 9 lanes em 4 ondas, 5 ADRs (ADR-177 a ADR-181), 22 chaves do legado migradas para destinos canônicos; fechou checkbox ADR-077 §"Contrato de cutover" após 7 meses | [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md](docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) |
| Platform review canônico (Sprint A11, origem 2026-05-06) — 32 tasks em 6 ondas, 138 findings consolidados de revisão multi-agente (data-engineer + financial-planner + product-designer + sre-devops + build-vs-buy + senior-cto), 6 ADRs Proposto (ADR-170 a ADR-175), W1 ✅ entregue | [docs/PLATFORM_REVIEW_PLAN.md](docs/PLATFORM_REVIEW_PLAN.md) |
