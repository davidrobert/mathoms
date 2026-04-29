# Track — Onda 5: Suggestion aggregate full-stack (Direção E)

> **Contexto:** Este prompt é self-contained para nova sessão Claude
> Code dedicada a entregar a Onda 5 da Direção E (redesign de
> interfaces). Branch sugerida: `agent/onda-5-suggestion-aggregate/<ts>`,
> partindo de `origin/main` **após o merge das Ondas 2/3/4/6** (PR
> atual: `agent/decisions-ui-plano/20260428-1654`).

---

## Briefing

Implementar o aggregate **`Suggestion`** full-stack — backend (modelo +
endpoints + pipeline), frontend (callout no relatório + card no
`/acao` Inbox tab). Esta é a peça **central** da Direção E: completa
o ritual **relatório gera sugestões → usuário aceita/modifica/descarta
em `/acao` → vira Decision (+ opcionalmente Tasks)**.

Validado metodologicamente com [financial-planner](.claude/agents/financial-planner.md):
sugestão acionável é a formalização event-sourced de "revisão de tese"
(AUVP) e "pacto familiar" (Cerbasi). Validado com
[product-designer](.claude/agents/product-designer.md): cap 3-6
sugestões por relatório, severidade tripla (info/warning/danger),
copy de leigo escondendo vocabulário event-sourced.

## Estado atual da Direção E (pré-Onda 5)

Ondas já entregues (assumir mergeadas em `main`):

- **Onda 2**: UI de gestão de Decisions D01–D15 em `/plano`
  (componentes em `frontend/src/app/(app)/plano/_components/`:
  `DecisionsSection`, `DecisionFormDialog`, etc).
- **Onda 3**: Modo Tático removido do relatório (ADR-151).
  Relatório agora só Estratégico + USA.
- **Onda 4**: `/plano` virou executive summary com KPIs row +
  `SuggestionsBanner` (que usa stub `useSuggestionsCount` — Onda 5
  liga essa fonte de dados).
- **Onda 6**: rota `/acao` (renomeada de `/plano-de-acao`, ADR-152)
  com 4 tabs (Inbox · Tarefas · Timeline · Notas). Tab **Inbox tem
  empty state ensinante** aguardando esta Onda 5.

Ondas pendentes paralelas (não bloqueiam Onda 5):

- **Onda 1**: migration `kanban_items` + `report_notes` → `tasks` +
  `workspace_notes`. Pode rodar em paralelo nesta sessão (branch
  separada). Onda 5 não depende dela.

## Modelo de domínio proposto (validar com data-engineer e senior-cto)

```python
# backend/app/models/suggestion.py
class Suggestion(Base):
    __tablename__ = "suggestions"

    id: UUID (PK)
    workspace_id: UUID (FK CASCADE, indexed)
    report_id: str (FK reports.id ON DELETE SET NULL)  # rastreabilidade
    section_id: str  # "S2", "S7", "U1"... onde nasceu a sugestão
    suggestion_id: str  # ID estável dentro do relatório, ex "SUG-2026-04-12"

    severity: Literal["info", "warning", "danger"]
    title: str  # imperativo curto, ex: "Reduzir TRS para 4%"
    rationale: str  # 1-2 linhas explicando porquê
    amount_brl: Decimal | None  # opcional, valor envolvido

    status: Literal["Pendente", "Aceita", "Modificada", "Descartada"]

    accepted_decision_id: UUID | None  # FK decisions.id quando vira Decision
    dismissed_reason: Literal[
        "Já considerei", "Não se aplica", "Discordo do diagnóstico",
        "Adiar", "Outro"
    ] | None
    dismissed_at: datetime | None
    accepted_at: datetime | None

    created_at: datetime
    updated_at: datetime
```

**Decisões de design pendentes (responder com data-engineer + senior-cto):**

1. **Sugestão é imutável?** Designer sugeriu sim — sugestão vem do
   gerador (pipeline E5), o que muda é o que o usuário cria a partir
   dela. Confirmar.
2. **Como evitar duplicatas?** Se o relatório de fevereiro gerou
   "Reduzir TRS" e março gera de novo, recriar ou marcar dedup? Designer
   sugeriu: dedup contra descartadas recentes — sugestão idêntica não
   ressuscita; só se houver **diff material** (ex.: TRS subiu de 4,8 →
   5,2%). Como expressar isso? Hash determinístico (workspace + section
   + title slug + amount bucket) que ignora pequenas variações?
3. **Cap de geração:** designer disse 3-6 por relatório. Como o
   pipeline E5 garante? Algoritmo de ranking + threshold?
4. **Origem (LLM vs determinístico):** v1 deve ser determinístico
   (regras simples sobre patrimônio/IF/aporte/alocação) ou já incluir
   LLM com fallback? **Recomendação minha**: v1 determinístico para 4-5
   gatilhos canônicos (TRS desalinhada, reserva insuficiente, alocação
   vs alvo, aporte abaixo da meta, dolarização atrasada); LLM em onda
   futura.
5. **Tasks vinculadas no aceitar:** designer sugeriu "Gerar tarefas
   vinculadas" como toggle opt-in. Templates de tarefas vêm de onde?
   Hard-coded por tipo de sugestão? Sugerido por LLM? **Recomendação**:
   v1 com 1-2 templates hard-coded por tipo de sugestão; LLM em futuro.

## Endpoints REST esperados

```
GET    /v1/workspaces/{ws}/suggestions?status=Pendente
POST   /v1/workspaces/{ws}/suggestions                  # interno (pipeline)
POST   /v1/workspaces/{ws}/suggestions/{id}/accept      # cria Decision
PATCH  /v1/workspaces/{ws}/suggestions/{id}/modify      # cria Decision modificada
POST   /v1/workspaces/{ws}/suggestions/{id}/dismiss     # com reason
GET    /v1/workspaces/{ws}/suggestions/count?status=Pendente  # para banner em /plano
```

`/accept` deve aceitar payload com (a) eventuais modificações ao
preset (title/rationale/amount), (b) toggle `generate_tasks: bool`,
(c) lista de templates de tasks selecionados pelo usuário.

OpenAPI snapshot (ADR-109): `make update-openapi-snapshot` obrigatório.

## Pipeline E5 — geração

Adicionar stage que pós-processa o snapshot E5 e produz sugestões:

```python
# pipeline/domain/services/suggestion_generator.py
class SuggestionGenerator:
    def __init__(self, config: SuggestionGeneratorConfig): ...

    def generate(self, snapshot: ReportAnalysisData) -> list[SuggestionDraft]:
        """Aplica regras determinísticas e retorna até `cap` sugestões
        rankeadas por severity."""
```

Regras canônicas v1 (proposta — refinar com financial-planner):

1. **TRS desalinhada**: se `derived.taxa_retirada_efetiva > taxa_retirada_conservadora * 1.15` →
   `severity=warning`, "Reduzir TRS para X%".
2. **Reserva insuficiente**: se `reserva.meses_cobertura < 6` →
   `severity=danger`, "Aumentar reserva para 6 meses".
3. **Alocação fora do alvo**: se algum bucket > alvo + 10pp →
   `severity=info`, "Rebalancear X% de Y".
4. **Aporte abaixo da meta**: se últimos 3 meses < `meta_aporte * 0.7` →
   `severity=warning`, "Retomar disciplina de aporte".
5. **Dolarização atrasada**: se `dolar.cobertura_pct < meta_pct - 15` →
   `severity=info`, "Acelerar conversão USD".

Cap = 6. Ranking por severity (danger > warning > info) + amount_brl
desc.

## Frontend — componentes a criar

### `<SuggestionCallout/>` no relatório (inline + agregador)

- Localização: `frontend/src/components/report/sections/SuggestionCallout.tsx`
- Renderizado **inline** dentro de cada seção que tem sugestões da
  mesma `section_id` (ex: S7 IF tem callout de TRS embutido)
- Agregador `§ Próximos passos` no fim do relatório com lista de
  títulos + link "Ver em contexto §SX"
- Severidade via faixa lateral 3px + ícone Lucide + label textual
- Botão discreto "Promover para ação ↗" → navega para `/acao?tab=inbox#SUG-XXX`
- No PDF (Playwright): vira nota cinza com ID, sem botão

### `<SuggestionCard/>` em `/acao` Inbox

- Localização: `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`
- Substitui o empty state do `InboxTab` atual quando há sugestões
- Card por sugestão com 3 ações inline: **Aceitar** · **Modificar** ·
  **Descartar**
- "Aceitar" reusa `DecisionFormDialog` da Onda 2 com payload
  pré-preenchido + campo readonly "Origem: Relatório Mar/26 §S7
  SUG-04-12"
- "Descartar" abre mini-dialog com 5 chips de motivo (ver enum acima)
- Filtro topo: Pendentes · Aceitas · Descartadas · Todas

### Hooks

- `useSuggestions(workspaceId)` — lista, filtra, mutação
- Substituir o stub `useSuggestionsCount` em
  `frontend/src/app/(app)/plano/_components/useSuggestionsCount.ts`
  pela implementação real (mesma assinatura)
- Atualizar `ActionStatusBar` em `/acao` para mostrar count real

## Critérios de aceite

- [ ] Aggregate `Suggestion` definido (ADR-153 nova)
- [ ] Migration Alembic + backfill (vazio inicialmente; cria tabela)
- [ ] Endpoints CRUD + accept/dismiss/modify
- [ ] OpenAPI snapshot atualizado (`make update-openapi-snapshot`)
- [ ] Pipeline E5 gera sugestões deterministicamente (regras 1-5)
- [ ] `<SuggestionCallout/>` no relatório (inline + agregador)
- [ ] `<SuggestionCard/>` em `/acao/Inbox`
- [ ] `useSuggestionsCount` real substitui stub em `/plano`
- [ ] `ActionStatusBar` em `/acao` mostra count real
- [ ] Aceitar sugestão cria Decision com `derived_from_suggestion_id`
- [ ] Descartar com motivo persiste e dedup contra novas gerações
- [ ] Testes: unit (gerador determinístico, hooks), E2E
  (`@critical` fluxo aceitar→Decision)
- [ ] CHANGELOG entry
- [ ] Pre-commit verde, code-style baseline mantido

## Fluxo de execução sugerido

1. **Phase 1 — Discussão e design (sessão Claude com plan mode):**
   - Convocar [data-engineer](.claude/agents/data-engineer.md) para
     validar schema da tabela `suggestions` (FK semantics, dedup
     strategy, índices).
   - Convocar [senior-cto](.claude/agents/senior-cto.md) para
     validar endpoints + idempotência do accept (criar Decision em
     transação atomic com update de Suggestion.status).
   - Convocar [financial-planner](.claude/agents/financial-planner.md)
     para refinar as 5 regras canônicas (thresholds, copy).
   - Travar decisões 1-5 da seção "Decisões de design pendentes".
   - Escrever ADR-153 (Suggestion aggregate event-sourced ou simple?
     Recomendo **simple aggregate** — Suggestions são imutáveis, status
     muta via state machine; Decision já é o event-sourced).

2. **Phase 2 — Backend (3-4 dias):**
   - Modelo SQLAlchemy + migration Alembic
   - Repository + Use cases (CreateSuggestion, AcceptSuggestion,
     DismissSuggestion, ListSuggestions)
   - Endpoints REST + DTOs
   - OpenAPI snapshot
   - Tests unitários + integração

3. **Phase 3 — Pipeline E5 (1 dia):**
   - `SuggestionGenerator` em `pipeline/domain/services/`
   - Stage E5 chama generator + persiste via `ArtifactStore` ou
     diretamente via `SuggestionRepository`
   - Tests com snapshots golden

4. **Phase 4 — Frontend (1-2 dias):**
   - Hook `useSuggestions` + types
   - `<SuggestionCallout/>` no relatório + integração com `ReportShell`
     (provavelmente em cada `<S*Section/>` consumindo
     `data.suggestions[section_id]`)
   - `<SuggestionCard/>` no `InboxTab`
   - Replace `useSuggestionsCount` stub
   - `ActionStatusBar` real
   - Tests vitest + E2E `@critical`

5. **Phase 5 — Docs + commit + push:**
   - ADR-153 + CHANGELOG entry
   - Smoke test humano
   - PR

## Arquivos relevantes (referência rápida)

**Já entregues nas Ondas 2-6:**
- `frontend/src/app/(app)/acao/_components/InboxTab.tsx` (placeholder
  — Onda 5 substitui empty state por lista real)
- `frontend/src/app/(app)/plano/_components/SuggestionsBanner.tsx`
  (Onda 5 liga ao count real)
- `frontend/src/app/(app)/plano/_components/useSuggestionsCount.ts`
  (Onda 5 substitui stub)
- `frontend/src/app/(app)/acao/_components/ActionStatusBar.tsx`
  (Onda 5 deixa count real)
- `backend/app/application/decisions/` (Onda 5 usa para criar
  Decision a partir de Suggestion aceita)

**ADRs a ler:**
- ADR-074 (Task aggregate)
- ADR-136 (Decision aggregate event-sourced) — base para Decision
  criada via accept
- ADR-151 (remoção do Modo Tático — fundamenta o /acao)
- ADR-152 (rota `/acao` com tabs — fundamenta onde Inbox vive)
- Direção E em geral: `~/.claude/plans/quero-repensar-as-interfaces-mellow-nova.md`

## Não fazer nesta sessão

- ❌ LLM-based suggestion generation (deixar para sessão futura
  `track_onda_5_llm_suggestions.md`)
- ❌ Migration `kanban_items` + `report_notes` (Onda 1, paralela)
- ❌ Tasks templates dinâmicos (v1 hard-coded)
- ❌ Acceptance flow para múltiplas sugestões em batch (v1 = uma de
  cada vez)
- ❌ Mexer em outras áreas do produto não relacionadas

## Smoke test humano antes do PR

1. Abrir `/reports/[id]` — confirmar callouts inline em S2/S7 com
   sugestões reais geradas pelo pipeline
2. Abrir `/acao?tab=inbox` — confirmar lista de sugestões pendentes
3. Aceitar uma sugestão → verificar que cria Decision em `/plano`
   com FK à origem visível
4. Descartar uma sugestão com motivo "Já considerei" → confirmar
   que sai da lista pendente e aparece em "Descartadas"
5. Re-rodar pipeline E5 → confirmar que sugestão idêntica descartada
   não ressuscita (dedup)
6. Abrir `/plano` — confirmar banner mostra contagem real

## Branch + commits

- Partir de `origin/main` pós-merge das Ondas 2/3/4/6
- Branch: `agent/onda-5-suggestion-aggregate/<yyyyMMdd-HHmm>`
- Commits sugeridos (1 por phase):
  1. `feat(suggestions): aggregate + endpoints (ADR-153)`
  2. `feat(pipeline): suggestion generator (E5)`
  3. `feat(frontend): SuggestionCallout + SuggestionCard + ligar /acao Inbox`
  4. `docs(adr): ADR-153 + CHANGELOG`
- PR único depois.
