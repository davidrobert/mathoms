---
id: TRACK-a6g4-frontend-style-sweep
type: track
title: "Track A6g.4 — Frontend Code Style Sweep"
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

# Track A6g.4 — Frontend Code Style Sweep

> **Lane ID:** A6g.4
> **Branch prefix:** `agent/a6g4-frontend-style/*`
> **Depende de:** A6g.1 ✅ (baseline de ofensores em `docs/archive/audits/`)
> **Paralelo com:** A6g.2 pipeline sweep (zero overlap — toca só `scripts/` + `pipeline/`)
> **Conflita com:** commits simultâneos em `frontend/src/`
> **Onda:** 1
> **Índice de prompts:** [docs/agent_prompts/README.md](../../../../README.md)
> **Fonte de verdade das regras:** [CLAUDE.md §Code style](../../../../CLAUDE.md#code-style)

> **Objetivo:** aplicar o `## Code style` do CLAUDE.md ao TypeScript em
> `frontend/src/`, consumindo o baseline de ofensores já catalogado em
> `docs/archive/audits/code_style_audit_20260421.md` (A6g.1 ✅).
>
> **Por que esse slice agora:** A6g.1 deixou 53 ofensores de frontend
> ranqueados (9 T1 any, 7 T2 long files, 24 T3 long functions, 1 T4
> forbidden filename, 12 T5 hex colors). Todos são categorias com solução
> bounded — nada exige refactor arquitetural. Baseline é o gate: cada
> commit deve mover o contador de ofensores para baixo, sem regressão em
> outras categorias.
>
> **Paralelizável:** Zero overlap com `backend/app/` (A6e Task) e com
> `pipeline/`+`scripts/` (A6g.2). Você toca **apenas** `frontend/src/`.

---

## Regras inegociáveis

Do CLAUDE.md `## Code style`:

1. **Sem `any`**. Use `unknown` + narrow para input externo. Tipos do codegen
   (`frontend/src/generated/`) são fonte de verdade — **não editar**.
2. **Arquivos ≤500 linhas.** `frontend/src/lib/api.ts` (1880 linhas) e
   `frontend/src/app/(app)/pipeline/page.tsx` (1195 linhas) violam.
3. **Funções ≤20 linhas.** Componentes React são funções — contam.
   Cap de 20 é aspiracional; `high` severity = >40 linhas.
4. **Sem nomes proibidos em filenames:** `data.ts`, `handler.ts`, `utils.ts`,
   `helpers.ts`, `Manager.ts` — grep <5 hits é o teste.
5. **Sem hex literal.** Cores vão em `design-tokens/tokens.json` → CSS vars
   (`var(--brand-*)`, `var(--semantic-*)`). ADR-076.
6. **Formatter:** `prettier` + `eslint` rodam no pre-commit. Diff
   "formatter-only" **nunca** mistura com lógica.
7. **Preserve comentários existentes em refactor.** Eles carregam histórico.

---

## Baseline (entrada)

Consulte `docs/archive/audits/code_style_audit_20260421.md`. Categorias frontend
(T1-T5) totalizam **53 ofensores** distribuídos em ~10 arquivos.

### T1 — `any` explícito (9 high)

```
frontend/src/app/(app)/dashboard/page.tsx:228           (entry: any)
frontend/src/components/report/sections/S3InvestimentosSection.tsx:47-68  (6 casts `as any`)
frontend/src/components/report/sections/S7IndependenciaSection.tsx:33    (1 cast)
frontend/src/lib/api.ts:497                              (data: any)
```

**Padrão de fix:** introduzir tipo concreto. Olhe o tipo de `inv`,
`estrategiaAporte`, `contrafluxo`, `ratios`, `previdencia` na prop do
componente pai ou no response da API; use tipos gerados em
`frontend/src/generated/` quando existirem.

Para `api.ts:497` (`data: any` num campo genérico), tipo correto é
provavelmente `unknown` + narrow no ponto de uso, ou uma generic
`<T> data: T`.

### T2 — Arquivos >500 linhas (7: 2 high, 5 med)

| Arquivo                                            | Linhas | Severity |
| -------------------------------------------------- | ------ | -------- |
| `frontend/src/lib/api.ts`                          | 1880   | high     |
| `frontend/src/app/(app)/pipeline/page.tsx`         | 1195   | high     |
| `frontend/src/app/(app)/documents/page.tsx`        | 801    | med      |
| `frontend/src/app/(app)/transactions/page.tsx`     | 742    | med      |
| `frontend/src/app/(app)/plano/page.tsx`            | 630    | med      |
| `frontend/src/app/(app)/plano/alocacao/wizard/page.tsx` | 533 | med    |
| `frontend/src/app/(app)/dashboard/page.tsx`        | 525    | med      |

**Padrão de decomposição:**

- `lib/api.ts` (1880 l): por domínio. Quebre em
  `lib/api/auth.ts`, `lib/api/documents.ts`, `lib/api/pipeline.ts`,
  `lib/api/tasks.ts`, `lib/api/goals.ts`, `lib/api/config.ts`. Um
  `lib/api/index.ts` re-exporta para não quebrar imports. **Priorize
  alto impacto (divide em 5-6 módulos, remove -900 linhas do hotspot).**

- Páginas (`page.tsx`): extrair componentes para
  `app/(app)/<rota>/_components/<Nome>.tsx` (convenção Next.js para
  components colocated que não viram rota). Decompor por seção visual:
  header, filtros, tabela, empty state. O `page.tsx` fica como
  orchestrator fino (<300 linhas de estado + composição).

### T3 — Funções >40 linhas (24 high, segundo top-10)

```
NotificationCenter.tsx:62      len=164  (componente)
register/page.tsx:15           len=130  RegisterPageInner
CommandPalette.tsx:47          len=111
login/page.tsx:15              len=108  LoginPageInner
UpcomingTasksWidget.tsx:29     len=94
ApendiceASection.tsx:51        len=61
WorkspaceSwitcher.tsx:38       len=49
ConfirmDialog.tsx:60           len=48   useConfirmDialog (hook!)
lib/useCurrentWorkspace.ts:32  len=46
lib/pipelinePhases.ts:125      len=44   computePhaseStates
```

**Padrão de decomposição em componentes:**

- Extrair sub-componentes (cabeçalho, body, footer) quando houver >3 seções
  visuais lógicas.
- Extrair hooks customizados quando houver lógica de estado reutilizável:
  `useXyz()` consolidando `useState`+`useEffect`+callbacks relacionados.
- Extrair handlers para funções nomeadas acima do `return` (JSX handler
  inline vira `handleXyz` puro).

**Para hooks:** `useConfirmDialog` (48 linhas, em `ConfirmDialog.tsx`) é
caso típico — separar renderização (componente) da lógica de estado
(hook). Mover hook para `src/lib/useConfirmDialog.ts` ou
`src/hooks/useConfirmDialog.ts`.

### T4 — Filename proibido (1 med)

```
frontend/src/lib/utils.ts
```

**Fix:** o arquivo existe e tem conteúdo. Para cada função/constante nele,
renomear para nome específico: `lib/tailwind-merge.ts`, `lib/cn.ts`
(se só tiver o helper clássico `cn`), etc. Atualizar imports com
`find+sed`.

Regra geral: cada export do `utils.ts` deve caber num módulo com nome
que explique **o que ele faz**, não "utils". Grep de imports identifica
todos os call-sites.

### T5 — Hex colors (12 med)

Todos em `frontend/src/app/(app)/dashboard/page.tsx:50-59` — paleta
inline de 10 cores usada provavelmente em um chart.

**Fix:** mover para CSS vars. Checar se já existem semantic/brand tokens
equivalentes em `design-tokens/tokens.json`. Se não, criar slot
`--chart-series-{1..10}` e usar `var(--chart-series-1)` etc.

Depois de editar `tokens.json`, rodar `python3 design-tokens/build.py`
(conforme ADR-076) para regenerar CSS. Pre-commit hook bloqueia se
token + CSS saírem de sync.

---

## Escopo (o que vale tocar vs. o que não)

### Dentro do escopo

- `frontend/src/lib/**`
- `frontend/src/components/**`
- `frontend/src/app/**` (exceto `layout.tsx` da raiz — não mexer em carregamento de fontes)
- `frontend/src/hooks/**` (se existir; caso contrário criar)
- Eventualmente `design-tokens/tokens.json` + build, para T5 fix

### Fora do escopo

- `frontend/src/generated/**` — codegen, fonte de verdade da API. **Nunca editar.**
- `frontend/tests/**` — A6g.5 cobre isso em Onda 2
- Mudanças de comportamento visual ou funcional. Sweep é refactor puro:
  comportamento idêntico antes/depois; diff deve ser organizacional ou
  de tipagem.
- Deps bump, Next upgrade, ESLint config — fora

---

## Sequência de execução

### 1. Setup (5 min)

```bash
git fetch origin
git checkout -b agent/a6g4-frontend-style/$(date +%Y%m%d-%H%M)
git log --oneline origin/main -5
```

### 2. Baseline funcional

```bash
cd frontend
npm install           # se lockfile mudou desde último setup
npm test -- --run     # Vitest baseline
# Anotar: quantos passed/failed. Zero novos failures permitidos.
```

**Nota:** Playwright E2E (`npm run test:e2e`) **não** precisa rodar a
cada commit — só antes do push final. É lento e flaky; rode uma vez
no fim.

### 3. Regenere audit baseline (gate de progresso)

```bash
cd ..    # raiz do repo
python dev/audit_code_style.py --format json --output-dir _scratch/
# guarda o total inicial de ofensores T1-T5 como baseline
grep -c '"category":' _scratch/code_style_audit_*.json
```

Cada commit seu deve **reduzir** esse número por pelo menos 1, sem
aumentar outras categorias. Re-rode após cada commit para conferir.

### 4. Commits — ordem sugerida (6 commits, cada um ≤300 linhas de diff)

Pegue **um ofensor categoria por commit**. Não misture T1 com T3 no
mesmo commit.

**Commit 1** — `frontend(types): elimina any em S3/S7 investimentos section (A6g.4 — T1)`
- `components/report/sections/S3InvestimentosSection.tsx` — 6 ocorrências
- `components/report/sections/S7IndependenciaSection.tsx` — 1 ocorrência
- Introduzir tipos concretos; verificar `frontend/src/generated/` para tipos
  de `Investimentos`, `Previdencia`, `Ratios`, etc
- Zero mudança visual; `npm test -- --run` verde

**Commit 2** — `frontend(types): elimina any em dashboard + api.ts (A6g.4 — T1)`
- `app/(app)/dashboard/page.tsx:228` — `(entry: any)` → tipo concreto
- `lib/api.ts:497` — `data: any` → `unknown` + narrow OU `<T> data: T`
- Zero mudança funcional

**Commit 3** — `frontend(lib): rename utils.ts → cn.ts / tailwind-merge.ts (A6g.4 — T4)`
- Identificar exports de `lib/utils.ts` via `grep -rn "from .*lib/utils" frontend/src/`
- Renomear arquivo + atualizar todos os imports
- Se houver múltiplos exports, quebrar em 2+ arquivos
- `npm test -- --run` verde

**Commit 4** — `frontend(theme): hex chart colors → CSS vars (A6g.4 — T5)`
- `dashboard/page.tsx:50-59` — 10 hex colors → `var(--chart-series-1..10)`
- Editar `design-tokens/tokens.json` adicionando slots `chart.series.{1..10}`
- Rodar `python3 design-tokens/build.py`
- Commitar CSS regenerado junto

**Commit 5** — `frontend(lib/api): decompõe 1880 → 6 módulos por domínio (A6g.4 — T2)`
- Quebrar `lib/api.ts` em `lib/api/{auth,documents,pipeline,tasks,goals,config}.ts`
- `lib/api/index.ts` re-exporta tudo — imports existentes seguem funcionando
- **Cada módulo ≤400 linhas**; idealmente ≤300
- Se algum módulo ainda passar de 500, quebrar sub-módulo (ex.:
  `lib/api/tasks/{tasks,suggestions,attachments}.ts`)
- **Este é o commit maior** (~1880 linhas movidas); valide com
  `npm test -- --run` + smoke manual no browser (login, upload,
  ver relatório) antes de seguir

**Commit 6** — `frontend(components): decompõe NotificationCenter + CommandPalette (A6g.4 — T3)`
- Pegue 2-3 dos componentes >100 linhas (`NotificationCenter` 164,
  `CommandPalette` 111, `LoginPageInner`/`RegisterPageInner` ~100 cada)
- Para cada, extrair: (a) hook customizado se houver lógica de estado,
  (b) sub-componentes para seções visuais
- Após: componente principal ≤60 linhas; cada filho ≤40
- `npm test -- --run` + verificação manual do fluxo afetado

**Se você tem tempo, adicione commit 7-8:**
- Páginas grandes (pipeline, documents, transactions) em
  `_components/` colocated
- Priorize por severity (high) e por linhas — `pipeline/page.tsx` (1195)
  dá maior redução de ofensores

### 5. Docs + push

**Commit N+1** — `docs(a6g.4): CHANGELOG + BACKLOG — 1ª rodada sweep frontend`
- `docs/CHANGELOG.md [Unreleased]` — seção "A6g.4 1ª rodada" com:
  - Categoria atacada (T1-T5)
  - Contagem **antes/depois** por categoria (extraído dos baselines)
  - Arquivos tocados
  - Impacto (ex.: "T1: 9 → 0; T2: 7 → 3 (api.ts removido, 6 pages
    ainda >500 l); T4: 1 → 0; T5: 12 → 0")
- `docs/BACKLOG.md` — marcar A6g.4 como "🚧 parcial — 1ª rodada 2026-04-XX"
  (provavelmente precisará de 2ª rodada para as páginas maiores; manter
  aberto)
- **Commit separado**, regra hotspot

### 6. Gates de push

```bash
.venv/bin/pre-commit run --all-files
cd frontend && npm test -- --run
cd frontend && npm run test:e2e   # rodar agora, 1x, antes de push
# Se E2E quebrar em cenário NÃO relacionado (flake) — 1 retry; se
# persistir, investigue. Sweep não pode mascarar regressão.
cd ..

# Regenerar audit e confirmar redução
python dev/audit_code_style.py --format json --output-dir _scratch/
# conferir deltas

# Drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && cd frontend && npm test -- --run

git push origin HEAD:main
```

---

## Critérios de aceite (binários)

- [ ] `T1` (any) drop de **9 → ≤2** (pode sobrar 1-2 em lugares onde
      o tipo correto vem do backend via shape dinâmico; documentar com
      comentário citando issue/ADR)
- [ ] `T4` (forbidden filename) drop de **1 → 0** (utils.ts renomeado)
- [ ] `T5` (hex colors) drop de **12 → 0** (dashboard em CSS vars)
- [ ] `T2` (long files): **pelo menos `lib/api.ts`** decomposto; outras
      páginas podem ficar para 2ª rodada
- [ ] `T3` (long functions): drop de **24 → ≤18** (pelo menos 6 componentes
      decompostos); 2ª rodada pega resto
- [ ] `npm test -- --run` passa sem novos failures
- [ ] `npm run test:e2e` passa (pode ter 1 retry em teste flaky
      não-relacionado)
- [ ] `docs/archive/audits/code_style_audit_<novadata>.md` regenerado e commitado
      se for rodar novo snapshot (opcional; prompt padrão é não substituir)
- [ ] Pelo menos 6 commits atômicos em `origin/main` fast-forward
- [ ] `docs/CHANGELOG.md [Unreleased]` tem entrada A6g.4 1ª rodada com
      deltas numéricos
- [ ] `docs/BACKLOG.md` §A6g.4 marca parcial + data

---

## Anti-patterns a evitar

- **Misturar categorias num commit.** "T1 + T3 juntos" dificulta revisão.
  Um ofensor por commit, ou commit por arquivo se são todos da mesma
  categoria.
- **Formatter-only na mesma commit de mudança real.** Rode prettier em
  commit separado (ou deixe pre-commit rodar e aceite o diff antes de
  criar o commit de lógica).
- **Touch em `generated/`.** Se seu diff inclui
  `frontend/src/generated/*`, algo está errado — é codegen.
- **Mudança funcional sub-reptícia.** Sweep é **organizacional**. Se
  você está reordenando props, mudando comportamento ou removendo
  features, saia do escopo e abra task separada.
- **Arquivos temporários/reports na raiz.** Só em `_scratch/`.

---

## Coordenação com outros agentes

Em paralelo a você podem estar rodando (Onda 1):
- `agent/a6e-task/*` — slice backend. Zero overlap (nunca toca `frontend/`).
- `agent/a6g2-pipeline-style/*` (se alguém pegar) — `pipeline/` + `scripts/`.
  Zero overlap.

**Hotspots compartilhados** (CHANGELOG + BACKLOG — commit atômico ≤5 min):

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md
```

Se agente Task fez commit <30min, pause 2 min, anuncie, commite.
Se Task e A6g.4 terminam próximos, faça PR/push sequencial — não
simultâneo.

Sync periódico (sessão >1h):
```bash
git fetch origin && git log --oneline HEAD..origin/main
# se origin/main moveu ≥1 commit, rebase incremental
```

---

## Rollback criteria

Aborte o sweep e reabra discussão se:
- `lib/api.ts` decomposto quebra ≥5% dos testes Vitest (sinaliza que a
  divisão por domínio não bate com a realidade de uso — repensar
  boundaries)
- Playwright E2E falha em cenário `@critical` pós-decomposição de
  `page.tsx` (sinaliza bug introduzido na separação de componentes —
  fix antes de seguir)
- `design-tokens/tokens.json` + build gera diff maior que esperado
  (outras CSS vars mexidas sem querer)
- `pre-commit` bloqueia por "design tokens out of sync" — rode
  `python3 design-tokens/build.py` de novo e commite o CSS regenerado

---

## O que este sweep NÃO entrega (explicitar no CHANGELOG)

- **Enforcement automatizado** (ESLint rule `no-explicit-any: error`)
  fica para A6g.6 em Onda 3 — só vale ligar o gate quando T1 já estiver
  baixo.
- **Refactor arquitetural** das páginas (ex.: migrar de pages para
  server components, dividir por feature) — fora. Escopo é style,
  não arquitetura.
- **Segunda rodada** para páginas >500 linhas que sobraram — prompt
  separado em A6g.4b.
