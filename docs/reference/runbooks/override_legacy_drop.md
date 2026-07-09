# Runbook — Fase E do ADR-282: drop destrutivo do estado legado de identidade do override

> **ADR:** [[ADR-282]] (Decidido · 2026-06-08 · Emenda 2026-07-01) — M2 destrutiva.
> **Lane:** [[A26.l5]] (`m2-override-drop`) — bloqueada por [[A26.l4]] + gates
> G1/G2/G2b/G3 + PITR + **go/no-go do owner do produto**.
> **Owner da execução:** SRE/agente da lane, **após** sign-off do owner (§9).
> **Janela alvo:** freeze→drop→unfreeze em minutos; o drop em si em segundos.
> **IRREVERSÍVEL:** não existe `downgrade` — contingência é restore PITR/snapshot
> **com perda** (§7). Nunca executar sob janela apertada.
> **Procedure exercitada em staging:** ☐ (gate obrigatório — §10).

---

## Por que este runbook existe

A M1 do [[ADR-282]] (`adr282overridenk`) adicionou a identidade v2
(`natural_key_hash` + snapshot re-hasheável) a `transaction_overrides` de forma
aditiva e reversível. A M2 — objeto deste runbook — é o **único ponto
irreversível** da migração: dropa a coluna `transaction_hash` (v1 legado), a UK
`uq_override_ws_hash` e deleta `generate_transaction_hash`
(`backend/app/services/transaction_service.py`) **na mesma PR**, junto com o
ramo v1/fallback de `override_dual_read.py`. Depois do drop, a linha de override
não é re-hasheável em v1 nunca mais — se o mapeamento v2 estiver errado, o
fallback que mascararia o erro já não existe. Por isso o drop é gated por
quatro condições auditáveis (§2), backup verificado (§4) e sign-off explícito
do owner (§9).

Este runbook é entregue **antes** do drop (preparação da lane [[A26.l5]],
PR docs-only). Os Apêndices A e B contêm os drafts da migration destrutiva e
do sentinela G3 — são **copiados para o PR do drop** quando o go/no-go sair;
não existem como arquivos executáveis até lá (evita dead code em `main`).

---

## 1. Escopo do drop (o que sai, o que fica)

**Sai (mesma PR, [[ADR-282]] Decisão 1 + [[A25.l1]] §5):**

| Objeto | Onde | Nota |
|---|---|---|
| Coluna `transaction_hash` (String 64) | `transaction_overrides` | via migration (Apêndice A) |
| UK `uq_override_ws_hash` (`workspace_id, transaction_hash`) | idem | idem |
| Índice `ix_transaction_overrides_transaction_hash` | idem | auto-criado por `index=True` na coluna |
| Índice parcial `uq_txov_active_rule` **sobre `transaction_hash`** | idem | **recriado sobre `natural_key_hash`** (ADR-188 §D2 continua valendo) |
| View `transaction_overrides_active` **na forma atual** | idem | SELECTa `transaction_hash` — Postgres **recusa** o drop da coluna com view dependente; a migration recria a view sem a coluna |
| Função `generate_transaction_hash` | `backend/app/services/transaction_service.py` | deletada, **não vira shim** |
| Ramo v1/fallback do dual-read (`by_legacy_hash`, `log_v1_fallback`, shadow-compare) | `backend/app/services/override_dual_read.py` | match passa a ser v2-only |
| `_find_by_legacy_hash` | `backend/app/application/transaction/create_override.py` + `delete_override.py` | lookup passa a `natural_key_hash` |
| Scope v1 do apply retroativo | `backend/app/application/categorization/_apply_engine.py` | idem |
| Flag `override_natural_key_v2_enabled` | `feature_flags_service.py` DEFAULTS | vira no-op/removida |
| Flag `override_dual_read_shadow_compare` | idem | instrumentação morre com a M2 ([[ADR-282]] §Emenda item 3) |
| Atributo `transaction_hash` do model | `backend/app/models/transaction_override.py` | **mesmo PR** — ORM não pode referenciar coluna dropada |

**Fica:**

- `natural_key_hash`, `hash_version`, snapshot `tx_*`, `orphaned_at` — a
  identidade v2 e o invariante "linha re-hasheável sozinha".
- Órfãos quarentenados (`orphaned_at IS NOT NULL`) — estado terminal
  permanente, **não bloqueiam** o gate ([[ADR-282]] §5).
- O **campo de wire** `transaction_hash` em `TransactionItem` /
  `TransactionOverrideResponse` — o nome é **opaco para o FE** ([[ADR-282]]
  §Wire/FE); o valor passa a ser o v2. Ver §2.5 (G3) sobre por que o sentinela
  **não** proíbe o token `transaction_hash` indiscriminadamente.
- O `transaction_hash` do **pipeline** (`pipeline/domain/services/_tx_identity.py`,
  `transaction_classifier.py`, `cash_flow_builder.py`) — é a identidade K4 do
  item E4 ([[ADR-287]]), já v2, conceito distinto do hash legado de override.

**Pré-condição de código no PR do drop (item de aceite da lane):** o read-path
`load_transactions` hoje ainda computa `tx_hash = generate_transaction_hash(tx)`
e serve `row_id = f"{tx_hash}:{idx}"` ao FE. O PR do drop **troca a key servida
para o v2** (`identity_from_transaction_item(...).natural_key_hash`) — senão o
FE perde o match no instante do deploy. Confirmar antes do merge; rodar
`make update-openapi-snapshot` se o shape do response mudar.

---

## 2. Gates G1/G2/G2b/G3 (condições conjuntas — verificar TODAS antes do drop)

Registrar o output de cada gate (timestamp + contagens) no
[SMOKE_TEST_HUMAN.md](../SMOKE_TEST_HUMAN.md) e anexar ao sign-off (§9).

### 2.1. G1 — estado de dado (zero legado não-quarentenado)

```sql
-- G1: todo override é v2-ancorado ou quarentenado. Esperado: 0.
SELECT count(*) AS legados_nao_quarentenados
FROM transaction_overrides
WHERE natural_key_hash IS NULL
  AND orphaned_at IS NULL;
```

Se ≠ 0, diagnóstico por bucket antes de qualquer ação (backfill pendente?
soft-deleted antigo sem backfill? — `deleted_at IS NOT NULL` também conta no
G1, por desenho: a migration dropa a coluna da tabela inteira):

```sql
SELECT
  (natural_key_hash IS NOT NULL)                  AS v2_ancorado,
  (orphaned_at IS NOT NULL)                       AS quarentenado,
  (deleted_at IS NOT NULL)                        AS soft_deleted,
  count(*)
FROM transaction_overrides
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
```

G1 vermelho → rodar o backfill
(`backend/app/services/internal_ops/backfill_override_identity.py`, dry-run
primeiro) ou quarentenar explicitamente o resíduo; **nunca** prosseguir com a
migration "porque o hard-assert vai pegar" — o hard-assert é defesa em
profundidade, não o gate.

### 2.2. G2 — cobertura (fallback zero COM exercício real, ≥1 sprint flag-ON)

Fonte de verdade: `audit_logs` com
`action = 'override.v2_dualread_snapshot'` (drenado ao fim do reprocesso E4 —
[[ADR-282]] §Emenda item 2; runs headless não persistem review_reasons, mas o
snapshot do dual-read é persistido no boundary do E4 normalmente).

```sql
-- G2: janela de ≥1 sprint sob flag-ON. Esperado: v1_fallback_total == 0 AND v2_match_total >= 1.
SELECT
  coalesce(sum((details->>'v1_fallback')::int), 0) AS v1_fallback_total,
  coalesce(sum((details->>'v2_match')::int), 0)    AS v2_match_total,
  count(*)                                          AS snapshots,
  min(created_at)                                   AS janela_inicio,
  max(created_at)                                   AS janela_fim
FROM audit_logs
WHERE action = 'override.v2_dualread_snapshot'
  AND created_at >= now() - interval '14 days';
```

Breakdown por workspace (todo workspace com override precisa ter exercitado v2):

```sql
SELECT
  workspace_id,
  coalesce(sum((details->>'v1_fallback')::int), 0) AS v1_fallback,
  coalesce(sum((details->>'v2_match')::int), 0)    AS v2_match
FROM audit_logs
WHERE action = 'override.v2_dualread_snapshot'
  AND created_at >= now() - interval '14 days'
GROUP BY workspace_id
ORDER BY v1_fallback DESC, v2_match ASC;
```

> ⚠️ `sum(v2_match) == 0` com `sum(v1_fallback) == 0` **não é verde** — é
> ausência de exercício (nenhum reprocesso E4 na janela). Disparar reprocesso
> real (in-process, não headless-only) antes de reavaliar.

### 2.3. G2b — corretude (shadow-compare, divergência zero)

G2 mede **cobertura**, não corretude: o `match()` retorna no 1º hit v2 sem
consultar v1, então override grudado na linha errada deixa `v1_fallback == 0`
(verde falso). G2b exige `divergence == 0` na janela, medido com a flag
`override_dual_read_shadow_compare` **ON** durante a janela de observação
([[ADR-282]] §Emenda item 3).

```sql
-- G2b: shadow-compare ativo na janela. Esperado: divergencia_total == 0.
SELECT
  coalesce(sum((details->>'divergence')::int), 0) AS divergencia_total,
  count(*) FILTER (WHERE details ? 'divergence')  AS snapshots_com_metrica
FROM audit_logs
WHERE action = 'override.v2_dualread_snapshot'
  AND created_at >= now() - interval '14 days';
```

> Nota de contrato: a key persistida pelo código é `divergence`
> (`OverrideMatchIndex.snapshot()`), não `divergence_count` como grafado na
> prosa da emenda — a query acima segue o código.

`divergencia_total > 0` → **NO-GO absoluto**. Investigar linha a linha (drift
de normalização? adapter `inputs_from_transaction_item` divergindo do dedup?)
antes de reabrir a janela. `snapshots_com_metrica == 0` → shadow-compare nunca
rodou; ligar a flag e recomeçar a janela de observação.

### 2.4. Pré-check das flags (ordem da emenda, item 1)

Ordem obrigatória: `backfill → flip por workspace → DEFAULTS por último`. Antes
do drop, confirmar que o cutover está formalizado no `DEFAULTS`
(`backend/app/services/feature_flags_service.py`) e que nenhum workspace tem
override individual **desligando** o v2:

```sql
-- Nenhum workspace pode estar com override_natural_key_v2_enabled=false.
SELECT workspace_id, flags
FROM feature_flags
WHERE flags::text LIKE '%override_natural_key_v2_enabled%';
-- Inspecionar manualmente: qualquer "false" para essa key = NO-GO.
```

### 2.5. G3 — sentinela de código

`dev/check_no_legacy_override_hash.py` (Apêndice B — só existe como arquivo no
PR do drop) verde no branch do drop:

```bash
python3 dev/check_no_legacy_override_hash.py
```

Falha se `generate_transaction_hash` (qualquer ocorrência) ou os marcadores
exclusivos do caminho legado (`uq_override_ws_hash`, `by_legacy_hash`,
`legacy_hash`) reaparecerem em `backend/app/` / `pipeline/` / `dev/`.

> **Desvio deliberado vs. o texto da lane:** a lane diz "falha se
> `transaction_hash` reaparecer". O token nu `transaction_hash` **não pode ser
> proibido** wholesale: (a) é o nome do campo de identidade K4 v2 do pipeline
> ([[ADR-287]] — `transaction_classifier.py`, `cash_flow_builder.py`,
> `_tx_identity.py`); (b) é o nome de campo de wire opaco que o FE continua
> recebendo ([[ADR-282]] §Wire/FE). O sentinela proíbe o token
> `transaction_hash` **apenas** em `backend/app/models/transaction_override.py`
> (a coluna dropada) e cobre o resto pelos marcadores exclusivos do legado.

O sentinela é **wired no pre-commit somente no PR do drop** (script puro
stdlib — sem import de app, para não quebrar o job Lint do CI).

---

## 3. Pré-condições operacionais (sre-devops — bloqueadores duros)

- **PITR confirmado no Postgres (Coolify)** — [RUNBOOK §5](../RUNBOOK.md)
  trata DR como pendente; **confirmar capacidade real antes do go/no-go**.
  Registrar: janela de retenção WAL, último base backup, LSN corrente. Se PITR
  **não** estiver disponível, registrar explicitamente
  "PITR N/A → RPO = timestamp do snapshot §4" no sign-off.
- **Janela de baixo tráfego + freeze de escrita de override** — nenhum
  `POST/DELETE /{transaction_hash}/override`, nenhum reprocesso E4 (learning
  loop cria overrides programaticamente — [[ADR-282]] Decisão 8) durante
  snapshot→count→drop. Mecanismo: desligar workers + janela anunciada
  (padrão do freeze em [pipeline_rollback.md §5](pipeline_rollback.md)).
- **In-place, não blue/green** — blue/green é teatro para drop irreversível
  single-tenant: as duas cores compartilham o mesmo Postgres.
- **Staging primeiro** — migration exercitada em staging (upgrade + hard-assert
  testado com fixture de 1 override legado não-quarentenado → aborta +
  `downgrade` testado para `raise`) **antes** de qualquer execução em prod (§10).
- **Retenção do backup: 30 dias**, purge documentado (LGPD — o dump contém
  categorização de transações do tenant; tratar como dado pessoal).

---

## 4. Backup pré-drop (obrigatório, verificado)

```bash
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BK_DIR="/var/backups/mathoms"

# 1. Dump de DADOS da tabela afetada
pg_dump --table=transaction_overrides \
  -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  > "$BK_DIR/pre-drop-override-data-$TS.sql"

# 2. Dump de SCHEMA (DDL completo — recriar view/índices exige a forma exata)
pg_dump -s --table=transaction_overrides \
  -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
  > "$BK_DIR/pre-drop-override-schema-$TS.sql"

# 3. Não-vazio + sha256 registrado
test -s "$BK_DIR/pre-drop-override-data-$TS.sql"   || { echo "DUMP DADOS VAZIO — ABORTA"; exit 1; }
test -s "$BK_DIR/pre-drop-override-schema-$TS.sql" || { echo "DUMP SCHEMA VAZIO — ABORTA"; exit 1; }
shasum -a 256 "$BK_DIR"/pre-drop-override-*-"$TS".sql | tee "$BK_DIR/pre-drop-override-$TS.sha256"

# 4. LSN corrente (âncora de PITR) — registrar no sign-off
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT pg_current_wal_lsn(), now();"
```

Counts de referência (comparar no §5 e no §6):

```sql
SELECT
  count(*)                                        AS total,
  count(*) FILTER (WHERE natural_key_hash IS NOT NULL) AS v2_ancorados,
  count(*) FILTER (WHERE orphaned_at IS NOT NULL) AS quarentenados,
  count(*) FILTER (WHERE deleted_at IS NOT NULL)  AS soft_deleted
FROM transaction_overrides;
```

> ⚠️ Sem backup verificado (não-vazio + sha256 + LSN), **não existe go**. O
> passo é gate, não recomendação.

---

## 5. Execução — gate-then-drop (janela de segundos)

Sequência única, sem pausa entre 3 e 5:

```bash
# 1. Freeze de escrita (workers off — queue acumula, não perde)
#    + anúncio no canal de ops.

# 2. Re-rodar G1 DENTRO da janela (o count do §2.1 pode ter mudado)
psql -c "SELECT count(*) FROM transaction_overrides WHERE natural_key_hash IS NULL AND orphaned_at IS NULL;"
# ≠ 0 → ABORTA (unfreeze, investigar, reagendar). Nunca "resolver na hora".

# 3. Snapshot §4 (dentro da janela — RPO = agora)

# 4. Deploy do PR do drop + migration (hard-assert de G1 embutido re-roda o count)
cd backend && alembic upgrade head

# 5. Verificação imediata (§6.1) — só então unfreeze (workers on)
```

Se a migration abortar no hard-assert (`RuntimeError: G1 violado`): a transação
da migration faz rollback sozinha — **nada foi dropado**. Unfreeze, investigar
a linha que apareceu entre o gate e a janela (write concorrente = freeze
falhou), reagendar.

---

## 6. Verificação pós-deploy (sem rollback — só forward)

### 6.1. Imediata (dentro da janela, antes do unfreeze)

```bash
# Coluna sumiu; view e índices recriados sobre v2
psql -c "\d transaction_overrides"        # sem transaction_hash, sem uq_override_ws_hash
psql -c "\d+ transaction_overrides_active" # view recriada sem a coluna
psql -c "SELECT count(*) FROM transaction_overrides;"  # == total do §4

# App de pé
curl -sf https://api.mathoms.ai/health
```

### 6.2. Funcional (pós-unfreeze, ainda na janela de observação)

- Goldens E3/E4/E5 + snapshot do view-model verdes no CI do commit-merge.
- `python3 dev/check_no_legacy_override_hash.py` verde em `main`.
- Read-path devolve `natural_key_hash` como key opaca: `GET /v1/.../transactions`
  em workspace canário → `row_id` tem prefixo de 16 hex (v2), não 64 (v1).
- Override sticky sobrevive: aplicar 1 override manual em workspace canário →
  reprocessar E4 → categoria persiste.
- ORM lê override sem erro (nenhum `UndefinedColumn` nos logs
  `mathoms.categorization.*`).

### 6.3. Aceite documental

- [[ADR-282]] flippa `Proposto → Decidido (A26)` no merge — **nota:** a ADR já
  consta `Decidido (A23 · pré-passo-2 B4)` no frontmatter; o PR do drop
  registra a Fase E fechada via `phase`/emenda datada, não re-flip de status.
- Snapshot dos gates no [SMOKE_TEST_HUMAN.md](../SMOKE_TEST_HUMAN.md).
- Linha nova no histórico §10.

---

## 7. Contingência — restore com perda (PITR/snapshot)

**Não existe `downgrade`.** Se pós-drop o match de override estiver
sistematicamente errado (divergência que G2b deixou passar) e a decisão for
voltar:

1. **Freeze absoluto** (workers off + anúncio) — cada minuto de escrita
   pós-incidente vira perda no restore.
2. Decidir o alvo com o owner:
   - **PITR** para o LSN registrado no §4 — restaura o **banco inteiro** ao
     instante pré-drop. Perde **tudo** que qualquer tabela escreveu depois
     (uploads, runs, auditoria) — RPO = LSN do §4. Só se o incidente for
     detectado em minutos/horas.
   - **Restore cirúrgico da tabela** — `psql < pre-drop-override-data-$TS.sql`
     num schema de staging, reconciliação manual linha a linha contra o estado
     corrente, reaplicação seletiva. Perde apenas overrides criados pós-drop
     que conflitem. Mais lento, blast radius menor — **preferir** quando o
     detect é tardio (>24h).
3. Revert do PR do drop via `gh pr revert` (o código volta a esperar a coluna;
   o restore acima recria o dado).
4. Verificação §6 completa + **postmortem obrigatório**
   ([incidents/](incidents/)) — contingência acionada nunca é silenciosa.

> A escolha "coluna nova + backfill + gates" em vez de "in-place + PITR como
> rede" existe exatamente para que este parágrafo nunca rode ([[ADR-282]]
> §Alternativas rejeitadas). Se rodou, o postmortem responde: qual gate mentiu?

---

## 8. Observação — 1h e 24h

**T+1h (operador na janela):**

- Logs `mathoms.categorization.*` sem `ERROR`/`UndefinedColumn`.
- Zero 5xx em `/{transaction_hash}/override` (o path param continua existindo —
  agora carrega o v2).
- 1 reprocesso E4 real em workspace canário: overrides aplicados, contagem de
  `is_overridden` estável vs. pré-drop.

**T+24h (async, registrar no histórico §10):**

- `audit_logs` **sem** snapshots novos de `override.v2_dualread_snapshot`
  (instrumentação removida junto — snapshot novo = código legado vivo em
  algum worker stale; investigar deploy).
- Nenhum ticket/dogfood de "categorização manual sumiu".
- Counts §4 vs. corrente: diff só positivo (overrides novos), nunca negativo
  inexplicado.

---

## 9. Sign-off do owner (go/no-go)

O drop **não executa** sem registro explícito do owner do produto, com
evidência anexada. Template:

```
GO/NO-GO — ADR-282 Fase E (drop transaction_hash legado)
Data/hora (UTC):
Decisão: [ ] GO   [ ] NO-GO
Evidências anexadas:
  [ ] G1 == 0 (query §2.1, timestamp + output)
  [ ] G2 v1_fallback==0 AND v2_match>=1, janela >= 1 sprint (§2.2)
  [ ] G2b divergence==0 com shadow-compare ativo (§2.3)
  [ ] Flags na ordem da emenda: DEFAULTS ON, nenhum workspace OFF (§2.4)
  [ ] G3 sentinela verde no branch do drop (§2.5)
  [ ] Staging: upgrade + hard-assert + downgrade-raise exercitados (§10)
  [ ] Backup §4: paths + sha256 + LSN + retenção 30d
  [ ] PITR confirmado OU "N/A → RPO = ts do snapshot" registrado
  [ ] Dogfood verde (nenhum override órfão inesperado)
Assinatura (owner):
Executor designado (SRE/agente):
```

Postmortem obrigatório se a contingência (§7) for acionada.

---

## 10. Histórico de exercícios em staging

Atualizar a cada exercício (gate: ≥1 linha verde de staging **antes** do
go/no-go de prod):

| Data | Operador | Cenário | Resultado | Duração da janela |
|---|---|---|---|---|
| YYYY-MM-DD | — | upgrade completo em staging (G1 verde) | — | — |
| YYYY-MM-DD | — | hard-assert: fixture 1 legado não-quarentenado → aborta | — | — |
| YYYY-MM-DD | — | `alembic downgrade -1` → `RuntimeError` (irreversibilidade) | — | — |

---

## 11. Referências

- [[ADR-282]] — identidade v2 do override (canônica; §Emenda = mecânica da M2)
- [[A26.l5]] — lane do drop (gates + aceite) · [[A26.l4]] — habilitador (flip + instrumentação)
- [[ADR-287]] — `transaction_hash` v2 do pipeline (conceito distinto do legado de override)
- [[ADR-188]] — soft-delete + partial unique `uq_txov_active_rule` (recriado sobre v2)
- [pipeline_rollback.md](pipeline_rollback.md) — modelo de forma deste runbook
- [data_lineage_migrations.md](data_lineage_migrations.md) — Fase A (M1 `adr282overridenk`)
- [incidents/](incidents/) — templates de postmortem
- [docs/_MOC/_generated/ADR_INDEX.md](../../_MOC/_generated/ADR_INDEX.md)

---

## Apêndice A — draft da migration destrutiva (copiar para o PR do drop)

> **Não é arquivo executável neste repo** — vive aqui como fenced block até o
> go/no-go. No PR do drop: criar
> `backend/alembic/versions/adr282m2drop_override_legacy_drop.py` com este
> conteúdo, ajustar `down_revision` para o head do momento, e cobrir com test
> `pytestmark = pytest.mark.migration` (hard-assert aborta com fixture de 1
> legado não-quarentenado; `downgrade` raise).

```python
"""ADR-282 M2 (Fase E): drop destrutivo do estado legado de identidade do override.

Revision ID: adr282m2drop
Revises: <head-no-momento-do-PR>
Create Date: <data-do-PR>

IRREVERSIVEL. Pre-condicoes: gates G1/G2/G2b/G3 verdes + backup verificado +
sign-off do owner (docs/reference/runbooks/override_legacy_drop.md). O
hard-assert de G1 abaixo e defesa em profundidade, nao o gate.

Sem ``IF EXISTS`` defensivo — migration one-shot deve falhar ruidoso em re-run.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr282m2drop"
down_revision: Union[str, Sequence[str], None] = "<head-no-momento-do-PR>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_G1_COUNT_SQL = (
    "SELECT count(*) FROM transaction_overrides "
    "WHERE natural_key_hash IS NULL AND orphaned_at IS NULL"
)

# View recriada SEM transaction_hash (a forma atual SELECTa a coluna e o
# Postgres recusa drop de coluna com view dependente).
_VIEW_TXOV_ACTIVE_V2_SQL = """
CREATE VIEW transaction_overrides_active AS
SELECT id, workspace_id, natural_key_hash, hash_version, original_category,
       new_category, notes, reviewed, source, rule_id, created_at, deleted_at,
       orphaned_at
FROM transaction_overrides
WHERE deleted_at IS NULL
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")

    legados = bind.execute(sa.text(_G1_COUNT_SQL)).scalar_one()
    if legados != 0:
        raise RuntimeError(
            f"G1 violado: {legados} override(s) com natural_key_hash IS NULL e "
            "orphaned_at IS NULL — drop abortado (nada foi alterado). Rode o "
            "backfill/quarentena e re-execute os gates do runbook "
            "override_legacy_drop.md antes de tentar de novo (ADR-282 Fase E)."
        )

    op.execute("DROP VIEW transaction_overrides_active")
    op.drop_index("uq_txov_active_rule", table_name="transaction_overrides")
    op.drop_index(
        "ix_transaction_overrides_transaction_hash",
        table_name="transaction_overrides",
    )
    with op.batch_alter_table("transaction_overrides") as batch_op:
        batch_op.drop_constraint("uq_override_ws_hash", type_="unique")
        batch_op.drop_column("transaction_hash")

    # ADR-188 §D2 continua valendo — race-protection recriada sobre o v2.
    op.create_index(
        "uq_txov_active_rule",
        "transaction_overrides",
        ["workspace_id", "natural_key_hash"],
        unique=True,
        sqlite_where=sa.text("source = 'rule' AND deleted_at IS NULL"),
        postgresql_where=sa.text("source = 'rule' AND deleted_at IS NULL"),
    )
    # Unicidade ativa da identidade v2 (substitui a UK full-table legada;
    # órfãos têm natural_key_hash NULL e não colidem — semântica NULL do UNIQUE).
    # >> Confirmar com data-engineer no co-design do PR do drop. <<
    op.create_index(
        "uq_override_ws_natural_key_active",
        "transaction_overrides",
        ["workspace_id", "natural_key_hash"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.execute(_VIEW_TXOV_ACTIVE_V2_SQL)


def downgrade() -> None:
    raise RuntimeError(
        "ADR-282 Fase E e IRREVERSIVEL: a coluna transaction_hash e a funcao "
        "generate_transaction_hash foram removidas e a linha de override nao e "
        "re-hasheavel em v1 (o algoritmo legado nao existe mais). Recuperacao: "
        "restore PITR/snapshot pre-drop com perda — "
        "docs/reference/runbooks/override_legacy_drop.md §7."
    )
```

---

## Apêndice B — draft do sentinela G3 (copiar para o PR do drop)

> **Não é arquivo executável neste repo** — no PR do drop: criar
> `dev/check_no_legacy_override_hash.py` com este conteúdo e **wirar no
> `.pre-commit-config.yaml` nesse mesmo PR** (não antes — o sentinela falharia
> contra o código legado ainda vivo). Script puro stdlib, sem import de app
> (hook com import real quebra o job Lint — lição registrada).

```python
#!/usr/bin/env python3
"""G3 do ADR-282 Fase E: falha se o hash legado de override reaparecer.

Proibidos em backend/app/, pipeline/ e dev/:
- ``generate_transaction_hash`` — a funcao deletada na M2 (qualquer ocorrencia);
- ``uq_override_ws_hash`` / ``by_legacy_hash`` / ``legacy_hash`` — marcadores
  exclusivos do caminho v1 do dual-read;
- ``transaction_hash`` APENAS em backend/app/models/transaction_override.py
  (a coluna dropada). O token nu e legitimo no resto do codebase: identidade
  K4 v2 do pipeline (ADR-287) e nome de campo de wire opaco (ADR-282 §Wire/FE).

Runbook canonico: docs/reference/runbooks/override_legacy_drop.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = ("backend/app", "pipeline", "dev")

FORBIDDEN_EVERYWHERE = re.compile(
    r"generate_transaction_hash|uq_override_ws_hash|by_legacy_hash|\blegacy_hash\b"
)
MODEL_ONLY_FORBIDDEN = re.compile(r"\btransaction_hash\b")
MODEL_PATH = "backend/app/models/transaction_override.py"

ALLOWLIST = frozenset(
    {
        "dev/check_no_legacy_override_hash.py",  # este script
        # O runbook cita os tokens por definicao (fora dos SCAN_ROOTS, mas
        # listado para sobreviver a expansao futura do scan):
        "docs/reference/runbooks/override_legacy_drop.md",
    }
)


def _violations() -> list[str]:
    found: list[str] = []
    for root in SCAN_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in ALLOWLIST:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if FORBIDDEN_EVERYWHERE.search(line):
                    found.append(f"{rel}:{lineno}: {line.strip()}")
                elif rel == MODEL_PATH and MODEL_ONLY_FORBIDDEN.search(line):
                    found.append(f"{rel}:{lineno}: {line.strip()}")
    return found


def main() -> int:
    found = _violations()
    if found:
        print("G3 VIOLADO — hash legado de override reapareceu (ADR-282 Fase E):")
        print("\n".join(found))
        print(
            "\nO estado legado foi dropado de forma irreversivel; reintroduzir "
            "qualquer marcador acima recria a divida do terceiro hash. Ver "
            "docs/reference/runbooks/override_legacy_drop.md §2.5."
        )
        return 1
    print("check_no_legacy_override_hash: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
