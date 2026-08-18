---
id: A40.l66
type: lane
title: "Seam extração/consolidação: o fato decide ativo vs. passivo, o rótulo do LLM vira hint"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l66-seam-extracao-consolidacao
owner: data-engineer
adrs:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-272]]"
  - "[[ADR-357]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
---

# A40.l66 — `a40-l66-seam-extracao-consolidacao`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (itens 1a,
> 1b, 1c). É o caminho crítico do MVP: enquanto o rótulo do LLM decidir o eixo,
> dois runs do mesmo corpus continuam divergindo e o contador do gate de saída
> da [[A40]] não pode iniciar.

## Problema

`scripts/consolidate_baseline.py:501` decide ativo vs. passivo pelo **rótulo**
que o LLM escreveu, não pelo fato:

```python
is_divida = categoria == "outros" and valor < 0
```

Na pipeline-review r6 a re-extração flipou `categoria` de um financiamento
imobiliário de `"outros"` para `"imovel"`. A conjunção quebrou, a dívida entrou
em `imoveis_consolidados` com valor **negativo**, `dividas[]` esvaziou, e o
efeito atravessou E5, CV (16/16 verde), parecer e render — o defeito chegou ao
leitor promovido a "ponto forte".

> **Corrigido em §Ataque (2026-08-17):** `dividas[]` **não** esvaziou — 4 entradas
> em r5 e 4 em r6. O que se perdeu foi uma **perna de ano** da dívida flipada.

Dois agravantes medidos:

1. **O detector já estava dentro do artefato e o código o descarta.** O `resumo`
   do próprio payload contabilizava o montante no lado do passivo;
   `consolidate_baseline.py:546-559` adota os totais do `resumo` ("mais
   confiáveis") sempre que `pj_skipped == 0`. O ramo `pj_skipped > 0` **já**
   desliga esse override — o fix de 1c é majoritariamente deleção.
2. **O ramo de dívida não carimba proveniência.** Só o ramo de imóvel grava
   `codigo_rfb`/`ano_referencia`; a dívida sai com `descricao`, `proprietario` e
   `saldo_31_12` e nada mais.

Instrumento já mergeado (Onda 0): `tests/test_e15c_golden_execution.py` tem 5
casos `xfail(strict=True)` que nomeiam esta lane, e o irmão
`..._conservacao_liquida_nasce_verde_sobre_o_payload_defeituoso` prova que a
identidade **líquida** fica verde sobre o mesmo payload — medido, Δ = (−200k,
−200k) nos dois eixos, e o líquido não vê.

## Escopo

**1a — roteamento por fato.** Função pura
`classify_baseline_item(codigo, valor_cents, categoria_hint, catalogo)` em
`pipeline/domain/services/`, recebendo VO de config tipado e devolvendo warnings
tipados ([[ADR-097]] D1). Hierarquia de autoridade, decidida no co-design e
**não reaberta aqui**:

1. **catálogo RFB** (grupo do código) — autoridade primária;
2. mapa `(secao, codigo)`;
3. **sinal do valor como veto/desempate** — suficiente, nunca necessário (o IRPF
   declara saldo devedor **positivo** na seção de dívidas);
4. `categoria_hint`.

Estende o substrato existente `pipeline/llm/rfb_codes.py` com os grupos de
bens/direitos e de dívidas/ônus, em YAML versionado por ano-base, com fail-fast
e runbook anual. Divergência fato×hint → warning tipado + `review_reason`
([[ADR-272]]), nunca silêncio. O ramo de dívida passa a carimbar
`fonte`/`ano_referencia`/`tipo`.

**1b — contrato E1.5a.** `categoria` → `categoria_hint` (opcional, string livre,
usado só no warning); o campo derivado server-side é fechado em enum. `secao`
entra **OPTIONAL** nesta etapa, com taxa de emissão medida; vira `required` só
com cobertura 100% comprovada, **nunca no PR que a introduz** — re-validação de
histórico dispara re-extração ([[ADR-261]] Tier 3). Bump `e15_baseline`
1.2.0→1.3.0 cobrindo o schema irmão. Conservação por seção **dentro do E1.5a**
(Σ itens ≡ `total_liabilities`/`total_assets`, por ano). Boundary tolerante:
enum desconhecido → `needs_review` no item, resto do documento extraído
(anti reask-storm, precedente [[ADR-292]]).

**1c — conservação intra-artefato no E1.5c**, por **eixo e por ano** (cents int,
tolerância zero): generalizar o ramo `pj_skipped > 0` que já desliga o override
do `resumo`. Determinístico ganha; divergência → `review_reason` + stage
`degraded` ([[ADR-357]]), nunca `raise` que mata o relatório. Inclui o contrato
de `review_reasons` no artefato E1.5c — hoje só `extract_baseline` projeta o
bloco.

**Cauda (mesma janela de rebaseline).** `temperature=0.0` + seed explícito nos
call-sites `extract_*` (kwarg, sem bump de prompt) + gate que falha em call-site
novo sem o kwarg. Claim honesto no PR: **reduz variância; não torna a extração
idempotente**.

## Enforcement

WARN-first, doutrina [[ADR-357]]/[[ADR-358]]. A taxa de disparo de 1c é medida
sobre os payloads r5+r6 e **declarada na ADR-A antes de qualquer flip**; default
é rebaixa/declara (warning tipado + `review_reason` + `degraded`), nunca reter
nem abortar run. Kill-switch de 1 env var, provado por teste.

## Critério de aceite

- Os 4 `xfail(strict=True)` de `tests/test_e15c_golden_execution.py` que nomeiam
  A40.l66 desmarcados e verdes; o 5º (schema) continua RED — é da [[A40.l67]].
- `tests/test_e5_invariante_entre_agregados.py::test_invariante_4a_entre_agregados`
  desmarcado e verde (invariante 4a — critério de aceite da Onda 1).
- `test_e15c_r6_o_cancelamento_exato_e_a_assinatura_do_bug` **deletado** (não
  relaxado): ele afirma a presença do defeito, e Δ passa a ser (0, 0).
- **Prova por mutação:** flipar `categoria` de um item negativo no corpus produz
  baldes **byte-idênticos**. Sem essa prova, o teste nomeia o mecanismo sem
  exercitá-lo.
- Taxa de disparo de 1c medida sobre r5+r6 e escrita na ADR-A.
- ADR-A aberta `Proposto` **antes** do PR de implementação (política P0/P1) e
  flipada para `Decidido` no merge.
- Rebaseline, se houver, em commit isolado dentro do PR do fix
  (`dev/check_golden_rebaseline_isolation.py`), com `dev/golden_diff.py
  --manifest` e sinal ↑/↓/= declarado.

## Ataque (2026-08-17) — medido antes do pickup

Corpus: os 7 runs completos de agosto do workspace de dogfood — r6 (`7b64b6c7`),
r5 (`0a040a22`), `1aaa1072`, `b842e6e5`, `ee124571`, `82b30303`, `2a0e82a4`.
Artefatos decriptados localmente (Fernet), leitura zero-write; só contagens,
sinais e códigos abaixo — nenhum valor, descrição ou membro.

> Os payloads de r5+r6 estão **encriptados em repouso**. Medir a taxa de disparo
> de 1c exige o path de decrypt — custo que a lane não orça.

### Confirmado

- **O flip existe e é frequente.** `imovel` + valor negativo aparece no E1.5a em
  **5/7 runs** do mesmo corpus; nos outros 2 o mesmo item sai como `outros`.
  Não é acidente de re-extração — é ~71%.
- **O detector está dentro do payload.** `resumo.total_passivos ≡ Σ|negativos|`
  em **7/7**, inclusive em r6, onde um dos negativos estava rotulado `imovel`.
- **O E1.5c não projeta `review_reasons`:** 0 em 7/7.
- **O ramo de dívida não carimba proveniência** — confirmado no código.

### Corrigido

1. **`dividas[]` não esvaziou.** 4 entradas em r5 e 4 em r6. O que mudou foi a
   cobertura de **ano**: r5 tem 6 pares (dívida, ano), r6 tem 5 — a dívida
   flipada perdeu a perna de 2025 de `dividas[]` e reapareceu negativa em
   `imoveis_consolidados{2025}`. O §Problema descreve um sumiço total que não
   ocorreu; o defeito real é **perda de uma perna de ano dentro de uma dívida
   que continua presente**.
2. **A assinatura chega ao E1.5c em 3/7, não 5/7.** Nos 2 runs restantes com
   flip, o E1.5c consolidou baseline **stale** (`dividas` só com 2024 enquanto o
   baseline do run tem 2024+2025) — o "baseline pegajoso" mascarando. Gate posto
   só no E1.5c mede a conjunção dos dois defeitos.
3. **O override do `resumo` está mascarando o defeito nos totais, não causando-o.**
   Como `total_passivos ≡ Σ|negativos|` (7/7), hoje `patrimonio_por_ano` sai
   certo apesar do balde errado. **1c é deleção que piora r6 se aterrissar antes
   de 1a** — a ordem 1a → 1c é restrição dura, não preferência.

### Novo — os degraus 1 e 2 da hierarquia medem zero

| degrau | cobertura medida no corpus |
| --- | --- |
| 1 · catálogo RFB por `codigo` | `codigo` 100% preenchido no E1.5a, **mas** `'11' → {imovel: 7, outros: 6}` e `'01' → {veiculo, investimento, poupanca, conta_corrente, imovel}`; no E1.6, `codigo_rfb` **vazio em 6/6** das dívidas |
| 2 · mapa `(secao, codigo)` | `secao` **não existe** no contrato E1.5a — 0/89 itens |
| 3 · sinal do valor | é o campo que flipou; o `SYSTEM_PROMPT` do e15 **nunca pede sinal negativo para dívida** e não tem categoria `divida` na enum |
| 4 · `categoria_hint` | é o defeito |

O espaço de código é misto por construção: o `SYSTEM_PROMPT` ensina a tabela
plana pré-2019 (`"41" poupança, "45" CDB`) e o corpus tem `41/45/61/71/74/97`
convivendo com `01–12` grupo-shaped; o E1.6 emite `GG-CC` (64 itens) e `GG` (122)
no mesmo run, e `normalize_grupo("01-11")` devolve `"01-11"`. Um YAML
`codigo → grupo` sobre esse campo adjudica errado com confiança.

**A seção já é extraída, estável, e no lugar errado.** `E1.6.dividas_onus` = **6
em 7/7 runs** — determinístico onde o rótulo flipa. Mas `extract_irpf_full` é
`FULL_ORDER[5]` e `consolidate_baseline` é `FULL_ORDER[4]`: a autoridade nasce
uma etapa **depois** de quem precisa dela. Três saídas — reordenar E1.6 antes do
E1.5c; o E1.5a emitir `secao` (o que 1b escolheu, com cobertura desconhecida e
bump de prompt); ou adjudicar ativo/passivo depois do E1.6. **Não reabro a
ordenação decidida no co-design** — reporto que ela ranqueia 4 candidatos e o que
mede 100% não está entre eles. Decisão do dono do plano; casa com o §Deferimento
datado *"E1.5a × E1.6 extraem o mesmo IRPF com contratos diferentes"*.

### Novo — a conservação de 1b/1c, medida

- **Agregado:** `resumo.total_ativos ≡ Σ de TODOS os anos` em **7/7** e
  `≢ Σ do ano-máx` em **7/7** — `_aggregate_baselines` soma os `resumo` per-file
  de anos distintos e o `ano_referencia` é `max(years)`. Conservação **por ano**
  contra esse `resumo` é falsa por construção: dispara **100%**, não é detector.
- **Per-file (E1.5a):** fecha **8/8** nos dois eixos, e cada artefato tem
  **1 ano distinto**. A conservação por ano de 1b já é verde hoje e dispara
  **0%** — é tautologia enquanto o artefato for mono-ano.
- `patrimonio_por_ano` tem **1 chave** (`2025`) enquanto os baldes carregam
  2023/2024/2025 — 7/7. É a chave que o E5 consome, e nenhum critério da lane a
  toca.

### Novo — dois buracos na mesma função

- **`previdencia` não tem ramo** em `consolidate_from_itens`: cai no `else` e
  vira `tipo="outros"` em `investimentos_consolidados`. 3 itens em r6. A enum do
  prompt emite a categoria; o consolidador não a conhece.
- **A fixture do instrumento é v1-shaped:** `_R6_PAYLOAD` usa `valor_brl` float e
  não traz `payload_version`; r5/r6 em produção são **string decimal** (v2).
  Conservação em cents sobre `safe_float` herda ruído de float — 1c precisa ler o
  decimal, não o `safe_float`.

### Correções ao §Critério de aceite

- "nenhum balde de ativo publica valor negativo" é **necessário e não
  suficiente**: não vê dívida positiva nem perna de ano perdida.
- "item negativo vira dívida carimbada" **passa no artefato real de r6** — a
  dívida está lá. Trocar por **conservação de pares (dívida, ano)** entre os
  itens do E1.5a e `dividas[]`.
- "conservação por eixo e por ano" precisa de referência por ano que o agregado
  não tem. Ou `_aggregate_baselines` passa a emitir `resumo` por ano (contrato
  não previsto em 1b), ou 1c compara contra os E1.5a per-file.
- **Prova por mutação:** flipar `categoria` de item **negativo** é satisfeita só
  pelo degrau 3 — não prova o catálogo. Exigir também (a) o caso **positivo** (o
  que o próprio §Escopo diz ser o caso real do IRPF) e (b) o caso **sem código
  útil** (6/6 das dívidas do E1.6).
- "taxa de disparo de 1c medida sobre r5+r6": **medida acima** — 0% ano-cego,
  100% por ano. A ADR-A precisa declarar qual das duas está sendo adotada.

## Fora de escopo

- Guarda de publicação no E5 e flip do schema para strict → [[A40.l67]].
- Balanço de fan-out do `extract_with_llm` → [[A40.l68]].
- `validate_cross`, `SCHEMA_BY_STAGE`/retenção e `llm_call_log` — donas vivas
  ([[A42.l4]], [[A42.l6]], [[A42.l7]]); ver §Roteamento do plano.
- Cache/pin de extração: só **depois** desta lane — pin antes congela extração
  errada (§Anti-decisões do plano).
- Identidade de imóvel com canonical ausente → Onda 4 (4b-i), destravada pela
  medição 0c.
