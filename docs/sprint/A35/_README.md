---
id: MOC-sprint-a35
type: moc
title: "Sprint A35 — Continuidade não some quando o número de conta não extrai (follow-up A32, issue #860)"
aliases: ["A35", "Sprint A35"]
sprint_status: done
date: "2026-07-08"
theme: "review-trust"
---

# Sprint A35 — Gap genuíno de continuidade não some por número de conta ausente

> **Status:** `done` (aberta e encerrada 2026-07-08 — 1/1 lane shipped,
> KR1–KR3 ✅, gate confirmado no dado real do dogfood; ver §Gate). Origem: ressalva nomeada do
> gate da [[MOC-sprint-a32|A32]] (§Gate l7, KR2 anti-Goodhart) +
> confirmação do owner na triagem KR3 — issue
> [#860](https://github.com/davidrobert/mathoms/issues/860). A A32.l4
> ([[ADR-310]]) apertou a `ContinuityAccountKey` para incluir
> `account_number_norm`; efeito colateral: quando um extrato **não tem
> número de conta extraído**, ele vira "conta diferente" e um gap de
> continuidade **genuíno** entre ele e os extratos numerados da MESMA
> conta deixa de ser sinalizado. Caso real (rico): buraco abr–jun/2026
> na conta corrente, hoje invisível. Trocamos 30 falsos positivos (A32)
> por 1 falso negativo de borda — esta sprint fecha esse falso negativo
> sem reabrir os 30. Co-design 2026-07-08: `senior-cto` + `data-engineer`
> + `financial-planner`. Emenda datada na [[ADR-310]] (não ADR nova —
> refina a decisão que a 310 tomou, herda a cláusula de absorção pelo
> `SourceRef.kind` da [[ADR-278]] §B7).

## Diagnóstico (co-design 2026-07-08)

`ContinuityAccountKey = AccountKey(banco, tipo, moeda) + member_key +
account_number_norm` (`reconciliation_validators.py`). `account_number_norm`
vem da **extração** do documento (`document.py:158`), não de invariante
estrutural — e falha silenciosamente quando o regex do parser não casa.
Um statement sem número tem **duas causas indistinguíveis**: (a) o banco
não expõe número naquele documento; (b) o parser regrediu num documento
que tinha o número. A chave estrita separa a série em duas cadeias e o
`TemporalGapDetector`/`SaldoContinuityValidator` nunca comparam os dois
lados → gap genuíno suprimido.

**Fato empírico que calibra o escopo:** o workspace dogfood tem **zero
contas cadastradas** (`bank_accounts` vazia). O `AccountResolver`
(ADR-226) — fonte de verdade mais forte que "números vistos no run" —
degrada para `unknown` sem cadastro, então **não conserta o caso real do
#860 sozinho**. A escada de resolução tem dois tiers que compõem.

## Decisão (escada de resolução — emenda ADR-310)

1. **Tier 1 (preferencial, quando há cadastro):** derivar a identidade de
   cadeia do `AccountResolver` (ADR-226) — grau `fallback_bank` (banco
   com 1 conta cadastrada → statement sem número herda essa conta),
   `ambiguous` (2+ contas → isola, com sinal). Fonte de verdade forte.
2. **Tier 2 (sem cadastro — realidade do dogfood/onboarding):** predicado
   intra-run **`count == 1`** — dentro do grupo `(banco, membro, tipo,
   moeda)`, se há exatamente **um** `account_number_norm` distinto
   não-nulo, os statements sem número coalescem naquela cadeia. O ramo
   `>= 2` (frágil a ruído de normalização — agência embutida, DV,
   zero-pad gerando "distintos" espúrios) **fica fora**: com 2+ números
   presentes não se inventa fusão.
3. **Sinal auditável obrigatório (não-negociável dos dois especialistas):**
   toda inferência emite `SaldoChainMemberInferred` (dataclass tipada,
   padrão `FaturaExcludedFromSaldoChain` da l4) — **sem número cru** (dado
   sensível). Mata o risco de mascarar regressão de parser: número que
   *deveria* extrair e não extraiu fica visível, não costurado em
   silêncio.
4. **Só `not is_fatura`:** faturas não têm número de conta (têm
   `final_cartao`) e já têm chave própria por `account_type=fatura*`; o
   fallback não se aplica a elas.
5. **Determinismo (ADR-111):** resolução é função pura do conteúdo do
   grupo (predicado set-based) + sobrevivente canônico fixo (a chave
   numerada). Sem estado mutável de módulo; estável entre workers.
6. **Local:** helper compartilhado `_partition_chains` em
   `reconciliation_validators.py`, consumido pelos DOIS validators.
   `_chain_key` permanece puro; `AccountGrouper` **não muda** (número de
   conta não é chave de dedup de transação — blast radius errado).

## Lanes

| Onda | Lane | Título | Prioridade | Status |
|---|---|---|---|---|
| 0 | [[A35.l1]] | Fallback da cadeia de continuidade quando número de conta não extrai + sinal auditável ([[ADR-310]] emenda) | P1 | shipped (#865/#868) |

## KR

- **KR1** — Re-run do workspace dogfood volta a emitir **exatamente um**
  `temporal_gap` (e/ou `balance_gap`) para o buraco abr–jun/2026 da conta
  rico, com selo `documento_faltando`. Medido contra o gate da A32
  (baseline 0 → +1 gap genuíno, nada mais).
- **KR2** — Zero regressão da A32.l4: nenhum dos 39 falsos positivos
  (famílias F1–F4 do §Gate l7 da A32) reaparece. Nenhuma fusão
  CC↔poupança↔fatura, nenhuma cascata de docs dropados. Manifesto
  `dev/golden_diff.py` valor-a-valor prova que o **único** delta
  adicionado é o gap genuíno do rico.
- **KR3** — Nenhuma inferência silenciosa: cada coalescência emite
  `SaldoChainMemberInferred`; teste negativo garante que statement sem
  número nunca some da observabilidade.

## Gate — resultado (2026-07-08)

Entregue em **2 PRs** de impl: **#865** (`08c535cf`) helper
`partition_chains` + `continuity_chain.py` + coalescência Tier 2
`count==1` + sinal + emenda ADR-310; **#868** (`6e8fb369`) expõe
`inferred_chain_members` no output do stage E3 para observabilidade.

**Prova unitária (14/14 testes, `test_saldo_chain_accountless_coalescence.py`):**
gap restaurado (temporal+balance) · guardas de não-fusão (2 números→não
coalesce · poupança≠CC · membros distintos · fatura · todos-`None`
agrupam) · sinal sempre emitido (sem número cru, nos dois validators) ·
determinismo (mesmo resultado independente de ordem; sobrevivente = chave
numerada).

**Confirmação no dado real do dogfood** (validators in-process sobre os
statements rico reais — as runs headless que completam sem pausar não
persistem os warnings de continuidade em `review_reasons`, então a
medição foi direta sobre os `BankStatement` carregados):

- Os 2 extratos rico caem no **mesmo grupo** `(Rico, membro=None,
  extratoconta, BRL)`; `da48e34d` com número, `95b3d36e` sem — o gatilho
  exato do Tier 2.
- `partition_chains` → **1 cadeia após coalescência** (antes: 2).
- Sinal emitido: `SaldoChainMemberInferred` — *"membro sem numero
  coalescido na cadeia rico/extratoconta/-/BRL src=95b3d36e… (ADR-310
  emenda 2026-07-08)"* — **sem número cru**.
- `TemporalGapDetector` → **1 gap**: *"Temporal gap rico/extratoconta/-/BRL:
  122 days between …202603 (fim=2026-03-01) and …202607
  (inicio=2026-07-01)"* — o buraco abr–jun/2026 **de volta à tela**
  (natureza `documento_faltando`).

**Regressão A32.l4 (KR2):** os guardas unit-testados garantem zero fusão
cross-conta; a coalescência só dispara no eixo `account_number` sob
`count==1` — os 39 falsos F1–F4 não reabrem (nenhuma fusão
CC↔poupança↔fatura; `account_type` segue no núcleo da chave). Zero
goldens de execução afetados (warnings de continuidade não persistem em
artefato).

**Status dos KRs:** KR1 ✅ (gap de 122d restaurado no dado real) · KR2 ✅
(guardas verdes, zero falsos reabertos) · KR3 ✅ (sinal emitido, sem
número cru). Issue [#860](https://github.com/davidrobert/mathoms/issues/860)
fechada.

## Fora de escopo (Later, nomeado)

- **Robustez de normalização de `account_number_norm`** (agência embutida
  vs. não, DV, zero-pad → "distintos" espúrios no ramo `>= 2`) — o Tier 2
  só usa `count == 1`, imune a isso; o ramo `>= 2` fica para o Tier 1
  (cadastro) ou para o `SourceRef.kind` do DATA_LINEAGE. Não estreitar
  nem alargar a normalização nesta sprint.
- **Métrica por banco `account_number_missing_total{bank}`** para caçar
  regressão de parser — desejável (data-engineer), mas o sinal
  `SaldoChainMemberInferred` já dá a observabilidade mínima; a métrica
  OTLP dedicada é follow-up.
- **Caminho "não tenho esses extratos / não houve movimentação"** que
  silencia o card com memória entre runs (financial-planner) — follow-up
  de review UX, não desta lane.
- **Absorção pelo `SourceRef.kind`** ([[ADR-278]] §B7, plano
  DATA_LINEAGE) — quando entregar, absorve tanto a chave (ADR-310) quanto
  este fallback; a emenda declara isso.
