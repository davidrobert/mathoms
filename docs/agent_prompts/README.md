# Agent Prompts — índice e convenções

Pasta contém **prompts self-contained** para rodar uma task específica do
Sprint A6 (ou outra sprint transversal). Cada prompt é consumido por um
agente LLM rodando em branch `agent/<slug>/<timestamp>` — deve conter
contexto suficiente para a task começar sem precisar ler o BACKLOG
inteiro.

## Índice de prompts

> **Fonte única de status/ocupação:** [../BACKLOG.md §Lanes abertas agora](../BACKLOG.md#lanes-abertas-agora--pickup-table). Este índice lista apenas **o que tem prompt escrito** — status omitido de propósito para evitar drift entre dois lugares.

| Lane | Arquivo | Onda | Branch prefix |
| --- | --- | --- | --- |
| A6g.2 Pipeline Code Style Sweep | [track_a6g2_pipeline_style_sweep.md](track_a6g2_pipeline_style_sweep.md) | 1 | `agent/a6g2-pipeline-style/*` |
| A6g.4 Frontend Code Style Sweep | [track_a6g4_frontend_style_sweep.md](track_a6g4_frontend_style_sweep.md) | 1 | `agent/a6g4-frontend-style/*` |
| A6f.1 Pipeline-as-Service (HTTP boundary) | [track_a6f1_pipeline_service.md](track_a6f1_pipeline_service.md) | 2 (greenfield) | `agent/a6f1-pipeline-service/*` |
| A6g.5 Tests Sweep (fakes + nomes descritivos) | [track_a6g5_tests_sweep.md](track_a6g5_tests_sweep.md) | 2 | `agent/a6g5-tests-sweep/*` |
| A6e.3 Application Layer (use cases — slice FamilyMember+Category+Goal) | [track_a6e3_use_cases.md](track_a6e3_use_cases.md) | 2 | `agent/a6e3-use-cases/*` |
| A6e.5 `/api/v1/` prefix + aliases + OpenAPI versionado | [track_a6e5_v1_prefix.md](track_a6e5_v1_prefix.md) | 2 | `agent/a6e5-v1-prefix/*` |
| A6e.3b Use cases remanescentes (ConfigBlob+Document+Task) | [track_a6e3b_use_cases_rest.md](track_a6e3b_use_cases_rest.md) | 2 | `agent/a6e3b-use-cases-rest/*` |
| A6e.4 Routers finos (≤50 linhas/endpoint) + teste AST | [track_a6e4_thin_routers.md](track_a6e4_thin_routers.md) | 2 | `agent/a6e4-thin-routers/*` |
| A6g.7 Go prep (`.golangci.yml` + CI skip + `services/` skeleton + ADR-113) | [track_a6g7_go_prep.md](track_a6g7_go_prep.md) | 3 | `agent/a6g7-go-prep/*` |
| A6e.events Domain events tipados (ADR-101 R17) — ex-`A6e.6` | [track_a6e_events_domain_events.md](track_a6e_events_domain_events.md) | 2 | `agent/a6e-events/*` |

Lanes sem prompt dedicado (A6g.3, A6g.6) são descritas direto no BACKLOG.

## Antes de começar — pickup protocol

1. Verifique a lane na tabela "Lanes abertas agora" do BACKLOG.
2. Rode o check de colisão (CLAUDE.md §Antes de pegar uma task):

   ```bash
   git fetch origin
   git for-each-ref --sort=-committerdate \
     --format='%(committerdate:iso) %(refname:short) %(subject)' \
     refs/remotes/origin/agent/ | head -15
   ```

3. Se já existe `origin/agent/<slug>-*` com commit <24h → pegue **outra**
   lane. Se stale >24h → anuncie retomada e continue OU abra nova
   branch.
4. Crie branch **antes** da primeira edição:
   `git checkout -b agent/<slug>/$(date +%Y%m%d-%H%M)`.

## Cabeçalho padrão de um prompt

Todo prompt novo deve começar com este bloco — permite ao agente decidir
em 10s se essa é a lane dele:

```markdown
# Track <Lane ID> — <Título curto>

> **Lane ID:** A6g.2 (exemplo)
> **Branch prefix:** `agent/a6g2-pipeline-style/*`
> **Depende de:** A6g.1 ✅ (baseline de ofensores)
> **Paralelo com:** A6g.4 frontend sweep (zero overlap de arquivos)
> **Conflita com:** qualquer commit ativo em `scripts/` ou `pipeline/`
> **Onda:** 1
> **Objetivo (1 frase):** aplicar §Code style do CLAUDE.md em X, Y, Z.
> **Fonte de verdade das regras:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style)
```

Depois do cabeçalho, o corpo livre (regras, targets, tiers, gates,
rollback). Ver `track_a6g2_*.md` e `track_a6g4_*.md` como modelo.

## Criando um novo prompt

1. Nome: `track_<lane>_<descricao-curta>.md` (ex.:
   `track_a6e3_use_cases.md`). Lane em lowercase + pontos substituídos
   por nada (`a6e.3` → `a6e3`).
2. Comece com o cabeçalho padrão acima.
3. Inclua pelo menos: **Regras inegociáveis** (do CLAUDE.md), **Targets
   por tier** (tier 1 seguro, tier 2 opcional, tier 3 fora de escopo),
   **Sequência de commits** sugerida, **Gates de push** (pytest, lint,
   drift check), **Rollback criteria**, **Coordenação com outros
   agentes** (paralelos vs conflitantes), **O que NÃO entrega**.
4. Adicione linha na tabela "Índice de prompts" acima.
5. Adicione entrada na tabela "Lanes abertas agora" do BACKLOG.
6. Commit separado: `docs(agent-prompts): add track_<lane>_<desc> (<motivo>)`.

## Por que prompts dedicados?

- **Onboarding em 5 minutos**: agente lê 1 arquivo, não 3 (BACKLOG +
  CLAUDE + ADR relevante).
- **Contexto cristalizado**: gates, rollback criteria, o que **não**
  tocar. Reduz oscilação entre sessões do mesmo agente.
- **Anti-colisão**: branch prefix + lane ID explícitos permitem grep
  rápido ao decidir pickup.
- **Rastreio**: commits no slice citam Lane ID (`(A6g.2 — T1.a)`),
  fácil correlacionar com prompt original.
