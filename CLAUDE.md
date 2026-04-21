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

## "Concluído" = commit mergeado em `main` com CI verde

Uma tarefa **só é concluída** quando:

1. `git fetch origin && git log origin/main --oneline | head -5` mostra o
   commit final em `origin/main`
2. CI está verde nesse commit

**Não conta como concluído:**

- Commit apenas local, mesmo com suíte verde localmente
- Branch pushed sem merge — "aguardando review/CI" continua `in_progress`
- Trabalho em worktree/branch de agente ainda não integrado a `main`

**Ao reportar estado, seja explícito:** "commitado e pushed na branch X,
aguardando merge" ≠ "mergeado em `main` (commit `abc1234`)". Se rastreia a
tarefa em TodoWrite, `BACKLOG.md` ou plano, só marque `completed` **após o
merge confirmado**; até lá, `in_progress`.

**Why:** commits locais e branches pendentes se perdem (reset, conflito de
rebase, PR abandonado). Outros agentes só podem confiar que o trabalho
"existe" se está em `main`.

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
- **Go** (futuro A6f): **sem `interface{}`/`any`** fora de util genérico.
  Tipos concretos em assinaturas. Errors tipados
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
- **Goldens de paridade** (Caminho B): legado ↔ novo, tolerância `0.01` BRL
  em whitelist monetária. Padrão: `tests/test_e3_main_with_store_parity.py`.
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

## Regras críticas (invariantes do repositório)

### Idioma e dados sensíveis

- **Idioma:** português brasileiro, salvo quando arquivos/APIs/convenções
  técnicas exigirem inglês.
- **Dados sensíveis:** **nunca** expor CPFs, valores monetários reais,
  senhas, documentos pessoais ou conteúdo financeiro bruto em commits,
  logs, exemplos, docstrings, fixtures ou outputs de console.

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

### Stage identifiers — use nomes legados até F9 (ADR-093)

Em código, DB (`pipeline_artifacts.stage`) e logs, use os identificadores
**legados** (`"E2"`, `"E3"`, `"E5"`…). Nomes descritivos
(`"extract_statements"`, `"reconcile_transactions"`…) estão mapeados em
`STAGE_RENAME_MAP` (ver `pipeline/stage_spec.py`) e só entram em vigor na
Fase 9. Fonte de verdade de execução: `pipeline.stage_spec.STAGE_REGISTRY`.

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

Default `False`. Controla cutover DB do `ArtifactStore`. Durante transição,
`MaterializationBridge` permite scripts legados rodarem com DB-backed
store. Por workspace: `workspaces.use_db_artifacts_override: bool | None`
(None = global flag, True = força DB, False = força disco).

### Paths proibidos no git (enforçados por `dev/check_forbidden_paths.py`)

`storage/`, `data/`, `inbox/`, `inbox_processed/`, `_scratch/`, `.env`,
`.env.test`, `mathoms.db`, `config/passwords.txt`, `*.db`, `*.sqlite`.
Hook bloqueia antes do commit.

### URLs canônicas (ADR-108)

Produto: `app.mathoms.ai` · API: `api.mathoms.ai/v1/...` · Console interno:
`ops.mathoms.ai` · Landing: `mathoms.ai`. Staging: `*.staging.mathoms.ai`.
Dev local: `localhost:3000` (app) + `localhost:8000` (api). Detalhes:
[docs/ARCHITECTURE.md §18](docs/ARCHITECTURE.md).

---

## Git e commits

Merge em `main` é o único marco de conclusão — ver
**"Concluído"** acima.

**Autonomia autorizada:** agentes **podem e devem** criar branches, fazer
commits e dar push, inclusive em `main` quando a suíte está verde. **Não
precisa pedir aprovação; é obrigatório anunciar** cada operação git em
1-2 linhas (ex.: "Commit `abc1234` — `feat(...): ...`", "Push para
`main` (5 commits, CI disparado)").

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
5. **Pre-push drift check** — imediatamente antes de `git push origin main`:

   ```bash
   git fetch origin
   BEHIND=$(git rev-list --count HEAD..origin/main)
   if [ "$BEHIND" -gt 0 ]; then
     git rebase origin/main            # re-sincroniza
     pytest backend/tests -q           # regressão silenciosa de rebase
   fi
   ```

   Pushar sem esse check produz (a) `push` rejeitado por non-fast-forward
   ou (b) tentação de `--force` — ambos proibidos em `main`. Enforçado
   também como hook pre-push em `dev/check_main_drift.py`.
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

### Cadência de commit (defensiva contra resets)

- **Commite a cada marco atômico** (criou repo, criou DTOs, refatorou
  endpoint) — commits sobrevivem a `git reset --hard HEAD` na branch.
- Trabalhe em sua branch (§naming); edits em `main` local podem ser
  destruídos por reset de outro agente.
- Pausando/fechando a sessão → commit antes, mesmo WIP
  (`chore(wip): ponto de parada A6e.3`). Push opcional; commit local já
  é seguro.
- `git diff --stat` >150 linhas sem commit → **commite agora**.

### Push para `main`

1. `git fetch origin && git rebase origin/main` na sua branch.
2. Rode a suíte **depois** do rebase (não antes). Quebrou pós-rebase →
   investigue e corrija antes de push.
3. `git push origin main` — **fast-forward only**. Se falhar por
   non-fast-forward, **não force** — refaça o rebase.

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

- **`git push --force`** / `--force-with-lease` em `main`. Em branches
  próprias pré-push inicial, aceitável para limpar histórico.
- **`git commit --no-verify`** ou skip de hooks — hooks bloqueiam dados
  sensíveis. Falhou legitimamente → **corrija a causa**, nunca bypasse.
- **`git commit --amend`** em commits já pushados — crie novo commit
  (`fix:` ou `chore: correct X`).
- **`git reset --hard`** em branch compartilhada, **incluindo `main`
  local quando outros agentes estão ativos no mesmo working tree**. Caso
  contrário, apaga working tree de outros. Para ressincronizar com
  remoto sem destruir, prefira `git pull --ff-only origin main`.
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

### Se CI quebra após push para `main`

1. **Anuncie imediatamente** — "CI quebrou no commit `abc1234` (job X).
   Investigando."
2. **Fix-forward** (novo commit) preferível a revert se o fix é trivial
   (<10 min).
3. **Revert** se vai demorar — deixa `main` verde; branch nova para o
   fix real.
4. **Nunca** deixe `main` quebrada overnight sem comunicar.

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
| `config/definitions.md`           | Membros, instituições, categorias, regras especiais                       |
| `config/pipeline.json`            | Parâmetros operacionais (inclui `report_version`, schema validation)      |
| `config/family_members.json`      | Dados cadastrais canônicos                                                |
| `config/institutions.json`        | Padrões de bancos e tipos de documento                                    |
| `config/categorization.json`      | Keywords de categorização                                                 |
| `config/report_layout.yaml`       | Seções e componentes do relatório (com comentários inline)                |
| `config/schemas/*.schema.json`    | Contratos JSON por etapa                                                  |
| `pipeline.stage_spec.STAGE_REGISTRY` | Source of truth de execução de stages (+ `STAGE_RENAME_MAP` para F9)   |

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
  Next.js e E6 standalone via `python3 design-tokens/build.py`.
- **Codegen do layout:** `config/report_layout.yaml` →
  `frontend/src/generated/report-layout.ts` +
  `backend/app/generated/report_layout.py` via
  `python3 dev/codegen_report_layout.py`.
- **Fontes:** Plus Jakarta Sans (display), Inter (body), JetBrains Mono
  (monetário). Carregadas via `next/font/google` no `layout.tsx` —
  **não redefinir no CSS**.
- **Relatório nativo:** `frontend/src/components/report/` é o render React
  primário (rota `/reports/[id]`). `e6_render.py` é exportador standalone
  (email, backup).
- **Cores:** nunca hex literal no frontend — sempre `var(--brand-*)`,
  `var(--surface-*)`, `var(--semantic-*)`.
- **Valores monetários:** sempre `<MonetaryValue/>` (font-mono +
  tabular-nums).

---

## Convenções de código do pipeline

- Scripts em `scripts/` seguem `eN_nome.py` (e0, e2, e3…). Exceção:
  `pipeline_common.py` (módulo compartilhado — paths, config, JSON I/O,
  atomic writes, schema validation, structured logging) e `e6_regen.py`
  (utilitário visual).
- Scripts E0 importam paths/config via
  `import scripts.pipeline_common as _pc`.
- `scripts/e6/` contém submódulos de `e6_render.py`: `sanitize.py`
  (formato monetário), `validate.py` (19 checks V1–V19 no HTML).
- Parsers de E2 ficam em `scripts/e2/banks/<banco>.py` — um módulo por
  banco, com lista `PARSERS` exportada. Novo banco = novo arquivo em
  `scripts/e2/banks/`.
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
| ADRs (076–109) e rationale de decisões              | [docs/DECISIONS.md](docs/DECISIONS.md)                                                     |
| Domínios e URLs públicas (ADR-108)                  | [docs/ARCHITECTURE.md §18](docs/ARCHITECTURE.md)                                           |
| Smoke test humano (gate pré-A6c)                    | [docs/SMOKE_TEST_HUMAN.md](docs/SMOKE_TEST_HUMAN.md)                                       |
| Artefatos de pipeline + schemas                     | [docs/PIPELINE_ARTIFACTS.md](docs/PIPELINE_ARTIFACTS.md)                                   |
| Motor canônico P0/P1                                | [docs/CANONICAL_ENGINE_P0.md](docs/CANONICAL_ENGINE_P0.md)                                 |
| Testes — estratégia e fixtures                      | [docs/TESTING.md](docs/TESTING.md)                                                         |
| Tenancy (multi-workspace)                           | [docs/tenancy.md](docs/tenancy.md)                                                         |
| DB schema de referência (auto-gerado)               | [docs/DB_SCHEMA_REFERENCE.md](docs/DB_SCHEMA_REFERENCE.md)                                 |
