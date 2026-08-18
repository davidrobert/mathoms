---
id: ADR-394
type: adr
title: "Fato determinístico é autoridade; saída de LLM é hint em vocabulário fechado"
status: Proposto
phase: A40.l66
date: "2026-08-18"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-259]]"
  - "[[ADR-261]]"
  - "[[ADR-272]]"
  - "[[ADR-292]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 394"
  - "fato determinístico é autoridade"
  - "ADR-A do PLAN-deterministic-authority"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - phase/a40-l66
---

# ADR-394 — Fato determinístico é autoridade; saída de LLM é hint

**Status:** Proposto • **Data:** 2026-08-18 • É a **ADR-A** do
[[PLAN-deterministic-authority]] (§ADRs a abrir), aberta pela [[A40.l66]].
Cobre 1a/1b/1c; a regra "prescrição exige cobertura" (1d/3a) fica para a
emenda que a [[A40.l67]] anexa.

## Contexto

`consolidate_baseline.py:501` decide ativo × passivo pelo **rótulo** que o LLM
escreveu:

```python
is_divida = categoria == "outros" and valor < 0
```

Na re-extração do run `7b64b6c7` o `categoria` de um financiamento flipou de
`"outros"` para `"imovel"`, a conjunção quebrou, e a dívida entrou em
`imoveis_consolidados` com valor negativo. O efeito atravessou E5, CV, parecer e
render: o defeito chegou ao leitor promovido a "ponto forte".

### O que a medição diz sobre a hierarquia (7 runs de agosto do dogfood)

O co-design ordenou a autoridade como *catálogo RFB > (secao, codigo) > sinal >
hint*. Medido sobre o corpus real, os dois primeiros degraus **não têm dado**:

| degrau | cobertura medida |
| --- | --- |
| catálogo RFB por `codigo` | `'11' → {imovel: 7, outros: 6}`; `'01' → 5 categorias`. `codigo_rfb` das dívidas do E1.6 **vazio em 6/6** |
| `(secao, codigo)` | `secao` **não existe** no contrato E1.5a — 0/89 itens |
| sinal do valor | flipa: o mesmo item sai `outros`/negativo em 2/7 runs e `imovel`/negativo em 5/7 |
| `categoria_hint` | a enum do prompt **não tem valor de passivo** — dívida só cabe em `"outros"` |

O espaço de `codigo` é **misto**: o `SYSTEM_PROMPT` do e15 ensina a tabela plana
pré-2019 (`"41" poupança`, `"45" CDB`) e o corpus tem `41/45/61/71/74/97`
convivendo com `01`–`12` grupo-shaped. O E1.6 emite `GG-CC` e `GG` no mesmo run.

**O sinal não é fato.** É um segundo campo autoral do mesmo gerador — e o prompt
nunca o pede. Tratá-lo como "o fato" é dar autoridade ao mesmo LLM com outro
chapéu.

### A autoridade estável existe, no artefato vizinho

`extract_irpf_full` (E1.6) separa `bens_direitos` × `dividas_onus` **por seção
da declaração** e devolve 6 dívidas em **7/7** runs — enquanto o rótulo do E1.5a
flipa em 5/7. E `consolidate()`, a irmã legada no mesmo arquivo, itera
`decl["bens_direitos"]`/`decl["dividas"]`: já roteia por seção e lê saldo devedor
**positivo**. São **duas implementações vivas roteando por seção**; só o caminho
`itens[]` — o plano, introduzido depois — perdeu a informação.

E1.6 é `FULL_ORDER[5]`, `consolidate_baseline` é `FULL_ORDER[4]`: nasce uma etapa
tarde demais para servir de fonte sem reordenar o pipeline.

### O critério de aceite original não separava os mundos

Provado por execução: um patch que implementa **só o sinal**, com catálogo e
`secao` inertes, deixa 3 dos 4 `xfail` da lane verdes e satisfaz a prova por
mutação prescrita em 4/4 flips. O entregável principal de 1a não era exercitado
por nenhum critério.

## Decisão

**D1 — a seção da declaração é a autoridade primária, e o E1.5a passa a
emiti-la.** A hierarquia do co-design é mantida na intenção (fato acima de
rótulo) e corrigida na ordem, porque o degrau que ela punha em primeiro não tem
dado:

1. **`secao`** — de qual ficha o item veio (`bens_direitos` | `dividas_onus`).
   Decide sozinha quando presente.
2. **`(secao, codigo)`** — refina o *subtipo* do ativo; nunca o eixo.
3. **sinal do valor** — veto **suficiente, nunca necessário**: negativo prova
   passivo; positivo não prova ativo (o IRPF declara saldo devedor positivo).
4. **`categoria_hint`** — último recurso, e sempre com `review_reason` quando é
   quem decide.

**D2 — o catálogo RFB entra por `(ano_base, secao, codigo)`, não por `codigo`.**
Estende `pipeline/llm/rfb_codes.py` com as seções de bens/direitos e
dívidas/ônus em YAML por ano-base. Sem `secao`, uma entrada de catálogo **não é
consultada** — código sozinho é ambíguo por medição, e consultar assim produz
adjudicação errada com cara de determinística.

**D3 — divergência entre degraus vira `review_reason`, nunca silêncio.**
Reusa `domain.baseline_divergence` ([[ADR-272]]); o schema declara que código
novo não pede migration, mas aqui nem código novo é preciso. Vale também para o
caso que hoje sai calado: dívida **positiva** rotulada como ativo.

**D4 — o agregado do LLM nunca sobrescreve a soma determinística.** O override
de `consolidate_from_itens` (`resumo.total_ativos` vence quando `pj_skipped ==
0`) é deletado. **Ordem é restrição dura:** medido, `resumo.total_passivos ≡
Σ|negativos|` em 7/7 — hoje o override *mascara* o defeito nos totais, então
deletá-lo **antes** do roteamento de D1 piora o run. D4 só aterrissa junto com
D1, nunca antes.

**D5 — conservação por eixo é medida contra a referência do mesmo grão.**
Medido: o `resumo` do agregado é a soma **de todos os anos** (7/7), porque
`_aggregate_baselines` soma os `resumo` per-file de anos distintos. Logo:

- **no E1.5a** (per-file, mono-ano): `Σ itens ≡ resumo`, por eixo, cents int,
  tolerância zero. Dispara 0% hoje — é contrato, não detector.
- **no E1.5c** (agregado, multi-ano): a conservação é **ano-cega** contra o
  `resumo` agregado e **por ano** contra a soma dos E1.5a. Exigir "por ano contra
  o `resumo` agregado" dispararia 100% por construção — seria erro de categoria,
  não achado.

**D6 — WARN-first.** Divergência rebaixa e declara (`review_reason` + stage
`degraded`, [[ADR-357]]); nunca `raise`, nunca retenção de run. Kill-switch por
env var, provado por teste.

**D7 — o contrato do E1.5a evolui aditivo primeiro.** `secao` entra
**opcional**; `categoria` ganha o irmão `categoria_hint` e o leitor aceita os
dois, com preferência pelo novo. Nenhum dos dois vira `required` no PR que o
introduz: há **766 artefatos E1.5a** gravados com `categoria`, o `read` não
valida mas o `write` do agregado valida, e o modo incremental relê todos e
agrega — um flip prematuro monta `itens[]` com as duas formas contra um schema
que admite uma só ([[ADR-261]] Tier 3). Boundary tolerante: valor de enum
desconhecido → `needs_review` no item, resto do documento extraído
([[ADR-292]]).

## Consequências

- O `secao` só cobre documento **re-extraído**. Enquanto a cobertura não é 100%,
  o degrau 3 (sinal) segue decidindo o histórico — com `review_reason` sempre que
  for ele quem decide. A taxa de cobertura é medida e citada antes de qualquer
  flip para `required`.
- A prova por mutação precisa de **projeção canônica**: `property_id` é `uuid4()`
  por run, então dois runs do mesmo payload nunca são byte-idênticos. E precisa
  incluir o caso **positivo** e o caso **sem `secao`** — só o flip negativo é
  satisfeito pelo degrau do sinal sozinho e não prova nada acima dele.
- `previdencia` não tem ramo em `consolidate_from_itens` e cai em `outros`; o
  roteamento novo passa a nomeá-la. É correção de subtipo, não de eixo.
- A unificação E1.5a × E1.6 continua deferida (§Deferimentos do plano, dono
  `senior-cto`), mas esta ADR registra que ela é o caminho **estruturalmente**
  certo: `secao` no E1.5a é a ponte enquanto os dois extratores existirem.
