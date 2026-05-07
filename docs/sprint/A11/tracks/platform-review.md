---
id: TRACK-platform-review
type: track
title: "Track Platform Review — Orquestração Multi-Agent (revisão + plano)"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track Platform Review — Orquestração Multi-Agent (revisão + plano)

> **Lane ID:** platform-review
> **Branch prefix:** `agent/platform-review/*`
> **Depende de:** —
> **Paralelo com:** qualquer lane de código (não toca código fora de
> `_scratch/` e `docs/PLATFORM_REVIEW_PLAN.md`)
> **Conflita com:** outra sessão `agent/platform-review/*` ativa (1
> revisão por vez)
> **Onda:** independente
> **Índice de prompts:** [docs/agent_prompts/README.md](README.md)
> **Fonte de verdade das regras:** [CLAUDE.md](../../CLAUDE.md)

> **Objetivo:** Conduzir uma revisão técnica abrangente da plataforma
> (pipeline + backend + docs + design system) usando os subagents de
> `.claude/agents/` em paralelo, consolidar achados e produzir um plano
> de execução resumível por outros agentes em sessões futuras.
>
> **Não-objetivo:** mudanças de código nesta sessão. Único output
> commitado em `main` é `docs/PLATFORM_REVIEW_PLAN.md`.

---

## Papel
Você é o orquestrador, atuando como
[`.claude/agents/senior-cto.md`](../../.claude/agents/senior-cto.md).
Lance os demais especialistas em paralelo via Agent tool, consolide os
achados e produza um plano executável.

## Contexto obrigatório (leia antes de instanciar subagents)
Antes de qualquer delegação, leia e cite explicitamente no consolidado
quais documentos foram considerados:

- [CLAUDE.md](../../CLAUDE.md) — invariantes do repo
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) — stack, stages, domain glossary (§4.1)
- [docs/DECISIONS.md](../DECISIONS.md) — ADRs 001-148+ (use ToC categorizado)
- [docs/BACKLOG.md](../BACKLOG.md) — sprint atual + lanes ocupadas
- [docs/CHANGELOG.md](../CHANGELOG.md) — últimos 30 dias de entregas
- [docs/STATELESS_AUDIT.md](../STATELESS_AUDIT.md) — globais permitidos (ADR-111)
- [docs/PIPELINE_ARTIFACTS.md](../PIPELINE_ARTIFACTS.md) + `config/schemas/`
- `pipeline/stage_spec.py` — `STAGE_REGISTRY` canônico (nomes descritivos pós-F9.2)

**Regra de dedupe:** se um achado já tem ADR aceita, BACKLOG entry
aberto ou CHANGELOG recente, **não re-reportar como novo** — referenciar
e classificar como `known-debt` ou `in-flight`.

## Lentes da revisão

Identificar, com evidência (`arquivo:linha`):

- Ineficiências (performance, custo LLM/cloud, recursos)
- Inconsistências entre código ↔ docs ↔ comportamento real
- Bugs e edge cases (lógica, integração, concorrência)
- Lacunas de precisão / completude / correção
- Desalinhamento entre componentes, domínios e contratos
- Código legado, dead code, débito técnico acumulado
- Gaps de observabilidade, segurança, resiliência e testes
- Violações silenciosas de invariantes (ADR-090 dinheiro, ADR-097 ISP,
  ADR-111 stateless, ADR-143 methodology=code, etc.)

## Escopo

**Inclui:**
- `pipeline/` (foco principal — domain services, stages, schemas)
- `backend/app/` (api, application, services, repositories)
- `frontend/src/` (apenas: design system, report renderer, codegen)
- `docs/**/*.md` (todos)
- `config/` (schemas, layout, pipeline.json) e `dev/` (gates)
- `.github/` (workflows, ruleset)

**Exclui (não revisar nesta passada):**
- `frontend/src/app/**` (telas individuais — passada própria depois)
- Migrations Alembic (apenas ADR-coverage; auditoria SQL fica para
  passada com `data-engineer` dedicado)
- `_archive/` (manual histórico)
- Tests vivos do pipeline (apenas detectar gaps, não revisar internals)

**Profundidade por agente:** cada subagent deve produzir entre **15-40
achados acionáveis** (não mais — concentre nos top issues; não menos —
revisão rasa será reexecutada). Achados duplicados entre agentes contam
uma vez.

## Pré-flight (antes de instanciar subagents)

```bash
git fetch origin
git status                                  # working tree limpo?
git worktree list                           # outras lanes ativas?
git log --since='30 days ago' --oneline    # mudanças recentes (não re-revisar)
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short) %(subject)' \
  refs/remotes/origin/agent/ | head -15
```

Se há lane ativa em `git worktree list` ou `origin/agent/*` <24h,
**marque essa área como "in-flight" e não proponha refactor concorrente**
no plano final.

## Orquestração — subagents em paralelo

Lance **todos** em uma única mensagem com múltiplos `Agent` tool calls:

| Subagent | Lente | Output |
|----------|-------|--------|
| `data-engineer` | Pipeline (E0-E7), schemas, paridade, idempotência, contratos entre stages, MLOps/eval/drift | `_scratch/review-YYYY-MM-DD/findings-data-engineer.md` |
| `financial-planner` | Domain glossary (ADR-143), cálculos monetários (ADR-090), metodologia Perini/Cerbasi/AUVP, auditabilidade | `_scratch/review-YYYY-MM-DD/findings-financial-planner.md` |
| `product-designer` | Design system (ADR-076), report renderer, copy, hierarquia, a11y | `_scratch/review-YYYY-MM-DD/findings-product-designer.md` |
| `sre-devops` | CI/CD, observabilidade (ADR-110), stateless (ADR-111), auth (ADR-109), FinOps, DR | `_scratch/review-YYYY-MM-DD/findings-sre-devops.md` |
| `build-vs-buy` | Dependências substantivas atuais (LLM provider, OCR, banking aggregator, error tracking) — vale o lock-in? | `_scratch/review-YYYY-MM-DD/findings-build-vs-buy.md` |
| `senior-cto` (você) | Visão sistêmica, ADR coverage gaps, boundaries, alinhamento com BACKLOG, trade-offs cross-cutting | `_scratch/review-YYYY-MM-DD/findings-senior-cto.md` |

`YYYY-MM-DD` = data da sessão (use `date +%Y-%m-%d`).

### Briefing comum a todos

Cada agente recebe (você compila no prompt):

1. Esta seção §Contexto obrigatório
2. Sua lente específica (uma frase)
3. Escopo (mesmo de cima)
4. **Schema de finding obrigatório** (abaixo)
5. **Quality gate**: rejeite achados sem evidência `arquivo:linha`,
   sem severidade, ou que duplicam ADR/BACKLOG existente sem citar

### Schema de finding (estrito)

```yaml
- id: DE-001                          # <agent-prefix>-<seq>: DE/FP/PD/SR/BB/CTO
  title: <≤80 chars, imperativo>
  severity: P0 | P1 | P2 | P3         # ver taxonomia abaixo
  category: bug | inefficiency | inconsistency | tech-debt
            | security | observability | docs | dead-code
  evidence:
    - path: pipeline/domain/services/foo.py
      lines: 42-67
      quote: "<≤15 palavras, opcional>"
  impact: <1-2 linhas: o que quebra/custa/atrasa>
  recommendation: <ação concreta — não "considerar X">
  effort: XS | S | M | L              # XS<2h, S<1d, M<3d, L>3d (split L)
  related_adr: ADR-NNN | none
  related_backlog: <link ou none>
  status_external: known-debt | in-flight | new
  uncertainty: <só se >baixa: o que precisa ser verificado>
```

### Taxonomia de severidade (alinhada com BACKLOG)

- **P0** — quebra invariante crítica (dinheiro errado, vazamento de
  dados, regressão silenciosa em paridade legado↔novo, segurança).
  Bloqueia release.
- **P1** — bug funcional confirmado, débito que paga juros mensais,
  inconsistência código↔doc que confunde agentes.
- **P2** — ineficiência mensurável, dead code, gap de teste em código
  ativo, doc desatualizada.
- **P3** — nice-to-have, polish, refactor cosmético.

## Consolidação (você como CTO)

Após todos os relatórios:

1. **Dedupe** — mesmo finding visto por 2 agentes vira um só, com
   `seen_by: [DE, SR]`. Resolva conflitos de severidade pegando a maior.
2. **Conflitos de recomendação** — quando 2 agentes propõem direções
   opostas, registre ambas em **`§Trade-offs`** do consolidado, decida
   como CTO com rationale, e marque a outra como "explored, rejected
   because…". Nunca silencie a divergência.
3. **Cobertura** — produza matriz: cada stage E0-E7 × cada agente =
   coberto/não-coberto. Lacunas viram `coverage-gap` no plano.
4. **Cross-check com BACKLOG** — se ≥3 P0/P1 caem em lane já em
   `in-flight`, sinalize ao usuário antes do plano (pode invalidar a
   lane atual).

Output: `_scratch/review-YYYY-MM-DD/consolidated-findings.md`

## Plano de execução

**Local:** `docs/PLATFORM_REVIEW_PLAN.md` (canonical multi-phase
conforme convenção UPPER_SNAKE de [CLAUDE.md §"Planos → docs/"](../../CLAUDE.md#planos--docs-nunca-_scratch-nunca-claude)).

### Frontmatter (parseável)

```yaml
---
plan: platform-review
created: YYYY-MM-DD
status: active
waves: <N>
total_tasks: <N>
ready_tasks: <N>           # com status: ready e sem deps
last_synced_with_main: <commit-sha>
---
```

### Estrutura fixa (ordem importa — agentes fazem grep posicional)

```
## NEXT UP                  ← topo, sempre. Lista tasks status=ready, sem deps.
## Index                    ← tabela: id | title | wave | status | owner | severity
## Quick Wins               ← tasks XS/S, P1+, sem deps, alto ROI
## Wave 1: <tema>
  ### [W1-T01] <title>
    - id, owner_agent, deps, severity, effort, status
    - acceptance_criteria (testáveis)
    - files_touched
    - related_findings: [DE-003, SR-007]
    - paired_doc_task: [W1-T02]    ← se altera comportamento
    - risk + rollback_plan         ← se M/L
## Wave 2: ...
## Trade-offs registrados   ← decisões de CTO em conflitos entre agentes
## Coverage matrix          ← stage × agente
## CLAUDE.md patches        ← propostas em diff format, NÃO edição direta
```

### Convenções

- **ID estável**: `[W<n>-T<NN>]` zero-padded (`W1-T03`). Reservado para
  grep — nunca renumere depois de criado.
- **Status enum**: `ready` | `blocked` | `in_progress` | `done` |
  `cancelled`. Nada além disso.
- **Granularidade**: 1 task = 1 PR. Effort `L` proibido em wave 1 —
  split obrigatório.
- **Doc é first-class**: toda task que altera comportamento tem task
  pareada `paired_doc_task` (atualizar ADR, ARCHITECTURE.md, RUNBOOK,
  schema). Sem isso, task fica `blocked`.
- **CLAUDE.md** é hotspot ([CLAUDE.md §"Hotspots de documentação"](../../CLAUDE.md#hotspots-de-documentação)).
  Não edite direto no plano. Em vez disso, gere seção
  `## CLAUDE.md patches` com diffs propostos; um agente humano revisa
  e aplica em commit dedicado.

### Priorização

- Pontuação: `severity_weight × impact_weight / effort_weight`
- Tie-break: `dependencies asc`, depois `severity desc`
- **Quick Wins** = `effort ∈ {XS,S}` ∧ `severity ∈ {P0,P1}` ∧ `deps=∅`

### Paralelização

- Dentro da wave: marcar `parallelizable: true` quando task não
  compartilha `files_touched` com outra. Conflito de path = serializar.
- Entre waves: definir `wave_gate` explícito (ex.: "W2 só inicia após
  todas as P0 da W1 mergearem em main").
- Nunca duas tasks tocando o mesmo arquivo na mesma wave (regra hard).

### Resumibilidade

Outro agente, em sessão futura, deve responder em <30s à pergunta:
> "Quais tasks posso pegar agora?"

Sem ler o plano inteiro: **deve bastar ler `## NEXT UP` + `## Index`**.
Se essa propriedade não está garantida, o plano falha o gate de
qualidade.

## Quality gates da própria revisão (auto-verificação)

Antes de devolver o resumo executivo, confirme:

- [ ] Todos os 6 subagents entregaram (não 4 + 2 missing)
- [ ] Cada finding tem `evidence.path` válido (`test -f` mental)
- [ ] Severidades P0/P1 são `≥80%` reproduzíveis com comando local
  (teste, grep, run script)
- [ ] Cobertura: stages E0-E7 cobertos por ≥1 agente cada
- [ ] Dedupe contra BACKLOG: nenhum finding novo duplica entry aberta
- [ ] `## NEXT UP` tem ≥3 e ≤10 tasks
- [ ] Plano tem trade-offs registrados (mínimo 1 — se zero conflitos
  entre 5 agentes, revisão foi rasa)

Se algum gate falha, **reexecute o agente correspondente** com prompt
mais focado (cite os achados que ele perdeu).

## Restrições

- Não execute mudanças de código nesta etapa.
- Não edite `CLAUDE.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`
  diretamente — só propostas em diff no plano.
- Não proponha adoção de SaaS/lib nova sem invocar `build-vs-buy`.
- Não proponha refactor que toca lane `in-flight` (`git worktree list`).
- Não invente caminhos — todo `arquivo:linha` deve existir hoje em HEAD.
- Sinalize incertezas em campo `uncertainty` em vez de chutar.

## Entregáveis (em ordem)

1. `_scratch/review-YYYY-MM-DD/findings-{data-engineer,financial-planner,product-designer,sre-devops,build-vs-buy,senior-cto}.md`
2. `_scratch/review-YYYY-MM-DD/consolidated-findings.md`
3. `docs/PLATFORM_REVIEW_PLAN.md` (commitado, único artefato no `main`)
4. **Resumo executivo no chat** (≤300 palavras):
   - Top 5 P0/P1 com link para finding
   - Próximas 3 waves (`W1`, `W2`, `W3`) com 1 linha cada
   - Coverage gaps explícitos (se houver)
   - Link clicável para o plano

## Anti-padrões a recusar

- "Considerar adicionar logging" → recomendação vaga, rejeitar
- "Refatorar para clean architecture" → escopo gigante, rejeitar
- "Pode ter problema de performance" → sem medição, rejeitar
- "Documentar melhor" → sem alvo específico, rejeitar
- Findings sem `arquivo:linha` → rejeitar e reexecutar

## Sequência de commits sugerida

1. `chore(wip): scaffold _scratch/review-YYYY-MM-DD/` (opcional —
   `_scratch/` é gitignored, mas estrutura pode ser commitada via
   `.gitkeep` se quiser estado intermediário inspecionável; pular
   normalmente)
2. `docs(plan): add PLATFORM_REVIEW_PLAN.md (revisão YYYY-MM-DD)` —
   único commit que vai para `main`. Diff exclusivamente em `docs/`,
   então CI gates de código não se aplicam ([CLAUDE.md §"Concluído"](../../CLAUDE.md#concluído--pr-mergeado-em-main-squash-com-ci-verde)
   exceção docs-only).

## Gates de push (antes de abrir PR)

```bash
pre-commit run --all-files     # PII, paths proibidos, commit msg
# Não rode pytest — diff é docs-only
```

## O que NÃO entrega

- Mudanças em código de produção (`pipeline/`, `backend/`, `frontend/`)
- Edits em `CLAUDE.md`, `BACKLOG.md`, `DECISIONS.md`, `CHANGELOG.md`
  (apenas propostas em diff dentro do plano)
- ADRs novas (apenas identificação de gaps de ADR — criação fica para
  tasks do plano)
- Execução de tasks do plano (agentes futuros consomem)

## Rollback criteria

- Se `consolidated-findings.md` produz <30 findings totais entre 6
  agentes → revisão rasa, descartar e reexecutar com escopo mais
  estreito (1 stage por vez).
- Se ≥40% dos findings P0/P1 já existem no BACKLOG → escopo mal
  definido, refazer pré-flight com filtro `git log --since` mais
  agressivo.
- Se plano final tem >50 tasks → granularidade errada, rebatchar em
  P0-only primeiro.
