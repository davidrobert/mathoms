# Serviços Go

Raiz para serviços reescritos em Go (pós-A6f.1 · ADR-112 + ADR-113).

Hoje o diretório é apenas skeleton — zero código `.go` produtivo. A
infra de lint + CI + convenções está pronta para o primeiro PR Go não
perder tempo configurando guardrails no meio do caminho.

## Convenções

As regras inegociáveis vivem em `CLAUDE.md` (§Code style › Go) e estão
consolidadas em [ADR-113](../docs/DECISIONS.md#adr-113). Resumo:

- Cada serviço em subdiretório próprio: `services/<name>/` com `go.mod`
  próprio (módulo independente dentro do `go.work`).
- Estrutura: `cmd/<name>/main.go` (entrypoint) + `internal/<aggregate>/`
  (domínio). Interfaces pequenas definidas no **consumer**, não no
  producer.
- **Sem `interface{}`/`any`** fora de util genérico. Tipos concretos em
  assinaturas.
- **Errors tipados:** `var ErrNotFound = errors.New(...)` ou struct com
  `Error()`. Nunca `errors.New("...")` inline espalhado.
- **Dinheiro = `int64` cents** (ADR-090). Nunca `float64` nem
  `decimal.Decimal` sem invariante documentado.
- **`log/slog` com handler JSON** + contexto propagado
  (`slog.With("workspace_id", id)`). Nada de `fmt.Println` fora de CLI.
- **Sem estado mutável em package-level** (paralelo a ADR-111 Python).
  Singletons lazy idempotentes OK (DB pool, slog handler).
- **`gofmt -s` + `go vet` + `staticcheck` + `golangci-lint run`** no
  pre-commit e CI.
- **`go test ./... -race`** obrigatório; race detector sempre on em CI.

## Setup

- Go 1.22+.
- `make go-all` roda fmt + lint + test (no-op enquanto não há `.go`).
- CI: `.github/workflows/go.yml` com skip inteligente — só executa
  quando `hashFiles('**/*.go') != ''`.

## Primeiro serviço (candidato)

`pipeline-service/` (FastAPI Python, A6f.1 · ADR-112) é o candidato
natural à reescrita: stateless rigoroso, contrato HTTP documentado em
`docs/api/v1/pipeline-service.openapi.json`, sem dependência
Python-to-Python via broker. Quando a decisão for tomada, abra ADR
própria e crie `services/pipeline-service-go/` com `go.mod` + entry em
`cmd/pipeline-service/main.go`.

## Ao adicionar o primeiro serviço

1. Criar `services/<name>/go.mod` (`go mod init mathoms.ai/<name>`).
2. Adicionar `use ./services/<name>` em `../go.work`.
3. Ativar regras calibradas (`forbidigo` banindo `fmt.Println`/`interface{}`,
   `depguard` gating boundaries) em `.golangci.yml` — isso é escopo de
   A6g.6, não do primeiro PR.
4. Codegen Go do OpenAPI via `oapi-codegen` (A6g.7b ou parte da
   reescrita).

## Refs

- [ADR-112](../docs/DECISIONS.md#adr-112) — pipeline-as-service (contrato
  HTTP que destravou esta preparação).
- [ADR-113](../docs/DECISIONS.md#adr-113) — Go conventions (este repo).
- [CLAUDE.md §Code style › Go](../CLAUDE.md#code-style).
- [ARCHITECTURE §17](../docs/ARCHITECTURE.md) — arquitetura alvo pós-A6.
