---
id: ADR-440
type: adr
title: "A identidade de imóvel ancora nos campos da ficha de Bens e Direitos, lidos por parser determinístico, com chave por nível e veto por unidade"
status: Proposto
phase: A40.l121
date: "2026-10-08"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-225]]"
  - "[[ADR-265]]"
  - "[[ADR-280]]"
  - "[[ADR-385]]"
  - "[[ADR-386]]"
  - "[[ADR-392]]"
  - "[[ADR-400]]"
  - "[[ADR-081]]"
  - "[[ADR-311]]"
  - "[[ADR-435]]"
  - "[[ADR-439]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 440"
  - "âncora estruturada de imóvel"
  - "parser da ficha de imóvel"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-440 — A identidade de imóvel ancora nos campos da ficha de Bens e Direitos, lidos por parser determinístico, com chave por nível e veto por unidade

> Co-design 2026-10-08: `data-engineer` (dono da [[A40.l121]]: contrato, join, veto, ordem dos
> PRs), `prompt-engineer` ([[ADR-081]], PII, medição), `senior-cto` (port, convergência, forma
> desta ADR). O **produtor** foi decisão do dono na mesma data: parser determinístico no lugar do
> bump do prompt `E1.5a` que o plano original previa. Executa o critério 3 da [[A40.l113]], cuja
> rede de segurança é a [[ADR-439]].

## Contexto

- A identidade de imóvel ([[ADR-215]]) é chaveada por `endereco_canonical = canonicalize(descricao)`:
  a cascata via+nº > `mat:` > `qa:` > `iptu:` elege **um** nível ([[ADR-225]] §1).
- O prompt `E1.5a` `1.4.1` ([[A42.l15]]) passou a copiar só a discriminação. Medido em 2026-10-08
  sobre os mesmos documentos: os imóveis que canonicalizam caem de **8/10 para 2/10**, e em 8/8 o
  via+nº vinha do campo rotulado `Logradouro` da ficha, que a `1.3.0` dobrava na descrição. A regra
  nova é certa; a identidade dependia de um efeito colateral da velha.
- Toda ficha de imóvel no layout com campos estruturados traz, em ordem fixa, `Inscrição Municipal
  (IPTU)`, `Logradouro`, `Nº`, um complemento sem rótulo, `Bairro` … `Matrícula`.
- 6 rows de `property_identity` têm override do usuário: 5 cunhadas em via+nº, 1 em `mat:`. Com os
  valores da ficha e sem mint, chaves nos três níveis re-alcançam **6/6**; só via+nº, 5/6.
- via+nº é chave de **prédio**: dois apartamentos do mesmo prédio fundem no match estrito, e casa
  `12` com apto `11` no mesmo canonical fundem no loose. Só matrícula e inscrição separam unidade.
- `match_or_create` cunha sempre que há canonical e nada casa, com commit imediato: chave que não
  bata byte a byte com a row gravada deixa a classificação do usuário órfã para sempre.

## Decisão

### D1 — A âncora é a ficha, lida por parser determinístico

O stage `E1.5a` ganha um parser de rótulo — função pura, sem LLM — que lê a janela de cada ficha
de imóvel no mesmo texto que vai ao modelo e devolve os valores **crus** de `Logradouro`, `Nº`,
complemento, `Matrícula` e `Inscrição Municipal`. Não importa o canonicalizer: extração emite valor
cru ([[ADR-280]]). O LLM não transcreve a âncora — transcrição não é mais confiável que
classificação ([[ADR-400]]), e o `01-11`×`11` da mesma era é essa deriva. É o degrau determinístico
da [[ADR-081]].

### D2 — Join ficha↔item, falhando fechado

Candidatas são as fichas cuja janela contém o valor BR exato do item. Uma só ⇒ `join: valor`. Mais
de uma ⇒ Jaccard de tokens entre a `descricao` do item e a discriminação de cada ficha, e vence a
que tiver pelo menos o dobro da segunda (`join: valor_tokens`). Fora disso — ou se a ficha for
reivindicada por dois itens de descrição diferente — o item fica **sem âncora**, com
`extract.ancora_imovel_ambigua`; ficha não achada dá `extract.ancora_imovel_sem_ficha`. Uma razão
por documento, com `offending_value` só de contagens.

### D3 — Contrato: no item do `E1.5a`, nunca no baseline consolidado

`e15_baseline_extract.schema.json`: o item ganha `ancora_imovel`, opcional e fechado —
`{join, logradouro, numero, complemento, matricula, inscricao_municipal}`, strings cruas com
`maxLength`, `required: [join]`, `minProperties: 2`, complemento vazio omitido —, e a raiz ganha
`ancora_versao`. Bairro, município, UF, CEP e cartório ficam fora (minimização). O consolidado
carrega a âncora em memória até o enricher, que a remove incondicionalmente depois da identidade:
ela não é declarada em `baseline_patrimonial.schema.json` e não chega a dedup, E5, view-model nem
parecer. O gate de PII da [[ADR-435]] casa rótulo e número na mesma string e não veria valor solto.

### D4 — Proveniência, e cura sem re-extração

O parser roda sobre **todo** IRPF do run, inclusive os que o incremental não reenvia ao LLM, antes
do early-return do incremental; se regravou algo, o agregado `E1.5` é recombinado. A row regravada
mantém o conteúdo e a `prompt_version` do LLM — a re-extração dirigida da [[ADR-311]] D3 segue
selecionando pela versão do LLM —, e `ancora_versao` registra o parser. Regrava só quando
`(ancora_versao, âncoras)` muda. Artefatos `1.3.0` e `1.4.1` já gravados ganham âncora no próximo
run, sem re-extração nem custo de API.

### D5 — Chave por nível, montada pelos extractors do canonicalizer

Com âncora, o enricher monta uma chave por nível — via+nº de `logradouro`+`numero`, `mat:` de
`matricula`, `iptu:` de `inscricao_municipal` — passando pelos **mesmos** extractors e pela mesma
normalização do `endereco_canonicalizer`: byte-identidade com as rows gravadas por construção, e
nenhuma segunda função de identidade ([[ADR-385]]). Sem âncora, a chave é exatamente a de hoje,
`canonicalize(descricao)`. A descrição não entra como candidata paralela: ela pode citar outro
imóvel ("adquirido com a venda do imóvel da Rua X") e daria ao imóvel novo a identidade — e a
classificação — do vendido.

### D6 — Match read-only com veto por unidade

O port ganha `match(...)`, a mesma cascata de `match_or_create` sem o insert; `match_or_create`
passa a ser `match` + insert. O enricher avalia todas as chaves do item e veta a candidata quando
(a) a unidade diverge com valor nos dois lados — matrícula > inscrição > complemento, o lado da row
lido do próprio `mat:`/`iptu:` ou da `descricao_sample` pelos mesmos extractors — ou (b) os
sub-códigos são específicos e diferentes. Entre as admissíveis, a provada por unidade vence a só
de endereço; no empate, a mais antiga, que é o first-write-wins de hoje. Perdedora que nenhuma outra
ficha reivindica ganha razão de split com os UUIDs. Supersessão fica no sweep ([[ADR-386]]).

### D7 — Mint em duas fases, só com posse provável

O enricher planeja o run inteiro antes de cunhar, porque `_insert_row` commita na hora. Se várias
fichas querem a mesma row, fica a que prova posse (discriminador igual ou `descricao_sample`
byte-igual); as demais recusam o attach e são cunhadas em `mat:` > `iptu:` — em via+nº
recolidiriam a cada run. Sem posse provável, ninguém anexa nem cunha: `needs_review`. Imóvel novo
cunha em via+nº quando ela é unívoca no run (apólice e informe de aluguel leem o canonical como
endereço), e em unidade nos demais casos. Não há flag de mint: mint commitado não se desfaz por flag
nem por revert. A proteção é pré-merge — a medição de alcance read-only — e a normalização do
`codigo_rfb` (`VARCHAR(4)`) é pré-condição.

## Consequências

- O dogfood volta a resolver residência e imóveis geradores por identidade, sem re-extração.
- [[ADR-225]] §1 ganha emenda datada (ordem de match ≠ ordem de mint; "o primeiro hit elege um
  nível" deixa de valer para item com âncora) e a [[ADR-265]] perde o veto de unidade para o
  enricher. As duas emendas vão no PR que vira esta ADR `Decidido`.
- Acoplamento ao layout do texto extraído: ficha não lida falha fechado — sem âncora, chave de
  hoje — e conta em razão, então a cobertura vira sinal.
- Matrícula e inscrição deixam de ser fallback e viram candidatas de todo item com âncora: a
  colisão entre cartórios que a [[ADR-225]] julgou baixa ganha exposição (§Deferimentos).

## Alternativas consideradas

1. **Bump do prompt `E1.5a` emitindo `imovel_*`** — o plano original; recusado pelo dono em
   2026-10-08. Repete a transcrição por LLM ([[ADR-400]]), e curar o corpus exigiria re-extração
   dirigida, que re-sorteia todo campo: na U5, 95 de 400 escalares se moveram sem documento novo.
2. **Reverter a regra de descrição da `1.4.1` para imóveis** — devolve a identidade à prosa, que é o
   defeito, e a descrição dobrada é justamente a que pode citar outro imóvel.
3. **Só via+nº** — medido: 5 de 6, órfã a row cunhada em `mat:`, e funde unidades do mesmo prédio.
4. **Multi-chave dentro do `PropertyLookupKey`** — o conflito precisa virar razão, e razão é do
   enricher; a política se duplicaria nos dois adapters.
5. **`_endereco_canonical_from_struct`** (apólice) — inclui cidade e UF; nunca bateria com as rows.
6. **Cunhar sempre em `mat:`** — desligaria apólice e informe de aluguel do imóvel novo.

## Deferimentos datados (2026-10-08, dono `data-engineer`)

- **Conjunto de chaves por row, ou namespace de matrícula por município/UF.** A row guarda uma
  chave só, e "mesmo prédio, matrícula distinta" segue indetectável quando a row nasceu em via+nº
  sem unidade na `descricao_sample`. Retomada: a primeira colisão entre cartórios medida, ou o
  primeiro split recusado por falta de discriminador na row.
- **Âncora por LLM como degrau de escalada.** Retomada: ficha com rótulo que o parser não lê em
  corpus real (`extract.ancora_imovel_sem_ficha` > 0). Exige bump do prompt e verificador de
  valor-ao-lado-do-rótulo.

## Gates

- PR0 — teste de contrato: o schema aceita a forma de D3 e recusa chave fora dela, `join` ausente e
  objeto vazio.
- PR1 — parser sobre texto sintético PII-zero no layout medido; a saída real do `E1.5a` valida
  contra o schema; `golden_diff` do dogfood igual a zero; o segundo run regrava zero rows.
- PR2 — `backend/tests/integration/test_property_override_sticky.py`, declarado pela [[ADR-215]] e
  inexistente até aqui; contrafactuais (sem âncora o colapso volta, sem veto dois apartamentos
  fundem, cada nível sozinho); medição read-only no dogfood: 6 de 6 rows com override, Δrows = 0,
  zero conflito.
