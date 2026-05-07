---
id: ADR-113
type: adr
title: "Convenções Go: `.golangci.yml` + CI + skeleton (A6g.7)"
status: Decidido
phase: "A6g.7"
date: "2026-04-22"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 113"]
tags:
  - type/adr
  - status/decidido
size_lines: 93
---

# ADR-113 — Convenções Go: `.golangci.yml` + CI + skeleton (A6g.7)

**Status:** Decidido (A6g.7) • **Data:** 2026-04-22

**Contexto:** A6f.1 (ADR-112) estabeleceu `pipeline-service/` como
FastAPI standalone falando HTTP — candidato natural à reescrita em Go
(footprint, startup, deploy estático, ausência de GIL). `CLAUDE.md`
§Code style já define regras Go inegociáveis (sem `interface{}`/`any`,
errors tipados, `int64` cents, interfaces pequenas no consumer, `log/slog`
com handler JSON, sem estado mutável em package-level). Sem linter +
CI + ADR rastreável, a convenção vira letra morta: o primeiro PR de Go
inevitavelmente perde tempo debatendo `.golangci.yml` no meio do
trabalho produtivo, e regras específicas do projeto (`int64` cents,
ausência de globais mutáveis) não vivem no `effective-go` para alguém
deduzir sozinho.

Duas alternativas consideradas:

1. **Deferir para o primeiro PR de Go** — rejeitada. Linter vira
   bikeshed no meio do PR que deveria ser foco na reescrita. Zero
   retorno em não fazer agora; custo próximo-de-zero (skeleton + config,
   sessão curta).
2. **Aderir estritamente ao `effective-go` sem ADR próprio** — rejeitada.
   Regras específicas do repo (`int64` cents, stateless package-level
   paralelo a ADR-111, `log/slog` JSON obrigatório) não estão em
   Effective Go; ficariam órfãs em `CLAUDE.md` sem justificativa
   histórica rastreável.

**Decisão:** adotar `.golangci.yml` conservador (errcheck, staticcheck,
gocritic, revive, bodyclose, noctx, sqlclosecheck, rowserrcheck,
errorlint, gocyclo min-complexity=15, goconst, prealloc, unparam,
unconvert, misspell, govet `enable-all`) — sem `forbidigo`/`depguard`
até A6g.6, que calibra com código real. CI em `.github/workflows/go.yml`
com detecção por `hashFiles('**/*.go') != ''` faz skip inteligente
enquanto o repo não tem `.go`, ativando gofmt + vet + golangci-lint +
`go test ./... -race` automaticamente no primeiro PR que introduzir o
primeiro serviço. `services/` skeleton reserva raiz para
`services/<name>/` com `go.mod` próprio. `go.work` declarado na raiz
com apenas `go 1.22` — `use` directive entra no mesmo PR do primeiro
módulo (dir sem `go.mod` faz `go work sync` falhar). Regras
inegociáveis de código (sem `interface{}`/`any`, errors tipados, `int64`
cents, `log/slog` JSON, ausência de estado mutável package-level, race
detector sempre on) continuam em `CLAUDE.md` §Code style › Go — ADR
referencia, não duplica.

**Consequências:**

- ✅ Linter pronto antes do primeiro PR de Go — revisão foca em domínio,
  não em estilo.
- ✅ Regras específicas do projeto (`int64` cents, stateless package-level)
  ganham referência ADR rastreável; quem chegar novo entende **por que**,
  não só **o que**.
- ✅ CI workflow é idempotente — mesmo arquivo funciona em repo com zero
  `.go` (hoje) e em repo com serviços Go (amanhã), sem edição.
- ✅ `Makefile` ganha `go-fmt`/`go-lint`/`go-test`/`go-all` com skip
  defensivo; `make go-all` num repo sem Go retorna 0.
- ⚠️ `.golangci.yml` versão conservadora — A6g.6 ativa
  `forbidigo`/`depguard` (banindo `interface{}`, `fmt.Println` fora de
  `cmd/`, imports cruzando boundary) **depois** que houver código para
  calibrar sem false-positives ruidosos.
- ⚠️ `golangci-lint` pinado em `v1.60` no workflow; upgrade exige
  verificação manual de compatibilidade com as regras ativas.
- ❌ `go.work` com apenas `go 1.22` (sem `use`) é menos idiomático que
  `use (./services/<name>)` apontando para um módulo real — aceito
  porque nenhum módulo existe ainda e `go work sync` com `use` para dir
  vazio aborta. O primeiro PR de Go adiciona `go.mod` + `use` no mesmo
  slice.

**Escopo deferido (follow-ups explícitos):**

- `forbidigo`/`depguard` rules em `.golangci.yml` — A6g.6, depois que
  houver `.go` para calibrar sem ruído.
- Codegen Go do OpenAPI via `oapi-codegen` consumindo
  `docs/api/v1/pipeline-service.openapi.json` — A6g.7b ou parte do
  primeiro PR produtivo.
- Hook `pre-commit` local para `gofmt`/`go vet`/`golangci-lint` —
  A6g.6 (`.pre-commit-config.yaml` ganha entrada Go paralela às
  Python/TS).
- Reescrita efetiva de `pipeline-service/` para Go — decisão separada
  com ADR própria; contrato HTTP de ADR-112 permite rodar ambas
  implementações atrás do mesmo LB durante cutover.

**Artefatos:**

- `.golangci.yml` — config do linter (linters-settings + revive rules
  + errorlint + gocyclo).
- `go.work` — workspace multi-module com guia embutida.
- `services/README.md` + `services/.gitkeep` — onboarding + reserva de
  diretório.
- `.github/workflows/go.yml` — CI com skip inteligente.
- `Makefile` — targets `go-fmt`, `go-lint`, `go-test`, `go-all`.
