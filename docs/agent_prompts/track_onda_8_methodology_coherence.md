# Track — Onda 8: coerência metodológica (Cerbasi/AUVP/Perini completos)

> **Status:** ☐ aberta · depende parcial de Onda 7 #4 (single-source
> patrimônio)
>
> **Contexto:** prompt self-contained para nova sessão Claude Code.
> Branch: `agent/onda-8-methodology-coherence/<ts>`, partindo de
> `origin/main` pós-Onda 7 (idealmente).
>
> **Esforço estimado:** ~5-7 dias (6 itens, médio risco — toca pipeline
> E5, modelo de Decision, design system).
> **Prioridade:** P1 — coerência completa do produto.
>
> **Atualização 2026-05-04:** ADRs renumeradas para 161/162/163
> (157/158/159 já mergearam em main). Coexiste com Suggestion
> `concentracao_imobiliaria_alta` da ADR-160 — não é duplicata da regra
> 9 "concentração por instituição" (uma é classe de ativo, outra é
> instituição financeira).

---

## Briefing

Revisão de produto (2026-04-29) identificou que a Direção E entregou
estrutura sólida mas a **camada metodológica está incompleta**:

- 5 regras Suggestion atuais cobrem AUVP+Perini puro; **faltam 6
  regras** que cobrem Cerbasi (endividamento, comportamental, seguros,
  concentração instituição, lifestyle creep, renda passiva real)
- Decisions e Goals vivem em órbitas separadas — Decision marcada como
  Executada **não atualiza** Goal correspondente, gerando estado
  divergente
- Loop "Suggestion → Decision → Task" quebra na última perna —
  Decision aceita não gera Task automática; usuário precisa criar
  manualmente
- SuggestionCard sem priorização visual de severidade (borda colorida
  definida mas nunca aplicada ao Card root); SuggestionsBanner usa
  `count` como severidade (bug semântico — 1 sugestão `danger` mostra
  banner azul calmo)
- Suggestion aceita meses depois pode estar baseada em KPI obsoleto
  (race condition temporal); Decision precisa congelar `context_snapshot`

Esta onda fecha esses 6 gaps.

## Itens (6 fixes)

### 1. 6 novas regras de Suggestion (Cerbasi/AUVP completo)

**Arquivo:** `pipeline/domain/services/suggestion_generator.py`

**Regras a adicionar:**

| # | Nome | Trigger | Severity | Metodologia |
|---|---|---|---|---|
| 6 | **Endividamento perigoso** | `dividas_total / patrimonio_bruto > 0.30` OU `custo_dividas_pct_aa > retorno_esperado_pct_aa` | `danger` | Cerbasi/AUVP |
| 7 | **Taxa de poupança caindo** | trimestre atual `< trimestre anterior - 5pp` por 2 trimestres seguidos | `warning` | Cerbasi (comportamental) |
| 8 | **Cobertura de seguros insuficiente** | renda_pj > R$50k/mês AND `seguros.vida_invalidez = false` | `danger` | Cerbasi |
| 9 | **Concentração por instituição** | algum banco com `>40%` patrimônio investível | `warning` | AUVP |
| 10 | **Lifestyle creep** | despesa essencial mensal `> inflação_acumulada * 1.5` por 6 meses | `warning` | Cerbasi/Perini |
| 11 | **Renda passiva real (Perini "300")** | renda_passiva_recorrente / custo_de_vida `< 0.30` quando IF % `> 50%` | `info` | Perini |

**Cap revisado:** 6 → 8 sugestões/relatório (com 11 regras candidatas,
cap baixo demais força exclusão de coisas relevantes). Priorização
explícita: ordenar por `severity desc` (danger > warning > info) +
`amount_brl desc`.

**Dedup semântica** (TRS desalinhada + aporte abaixo da meta podem
ser sintoma da mesma causa) — adicionar `category` field na
Suggestion + dedup por `(workspace, category, period)`.

**Critério de aceite:**
- 6 testes determinísticos novos em
  `tests/test_suggestion_generator.py` cobrindo cada regra
- Validação com financial-planner que regras são corretas para alta
  renda PJ + família
- ADR-161 "Regras canônicas de Suggestion v2"
- Custo: ~3 dias

### 2. Decisions atualizam Goals (event projection)

**Arquivos:**
- `backend/app/models/decision.py` (schema novo)
- `backend/app/application/decisions/use_cases/execute_decision.py`
- `backend/app/services/goal_service.py`

**Mudança no schema da Decision:**
```python
class Decision(Base):
    # ... existentes ...
    target_field: str | None  # ex: "goal.if.trs_pct"
    target_value: str | None  # ex: "4.0" (decimal string)
    target_value_type: Literal["pct", "brl", "int", "str"] | None
```

**Comportamento:**
- Quando Decision vira `Executada`, use case `ExecuteDecision` dispara
  `goal_service.update_version(target_field, target_value)`
  atomicamente na mesma transação
- Se `target_field == None`, não dispara projeção (Decisions sem
  target — ex.: "decidi conversar com consultor" — continuam válidas)
- Goal cria nova version com `derived_from_decision_id=<decision.id>`

**Critério de aceite:**
- Ciclo completo: criar Goal IF com TRS=4.5% → criar Decision com
  `target_field="goal.if.trs_pct", target_value="4.0"` → marcar
  Executada → Goal nova versão tem TRS=4.0%
- Test integração novo
- ADR-162 "Decisions como event projection sobre Goals"
- Migration Alembic adiciona campos
- Custo: ~2 dias

### 3. Decision → Task automática (botão "Gerar tarefas vinculadas")

**Arquivos:**
- `frontend/src/app/(app)/plano/_components/DecisionCard.tsx`
- `frontend/src/components/tasks/TaskFormDialog.tsx`

**Comportamento:**
- DecisionCard ganha botão "Gerar tarefas" (visível quando
  `status === "Decidido"` ou `"Executado"`)
- Click abre `TaskFormDialog` em modo bulk com 1-3 templates
  pré-preenchidos baseados no `target_field` da Decision:
  - `goal.if.trs_pct` → "Atualizar planilha de IF" + "Reler relatório
    com novo TRS"
  - `goal.allocation` → "Rebalancear carteira" + "Verificar custos
    operacionais"
  - sem target → "Executar decisão {code}" (template genérico)
- User edita títulos antes de salvar; cada Task criada tem
  `derived_from_decision_id`

**Critério de aceite:**
- Aceitar Suggestion → criar Decision → click "Gerar tarefas" → 1-3
  Tasks criadas em /acao com `derived_from`
- Métrica nova exposta no `ActionStatusBar`: "X% das tarefas vêm de
  decisão" (sinal de aderência metodológica)
- Custo: ~1 dia

### 4. SuggestionCard borda colorida + sort por severidade

**Arquivo:** `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`

**Bug atual:** `SEVERITY_CONFIG.cls` define cores mas a borda esquerda
nunca chega ao Card root. Cards de severidade diferentes parecem iguais.

**Mudança:**
```tsx
const SEVERITY_BORDER: Record<Severity, string> = {
  danger: "border-l-4 border-l-destructive",
  warning: "border-l-4 border-l-amber-500",
  info: "border-l-4 border-l-sky-500",
};

return (
  <Card
    id={`SUG-${suggestion.id}`}  // já adicionado em Onda 7 #3
    data-suggestion-id={suggestion.id}
    className={SEVERITY_BORDER[suggestion.severity]}
  >
    {/* ... */}
  </Card>
);
```

**Sort:** InboxTab ordena por `severity desc, created_at desc`.

**Critério de aceite:**
- Cards `danger` aparecem primeiro, com borda esquerda vermelha
  visível
- Cards `info` aparecem por último com borda azul
- Visual coerente entre Inbox e SuggestionCallout no relatório
- Custo: ~10 LOC

### 5. SuggestionsBanner usa severidade real

**Arquivo:** `frontend/src/app/(app)/plano/_components/SuggestionsBanner.tsx`

**Bug atual:** `count >= 4 ? "warning" : "info"`. 1 sugestão `danger`
mostra banner azul calmo.

**Mudança:**
- `useSuggestionsCount` evolui para `useSuggestionsSummary` retornando
  `{ count: number, maxSeverity: Severity, byCategory: Record<...> }`
- Banner reflete `maxSeverity`:
  - `danger` → vermelho ("3 sugestões críticas pendentes")
  - `warning` → amarelo
  - `info` → azul
- Hook real (não mais stub) chama `/v1/workspaces/{ws}/suggestions/summary`
  novo endpoint backend

**Critério de aceite:**
- 1 sugestão `danger` → banner vermelho
- 5 sugestões `info` + 1 `warning` → banner amarelo
- Custo: ~30 LOC backend (endpoint summary) + ~20 LOC frontend

### 6. Decision congela `context_snapshot` ao aceitar

**Arquivos:**
- `backend/app/models/decision.py`
- `backend/app/application/suggestions/use_cases/accept_suggestion.py`

**Race condition atual:** Suggestion gerada em fevereiro com
`progresso_if=42%` aceita em maio quando virou 48%. Decision
referencia Suggestion fevereiro mas decisão foi tomada com base no
contexto de fevereiro — depois fica perdido qual era o estado quando
a decisão foi tomada.

**Mudança:** Decision ganha campo `context_snapshot: JSON` populado
no momento da aceitação:
```json
{
  "patrimonio_brl": 1234567.89,
  "if_progress_pct": 42.0,
  "trs_pct_when_decided": 4.5,
  "report_id": "rep-abc",
  "report_period": "2026-02"
}
```

**Critério de aceite:**
- Aceitar Suggestion → Decision criada com `context_snapshot`
  populado a partir do **relatório que originou a Suggestion** (não
  do estado atual)
- DecisionCard mostra "Decidida com base em: Patrimônio R$ 1,2M, IF
  42%" (valores do snapshot, não atuais) quando user expande detalhe
- Migration Alembic adiciona campo
- Custo: ~1 dia

## Coordenação com outras ondas

- **Onda 7 #4** (single-source patrimônio) precisa estar mergeada
  antes de #5 (suggestions banner severidade) para evitar regression.
- **Onda 9** (design system polish) independente.
- Pode rodar com Onda 9 em paralelo (branches separadas, merge
  trivial — Onda 8 toca lógica, Onda 9 toca primitivos UI).

## Referências

- Revisão financial-planner (2026-04-29) na sessão da revisão de
  produto.
- ADRs: [ADR-136](../DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain) (Decision),
  [ADR-153](../DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples) (Suggestion),
  [ADR-074](../DECISIONS.md#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório) (Task).
- Methodologies docstring: ver `pipeline/domain/services/financial_score_calculator.py` + `scoring.json`.

## Sequência de execução

1. **Phase 1 (~3 dias):** itens #1 (6 regras Suggestion) — backend +
   pipeline E5 + tests + financial-planner validation.
2. **Phase 2 (~2 dias):** item #2 (Decisions → Goals projection) —
   ADR-162 + migration + use case.
3. **Phase 3 (~1 dia):** item #6 (context_snapshot na Decision).
4. **Phase 4 (~1 dia):** itens #3 (Decision → Task) + #4 (severidade
   visual) + #5 (banner real).

## Não fazer

- ❌ Sucessão / holding (fora de v1, futura ADR explícita)
- ❌ Seguros como módulo (avaliar pós-GA — esta onda só dispara
  Suggestion regra 8 quando ausência detectada; módulo de gestão de
  seguros é separado)
- ❌ PGBL/VGBL otimização (futura)
- ❌ IRPF declaração (futura)
- ❌ LLM-based generation de Suggestions (v1 determinístico)
- ❌ Mexer em design system / empty states (Onda 9)

## Critério de aceite global

- [ ] 6 itens entregues em main
- [ ] 6 regras Suggestion validadas com financial-planner
- [ ] Loop ponta-a-ponta: pipeline gera Suggestion → /acao Inbox
  Aceitar → Decision criada com context_snapshot → Decision Executada
  atualiza Goal → "Gerar tarefas" cria 1-3 Tasks com `derived_from`
- [ ] SuggestionCard com severidade visual; banner reflete
  `maxSeverity`
- [ ] Vitest + pytest verde
- [ ] ADR-161 + ADR-162 + ADR-163 (context_snapshot)
- [ ] CHANGELOG entry
- [ ] Pre-commit verde, code-style baseline mantido

## Branch + commits

- Partir de `origin/main` pós-Onda 7 (ideal) ou pós-Direção E (OK)
- Branch: `agent/onda-8-methodology-coherence/<yyyyMMdd-HHmm>`
- Commits sugeridos:
  1. `feat(suggestions): 6 regras canônicas v2 (ADR-161)`
  2. `feat(decisions): event projection sobre Goals (ADR-162)`
  3. `feat(decisions): context_snapshot ao aceitar (ADR-159)`
  4. `feat(decisions): "Gerar tarefas" com templates derived_from`
  5. `fix(suggestions): borda colorida + sort por severidade`
  6. `feat(suggestions): banner com maxSeverity real`
  7. `docs(adr): ADR-161 + ADR-162 + ADR-159 + CHANGELOG`
