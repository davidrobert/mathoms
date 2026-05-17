---
id: TRACK-a6g7-go-prep
type: track
title: "Track A6g.7 — Go prep (golangci-lint + CI job + skeleton convention)"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6g.7 — Go prep (golangci-lint + CI job + skeleton convention)

> **Lane ID:** A6g.7
> **Branch prefix:** `agent/a6g7-go-prep/*`
> **Depende de:** A6f.1 ✅ (pipeline-as-service mergeada — existe primeiro serviço candidato à reescrita em Go; sem ele, Go prep era prematuro).
> **Paralelo com:** qualquer lane A6e.*/A6g.* — **zero overlap** (esta lane adiciona `.go` e config files; não mexe em Python, TS ou YAML existente).
> **Conflita com:** nada (arquivos novos) exceto `.github/workflows/*.yml` se outra lane tocar CI simultaneamente.
> **Onda:** 3
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:** [ADR-112 pipeline-as-service](../../../DECISIONS.md), [CLAUDE.md §Code style › Go](../../../../CLAUDE.md#code-style), [ARCHITECTURE §17](../../../reference/ARCHITECTURE.md) (arquitetura alvo pós-A6)

> **Objetivo:** preparar a infra de lint + CI + convenções para quando
> o primeiro serviço Go entrar (candidato: `pipeline-service/` reescrito
> de FastAPI para Go). Esta lane **não** escreve serviço — só o
> skeleton + guardrails + CI job que valida o próximo PR de Go.
> Zero código Go produtivo; apenas `.golangci.yml`, `Makefile` targets,
> CI workflow, `ADR-113` (ou próximo livre) sobre convenções.

---

## Por que esta lane agora

- **CLAUDE.md §Code style › Go** já define regras (sem `interface{}`/`any`, errors tipados, `int64` cents, interfaces definidas no consumer). Sem linter, convenção é letra morta.
- **A6f.1 ✅** prova que `pipeline-service/` pode rodar isolado por HTTP. Candidato natural para reescrita Go (latência, footprint, facilidade de deploy estático). Quem fizer a reescrita precisa de linter pronto — senão perde tempo configurando no meio do PR.
- **ADR-102 R19-R20** (language-neutral) exige OpenAPI estável; reescrita Go consome `docs/reference/api/v1/openapi.json` via codegen (`oapi-codegen`). Skeleton do generator entra aqui.
- **A6g.6** (enforcement) precisa de linter Go ativo para gating uniforme (Python ruff + TS eslint + Go golangci).
- Baixo custo, destrava o futuro sem bloquear ninguém.

---

## Regras inegociáveis

Do CLAUDE.md §Code style › Go:

1. **Sem `interface{}`/`any`** fora de util genérico. Tipos concretos em assinaturas.
2. **Errors tipados:** `var ErrNotFound = errors.New(...)` ou struct com `Error()`. Nunca `errors.New("...")` inline espalhado.
3. **Dinheiro = `int64` cents.** Nunca `float64` nem `decimal.Decimal` sem invariante.
4. **Interfaces pequenas definidas no consumer**, não producer. Injete `io.Reader`, não `*os.File`.
5. **Sem `fmt.Println` fora de CLI.** `log/slog` com handler JSON + contexto propagado.
6. **Sem estado mutável em package-level** (paralelo a ADR-111 Python): sem `var globalCounter int`. Singletons lazy idempotentes OK (DB pool, slog handler).
7. **`gofmt -s` + `go vet` + `staticcheck` + `golangci-lint run` no pre-commit + CI.**
8. **`go test ./... -race`** obrigatório; race detector sempre on em CI.

---

## Estado atual — mapeamento

**Go no repo:** zero. `find . -name "*.go" | grep -v node_modules | grep -v .git` retorna vazio.

**Infra-correlata existente:**
- `.github/workflows/ci.yml` — Python + frontend.
- `Makefile` — targets `test`, `lint`, `format`, `check-boundaries`, `update-openapi-snapshot`.
- `.pre-commit-config.yaml` — hooks Python/TS.
- `docs/reference/api/v1/openapi.json` — contrato estável (ADR-102).

**Candidato de serviço Go (não é escopo desta lane, só referência):** `pipeline-service/` atual (FastAPI, A6f.1) — ~8 endpoints, stateless, faz chamada para Celery worker. Latência e startup são críticos → Go é a escolha natural pós-validação.

---

## Alvo estrutural

```
.golangci.yml                          # lint config (abaixo)
go.work                                # workspace multi-module (prep futuro)
services/                              # raiz para serviços Go (ex.: pipeline-service-go/)
  README.md                            # onboarding Go + convenções
  .gitkeep
.github/workflows/go.yml               # CI: vet + staticcheck + golangci + test -race
Makefile                               # novos targets: go-lint, go-test, go-fmt
docs/DECISIONS.md                      # ADR-113 (ou próximo) Go conventions
docs/agent_prompts/                    # você já está aqui
```

**Nota sobre `services/` vs `pipeline-service/`:** o serviço atual vive em `/pipeline-service/` na raiz (escolha de A6f.1). Quando/se vier um segundo serviço, `services/<name>/` consolida. Esta lane **não** move `pipeline-service/`; só cria `services/` vazio com README apontando o caminho futuro.

---

## `.golangci.yml` — configuração inicial

Base conservadora (pode apertar em A6g.6 depois):

```yaml
run:
  timeout: 3m
  go: "1.22"

linters:
  disable-all: true
  enable:
    - errcheck           # erro não-verificado = bug
    - govet              # suspeitas de bug
    - staticcheck        # compreensive static checks (SA*)
    - ineffassign        # assign sem uso
    - unused             # código morto
    - gofmt              # formato
    - goimports          # imports ordenados
    - gocritic           # style + performance
    - revive             # substituto de golint
    - bodyclose          # HTTP body fechado
    - noctx              # http.Request sem context
    - sqlclosecheck      # rows/stmt fechado
    - rowserrcheck       # rows.Err() checado
    - errorlint          # errors.Is/As + %w
    - gocyclo            # complexidade ciclomática
    - goconst            # literais repetidas
    - misspell           # tipos óbvios
    - unconvert          # conversão redundante
    - unparam            # param nunca usado
    - prealloc           # slice sem prealocação

linters-settings:
  gocyclo:
    min-complexity: 15
  govet:
    enable-all: true
  revive:
    rules:
      - name: exported
      - name: error-return
      - name: error-naming
      - name: error-strings
      - name: unused-parameter
      - name: var-naming
      - name: package-comments
  errorlint:
    errorf: true
    asserts: true
    comparison: true

issues:
  max-issues-per-linter: 0
  max-same-issues: 0
  exclude-rules:
    # testes podem usar any em table-driven
    - path: _test\.go
      linters:
        - revive
      text: "unused-parameter"

severity:
  default-severity: error
```

**Regras banidas por policy (do CLAUDE.md) — adicionar em A6g.6:**
- `forbidigo`: lista `interface\{\}`, `fmt.Println` (fora de `cmd/`), `float64` em aggregate `money`/`cents`.
- `depguard`: impedir imports cruzando boundary (ex.: domínio não importa `net/http`).

Deixe `forbidigo`/`depguard` fora do `.golangci.yml` inicial — eles exigem arquivos reais para calibrar. A6g.6 ativa quando houver código.

---

## `.github/workflows/go.yml`

```yaml
name: Go CI

on:
  pull_request:
    paths:
      - '**.go'
      - 'go.*'
      - 'services/**'
      - '.golangci.yml'
      - '.github/workflows/go.yml'
  push:
    branches: [main]
    paths:
      - '**.go'
      - 'go.*'
      - 'services/**'
      - '.golangci.yml'

permissions:
  contents: read

jobs:
  go-lint:
    name: Go lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - name: Go mod download (no-op se não houver go.mod ainda)
        run: test -f go.work && go work sync || echo "No go.work yet"
      - name: gofmt check
        run: test -z "$(gofmt -s -l . 2>/dev/null)" || (gofmt -s -d . && exit 1)
      - name: go vet
        run: test -f go.work && go vet ./... || echo "Skipping: no Go modules"
      - uses: golangci/golangci-lint-action@v6
        with:
          version: v1.60
          args: --timeout=3m
          skip-save-cache: true
        # só falha se houver código Go — evita CI vermelho quando repo não tem .go
        if: hashFiles('**/*.go') != ''

  go-test:
    name: Go test -race
    runs-on: ubuntu-latest
    needs: go-lint
    if: hashFiles('**/*.go') != ''
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - name: Tests with race detector
        run: go test ./... -race -count=1 -timeout=5m
```

**Nota sobre idempotência:** enquanto o repo não tem `.go`, os jobs passam (skip). Quando o primeiro `.go` entrar, jobs ativam automaticamente. CI não precisa ser alterado no PR da reescrita.

---

## `Makefile` — novos targets

```makefile
.PHONY: go-fmt go-lint go-test go-all

go-fmt:
	@gofmt -s -w $(shell find . -name "*.go" -not -path "./node_modules/*" 2>/dev/null) || echo "No Go files yet"

go-lint:
	@test -f go.work && golangci-lint run --timeout=3m ./... || echo "No Go workspace yet"

go-test:
	@test -f go.work && go test ./... -race -count=1 || echo "No Go workspace yet"

go-all: go-fmt go-lint go-test
```

---

## `go.work` (workspace skeleton)

```go
go 1.22

use (
	./services
)
```

**Deixar `services/` vazio** com apenas `.gitkeep` + `README.md`. `go.work` com `use (./services)` vazio é válido (Go 1.18+ aceita).

---

## `services/README.md` — onboarding

Conteúdo mínimo (exemplo; escreva em Português BR, ver CLAUDE.md):

```markdown
# Serviços Go

Raiz para serviços reescritos em Go (pós-A6f.1, ADR-112+ADR-113).

## Convenções

- Cada serviço em subdiretório próprio: `services/<name>/`.
- Estrutura: `cmd/<name>/main.go` (entrypoint) + `internal/<aggregate>/` (domínio).
- Sem `interface{}`/`any` fora de util genérico.
- Errors tipados (`var ErrNotFound = errors.New(...)` ou struct).
- Dinheiro = `int64` cents.
- `log/slog` com handler JSON (nada de `fmt.Println`).
- Interfaces pequenas no consumer (injete `io.Reader`, não `*os.File`).

## Setup

- Go 1.22+.
- `make go-all` roda fmt + lint + test.
- CI: `.github/workflows/go.yml` gating em PR.

## Primeiro serviço (candidato)

`pipeline-service/` (FastAPI Python, A6f.1) é o candidato natural à
reescrita. Quando a decisão for tomada, abra ADR e crie
`services/pipeline-service-go/`.

## Refs

- ADR-112 — pipeline-as-service (forma atual)
- ADR-113 — Go conventions (este repo)
- CLAUDE.md §Code style › Go
```

---

## ADR-113 — Go conventions (ou próximo número livre)

Docs em `docs/DECISIONS.md`. Consolida as regras do CLAUDE.md §Code style › Go em formato ADR rastreável. Resumo:

- **Contexto:** CLAUDE.md tem regras; sem ADR, não há fonte de verdade histórica.
- **Decisão:** adotar `.golangci.yml` conservador (errcheck, staticcheck, gocritic, revive) + ban `interface{}`/`any` + errors tipados + `int64` cents + `log/slog` JSON + race detector sempre on.
- **Consequências:** (a) linter força consistência desde o primeiro PR; (b) reescrita de `pipeline-service/` nasce dentro do guardrail; (c) A6g.6 ativará `forbidigo`/`depguard` quando houver código.
- **Alternativas consideradas:** (a) deixar para primeiro PR de Go — rejeitada (linter vira bikeshed no meio do PR produtivo); (b) aderir a `effective-go` sem ADR — rejeitada (regras específicas do projeto, ex.: `int64` cents, não estão em Effective Go).

---

## Sequência de commits

**Commit 1 — skeleton + CI**:
- `.golangci.yml` + `go.work` + `services/README.md` + `services/.gitkeep`.
- `.github/workflows/go.yml`.
- Makefile targets.
- `feat(go): skeleton + golangci-lint + CI job (A6g.7)`

**Commit 2 — ADR**:
- `docs/DECISIONS.md` ADR-113.
- `docs/CHANGELOG.md [Unreleased]` entrada A6g.7.
- `docs/BACKLOG.md` A6g.7 ☐ → ✅.
- CLAUDE.md §Code style › Go: adicionar link "ver ADR-113 para detalhes" (inline link, não duplicação).
- `docs(a6g.7): ADR-113 Go conventions + BACKLOG + CHANGELOG`

---

## Critérios de aceite (binários)

- [ ] `.golangci.yml` existe e `golangci-lint run --timeout=3m .` **exita 0** num repo sem código Go (vacuously true).
- [ ] `go.work` existe válido.
- [ ] `services/README.md` + `services/.gitkeep` commitados.
- [ ] `.github/workflows/go.yml` exists; jobs passam (skip inteligente com `if: hashFiles('**/*.go') != ''`).
- [ ] `make go-fmt`, `make go-lint`, `make go-test` retornam 0 num repo sem Go (mensagens informativas OK).
- [ ] `docs/DECISIONS.md` tem ADR-113 (ou próximo número livre) com contexto + decisão + consequências.
- [ ] `docs/CHANGELOG.md` [Unreleased] tem bloco A6g.7.
- [ ] `docs/BACKLOG.md` tabela de lanes marca A6g.7 como ✅.
- [ ] `pre-commit run --all-files` passa (nenhum hook novo adicionado neste slice; hooks Go entram em A6g.6).
- [ ] Zero `.go` produtivo adicionado (esta lane é só infra).

---

## Rollback criteria — ABORTE se

- CI `.github/workflows/go.yml` falha mesmo sem código Go (erro de sintaxe YAML, action inexistente) — reverta o workflow, commit isolado.
- `golangci-lint` pinned version (v1.60 acima) não existe ou foi yanked — use `latest` e documente no ADR.
- Outra lane adicionou workflow em `.github/workflows/` no mesmo turno — rebase, sem force.

Em rollback: `git reset --hard origin/main` na branch local, anuncia, abre issue.

---

## Anti-patterns a evitar

- **Adicionar `.go` de exemplo / "hello-world"** para "testar CI". Zero código produtivo. CI já vacuously-true.
- **Mover `pipeline-service/` para `services/pipeline-service-go/`.** Fora do escopo. A reescrita é decisão separada com ADR próprio.
- **Ativar `forbidigo`/`depguard`** sem código para calibrar. Gera ruído. A6g.6 faz quando houver.
- **Requerer Go 1.23+ / features bleeding-edge.** 1.22 é LTS com ampla suporte em runners.
- **Adicionar dependency Go** (qualquer `require` em `go.mod`). Skeleton puro.
- **Duplicar convenções do CLAUDE.md no ADR.** ADR referencia CLAUDE.md; não reexpõe a lista inteira.

---

## Coordenação com outros agentes

Lanes ativas relevantes:

- `agent/a6e*` — Python backend. **Zero overlap** (você só adiciona `.go*`, `.golangci.yml`, `services/`, workflow novo).
- `agent/a6g2-pipeline-style/*`, `agent/a6g4-frontend-style/*` — sweeps Python/TS. Zero overlap.
- `agent/a6g6-enforcement/*` (futuro) — vai adicionar rules ao seu `.golangci.yml`. Sem conflito (arquivo diferente).

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  .github/workflows/ \
  Makefile \
  docs/DECISIONS.md docs/CHANGELOG.md docs/BACKLOG.md
```

Se outro agente tocou `.github/workflows/*.yml` <30min atrás, espere 2min, anuncie, commite seu workflow no mesmo turno.

**Sessão curta:** 1-2h total. Skeleton + ADR + docs. Não é lane de sessão longa.

---

## O que esta lane NÃO entrega

- **Código Go produtivo** — fora do escopo. Esta lane é infra/config.
- **Reescrita de `pipeline-service/`** — decisão separada, ADR próprio.
- **`forbidigo`/`depguard` rules ativas** — A6g.6 quando houver código.
- **Codegen `oapi-codegen` do OpenAPI para Go** — A6g.7b ou parte da reescrita real.
- **Go modules + dependências** — nada de `require` real. Skeleton puro.
- **Mudar Python/TS** — nenhum arquivo existente tocado exceto docs (CHANGELOG/BACKLOG/CLAUDE link) e Makefile (append-only).

---

## Referências

- [ADR-112](../../../DECISIONS.md) — pipeline-as-service (motivação para Go)
- [CLAUDE.md §Code style › Go](../../../../CLAUDE.md#code-style) — regras inegociáveis
- [ARCHITECTURE §17](../../../reference/ARCHITECTURE.md) — arquitetura alvo pós-A6
- [golangci-lint docs](https://golangci-lint.run/usage/configuration/) — lint config reference
- [effective-go](https://go.dev/doc/effective_go) — idioms
- Prompts paralelos: [track_a6f1](a6f1-pipeline-service.md), [track_a6e4](a6e4-thin-routers.md)
