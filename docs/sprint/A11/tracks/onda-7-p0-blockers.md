---
id: TRACK-onda-7-p0-blockers
type: track
title: "Track — Onda 7: bloqueadores P0 da Direção E (pós-revisão de produto)"
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

# Track — Onda 7: bloqueadores P0 da Direção E (pós-revisão de produto)

> **Status:** ✅ entregue 2026-04-29 (5 fixes em main, vitest 691 passing,
> ADR-156, CHANGELOG)
>
> **Contexto:** prompt self-contained para nova sessão Claude Code
> dedicada à Onda 7 da Direção E. Branch sugerida:
> `agent/onda-7-p0-blockers/<ts>`, partindo de `origin/main` pós-Direção E
> consolidada (HEAD em `f2284b5` ou superior).
>
> **Esforço estimado:** ~3 dias (5 fixes contidos, baixo risco).
> **Prioridade:** P0 — bloqueia ritual mensal real do produto.

---

## Briefing

A Direção E completa entregou estrutura (Plano + Ação + Relatório) mas a
revisão de produto (2026-04-29) com `product-designer` + `financial-planner`
identificou 5 bloqueadores P0 que **impedem o ritual mensal funcionar
ponta-a-ponta**. Esta onda corrige os 5.

**Estado atual problemático:**

1. `/plano` tem 3 páginas empilhadas em ordem errada (estratégia → mês
   corrente → plano de ação). Cerbasi diz para casal ler:
   estratégia → **o que vamos fazer** → mês corrente como footer.
2. `/acao` abre em "Tarefas" por default mas a peça central da Direção E
   é o **Inbox** (Suggestion → Decision). TODO esquecido em
   `acao/page.tsx:10-12` mesmo após Onda 5 ter entregue.
3. Anchor scroll do relatório → Inbox **não funciona**. Bug crítico que
   quebra o fluxo "promover sugestão para ação".
4. Patrimônio aparece em 2 lugares com fontes potencialmente
   divergentes (PlanoKpiRow + Hero IF). Risco de "dois números
   diferentes na mesma tela" = perda imediata de confiança.
5. Workspace recém-criado mostra 6 blocos vazios em `/plano` —
   onboarding zero é desolador.

## Itens (5 fixes)

### 1. Reordenar `/plano`: Estratégia → Plano de Ação → Mês corrente (collapsible)

**Arquivo:** `frontend/src/app/(app)/plano/page.tsx:74-141`

**Mudança:**
- Mover seção "Plano de Ação" (DecisionsSection + UpcomingTasksWidget +
  LinkedTasksSection) para **antes** de "Mês corrente"
- Tornar "Mês corrente" `<details>` colapsado por default (alertas + KPIs
  operacionais + ChartsGrid). Casal abre quando algo pisca; default é
  colapsado para reduzir scroll na leitura mensal típica
- `<SectionDivider/>` continua, mas o de "Mês corrente" tem ícone
  expand/collapse e está dentro de `<details>`

**Critério de aceite:**
- `/plano` em desktop tem ~6-8 blocos visíveis por default (vs 12 hoje)
- Mês corrente expande com 1 clique e mostra alertas + KPIs + charts
- Mantém URL state opcional via `<details>` data-attribute (não
  obrigatório em v1; futuro pode ser query param)
- Custo: ~30 LOC

**Razão (Cerbasi):** "estamos onde queríamos? o que vamos fazer? como o
mês está nos posicionando?" — última pergunta é footer analítico, não
meio.

### 2. `/acao` default = Inbox quando há pendentes + ler `?tab=`

**Arquivo:** `frontend/src/app/(app)/acao/page.tsx:35-39`

**Mudança:**
```tsx
import { useSearchParams } from "next/navigation";
import { useSuggestionsCount } from "../plano/_components/useSuggestionsCount";

export default function AcaoPage() {
  const params = useSearchParams();
  const { count: pending } = useSuggestionsCount(workspace?.id);
  const initialTab = (params.get("tab") as TabId)
    ?? (pending > 0 ? "inbox" : "tarefas");
  const [tab, setTab] = useState<TabId>(initialTab);
  // ...
}
```

**Critério de aceite:**
- Workspace com sugestões pendentes → `/acao` abre em Inbox
- Workspace sem sugestões → `/acao` abre em Tarefas (default atual)
- Deep-link `/acao?tab=inbox` funciona (bate com link do relatório)
- Custo: ~15 LOC

**Razão:** Onda 5 declarou Suggestion como "peça central" mas Onda 6
deixou Inbox enterrado em segundo lugar. TODO esquecido em
`acao/page.tsx:10-12`.

### 3. Fix anchor `#SUG-XXX` no relatório → Inbox

**Arquivos:**
- `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx:61`
- `frontend/src/app/(app)/acao/page.tsx`

**Bug atual:**
- SuggestionCard usa `data-suggestion-id={suggestion.id}` (não
  `id={...}`) → browser não pula para o card
- AcaoPage não lê `searchParams.tab` nem `window.location.hash` →
  tab e card não posicionam

**Mudança:**
- Adicionar `id={`SUG-${suggestion.id}`}` no Card raiz (manter
  `data-suggestion-id` também — pode ser usado em testes)
- AcaoPage lê hash em useEffect:
  ```tsx
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (!hash) return;
    const el = document.getElementById(hash.slice(1));
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [tab]);
  ```

**Critério de aceite:**
- Click em "Promover para ação" no relatório (`/reports/[id]`) abre
  `/acao?tab=inbox#SUG-XXX` e posiciona scroll no card respectivo
- Card destacado visualmente por 2-3s (subtle highlight via
  `:target` CSS pseudo-class ou state local)
- Custo: ~20 LOC

### 4. Single-source `patrimonio_snapshot` em `usePlanoOverview`

**Arquivo:** `frontend/src/app/(app)/plano/_components/usePlanoOverview.ts`

**Risco atual:** PlanoKpiRow lê `overview.patrimonio` (de `listReports`).
Hero IF lê `overview.progress.patrimonio` (de `computeIFGoal`). Hoje
convergem por sorte do hook; refactor pode introduzir 2 caminhos
divergentes.

**Mudança:**
- Hook expõe **um único** `patrimonio_snapshot: { value: number, asOf: string, sourceReportId: string | null }`
- PlanoKpiRow consome `patrimonio_snapshot.value`
- IFHeroCard recebe esse mesmo valor via prop (em vez de calcular
  via `progress`)
- ADR curta ou comentário fixo no hook: "toda exibição de patrimônio
  em `/plano` vem deste único campo"

**Critério de aceite:**
- Test unitário garante PlanoKpiRow + IFHeroCard mostram exatamente
  o mesmo número
- `usePlanoOverview` retorna o snapshot mesmo quando IFGoal não
  existe (KPI ainda mostra patrimônio)
- Custo: ~10 LOC + 1 test

### 5. `<OnboardingHero/>` para workspace zero

**Arquivo novo:** `frontend/src/app/(app)/plano/_components/OnboardingHero.tsx`

**Comportamento:**
- Renderizar quando `!ifGoal && decisions.length === 0 && tasks.length === 0`
- 3 next-steps verticais com badges de progresso:
  1. **Configurar IF** (CTA primário → `/plano/meta-if/wizard`)
  2. **Importar primeiro relatório** (CTA secundário → `/documents`
     ou `/pipeline`)
  3. **Criar primeira decisão** (CTA terciário, desabilitado até IF
     configurada)
- Esconde resto do `/plano` (todos os outros blocos)
- Mensagem ensinante: "Mathoms te ajuda a ler sua vida financeira
  e planejar próximos passos. Comece configurando sua meta de
  Independência Financeira."

**Critério de aceite:**
- Workspace zero → `/plano` mostra **só** OnboardingHero
- Após IF configurada → resto do `/plano` aparece (mesmo se ainda
  não houver report)
- Botão (1) está desabilitado se IF já configurada
- Custo: ~80 LOC

## Coordenação com outras ondas

- **Onda 8 (coerência metodológica)** depende de Onda 7 #4 (single-source
  patrimônio) para evitar regression. Pode rodar em paralelo se branch
  separada e merge atento.
- **Onda 9 (design system polish)** independente — pode rodar em paralelo.

## Referências

- Revisão de produto (2026-04-29): conversation log na sessão atual,
  síntese product-designer + financial-planner + PM analysis.
- Direção E original: `~/.claude/plans/quero-repensar-as-interfaces-mellow-nova.md`.
- ADRs relevantes:
  [ADR-151](../DECISIONS.md#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces),
  [ADR-152](../DECISIONS.md#adr-152--plano-de-acao-renomeada-para-acao-com-tabs-direção-e--onda-6),
  [ADR-153](../DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples),
  [ADR-154](../DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1),
  [ADR-155](../DECISIONS.md#adr-155--dashboard-absorvido-por-plano-direção-e-consolidação).

## Sequência de execução sugerida

1. **Phase 1 (~0.5 dia):** itens #2 (default Inbox) + #3 (anchor) — fixes
   contidos no `/acao`. Entrega valor imediato (ritual relatório → /acao
   funciona).
2. **Phase 2 (~0.5 dia):** item #4 (single-source patrimônio) — backbone
   para Onda 8.
3. **Phase 3 (~1 dia):** item #1 (reordenar /plano com collapsible) —
   maior mudança visual; rodar com smoke test.
4. **Phase 4 (~1 dia):** item #5 (OnboardingHero) — novo componente,
   testar com workspace zero e workspace povoado.
5. **Phase 5 (~0.5 dia):** ADR-156 (curta — "Patrimônio single-source"),
   CHANGELOG, PR.

## Não fazer nesta sessão

- ❌ Decisions atualizam Goals (Onda 8)
- ❌ Novas regras de Suggestion (Onda 8)
- ❌ Refactor de empty states / filter-tabs (Onda 9)
- ❌ Mobile collapsibles (Onda 9)
- ❌ ADR grande de mudança de modelo

## Critério de aceite global

- [ ] 5 itens entregues em main
- [ ] CI verde
- [ ] Vitest 690+ passing
- [ ] Pre-commit verde, code-style baseline mantido
- [ ] ADR-156 (Patrimônio single-source) escrita
- [ ] CHANGELOG entry
- [ ] Smoke test humano: abrir /plano com workspace zero, depois
  povoado; clicar promover sugestão no relatório → cair no card
  certo; ler /plano em modo casal (≤30s para entender posição)

## Branch + commits

- Partir de `origin/main` pós-Direção E (HEAD `f2284b5` ou superior)
- Branch: `agent/onda-7-p0-blockers/<yyyyMMdd-HHmm>`
- Commits sugeridos:
  1. `fix(acao): default tab Inbox quando há pendentes + ler ?tab=`
  2. `fix(acao): anchor #SUG-XXX scrolla até o card`
  3. `refactor(plano): single-source patrimonio_snapshot (ADR-156)`
  4. `feat(plano): reordena seções + Mês corrente collapsible`
  5. `feat(plano): OnboardingHero para workspace zero`
  6. `docs(adr): ADR-156 + CHANGELOG`
- Push direto em main quando CI verde (após validação humana das
  mudanças visuais).
