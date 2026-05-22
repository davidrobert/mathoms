# Runbook — Recompute E4 após dedup K4 (ADR-255)

> **ADR:** [[ADR-255]] — Dedup K4 cross-document no pipeline E3→E4.
> **Owner:** Engenharia (dev on-call) ou operador interno via console.
> **Janela alvo:** ~5min audit + ~2min recompute por run.

## Quando usar

1. **Diagnóstico**: usuário reporta receita/despesa "estranhamente alta" no relatório (tipicamente 2-3× o real). Sinal típico: `_total` mensal não bate com o que ele soma manualmente dos extratos.
2. **Após merge** da Camada A (`cash_flow_builder` dedup K4): workspaces antigos têm `cash_flow` no DB inflado pelo bug. Camada A só dedupa **runs novos**; runs antigos precisam de recompute.
3. **Após detecção em massa**: rodar `audit_duplicate_transactions.py` antes pra identificar workspaces afetados.

## Procedimento

### 1. Identificar workspaces afetados (audit)

```bash
MATHOMS_FERNET_KEY="<chave do .env>" \
MATHOMS_DATABASE_URL="postgresql+psycopg2://..." \
  python3 dev/audit_duplicate_transactions.py \
  --output _scratch/dedup-audit-$(date +%F).json
```

Output JSON com schema:

```json
{
  "affected_count": 8,
  "affected": [
    {
      "workspace_id": "1b9f2cf5-...",
      "pipeline_run_id": "be938a50-...",
      "dup_unique_txs": 129,
      "total_extra_copies": 140,
      "sample": [
        {"data": "...", "cents": ..., "descricao_lower": "...", "keys": ["E3-key-1", "E3-key-2"]}
      ]
    }
  ]
}
```

- `dup_unique_txs`: quantas transações distintas têm cópias cross-document.
- `total_extra_copies`: soma de cópias removíveis (= total a colapsar pelo dedup).
- `sample`: até 3 transações mais duplicadas, com keys dos artefatos E3 envolvidos.

### 2. Dry-run recompute (validação antes de aplicar)

```bash
MATHOMS_FERNET_KEY="<chave>" \
  python3 dev/recompute_e4_for_run.py \
  --workspace-id <uuid> --run-id <uuid> \
  --db-url "postgresql+psycopg2://..."
```

Sem `--apply`, **NÃO grava** — só roda o adapter com Camada A ativa e reporta:

```json
{
  "workspace_id": "...",
  "run_id": "...",
  "receitas_total": 994,
  "despesas_total": 3996,
  "transferencias_total": 0,
  "dups_collapsed": 340,
  "dups_review": 51,
  "artifacts_written": [],
  "dry_run": true
}
```

Confirme:
- `dups_collapsed` > 0 (esperado se workspace estava no audit output).
- `dups_review` ≤ `dups_collapsed`; review entries são casos de valor ≥ R$ 10k ou tipo_conta vazio.
- `receitas_total`/`despesas_total` consistentes com o que o user espera (ordem de grandeza).

### 3. Apply (regrava artefatos E4 no DB)

```bash
MATHOMS_FERNET_KEY="<chave>" \
  python3 dev/recompute_e4_for_run.py \
  --workspace-id <uuid> --run-id <uuid> \
  --db-url "postgresql+psycopg2://..." \
  --apply
```

`--apply` faz `session.commit()` após regravar. Idempotente: rodar 2× produz o mesmo output.

### 4. Validar relatório do user

Abrir `/reports/<id>` do user e conferir:
- Card "Receita vs Despesa — Mês a Mês" mostra `_total` mensal correto.
- Tooltip de cada mês não tem mais o sintoma de 2-3× inflado.
- KPIs do top-card (taxa de poupança, despesa média) recalculados.

## Out-of-scope (downstream stale)

`recompute_e4_for_run.py` **só toca E4**. Stages downstream (E5 `analise_financeira`, parecer planejador E6) continuam com payloads gerados antes do recompute — ficam **stale** (KPIs E5 calculados sobre cash_flow inflado, parecer LLM raciocinando sobre KPIs errados).

Opções para regerar downstream:
1. **Reset destrutivo via console interno** (`reset_workspace_from_stage analyze_finances`): apaga E5 + E6 + parecer; próximo run regenera (custo LLM ~$0.50-2.00 por workspace).
2. **Esperar próximo run completo** quando user atualiza algum config ou upload novo (regen on-demand). Mais lento mas zero custo extra agora.
3. **Endpoint admin futuro** (`POST /ops/recompute_downstream/{workspace_id}`) — não escopo deste runbook.

## Verificação pós-fix

```bash
# Confirma que a lista de afetados encolheu:
MATHOMS_FERNET_KEY="..." \
  python3 dev/audit_duplicate_transactions.py \
  --output _scratch/dedup-audit-pos.json
```

Esperado: `affected_count` reduzido em pelo menos 1 (o workspace recomputado some da lista — runs novos passam por dedup automaticamente).

> **Atenção**: o audit lê **E3** (input do E4). Mesmo após recompute do E4, os E3 continuam contendo as transações duplicadas — o audit ainda vai listar o run. O sinal de "fix aplicado" é o output do `recompute_e4_for_run.py` ter `dups_collapsed=0` quando re-executado.

## Rollback

Camada A é **idempotente e determinística**. Não há rollback necessário — re-rodar o recompute produz exatamente o mesmo output. Se algum payload E4 ficou inconsistente por bug residual:

```bash
# Reset destrutivo + re-run completo:
# (via console interno ou backend/app/services/internal_ops/pipeline_reset.py)
reset_workspace_from_stage(workspace_id, "categorize_transactions")
# depois disparar novo pipeline run
```

Custo: re-roda E4 + tudo downstream (custo LLM completo do workspace).
