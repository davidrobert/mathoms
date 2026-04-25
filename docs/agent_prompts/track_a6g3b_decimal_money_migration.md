# Track A6g.3b — Migração completa `float` → `Decimal` em money DTOs + math

> **Lane ID:** A6g.3b
> **Branch prefix:** `agent/a6g3b-decimal-money/*`
> **Depende de:** A6g.6 ✅ (enforcement ativo — audit detecta P5) · A6g.3 ✅ parcial (slice 2b decomp já extraiu `_aporte_cobrindo_gap_com_patrimonio`)
> **Paralelo com:** A6e.4 (só se disciplinar escopo — **nunca tocar `backend/app/api/*.py` nem `backend/app/application/*`**); A6g.6b (ruff format pode tocar mesmos arquivos — coordenar sequencial)
> **Conflita com:** commits simultâneos em `backend/app/schemas/dto/goal/*.py`, `backend/app/services/goal_service.py`, `backend/app/services/pipeline_adapter.py`, `backend/app/schemas/transactions.py`, `backend/app/services/task_progress_service.py`, `backend/app/services/transaction_service.py`, `frontend/src/lib/api/goals.ts`
> **Onda:** 3+ (depois de A6g.6b ou em paralelo com disciplina)
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-090](../DECISIONS.md#adr-090--decimal-para-valores-monetários) · [CLAUDE.md §Dinheiro nunca é float](../../CLAUDE.md#dinheiro-nunca-é-float-adr-090) · [ADR-114 baseline](../DECISIONS.md#adr-114--enforcement-automatizado-de-code-style-gates-imediatos--progressivos-a6g6) · audit `dev/code_style_baseline.json` (categoria `P5_float_money`)

> **Objetivo:** eliminar a categoria `P5_float_money` em `backend/app/` (13
> ofensores em 2026-04-22) migrando money fields de `float` para `Decimal`
> no núcleo, com shim de wire-compat (JSON emite number). Compliance
> completo com ADR-090 sem quebrar frontend. Baseline A6g.6 decresce em
> P5 exata quantidade migrada.

---

## Por que esta lane agora

1. **Último débito ADR-090 visível** — A6g.3 rodada 1+2 limpou P1/P4/P8 em
   backend, mas P5 ficou deferido explicitamente porque migração exige
   cascade de `compute_if_derived` (math Decimal). Sem essa lane, gate
   de regressão da A6g.6 aceita P5=13 como novo "normal".
2. **Toda introdução de money via API pode escorregar** — sem tipo
   tipado `MoneyBRL`, qualquer PR novo copia `x: float = Field(...)` e
   passa audit só por não estar no baseline. Tipo formal força disciplina.
3. **F7B.5 (audit log + precision)** depende de values exatos — se
   entrarmos em produção com `float` money em 12 campos, bugs de
   arredondamento silenciosos vão aparecer quando usuários começarem
   a registrar números reais.
4. **A6c.3** planeja deletar bridge + `main(root_dir)` legacy; quando
   E5/E6 pipeline for reescrito, contrato HTTP com money já deve ser
   Decimal-compliant. Migrar agora evita retrabalho.

---

## Premissas inegociáveis

Do CLAUDE.md §Code style + ADR-090:

1. **Dinheiro nunca é `float`** (ADR-090). `Money.brl(...)` / `Decimal(str(v))`
   em Python. Wire: string decimal **OU** number via serializer customizado
   (este track adota number-via-serializer para não quebrar frontend).
2. **Tolerâncias, rates, percentuais NÃO são money.** Mantêm `float`.
   - `trs_pct`, `retorno_real_anual_pct`, `taxa_retirada_conservadora_pct`
     — são ANUAIS em %.
   - `saldo_diff`, `baseline_irpf_diff` — tolerâncias de reconciliação.
     (**Rename para `_tolerance` suffix** antes da migração principal OU
     skip por semantic comment — ver Slice 0.)
   - `cambio_brl_usd` — taxa de câmbio (rate), não money.
   - `horizonte_estimado_meses` — duração, não money.
3. **USD também é money** (ADR-090 não distingue moeda). `meta_usd` em
   `DolarGoalInputs` vira `MoneyUSD`. Opcionalmente tipo separado se
   precisar de tratamento distinto; por ora um único `MoneyBRL` com doc.
4. **Preserve comportamento numérico** — valores persistidos no DB
   (`params_json`, `derived_json`) ficam como number no JSON; Decimal é
   apenas representação in-memory. Testes de igualdade monetária usam
   `Decimal.compare` com tolerância `Decimal("0.01")` (já é o padrão em
   `test_goal_service.py`).
5. **Frontend codegen é manual** (`frontend/src/lib/api/goals.ts` é
   handwritten). Se mantivermos wire format JSON como `number`, frontend
   TS continua `number` sem edição.
6. **OpenAPI snapshot vai mudar** — request schemas ganham `anyOf
   [number, string]` por causa do Pydantic aceitar Decimal como input.
   Isso **não quebra** o frontend (ele só manda number) mas o diff do
   snapshot precisa ser aceito.

---

## Escopo exato — catalogado por arquivo

### Grupo A — tipo infraestrutural novo

| Arquivo | O que criar |
|---|---|
| `backend/app/schemas/money.py` **(novo)** | `MoneyBRL = Annotated[Decimal, BeforeValidator(_coerce_to_decimal), PlainSerializer(lambda v: float(v), return_type=float, when_used='json')]`. Idem `MoneyUSD`. Doc inline com exemplo + rationale. Exporta também `to_decimal_exact(v) -> Decimal` helper para call-sites que recebem `float` do legacy/DB. |

### Grupo B — DTOs migrados (13 campos)

| Arquivo | Campo atual | Semântica | Tipo novo |
|---|---|---|---|
| `backend/app/schemas/dto/goal/aporte.py:20` | `meta_aporte_mensal_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/aporte.py:29` | `distribuicao: dict[str, float]` | money BRL | `dict[str, MoneyBRL]` |
| `backend/app/schemas/dto/goal/aporte.py:49` | `aporte_anual_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/dolar.py:20` | `meta_usd: float` | money USD | `MoneyUSD` |
| `backend/app/schemas/dto/goal/dolar.py:23` | `aporte_mensal_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/if_goal.py:26` | `renda_passiva_mensal_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/if_goal.py:64` | `if_meta_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/if_goal.py:68` | `aporte_necessario_mensal_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/if_goal.py:76` | `if_meta_conservadora_brl: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/dto/goal/if_goal.py:80` | `aporte_mensal_com_patrimonio_atual_brl: Optional[float]` | money BRL | `Optional[MoneyBRL]` |
| `backend/app/schemas/dto/goal/if_goal.py:89` | `patrimonio_atual_utilizado_brl: Optional[float]` | money BRL | `Optional[MoneyBRL]` |
| `backend/app/schemas/dto/goal/if_goal.py:100` | `IFGoalComputeRequest.patrimonio_atual_brl: Optional[float]` | money BRL | `Optional[MoneyBRL]` |
| `backend/app/schemas/dto/goal/if_goal.py:118` | `faltante_brl: Optional[float]` | money BRL | `Optional[MoneyBRL]` |
| `backend/app/schemas/transactions.py:12` | `valor: float` | money BRL (ou USD — campo `moeda` indica) | `MoneyBRL` (simplificar — maioria BRL; documentar exceção USD) |
| `backend/app/schemas/transactions.py:24` | `total_receitas: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/transactions.py:25` | `total_despesas: float` | money BRL | `MoneyBRL` |
| `backend/app/schemas/transactions.py:26` | `saldo: float` | money BRL | `MoneyBRL` |

**Não migrar (mantêm `float`, não são money):**
- `trs_pct`, `retorno_real_anual_pct`, `taxa_retirada_conservadora_pct` — percentuais anuais
- `cambio_brl_usd` — taxa de câmbio (rate)
- `horizonte_estimado_meses` — duração
- `percentual_conquistado` — porcentagem
- `distribuicao_pct` em `AporteGoalDerived` — porcentagem
- Tolerâncias em `config_blob/response.py` (`saldo_diff`, `baseline_irpf_diff`, `score_diff_max`, `patrimonio_composicao_diff_pct_max`, `cv_*_diff_max`, `qa_unidentified_target_pct`) — tolerâncias/pct

### Grupo C — math em services migrado

| Arquivo | Função | Mudança |
|---|---|---|
| `backend/app/services/goal_service.py` | `_pmt_constante_ate_fv(fv_alvo, n_meses, retorno_mensal)` | Assinatura vira `(fv_alvo: Decimal, n_meses: int, retorno_mensal: Decimal) -> Decimal`. Implementação usa `Decimal('1')`, `Decimal(str(n_meses))`. Cuidado: `(1 + r) ** n` em Decimal exige `.quantize` para não explodir precisão. Padrão: `Decimal('0.00000001')` para intermediários, `Decimal('0.01')` no return. |
| `backend/app/services/goal_service.py` | `_if_meta_targets(inputs)` | Retorna `tuple[Decimal, Decimal]`. Conversão interna: `renda_mensal * Decimal('12') / (Decimal(str(inputs.trs_pct)) / Decimal('100'))`. |
| `backend/app/services/goal_service.py` | `_aporte_cobrindo_gap_com_patrimonio(if_meta, n_meses, retorno_mensal, patrimonio_atual_brl)` | Todas Decimal. Caller converte na entrada. |
| `backend/app/services/goal_service.py` | `compute_if_derived(inputs, patrimonio_atual_brl)` | `patrimonio_atual_brl: Optional[Decimal]`. Retorna IFGoalDerived com Decimal. |
| `backend/app/services/goal_service.py` | `compute_aporte_derived(inputs)` | `inputs.meta_aporte_mensal_brl` já Decimal → `anual = meta * Decimal('12')`. `distribuicao_pct` permanece float (% não é money). |
| `backend/app/services/goal_service.py` | `compute_dolar_derived(inputs, cambio_brl_usd)` | `aporte_mensal_brl` Decimal, `cambio_brl_usd` float (rate). `aporte_usd_mensal = aporte_mensal_brl / Decimal(str(cambio))`. `horizonte_estimado_meses` permanece float (duração). |
| `backend/app/services/goal_service.py` | `get_latest_report_patrimonio_liquido(workspace_id, db)` | Retorna `Optional[Decimal]` ao invés de `Optional[float]`. Callers em `backend/app/api/goals.py` convertem quando passam para `compute_if_derived`. |
| `backend/app/services/task_progress_service.py` | `_match_transactions_by_keyword(...)` | `executed` inicializa `Decimal('0')`. `executed += abs(tx.valor)` com Decimal. Retorno: `tuple[Decimal, int, set[str]]`. |
| `backend/app/services/task_progress_service.py` | `compute_progress(...)` | Após slice 2c, recebe `(executed: Decimal, ...)`. `TaskProgress.executed_brl: Optional[MoneyBRL]`; `target_brl: Optional[MoneyBRL]`. Converter `_parse_brl_target` retorno de `float` para `Decimal`. |
| `backend/app/services/transaction_service.py` | `load_transactions(tenant_root)` | `TransactionItem(valor=Decimal(str(tx.get("valor", 0))))` ao invés de `float(...)`. |
| `backend/app/services/transaction_service.py` | `filter + summary` | Aritmética com Decimal. `value_min`/`value_max` recebidos como float → converter `Decimal(str(v))`. `sum(t.valor)` funciona com Decimal. |

### Grupo D — serialização legacy pipeline

| Arquivo | Como preservar | Nota |
|---|---|---|
| `backend/app/services/pipeline_adapter.py::_serialize_if_goal(goal)` | `goal.derived_json` vem do DB como dict com number; JSON produzido **já** é wire-compat. Não precisa mudar. Apenas confirmar que `goal.derived_json["if_meta_brl"]` continua JSON-serializável (Decimal → number pelo adapter JSON). |
| `backend/app/services/pipeline_adapter.py::_serialize_aporte_goal`, `_serialize_dolarizacao_goal` | Idem. |
| `backend/app/schemas/dto/goal/mapper.py::goal_to_typed_response` | Recebe `Goal.params_json`/`derived_json` como dict; constrói DTO Pydantic. Pydantic valida `MoneyBRL` e aceita number (input schema permite). |
| **`params_json` / `derived_json` persistidos** | **Sem migração de schema** — valores permanecem number no DB (JSON column). Decimal in-memory, number on disk. |

### Grupo E — audit + gate

| Arquivo | Mudança |
|---|---|
| `dev/code_style_baseline.json` | Regenerar pós-migração; P5 cai de 13 → 0 no escopo `backend/app/schemas/` + `goal_service.py`. |
| `backend/tests/architecture/test_no_any_in_boundary.py` | Não afeta — `Any` em annotations, ortogonal. |
| `dev/check_float_money.py` | Não afeta — hook só bloqueia NOVO; código migrado some. |

---

## Ordem de execução — 6 slices

### Slice 0 — Prep (cleanup de false positives) [~15 min]

**Objetivo:** eliminar P5 que NÃO são money (rename + helper param).

1. `backend/app/schemas/dto/config_blob/response.py::saldo_diff` → rename
   para `saldo_diff_tolerance` (documenta `# Tolerância de reconciliação,
   não money (ADR-090 não se aplica)`). Buscar callers:
   - `scripts/e3*.py`?
   - `pipeline/domain/services/reconciliation_service.py`?
   - `config/pipeline.json` schema?
   Atualizar todos. Preservar paridade com `pipeline.json` — se o campo
   é persistido com esse nome, **não** renomear; adicionar skip no audit
   via `dev/_audit_cs_internals/detectors_py.py` lista `_TOLERANCE_NAMES
   = {"saldo_diff", "baseline_irpf_diff"}` (preferível: NÃO mexer em
   audit; aceitar P5=1 documentado).

2. `backend/app/services/goal_service.py::_aporte_cobrindo_gap_com_patrimonio`
   param `patrimonio_atual_brl` — será migrado em slice 2 (para
   Decimal). Aqui não muda nada.

**Gate:** `pytest backend/tests -q` verde. Audit P5 cai 13 → 12 (só
o rename de `saldo_diff` conta, se aplicado) ou fica em 13 (se aceitar
tolerance-as-float).

**Commit 0:** `refactor(config): rename saldo_diff_tolerance (A6g.3b slice 0 · ADR-090 false positive)`

### Slice 1 — Tipo `MoneyBRL` + `MoneyUSD` [~30 min]

**Objetivo:** criar tipo de infraestrutura + testes.

1. Criar `backend/app/schemas/money.py`:
   ```python
   """Money types — Decimal in-memory, number on wire (ADR-090, A6g.3b)."""
   from decimal import Decimal
   from typing import Annotated
   from pydantic import BeforeValidator, PlainSerializer

   def _coerce_to_decimal(v):
       if isinstance(v, Decimal):
           return v
       if isinstance(v, (int, float, str)):
           return Decimal(str(v))
       raise TypeError(f"cannot coerce {type(v).__name__} to Decimal")

   MoneyBRL = Annotated[
       Decimal,
       BeforeValidator(_coerce_to_decimal),
       PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
   ]
   MoneyUSD = Annotated[
       Decimal,
       BeforeValidator(_coerce_to_decimal),
       PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
   ]
   ```
2. Criar `backend/tests/test_money_type.py` com testes:
   - Accept int/float/str/Decimal on input
   - Emit number on JSON output
   - Precision roundtrip: `Decimal("1234.567890")` serializa como
     `1234.567890` (float) — documentar limitação inerente.
   - Python `.model_dump()` mantém Decimal.

**Gate:** `pytest backend/tests/test_money_type.py -q` verde. Pre-commit
ok (ruff + hooks). Nenhuma mudança em DTOs ainda.

**Commit 1:** `feat(schemas): MoneyBRL/MoneyUSD type (A6g.3b slice 1 · ADR-090)`

### Slice 2 — Goal DTOs + `goal_service` math [~1h]

**Objetivo:** migrar os 11 campos de goal DTOs + reescrever math em Decimal.

1. Substituir `float` por `MoneyBRL`/`MoneyUSD` em:
   - `backend/app/schemas/dto/goal/aporte.py` (2 money + 1 dict[str, MoneyBRL])
   - `backend/app/schemas/dto/goal/dolar.py` (1 USD + 1 BRL)
   - `backend/app/schemas/dto/goal/if_goal.py` (7 campos, contando
     Inputs + Derived + ComputeRequest/Response)
2. Atualizar `goal_service.py`:
   - `_pmt_constante_ate_fv(fv_alvo: Decimal, n_meses: int, retorno_mensal: Decimal) -> Decimal`.
     Operações: `Decimal('1') + retorno_mensal`, `** n_meses` via
     exponentiation Python (Decimal suporta `__pow__` com int), `.quantize`
     no return.
   - `_if_meta_targets(inputs)` retorna `tuple[Decimal, Decimal]`. Conversões:
     `Decimal(str(inputs.trs_pct))` (pct é float).
   - `_aporte_cobrindo_gap_com_patrimonio` tudo Decimal.
   - `compute_if_derived(inputs, patrimonio_atual_brl: Optional[Decimal])`
     — caller converte antes; retorna `IFGoalDerived` com Decimals
     (Pydantic aceita e serializa).
   - `compute_aporte_derived(inputs)`: `anual = inputs.meta_aporte_mensal_brl
     * Decimal('12')`. Zero cambio.
   - `compute_dolar_derived(inputs, cambio_brl_usd)`: `meses =
     inputs.meta_usd * Decimal(str(cambio_brl_usd)) / inputs.aporte_mensal_brl`.
     `horizonte_estimado_meses` é **duração** (Decimal dividido → converte
     float).
   - `get_latest_report_patrimonio_liquido` retorna `Optional[Decimal]`.
3. Atualizar callers em `backend/app/api/goals.py`:
   - Where it receives `patrimonio_atual_brl: float | None` from query
     param and passes to `compute_if_derived`, convert via `Decimal(str(v))`
     at the boundary.
   - Onde monta `IFGoalComputeResponse(percentual_conquistado=...,
     faltante_brl=...)`, todos os valores podem vir como Decimal (Pydantic
     serializa como number).

**Gate:**
- `pytest backend/tests/test_goal_service.py -q` — 23 tests devem
  continuar verdes. Assertions usam `Decimal` nos valores esperados;
  comparações precisam `Decimal.__eq__` ou `.compare_total` — se teste
  hoje faz `assert derived.if_meta_brl == 7200000.0`, converter teste
  para `Decimal("7200000.00")` OU `float(derived.if_meta_brl) == 7200000.0`.
- `pytest backend/tests/test_goals_api.py -q` — E2E com FastAPI test
  client, wire format JSON deve continuar number.
- `pytest backend/tests/architecture/test_no_any_in_boundary.py -q`
  — não afeta.
- OpenAPI snapshot: `make update-openapi-snapshot` → diff em request
  schemas (anyOf [number, string] substitui number). Commitar snapshot
  junto do commit.

**Commit 2:** `refactor(goals): Decimal money em DTOs + goal_service math (A6g.3b slice 2 · ADR-090)`

### Slice 3 — Transactions DTOs + services [~45 min]

**Objetivo:** migrar os 4 campos de `transactions.py` + todos os callers
(`transaction_service.py`, `task_progress_service.py`, `api/transactions.py`).

1. `backend/app/schemas/transactions.py`:
   - `TransactionItem.valor: MoneyBRL` (nota: pode ser USD, mas maioria
     BRL; `.moeda` field já existe — documentar no docstring).
   - `TransactionSummary.total_receitas/total_despesas/saldo: MoneyBRL`.
2. `backend/app/services/transaction_service.py::load_transactions`:
   - Construtor: `TransactionItem(valor=Decimal(str(tx.get("valor", 0))))`.
   - `filter` com `value_min/value_max`: converter para Decimal na entrada
     (`value_min_d = Decimal(str(value_min)) if value_min is not None else None`).
   - `summary`: `sum(t.valor for t in ...)` — funciona nativamente em
     Decimal.
3. `backend/app/services/task_progress_service.py`:
   - `_match_transactions_by_keyword`: `executed = Decimal('0')`,
     `executed += abs(tx.valor)`, retorna Decimal.
   - `compute_progress`: `target` do `_parse_brl_target` precisa virar
     Decimal também (alterar assinatura do `_parse_brl_target` +
     `_raw_to_float` para retornar Decimal — rename `_raw_to_decimal`).
     `percent_executed` fica float (é porcentagem).
4. `backend/app/api/transactions.py::143`: `tx.valor` já usado — confirmar
   que destination field aceita Decimal ou faz conversão.

**Gate:**
- `pytest backend/tests -q -k "transaction or task_progress"` — todos
  verdes.
- Se existir `test_tasks_api.py`/`test_transactions_api.py`, rodar.
- OpenAPI snapshot atualizado se transactions está exposto.

**Commit 3:** `refactor(transactions): Decimal money em TransactionItem + task_progress (A6g.3b slice 3 · ADR-090)`

### Slice 4 — OpenAPI snapshot + frontend sanity [~20 min]

**Objetivo:** regenerar snapshot e verificar frontend manual.

1. `make update-openapi-snapshot` — revisar diff linha a linha. Esperado:
   - Request schemas: `anyOf [number, string]` em endpoints que recebem
     money como body.
   - Response schemas: continuam `type: number`.
   - Title/description inalterados.
2. Frontend:
   - `frontend/src/lib/api/goals.ts` — typings manuais. Confirmar que
     `number` no TS continua válido (backend sempre serializa number).
     Nenhuma edição necessária se wire OK.
   - `cd frontend && npm run lint` verde.
   - `cd frontend && npm test -- --run` — vitest verde.
3. Opcional: E2E `@critical` em goal flows (`plano/meta-if`,
   `plano/aportes`) — roda apenas se tiver ambiente configurado.
4. Smoke manual (dogfood): criar Goal IF via UI, compute derived, salvar,
   reler — comparar valores com fórmula mental.

**Gate:** OpenAPI snapshot aceito + frontend unit green.

**Commit 4:** `docs(api): openapi snapshot pós-Decimal money (A6g.3b slice 4)`

### Slice 5 — Audit regression + docs + CHANGELOG/BACKLOG [~15 min]

**Objetivo:** fechar a lane.

1. `python dev/check_code_style_regression.py --save-baseline` — baseline
   regenerada com P5 = X (esperado 0 em `backend/app/`, 1 se aceitar
   tolerance-as-float).
2. `docs/CHANGELOG.md [Unreleased]`: entry "A6g.3b — migração completa
   Decimal money" com resumo de slices.
3. `docs/BACKLOG.md`: linha A6g.3b ☐ → ✅ + data; lanes abertas atualiza
   restante do A6g.
4. `docs/DECISIONS.md`: ADR-090 ganha nota "A6g.3b ✅ 2026-MM-DD — MoneyBRL
   type introduzido; 11 campos goal + 4 transactions migrados".

**Commit 5 (docs hotspot, atomic ≤5min):** `docs(a6g.3b): ADR-090 fecha com MoneyBRL + CHANGELOG + BACKLOG`

### Slice 6 — Push + CI verify

```bash
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -gt 0 ] && git rebase origin/main && pytest backend/tests -q
git push origin HEAD:main
```

CI fica 10-15min. Confirmar all-green; ESLint + Ruff + backend + pipeline
+ audit regression todos verdes.

---

## Critérios de aceite (binários)

- [ ] `backend/app/schemas/money.py` existe com `MoneyBRL` + `MoneyUSD`.
- [ ] 13 campos money migrados (7 goal + 4 transactions + 2 helpers).
  Audit P5 em `backend/app/` cai para 0 (ou 1 se tolerance aceito).
- [ ] `test_money_type.py` novo com ≥5 casos (input types, JSON output,
  python output, roundtrip precision nota).
- [ ] `pytest backend/tests -q` — 1150+ passed, zero regressão.
- [ ] `pytest tests -q` — 1461 passed (não deveria tocar).
- [ ] `dev/check_code_style_regression.py` verde.
- [ ] OpenAPI snapshot diff revisado + aceito; `make update-openapi-snapshot`
  rodado.
- [ ] `cd frontend && npm run lint && npm test -- --run` verde.
- [ ] Frontend E2E @critical (se ambiente disponível) — goal creation
  + read flows verdes.
- [ ] CHANGELOG + BACKLOG + DECISIONS atualizados.
- [ ] CI all-green em `main`.

---

## Rollback criteria — ABORTE se

- `test_goal_service.py` tem ≥3 testes vermelhos pós-migração que exigem
  ajuste extensivo de assertion — sinal de que precisão Decimal mudou
  valores em casas decimais onde o teste compara igualdade exata. Nesse
  caso: primeiro commit que muda DTO, reverter, refatorar teste para
  usar tolerância `Decimal("0.01")`, então retomar.
- OpenAPI snapshot diff >200 linhas — sinal de que schemas não-esperados
  estão mudando. Investigar; possivelmente `MoneyBRL` precisa override de
  `json_schema_input_type` para forçar `type: number` no input.
- Frontend `npm run lint` quebra em tipos gerados — sinal de que TS
  codegen picou mudança. Verificar `frontend/src/generated/`.
- E2E @critical falha em goal creation — sinal de que endpoint aceita
  payload que o frontend manda mas valor salvo fica 0/null. Precision
  bug. Debug no compute layer.
- Backend tests regridi em 2+ tests não relacionados a goals/transactions
  — cuidado: pode haver código em outro aggregate que acessa
  `Goal.params_json["inputs"]["renda_passiva_mensal_brl"]` como float.

Em rollback: `git reset --hard origin/main`; anunciar qual slice quebrou
+ diff dos ofensores; abrir issue com repro.

---

## Anti-patterns a evitar

- **Migrar tudo em um commit gigante.** Cada slice deve ser atômico,
  com teste verde e diff revisável. Se precisa de rebase, rebase é
  linha por linha.
- **Usar `float()` em todo call-site do Decimal.** Isso anula o ganho
  de precisão. Preserve Decimal até o boundary JSON (Pydantic serializer
  faz a conversão uma única vez).
- **Mudar `trs_pct` para Decimal.** Não é money, é percentual. Se o
  audit reclamar, isso é bug do audit — tolerâncias e percentuais são
  legitimamente float.
- **Alterar schemas JSON (params_json/derived_json) no DB para string.**
  Quebra compat com pipeline legacy e migration path; valores na coluna
  JSON devem continuar number.
- **Promover `meta_usd` para tipo separado se não precisar.** Um tipo
  `MoneyUSD` idêntico a `MoneyBRL` na implementação é só doc + label
  semântico. Útil para clareza mas não muda serialização.
- **Quebrar `@patch` em tests de pipeline** que mockam
  `pipeline.llm.service.LLMService.call` — ortogonal a esta lane (a
  renomeação foi A6g.2c).
- **Esquecer `make update-openapi-snapshot`.** CI irá quebrar em
  `test_openapi_snapshot.py`.

---

## Coordenação com outros agentes

| Lane | Status | Overlap |
|---|---|---|
| **A6e.4** thin routers | 🚧 ativo | **Zero overlap direto** — A6e.4 toca `backend/app/api/*.py`. Esta lane toca `backend/app/schemas/` + `backend/app/services/`. Cuidado só com `api/goals.py` que talvez A6e.4 mexa em paralelo — anunciar no CHANGELOG. |
| **A6g.3** backend sweep r3 | ☐ pendente | **Overlap real** em `goal_service.py` (slice 2 dessa lane) — coordenar: ou faz A6g.3 r3 primeiro OU A6g.3b antes. Recomendação: A6g.3b primeiro (escopo bounded), A6g.3 r3 foca em `content_classifier`/`pipeline_service`/`models/task.py`. |
| **A6g.6b** ruff format | ☐ destravada | **Overlap de reformat** — se A6g.6b rodar antes, meu diff fica "em cima" da formatação nova (bom). Se depois, rebase meu diff contra formatação nova (revisar). |
| **A6e.3c** tipar DTOs | ✅ mergeado | Não afeta — A6e.3c foi `Dict[str, Any]`, esta é `float → Decimal`. Arquivos diferentes. |

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/schemas/dto/goal/ \
  backend/app/services/goal_service.py \
  backend/app/services/pipeline_adapter.py \
  backend/app/schemas/transactions.py \
  frontend/src/lib/api/goals.ts \
  docs/CHANGELOG.md docs/BACKLOG.md docs/DECISIONS.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no
**mesmo turno** (≤5min).

**Sync periódico (sessão >2h — essa pode ser assim):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# Se A6e.4 slice tocou api/goals.py, rebase imediato e re-run test_goal_*.
```

---

## O que esta lane NÃO entrega

- **Migração de todos os outros floats em backend** — só money. `trs_pct`,
  `cambio_brl_usd`, `horizonte_anos`, `taxa_*_pct`, `score_diff_max`,
  `confidence`, `percent_*` permanecem float por design.
- **Migração do pipeline `pipeline/` para Decimal** — escopo é `backend/
  app/` apenas. Pipeline legacy (e3_reconcile, e4_unified, e5_analyze)
  continua float. Migração dele viria em A6c/F7 phase com refactor maior.
- **Alteração do schema DB (coluna JSON)** — values no `params_json`/
  `derived_json` ficam number. Migração de DB é zero.
- **Tipo `MoneyAgregado`** (tuple de Decimal + moeda) — por ora
  `MoneyBRL`/`MoneyUSD` como tipos separados; união com currency code
  é over-engineering sem caso de uso claro.
- **Garantia de precisão 100% byte-compat vs código atual** — float →
  Decimal pode mudar último dígito em arredondamentos compostos. Testes
  que comparam exato podem precisar tolerância `Decimal("0.01")`.

---

## Referências

- [ADR-090](../DECISIONS.md#adr-090--decimal-para-valores-monetários) — Dinheiro nunca é `float` (regra original)
- [ADR-114](../DECISIONS.md#adr-114--enforcement-automatizado-de-code-style-gates-imediatos--progressivos-a6g6) — Enforcement automatizado de code style (A6g.6)
- [CLAUDE.md §Tipos](../../CLAUDE.md#tipos) — invariante de money
- [CLAUDE.md §Dinheiro](../../CLAUDE.md#dinheiro-nunca-é-float-adr-090)
- [track_a6g3_backend_style_sweep.md](track_a6g3_backend_style_sweep.md) — A6g.3 pai; P5 foi deferido dele
- [track_a6g6_enforcement.md](track_a6g6_enforcement.md) — gate que detecta P5
- **Pydantic v2 docs:** [Annotated types](https://docs.pydantic.dev/2.0/usage/types/types/#using-annotated-to-declare-validators-and-metadata), [PlainSerializer](https://docs.pydantic.dev/2.0/usage/types/custom/)
- **Python Decimal:** [`decimal.Decimal`](https://docs.python.org/3/library/decimal.html) — aritmética exata para money
