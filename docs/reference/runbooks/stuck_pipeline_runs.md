---
id: runbook-stuck-pipeline-runs
type: runbook
title: "Runbook — Run de pipeline travado (órfão de dispatch + heartbeat)"
status: ativo
date: "2026-08-07"
relates_to:
  - "[[ADR-359]]"
  - "[[ADR-172]]"
  - "[[A40.l27]]"
tags:
  - type/runbook
  - area/backend
  - area/pipeline
  - area/ops
---

# Runbook — Run de pipeline travado

> **ADRs:** [[ADR-359]] (dispatch falha alto + compensação síncrona) · [[ADR-172]]
> (detector de heartbeat). **Lane:** [[A40.l27]].
> **Owner:** operador on-call. **Sem pager** — nada aqui é `CRITICAL` ([[ADR-359]] §7).
> **Sinal de entrada:** run parado na UI · `failure_reason` não-NULL em `pipeline_runs` ·
> `WARNING` do reaper (`mathoms.pipeline.undispatched_run_reaped` ou
> `mathoms.pipeline.stuck_run_detected`).
> **NÃO faça:** cancelar run com `celery_task_id` **não-NULL** antes de medir a fila (§1.2).
> Fila funda é trabalho legítimo esperando, e cancelar destrói o run do usuário.
> **Janela alvo:** diagnóstico ≤5min · ação ≤5min · sem downtime.

---

## Modelo mental (30 segundos)

Um run é **1 linha** em `pipeline_runs` + **1 task** no broker. "Travado" é sempre uma de
duas classes:

- **linha sem executor** — órfão de dispatch (`dispatch_failed`, `run_setup_failed`,
  `dispatch_unconfirmed`, ou o estado `resuming`);
- **linha com executor mudo** — `heartbeat_timeout`.

O discriminante entre elas é **`celery_task_id`** + a profundidade da fila, nunca o tempo
decorrido. Desde a [[ADR-359]] §4 o id é persistido **antes** do enqueue, então
`celery_task_id IS NULL` significa *"dispatch nunca foi tentado"* — e nunca *"enfileirado
esperando"*.

## 1. Diagnóstico (nesta ordem)

A ordem é **DB antes de broker** de propósito: a query não depende do broker, e é
exatamente quando o broker está fora que o órfão nasce.

### 1.1 Qual é o `failure_reason`?

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    SELECT id, status, failure_reason,
           celery_task_id IS NULL AS sem_dono,
           started_at, last_heartbeat_at, paused_at_stage
      FROM pipeline_runs
     WHERE workspace_id = '<WORKSPACE_ID>'
     ORDER BY started_at DESC
     LIMIT 5;"
```

`failure_reason` também chega pela API (`GET /pipeline/runs/{id}` → `failure_reason`) e
pelo card de falha da UI — a query é o caminho de menor dependência, não o único.

| Sintoma | Discriminante | Ação |
| --- | --- | --- |
| `status='failed'`, `failure_reason='dispatch_failed'` | o caller já compensou | §2 |
| `status='failed'`, `failure_reason='dispatch_unconfirmed'` | ninguém reivindicou | §3 |
| `status='failed'`, `failure_reason='run_setup_failed'` | falhou antes do enqueue | §4 |
| `status='failed'`, `failure_reason='heartbeat_timeout'` | executor emudeceu | §5 |
| `status='resuming'` parado | `sem_dono = true` | §6 |
| `status='pending'`/`'running'` parado, `sem_dono = false` | **pode ser legítimo** | §1.2 antes de agir |

Esta tabela é **roteamento** — não contém procedimento de propósito. Comando aqui criaria
uma segunda fonte de verdade para as §2–§6.

### 1.2 Bifurcação obrigatória: broker fora vs. worker vivo com fila funda

**Se §1.1 mostrou `sem_dono = true`, pule esta seção** — run sem dono nunca é caso de
esperar. Esta bifurcação existe para o caso `celery_task_id` **não-NULL**.

```bash
# 1. Broker vivo? (é o `redis-broker`, NÃO o `redis-cache`)
docker compose -f docker-compose.prod.yml exec redis-broker redis-cli PING

# 2. Worker vivo? `inspect ping` é control-channel broadcast, não task enfileirada —
#    responde MESMO com a fila saturada, e é por isso que serve como discriminante.
docker compose -f docker-compose.prod.yml exec worker \
  celery -A backend.app.worker inspect ping -t 5

# 3. Quem detém o run? O `celery_task_id` de §1.1 aparece aqui?
docker compose -f docker-compose.prod.yml exec worker \
  celery -A backend.app.worker inspect active
docker compose -f docker-compose.prod.yml exec worker \
  celery -A backend.app.worker inspect reserved

# 4. Profundidade da fila default (não há `task_routes`: tudo divide a fila `celery`)
docker compose -f docker-compose.prod.yml exec redis-broker redis-cli LLEN celery
```

**Leitura do resultado:**

| observação | conclusão | ação |
| --- | --- | --- |
| `PING` falha, ou `inspect` estoura o timeout | **broker fora** — falha do `inspect` **é** o sinal, não resultado inconclusivo | suba o broker; os órfãos se curam no próximo trigger ([[ADR-359]] §5) |
| `inspect ping` responde **e** o `celery_task_id` está em `active` | **executor vivo** | **NÃO cancele.** Espere |
| `inspect ping` responde, task_id em `reserved`, `LLEN` alto | **fila funda** | **NÃO cancele.** Espere |
| `inspect ping` responde e o task_id **não** aparece em `active` nem `reserved` | resíduo do §Resíduo conhecido | ação manual (§7) |

**Critério de "fila funda" que autoriza esperar:** `inspect ping` responde **E**
(`active` mostra 2 tasks — a concorrência é 2 — **ou** o task_id está em `reserved`) **E**
`celery_task_id` não-NULL.

**Teto honesto da espera: `task_time_limit = 3600`.** Passou de 1h com o task_id ainda em
`active`, **não é fila funda, é hang** — trate como §5.

## 2. `dispatch_failed` — a compensação síncrona já rodou

O broker recusou o enqueue e o **caller** reverteu o estado ([[ADR-359]] §2/§3); o usuário
recebeu 503. Não há órfão a curar: o run já está `failed` com o motivo nomeado.

- **O que se sabe:** o enqueue foi tentado e recusado.
- **O que não se sabe:** se a recusa foi pontual ou o broker está fora — só §1.2 responde.
- **Ação:** rode §1.2 item 1. Broker fora ⇒ suba-o. Broker vivo ⇒ falha pontual; o usuário
  pode disparar de novo.
- **NÃO faça:** relançar em loop antes do `PING`. Se o broker está fora, cada tentativa
  produz outro `dispatch_failed` e enterra o sinal.

**Rate ≥5 em 5min** neste motivo ⇒ trate como *broker degradado*, que é incidente de outra
natureza (e o único candidato futuro a page).

## 3. `dispatch_unconfirmed` — colhido pela varredura periódica

A varredura (`fin.detect_undispatched_runs`, [[A40.l27]]) achou um run pré-dispatch que
ninguém reivindicou e que nunca gravou `celery_task_id`.

- **Por que não é `dispatch_failed`:** ali sabemos *que* o enqueue falhou; aqui só sabemos
  que **não há dono**. Os dois nomes existem para o postmortem — colapsá-los destrói o
  sinal ([[ADR-359]] §3).
- **Causa provável:** morte do processo entre o INSERT e o dispatch. **Correlacione com a
  janela de deploy/restart** — é a causa correlata que a [[ADR-359]] §Consequências nomeia.
- **Falso-positivo é impossível por construção:** a pré-geração do task_id garante que run
  legitimamente enfileirado tem `celery_task_id` não-NULL e **nunca** é colhido.
- **Ação:** o run já está `failed`; o usuário pode disparar de novo. Rode §1.2 antes se
  houver **outro** run ativo no workspace.

> **Detecção não tem teto garantido.** Não há `task_routes`: a varredura compete com
> `pipeline.run` (`task_time_limit=3600`) na fila `celery` com `worker_concurrency=2`. Dois
> runs longos **famintam o reaper por até ~1h**, então "beat 300s + threshold 2min" é o
> melhor caso, não o pior. Sob fila funda, use a query de §1.1 como caminho manual: run
> `pending`/`resuming` com `sem_dono = true` e mais velho que 2min é o mesmo diagnóstico
> que a varredura faria.

## 4. `run_setup_failed` — falhou antes de o run começar

`_prepare_run_context` falhou (materialização de config, storage do tenant) **antes** de
qualquer tentativa de enqueue.

- **Não é broker.** Não gaste tempo no `PING`.
- **O `failure_reason` é rótulo, não causa:** o erro real está no log estruturado
  `mathoms.pipeline.dispatch_failed` com `failure_reason=run_setup_failed`.
- **Ação:** verifique a materialização de config do workspace e o volume de storage. Sem
  estado parcial de pipeline a limpar — o run nunca escreveu artefato.

## 5. `heartbeat_timeout` — executor perdeu o sinal

O detector da [[ADR-172]] flagou `status='running'` com heartbeat estale além de **15min**
(`MATHOMS_STUCK_RUN_THRESHOLD_MINUTES`). Esse threshold é maior que os 2min da varredura de
propósito: ali existe *stage genuinamente lento*, semântica que no pré-dispatch não existe.

**Passo de diagnóstico OBRIGATÓRIO antes de qualquer retry** — "just retry" é insuficiente,
e o motivo é mecânico:

1. Procure o `celery_task_id` em `active` (§1.2 item 3).
2. **Se aparecer:** o worker está vivo, só lento. Revogue com terminate e confirme a saída
   de `active`:
   ```bash
   docker compose -f docker-compose.prod.yml exec worker python -c "
   from backend.app.worker import celery_app
   celery_app.control.revoke('<CELERY_TASK_ID>', terminate=True)"
   ```
3. **Só então** relance. Se não apareceu em `active`, o retry é seguro direto.

**Por que o passo 2 não é opcional:** `_is_cancelled` aborta **somente** em
`status='cancelled'`, e `_finalize_run` só faz early-return em `cancelled`/`needs_review`.
Logo o flip do reaper para `failed` **não para** o worker vivo — ele **sobrescreve** o
`failed` de volta para `completed`/`partial_failure`. Pior: `failed` sai do índice parcial
`ux_pipeline_runs_ws_active`, então o "Reprocessar" do usuário cria um **segundo executor
vivo no mesmo workspace**, os dois escrevendo artefatos. O custo aceito pela [[ADR-172]]
("não detecta falsos-running") era **detecção**, não corrupção por retry cego.

## 6. Órfão em `resuming` (é status, não `failure_reason`)

`resume_pipeline_run` flippa `needs_review` → `resuming` e só então despacha. Morte do
processo nesse intervalo deixa a linha em `resuming`.

- **Sintoma:** a UI mostra `ActiveRunCard` girando indefinidamente (`resuming` está em
  `ACTIVE_STATUSES` do frontend). Antes da [[A40.l27]] o Cancelar respondia **409** e
  nenhuma superfície matava o run.
- **Diagnóstico:** `status='resuming'` **e** `sem_dono = true` na query de §1.1.
  `paused_at_stage` está **preservado** (a [[A40.l27]] parou de zerá-lo), então o ponto de
  retomada continua legível — use-o para orientar o usuário.
- **Ação:** a varredura o colhe sozinha (`dispatch_unconfirmed`); se precisar agir antes,
  **cancele pela UI ou pelo endpoint** — `resuming` passou a ser cancelável.
- **NÃO faça:** `UPDATE ... SET status='needs_review'` à mão. Ver §7.

## 7. Ações e seus limites

| Ação | Quando | Efeito | Irreversível? |
| --- | --- | --- | --- |
| **Esperar** | `inspect ping` responde **e** task_id em `active`/`reserved` (§1.2) | nenhum | não |
| **Subir o broker** | `PING` falha | órfãos se curam no próximo trigger | não |
| **Cancelar** (UI/endpoint) | `sem_dono = true`, ou `resuming` zumbi | `status='cancelled'`; libera o workspace | **sim** — o run não volta |
| **Revogar com terminate** | §5 passo 2, task_id em `active` | mata o executor vivo | **sim** — trabalho parcial perdido |
| **Re-disparar** | após o run estar terminal | novo run | não, mas re-custa LLM |
| **Reiniciar o worker** | worker não responde ao `inspect` mas o broker está vivo | tasks em voo morrem | **sim** para o que estava em voo |
| **`UPDATE` manual de `status`** | — | — | **proibido** — burla os UPDATEs condicionais que protegem contra corrida; use as superfícies |

Toda linha de ação pressupõe §1.2 executado. Cancelar sem medir a fila é o modo de falha
central deste runbook.

## 8. Verificação pós-ação

- A query de §1.1 mostra o run em estado **terminal** (`completed`/`failed`/`cancelled`) ou
  progredindo (`current_stage` mudando entre duas leituras).
- Ao re-disparar: um **único** run não-terminal no workspace. Dois é o cenário de escrita
  dupla de §5.
- **O que NÃO confirma nada:** ausência de erro novo no log. Reaper faminto (§3) e worker
  mudo produzem exatamente o mesmo silêncio.

## 9. Escalação e postmortem

Se o motivo não é nenhum dos 5 e o status não é `resuming`, **preserve antes de mexer**:
`run_id`, `workspace_id`, `status`, `failure_reason`, `celery_task_id`, `started_at`,
`last_heartbeat_at`, e a linha de log do reaper. É esse conjunto que a distinção
`dispatch_failed` ↔ `dispatch_unconfirmed` existe para comprar.

### Resíduo conhecido (sem detecção automática)

`celery_task_id` foi gravado e o processo morreu **dentro** do `apply_async` — o publish
nunca chegou ao broker. Esse run é invisível às três portas: ao sweep (exige NULL), ao
detector da [[ADR-172]] (exige `running`) e à cura síncrona. É o preço declarado da
[[ADR-359]] §4; auto-detectá-lo exigiria consultar o broker de dentro do reaper, o que
§Consequências rejeitou.

**Identificação:** `celery_task_id` não-NULL, `status` pré-dispatch, e o task_id **não**
aparece em `active` nem em `reserved` com o broker vivo. **Fechamento:** cancele pela UI e
oriente o re-disparo.

## O que este runbook NÃO cobre

- Rollback de deploy do pipeline → [pipeline_rollback.md](pipeline_rollback.md)
- Disaster recovery → [disaster_recovery.md](disaster_recovery.md)
- Reset destrutivo de pipeline →
  `backend/app/services/internal_ops/pipeline_reset.py::reset_workspace_from_stage`
- Broker degradado como incidente próprio (rate alto de `dispatch_failed`)

## Referências

- [[ADR-359]] — dispatch falha alto; compensar é reverter; vocabulário de `failure_reason`
- [[ADR-172]] — detector de heartbeat via Celery Beat
- [[A40.l27]] — varredura de órfão pré-dispatch, cancel de `resuming`, read path
- `backend/app/tasks/periodic_tasks.py` — `detect_stuck_runs`, `detect_undispatched_runs`
- `backend/app/services/pipeline/dispatch_contract.py` — estados pré-dispatch + threshold
- `backend/app/services/pipeline/pipeline_service.py` — `cancel_pipeline_run`, resume
- [runbooks/automerge_train.md](automerge_train.md) — forma deste runbook (variante incidente)
