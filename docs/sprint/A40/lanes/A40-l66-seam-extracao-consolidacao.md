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

## Fora de escopo

- Guarda de publicação no E5 e flip do schema para strict → [[A40.l67]].
- Balanço de fan-out do `extract_with_llm` → [[A40.l68]].
- `validate_cross`, `SCHEMA_BY_STAGE`/retenção e `llm_call_log` — donas vivas
  ([[A42.l4]], [[A42.l6]], [[A42.l7]]); ver §Roteamento do plano.
- Cache/pin de extração: só **depois** desta lane — pin antes congela extração
  errada (§Anti-decisões do plano).
- Identidade de imóvel com canonical ausente → Onda 4 (4b-i), destravada pela
  medição 0c.
