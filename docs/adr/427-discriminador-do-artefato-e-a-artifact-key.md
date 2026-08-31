---
id: ADR-427
type: adr
title: "O discriminador do artefato é a `artifact_key`: o guard de escrita resolve por `(stage, key)`, e o balde herda o contrato da própria fonte"
status: Decidido
phase: A42
date: "2026-08-30"
relates_to:
  - "[[ADR-212]]"
  - "[[ADR-239]]"
  - "[[ADR-284]]"
  - "[[ADR-409]]"
  - "[[ADR-132]]"
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/decidido
  - area/dados
  - area/pipeline
  - area/testing
aliases:
  - "ADR 427"
  - "guard de escrita por artifact_key"
  - "e4 schema por balde"
---

# ADR-427 — O discriminador do artefato é a `artifact_key`

> **Decidido** em [[A42.l19]] · PR [#1871](https://github.com/davidrobert/mathoms/pull/1871)
> (`5504d91c`). D1–D6 implementadas e mergeadas.
>
> Levantado pela [[A42.l19]] (origem `N2` da rodada unificada `U4`). O enunciado da
> lane apontava **um** ramo placeholder; a medição no produtor real achou **dois**
> ramos mortos, um catch-all que não restringe nada e uma fixture que mantinha o
> ramo morto parecendo vivo.

## Contexto

`DBArtifactStore.write` valida o payload contra `SCHEMA_BY_STAGE[stage]` ([[ADR-212]]
PR3). O mapa é 1:1 **stage → schema**, e o stage `categorize_transactions` escreve
**7 baldes** com contratos diferentes (`receitas`, `despesas`,
`fluxo_mensal_detalhado`, `patrimonio`, `investimentos`, `seguros`,
`pontos_milhas`). Todos batiam contra um único `e4_unified.schema.json`, um `oneOf`
de 5 ramos.

**Medido em 2026-08-30**, rodando o produtor real (`main_with_store`) sobre as
fixtures commitadas `minimal-conta-3_reconciled.json` +
`minimal-baseline-1.5_consolidated.json`:

| Ramo do `oneOf` | Quem casava |
|---|---|
| `{schema_version, apolices}` — seguros v2 | `seguros`, só quando há apólice |
| `{periodo: object, total_geral}` — "receitas ou despesas" | **ninguém**: o produtor emite `periodo` como **string** |
| `{meses_ordenados}` — fluxo | `fluxo_mensal_detalhado` |
| `{dados}` com `dados: {}` — "patrimônio ou investimentos" | `receitas`, `despesas`, `investimentos`, `seguros` v1, `pontos_milhas` — **5 baldes**, e o ramo não restringe **nada** |
| `{status: string}` — "placeholder (seguros, pontos_milhas)" | **ninguém**: o placeholder do produtor é `{"dados": []}` |
| — | `patrimonio` casava com **zero** ramos: reprovava em `$` e era gravado assim mesmo sob `warn` |

Três consequências compostas:

1. **O guard não podia pegar troca de balde.** `{"status": "vazio"}` gravado como
   `despesas` validava; `receitas` escrito no shape de `fluxo` também.
2. **O `patrimonio` reprovava e passava.** `warn` é o default de
   `pipeline.json → schema_validation.mode`, e o flip global segue rejeitado
   ([[ADR-409]]) — logo o drift era permanente, não transitório.
3. **A telemetria per-path da [[ADR-284]] ficava cega.** `oneOf` colapsa o path de
   drift para a raiz `$`, e é justamente o path que gateia a fila do flip.

A jusante, `_non_ledger_verdict` da ledger-certify sondava `dados`/`apolices`/
`composicao` — nenhum deles presente no balde `patrimonio` (`composicao` é campo do
bloco `patrimonio` do **E5**) — e imprimia *coberto · 0 itens* para um balde com 87
itens. Duas guardas, a mesma cegueira.

## Decisão

**D1 — O guard resolve por `(stage, artifact_key)`.** `SCHEMA_BY_STAGE_KEY` é
consultado antes de `SCHEMA_BY_STAGE`; stage sem entrada por chave segue resolvendo
por stage. O mapa por chave **acrescenta precisão, não troca o mecanismo**.

**D2 — Quando a `artifact_key` já é o tipo, o discriminador NÃO vai para o payload.**
É a diferença desta nota para o `comprovante_base.schema.json` da [[ADR-239]]: lá a
`artifact_key` varia por documento (`apolice_portoseguro_2024`) e **não** diz o tipo,
então o stage enxerta `tipo_comprovante`. Aqui as 7 chaves **são** o tipo, e elas já
são coluna da row. Enxertar campo mudaria os bytes do payload — e com eles o
`sha256(json.dumps(e5_data))` da chave de cache do parecer ([[ADR-173]]), os goldens
e o snapshot do view-model — para servir a um guard que já tinha a informação.

**D3 — O balde herda o contrato da própria fonte.** `patrimonio` é cópia normalizada
do artefato E1.5c, que já é gateado por `baseline_patrimonial.schema.json`; o balde
passa a apontar para **o mesmo** schema. A cópia não pode ser julgada por contrato
mais frouxo que a fonte. (O golden do E4 **já** validava assim — e pulava o balde no
laço do `e4_unified`: sabia o contrato certo e registrava a isenção em vez de fechá-la.)

**D4 — O schema por stage vira backstop `anyOf`, nunca buraco.**
`e4_unified.schema.json` passa a ser `anyOf` de `$ref` para os contratos por balde:
cobre `artifact_key` que ninguém mapeou com fail-closed frouxo em vez de passthrough.
`anyOf` e não `oneOf` porque `seguros` v1 e `pontos_milhas` são ambos `{"dados": []}`
— sob `oneOf`, duas correspondências reprovariam um payload correto.

**D5 — Completude por igualdade de conjunto.** O gate compara
`{key | (stage, key) ∈ SCHEMA_BY_STAGE_KEY}` com `ARTIFACT_KEYS`, nos dois sentidos:
balde novo sem schema cairia no backstop e reabriria o buraco em silêncio; entrada
órfã aponta para balde que ninguém escreve. Continência num sentido só não serve.

**D6 — Shape não reconhecido é `não-verificável`, nunca `coberto`.** O contêiner
contável de cada balde não-transacional é resolvido pela **chave** (mesmo
discriminador do D1), e a ausência dele deixa de ser silenciada.

## Consequências

- **`schema_version` passa a ser token por `(stage, key)`.** Com token por stage os 7
  baldes carregariam o mesmo hash e a coluna deixaria de dizer qual contrato validou
  a row. Rows E4 gravadas a partir daqui têm token novo; rows históricas não são
  revalidadas (a validação é de **escrita**).
- **O flip `warn→strict` do E4 fica elegível.** Medido: os 7 baldes validam em
  `strict` contra o schema resolvido. A ordem exigida pela [[A42.l19]] — corrigir o
  schema **antes** de gatear — é satisfeita dentro do próprio PR. A decisão de flip
  segue com a [[ADR-409]]; esta nota só remove o impedimento.
- **A telemetria de drift do E4 deixa de colapsar em `$`** e passa a nomear paths
  reais, que é o eixo da fila da [[ADR-284]]. Gate:
  `test_drift_do_e4_nomeia_path_real_e_nao_a_raiz`. A/B contra o schema anterior:
  `seguros` malformado dava `['$']` e passa a dar `['$.apolices']`; `investimentos`
  sem 4 campos `required` **não driftava de todo** (o ramo catch-all aceitava) e passa
  a nomear os 4.
- **`dev/measure_schema_drift.py` mede pelo schema resolvido.** Consertar só o guard
  faria os 7 baldes baterem contra o backstop `anyOf` e saírem `GO` sem contrato nenhum
  checado — o falso-verde migraria do guard para o instrumento que audita o guard.
- **A fixture `minimal-receitas-4_unified.json` foi reescrita.** Ela tinha o shape do
  ramo morto (`periodo` como objeto, 2 campos) e era o único consumidor do ramo: a
  fixture espelhava o **ramo**, não o produtor, e por isso o teste passava sem
  afirmar nada. Passa a espelhar `ReceitasUnified.to_legacy_dict`.
- **Custo:** 5 schemas novos em `config/schemas/`. É o preço de o contrato ser
  legível por balde; a alternativa (um arquivo com ramos) foi o que produziu os dois
  ramos mortos sem ninguém notar por duas sprints.

## Alternativas consideradas

- **Só remover o ramo placeholder.** Fecha a instância citada no enunciado e deixa a
  classe viva: `receitas` no shape de `fluxo` continuaria passando. Medido: com o
  mapa por chave esvaziado e só o ramo removido, o controle do placeholder **passa** —
  a prova de que o remédio menor é inerte contra o defeito maior.
- **Discriminador no payload (`_bucket`)**, como o `comprovante_base`. Rejeitado em
  D2: muda os bytes de 7 payloads para informação que já é coluna.
- **Nada de backstop — remover `E4` de `SCHEMA_BY_STAGE`.** Chave não mapeada viraria
  passthrough, que é exatamente a classe de falha em reparo.
