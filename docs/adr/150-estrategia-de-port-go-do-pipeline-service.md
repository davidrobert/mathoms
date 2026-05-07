---
id: ADR-150
type: adr
title: "Estratégia de port Go do `pipeline-service`: Caminho 1 (shell-only via subprocess) como default deferido para Roadmap"
status: Roadmap
phase: "deferido em W6-T06, 2026-05-07"
date: "2026-04-27"
relates_to: ["[[ADR-112]]", "[[ADR-113]]", "[[ADR-102]]", "[[ADR-110]]", "[[ADR-111]]", "[[ADR-093]]", "[[ADR-097]]", "[[ADR-109]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 150"]
tags:
  - type/adr
  - status/roadmap
size_lines: 159
---

# ADR-150 — Estratégia de port Go do `pipeline-service`: Caminho 1 (shell-only via subprocess) como default deferido para Roadmap

**Status:** Roadmap (deferido em W6-T06, 2026-05-07) • **Data:** 2026-04-27 (proposta) → 2026-05-07 (Roadmap) • **Relaciona** [ADR-112](#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1), [ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7), [ADR-102](#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f), [ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3), [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6), [ADR-093](#adr-093--rename-completo-de-identificadores-de-stage-opção-a), [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a).

> **Decisão W6-T06 (2026-05-07):** Caminho 1 **continua sendo o default escolhido**
> quando algum gatilho disparar — a estratégia de port (layout, pré-requisitos,
> cutover) abaixo permanece autoritativa. O que muda é o status: sai de
> `Proposto indefinido` para `Roadmap` com critério de destrava explícito e
> revisita agendada. **Não há lane A6h aberta.** Skeleton Go preventivo
> ([ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7)) **fica
> mantido** — custo de manutenção é ~zero (CI workflow é no-op via
> `hashFiles('**/*.go') != ''`, `make go-all` retorna 0 em repo sem `.go`,
> `.golangci.yml` + `go.work` somam ~70 LOC de config). Deletar perderia
> opção sem benefício mensurável; manter preserva a propriedade-chave de
> ADR-113 (primeiro PR Go produtivo não perde tempo configurando guardrails).
>
> **Critério de destrava (qualquer um autoriza arrancar Caminho 1):** os 4
> gatilhos numerados no §"Quando port se justifica" abaixo permanecem válidos.
> Adicionalmente, esta ADR é **revisitada em 2027-Q2 ou ao atingir 100
> workspaces ativos pagantes** (o que vier primeiro), independente dos
> gatilhos — momento em que custo operacional do `pipeline-service` Python
> deve ter série temporal de prod suficiente para refalsificar os thresholds
> originais (que foram colocados sem dados de prod em 2026-04).
>
> Razões da decisão (W6-T06):
>
> 1. **Nenhum gatilho está ativo hoje** (~10 workspaces, single-instance,
>    `/health` p99 174ms container — não é hot path; stages levam minutos
>    LLM-bound, overhead HTTP é ruído).
> 2. **Nenhuma feature pendente do BACKLOG depende de Caminho 1** — Sprint
>    A10 (goals.json cutover), F7 (produção + LGPD), F11 (confiança beta→GA),
>    F12 (i18n), Report Premium são todas feature work em Python/TS sem
>    requisito de footprint Go.
> 3. **Capacidade do time** (1 dev humano + agentes) está alocada em A10/F7
>    pelos próximos 2-3 meses. Caminho 1 é multi-week com 5 pré-requisitos
>    hard (A2.fix, A3.cli, A3.cli.otel, A3.cli.benchmark, A3.codegen) — não
>    cabe em paralelo.
> 4. **LGPD/soberania não é argumento técnico para Go** — runtime Python
>    em VPS BR atende ao mesmo requisito de localidade. PII handling vive
>    no domain layer Python independente da linguagem do shell.
> 5. **Skeleton Go preventivo é assimétrico:** custo de manter
>    (CI no-op, lint config dormente) é desprezível; custo de recriar (ADR
>    nova, calibração de linter, debate de convenções no PR produtivo) é
>    real. ADR-113 já registrou explicitamente esta postura "infra
>    preventiva sem disparar port" — `Roadmap` é coerente com ela.
>
> Diferença em relação a `Rejeitada`: rejeitar exigiria nova ADR caso
> qualquer gatilho dispare no futuro, pagando o custo de raciocínio
> arquitetural duas vezes. Diferença em relação a `Decidido`: aceitar
> dispararia lane A6h em conflito direto com sprints ativos. **`Roadmap`
> elimina o pior estado (`Proposto` indefinido) sem destruir a opção.**

**Contexto:** [ADR-112](#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1) estabeleceu o `pipeline-service/` como FastAPI standalone com contrato HTTP versionado, justamente para que uma reescrita Go fosse possível sem retrabalho de fronteira. [ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) entregou `.golangci.yml`, CI workflow e skeleton `services/`. Falta a decisão estratégica: **se** e **como** disparar o port, e em que ordem.

A2 (entregue em [docs/PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md), 2026-04-27) e A1 (entregue em [docs/GO_PORT_DEPS.md](GO_PORT_DEPS.md), 2026-04-27) deram a base empírica:

1. **Shell HTTP é pequeno** — 532 LOC Python em 14 arquivos; importa **5 símbolos** de `pipeline.*` (`WorkspaceContext`, `_run_stage`, `LLM_STAGES`, `StageResult`, `STAGE_REGISTRY`) e 1 import opcional de `backend.*` (`setup_logging` com fallback).
2. **Domínio é grande** — 17.823 LOC em `pipeline/`, dos quais ~13.077 LOC em 61 arquivos de `pipeline/domain/services/`. Goldens de paridade BRL `0.01` ([ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)) cobrem a regressão de cálculo monetário, mas exigiriam port 1-a-1 numa rewrite completa.
3. **Footprint mensurado:** imagem Docker 283 MB (DISK), cold start ~500ms mediana, RSS idle 36-39 MB, `/health` p99 15ms (local) / 174ms (container macOS Docker Desktop), throughput `/health` 7100 req/s local / 2700 req/s container.
4. **`/health` é proxy informativo, não hot path.** Stages reais (E3/E5) levam minutos; overhead HTTP serializa em ms. Uma melhora de 10× em `/health` some no ruído.
5. **Stage execution real NÃO foi medida** — exigiria smoke tenant com dados (out-of-scope sem orquestração combinada). Sem isso, gatilho "GIL/CPU-bound" para Caminho 3 fica especulativo (ver A2.1 em §Próximos passos).
6. **Bug pré-existente no Dockerfile** ([pipeline-service/Dockerfile](../pipeline-service/Dockerfile)): `COPY pyproject.toml` antes de `app/` faz setuptools falhar com `package directory 'app' does not exist`. Imagem oficial não builda hoje. Pré-requisito de qualquer port que valide paridade via container.

Três caminhos foram detalhados em A1 §3:

- **Caminho 1 — Shell-only Go + Python via subprocess.** Porta ~600 LOC do `pipeline-service/app/` para Go. Stage execution vira `python -m pipeline.orchestrator run-stage <name> ...`. Mantém `pipeline/` inteiro em Python. Custo: 1-2 sessões grandes + 1 entry-point CLI novo no orchestrator. Ganha: imagem 283 MB → ~30 MB, cold start ~500ms → <100ms, deploy estático, observabilidade unificada via `slog` JSON ([ADR-110](#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3)). Não ganha: GIL, CPU dos stages.
- **Caminho 2 — Roteador Go + Python worker pool.** Adiciona pool de workers Python warm para evitar `fork+exec` por stage. Mesmos ganhos do Caminho 1, elimina cold-start de subprocess. Custo: complexidade de lifecycle (restart policy, draining, monitoring). Marginal vs. Caminho 1 enquanto cargas atuais estão muito abaixo do ponto onde fork+exec dói.
- **Caminho 3 — Reescrita completa em Go.** Port de 17.823 LOC para Go (estimado 25-35k LOC Go, mais verboso). Inclui parsers de E2 (8+ instituições), `litellm_client` (488 LOC), domain services (~13k LOC) com paridade obrigatória contra goldens BRL. Custo: 3-5 meses de sprint dedicado com 1-2 engenheiros. Ganha tudo: footprint pleno, sem GIL, cold start <50ms, stack monolíngue.

**Quando port se justifica.** Gatilhos com threshold falsificável — qualquer um disparando autoriza arrancar Caminho 1:

1. **Custo de container Python virou problema operacional medido**: ≥3 instâncias simultâneas do `pipeline-service` em prod **ou** RSS agregado >2 GB sustentado por 7 dias **ou** custo cloud (compute + memory) do `pipeline-service` >USD 50/mês por workspace ativo. Threshold inicial — refinável por ADR posterior assim que houver série temporal de prod.
2. **Cliente externo não-Python consumindo a API direto** — CLI ops, integração terceiros, mobile worker — com requisito assinado de SLA (não exploratório).
3. **Janela natural de re-encrypt/migração maior** ([ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a) §A6f.5b Fernet→AES-GCM **ou** equivalente) tornando o port "carona" barato.
4. **Sprint dedicado com orçamento explícito** (4-6 semanas) — não em paralelo com features.

Hoje, nenhum dos quatro está ativo.

[ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) já adotou a postura "infra preventiva" (linter, CI, skeleton, contrato HTTP) sem disparar o port. Esta ADR formaliza a estratégia para quando algum gatilho disparar.

**Decisão:**

1. **Caminho 1 é o default proposto** quando algum dos 4 gatilhos disparar. Razões:
   - Entrega 90% do ganho operacional (image size, cold start, deploy estático) com 5% do custo do Caminho 3.
   - Mantém domínio Python intacto — goldens, ADR-090/097/090 e regras de domínio em [docs/ARCHITECTURE.md §4.1 Domain glossary](ARCHITECTURE.md) continuam autoridade única.
   - Cutover gradual já desenhado em [ADR-112](#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1): backend usa `PipelineServiceClient` Protocol; flip de `MATHOMS_PIPELINE_SERVICE_URL` aponta para o serviço Go sem código novo no backend.

2. **Caminho 3 fica deferido** até que evidência empírica de gargalo CPU-bound nos stages exista. Sem A2.1 (smoke real medindo RSS/CPU/duração por stage), "GIL é o problema" é especulação. Se a evidência aparecer, abrir nova ADR (ADR-151+) que justifique e supersede esta.

3. **Caminho 2 fica descartado por ora.** Complexidade operacional acima do retorno enquanto cargas estão muito abaixo do ponto de saturação. Se Caminho 1 entregar e fork+exec por stage virar gargalo medido (não suposto), reabrir em ADR própria.

4. **Pré-requisitos do Caminho 1, ordem obrigatória:**
   - **A2.fix** — fixar [pipeline-service/Dockerfile](../pipeline-service/Dockerfile) bug de COPY ordering. Sem isso, paridade Python↔Go não pode ser validada via container nem CI smoke.
   - **A3.cli** — adicionar entry-point CLI no orchestrator: `python -m pipeline.orchestrator run-stage <stage> --workspace <path> --run-id <id> [--config-dir <path>] [--incremental] [--incremental-doc <path>...]`. Output JSON estruturado em stdout (mesmo shape de `StageResult`), erros estruturados em stderr. Sem CLI, Caminho 1 vira hack de import dinâmico, não interface estável.
   - **A3.cli.otel** *(sub-pré-requisito hard)* — entry-point CLI lê `TRACEPARENT` do env e instancia span filho via OTel context propagation, mantendo o trace contínuo entre Go (parent) e Python (child). Sem isso, gate de paridade do §7 não cobre traces e regressão de latência em produção fica invisível.
   - **A3.cli.benchmark** *(gate empírico)* — após A3.cli + A3.cli.otel, medir cold start real do `python -m pipeline.orchestrator run-stage` num venv com deps típicas (`pipeline.*`, `pipeline.llm.*`, fallback opcional `backend.app.core.logging`). **Se cold start mediano >500ms**, Caminho 2 (worker pool warm) volta à mesa **antes** do primeiro PR Go produtivo — não depois. Boot Python real não é o `python -c` vazio (~50ms); é o re-import da árvore de domínio, que A2 não mediu (pipeline-service local importa lazy dentro de funções).
   - **A3.codegen** — codegen Go via `oapi-codegen` consumindo [docs/api/v1/pipeline-service.openapi.json](api/v1/pipeline-service.openapi.json) para `services/pipeline-service-go/internal/contracts/`. Snapshot test garante regen limpo.

5. **Layout do serviço Go (quando criado):**
   ```
   services/pipeline-service-go/
   ├── go.mod                    (module mathoms.ai/pipeline-service)
   ├── cmd/pipeline-service/
   │   └── main.go               (≤30 linhas — wire + boot)
   └── internal/
       ├── api/                  (chi router, handlers — porta de api/*.py)
       ├── runs/                 (RunCoordinator — porta de run_coordinator.py)
       ├── stages/               (StageExecutor — exec.Cmd subprocess)
       ├── events/               (Redis publisher — porta de event_publisher.py)
       └── contracts/            (structs gerados via oapi-codegen)
   ```
   Convenções de [CLAUDE.md §Code style › Go](../CLAUDE.md) e [ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) inegociáveis: sem `interface{}`/`any`, errors tipados, `int64` cents, `slog` JSON, sem estado mutável package-level, race detector sempre on.

6. **Acoplamentos out-of-band a replicar idênticos:**
   - **Layout de paths** — `WorkspaceContext.__post_init__` define `processed_dir`, `e2_dir`, etc. Convenção compartilhada com Python via subprocess; tem que bater byte-a-byte.
   - **Redis pub/sub envelope** — formato em [event_publisher.py:56](../pipeline-service/app/services/event_publisher.py:56) (`event`, `run_id`, `timestamp`, `stage`, `status`, `progress_pct`, `error`, `detail`). Backend WebSocket consumer espera esse shape exato.
   - **Channel naming** — `pipeline:{run_id}` em [event_publisher.py:72](../pipeline-service/app/services/event_publisher.py:72). Hardcoded; idêntico no Go.
   - **OTel span naming** — `pipeline.{stage}` em [pipeline/orchestrator.py:237](../pipeline/orchestrator.py:237). `otel.Tracer("mathoms.pipeline").Start(ctx, "pipeline."+stage)`.

7. **Cutover.** Um único toggle, sem flag de produto:
   - `MATHOMS_PIPELINE_SERVICE_URL` apontando para `pipeline-service-go` em staging primeiro, depois prod por workspace via reverse proxy ou env var por instância.
   - **Gate técnico:** 3 runs E0→E5 completos contra workspaces controlados, paridade byte-a-byte de artefatos finais, WS events e atributos de span OTel (com TRACEPARENT propagado — ver A3.cli.otel).
   - **Gate humano** *(obrigatório, não pulável)*: 1 workspace real, smoke humano completo seguindo o protocolo de [docs/SMOKE_TEST_HUMAN.md](SMOKE_TEST_HUMAN.md) (precedente: A6b.5 / [ADR-103](#adr-103--teste-manual-como-gate-antes-de-remoção-do-bridge-a6b5--a6-human)) — validação visual do relatório final em `/reports/[id]` antes de flip prod. Sem isso, divergência semântica que escapa de paridade byte-a-byte (formatação de narrativa, copy de status) chega ao cliente.
   - Backend permanece dono do `DBArtifactStore`; serviço Go fala `DiskArtifactStore` apenas — mantém fronteira fina ([ADR-112](#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1)).

8. **Coexistência.** Python `pipeline-service/` permanece como fallback durante cutover. Decommission do `pipeline-service/` Python só após **≥2 semanas calendário** em prod com Go-shell sem rollback e sem regressão de paridade documentada (artefatos final ou WS events). Decommission é slice próprio com ADR de remoção, similar a [ADR-107](#adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2) bridge removal.

**Consequências:**

- ✅ **Decisão sobre Caminho 1 é não-ambígua.** Quando o gatilho disparar, primeiro PR Go produtivo já tem layout, pré-requisitos e cutover definidos. Revisão foca em domínio, não em estratégia.
- ✅ **Linhas vermelhas explícitas.** Caminho 3 não acontece sem evidência empírica nova (A2.1+); Caminho 2 não acontece sem fork+exec medido como gargalo. Evita port "exploratório" sem trigger.
- ✅ **Pré-requisitos numerados.** A2.fix (Dockerfile) e A3.cli (entry-point orchestrator) são pré-requisitos hard — não dá pra começar Caminho 1 sem eles. Lock contra "comecei Go e descobri que precisava antes…".
- ✅ **Domain layer Python intacto.** Regras de domínio (ADR-090, ADR-097, ADR-145, ADR-146, ADR-147, etc.) continuam vivas em `pipeline/domain/services/` e `docs/methodology/` correspondente. Caminho 1 não toca esse perímetro.
- ✅ **Reversibilidade.** Se Caminho 1 entregar e algo falhar em produção, flip de `MATHOMS_PIPELINE_SERVICE_URL` reverte para Python em segundos. Sem migração de schema, sem mudança de DB, sem perda de dados.
- ⚠️ **Caminho 1 não elimina Python.** Container final tem **Go binary + Python runtime + `pipeline/` source**. Footprint cai de 283 MB para ~80-150 MB (Go binary + python:3.12-slim + pipeline source), não para os ~15-30 MB de Caminho 3 puro. Se a meta é "imagem mínima Alpine", Caminho 1 não atinge.
- ⚠️ **`fork+exec` Python por stage tem custo real maior que aparenta.** Boot Python vazio (`python -c pass`) é ~50ms; mas o entry-point do orchestrator re-importa `pipeline.*` (orchestrator + stage_spec + context + lazy import do runner correto + `pipeline.llm` se LLM stage), o que num venv produtivo é ~400-800ms cold. Em `/runs` que sequencia 16 stages, overhead acumulado é **6-13s** — observável e potencialmente intolerável em testes locais que rodam o pipeline iterativamente. Mitigação obrigatória: A3.cli.benchmark mede empírico antes do primeiro PR Go produtivo; se cold real >500ms, Caminho 2 (worker pool warm) reabre antes, não depois.
- ⚠️ **Goldens de paridade exigem `pipeline-service-go` rodar contra workspace fixture com mesmo input que o Python.** A2.1 (smoke real) é pré-condição também para validação de Caminho 1 — não só para Caminho 3.
- ⚠️ **OTel span attributes precisam ser bit-exact e o trace tem que ser contínuo.** [orchestrator.py:237-245](../pipeline/orchestrator.py:237) emite `pipeline.stage`, `pipeline.workspace_root`, `pipeline.run_id`, `pipeline.is_llm`, `pipeline.success`, `pipeline.exit_code`. Subprocess Python emite spans filhos; Go emite span pai. Trace contínuo é **gate de paridade** (não opcional) — endereçado por A3.cli.otel acima.
- ❌ **Caminho 3 fica adiado indefinidamente.** Quem queria Go monolíngue puro fica frustrado. Aceito porque (a) custo é muito alto (3-5 meses), (b) gatilho empírico ainda não existe, (c) Caminho 1 desbloqueia 90% dos ganhos sem fechar a porta para Caminho 3 futuro (esta ADR pode ser superseded).
- ❌ **Stack heterogênea por mais tempo.** Backend Python + pipeline Python + serviço Go shell. Custo cognitivo para devs novos. Aceito porque o shell Go é pequeno e não toca domínio.

**Escopo deferido (follow-ups explícitos):**

- **A2.1** — smoke real do `pipeline-service` Python: workspace tenant + run E0→E5 completo, medindo RSS/CPU/duração por stage. **Pré-requisito de Caminho 3** e validação de Caminho 1.
- **A2.fix** — fix do bug de COPY ordering em [pipeline-service/Dockerfile](../pipeline-service/Dockerfile). Slice docs+código próprio, sem ADR (refactor mecânico).
- **A3.cli** — entry-point `python -m pipeline.orchestrator run-stage` com output JSON estruturado. Slice próprio, sem ADR (interface adicional, retro-compatível com `_run_stage` programático).
- **A3.codegen** — `oapi-codegen` setup para `services/pipeline-service-go/internal/contracts/`. Slice próprio, parte do primeiro PR Go produtivo ou imediatamente antes ([ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) §Escopo deferido).
- **ADR-151+ (hipotética)** — promoção de Caminho 1 para Caminho 3 se A2.1 mostrar gargalo CPU-bound nos stages. Esta ADR seria superseded.
- **ADR de decommission do Python `pipeline-service`** — quando Caminho 1 entregar e estabilizar em prod, slice próprio remove `pipeline-service/` Python (similar a [ADR-107](#adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2)).

**Artefatos:**

- [docs/GO_PORT_DEPS.md](GO_PORT_DEPS.md) — A1, inventário de dependências.
- [docs/PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md) — A2, baseline empírico.
- [docs/api/v1/pipeline-service.openapi.json](api/v1/pipeline-service.openapi.json) — contrato HTTP fonte de verdade.
- [services/](../services/) — skeleton Go ([ADR-113](#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7)).
- [.golangci.yml](../.golangci.yml), [.github/workflows/go.yml](../.github/workflows/go.yml), [Makefile](../Makefile) `go-*` targets — infra preventiva pronta.
