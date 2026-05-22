---
id: ADR-255
type: adr
title: "Dedup de transações cross-document no pipeline E3→E4 (chave determinística + needs_review)"
status: Proposto
phase: A17.tx-dedup-cross-doc
date: "2026-05-22"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-093]]"
  - "[[ADR-212]]"
  - "[[ADR-186]]"
  - "[[ADR-228]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 255"
  - "Tx dedup cross-doc"
  - "Cash flow dedup"
tags:
  - area/pipeline
  - area/domain
  - status/proposto
  - type/adr
---

# ADR-255 — Dedup de transações cross-document no pipeline E3→E4

**Status:** Proposto • **Data:** 2026-05-22 • **Relaciona** [[ADR-097]] (fatura sintetizada D2), [[ADR-093]] (stage names), [[ADR-212]] (DBArtifactStore), [[ADR-186]] (learned rules), [[ADR-228]] (dedup de documento upstream).

## Contexto

Bug reportado em prod no relatório `/reports/9b31d739-...`, card "Receita vs Despesa — Mês a Mês". Em mar/26 o tooltip mostra "Arvo (David - PJ): R$ 141.626" — valor correto R$ 47.208,77. **Razão exata 3×**.

Investigação local confirmou: a transação `Pix recebido de ARVO SAUDE LTDA` de **2026-03-30, R$ 47.208,77** está em **3 artefatos `pipeline_artifacts` (stage=E3) do mesmo `pipeline_run_id`**, com origens distintas:

| `artifact_key` | Banco no payload | Documentos de origem (campo `fontes`) |
|---|---|---|
| `c6bank_extratoconta_BRL_202512_202604` | C6Bank | 1 CSV (`d7f8c691ab80…`) + 1 fonte (`f4bf6653a3fd…`) |
| `_extrato_BRL_202504_202504` | "" (não identificado) | 2 PDFs C6 "extrato-da-sua-conta-{ULID}.pdf" (`2554457c5e1e…`, `87cbeff3a899…`) |
| `_extrato_BRL_202505_202505` | "" (não identificado) | 2 PDFs C6 "extrato-da-sua-conta-{ULID}.pdf" (`4e11dead46e8…`, `87c77fc9bf58…`) |

Os 3 artefatos E3 são da **mesma conta C6 Bank** do mesmo titular: o CSV `c6bank_extratoconta_BRL_202512_202604` foi corretamente identificado pelo E0, mas os 4 PDFs `extrato-da-sua-conta-{ULID}.pdf` (snapshots cumulativos do app C6 baixados em datas diferentes) **não foram identificados como C6** — `bank_code=""`. Cada PDF cobre ~13 meses retroativos, com sobreposição substancial entre snapshots. O dedup exato (`content_hash`) não dispara (bits diferentes — ULID no nome + signature/timestamp interno mudam), e o dedup fuzzy `(doc_type, bank_code, period)` falha porque `bank_code=""` quebra o match com o CSV C6 explícito e o `period` extraído do filename é enganoso (declarado `202505_202505` mas conteúdo cobre `202505→202605`).

### Cadeia técnica

1. **E0** (`backend/app/services/document_classification.py`) classificou como `bank_statement` com `bank_code=""` e `period` derivado do nome — sem detectar overlap de conteúdo.
2. **E2** extraiu transações para cada PDF/CSV. Sem dedup cross-document.
3. **E3** (`pipeline/domain/services/reconciliation_service.py:_dedup` linha 145-155) deduplica **intra-statement** (loop sobre `stmt.transactions` por statement). **Não há dedup cross-statement.**
4. **E4** (`pipeline/domain/services/cash_flow_builder.py::build_fluxo_mensal` linha 209-268): `receita_por_mes[mes][origem] += t.valor` direto, **sem `seen_transactions: set` nem hash**. Idem `build_despesas_unified` e `build_receitas_unified`.
5. `ClassifiedTransaction` (`pipeline/domain/services/transaction_classifier.py:177`) é `@dataclass(frozen=True)` com `kind, data, descricao, valor, banco, moeda, tipo_conta, titular, tipo, categoria, origem, learned_rule_id, categorization_origin` — **não tem `transaction_id` nem `source_doc_id`**, impossibilitando dedup a posteriori sem fabricar chave.

### Impactos

- **Receitas/despesas por mês infladas** em qualquer workspace com documentos sobrepostos (extratos cumulativos, re-uploads que escapam de fuzzy dedup, dois bancos exportando o mesmo PIX em conta espelhada).
- **KPIs derivados errados**: taxa de poupança, despesa média mensal, fluxo de caixa, gráficos por origem, alocação-alvo (denominador inflado), score AUVP.
- **Parecer LLM (E6)** raciocina sobre KPIs errados — pode recomendar reserva/PGBL com base em receita fictícia.
- **Override de classificação** ([[ADR-186]]) é por `(descricao, banco)` e funciona, mas dedup posterior pode reverter override aparente.

## Decisão

Introduzir **identidade determinística por transação** propagada do produtor (E3) ao consumidor (E4 agregadores), com camada defensiva imediata no agregador e camada sistêmica no boundary de domínio. Política de **dedup silente** para transações materialmente menores e **`needs_review`** para transações materiais (valor ≥ R$ 10.000) ou com chave incompleta.

### Camada A — Defesa imediata no agregador (PR1, hot-fix)

Em `pipeline/domain/services/cash_flow_builder.py`:

- `build_fluxo_mensal`, `build_receitas_unified`, `build_despesas_unified` mantêm `seen: dict[str, ClassifiedTransaction]` indexado por **hash inline** computado em-fluxo.
- Chave do hash (K4):
  ```python
  key = (
      data,                       # YYYY-MM-DD
      banco_norm,                 # lowercased, sem acento, sem espaço
      titular_norm,               # lowercased, sem acento, sem espaço
      tipo_conta_norm,            # lowercased, sem espaço
      int(round(valor * 100)),    # cents int (evita float drift)
      descricao_norm,             # lowercase + strip + collapse whitespace
                                  # PRESERVA: dígitos, tokens "N/M" (parcela 3/12),
                                  # nomes próprios. NÃO remove acento.
  )
  transaction_hash = sha256("|".join(map(str, key)).encode()).hexdigest()[:16]
  ```
- Quando colisão: **mantém a primeira ocorrência** (estável por ordem do `list_keys` E3, que é alfabética por `artifact_key`). Tie-break **não** aleatório.
- Helpers em `pipeline/domain/services/_tx_identity.py` (novo módulo): `normalize_banco`, `normalize_titular`, `normalize_tipo_conta`, `normalize_descricao`, `compute_transaction_hash(tx_or_dict)`. Reutilizáveis em E3 (geração futura) e E4 (consumo atual).

### Política needs_review (resposta ao financial-planner)

Quando o agregador detecta colisão de hash **e** qualquer das condições abaixo é verdadeira, **não dedupa silenciosamente** — registra em `CategorizationResult.dedup_review` e mantém apenas uma instância no agregado (para não inflar), mas marca a entry com `_needs_review = true` e expõe contexto para a UI/console:

| Condição | Razão |
|---|---|
| `abs(valor) ≥ R$ 10.000` | Materialidade — falso-positivo em transação grande custa mais que fricção. |
| `tipo_conta` ausente em qualquer candidato | Chave incompleta — não decidir sozinho. |
| `source_doc_id` divergente e origens conflitantes (extrato + IRPF ou extrato + informe) | Origens declaradas diferentes — usuário precisa confirmar qual é canônica. |

Default: dedup silente quando todos os candidatos vêm do mesmo `(banco, titular, tipo_conta)` e valor < R$ 10k — é overlap de upload clássico.

### Camada B — Identidade no boundary de domínio (PR2, sistêmica)

Adicionar em `ClassifiedTransaction`:

```python
source_doc_id: str | None = None      # UUID do documento de origem (quando rastreável)
transaction_hash: str | None = None   # sha256[:16] determinístico
```

Geração no produtor: `pipeline/domain/services/e3_serialization.py::serialize_account` propaga `arquivo_origem` (`documents.id` ou hash de filename) para `source_doc_id` por transação, e computa `transaction_hash` a partir dos mesmos helpers de `_tx_identity.py`.

Builders preferem `tx.transaction_hash` quando presente; **fallback** para hash inline computado (compat com payloads pré-PR2 e com runs antigos lidos do DB). Sem flip-day forçado.

### Schema E4 (aditivo, sem version major)

`config/schemas/e4_unified.schema.json` — `$defs` novo:

```json
"$defs": {
  "transactionIdentity": {
    "type": "object",
    "properties": {
      "source_doc_id": {"type": ["string", "null"]},
      "transaction_hash": {"type": ["string", "null"], "pattern": "^[a-f0-9]{16}$"}
    }
  }
}
```

Items em `dados.<categoria>[]` e `data.transacoes[]` ganham os campos opcionais (sem `required`). Payloads pré-PR2 continuam válidos em strict mode — confirmar via teste explícito.

### Schema E3 (sem mudança)

`transacoes[].arquivo_origem` já existe via `additionalProperties: true` no items. Propagação reusa o campo; `source_doc_id` em E4 deriva dele.

### Fatura sintetizada (ADR-097 D2)

Confirmado no código que `statement_preprocessor` **não** cria transação contábil duplicada (só ajusta `periodo`). Dedup pode ser cego ao conceito — não há linha contábil paralela a preservar. **Adicionar teste de regressão explícito** caso o conceito ressurja: tx sintetizada vs tx original do mesmo dia/valor — devem coexistir SE `source_doc_id` diferente ou `tipo_conta` diferente; mesmo hash colapsa.

### Camada de defesa em profundidade

Camada A **permanece após** Camada B. Se geração de hash em E3 quebrar por bug futuro de normalização (ex.: parser muda casing de `banco`), os builders ainda colapsam por hash inline. Custo: ~10 linhas de safety net.

### Backfill (opção c — recompute E4 only)

Runs históricos em `pipeline_artifacts` têm cash_flow inflado. Estratégia:

1. **Audit script** (`dev/audit_duplicate_transactions.py`): itera `pipeline_artifacts` stage=E3, decryptar com `_maybe_decrypt`, contar `(data, valor, descricao_lower)` em múltiplos `artifact_keys` do mesmo workspace; output: `workspace_id | n_dups | sample`. Roda em ~5min para o universo todo.
2. **Recompute E4** (`backend/app/services/internal_ops/recompute_e4.py`): recomputa só stage E4 a partir do E3 existente — determinístico, **sem custo LLM**. Marca `pipeline_runs.stale = true` em E5/E6/parecer; regen on-demand quando workspace abre report. Idempotente, revisitável.
3. RTO ~30min para todos workspaces afetados.

## Consequências

**Positivas:**

- Receita Arvo (e similares) aparece 1× no card mensal — valor correto.
- KPIs derivados (taxa de poupança, despesa média, alocação-alvo, parecer LLM) corretos.
- `transaction_hash` habilita features futuras: chat sobre relatório com referência por linha, override por transação ([[ADR-186]] §D6), audit trail "qual doc trouxe essa tx".
- Defesa em profundidade — bug em uma camada não revira o sintoma.
- Backfill barato (sem LLM); regen on-demand distribui custo de E5/E6.

**Negativas / trade-offs aceitos:**

- **Falso-positivo possível** (dedup demais → some receita real): casal com mesma conta no mesmo banco, ambos recebendo PIX idêntico no mesmo dia. K4 inclui `titular` + `tipo_conta` para mitigar; valor ≥ R$ 10k vira `needs_review`. Custo de FP > custo de FN (estado atual).
- **`descricao_norm` exige preservação cuidadosa** de tokens N/M e nomes próprios — bug na normalização pode dropar tx legítimas. Mitigação: teste explícito com parcelamentos.
- **Schema E4 aditivo** cria contrato implícito para consumers futuros (cenários de estresse, parecer planejador) — deve ler `transaction_hash` quando presente, senão computar.
- **Workspaces antigos** precisam recompute E4 — automático on-demand; sem migration destrutiva.

## Observabilidade

Log JSON estruturado no agregador (sem PII — não logar `descricao` nem `valor` exato):

```json
{
  "logger": "mathoms.pipeline.dedup",
  "stage": "categorize_transactions",
  "workspace_id": "<uuid>",
  "pipeline_run_id": "<uuid>",
  "dups_collapsed": 14,
  "dups_review": 2,
  "sample_keys": ["a1b2c3d4e5f6g7h8", "..."]
}
```

`CategorizationResult.dedup_report`:
```python
@dataclass(frozen=True)
class DedupReport:
    collapsed_count: int
    review_count: int
    review_entries: tuple[DedupReviewEntry, ...]  # data, banco_norm, valor_cents, hash, source_doc_ids, reason
```

Surface no console interno (`/ops/workspaces/<id>/pipeline`) para o operador investigar quais transações foram colapsadas/marcadas.

## Critério de aceite

1. **Cenário Arvo** — Workspace `1b9f2cf5-…` (report `9b31d739-…`) recompute E4 → `receita_por_mes["2026-03"]["Arvo (David - PJ)"] = 47208.77` (não 141626.31). Outras linhas do tooltip recompõem.
2. **Hash determinístico** — Mesma transação dictada 2× com `banco="C6Bank"` vs `banco="C6 Bank"` produz mesmo `transaction_hash` (normalização robusta).
3. **K4 conservadora** — Casal recebendo PIX idêntico no mesmo dia em contas distintas do **mesmo** banco mas com `titular_key` diferente → 2 linhas preservadas. Goldens novos.
4. **needs_review acima de R$ 10k** — Tx ≥ R$ 10k com colisão → dedup_report.review_entries não-vazio; agregador mantém 1 instância mas marca entry com `_needs_review=true`.
5. **Transferência intra-titular** — mesmo titular, mesmo banco, CC→poupança no mesmo dia/valor → 2 linhas preservadas (tipo_conta diferente).
6. **Parcelamento** — `"PARC 3/12"` e `"PARC 4/12"` mesmo dia/valor → 2 linhas (descricao_norm preserva token N/M).
7. **Schema aditivo** — `validate_dict(payload_e4_pre_pr2, "e4_unified.schema.json")` em strict mode continua válido (payload sem `transaction_hash` aceito).
8. **Goldens E3/E4** (`tests/test_e{3,4}_golden_execution.py`) verdes após regen.
9. **Backfill** — `recompute_e4 --workspace-id <id>` corrige cash_flow sem chamar LLM; `pipeline_runs.stale=true` em E5/E6/parecer; regen on-demand quando user abre report.
10. **Telemetria** — log JSON `mathoms.pipeline.dedup` emitido com counts (sem PII).
11. **Defesa em profundidade** — Camada A roda mesmo com `transaction_hash` presente em todas as txs (idempotente).

## Alternativas consideradas

- **Apenas Camada A defensiva** (rejeitado): patcha 3 agregadores hoje; futuros consumers (cenários de estresse, parecer, chat sobre relatório) reincidirão. Sem audit trail por transação. Cria dívida arquitetural.
- **Apenas Camada B sistêmica** (rejeitado): ADR + schema + goldens + backfill leva ~2-3 dias; sangra valor em prod no intervalo. Camada A defensiva em horas destrava o caso.
- **Dedup em E3 reconciler** (rejeitado para o produtor de hash, considerado para dedup): atravessa boundary intra-statement do reconciler ([[ADR-097]]) que tem invariantes próprios (saldo continuity). Gerar hash em E3 é OK (boundary natural — antes do fan-out E4) mas dedup fica em E4 (perto do consumo).
- **Fingerprint só por `(data, valor)` + LLM tie-break** (rejeitado): introduz dependência LLM em stage determinístico; quebra goldens estáveis; custo recorrente alto.
- **Marcar duplicata só na UI** (rejeitado): backend continua inflado; KPIs/parecer/alocação-alvo enganados; UI seria band-aid.
- **Soma N×valor com divisão por N** (rejeitado): introduz heurística não-determinística e diverge de fonte primária (extrato bancário oficial).
- **Bloquear upload duplicado upstream com fuzzy dedup por conteúdo** (futuro, complementar): exige E2 rodar antes do dedup decidir; é caminho válido para track separado ([[ADR-228]] estendida) mas não substitui a defesa em E4 — workspaces com baseline já corrompido continuam.

## Próximos passos

- **PR1 (este escopo — hot-fix)**: helper `pipeline/domain/services/_tx_identity.py` + dedup K4 + `DedupReport` em `cash_flow_builder` × 3 funções + log JSON + goldens E4 regenerados + teste cross-doc (`tests/test_e4_cross_doc_dedup.py`). **Sem schema bump.** Camada A ship hoje.
- **PR2 (sistêmico)**: campos `source_doc_id` + `transaction_hash` em `ClassifiedTransaction`; geração em `e3_serialization`; schema E4 aditivo; builders preferem field, fallback computed. Goldens regeneram. Teste explícito de aditividade do schema.
- **PR3 (backfill)**: `dev/audit_duplicate_transactions.py` + `backend/app/services/internal_ops/recompute_e4.py`. Marca `pipeline_runs.stale=true`. Runbook em `docs/reference/runbooks/`.
- **Follow-up tracked separadamente**: detecção upstream de overlap de conteúdo em E0/E2 (estender [[ADR-228]]) — preventiva, não substitui defesa em E4.
- **Follow-up tracked separadamente**: melhorar classificador de banco em E0 para PDFs C6 "extrato-da-sua-conta-{ULID}" (snapshots cumulativos do app C6 PJ) — reduz casos de `bank_code=""` que escapam de fuzzy dedup. Causa raiz upstream: o parser de E0 não reconhece o cabeçalho/layout do PDF "extrato completo" do C6.
