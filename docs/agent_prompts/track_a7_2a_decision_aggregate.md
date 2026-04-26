# Track A7.2a — `Decision` aggregate (event-sourced) + migrator + tela Plano de Ação

> **Lane ID:** A7.2a
> **Branch prefix:** `agent/a7-2a-decision-aggregate/*`
> **Depende de:** A7.0 ✅ mergeada (precisa do tipo `DecisionsConfig` referenciado pelo Protocol — ou criar tipo aqui se não foi incluído em A7.0).
> **Paralelo com:** A7.1, A7.2b, A7.4.
> **Conflita com:** qualquer commit ativo em `backend/app/models/`, `backend/app/application/`, `backend/app/api/`, `frontend/src/components/report/sections/` (especialmente PlanoDeAcao).
> **Onda:** 2 (paralelizável).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.2a](../CONFIG_CUTOVER_PLAN.md#§52a-a72a--decision-aggregate-event-sourced)
> **ADR:** [ADR-136](../DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain) — **G1 obrigatório antes de codar**.
> **Supervisão CTO:** G1 (ADR) · G2 (schema) · G3 (PR pré-merge).

> **Objetivo (1 frase):** introduzir entidade `Decision` event-sourced com lifecycle (Pendente → Decidido → Executado), supersede chain, valor BRL; migrar conteúdo de `config/decisions.md` para o workspace piloto; expor tela "Plano de Ação" no relatório; **deletar `decisions.md`** (resolve dívida PII).

---

## Por que esta lane

`config/decisions.md` viola CLAUDE.md §Regras críticas — contém valores reais em BRL versionados em git. Modelagem como CRUD ingênuo perde audit trail e supersede chain. Event sourcing escopado a este aggregate (não convenção a propagar) resolve ambos.

---

## Regras inegociáveis

1. **Money em BIGINT cents** ([ADR-090](../DECISIONS.md)): `amount_brl_cents`. No wire, string decimal. Frontend renderiza via `<MonetaryValue/>`.
2. **`response_model` explícito** em todo endpoint ([ADR-109](../DECISIONS.md#adr-109--padrão-de-fastapi--testes-de-contrato)) + `make update-openapi-snapshot`.
3. **Routers finos** ([ADR-101](../DECISIONS.md#adr-101--routers-finos-use-cases-em-application)) — endpoints em `backend/app/api/decisions.py` apenas montam DTOs e chamam use cases em `backend/app/application/decisions/`.
4. **Stateless rigoroso** ([ADR-111](../DECISIONS.md)): zero estado in-memory; todas as queries via repository.
5. **Funções 4-20 linhas, módulos ≤500** (CLAUDE.md §Code style).
6. **Dados sensíveis** (CLAUDE.md): testes/fixtures usam valores fictícios (R$1.000, R$50.000) — **nunca** copiam valores reais do `decisions.md` original.
7. **Migrator é descartável** — não generalizar parser markdown→Decision para outros usos.

---

## Entregáveis (CONFIG_CUTOVER_PLAN.md §5.2a)

### Backend

1. **Models** (`backend/app/models/decision.py`):
   ```python
   class Decision(Base):
       __tablename__ = "decisions"
       id: Mapped[UUID]
       workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
       code: Mapped[str]
       title: Mapped[str]
       rationale: Mapped[str | None]
       amount_brl_cents: Mapped[int | None]
       status: Mapped[DecisionStatus]  # Enum
       supersedes_id: Mapped[UUID | None] = mapped_column(ForeignKey("decisions.id"))
       decided_at: Mapped[date | None]
       executed_at: Mapped[date | None]
       __table_args__ = (UniqueConstraint("workspace_id", "code"),)

   class DecisionEvent(Base):
       __tablename__ = "decision_events"
       id, decision_id, event_type, occurred_at, actor, payload (jsonb)
   ```

2. **Alembic migration** — `alembic upgrade head` cria as 2 tabelas + indexes (workspace_id, code; decision_id, occurred_at).

3. **Repository** (`backend/app/repositories/decision_repository.py`).

4. **Application layer** (`backend/app/application/decisions/`):
   - `commands/create_decision.py`, `update_decision.py`, `mark_executed.py`, `supersede_decision.py`.
   - `queries/list_decisions.py`, `get_decision.py`.
   - Eventos: `DecisionCreated`, `DecisionUpdated`, `DecisionExecuted`, `DecisionSuperseded`. Append-only em `decision_events`.

5. **API** (`backend/app/api/decisions.py`):
   - `GET    /api/v1/workspaces/{id}/decisions` → `list[DecisionResponse]`
   - `POST   /api/v1/workspaces/{id}/decisions` → `DecisionResponse`
   - `GET    /api/v1/workspaces/{id}/decisions/{decision_id}` → `DecisionResponse`
   - `PATCH  /api/v1/workspaces/{id}/decisions/{decision_id}` → `DecisionResponse`
   - `POST   /api/v1/workspaces/{id}/decisions/{decision_id}/execute` → `DecisionResponse`
   - Todos com `response_model` + DTOs em `backend/app/schemas/dto/decision/`.
   - OpenAPI snapshot atualizado: `make update-openapi-snapshot`.

### Frontend

6. **Componente** (`frontend/src/components/report/sections/PlanoDeAcao/`):
   - `PlanoDeAcaoSection.tsx` — tabela ordenada por `code`; colunas: code, title, valor (`<MonetaryValue/>`), status badge, supersede chip ("supersede D06" como link clicável), data decisão, data execução.
   - Filtro por status (toggle Pendente/Decidido/Executado/Todos).
   - CTA "Marcar como executada" via `POST /execute` quando status = Decidido.

7. **Hook** (`frontend/src/hooks/useDecisions.ts`):
   - `listDecisions`, `getDecision`, `createDecision`, `updateDecision`, `executeDecision`.
   - Cache via SWR/React Query (padrão do repo).

8. **Layout integration**:
   - Entrada nova no `config/report_layout.yaml` (até A7.5; depois entrega via DB):
     ```yaml
     - id: plano_de_acao
       title: Plano de Ação
       enabled: true
       component: PlanoDeAcaoSection
     ```
   - Roda `python3 dev/codegen_report_layout.py`.
   - `frontend/src/components/report/sections/index.ts` exporta `PlanoDeAcaoSection`.

### Migrator one-shot

9. **`dev/migrate_decisions_to_db.py`**:
   - CLI: `python dev/migrate_decisions_to_db.py --workspace-id <UUID> [--dry-run]`.
   - Lê `config/decisions.md`, parseia tabela markdown (linhas com `| Dxx |`).
   - Para cada item: cria `Decision` + emite `DecisionCreated` event.
   - Idempotente: se `code` já existe no workspace, **skipa com log** (não atualiza).
   - Mapeia status do markdown ("Pendente execução", "Decidido", "Pendente configuração") para enum `DecisionStatus`.
   - Mapeia supersede ("**Superseded por D15**") para `supersedes_id`.
   - **Não generaliza** — código fica em `dev/`, não em `backend/app/`.

### Limpeza

10. **`git rm config/decisions.md`** no commit final (após migrator validar no workspace piloto).

### Testes

11. ≥16 testes novos:
    - `backend/tests/test_decision_repository.py` — CRUD + supersede.
    - `backend/tests/test_decision_use_cases.py` — todos os use cases + emit eventos.
    - `backend/tests/test_decisions_api.py` — endpoints com client de teste.
    - `frontend/tests/components/PlanoDeAcaoSection.test.tsx` — render + interaction.
    - `frontend/tests/e2e/plano-de-acao.spec.ts` `@critical` — navega → listar → executar.

---

## Sequência de commits sugerida

```
1. feat(backend): Decision + DecisionEvent models + Alembic migration (A7.2a · ADR-136)
2. feat(backend): DecisionRepository + base use cases (A7.2a)
3. feat(backend): /v1/.../decisions endpoints + DTOs (A7.2a)
4. test(backend): decision use cases + repository + api (A7.2a) — ≥10 tests
5. feat(frontend): PlanoDeAcaoSection + useDecisions hook (A7.2a)
6. test(frontend): unit + e2e @critical Plano de Ação (A7.2a)
7. feat(report): plano_de_acao section in report_layout + codegen (A7.2a)
8. chore(dev): migrate_decisions_to_db.py one-shot migrator (A7.2a)
9. chore(config): rm config/decisions.md after pilot migration (A7.2a)
10. docs(a7): A7.2a ✅ + ADR-136 + CHANGELOG entry
```

---

## Gates de push

```bash
pre-commit run --all-files
pytest backend/tests -q                              # ≥1175 + novos
cd frontend && npm test -- --run                     # vitest verde
cd frontend && npm run test:e2e -- --grep @critical  # Playwright @critical
make update-openapi-snapshot && git diff --quiet -- backend/tests/openapi.snapshot.json  # snapshot atualizado
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.2a)

- [ ] Models + Alembic ✓
- [ ] Application layer com use cases append-only events ✓
- [ ] API endpoints com `response_model` + OpenAPI snapshot ✓
- [ ] Frontend tela Plano de Ação + hook ✓
- [ ] Migrator one-shot funcional + idempotente ✓
- [ ] `config/decisions.md` removido ✓
- [ ] ≥16 testes novos verdes ✓
- [ ] Smoke E2E verde com `decisions.md` ausente ✓
- [ ] CTO G1 (ADR-136) ✅ + G2 (schema) ✅ + G3 (PR review) ✅

---

## O que NÃO entrega

- Generalização do parser markdown→Decision para outras entidades.
- Cross-aggregate events (Decision → Notification etc) — fica para sprint posterior.
- Edição visual da supersede chain como árvore — UI é tabela linear; árvore vem se houver demanda.
- Execução automática de decisões (lógica financeira) — Decision é apenas registro editorial; pipeline não age sobre ela.

---

## Coordenação com outros agentes

- **Disjunto a A7.1** (que toca pipeline E3/E4/E5).
- **Disjunto a A7.2b** (que toca `pipeline/domain/services/{previdencia,cenarios}_*`).
- **Disjunto a A7.4** (docs metodologia).
- **Hotspot único:** `config/report_layout.yaml` (codegen). Anuncie no CHANGELOG `[Unreleased]` antes de tocar — evita conflito com lanes Report Premium.
- **Schema review (G2):** antes de gerar Alembic migration, peça revisão CTO. Schema event-sourced é caso isolado; CTO confirma que nomes/types fazem sentido antes do `alembic revision` ir para o branch.

---

## Rollback

- Revert do PR de cutover.
- Models + tabelas permanecem (Alembic não descomissiona automaticamente; nova migration vazia se quiser limpar).
- `decisions.md` recuperável via git history.

---

## Estimativa

~3–4 sessões de 2h (a maior da Onda 2). Frontend + backend + UI + migrator + testes.
