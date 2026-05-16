---
id: TRACK-onda-10-cross-route-coherence
type: track
title: "Track — Onda 10: coerência cross-rota (/plano · /acao · /reports)"
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

# Track — Onda 10: coerência cross-rota (/plano · /acao · /reports)

> **Status:** ✅ entregue 2026-05-04 · branch
> `agent/onda-10-cross-route-coherence/20260504-1721` · 7 commits squash-merged
> via PR. Onda 8 (UI semantics dos drafts + 6 regras novas) é independente
> e segue separada.
>
> **Contexto:** prompt self-contained para nova sessão Claude Code.
> Branch: `agent/onda-10-cross-route-coherence/<yyyyMMdd-HHmm>`,
> partindo de `origin/main`.
>
> **Esforço estimado:** ~3-5 dias (5 itens UI puros + 1 toque em
> body de Suggestion draft).
> **Prioridade:** P1 — destrava ritual mensal do casal usuário **agora**
> (3 usuários atuais sentem a fricção toda manhã de domingo).

---

## Briefing

Revisão multi-agente (2026-05-04, `product-designer`) identificou que
o produto entregou estrutura sólida (Onda 4 KPIs, Onda 5 Suggestion,
Onda 6 /acao tabs, Onda 7 P0, ADR-156 patrimônio single-source) mas
**as 3 telas críticas do ritual mensal não se reforçam** — casal
navega entre `/plano` (executive summary), `/reports/[id]` (relatório
premium) e `/acao` (Inbox + Tarefas) e sente como **3 produtos
distintos colados**:

- **`/plano` não tem CTA pro relatório do mês** — produto core
  escondido em sidebar item nivelado com "Pipeline" e "Documentos".
  Casal abre app domingo, vê KPIs, **não sabe que existe documento de
  60 páginas** que aprofunda os mesmos números.
- **Tipografia divergente do mesmo número** — Patrimônio em `/plano`
  HeroCard renderiza `formatCurrency()` em string solta dentro de
  `<p className="font-heading text-3xl">` (Plus Jakarta Sans), o
  mesmo número no relatório §S1 usa `<MonetaryValue/>` (JetBrains
  Mono + tabular-nums). Casal compara, vê números "diferentes",
  desconfia. Quebra regra "valor monetário é sempre `<MonetaryValue/>`"
  do CLAUDE.md §Design System.
- **Backward link Suggestion → relatório quebrado** — Onda 7 #3 fez
  forward `relatório → /acao?tab=inbox#SUG-XXX` (✅), mas o card da
  Inbox em `/acao` **não tem link de volta** para a seção do
  relatório que originou a sugestão. Sugestão fica órfã do contexto.
- **`SuggestionCallout` usa Tailwind utilities (`border-l-sky-500`,
  `bg-amber-50`, `text-red-900`) ao invés de tokens semânticos**
  (`var(--semantic-info|warn|danger)` + `color-mix`). Dark mode
  quebra ou fica fora do tom; mudar marca = caçar 30 lugares.
  ReportCard variants (`warn`, `critical`, `success`) já usam tokens
  corretamente — duplicação de paleta entre 2 componentes que
  comunicam o mesmo conceito (severidade).
- **Body dos drafts Suggestion regra 2 e 3** ("Reserva insuficiente",
  "Alocação fora do alvo") tem copy genérica demais — não diz
  **quanto** falta nem **qual classe**. Não vira Task acionável.
- **Onboarding desnivelado em `/acao`** — Onda 7 entregou
  `<OnboardingHero/>` em `/plano` para workspace zero, mas `/acao`
  com workspace zero mostra `<TasksTab/>` placeholder vazio sem
  tutorial. Usuário que vai direto em /acao (link de email,
  navegação livre) cai num lugar mais frio que `/plano`.

Esta onda fecha esses 6 gaps. Não toca lógica de domínio (regras de
Suggestion são Onda 8); foco é **coerência da experiência** entre
as 3 superfícies.

## Itens (6 fixes UI)

### 1. `<MonetaryValue/>` adotado em `/plano` + prop `size`

**Arquivos:**
- `frontend/src/components/report/MonetaryValue.tsx` (adicionar prop)
- `frontend/src/app/(app)/plano/_components/IFHeroCard.tsx`
- `frontend/src/app/(app)/plano/_components/PlanoKpiRow.tsx`
- Possíveis: outros `_components/` em `/plano` que ainda usem
  `formatCurrency` direto em JSX.

**Mudança no componente:**

```tsx
type MonetaryValueSize = "hero" | "kpi" | "body";

const SIZE_CLASS: Record<MonetaryValueSize, string> = {
  hero: "text-style-hero",      // 4xl extrabold display
  kpi:  "text-style-kpi-value", // 3_5xl bold mono (hoje implícito)
  body: "text-style-mono-value", // sm medium mono (default)
};

// MonetaryValue ganha:
//   size?: MonetaryValueSize;   default "body"
// e aplica SIZE_CLASS junto com font-mono + tabular-nums + null safe.
```

**Migração nos call-sites:**

```tsx
// IFHeroCard antes:
<p className="font-heading text-3xl font-bold">{formatCurrency(patrimonio)}</p>

// IFHeroCard depois:
<MonetaryValue value={patrimonio} size="hero" />
```

```tsx
// PlanoKpiRow antes:
<p className="font-heading text-2xl">{formatCurrency(aporte)}</p>

// PlanoKpiRow depois:
<MonetaryValue value={aporte} size="kpi" />
```

**Critério de aceite:**
- Snapshot Vitest comparando `getComputedStyle(font-family)` do mesmo
  valor monetário em `/plano` HeroCard e `/reports/[id]` §S1 KPI →
  ambos retornam `JetBrains Mono`.
- Zero ocorrência de `formatCurrency(...)` em JSX dentro de
  `frontend/src/app/(app)/plano/_components/**` (grep gate).
- Variação `signed` continua funcionando (gain/loss color).
- Custo: ~0,5 dia.

### 2. Link "Abrir relatório de {mês}" em `/plano`

**Arquivo:** `frontend/src/app/(app)/plano/page.tsx` (header actions
ou local equivalente, próximo ao título da página).

**Comportamento:**
- Resolve último `Report` do workspace via API (já existe
  `listReports({workspaceId, limit: 1, sort: "created_at:desc"})`).
- Renderiza CTA primário "Abrir relatório de {YYYY-MM}" (texto formatado
  com `Intl.DateTimeFormat('pt-BR', {month: 'long', year: 'numeric'})`).
- `<Link href={`/reports/${report.id}`}>` — Next.js client-side nav,
  não window.open.
- **Estado vazio** (workspace sem nenhum `Report` ainda): CTA muda para
  "Gerar relatório do mês" → roda pipeline (rota
  `/pipeline?ws=<id>&run=auto` ou padrão equivalente já existente).
- KPIs do `<PlanoKpiRow/>` viram **clicáveis**: Patrimônio →
  `/reports/{id}#S1`, IF → `#S7`, Aporte alvo → `#S2` (anchor
  hash; padrão Onda 7 #3).

**Critério de aceite:**
- `/plano` em workspace com ≥1 Report mostra link primário "Abrir
  relatório de {mês}".
- Click leva pra `/reports/{id}`.
- Click em KPI Patrimônio leva pra `/reports/{id}#S1` com scroll +
  highlight (já implementado para SUG; reusar o mesmo padrão).
- Workspace zero mostra "Gerar relatório do mês" no lugar.
- Custo: ~0,5 dia.

### 3. Backward link `<SuggestionCard/>` em `/acao` → relatório

**Arquivo:** `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`

**Comportamento:**
- Cada `Suggestion` já tem `report_id` + `section_id` (campos
  existentes em ADR-153). Hoje o card mostra body + ações
  Aceitar/Modificar/Descartar mas **não link de volta**.
- Adicionar link secundário discreto **abaixo do body, antes das ações**:
  - Texto: `"Ver no relatório do mês · §{section_id}"`.
  - Ícone `ExternalLink` (lucide-react) à direita.
  - Token: `text-style-caption` + `text-muted-foreground`.
- `<Link href={`/reports/${suggestion.report_id}#S${suggestion.section_id}`}>`.

**Coordenação com Onda 8 #4:** Onda 8 muda o mesmo arquivo para
adicionar `border-l-4` por severidade. Se Onda 10 mergear primeiro,
Onda 8 só adiciona a borda — sem conflito. Se Onda 8 primeiro, Onda
10 adiciona o link inline. Hotspot **previsível**, baixa fricção.

**Critério de aceite:**
- Card Inbox em `/acao` exibe "Ver no relatório do mês · §S7"
  quando `report_id` e `section_id` populados.
- Click navega para `/reports/{report_id}#S7` com scroll + highlight
  da seção.
- Quando `report_id` é `null` (suggestion órfã, edge case), link é
  omitido (não `disabled`).
- Vitest cobertura de ambos casos.
- Custo: ~0,3 dia.

### 4. `SuggestionCallout` migra para tokens semânticos

**Arquivo:** `frontend/src/components/report/sections/SuggestionCallout.tsx`

**Bug atual:** `SEVERITY_VARIANTS` usa `border-l-sky-500`,
`bg-amber-50/60`, `text-red-900` — paleta default Tailwind
hardcoded.

**Mudança:**

```tsx
// SectionSummary.tsx:35 já usa o padrão correto — replicar:
const SEVERITY_VARIANTS: Record<Severity, string> = {
  info:   "border-l-[var(--semantic-info)] bg-[color-mix(in_oklab,var(--semantic-info)_8%,transparent)]",
  warn:   "border-l-[var(--semantic-warn)] bg-[color-mix(in_oklab,var(--semantic-warn)_8%,transparent)]",
  danger: "border-l-[var(--semantic-danger)] bg-[color-mix(in_oklab,var(--semantic-danger)_10%,transparent)]",
};
```

**Critério de aceite:**
- Zero ocorrência de `border-l-sky|border-l-amber|border-l-red|bg-sky|bg-amber|bg-red|text-red-9|text-amber-9` em
  `frontend/src/components/report/**` (grep gate em pre-commit).
- Dark mode renderiza corretamente em ambos `data-theme="dark"` e
  `.dark` (já gerado por `tokens.css` design-tokens build).
- Visual baseline Playwright para SuggestionCallout {light, dark}
  re-gerada (`gh workflow run CI -f run_visual=true -f
  update_visual_baselines=true`) — diff de cor esperado, aprovar.
- Custo: ~0,3 dia.

### 5. Body dos drafts Suggestion regras 2 e 3 enriquecido

**Arquivo:** `pipeline/domain/services/suggestion_generator.py`

**Bug atual:** drafts da regra 2 (`reserva_insuficiente`) e regra 3
(`alocacao_fora_do_alvo`) têm `body_md` genérico ("sua reserva está
abaixo do alvo", "ajuste a alocação"). Não vira Task acionável.

**Mudanças:**

**Regra 2 — Reserva insuficiente:**

```markdown
Sua reserva atual cobre {meses_atual:.1f} meses de custo essencial,
abaixo do alvo de {meses_alvo:.1f} meses. Faltam **R$ {gap_brl:,.2f}**.
Aportando {aporte_mensal_brl:,.2f}/mês, completa em ~{meses_para_completar}
meses (~{ano_meta:%Y-%m}).

**Próximo passo sugerido:** elevar aporte mensal para reserva ou
direcionar próximo aporte de R$ {proximo_aporte_brl} integralmente
para conta Tesouro Selic / CDB liquidez diária.
```

**Regra 3 — Alocação fora do alvo:**

```markdown
Classe **{classe_mais_subalocada}** está {desvio_pp:.1f}pp abaixo do
alvo (atual {atual_pct:.1f}% vs alvo {alvo_pct:.1f}%). Para
rebalancear, próximo aporte de R$ {proximo_aporte_brl} pode ir
integralmente para essa classe.

**Tabela atual vs alvo:**

| Classe | Atual | Alvo | Δ |
|---|---|---|---|
{linhas_tabela}
```

(Tabela renderizada Markdown — `SuggestionCard` já consome
`react-markdown`; verificar.)

**Decision template integration:**
- `SuggestionDraft` ganha campo opcional
  `decision_target_field` + `decision_target_value` que vai virar
  `Decision.target_field` + `target_value` quando aceita.
- Regra 2 → `target_field = "goal.reserva.gap_brl"`,
  `target_value = "{gap_brl}"`.
- Regra 3 → `target_field = "goal.allocation.next_aporte_classe"`,
  `target_value = "{classe_mais_subalocada}"`.

**Coordenação com Onda 8 #2 (Decisions atualizam Goals):** o campo
`target_field` na Decision **só é projetado** se Onda 8 #2 estiver
mergeada. Antes disso, fica gravado mas não tem efeito.
Compatibilidade forward-only (não breaking). **Pode shipar Onda 10
antes de Onda 8 #2** — fica latent until projection wired.

**Critério de aceite:**
- Pipeline E5 com fixture "reserva insuficiente" gera draft com
  `body_md` contendo `gap_brl`, `meses_para_completar`,
  `proximo_aporte_brl` formatados.
- Pipeline E5 com fixture "alocação fora do alvo" gera draft com
  tabela markdown e classe específica.
- Vitest do `SuggestionCard` renderiza tabela markdown sem regressão.
- Custo: ~1 dia.

### 6. `/acao` workspace zero não fica frio

**Arquivo:** `frontend/src/app/(app)/acao/page.tsx`

**Comportamento atual:** `/acao` em workspace zero
(`pending=0 && tasks=0 && notes=0`) mostra TasksTab placeholder vazio.

**Mudança:** detecção early de workspace zero → renderizar
**banner de redirect** "Configure sua meta IF em /plano para começar
a agir" + CTA para `/plano`. NÃO duplica o `<OnboardingHero/>` (já
existe em `/plano`); só sinaliza que a entrada canônica é `/plano`.

```tsx
const isWorkspaceZero =
  suggestionsCount === 0 &&
  tasksCount === 0 &&
  notesCount === 0;

if (isWorkspaceZero) {
  return (
    <EmptyState
      title="Comece pela tela inicial"
      description="Configure sua meta de Independência Financeira em /plano para começar a planejar suas ações."
      action={<Link href="/plano">Ir para /plano</Link>}
    />
  );
}
```

**Critério de aceite:**
- Workspace zero em `/acao` redireciona visualmente para `/plano`.
- Workspace com ≥1 suggestion / task / note renderiza tabs
  normalmente (sem regressão).
- Vitest cobre ambos cenários.
- Custo: ~0,3 dia.

## Coordenação com outras ondas

- **Onda 8** — toca `SuggestionCard.tsx` (item #4 borda) e
  `suggestion_generator.py` (item #1 6 regras novas). Onda 10 toca
  os mesmos 2 arquivos em itens #3 (link backward) e #5 (body
  enriquecido). Hotspots **previsíveis**:
  - **Ordem segura:** Onda 10 mergeia primeiro (UI puro mais rápido,
    zero migration). Onda 8 vem depois e absorve as mudanças via
    `git merge origin/main` na branch dela.
  - **Ordem invertida** (Onda 8 primeiro) também funciona — conflito
    em `SuggestionCard.tsx` é trivial (1 import + 1 className root).
- **Onda 9** (design system polish + mobile) — independente. Pode
  rodar em paralelo. Onda 9 cria primitivos (`<SectionHeading/>`,
  `<EmptyState/>`, `<SegmentedTabs/>`); Onda 10 item #6 pode usar
  `<EmptyState/>` se Onda 9 mergear antes. Caso contrário, usar
  componente ad-hoc.
- **Onda 7** (P0 bloqueadores) — ✅ pré-requisito mergeado.

## Não fazer

- ❌ Refactor de `<DataTable/>` primitivo compartilhado entre
  `/transactions` e relatório — escopo separado, ~M (3-5d), entra em
  Onda 11 ou separada.
- ❌ Glossário inline `<JargonHint term="TRS">` (siglas) — backlog
  editorial pós-Onda 8/10/11.
- ❌ Voice guide LLM E5.N narrativas — backlog editorial,
  `docs/REPORT_VOICE.md` é doc nova (sprint dedicada com
  financial-planner + product-designer).
- ❌ Mexer em ações Suggestion (Aceitar/Modificar/Descartar dialogs)
  — escopo de Onda 8 #3 "Decision → Task automática".
- ❌ Mover ações de SuggestionCard para virar Decision (escopo Onda
  8 #2/#3).
- ❌ S_IRPF_OTIMIZACAO recriar 2 cards removidos — spawn task
  separada (post-review #1, depende de IRPFAnalyzer ampliado).

## Critério de aceite global

- [ ] 6 itens entregues em `main`.
- [ ] Tipografia: snapshot Vitest confirma `JetBrains Mono` em
  Patrimônio cross-rota (`/plano` vs `/reports`).
- [ ] CTA "Abrir relatório do mês" visível em `/plano` quando há
  Report; "Gerar relatório" no estado vazio.
- [ ] Backward link `/acao` SuggestionCard → `/reports/{id}#S{N}`
  funciona com scroll + highlight.
- [ ] `SuggestionCallout` usa apenas `var(--semantic-*)` —
  grep `border-l-(sky|amber|red)\|bg-(sky|amber|red)` em
  `components/report/**` retorna 0.
- [ ] Drafts Suggestion regras 2 e 3 incluem `gap_brl` /
  `classe` / `proximo_aporte_brl` reais; Vitest do SuggestionCard
  renderiza tabela markdown.
- [ ] `/acao` em workspace zero não exibe TasksTab placeholder
  vazio — redireciona visualmente para `/plano`.
- [ ] Pre-commit verde (style baseline mantido, tokens sync,
  codegen sync, anchor links válidos).
- [ ] Vitest + Playwright `@critical` verde.
- [ ] Visual baselines re-geradas se SuggestionCallout mudou cor
  (item #4).
- [ ] CHANGELOG entry com link para os 6 itens.

## Branch + commits sugeridos

- Partir de `origin/main` atualizado.
- Branch: `agent/onda-10-cross-route-coherence/<yyyyMMdd-HHmm>`.
- Commits sugeridos (1 por item — squash no merge):
  1. `feat(report): MonetaryValue ganha prop size={"hero"|"kpi"|"body"}`
  2. `feat(plano): CTA primário "Abrir relatório de {mês}" + KPIs clicáveis`
  3. `feat(acao): backward link SuggestionCard → relatório §{section_id}`
  4. `refactor(report): SuggestionCallout migra de Tailwind utilities para tokens semânticos`
  5. `feat(suggestions): drafts regras 2/3 com gap_brl + classe + próximo aporte`
  6. `feat(acao): workspace zero redireciona para /plano (não TasksTab vazio)`
  7. `docs(changelog): Onda 10 cross-route coherence`

## Pré-flight

1. `git fetch origin && git status` — clean. Branch nova partindo
   de `origin/main`.
2. Verificar se `agent/onda-8-methodology-coherence/*` está ativa em
   `git for-each-ref refs/remotes/origin/agent/`. Se sim, alinhar
   ordem de merge com agente da Onda 8 (sugestão: Onda 10 primeiro
   por ser mais leve).
3. Confirmar que `<MonetaryValue/>` ainda existe em
   `frontend/src/components/report/MonetaryValue.tsx` (pode ter sido
   movido em refactors recentes).
4. Confirmar que `Suggestion` tem `report_id` + `section_id` no
   schema atual (ADR-153) — campos load-bearing para item #3.

## Referências

- Revisão `product-designer` 2026-05-04 (sessão pós-revisão multi-agente).
- ADRs: [ADR-076](../../../DECISIONS.md#adr-076--design-tokens-unificados-site--relatório) (tokens),
  [ADR-153](../../../DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples) (Suggestion),
  [ADR-156](../../../DECISIONS.md#adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7) (patrimônio single-source).
- Padrão de scroll+highlight de anchor: implementação Onda 7 #3
  (`#SUG-XXX` em /acao).
- CLAUDE.md §Design System: regra "valor monetário é sempre
  `<MonetaryValue/>`" + zero hex literal em frontend.
