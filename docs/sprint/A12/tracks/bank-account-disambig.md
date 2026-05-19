---
id: TRACK-bank-account-disambig
type: track
title: "Track bank-account-disambig — 4 PRs sequenciais (ADR-226)"
sprint: A12
lane: "[[A12.bank-account-disambig]]"
status: ready
created_at: "2026-05-19"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/backend
  - area/pipeline
  - area/persistence
---

# Track bank-account-disambig — 4 PRs sequenciais

> **Lane:** [[A12.bank-account-disambig]] · **ADR canônica:** [[ADR-226]]
> · **Branch prefix:** `agent/bank-account-disambig-pr<N>/*` (1 branch
> por PR; cada PR independentemente revertível)
> · **Pré-requisitos internos:** nenhum. Migration de `workspace_id`
> denormalizado em `bank_accounts` é primeira etapa do PR1.
> · **Supervisão obrigatória:** **senior-cto** revisa PR3 (resolver +
> DI no E4/InvestmentsConsolidator/E1); **data-engineer** revisa PR1
> (migration + backfill) e PR2 (schema E3 bump + 11 parsers); **financial-planner**
> revisa PR3 (semântica do `needs_review` em investments + UX `titulares:
> list`) e PR4 (UI pre-fill IRPF + FAQ).

## Briefing (1 frase)

Executar os 4 PRs sequenciais de [[ADR-226]] — introduzir `account_number`
como discriminador real (mantendo `banco_membro` legado como fallback
degradado), criar `account_resolver` puro consumido por E4 +
InvestmentsConsolidator + E1 (merge idempotente), reservar schema
`is_joint`/`co_titulares` para V2.

## Por que ler [[ADR-226]] antes de codar

ADR-226 é o plano: §Decisão lista as 5 mudanças coordenadas (account_number
normalização, schema family_members aditivo, account_resolver puro,
schema E3 bump + titulares: list, E1 merge idempotente),
§Follow-ups delimita o escopo (V1 não rateia conta conjunta; reserva schema),
§Riscos lista mitigações enforçadas em código. **Não duplique conteúdo da
ADR neste track** — referencie seção.

## Ordem obrigatória dos PRs

1. **PR1 primeiro** (migration + aditivo) — sem este, PR2/PR3 não têm
   onde gravar/ler `workspace_id` em `bank_accounts` nem `contas[]` no JSON.
2. PR2 (schema E2/E3 bump aditivo + parsers normalizam).
3. PR3 (resolver + DI nos consumidores + goldens) — maior PR; **gate**
   golden multi-membro verde + paridade single-member.
4. PR4 (CONCURRENTLY index + UI pre-fill + telemetria + flip ADR).

## PR1 — Migration + serializer aditivo + UI in-app UNIQUE (~1.5d)

**Migration Alembic** `<rev>_bank_accounts_workspace_id_and_disambig_reserve.py`:

```python
def upgrade() -> None:
    # Phase 1: workspace_id denormalizado
    with op.batch_alter_table("bank_accounts") as batch:
        batch.add_column(sa.Column("workspace_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(text("""
        UPDATE bank_accounts ba
           SET workspace_id = fm.workspace_id
          FROM family_members fm
         WHERE fm.id = ba.member_id
    """))
    with op.batch_alter_table("bank_accounts") as batch:
        batch.alter_column("workspace_id", nullable=False)
        batch.add_column(sa.Column("is_joint", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("co_titulares", sa.dialects.postgresql.JSONB(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("bank_accounts") as batch:
        batch.drop_column("co_titulares")
        batch.drop_column("is_joint")
        batch.drop_column("workspace_id")
```

**Partial unique index é PR4** (`CONCURRENTLY` precisa de migration própria fora de transação).

**Serializer aditivo** em [config_materializer.py](../../../../backend/app/services/config_materializer.py)
e [api/config.py](../../../../backend/app/api/config.py):

```python
def serialize_family_members(members):
    # ... código atual gerando "banco_membro" mantido ...
    contas: list[dict] = []
    for m in members:
        for acc in m.accounts:
            contas.append({
                "institution_code": acc.institution_code,
                "account_number_norm": _normalize_account_number(acc.account_number),
                "account_number_raw": acc.account_number,
                "agency": acc.agency,
                "account_type": acc.account_type,
                "member_key": m.key,
                "is_joint": acc.is_joint,
                "co_titulares": acc.co_titulares or [],
            })
    return {..., "banco_membro": banco_membro, "contas": contas}
```

`_normalize_account_number` é o **mesmo helper** que entrará em
`pipeline/domain/services/account_resolver.py` no PR3 — extraído já
em PR1 para `backend/app/services/_account_normalization.py` (ou
equivalente neutro).

**Parser** em [pipeline/adapters/config_parsers.py](../../../../pipeline/adapters/config_parsers.py)
ganha `ContaConfig` dataclass + leitura de `contas[]` com fallback para
`banco_membro` legado quando ausente.

**UI** — `frontend/src/app/(app)/config/MembersTab.tsx`:
- Adiciona campos `is_joint` (checkbox, default false) + `co_titulares`
  (multi-select de membros, condicional a `is_joint=true`).
- Valida UNIQUE in-app: ao salvar, percorre `bankAccounts` do workspace
  e bloqueia se `(institution_code, account_number_norm)` já existe
  com `member_key` diferente. Mensagem: "Já existe conta neste banco
  para outro membro; informe o número da conta para diferenciar".
- **Não exige `account_number`** para todas as contas — só quando
  detecta colisão.

**Validação:**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_migration_bank_accounts_workspace_id.py -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
cd frontend && npm test -- --run
```

**Commit:** `feat(db): bank_accounts.workspace_id + is_joint/co_titulares reserve + serializer contas[] (ADR-226 PR1)`

## PR2 — Schema E2/E3 bump aditivo + 11 parsers normalizam (~2d)

**Helper compartilhado** `pipeline/domain/services/account_normalization.py`
(ou colocar no resolver direto; ADR-226 §1):

```python
import re

_NON_DIGITS = re.compile(r"\D")

def normalize_account_number(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    return digits or None
```

**E2 parsers** ([scripts/e2/banks/](../../../../scripts/e2/banks/)) —
auditar 11 parsers; cada um propaga `numero_conta_norm: str | None`
no template de output:

- Reaproveitar `extract_account_number` quando existir
  ([scripts/e2/common.py](../../../../scripts/e2/common.py)).
- Para parsers que retornam digits cru (BTG), normalização é idempotente.
- Para parsers que entregam regex group cru (Bradesco), aplicar
  `normalize_account_number()` no boundary.
- `make_result_template` ganha campo `numero_conta_norm` default `None`.

**Schema E3** [config/schemas/e3_reconciled.schema.json](../../../../config/schemas/e3_reconciled.schema.json):

```jsonc
{
  "properties": {
    "titular":   { "type": "string", "description": "DEPRECATED — use titulares; mantido por compat" },
    "titulares": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
    "account_number": { "type": ["string", "null"] },   // top-level
    "transacoes": {
      "type": "array",
      "items": {
        "properties": {
          "account_number": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```

`titulares` é primário; `titular` permanece readable para compat. E3 reconciler
([pipeline/domain/services/e3_*.py](../../../../pipeline/domain/services/))
propaga `account_number_norm` por transação.

**Bump versão** em [config/pipeline.json](../../../../config/pipeline.json)
(`report_version` ou schema version conforme padrão).

**`make update-openapi-snapshot`** se algum endpoint expõe schema E3.

**Validação:**

```bash
MATHOMS_PIPELINE_SCHEMA_MODE=strict pytest tests/test_e3_golden_execution.py -q
pytest tests/unit/scripts/test_account_normalization.py -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Commit:** `feat(pipeline): normalize account_number across E2 parsers + E3 schema bump aditivo (ADR-226 PR2)`

## PR3 — `account_resolver` puro + DI nos consumidores + golden multi-membro (~2d)

**Resolver puro** `pipeline/domain/services/account_resolver.py` — ver
[[ADR-226]] §3 para assinatura completa (~40 linhas).

**Teste unitário** `tests/unit/pipeline/test_account_resolver.py` cobre
8 cases (ADR-226 §Gates).

**Consumidores ajustados:**

- [scripts/e4_categorize.py](../../../../scripts/e4_categorize.py) — `BANCO_MEMBRO` global removido; resolver instanciado em construção via DI; lookup por `(banco, account_number)` da transação ([[ADR-111]] stateless rigoroso).
- [pipeline/domain/services/investments_consolidator.py](../../../../pipeline/domain/services/investments_consolidator.py) — fallback de membro usa resolver; `confidence in {"ambiguous", "unknown"}` ⇒ posição marcada `needs_review=true` + motivo legível (não chuta).
- [pipeline/stages/extract_members.py](../../../../pipeline/stages/extract_members.py) — merge idempotente:
  - Existe `(workspace_id, institution_code, account_number_norm)` → skip + log INFO.
  - Existe `(workspace_id, institution_code)` mas account_number difere → append nova `BankAccount` ao mesmo `member` (quando resolver casa) ou titular default + warning.
  - Member do IRPF não casa nenhum `family_members.cpf_encrypted` → cria `role="dependente"` + warning.

**Golden multi-membro novo** `tests/test_e4_golden_multi_member.py`:

- Fixture: workspace com David + Mariana ambos Itaú, contas distintas.
- Input: extrato Itaú David com transações + extrato Itaú Mariana com transações.
- Output esperado: cada transação atribuída ao membro correto via
  `account_number` matching. `BANCO_MEMBRO` legado **não** consultado
  (confidence=strict).

**Goldens single-member existentes** ([tests/test_llm_golden.py:41](../../../../tests/test_llm_golden.py),
`test_e3/e4/e5_golden_execution.py`) verdes — paridade.

**Teste idempotência E1** `tests/test_extract_members_idempotent.py`:

- Cadastro manual em `bank_accounts` com `source_tier=editorial`.
- Rodar E1 sobre IRPF que declara mesma conta.
- Esperado: manual preservado; IRPF não duplica nem sobrescreve.

**Validação:**

```bash
pytest tests/unit/pipeline/test_account_resolver.py -q
pytest tests/test_e4_golden_multi_member.py -q   # novo
pytest tests/test_llm_golden.py -q               # paridade
pytest tests/test_e3_golden_execution.py -q
pytest tests/test_e4_golden_execution.py -q
pytest tests/test_e5_golden_execution.py -q
pytest tests/test_extract_members_idempotent.py -q
pytest backend/tests -q
pytest tests -q
pre-commit run --all-files
```

**Commit:** `feat(pipeline): account_resolver puro + DI E4/Investments/E1 merge idempotente (ADR-226 PR3)`

## PR4 — Partial unique index + UI pre-fill IRPF + telemetria + flip ADR (~1d)

**Migration nova** `<rev>_bank_accounts_partial_unique_account_number.py`:

```python
def upgrade() -> None:
    # CONCURRENTLY exige autocommit; fora de transação Alembic
    with op.get_context().autocommit_block():
        op.execute(text("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
              uq_bank_account_workspace_inst_num
              ON bank_accounts (
                workspace_id,
                institution_code,
                regexp_replace(account_number, '\\D', '', 'g')
              )
              WHERE account_number IS NOT NULL
        """))

def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS uq_bank_account_workspace_inst_num"))
```

**Backend** retorna `409 Conflict` em violação do UNIQUE
(`backend/app/api/config.py` endpoints de `bank_accounts`) com mensagem
acionável: `{"error": "account_already_registered", "detail": "Conta (banco {x}, número {y}) já cadastrada para membro {z}."}`.

**UI** — `frontend/src/app/(app)/config/MembersTab.tsx`:

- **Pre-fill IRPF** (financial-planner item): quando `extract_members`
  (E1) já rodou no workspace, mostra "Contas detectadas no IRPF" como
  sugestões pré-preenchidas; usuário confirma/edita em vez de digitar.
- Mensagem clara de 409 quando colisão remota (in-app valida primeiro,
  mas race condition pode acontecer).

**Telemetria** [backend/app/core/logging.py](../../../../backend/app/core/logging.py):

```python
mathoms.account_resolver.resolve_total{confidence="strict|fallback_bank|ambiguous|unknown"}
```

Counter incrementado em cada call de `AccountResolver.resolve()`. Monitoring
em workspaces piloto por 1 semana pós-merge.

**FAQ produto** (financial-planner item): seção "Como o Mathoms decide
de qual membro é cada conta" em `docs/reference/` ou Wiki — texto curto
explicando hierarquia (account_number > banco_único > IRPF) +
`needs_review` quando ambíguo.

**Flip ADR-226** `Proposto` → `Decidido (A12.bank-account-disambig)`.

**Validação:**

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_api_config_bank_account_conflict.py -q
pytest backend/tests -q
pytest tests -q
cd frontend && npm test -- --run
pre-commit run --all-files
```

**Commit:** `feat(db): bank_accounts partial unique + UI pre-fill IRPF + telemetria (ADR-226 PR4)`

## Decisões já tomadas ([[ADR-226]] §Alternativas)

- **`account_number` digits-only normalizado no boundary**, não coluna nova
  (regex index sobre expressão).
- **Materializar `contas[]` no JSON** (não DB-lookup) — preserva boundary
  pipeline↔backend ([[ADR-097]]).
- **`workspace_id` denormalizado em `bank_accounts` no PR1**, não no PR4
  (precondição de PR4 index).
- **E1 merge idempotente** (não sobrescrever cadastro manual) — `source_tier`
  editorial vence IRPF/LLM ([[ADR-146]]).
- **`is_joint` + `co_titulares` reservados em V1**, sem implementar rateio
  (V2 follow-up ADR).
- **InvestmentsConsolidator `needs_review` em ambiguidade**, sem fallback
  silencioso (financial-planner veto).
- **Não esconder UI de contas para workspace single-member** (rejeitado
  por financial-planner: família cresce, fricção primeira vez < desconfiança).

## Ligações

- ADR canônica: [[ADR-226]] (Proposto)
- Lane: [[A12.bank-account-disambig]]
- Pré-req externo: nenhum
- Desbloqueia: V2 ADR (conta conjunta com rateio proporcional)
- Relacionado: [[ADR-127]] (E1 extract_members; merge idempotente), [[ADR-137]] (institution_catalog), [[ADR-097]] (boundary pipeline↔backend), [[ADR-111]] (stateless; BANCO_MEMBRO global some), [[ADR-146]] (source_tier), [[ADR-143]] (rules-as-code), [[ADR-186]] (override sticky pattern), [[ADR-215]] (workspace overrides + partial unique pattern), [[ADR-157]] (IRPF full; pre-fill UI)
