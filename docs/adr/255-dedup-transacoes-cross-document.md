---
id: ADR-255
type: adr
title: "Dedup de transações cross-document no pipeline E3→E4 (chave determinística + needs_review)"
status: Decidido
phase: A17.tx-dedup-cross-doc
date: "2026-05-22"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-093]]"
  - "[[ADR-212]]"
  - "[[ADR-186]]"
  - "[[ADR-228]]"
  - "[[ADR-282]]"
  - "[[ADR-287]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 255"
  - "Tx dedup cross-doc"
  - "Cash flow dedup"
tags:
  - area/pipeline
  - area/domain
  - status/decidido
  - type/adr
---

# ADR-255 — Dedup de transações cross-document no pipeline E3→E4

**Status:** Decidido • **Data:** 2026-05-22 • **Relaciona** [[ADR-097]] (fatura sintetizada D2), [[ADR-093]] (stage names), [[ADR-212]] (DBArtifactStore), [[ADR-186]] (learned rules), [[ADR-228]] (dedup de documento upstream).

## Contexto

Bug reportado em prod no relatório `/reports/9b31d739-...`, card "Receita vs Despesa — Mês a Mês". Em mar/26 o tooltip mostra "Empregador Exemplo (Titular - PJ): R$ 150.000" — valor correto R$ 50.000,00. **Razão exata 3×**.

Investigação local confirmou: a transação `Pix recebido de EMPREGADOR EXEMPLO LTDA` de **2026-03-30, R$ 50.000,00** está em **3 artefatos `pipeline_artifacts` (stage=E3) do mesmo `pipeline_run_id`**, com origens distintas:

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
      descricao_norm,             # lowercase + strip + collapse whitespace +
                                  # strip de sufixos de roteamento PIX (ver
                                  # §"Sufixos de roteamento" abaixo).
                                  # PRESERVA: dígitos, tokens "N/M" (parcela 3/12),
                                  # nomes próprios. NÃO remove acento.
  )
  transaction_hash = sha256("|".join(map(str, key)).encode()).hexdigest()[:16]
  ```
- Quando colisão: **mantém a primeira ocorrência** (estável por ordem do `list_keys` E3, que é alfabética por `artifact_key`). Tie-break **não** aleatório.
- Helpers em `pipeline/domain/services/_tx_identity.py` (novo módulo): `normalize_banco`, `normalize_titular`, `normalize_tipo_conta`, `normalize_descricao`, `compute_transaction_hash(tx_or_dict)`. Reutilizáveis em E3 (geração futura) e E4 (consumo atual).
  > **Nota (audit r6, 2026-07-03):** `compute_transaction_hash` (chave v1)
  > foi substituído por `compute_identity_hash(..., natural_key_v2)` em
  > `pipeline/domain/services/_tx_identity.py`, com as flags v2 ligadas
  > (`dedup_natural_key_v2=True` em `e4_categorizer_adapter.py`) — ver
  > [[ADR-282]] (natural key v2) e [[ADR-287]] (flip do dedup E4).

### Sufixos de roteamento PIX (iteração 2 — refinamento de Camada A)

**Caso real observado em produção** (workspace `1b9f2cf5-…`, report `ffde7f63-…`, run `f66b519e-…`, 2026-05-23): após mergear o PR1 (Camada A), o cenário do empregador PJ **continuou inflado em ~R$ 200.000 nos 12M** (≈ 32% acima do real) porque o C6Bank emite a **mesma transação PIX em PDFs diferentes** com sufixos de descrição variantes. Exemplos coletados:

| Data | Valor | Descrição extrato A | Descrição extrato B |
|---|---|---|---|
| 2025-10-30 | R$ 50.000,00 | `"Pix recebido de EMPREGADOR EXEMPLO LTDA — Salários PJ"` | `"Pix recebido de EMPREGADOR EXEMPLO LTDA"` |
| 2025-11-27 | R$ 8.000,00 | `"Pix recebido de EMPREGADOR EXEMPLO LTDA — 13 Salário"` | `"Pix recebido de EMPREGADOR EXEMPLO LTDA"` |
| 2025-11-28 | R$ 45.000,00 | `"Pix recebido de EMPREGADOR EXEMPLO LTDA — Salários PJ"` | `"Pix recebido de EMPREGADOR EXEMPLO LTDA"` |
| 2026-02-27 | R$ 50.000,00 | `"Pix recebido de EMPREGADOR EXEMPLO LTDA"` | `"Pix recebido de EMPREGADOR EXEMPLO LTDA — Salários PJ"` |
| 2026-03-30 | R$ 50.000,00 | `"Pix recebido de EMPREGADOR EXEMPLO LTDA"` | `"Pix recebido de EMPREGADOR EXEMPLO LTDA — Salários PJ"` |

Em despesas, padrão equivalente:

| Padrão | Variante A | Variante B |
|---|---|---|
| DARF | `"TRIBUTOS FEDERAIS DARF NUMERADO"` | `"TRIBUTOS FEDERAIS DARF NUMERADO SIMPLES NACIONAL"` |
| PIX enviado | `"Pix enviado para X — TRANSF ENVIADA PIX"` | `"Pix enviado para X"` |
| Boleto | `"Y — Boleto"` | `"Y"` |

`descricao_norm` (lowercase + whitespace collapse apenas) produz hashes diferentes → dedup não dispara → contado 2×–3× quando há extratos sobrepostos. Inflação total medida em produção: **R$ 366k em receitas (12M) + R$ 92k em despesas (40M)**.

**Refinamento:** `normalize_descricao` estende para strip de sufixos **conhecidos** quando aparecem após separador ` — ` (em-dash com espaços) ou ` - ` (hífen com espaços). Whitelist conservadora (lista finita, vive em `_tx_identity.py`):

```python
_ROUTING_SUFFIX_PATTERNS = (
    r"\s+[—-]\s+TRANSF\s+ENVIADA\s+PIX$",      # C6 — débito PIX
    r"\s+[—-]\s+Sal[áa]rios?\s+PJ$",            # C6 — receita PJ
    r"\s+[—-]\s+13\s+Sal[áa]rio$",              # C6 — décimo terceiro
    r"\s+[—-]\s+Boleto$",                       # C6 — pagamento boleto
    r"\s+[—-]\s+NFS?\s+\d+$",                   # C6 — NF/NFS numerada
    r"\s+SIMPLES\s+NACIONAL$",                  # C6 — DARF detalhada
)
```

O strip aplica **antes** do lowercase, sobre o `value.strip()` original (preserva ordem: dedup→lowercase→collapse). Resultado: `"Pix recebido de EMPREGADOR EXEMPLO LTDA — Salários PJ".strip_routing() == "Pix recebido de EMPREGADOR EXEMPLO LTDA"`.

**Guard contra falsos-positivos:** o strip **só remove o segmento final após ` — `/` - `**. Descrições com parcela (`"PARC 3/12"`) ou nome próprio composto (`"Maria de Fátima"`) não sofrem porque não casam com padrões da whitelist. Teste explícito de regressão garante.

**Por que whitelist, não regex genérica `s/ — .*$//`**: variantes legítimas pós-em-dash existem (`"Pix de João — Aluguel apto 12"` vs `"Pix de João — Aluguel apto 13"` são receitas distintas de aluguéis diferentes). Strip cego juntaria. Whitelist limita aos padrões observados de **roteamento bancário** (sufixos sintéticos do C6 indicando categoria interna do banco, não conteúdo de negócio).

**Extensibilidade futura:** quando outros bancos (NuBank, Inter, BTG) forem observados emitindo sufixos análogos, adicionar padrões à whitelist com PR + teste. Lista finita é dívida aceita (vs bucket-based ou fuzzy Levenshtein — ver Alternativas).

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

- Receita do Empregador Exemplo (e similares) aparece 1× no card mensal — valor correto.
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

1. **Cenário empregador PJ** — Workspace `1b9f2cf5-…` (report `9b31d739-…`) recompute E4 → `receita_por_mes["2026-03"]["Empregador Exemplo (Titular - PJ)"] = 50000.00` (não 150000.00). Outras linhas do tooltip recompõem.
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
12. **Sufixos de roteamento PIX** (iteração 2) — `"Pix recebido de X"` e `"Pix recebido de X — Salários PJ"` no mesmo dia/banco/titular/tipo_conta/valor produzem **mesmo** `transaction_hash`. Análogo para sufixos ` — 13 Salário`, ` — TRANSF ENVIADA PIX`, ` — Boleto`, ` — NFS \d+`, ` SIMPLES NACIONAL` (DARF). Whitelist conservadora — outros sufixos pós- ` — ` (ex.: `"— Aluguel apto 12"`) **não** sofrem strip.
13. **Cenário empregador PJ iteração 2** — Workspace `1b9f2cf5-…` (run `f66b519e-…`, report `ffde7f63-…`) recompute E4 → soma do Empregador Exemplo no janela 12M cai de R$ 650.000,00 para **R$ 450.000,00** (5 PIXes ≥ R$ 8k duplicados por sufixo `" — Salários PJ"` / `" — 13 Salário"` são colapsados — Δ R$ 200.000,00). Análogo Cliente PJ Exemplo: R$ 240.000 → **R$ 160.000** (2 PIXes R$ 40k duplicados por sufixo `" — NFS 25"` / `" — NF 26"` colapsam — Δ R$ 80.000). **Total receitas:** R$ 280.000,00 removido em 7 tx.

    **Despesas (mesmo workspace):** 22 tx colapsadas, R$ 50.000,00 removido. Padrões dominantes: DARF detalhada (`"SIMPLES NACIONAL"`), pagamento serviços domésticos com sufixo `" — TRANSF ENVIADA PIX"` (Prestador Exemplo), boleto (Estabelecimento Exemplo).

    **Total inflação removida no workspace:** R$ 330.000,00 (receitas + despesas).

    **Resíduo não-coberto por esta ADR** (~R$ 130k restantes): casos `"Pix recebido de CLIENTE PJ EXEMPLO LTDA Pix enviado para RECEITA FEDERAL"` (2025-08-26) e `"Pix recebido de CLIENTE PJ EXEMPLO 2 LTDA Pix recebido de EMPREGADOR EXEMPLO LTDA"` (2025-09-30) são **2 transações concatenadas em 1 pelo parser C6Bank extratoconta** — bug parser-específico, não problema de hash. Tratado em PR isolado sem ADR (ver §Próximos passos).

## Alternativas consideradas

- **Apenas Camada A defensiva** (rejeitado): patcha 3 agregadores hoje; futuros consumers (cenários de estresse, parecer, chat sobre relatório) reincidirão. Sem audit trail por transação. Cria dívida arquitetural.
- **Apenas Camada B sistêmica** (rejeitado): ADR + schema + goldens + backfill leva ~2-3 dias; sangra valor em prod no intervalo. Camada A defensiva em horas destrava o caso.
- **Dedup em E3 reconciler** (rejeitado para o produtor de hash, considerado para dedup): atravessa boundary intra-statement do reconciler ([[ADR-097]]) que tem invariantes próprios (saldo continuity). Gerar hash em E3 é OK (boundary natural — antes do fan-out E4) mas dedup fica em E4 (perto do consumo).
- **Fingerprint só por `(data, valor)` + LLM tie-break** (rejeitado): introduz dependência LLM em stage determinístico; quebra goldens estáveis; custo recorrente alto.
- **Marcar duplicata só na UI** (rejeitado): backend continua inflado; KPIs/parecer/alocação-alvo enganados; UI seria band-aid.
- **Soma N×valor com divisão por N** (rejeitado): introduz heurística não-determinística e diverge de fonte primária (extrato bancário oficial).
- **Bloquear upload duplicado upstream com fuzzy dedup por conteúdo** (futuro, complementar): exige E2 rodar antes do dedup decidir; é caminho válido para track separado ([[ADR-228]] estendida) mas não substitui a defesa em E4 — workspaces com baseline já corrompido continuam.

### Alternativas para sufixos de roteamento (iteração 2)

Quando a observação de produção mostrou que `normalize_descricao` lowercase + whitespace **não** captura sufixos PIX variantes, 3 caminhos foram avaliados:

- **(A) Strip de sufixos por whitelist conservadora** (escolhido): regex finito sobre padrões observados (`" — TRANSF ENVIADA PIX"`, `" — Salários PJ"`, `" — 13 Salário"`, `" — Boleto"`, `" — NFS \d+"`, `" SIMPLES NACIONAL"`). Custo de manutenção: 1-2 PRs por banco novo. Determinístico. Goldens estáveis após regen.
- **(B) Dedup em 2 camadas — strict + relaxed** (rejeitado por overhead UX): camada 1 mantém K4 atual (silent dedup); camada 2 com hash relaxado sem `descricao` → match vira `needs_review`. **Problema:** todo PIX simétrico legítimo de casal, toda parcela mensal recorrente de valor fixo, toda transferência intra-titular CC↔poupança caem em `needs_review`. Volume estimado > 5% das transações → fila ingerenciável. Bucketing `(data, banco_norm, titular_norm, tipo_conta_norm, valor_cents)` mitigaria mas adiciona complexidade significativa sem cobrir o caso observado melhor que (A).
- **(C) Fuzzy match Levenshtein/Jaccard** (rejeitado): similaridade ≥ 0,8 sobre `descricao_norm` cobriria sufixos + parser-concat-issues. **Problemas:** (1) O(n²) custoso para workspaces grandes (50k+ tx); (2) não-determinístico em ordem de iteração quando `(data, valor, banco)` colide em 3+; (3) regressão de paridade golden imprevisível — qualquer mudança em threshold troca grupos de dedup. Reservar para parser-concat-issues isolados (PR separado, sem ADR).

Decisão (A) por: determinismo absoluto (goldens estáveis), custo cirúrgico (~15 linhas em `_tx_identity.py`), debug trivial (regex em logs), extensibilidade incremental por banco. Trade-off aceito: lista finita é dívida — quando aparecer NuBank/Inter/BTG com sufixos análogos, adicionar padrão + golden de regressão. Custo amortizado < custo de UX de needs_review massivo de (B) ou não-determinismo de (C).

## Próximos passos

- **PR1 (entregue em #429)**: helper `pipeline/domain/services/_tx_identity.py` + dedup K4 + `DedupReport` em `cash_flow_builder` × 3 funções + log JSON + goldens E4 regenerados + teste cross-doc (`tests/test_e4_cross_doc_dedup.py`). **Sem schema bump.** Camada A shipou em 2026-05-22.
- **PR2 (entregue em #429)**: campos `source_doc_id` + `transaction_hash` em `ClassifiedTransaction`; geração em `e3_serialization`; schema E4 aditivo; builders preferem field, fallback computed. Goldens regeneram. Teste explícito de aditividade do schema.
- **PR3 (entregue em #429)**: `dev/audit_duplicate_transactions.py` + `backend/app/services/internal_ops/recompute_e4.py`. Marca `pipeline_runs.stale=true`. Runbook em `docs/reference/runbooks/`.
- **PR4 — iteração 2 (este escopo)**: refinar `normalize_descricao` em `_tx_identity.py` com strip de sufixos PIX whitelistados; estender `compute_transaction_hash` correspondentemente; testes unitários cobrindo critério #12 (sufixos colapsam) + regressão #6 (parcelamento preservado) + #3 (casal titular distinto preservado); regen goldens E3/E4; recompute_e4 no workspace `1b9f2cf5-…` para validar critério #13. Após verde, **flip ADR-255 → Decidido**.
- **Follow-up tracked separadamente**: detecção upstream de overlap de conteúdo em E0/E2 (estender [[ADR-228]]) — preventiva, não substitui defesa em E4. Trigger: confirmar com product-designer + financial-planner se UX é flag-and-mark ou block-and-replace.
- **Follow-up tracked separadamente**: melhorar classificador de banco em E0 para PDFs C6 "extrato-da-sua-conta-{ULID}" (snapshots cumulativos do app C6 PJ) — reduz casos de `bank_code=""` que escapam de fuzzy dedup. Causa raiz upstream: o parser de E0 não reconhece o cabeçalho/layout do PDF "extrato completo" do C6.
- **Bug parser isolado (sem ADR)**: parser C6Bank extratoconta (`scripts/e2/banks/c6bank.py`) concatenou 2 transações adjacentes em 1 (caso observado: `"Pix recebido de CLIENTE PJ EXEMPLO 2 LTDA Pix recebido de EMPREGADOR EXEMPLO LTDA"` em 2025-09-30, R$ 40.000). Bug parser-específico; resolve com fixture + regression test, sem decisão arquitetural.
