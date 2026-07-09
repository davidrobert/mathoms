# Runbook — Backfill heurístico de Suggestions pré-ADR-290

> **ADR:** [[ADR-290]] — supersede-per-run + thesis_key (F4 do
> [[PLAN-suggestion-lifecycle]]).
> **Owner:** Engenharia (operador interno).
> **Janela alvo:** ~5min por workspace (dry-run + revisão + apply).

## Quando usar

One-shot por workspace com acúmulo de Suggestions `Pendente` do parecer
anteriores a F1 (ADR-290). Linhas antigas não têm `thesis_key` (campos-fonte
não persistidos) → o supersede automático de runs novos **não as alcança**.
Caso de origem: dogfood com 158 pendentes em 12 runs.

## Pré-condições

1. F1 (ADR-290) mergeada e migration `adr290supersede` aplicada
   (`alembic current` ≥ `adr290supersede`).
2. **Sem pipeline ativo no workspace** durante a janela (o serviço ignora
   pendentes com `created_at` posterior ao início como defesa extra, mas a
   janela limpa evita relatório confuso).
3. `workspace_id` em mãos — o serviço **não aceita** "todos os workspaces".

## Dry-run (default)

```python
# shell do backend (mesmo venv/env do worker):
import asyncio
from backend.app.core.database import async_session as AsyncSessionLocal
from backend.app.services.internal_ops.suggestion_backfill import (
    backfill_supersede_pending_suggestions,
)

async def main():
    async with AsyncSessionLocal() as db:
        r = await backfill_supersede_pending_suggestions(
            db, workspace_id="<UUID>", actor="<seu-id>", apply=False
        )
        print(r.details["pendentes"], "pendentes,", r.details["groups"], "grupos,",
              r.details["superseded_planned"], "a superseder")
        for g in r.details["report"]:
            print(g["section_id"], "|", g["titulo_normalizado"][:60],
                  "| mantém", g["mantem"]["id"], "| supersede", g["supersede_count"])

asyncio.run(main())
```

**Revise o relatório com um humano antes do apply** — o agrupamento é
heurístico `(section_id, título normalizado)`; título re-redigido pelo LLM
entre runs **não** agrupa (fica Pendente; o supersede automático de runs
pós-F1 resolve daí em diante).

## Modo `latest_batch` ("último parecer vence")

Quando o dry-run heurístico encontra **0 grupos** (LLM re-redigiu títulos em
todos os runs — caso dogfood 2026-06-12, 165 pendentes → 0 duplicatas), use
`mode="latest_batch"`: mantém o burst mais recente de pendentes (janela de
1h cobre o persist de um run) e supersede todas as anteriores — semântica
ADR-290 ("inbox converge para o parecer mais recente"). Aprovado pelo owner
em 2026-06-12. Mesma chamada com `mode="latest_batch"`; o dry-run retorna
`kept_ids` + `cutoff` para revisão.

## Apply

Mesmo bloco com `apply=True` + `await db.commit()` após o resultado `ok`.
Audit entry `suggestions.backfill_supersede` é gravada em
`logs/internal_ops_audit.log`.

## Rollback

`Superseded` é terminal **soft** — nenhum dado é apagado. Re-promover por SQL:

```sql
UPDATE suggestions
SET status = 'Pendente', superseded_at = NULL
WHERE workspace_id = '<UUID>'
  AND status = 'Superseded'
  AND superseded_by_run_id IS NULL;  -- só linhas do backfill (runs têm run_id)
```

## Verificação

```sql
SELECT status, COUNT(*) FROM suggestions
WHERE workspace_id = '<UUID>' AND kind = 'parecer_planejador'
GROUP BY status;
```

Aceite F4 (dogfood `1b9f2cf5-6a19-4d2a-af7a-79d739ddeff6`): `Pendente`
acionáveis (danger+warning) ≤ 14 após o apply.
