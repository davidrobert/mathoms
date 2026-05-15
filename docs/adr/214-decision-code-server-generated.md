---
id: ADR-214
type: adr
title: "`Decision.code` é server-generated com `pg_advisory_xact_lock`"
status: Decidido
phase: "A12.decision-code-autogen"
date: "2026-05-15"
relates_to:
  - "[[ADR-136]]"
  - "[[ADR-111]]"
  - "[[ADR-089]]"
  - "[[ADR-097]]"
  - "[[ADR-109]]"
supersedes: []
superseded_by: []
aliases: ["ADR 214", "decision-code-server-generated"]
tags:
  - area/backend
  - area/multitenancy
  - phase/a12
  - status/decidido
  - type/adr
  - breaking/api
---

## Contexto

[[ADR-136]] estabeleceu `Decision` aggregate event-sourced com `code`
(`D01..D{1,3}`) **único por workspace** (`UNIQUE (workspace_id, code)`),
**imutável após criação**, e **legível editorial** (referenciado em
narrativa do plano e supersedure chain: "D01 substituída por D03"). A
ADR não decidiu **quem gera o code** — frontend assumiu por default
tácito: [`InboxTab.tsx:165`](../../frontend/src/app/(app)/acao/_components/InboxTab.tsx)
calcula `D{max+1}` a partir da lista local de decisões carregadas e
envia no body do POST como `decision_code` (`AcceptSuggestionCommand`,
`ModifySuggestionCommand`, `DecisionCreateCommand`).

Três problemas observados em produção:

1. **Race condition real.** Duas abas/agentes aceitando sugestões em
   paralelo no mesmo workspace calculam o mesmo "próximo `D{N}`"; o
   segundo `INSERT` bate em `UNIQUE (workspace_id, code)` e estoura
   `IntegrityError` para o usuário. Não há lock entre o cálculo (client)
   e a persistência (server).
2. **Vazamento de implementação na UX.** Modal "Aceitar sugestão"
   ([`SuggestionDialogs.tsx:45-118`](../../frontend/src/app/(app)/acao/_components/SuggestionDialogs.tsx))
   expõe input editorial `"Código da decisão"` com `autoFocus` — rouba
   o protagonismo do CTA primário. Form manual de criação
   ([`DecisionFormDialog.tsx:262-271`](../../frontend/src/app/(app)/plano/_components/DecisionFormDialog.tsx))
   coloca `code` como primeiro campo, invertendo o fluxo cognitivo
   (conteúdo → identificador, não o contrário). Revisão `product-designer`
   (sessão 2026-05-15) recomenda remoção em ambos os modais.
3. **Quebra de padrão do produto.** Mathoms nunca expõe identificadores
   gerenciados pelo sistema em form de criação — `workspace.slug` só é
   editável em settings após criação; categoria `code` vem do catalog
   global ([[ADR-137]]). Permitir edição no momento da criação contradiz
   esse princípio.

## Decisão

**`code` é gerado server-side dentro da transação do INSERT, com
`pg_advisory_xact_lock` per-workspace.** Cliente não envia mais
`decision_code` em nenhum dos três commands; valor retorna no response
para que a UI possa exibi-lo em toast pós-criação.

### Estratégia de lock — Opção A (`pg_advisory_xact_lock`)

```sql
SELECT pg_advisory_xact_lock(
  hashtextextended('decision_code:' || workspace_id::text, 0)
);
SELECT COALESCE(MAX(CAST(substring(code FROM 2) AS INTEGER)), 0) + 1
FROM decisions
WHERE workspace_id = $1 AND code ~ '^D\d+$';
-- INSERT ... segue na mesma transação
```

Lock é **por chave semântica** (`'decision_code:' + workspace_id`), não
pela row de `workspaces` — evita contenção com escritas de settings/outras
operações no workspace. Escopo automático de transação (libera em
commit/rollback), zero gestão manual de release — aderente a
[[ADR-111]] §"sem estado mutável fora do DB".

### Defesa em profundidade — CHECK constraint

Migration adiciona:

```sql
ALTER TABLE decisions
  ADD CONSTRAINT chk_decisions_code_canonical
  CHECK (code ~ '^D\d+$') NOT VALID;
ALTER TABLE decisions VALIDATE CONSTRAINT chk_decisions_code_canonical;
```

(`NOT VALID` + `VALIDATE` separados são online-safe.) Formaliza a
convenção implícita que a query de `MAX` depende; impede regressão
futura (alguém inserindo `code='M01'` ou `code='X-2026-001'`).

### Localização da lógica — Repository

`DecisionRepositoryProtocol.next_code(workspace_id) -> str` retorna o
próximo code (já formatado `D{N}`). Geração é DB-aware por natureza
(precisa do lock + scan da tabela) — não cabe no aggregate (`Decision`
deve ser puro, sem conhecer advisory locks). Use case orquestra:

```python
async def create_decision(cmd, repo, ...):
    code = await repo.next_code(cmd.workspace_id)
    decision = Decision(code=code, title=cmd.title, ...)
    await repo.add(decision)
```

Tudo na mesma transação. `FakeDecisionRepository` (testes) implementa
`next_code` com `max + 1` sobre dict interno — determinístico, sem DB.

### DTOs — breaking change

`decision_code` removido de:
- `AcceptSuggestionCommand` ([`backend/app/schemas/dto/suggestion/command.py`](../../backend/app/schemas/dto/suggestion/command.py))
- `ModifySuggestionCommand` (idem)
- `DecisionCreateCommand` ([`backend/app/schemas/dto/decision/command.py`](../../backend/app/schemas/dto/decision/command.py))

DTOs já têm `model_config = ConfigDict(extra="forbid")` — enviar campo
removido gera 422. Snapshot OpenAPI atualizado no mesmo PR
(`make update-openapi-snapshot`, [[ADR-109]]).

`SuggestionResponse` ganha campo **additive**:

```python
class SuggestionResponse(BaseModel):
    ...
    accepted_decision_code: str | None = None  # populado quando status=Aceita
```

Frontend usa para toast pós-aceite: `"Decisão D03 criada — abrir no plano"`.

### Use case interno mantém parâmetro `code` opcional

Boundary do contrato server-side é o **endpoint HTTP**, não a application
layer ([[ADR-101]] R12/R13). `create_decision` use case aceita
`code: str | None = None` — se `None`, chama `repo.next_code`; se
informado (importer/migrator one-shot), respeita. Não força "server
sempre gera" no use case interno.

### Gap em codes — aceitável

Rollback de transação após reservar code via lock + `MAX` consome o
número mas não comita o INSERT → sequência fica com gap (`D01, D02, D04`).
**Aceito.** Code é editorial, não contábil — usuário não conta. Tentar
garantir sequência sem gap exige row-lock estendido ou pool de reciclados;
custo > benefício. Documentar invariante: "code é monotonic mas pode ter
gaps por rollback ou delete".

## Alternativas consideradas

- **(B) Tabela `workspace_counters (workspace_id, counter_name, next_value)`
  + `INSERT ... ON CONFLICT ... UPDATE ... RETURNING`.** Atômico,
  generalizável para futuros aggregates (Reports `R01`, Goals etc.),
  observável (`\d workspace_counters` em prod). Descartada por **YAGNI**
  — não há outro aggregate com code sequencial editorial hoje. Se
  Reports/Goals/outros aggregates ganharem essa convenção, **evolui-se
  para B** (migration: backfill counter table a partir do `MAX` atual).
  Trade-off documentado: parse `substring + cast` da Opção A funciona em
  N < 10k decisões/workspace; o `CHECK` constraint elimina o risco de
  regressão por dado inválido.

- **(C) `SELECT MAX + 1` otimista, sem lock, com retry em `IntegrityError`.**
  Loop pode degenerar em concorrência alta; suja semântica do use case
  com exceção esperada. Descartada.

- **(D) Sequence Postgres global (`decision_code_seq`).** Quebra "único
  por workspace" — exige mapping per-workspace que reproduz Opção B com
  semântica menos explícita. Descartada.

## Consequências

**Positivas:**

- ✅ Race condition eliminada por construção (lock per-workspace + tx
  serializada).
- ✅ UX limpa: modal de aceite foca no conteúdo da sugestão; toast
  pós-criação educa sobre o code (`"Decisão D03 criada"`) no momento
  certo, com contexto.
- ✅ Frontend simplificado: `computeNextDecisionCode` deletado, prop
  drilling de `nextDecisionCode` removido, 3 inputs deletados.
- ✅ Consistência com resto do produto (identificadores gerenciados
  pelo sistema não aparecem em form de criação).
- ✅ `CHECK (code ~ '^D\d+$')` formaliza convenção no schema, não só
  no código.

**Negativas:**

- ⚠️ Breaking change na API (snapshot OpenAPI muda). Mitigação: único
  consumer formal é o frontend Next.js (regenerado no mesmo PR via
  codegen). Sem cliente externo público hoje ([[ADR-109]] governa auth
  portability, não estabilidade de DTOs).
- ⚠️ Gap em codes possível (rollback, delete). Aceito por design — code
  é editorial.
- ⚠️ Parse `substring + cast` da Opção A é menos elegante que counter
  table. Aceito porque (a) `CHECK` constraint trava regressão, (b)
  YAGNI para outro aggregate, (c) custo de migração futura para B é
  baixo se a necessidade aparecer.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Lock advisory contende em batch (agente IA aceita 5 sugestões) | Carga típica é serializável em ~5-25ms total; aceitável. Telemetria de `mathoms.decisions.next_code_lock_wait_ms` no use case revela contenção real. |
| `CHECK` constraint quebra rows legadas | `NOT VALID` + audit pré-merge (`SELECT workspace_id, code FROM decisions WHERE code !~ '^D\d+$'`). Se aparecer, decisão case-a-case antes de `VALIDATE`. |
| Compat reverso quebra cliente externo | Não há cliente externo. Frontend único, regenerado no mesmo PR. |
| Use case interno (importer) precisa passar code custom | `create_decision(code=None)` respeita parâmetro quando informado; migrator one-shot continua funcionando. |

## Gates

- **Teste de concorrência:** `test_concurrent_decision_creation_no_code_collision`
  em [`backend/tests/integration/test_multi_worker_concurrency.py`](../../backend/tests/integration/test_multi_worker_concurrency.py) —
  5-10 tasks paralelas chamando `create_decision` no mesmo workspace →
  codes únicos + sequenciais + sem `IntegrityError`. Gate empírico
  [[ADR-111]] §"stateless rigoroso".
- **CHECK constraint:** migration up/down/up testada local; audit
  pré-`VALIDATE` registrado no PR description.
- **Snapshot OpenAPI:** diff esperado é remoção de `decision_code` em 2
  schemas (`AcceptSuggestionCommand`, `ModifySuggestionCommand`) + adição
  de `accepted_decision_code` em `SuggestionResponse`. `DecisionCreateCommand`
  perde `code` se decidirmos não permitir POST direto com code custom
  (TBD na lane operacional).
- **Frontend regenerado** (`frontend/src/generated/`) e build verde no
  mesmo PR.

## Referências

- [[ADR-136]] — `Decision` aggregate event-sourced (invariantes preservados)
- [[ADR-111]] — stateless rigoroso (advisory lock alinhado; gate empírico)
- [[ADR-097]] D3 — services recebem value objects tipados (`DecisionRepositoryProtocol` ganha `next_code` na interface)
- [[ADR-089]] — ISP em domínio
- [[ADR-109]] — auth portability (snapshot OpenAPI como contrato)
- Co-design: `product-designer` (sessão 2026-05-15), `senior-cto`, `data-engineer`
