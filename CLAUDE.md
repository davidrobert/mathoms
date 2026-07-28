# CLAUDE.md — Mathoms AI

> Instruções para **agentes LLM** trabalhando neste repositório. Apenas regras
> **timeless** (princípios, convenções, protocolos). Estado dinâmico — sprint
> atual, sessões, deltas — vive nos arquivos ligados abaixo.
>
> **Referências dinâmicas (leia sob demanda):**
>
> - Contexto mínimo por intenção · [docs/_MOC/_generated/CONTEXT_INDEX.md](docs/_MOC/_generated/CONTEXT_INDEX.md) (auto); comece por 1 context pack antes de abrir docs longos
> - Sprint atual + lanes prontas · [docs/_MOC/_generated/SPRINT_CURRENT.md](docs/_MOC/_generated/SPRINT_CURRENT.md) (auto) + [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md) (editorial); BACKLOG.md é shim
> - Log cronológico de entregas · [docs/CHANGELOG.md](docs/CHANGELOG.md)
> - ADRs (vault atomizado) · [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) + [docs/adr/](docs/adr/); DECISIONS.md é shim
> - Arquitetura técnica (stack, models, stages, pastas) · [docs/reference/ARCHITECTURE.md](docs/reference/ARCHITECTURE.md)
> - Setup dev · [docs/reference/SETUP.md](docs/reference/SETUP.md)
> - Runbook operacional · [docs/reference/RUNBOOK.md](docs/reference/RUNBOOK.md)
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

<!-- BEGIN auto-gen subagent catalog -->

<!-- Esta lista é auto-gerada por dev/build_subagent_catalog.py. -->
<!-- Para editar, modifique .claude/agents/<slug>.md (frontmatter `description`) e rode: -->
<!--   python3 dev/build_subagent_catalog.py --inline -->

- **[build-vs-buy](.claude/agents/build-vs-buy.md)** — Especialista sênior em estratégia de produtos e serviços de tecnologia, focado em decisão **build vs. buy** (construir in-house vs. adotar SaaS/lib/framework/serviço gerenciado pronto).
  Use ao avaliar adoção/substituição de dependência substantiva — auth provider, error tracking, queue, DB managed, search, payment, banking aggregator, OCR/parsing, LLM provider, analytics, CMS, design system de terceiros, observability stack, feature flag service, e correlatos.
  NÃO invoque para libs triviais (utility lib < $5k esforço comparável), bugs, ou decisões de UI puras.
- **[data-engineer](.claude/agents/data-engineer.md)** — Engenheiro de Dados sênior com 15+ anos em modelagem de bancos relacionais, data lakes, pipelines ETL/ELT, MLOps e LLMOps.
  Use para revisar schema de DB (modelos SQLAlchemy, índices, partitioning, FKs, migrations Alembic), contratos de dados entre stages do pipeline (E0→E7), idempotência e backfill, schema evolution (JSON Schema em `config/schemas/`, snapshot OpenAPI), política de retenção de artefatos, paridade legado↔novo (goldens), eval/drift/custo de LLM, e arquitetura de armazenamento (DB vs. blob store vs. cache).
  NÃO invoque para bugs de UI, decisões puramente arquiteturais cross-cutting (use senior-cto), ou regras de domínio financeiro (use financial-planner).
- **[financial-planner](.claude/agents/financial-planner.md)** — Especialista sênior em planejamento financeiro e patrimonial brasileiro.
  Use para revisar requisitos, features, regras de domínio e UX do Mathoms sob a ótica de metodologias consagradas (Viver de Renda / Bruno Perini, Equilíbrio Financeiro / Gustavo Cerbasi, AUVP / Raul Sena).
  NÃO invoque para bugs puros de código, CI, ou mudanças técnicas sem dimensão de produto.
- **[gtm-strategist](.claude/agents/gtm-strategist.md)** — Estrategista sênior de posicionamento, narrativa de marca, pricing strategy, GTM (go-to-market) e resposta competitiva, com 15+ anos em B2C/B2B2C SaaS e fintech/wealth-tech. Domina frameworks de positioning (April Dunford), segmentação/adoção (Geoffrey Moore), pricing baseado em valor (Madhavan Ramanujam), JTBD (Christensen/Ulwick) e canais (SEO/conteúdo/embaixadores/parcerias).
  Use para definir pilares narrativos antes de copy de landing, escolher estrutura de pricing (free vs. trial vs. paywall), responder estrategicamente a concorrente, refinar ICP/segmentação, decidir canais GTM, ou enquadrar diferenciação competitiva.
  NÃO invoque para execução de copy/UI (use `product-designer`), priorização de sprint (use `product-manager`), regras de domínio financeiro (use `financial-planner`), arquitetura técnica (use `senior-cto`), ou adoção de SaaS específico (use `build-vs-buy`).
- **[information-architect](.claude/agents/information-architect.md)** — Arquiteto de Informação sênior especializado em Second Brain (PARA, Zettelkasten, LYT/MOCs, BASB / C-O-D-E), Obsidian, Markdown disciplinado e estruturação de documentos em HTML como artefato derivado (ADR-247).
  Use para revisar formato de plano canônico (UPPER_SNAKE de pastas em `docs/plan/<X>/` + `track_<slug>` em `docs/agent_prompts/`), estrutura de ADR atômico (ADR-182), novos MOCs, frontmatter schemas em `docs/_schemas/`, refactor de Wiki/vault, changelog discipline (Keep a Changelog), README hygiene, glossário (forma), runbook (forma), mockup HTML de relatório/dashboard derivado, ou hierarquia semântica de documento longo.
  NÃO invoque para visual styling / cores / tipo / microcopy / escolha de chart (escopo de `product-designer`), priorização de lane / OKR / KR / fases (escopo de `product-manager`), prompts LLM / eval / determinismo (escopo de `prompt-engineer`), código de feature de produto (escopo de `senior-cto`), ou adoção de doc-site externo / mkdocs / Docusaurus / Sphinx (escopo de `build-vs-buy`).
- **[product-designer](.claude/agents/product-designer.md)** — Product Designer sênior especializado em fintech, dashboards financeiros e relatórios de planejamento patrimonial.
  Use para revisar telas, fluxos, componentes, hierarquia de informação, tipografia, uso do design system, acessibilidade (WCAG), responsividade, e clareza de dados financeiros (tabelas, gráficos, valores monetários).
  NÃO invoque para bugs de lógica, mudanças de backend sem UI, decisões puramente arquiteturais, OU estrutura semântica HTML / IDs / anchors / ToC / acoplamento MD↔HTML em documento derivado (escopo de `information-architect`).
- **[product-manager](.claude/agents/product-manager.md)** — Product Manager sênior com 20+ anos em gestão de produto, OKRs e métricas de saúde (North Star, AARRR, HEART), curadoria de BACKLOG/SPRINT, ROADMAP (Now/Next/Later), planejamento de Sprints, priorização (RICE/WSJF/MoSCoW/Kano), discovery (Continuous Discovery/JTBD), MVP/MLP/MMP, Shape Up e Working Backwards. Foco em **priorização, ondas/fases e critério de aceite** de planos canônicos (`docs/plan/<X>/_README.md`) e lanes operacionais (`docs/agent_prompts/track_<slug>.md`).
  Use para revisar lane do BACKLOG, definir KR/OKR, priorizar débito vs. feature, escolher escopo de release (MVP/MLP/MMP), validar pitch de feature, ou refinar prioridade/fases de plano canônico.
  NÃO invoque para regras de domínio financeiro (escopo de `financial-planner`), UX/UI/copy/escolha de gráfico (escopo de `product-designer`), arquitetura técnica / ADR técnica / refactor estrutural (escopo de `senior-cto`), prompts LLM / eval / determinismo (escopo de `prompt-engineer`), forma de plano / frontmatter / MOC / wikilinks / changelog discipline (escopo de `information-architect`), adoção de SaaS substantivo (escopo de `build-vs-buy`), ou posicionamento / pricing / GTM (escopo de `gtm-strategist`).
- **[prompt-engineer](.claude/agents/prompt-engineer.md)** — Engenheiro de prompts LLM sênior especializado em **produção** (system prompt, few-shot, structured output, determinismo, eval com golden set, custo/latência como features, guardrails, observabilidade de prompt e drift detection). Domina o padrão canônico do Mathoms regex→LLM→needs_review (ADR-081) e o ciclo eval-driven do Parecer Planejador + Categorization Learning Loop.
  Use para revisar prompt LLM novo em `config/prompts/`, desenhar/refinar eval golden, decidir temperature/seed/model, validar fallback determinístico, especificar telemetria de prompt (tokens/latência/confidence), ou caçar drift entre versões.
  NÃO invoque para regras de domínio financeiro do output (escopo de `financial-planner`), arquitetura de stages do pipeline (escopo de `senior-cto`), UX do estado `needs_review` ou copy de feedback (escopo de `product-designer`), priorização da feature LLM (escopo de `product-manager`), forma/schema do arquivo YAML que hospeda o prompt (escopo de `information-architect`), ou decisão de provider/lock-in/custo de fornecedor (escopo de `build-vs-buy`).
- **[senior-cto](.claude/agents/senior-cto.md)** — CTO sênior com 20+ anos de experiência em arquitetura de software, sistemas distribuídos, IA/LLMs, DDD, Design Patterns, OO, TDD e SOLID. Especialista em Go, Python, TypeScript e JavaScript.
  Use para revisar decisões arquiteturais, ADRs, design de API, modelagem de domínio, escolhas de stack, estratégia de testes, boundaries entre serviços, trade-offs de performance/consistência/complexidade, e PRs de grande impacto.
  NÃO invoque para typos, bugs triviais, ou tarefas já bem definidas.
- **[sre-devops](.claude/agents/sre-devops.md)** — Engenheiro SRE/DevOps sênior com 15+ anos em confiabilidade de SaaS multi-tenant, segurança aplicada, FinOps, observabilidade, containers (Docker) e infrastructure-as-code (IaC — Terraform/Pulumi/Ansible) e operação de produto em produção.
  Use para revisar SLO/SLA, runbooks, postmortems, deploy strategy (blue/green, canary, rollback), CI/CD, secrets management, política de backup/DR, hardening (auth, rate limit, CSRF/CORS, headers, JWT, Fernet vault), surface de pen-test, capacity planning, instrumentação (logs estruturados, métricas, traces, alertas), custo de cloud (FinOps — sizing, autoscaling, retention, cold storage, modelo de cobrança LLM/blob/DB), Dockerfiles / docker-compose / imagens (multi-stage, base hardening, scan de vuln, pin por SHA, healthcheck, non-root, dockerignore), e IaC (módulos Terraform/Pulumi, state backend + locking, plan/apply gates, drift detection, tagging, secrets via vault).
  NÃO invoque para bugs puros de domínio, UX, ou regras financeiras de produto (use financial-planner).

<!-- END auto-gen subagent catalog -->

Cada arquivo `.claude/agents/<nome>.md` tem o briefing completo.
**Não duplique** o briefing aqui — leia direto.

### Protocolo de delegação

**Co-design > review.** Invoque o especialista ao **planejar** a mudança
(antes de codar) — com premissas + opções + recomendação inicial — não
ao final pra "carimbar" PR pronto. O briefing rende mais quando o custo
de mudar de direção ainda é baixo; consultar tarde produz rubber-stamp
ou retrabalho caro.

**Gatilhos obrigatórios** — antes de propor decisão/PR que envolva:

| Mudança proposta | Especialista |
| --- | --- |
| Dinheiro, fórmula, threshold de domínio, alocação, dívida, reserva, IF, metodologia (Perini/Cerbasi/AUVP) | `financial-planner` |
| Relatório financeiro: mudança no que os números **mostram** ou em **como os dados são calculados / mensurados / agrupados / classificados** (o visual/componente do relatório fica em `product-designer`) | `financial-planner` |
| Schema DB, migration Alembic não-trivial, contrato `config/schemas/*`, contrato entre stages (E0→E7), eval/retenção de LLM | `data-engineer` |
| Componente novo no relatório, copy de produto, escolha de gráfico, hierarquia de informação, design token novo | `product-designer` |
| ADR `Proposto` P0/P1, design de API, modelagem de domínio, refactor estrutural, boundary entre serviços | `senior-cto` |
| Adoção/substituição de SaaS substantivo (auth, queue, OCR, LLM provider, observability, payment, banking aggregator) | `build-vs-buy` |
| Pricing, posicionamento, narrativa, ICP/segmentação, resposta competitiva | `gtm-strategist` |
| Priorização/ondas/fases/KR de plano canônico (`docs/plan/<X>/`), curadoria BACKLOG/SPRINT, OKR/KPI, escopo de release (MVP/MLP/MMP), pitch de feature | `product-manager` |
| Prompt LLM em produção (system prompt, eval golden, determinismo, custo/latência, guardrails, observabilidade), nova chamada LLM, mudança de model/seed, padrão regex→LLM→needs_review (ADR-081) | `prompt-engineer` |
| Formato de plano/MOC/ADR atômico, frontmatter schemas (`docs/_schemas/`), wikilinks, atomicidade (ADR-182), changelog discipline, README/glossário/runbook hygiene (forma), HTML como artefato derivado (ADR-247) | `information-architect` |
| Política CI/CD, secrets, alerta novo, política de backup/RPO/RTO, capacity, FinOps, hardening, Dockerfile / docker-compose / imagem base, módulo IaC (Terraform/Pulumi/Ansible) | `sre-devops` |

Múltiplos gatilhos → invoque os especialistas em **paralelo** (1 mensagem,
N `Agent` calls). Brief mínimo: contexto + premissas + opções consideradas
+ recomendação inicial + pergunta clara ("objeção? trade-off perdido?
ADR ignorada?"). **NÃO peça código** ao especialista — peça **decisão
ou revisão**. Execução é do agente principal.

**Pares frequentes em paralelo** (não é exaustivo — invoque sempre que dois
gatilhos casarem):

- **Plano canônico novo** → `product-manager` (KR/ondas/fases/critério) +
  `information-architect` (filename/frontmatter/MOC entry/wikilinks). PM
  define **o quê/quando**; IA define **onde e como**. Sem o par, plano
  fica priorizado mas sem forma, ou bem-formado sem ancoragem em KR.
- **Dashboard/mockup HTML derivado** → `information-architect`
  (estrutura semântica, anchors, ToC, acoplamento MD↔HTML) +
  `product-designer` (visual, cores, tipo, microcopy). IA cuida da IA;
  PD cuida do visual.
- **Feature LLM nova em produção** → `product-manager` (priorização +
  KR + budget) + `prompt-engineer` (prompt + eval + determinismo +
  observabilidade). PM decide se vale fazer; PE dimensiona como rodar.
- **Schema novo em `docs/_schemas/`** → `information-architect` (forma do
  schema, migration de docs existentes) + `data-engineer` (se o schema
  refletir contrato entre stages ou tabela DB).
- **Runbook novo** → `information-architect` (estrutura, ToC, seções
  padrão) + `sre-devops` (conteúdo operacional, alertas, rollback).

**NÃO delegue para:**

- Bug fix simples (≤30 linhas, com teste de regressão).
- Refactor mecânico, rename, typo, cleanup, diff formatter-only.
- Codegen automático (`frontend/src/generated/`, OpenAPI snapshot,
  `design-tokens/build.py`, `dev/codegen_report_layout.py`).
- Mudança que apenas conforma a uma ADR já decidida sem reabrir a
  decisão.
- Mesmo especialista, mesmo escopo, mesma sessão — não re-invoque
  só pra carimbar.

**Anti-loop.** Objeção do especialista → **1 rodada** de ajuste no plano.
Se a objeção persistir, escale para `senior-cto` que **decide e fecha**.
Sem ping-pong: o custo de bloquear o trabalho excede o ganho de mais
uma rodada.

**Catálogo extensível.** O senior-cto tem autonomia (`Write`/`Edit` em
`.claude/agents/`) para criar novo especialista quando identificar gap
de domínio recorrente não coberto pelos atuais. Critérios e protocolo
em [.claude/agents/senior-cto.md](.claude/agents/senior-cto.md)
§Criação de novos especialistas. Esqueleto para novo agente:
[.claude/agents/_TEMPLATE.md](.claude/agents/_TEMPLATE.md). Após o
senior-cto criar o arquivo, o agente principal roda
`python3 dev/build_subagent_catalog.py --inline` para regenerar o bloco
acima a partir do frontmatter `description` e commita CLAUDE.md +
`.claude/agents/<slug>.md` juntos — sem essa atualização, o orquestrador
não sabe que o agente existe. O hook `subagent-catalog` (pre-commit)
falha se a lista ficar dessincronizada.

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
  (`bank_parser.py`, não `extractors.py` gigante). O `analyze_finances.py` (ex-`e5_analyze.py`) de ~127KB
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
- **Dinheiro nunca é `float`** em memória/cálculo (ADR-090): `Money` /
  `Decimal` em Python. No wire HTTP os DTOs serializam JSON `number` via
  `PlainSerializer` (`MoneyBRL`/`MoneyUSD`, A6g.3b — o frontend TS espera
  `number`); `int64` em cents em Go.

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
  Caminho A foi removido. Re-construção de baselines snapshot (débito **DE-005**,
  [docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)
  §W6-T01) **fechado** pela lane A23.l2
  (`docs/sprint/A23/lanes/A23-l2-golden-substrate.md`): `dev/golden_diff.py`
  (diff valor-a-valor em cents int + manifesto de rebaseline),
  `backend/tests/test_report_view_model_snapshot.py` (snapshot do view-model,
  zero float, `monetary_fields ⊆ snapshot`), `tests/test_e5_conservation_invariants.py`
  (invariantes de conservação por balde, tolerância zero) e fixture sintética
  PII-zero em `tests/fixtures/pipeline_golden/dogfood/`.
- Endpoint JSON novo → teste + rodar `make update-openapi-snapshot`
  (ADR-109).
- **Saúde do test suite (ADR-210)** — pre-commit roda `dev/check_test_health.py`
  para detectar anti-padrões que custam CI sem dar sinal:
  - Parametrize recomputando scan caro (sem `@functools.lru_cache`)
  - Soft-fail (`print` em vez de `pytest.fail`) cuja env de hard-fail
    não está em workflow do CI — use `@pytest.mark.skipif`
  - Migration test sem `pytestmark = pytest.mark.migration` (PR sem
    `backend/alembic/versions/**` skipa via `-m "not migration"`)
  - Test pós-cutover órfão (docstring "Após Sprint X" + sprint
    entregue) — delete em vez de manter rodando
  - `bcrypt.hashpw` em test individual quando o `_fast_bcrypt_for_tests`
    fixture (session autouse, rounds=4) está disponível
  Ao adicionar teste, pergunte: "esse teste dá sinal proporcional ao
  custo de CI?" Se o sinal vem só ocasionalmente (deprecation gate
  futuro, migration one-shot já mergeada), use marker/skipif em vez
  de rodar em todo PR.

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
  `plan/REPORT_PREMIUM/_README.md`, `plan/I18N/_README.md`.
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

### Formato: Markdown canônico, HTML apenas derivado ([[ADR-247]])

`docs/**` é **100% Markdown** — source-of-truth. Gates atuais
(`validate_frontmatter`, `check_doc_links`, `check_adr_anchors`,
`build_doc_index`, `check_doc_filename_id`) assumem MD + frontmatter
YAML + wikilinks `[[X]]`. **Não converter doc canônico para HTML** —
infla tokens (1.5–2.5×), quebra Obsidian (graph/backlinks/Dataview),
polui diff de PR, e wikilinks param de ser refactor-friendly.

**HTML permitido apenas como artefato derivado/efêmero:**

- `_scratch/<slug>.html` — exploratório, gitignored.
- `docs/plan/<X>/assets/<nome>.html` — anexo a plano específico,
  ignorado por gates de doc.
- Rotas em `ops.mathoms.ai` (plano [INTERNAL_ADMIN](docs/plan/INTERNAL_ADMIN/_README.md))
  — código de console interno, não doc.
- Relatório do produto (`/reports/[id]`) — já é React, fora do escopo
  desta política ([[ADR-129]]).

**Casos legítimos** para HTML derivado: dashboard interativo dos 138
findings do PLATFORM_REVIEW, comparativos de approach em ADR
`Proposto`, relatórios sintéticos de revisão multi-agente, mockups.

**Proibido:** HTML substituindo `.md` em `docs/adr/`, `docs/sprint/`,
`docs/plan/<X>/_README.md`, `docs/reference/`, `docs/agent_prompts/`.
HTML como fonte primária em wikilinks de docs canônicos.

### Proibido

- `_scratch/<plano>.md` — gitignored, invisível a outros agentes.
- `.claude/<plano>.md`, `.claude/worktrees/<x>/<plano>.md` — local da
  sessão; não chega ao `main`.
- `<plano>.md` na raiz do repo — `dev/check_forbidden_paths.py` já
  bloqueia muitos paths; raiz é reservada a `README.md`, `CLAUDE.md`,
  `LICENSE`, configs.
- `_archive/` e `archive/` na raiz — deletados do HEAD em A34.l7
  ([[ADR-319]]; concentravam PII histórica). Recriação é bloqueada por
  `dev/check_forbidden_paths.py`; arqueologia de docs vive em `docs/archive/`.
- `docs/<X>.html` substituindo `.md` canônico — ver subseção
  "Formato: Markdown canônico" acima ([[ADR-247]]).

---

## ADRs → notas atômicas em `docs/adr/` (ADR-182 · F2)

Toda decisão arquitetural ou de produto não-trivial vira ADR. Pós-F2 do
DOC_REORG, ADRs vivem como notas atômicas em [`docs/adr/NNN-slug.md`](docs/adr/),
uma por arquivo, com frontmatter validado por JSON Schema
(`docs/_schemas/note-adr.schema.json`). [`docs/DECISIONS.md`](docs/DECISIONS.md)
é shim de ~220 linhas que preserva âncoras históricas para PRs antigos.

Convenções:

- **Filename:** `NNN-<slug>.md` (3 dígitos zero-padded + slug derivado do
  título, lowercase ASCII, hífens). Sufixos legados (`ADR-029-TQ`,
  `ADR-102-WS`) viram `029-tq-...md` / `102-ws-...md`.
- **Frontmatter obrigatório:** `id` (`ADR-NNN`), `type: adr`, `title`,
  `status` (`Decidido` | `Proposto` | `Roadmap`), `date` (string ISO,
  com aspas).
- **Status sufixo de fase:** vai em campo `phase:` (ex.: `Decidido (F8.4)`
  → `status: Decidido`, `phase: F8.4`). Schemas + `validate_frontmatter`
  enforçam.
- **Tags hierárquicas:** `type/adr` obrigatória; `status/<lc>` automática;
  opcional `area/<dominio>`, `phase/<fase>`, `methodology/<m>`.
- **Anchor histórico:** copy-paste do slug GH em `docs/DECISIONS.md`
  shim (PR antigo continua clickable). Use
  `python3 dev/check_adr_anchors.py --suggest` para gerar slug novo.
- **Supersedure bidirecional:** ADR-Y supersede ADR-X → declare
  `supersedes: ["[[ADR-X]]"]` em Y E `superseded_by: ["[[ADR-Y]]"]`
  em X (frontmatter).
- **Emenda datada:** emendar ADR (`## Emenda/Correção/Calibração ... YYYY-MM-DD`)
  exige `amended_at: ["YYYY-MM-DD"]` no frontmatter + blockquote de sinal
  no topo (padrão ADR-027). Gate: `dev/check_adr_amendment_signal.py`.
- **Tamanho:** `size_lines` no frontmatter (auto-gerado). ADR > 150
  linhas → justificativa explícita ou split.
- **ÍNDICE:** [`docs/_MOC/_generated/ADR_INDEX.md`](docs/_MOC/_generated/ADR_INDEX.md)
  é auto-gerado por `dev/build_doc_index.py` (categoria + status). Nunca
  editar manualmente.

**Gates de validação** (pré-commit cobre todos):

```bash
python3 dev/validate_frontmatter.py     # frontmatter contra schemas
python3 dev/check_doc_filename_id.py    # filename ↔ id
python3 dev/check_doc_links.py          # wikilinks resolvem
python3 dev/check_adr_anchors.py        # anchors históricos + slug
python3 dev/check_adr_amendment_signal.py  # emenda datada exige amended_at
python3 dev/build_doc_index.py --check  # _generated/ sincronizado
python3 dev/validate_adr_format.py      # formato Status/Data (legado, mantido)
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
[docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) §Trade-off 5).

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
[docs/reference/ARCHITECTURE.md §4.1 Domain glossary](docs/reference/ARCHITECTURE.md).

### Pipeline não importa framework

`pipeline/**/*.py` **não pode importar** `fastapi`, `celery`, `sqlalchemy`.
Enforçado por `dev/check_pipeline_boundaries.py`. Adaptadores DB vivem em
`backend/app/services/` / `backend/app/repositories/`. `DBArtifactStore`
mora em `backend/app/services/storage/db_artifact_store.py` por esse motivo.

### Dinheiro nunca é `float` (ADR-090)

`Money.brl("1.23")` ou `Decimal(str(v))` no call-site. Wire HTTP: JSON
`number` (DTOs `MoneyBRL`/`MoneyUSD` com `PlainSerializer`; `Decimal` em
memória — ADR-090 §consequências + A6g.3b). Go: `int64` cents. A regra que
**sempre** produz bug de arredondamento silencioso é `float` em
cálculo/acúmulo — não a representação no wire.

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

`STAGE_RENAME_MAP` permanece como compat reverso. Em
`pipeline_artifacts.stage`, **todos** os writers gravam nomes descritivos
desde F9.6/W6-T03 (2026-07-06) — os últimos legados (`E2-faturas`/
`E2-extratos` em `scripts/e2_extract.py` (hoje `extract_bank_documents.py`), `E2-llm` em `extract_with_llm`,
`E6-parecer` no parecer) e os labels de progresso foram cortados. O leitor
aceita ambas as formas (`stage_aliases` /
`backend/app/services/storage/artifact_reader.py::_stage_query_candidates`) — rows
antigos seguem legíveis. Gate: `tests/unit/pipeline/test_no_legacy_stage_names.py`
hard-fail no CI. F9.4 (rename de `scripts/e*.py` → nomes descritivos)
entregue em 2026-07-06 — sub-fases da F9 concluídas.

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
`backend/app/services/security/vault.py` (Fernet) são **breaking** e exigem nova
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
[docs/reference/STATELESS_AUDIT.md](docs/reference/STATELESS_AUDIT.md) §2 — se não couber em
(a) ou (b), **não** adicione. Gate empírico:
`backend/tests/integration/test_multi_worker_concurrency.py`.

### `ArtifactStore` é DB-only (ADR-212)

Pipeline grava artefatos **exclusivamente** em `pipeline_artifacts`
via `DBArtifactStore`. `DiskArtifactStore` foi deletado em A12 (PR3b);
flag `MATHOMS_USE_DB_ARTIFACTS` + coluna `workspaces.use_db_artifacts_override`
removidos em PR4. Testes injetam `InMemoryArtifactStore` explícito —
`WorkspaceContext.get_artifact_store()` raise `RuntimeError` se store
não foi injetada. Validação JSON-schema universal via hook pós-write
em `DBArtifactStore.write` (mapping `SCHEMA_BY_STAGE`). Rollback:
snapshot DB pré-deploy + revert PR + migration downgrade (runbook em
[docs/reference/runbooks/pipeline_rollback.md](docs/reference/runbooks/pipeline_rollback.md);
janela ~30min RTO). Reset destrutivo de pipeline:
`backend/app/services/internal_ops/pipeline_reset.py::reset_workspace_from_stage`
(consumido pelo console interno, ADR-116).

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
[docs/reference/ARCHITECTURE.md §18](docs/reference/ARCHITECTURE.md).

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

### Busca ampla no repo

Use `rg`/`rg --files` para exploração. A raiz tem `.rgignore`/`.ignore`
excluindo `.claude/worktrees/`, que contém cópias completas do repo e
multiplica tokens sem adicionar contexto canônico. **Não use `--no-ignore`
em busca exploratória.** Se precisar auditar um worktree específico,
busque pelo path explícito desse worktree e diga por quê.

Antes de abrir muitos arquivos em `docs/`, leia
[docs/_MOC/_generated/CONTEXT_INDEX.md](docs/_MOC/_generated/CONTEXT_INDEX.md)
e escolha **1 context pack** para a intenção da tarefa. Depois busque por
bucket (`docs/reference`, `docs/plan`, `docs/sprint/<X>`, `docs/adr`) em vez
de varrer a vault inteira. `docs/archive/**` é arqueologia: consulte apenas
quando uma decisão histórica ou plano substituído for explicitamente relevante.

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
- **Sprint atual + lanes prontas**: [docs/_MOC/_generated/SPRINT_CURRENT.md](docs/_MOC/_generated/SPRINT_CURRENT.md)
  é fonte única (auto-gerado por `dev/build_doc_index.py`, filtra
  `status: ready/open/in_progress` da sprint corrente). Visão narrativa:
  [docs/_MOC/SPRINTS-active.md](docs/_MOC/SPRINTS-active.md). Detalhe por
  sprint: `docs/sprint/<X>/_README.md`. Detalhe por lane: `docs/sprint/<X>/lanes/<id>.md`.
  Como o SPRINT_CURRENT é regenerado a cada commit que toca lanes, pode
  ter atraso de poucos minutos vs realidade — confirme com os 2 comandos
  acima antes do pickup.

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

> ✅ **DOC_REORG (ADR-182) concluído em 2026-05-07.** As 5 fases entregues:
> F1 (foundation) · F2 (split DECISIONS → 175 ADRs em `docs/adr/`) · F3 (62 tracks + 6 plans) · F4 (35 lanes + 18 sprint MOCs) · F5 (167 changelog entries + cleanup raiz). DECISIONS.md, BACKLOG.md, CHANGELOG.md são shims com âncoras históricas; ROADMAP.md deletado (substituído por `docs/reference/PHASES.md`); PRODUCT.md movido para `docs/reference/`.

`CLAUDE.md` é o único hotspot que continua editado em toda sessão.

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
  [docs/reference/SETUP.md](docs/reference/SETUP.md). `git commit` direto e `dev/commit.py`
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
| `docs/reference/ARCHITECTURE.md §4.1 Domain glossary` | Índice de regras de domínio (rules-as-code, ADR-143) — aponta para o módulo enforcer + ADR canônica de cada conceito |
| `config/pipeline.json`            | Parâmetros operacionais (inclui `report_version`, schema validation)      |
| `config/report_layout.yaml`       | Seções e componentes do relatório (com comentários inline) — source-of-truth do codegen `dev/codegen_report_layout.py` (ADR-076) |
| `config/schemas/*.schema.json`    | Contratos JSON por etapa                                                  |
| `pipeline.stage_spec.STAGE_REGISTRY` | Source of truth de execução de stages (+ `STAGE_RENAME_MAP` para F9)   |
| `ConfigStore` protocol (DB-first) | `family_members`, `categorization`, `institutions`, `report_layout`, `transferencias_internas` (Sprint A7.0–A7.5 · ADR-134). Workspace lê via `DBConfigStore` em `WorkspaceContext.config_overrides`. |
| `fiscal_parameters` + `market_rates` (DB) | Tabelas globais versionadas por data — IRPF/PGBL/lucro presumido (ADR-135) e câmbio (USD/BRL, EUR/BRL). Substituiu `parametros_fiscais.json` + `taxas.json` em Sprint A7.2b. |
| `category_template` + `workspace_category_overrides` + `institution_catalog` (DB) | Catalog global versionado + diff por workspace (ADR-137 · A7.3). Substituiu `categorization.json` + `institutions.json` legados. |
| `Decision` aggregate (DB)         | Plano de Ação event-sourced (ADR-136 · A7.2a). Substituiu `decisions.md` editorial. |

Em caso de dúvida sobre como o pipeline funciona, consulte scripts,
configs e docstrings antes de agir. O fluxo canônico de stages vive em
[docs/reference/ARCHITECTURE.md §7](docs/reference/ARCHITECTURE.md) +
`pipeline.stage_spec` (o manual CLI legado foi deletado com `_archive/`
em A34.l7 — conteúdo superado por essas fontes).

**Arqueologia de valor (economia de token · ADR-281).** Para descobrir de
onde vem um número do relatório e **qual função o produz**, rode
`python3 dev/explain_number.py --field <dot.path> --format llm` — trace
linearizado que aponta fórmula + inputs + função + ADR (ex.:
`patrimonio.liquido` → `PatrimonioCalculator.calculate`, ADR-145). Custa
~80 tokens vs ~33k lendo `analyze_finances.py` inteiro (~400×). **Não abra
o stage inteiro para caçar um número** — o substrato de lineage
([`lineage_debug_tools.py`](pipeline/domain/services/lineage_debug_tools.py):
`explain_number`/`trace_source`/`expand_node`, whitelist + cap) já resolve
a árvore. Custo de investigação é gateado por `dev/check_lineage_eval_gate.py`.

---

## Classificação de documentos — duas vias (ADR-081)

**Classificação unificada (P2):** núcleo em
`backend/app/services/documents/document_classification.py` (`classify_document`,
`ClassificationResult`). Upload web, `POST /documents/reclassify` e
`route_documents.route_file` (quando o pacote `backend` é importável) usam o
**mesmo** fluxo: regex sobre **conteúdo** extraído → LLM opcional
(confidence < 0,8) → `needs_review` se confidence < 0,7.

1. **E0-route (`scripts/route_documents.py`):** com backend disponível, chama
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

- Scripts de stage em `scripts/` usam **nomes descritivos** espelhando
  `STAGE_RENAME_MAP` (`route_documents.py`, `reconcile_transactions.py`,
  `analyze_finances.py`… — F9.4 · ADR-093). Caso não-1:1:
  `extract_bank_documents.py` cobre `extract_invoices` +
  `extract_statements`. Exceção: `pipeline_common.py` (módulo
  compartilhado — paths, config, JSON I/O, atomic writes, schema
  validation, structured logging).
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

Pós-[[ADR-212]] + [[ADR-213]], artifacts vivem em `pipeline_artifacts` (DB)
— `stage` e `artifact_key` são colunas; **não há filename físico em
produção**. Os sufixos preservam 3 usos atuais:

1. **Rastreabilidade em E3** — [`e3_reconciler_adapter.py:239`](pipeline/domain/services/e3_reconciler_adapter.py) concatena `key + stage_suffix(stage)` no `stmt.source_document` (mostra qual input deu origem à linha).
2. **`_source` em itens E4** — [`e4_categorizer_adapter.py:217`](pipeline/domain/services/e4_categorizer_adapter.py) anexa origem a posição patrimonial / investimento.
3. **Campo `arquivo` no payload E3** — [`e3_serialization.generate_legacy_filename`](pipeline/domain/services/e3_serialization.py) gera `{banco}_{tipo_conta}_{MOEDA}_{YYYYMM}_{YYYYMM}-3_reconciled.json` para logs / UI.

Fonte de verdade do mapeamento: [`_STAGE_TO_SUFFIX`](pipeline/artifact_store.py) em `pipeline/artifact_store.py`. `_STAGE_TO_DIR` + `stage_dir_name()` foram deletados em [[ADR-213]] (dead code pós-sunset do stage `audit_documents`). **Paridade legacy ↔ descritivo (W2-T06, Sprint A11):** todo par `(legacy, descritivo)` de [`STAGE_RENAME_MAP`](pipeline/stage_spec.py) que produz artifact tem ambas as keys em `_STAGE_TO_SUFFIX` apontando para o mesmo sufixo — `stage_suffix("reconcile_transactions")` e `stage_suffix("E3")` retornam ambos `-3_reconciled.json`. Exceção: `E1.6` legacy (ADR-157 nasceu descritivo); somente `extract_irpf_full` está em `_STAGE_TO_SUFFIX`. Invariante enforçado por `tests/unit/pipeline/test_artifact_stores.py::test_legacy_descriptive_parity`.

| Stage / `_STAGE_TO_SUFFIX` key | Sufixo              | Stage descritivo                                         | Exemplo de `artifact_key`                  |
| ------------------------------ | ------------------- | --------------------------------------------------------- | ------------------------------------------ |
| `E0` (filename)                | `-0_original`       | Upload + roteamento (filename em `inbox/`)               | `c6bank_extratoconta_202601-0_original.csv` |
| `E1`                           | `-1b_unified`       | `extract_members` · ADR-127                              | `members`                                  |
| `E1.5a`                        | `-1.5a_extract`     | Extract per-IRPF pré-baseline                            | `irpfdeclaracao_2024`                      |
| `E1.5`                         | `-1.5_baseline`     | `extract_baseline` (baseline puro)                       | `baseline_patrimonial`                     |
| `E1.5c`                        | `-1.5_consolidated` | `consolidate_baseline`                                   | `baseline_patrimonial`                     |
| `extract_irpf_full`            | `-1.6_irpf_full`    | E1.6 — IRPF completo · ADR-157                           | `irpfdeclaracao_2024`                      |
| `E2-extratos`/`E2-faturas`/`E2-llm` | `-2_extract`   | E2 — extratos / faturas / LLM fallback                   | `itau_extratoconta_202601_202604`          |
| `E2-informe-aluguel`           | `-2_informe_aluguel` | `extract_informe_aluguel` · ADR-216 Onda 0.5b            | `informe_imobiliaria_2024`                 |
| `E2-informe-anual`             | `-2_informe_anual`  | `extract_informes_anuais` · ADR-238                      | `informe_brasilprev_2024`                  |
| `E2-comprovante-bem`           | `-2_comprovante_bem` | `extract_comprovantes_bens` · ADR-239                    | `apolice_portoseguro_2024` / `crlv_abc1d23_2024` |
| `E3`                           | `-3_reconciled`     | `reconcile_transactions`                                 | `itau_extratoconta_BRL_202212_202604`      |
| `E4`                           | `-4_unified`        | `categorize_transactions` — 7 keys                       | `despesas` / `receitas` / `fluxo_mensal_detalhado` / `patrimonio` / `investimentos` / `seguros` / `pontos_milhas` |
| `E5`                           | `-5_analysis`       | `analyze_finances`                                       | `analise_financeira`                       |
| `E6-parecer`                   | `-6_parecer`        | `review_finances_holistic` · ADR-199                     | `parecer_planejador`                       |

**Sufixos `-5n_narrativas` (`E5.N`) e `-7_crossval` (`E7`) permanecem em
`_STAGE_TO_SUFFIX`, mas são dead code de write em produção:**

- `generate_narratives` ([`scripts/generate_narratives.py:687`](scripts/generate_narratives.py)) faz `store.write("analyze_finances", "analise_financeira", ...)` — **merge** das narrativas no payload E5 existente (não há row com stage="E5.N" em `pipeline_artifacts`).
- `validate_cross` ([`scripts/validate_cross.py:480`](scripts/validate_cross.py)) é puro read-only sobre E5; **não chama `store.write`** (sem row com stage="E7").

Nomes de banco seguem o código canônico de `institution_catalog`
(DB, ADR-137; ex.: `bankofamerica`, `btgpactual`, `c6bank`, `itau` —
sem espaços, sem acentos).

**Período sentinel `999999`:** usado em faturas de cartão cujo período
não pôde ser determinado. Propaga de E0→E2→E3.

---

## Convenções intencionais (não "arrumar" em refactor)

- `config/report_layout.yaml` é o único YAML de **config de produto**
  versionado no repo — formato escolhido por suportar comentários inline
  que documentam decisões de seção (codegen em
  `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`,
  ADR-076). Outros YAMLs do repo (`.pre-commit-config.yaml`,
  `config/internal_operators.example.yaml`, `config/prompts/*.yaml`)
  servem propósitos ortogonais (CI, ops, prompts LLM) — não confundir.
- Sufixos mistos por stage (substantivo vs particípio: `E2_extracts`,
  `E3_reconciled`, `E4_unified`, `E5_analysis`, `E7_review`,
  `E6_parecer`) — padrão histórico aceito do layout legado em disco.
  Mapping `_STAGE_TO_DIR` foi deletado em [[ADR-213]]; o que sobrevive
  é `_STAGE_TO_SUFFIX` (consumidores em §"Convenções de naming de
  artefatos"). Artifacts em produção vivem em `pipeline_artifacts` (DB).
- `inbox_processed/` sem prefixo `_` — é parte do fluxo de upload (move
  arquivo de `inbox/` após classificação), não diretório auxiliar.
- `config/schemas/` contém 27 schemas JSON usados por `validate_dict` (hook
  pós-write em `DBArtifactStore.write`, ADR-212 PR3a): estágios canônicos
  (`baseline_patrimonial`, `e15_baseline_extract` (A20.l11), `e16_irpf_full`,
  `e2_extract`, `e2_llm_artifact`,
  `e3_reconciled`, `e4_unified`, `e5_analysis`, `pipeline`) + `Goal`
  (alocacao_alvo v1/v2, aporte_mensal, dolarizacao, if v1/v2,
  reserva_emergencia) + informes (`informe_base`/`_pf`/`_pj`/`_aluguel`/
  `_previdencia`/`_proventos`, ADR-238) + comprovantes de bem (`crlv`,
  ADR-239) + `parecer_planejador` + `protecao_patrimonial` (ADR-240) +
  `review_reason` + `report_layout`. Modo `warn` (default) vs `strict`
  controlado por `pipeline.json → schema_validation.mode` (override via env
  `MATHOMS_PIPELINE_SCHEMA_MODE`).

Para outras decisões idiossincráticas, consulte [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md).

---

## Comandos principais

Agente use `--help` nos scripts para descobrir flags. Comandos canônicos
de teste estão em §Code style › Testes. Para ops avançadas (smoke test,
seed, cutover DB, comparação disk↔DB), ver
[docs/reference/RUNBOOK.md](docs/reference/RUNBOOK.md) e
[docs/reference/SMOKE_TEST_HUMAN.md](docs/reference/SMOKE_TEST_HUMAN.md). CLI standalone
do pipeline descontinuada em ADR-212 (PR1+PR1b); `scripts/e0_audit.py`
era stage do pipeline (`audit_documents`) e foi deletado em ADR-213
(sunset; checks dependiam de `processed/E2_extracts/` que não existe
pós-ADR-212). Reset destrutivo de pipeline é service-layer
`backend/app/services/internal_ops/pipeline_reset.py::reset_workspace_from_stage`.

---

## Onde procurar contexto adicional

Conteúdo que **era** duplicado neste arquivo e agora vive em sua fonte
única:

| Pergunta                                            | Onde olhar                                                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Estrutura de diretórios completa (backend/pipeline/frontend/…) | [docs/reference/ARCHITECTURE.md §10](docs/reference/ARCHITECTURE.md)                               |
| Tabela completa de stages + `FULL_ORDER` + `DETERMINISTIC_ORDER` | [docs/reference/ARCHITECTURE.md §7](docs/reference/ARCHITECTURE.md)                              |
| Modo incremental (ADR-080) — API, filtragem, UI     | [docs/reference/ARCHITECTURE.md §7](docs/reference/ARCHITECTURE.md)                                            |
| Arquitetura alvo pós-A6 (migração infra+domínio)    | [docs/reference/ARCHITECTURE.md §17](docs/reference/ARCHITECTURE.md)                                           |
| Sprint atual + lanes prontas — vault atomizado pós-F4 (ADR-182). [`docs/_MOC/_generated/SPRINT_CURRENT.md`](docs/_MOC/_generated/SPRINT_CURRENT.md) (auto, filtra `status: ready/open/in_progress`) + [`docs/_MOC/SPRINTS-active.md`](docs/_MOC/SPRINTS-active.md) (editorial). Detalhe por sprint: [`docs/sprint/<X>/_README.md`](docs/sprint/A11/_README.md). Detalhe por lane: `docs/sprint/<X>/lanes/<id>.md`. [docs/BACKLOG.md](docs/BACKLOG.md) é shim. | [docs/sprint/](docs/sprint/) |
| Log cronológico de entregas (sessões A1–A6f por data) | [docs/CHANGELOG.md](docs/CHANGELOG.md)                                                   |
| ADRs (001–301+) — notas atômicas em `docs/adr/NNN-slug.md` (ADR-182 · F2). Índice agrupado por categoria + status: [docs/_MOC/_generated/ADR_INDEX.md](docs/_MOC/_generated/ADR_INDEX.md) (auto-gerado por `dev/build_doc_index.py`). Gates: `dev/validate_frontmatter.py`, `dev/check_doc_filename_id.py`, `dev/check_doc_links.py`, `dev/check_adr_anchors.py`. Protocolo em §"ADRs → notas atômicas em docs/adr/" deste CLAUDE.md. [docs/DECISIONS.md](docs/DECISIONS.md) é shim com âncoras históricas | [docs/adr/](docs/adr/) |
| Domínios e URLs públicas (ADR-108)                  | [docs/reference/ARCHITECTURE.md §18](docs/reference/ARCHITECTURE.md)                                           |
| Smoke test humano (runbook vivo — snapshots de gate §4.9; conteúdo do gate A6b arquivado) | [docs/reference/SMOKE_TEST_HUMAN.md](docs/reference/SMOKE_TEST_HUMAN.md)                                       |
| Artefatos de pipeline + schemas                     | [docs/reference/PIPELINE_ARTIFACTS.md](docs/reference/PIPELINE_ARTIFACTS.md)                                   |
| Motor canônico P0/P1                                | [docs/reference/CANONICAL_ENGINE_P0.md](docs/reference/CANONICAL_ENGINE_P0.md)                                 |
| Testes — estratégia e fixtures                      | [docs/reference/TESTING.md](docs/reference/TESTING.md)                                                         |
| Tenancy (multi-workspace)                           | [docs/reference/tenancy.md](docs/reference/tenancy.md)                                                         |
| DB schema de referência (auto-gerado)               | [docs/reference/DB_SCHEMA_REFERENCE.md](docs/reference/DB_SCHEMA_REFERENCE.md)                                 |
| Fluxo de PR (humano + agente) — branch naming, template, gates locais + CI, Dependabot, stale bot | [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) |
| Política de disclosure de vulnerabilidades (LGPD)   | [SECURITY.md](SECURITY.md)                                                                  |
| Plano canônico do shell Report Premium — v1 (10 fases ✅) + v2 §17 (🚧, ondas A-F paralelizadas), paridade React com EXEMPLO_DE_RELATORIO.html, único renderer pós-ADR-129 | [docs/plan/REPORT_PREMIUM/_README.md](docs/plan/REPORT_PREMIUM/_README.md)                      |
| Cutover final `config/goals.json` (Sprint A10, ✅ entregue 2026-05-07) — 9 lanes em 4 ondas, 5 ADRs (ADR-177 a ADR-181), 22 chaves do legado migradas para destinos canônicos; fechou checkbox ADR-077 §"Contrato de cutover" após 7 meses | [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md](docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) |
| Platform review canônico (Sprint A11, origem 2026-05-06, ✅ fechada `done` 2026-07-08 e plano arquivado) — 32 tasks em 6 ondas, 138 findings de revisão multi-agente; residual owner-gated (Resend, off-site R2, Coolify, Sentry, status page) transferido para LAUNCH_TRUST §F2 via emenda ADR-228 | [docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) |
| Parecer do Planejador (E6, ✅ `done` 2026-05-14, **arquivado 2026-07-09**) — substituição de `review_finances` por novo stage LLM com persona Perini/Cerbasi/AUVP (Sprint A11/A12, origem 2026-05-12). Atos 1-6 mergeados (PRs #242-#250): 10 ADRs (ADR-199 a ADR-208, Decididas), schemas + manifest declarativo, aggregate + endpoint stub, stage + orchestrator + golden mockado, renderer + UX + tier filter, telemetria + cross-provider + cutover + healthcheck | [docs/archive/PLANNER_REVIEW-2026-07-09.md](docs/archive/PLANNER_REVIEW-2026-07-09.md) |
| Categorization Learning Loop (Sprint A12, ✅ concluído 2026-07-08) — promoção de override de transação em regra persistida; MVP V1 completo (P1-P4 #188/#194/#195-#198/#203 + gate técnico 11/11 #202; gate humano PASS por decisão do owner 2026-07-02); modelo híbrido C-light + D-forte com invariantes (override manual sticky, mês fechado imutável, conflito determinístico). ADRs canônicas: ADR-186 + ADR-188, Decididas. V2 (P5/P6) pós-tração | [docs/archive/CAT_LEARNING_LOOP-2026-07-08.md](docs/archive/CAT_LEARNING_LOOP-2026-07-08.md) |
| Resposta competitiva a Pierre Finance (CloudWalk) (Sprint A11, origem 2026-05-08) — quatro fases: recon POC, Mathoms-as-MCP, chat sobre relatório, reposicionamento brand. Tracks ready: `competitor-pierre-poc` (Fase 1) + `gtm-landing-copy-rewrite` (Fase 4.B skeleton). ADR-183 (landing positioning pillars) | [docs/plan/COMPETITIVE_PIERRE/_README.md](docs/plan/COMPETITIVE_PIERRE/_README.md) |
| Data Lineage fim-a-fim + Fonte plugável (origem A23, corrente A26 — sprints A23–A26, origem 2026-06-02) — lineage forward+reverso legível por LLM + `SourceAdapter`/`SourceRef` (fonte plugável acoplada) + extração limpa (de-leak). 8 fases (F0 gate → F7 debug substrate); F0 abre 4 ADR Proposto (ADR-278 a ADR-281) + emenda ADR-146 (B1); supersede ADR-045. Nenhuma lane abre antes de B1–B8 travados | [docs/plan/DATA_LINEAGE/_README.md](docs/plan/DATA_LINEAGE/_README.md) |
| Outros planos ativos: Console interno admin IA-0..IA-4 (F7/A11, ADR-116) · Snapshot changelog v3 (A11, ADR-148/ADR-190) | [docs/plan/INTERNAL_ADMIN/_README.md](docs/plan/INTERNAL_ADMIN/_README.md) · [docs/plan/SNAPSHOT_CHANGELOG_V3/_README.md](docs/plan/SNAPSHOT_CHANGELOG_V3/_README.md) |
