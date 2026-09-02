---
id: A42.l26
type: lane
title: "O guard de escrita do E4 passa com zero erros e não mede profundidade: item vazio, campo lixo e número-como-string atravessam"
sprint: A42
status: shipped
ship_pr: 1968
ship_date: "2026-09-02"
priority: P1
branch_slug: a42-l26-guard-de-escrita-valida-largura-nao-profundidade
owner: data-engineer
depends_on: []
adrs: ["[[ADR-212]]", "[[ADR-436]]", "[[ADR-409]]", "[[ADR-432]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p1, area/dados]
---

# A42.l26 — `guard-de-escrita-valida-largura-nao-profundidade`

> **Origem:** `PV13-13` da rodada unificada **U5** ([[PIPELINE-REVIEWS-active]] §r13).
> Sucessora da [[A42.l19]], cujo conserto **segura** — e cuja medição revelou o limite.

## O que está medido

O balde de patrimônio agora **resolve e valida com 0 erros** — a [[A42.l19]] entregou. Mas
o contrato re-derivado tem `required` e `additionalProperties: false` **só na raiz**: o
item de `imoveis_consolidados` sai com `required` nulo, então **item vazio `{}`, campo não
previsto e número serializado como string atravessam** a validação.

## Por que importa nesta rodada especificamente

A regressão de identidade de imóvel que a [[A40.l113]] descreve **passou por este guard**.
O guard não é cego a ela por acidente de configuração: ele **não olha o grão do item**, que
é exatamente onde a identidade mora. Um guard que valida largura declara cobertura que não
tem — mesma classe de [[A42.l24]].

## Critério de aceite

1. `required` e `additionalProperties` no **item**, não só na raiz.
2. Tipo numérico enforçado (número-como-string reprova).
3. Contrafactual medido por caso: item vazio, campo lixo, num→str — **os três reprovam**
   contra o código pré-mudança, e passam depois.
4. O guard publica **em que profundidade** validou; "0 erros" sem grão declarado não é
   veredito.


---

> **Entregue** em [#1968](https://github.com/davidrobert/mathoms/pull/1968),
> commit-merge `e3f595a7` (2026-09-02).
>
> ⚠️ **O título do commit em `main` cita `ADR-435`, e esse número é de outra lane.**
> A ADR desta lane é a **[[ADR-436]]**. O ID renumerou **duas vezes** durante o PR
> — `433` → `435` → `436`, perdendo para `ano-base-por-classe-de-ativo`, para a
> [[A42.l25]] (`ADR-434`) e para a [[A40.l115]] (`ADR-435`) —, e o título do PR
> tinha sido escrito antes da segunda. Squash-merge congela o título, então o
> ponteiro errado é permanente no histórico: quem procurar `ADR-435` a partir do
> commit cai na ADR de PII da [[A40.l115]]. O ponteiro correto vive aqui e no
> frontmatter `adrs:`.

## Medição de execução — 2026-09-01

Decisão canônica: [[ADR-436]] (D1–D7), com emenda datada na [[ADR-409]] §B.

**O enunciado acertou a classe e errou dois números.**

**(a) "número-como-string atravessa" já era falso pela metade.** Medido contra o
contrato de `HEAD`: `{"2024": "100.00"}` — chave que casa `^(31_12_)?\d{4}$` — **já
reprovava** por tipo. O vetor vivo era a chave que **não** casa
(`{"total": "100.00"}`), que atravessava porque `valores_31_12` não tinha
`additionalProperties`. O buraco é de fecho, não de tipo.

**(b) Não eram 3 casos; eram 8.** Item vazio nas **três** coleções (o enunciado só
nomeia `imoveis_consolidados`), campo lixo, a chave fora do pattern, e mais três em
`patrimonio_por_ano`, que ninguém tinha olhado: objeto-do-ano **vazio**, lixo dentro
dele, e **chave não-ano** no mapa.

**(c) O contrato do item estava 5 chaves atrás do produtor.** Censo do corpus (171
artefatos, 106 runs, 0 ilegíveis, 10.597 itens): `imoveis_consolidados[]` emitia
`ano_referencia` e `low_confidence` em **100%** dos 1.154 itens, mais `needs_review`
/`review_reasons` (50) e `instituicao` (6) — nenhuma declarada. Fechar o item sem
declará-las abortaria o write em `strict`. É a ordem dura do `RV4-23`/[[A42.l6]]:
**corrigir o contrato antes de gatear**.

**(d) O aperto é drift-neutro.** `dev/measure_schema_drift.py --all` antes e depois:
**74/171 nos dois**, os mesmos 3 paths. Detecção nova, custo zero de compatibilidade.

**(e) A alternativa `31_12_` do ano era fantasma de nível-2.** 10.699 chaves no corpus,
**100% `^\d{4}$`, zero com o prefixo**, e produtor nenhum a emite — a tolerância vive
só no leitor (`parse_ano_31_12`, que existe pelo bug lexicográfico da [[A40.l42]]).
Aposentada pela D2 da [[ADR-432]]. **Inerte como detecção, e o meu próprio gate
provou:** a igualdade de conjunto do `_MUTACOES` reprovou a primeira versão do caso,
porque com valor string ele era indistinguível do `campo_lixo`. Com valor numérico ele
só reprova pela **conjunção** fecho+pattern — e por isso aparece nos dois conjuntos.

## O critério 4 custou uma arbitragem, e o meu primeiro predicado caiu

*"O guard publica em que profundidade validou"* parece publicação e é **decisão de
veredito**: o instrumento que gateia a fila da [[ADR-409]] é quem publica.

Meu protótipo contava nós com `additionalProperties: false`. O `data-engineer` o
corrigiu para `required` no **nó terminal de coleção** (negador exato do vetor: `{}`
atravessa sse existe terminal sem `required`); o `senior-cto` derrubou os **dois**, e
a razão vale mais que o predicado: fecho e `required` são propriedades do schema
**isolado** — nada no corpus os falsifica, e o caminho barato para o verde é **fechar
sem declarar**, que sob `strict` aborta o write de todo payload real. O termo que
entrou é `emitidas ⊆ declaradas` **por nó**, medido no corpus.

**A arbitragem que isso força, e que eu não podia tomar sozinho:** `e4_cashflow` e
`e4_investimentos` — os dois que a [[A42.l19]] promoveu por arbitragem do
`senior-cto` — **saem da fila**. Não é reversão: o §D da [[ADR-409]] se chama *"a fila
é a medição, não a intenção"*, e a informação mudou. Na **raiz** os dois contratos são
completos (9/9 e 7/7 chaves); a cegueira está **só** no item, e é lá que moram
`natural_key`, `transaction_hash` e `source_doc_id` — 292.134 itens com **0 de 12**
chaves declaradas em `e4_cashflow`.

**E o candidato de reposição também caiu, pela mesma medição.** O `senior-cto` apontou
`informe_base` (312 artefatos, 298 payloads, drift 0) declarando que o `0` dele era
**sub-medição**, porque a sonda não seguia `$ref`. Seguindo: **4 nós indeclarados** em
`financeiro_pf`. A fila fica sem alvo imediato, e isso é o resultado honesto.

## Evidência contra o critério

| Critério | Evidência |
| --- | --- |
| 1 · `required` + `additionalProperties` no item | `config/schemas/baseline_patrimonial.schema.json`, 3 coleções + objeto-do-ano; `grão 3/7 → 9/9` |
| 2 · tipo numérico enforçado | Medido: já valia para chave que casa o ano; o buraco vivo era o **fecho** de `valores_31_12` (caso `num_como_str_em_chave_nao_ano`) |
| 3 · contrafactual por caso | **8 casos** flipam `ATRAVESSA`→`reprova`; controle positivo (payload do produtor real) continua passando |
| 4 · o guard publica a profundidade | Colunas `grão` e `cob` no `measure_schema_drift`, com os **paths** impressos; `NO-GO (cobertura)` é veredito novo |

**Não-inércia, por subconjunto.** 6 mutações, cada uma desligando **um** mecanismo,
com **igualdade** do conjunto de casos que deixam de reprovar — não `⊇`. Mutação que
derruba caso a mais estaria acoplando mecanismos; mutação que não derruba nenhum é
linha inerte no schema. Foi essa igualdade que pegou o acoplamento do (e) acima.

**O gate de completude é provado por mutação do PRODUTOR**, não do payload: plantar
`entry["chave_nova"]` em `consolidate_from_itens` tem de deixar o gate vermelho sem
ninguém tocar no teste. Payload mutado provaria só que o validador roda.

## Fora de escopo, roteado

- **Aperto do item de `e4_cashflow`/`e4_investimentos`** — é a rota mais barata para o
  primeiro flip do repo (melhor massa da fila, drift 0, 12 e 11 chaves de vocabulário
  estável, todas já medidas na [[ADR-436]] D6). `owner: data-engineer`.
- **6 nós indeclarados que sobram no `baseline_patrimonial`** — `_meta`, `resumo`,
  `validation`, `itens[]`, `informe_pf_saldos_31_12[]` e
  `imoveis_consolidados[]._dedup_warning`. A [[ADR-432]] os declarou com descrição em
  prosa ("contrato próprio em `e15_baseline_extract.schema.json`") em vez de estrutura;
  agora o instrumento os **nomeia**, que era o ponto.
- **Dois defeitos de código no `BaselineNormalizer`**, achados ao medir o O3 e que
  **não** são de contrato — se ficarem nomeados só como "incompatibilidade com
  `strict`", o próximo agente conserta o schema em vez do normalizer:
  - [`baseline_normalizer.py:104`](../../../../pipeline/domain/services/baseline_normalizer.py) —
    o passthrough v2 **não remove** `bens_imoveis_consolidados` do payload, então a
    chave v2 sobrevive ao lado da renomeada e bate no fecho de raiz da [[ADR-432]] D4;
  - mesmo bloco — o `if not isinstance(im, dict): continue` **não filtra**: o não-dict
    segue para dentro de `imoveis_consolidados`, violando `items.type: object`.

  Medido: o payload v2 **já reprovava** contra o contrato de antes desta lane (2
  erros). A incompatibilidade é **herdada da [[ADR-432]]**, não criada aqui — vira
  precondição de flip, e reabrir a §Não-decisão dela seria supersedure parcial de
  cláusula viva.
- **Assimetria write↔read:** o write passa a exigir grão; `dev/check_artifact_read_keys.py`
  cobre chave de topo/bloco, não item. Dívida de classe conhecida ([[ADR-436]]
  §Consequências).
