---
id: ADR-435
type: adr
title: "Cobertura por profundidade é termo do veredito de flip, e o grão do item é contrato"
status: Decidido
phase: A42.l26
date: "2026-09-01"
relates_to:
  - "[[ADR-409]]"
  - "[[ADR-432]]"
  - "[[ADR-427]]"
  - "[[ADR-284]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 435"
  - "cobertura por profundidade"
  - "grão do item"
  - "veto de cobertura no measure_schema_drift"
tags:
  - type/adr
  - status/decidido
  - area/dados
  - area/pipeline
  - area/observability
---

# ADR-435 — Cobertura por profundidade é termo do veredito de flip, e o grão do item é contrato

**Status:** Decidido (A42.l26) • **Data:** 2026-09-01 • **Relaciona** [[ADR-409]] §B/§D/§F
(fila derivada de medição — esta ADR acrescenta um termo ao predicado e **re-deriva a
fila**), [[ADR-432]] D4/D5 (fecho da raiz e completude por igualdade de conjunto — esta
ADR os estende ao item), [[ADR-427]] D3/D5 (dois produtores, um arquivo),
[[ADR-284]] (modo `warn`/`strict`), [[ADR-212]] (validação pós-write).

## Contexto

A [[ADR-432]] fechou a **raiz** do `baseline_patrimonial`: 15 chaves declaradas,
`additionalProperties: false`, completude por igualdade de conjunto derivada do
produtor. O defeito desceu um nível. Medido no corpus (171 artefatos, 106 runs, 0
ilegíveis, 10.597 itens):

| coleção | itens | chaves emitidas fora do contrato de item |
| --- | ---: | --- |
| `imoveis_consolidados[]` | 1.154 | **5** — `ano_referencia` e `low_confidence` em **100%**; `needs_review`/`review_reasons` (50); `instituicao` (6) |
| `investimentos_consolidados[]` | 8.678 | 0 |
| `veiculos_consolidados[]` | 765 | 0 |

E o item não tinha `required` nem fecho, então **item vazio `{}`, campo não previsto e
valor fora de tipo atravessavam**. Medido por caso contra o contrato de antes: **8
casos** entravam limpos. A regressão de identidade de imóvel da [[A40.l113]] passou por
este guard — não por acidente de configuração, mas porque ele não olha o grão em que a
identidade mora.

A jusante, o instrumento que gateia a fila da [[ADR-409]] herdava a mesma cegueira:
`e4_cashflow` saía **`GO`** com drift 0 sobre 144 artefatos enquanto declarava **0 de
12** chaves em 292.134 itens de transação — entre elas `natural_key`,
`transaction_hash` e `source_doc_id`. `0 erros` sobre um nó que o contrato não descreve
não é afirmação sobre aquele nó; é a classe de falso-verde da [[A42.l24]].

## Decisão

**D1 — O grão do item é contrato.** `required` + `additionalProperties: false` no
`items` das três coleções e no objeto-do-ano de `patrimonio_por_ano`, com as 5 chaves
medidas declaradas e 4 declaradas por alcance de código (`endereco`,
`dados_completos`, `fonte` do ramo `consolidate_from_declarations`; `valor_nao_apurado`
da [[ADR-431]]). Drift no corpus **idêntico** antes e depois — 74/171, os mesmos 3
paths. O aperto é detecção nova sem custo de compatibilidade.

**D2 — A completude da [[ADR-432]] D5 vale por nível, não só na raiz.** Fechar o item
sem estender o ratchet instalaria, um nível abaixo, exatamente a condição que a
[[ADR-409]] §F mediu: sob `strict`, a próxima chave de item aborta o write. O conjunto
emitido vem de **rodar** o produtor e a cadeia de enriquecedores, nos **dois**
produtores ([[ADR-427]] D3), nunca de censo de corpus — corpus é história, e lista à
mão é a fantasma da próxima vez.

**D3 — O termo novo do veredito é cobertura por profundidade, não fecho.** Fecho e
`required` são propriedades do schema **isolado**: nada no corpus os falsifica, e o
caminho barato para o verde é fechar sem declarar — que sob `strict` aborta o write de
todo payload real. Cobertura é `emitidas ⊆ declaradas` **por nó**, com o corpus como
árbitro. É a D5 da 432 um nível abaixo, e é falsificável.

**D4 — A especificação, e cada cláusula existe por um falso-positivo ou falso-negativo
medido:**

- **Mapa de chave livre ≠ registro.** Nó sem `properties` e com
  `additionalProperties: {schema}` ou `patternProperties` modela **dado na chave**
  (`{categoria → lançamentos}`, `patrimonio_por_ano`); a cobertura se avalia no
  **valor**. Sem esta cláusula, 8 nós legítimos reprovariam.
- **`$ref` e combinadores resolvidos, com união de `properties`.** Sem seguir `$ref`,
  o `informe_base` — cuja profundidade inteira está atrás de `$ref` — sai verde por
  não ser medido. União e não interseção: sob `anyOf`, basta um ramo declarar a chave
  para o validador aceitar, e interseção fabricaria defeito que não existe.
- **Nó indeclarado é defeito, não ausência.** `{"type": "object"}` sem `properties` é
  literalmente profundidade não medida; tratá-lo como ausência faria de **apagar
  `properties`** o caminho barato para o verde.
- **Só a direção `emitida ⊄ declarada` veta.** A direção fantasma
  (`declarada ⊄ emitível`) é reportada pelos gates de completude e **nunca** veta
  aqui: vetá-la quebraria a [[ADR-432]] D1, que declara `membros` por alcance de
  código com 0 ocorrências no corpus.
- **Chave de nó indeclarado não é publicada.** Ali ela é **dado** (mês, membro,
  categoria), não nome de campo. Só o path e a contagem saem. Onde o nó declara
  `properties`, a chave extra é metadado e é publicada — mesma política da
  [[ADR-284]], que já imprime nome de campo na telemetria de drift.

**D5 — O veto entra em `is_go`/`veredito` e NÃO no exit code de `--gate`.** Precedente
escrito no próprio instrumento para `mass_trivial` e `contrato_nao_derivado`: `--gate`
significa "há drift", e vermelho ali trocaria falso-verde por falso-vermelho no CI.
**Corolário obrigatório, entregue junto:** o runbook §1.3 afirmava `Exit 0 = GO,
exit 1 = NO-GO` desde 2026-08-24 e **já era falso** — `e4_pontos_milhas` saía `0` sem
ser promovível. A linha foi corrigida no mesmo PR; frase que o instrumento contradiz é
como o §F chegou onde chegou.

**D6 — A fila é re-derivada, e os dois promovidos saem.** A [[A42.l19]] promoveu
`e4_cashflow` e `e4_investimentos` por arbitragem do `senior-cto` sobre drift 0 medido
**na raiz**. A informação mudou: na raiz os dois contratos são completos (9 de 9 e 7 de
7 chaves), e a cegueira está **só** no item. Não é reversão da arbitragem — é a regra
sob a qual ela foi feita: a §D da [[ADR-409]] tem por título *"a fila é a medição, não
a intenção"*, e o §Critério de aceite da [[A42.l19]] escreve a ordem dura *"corrigir o
schema **antes** de gatear"*. Apertar **depois** do flip é estritamente pior: sob
`strict` não há janela `warn` para medir, e o aperto aborta produção no mesmo PR.

Fila re-medida sobre o corpus inteiro (16 schemas, 0 ilegíveis):

| schema | artef | drift | grão | cob | veredito |
| --- | ---: | ---: | ---: | ---: | --- |
| `e4_seguros` | 72 | 0 | 1/1 | ok | **GO** |
| `e4_pontos_milhas` | 72 | 0 | 0/0 | ok | GO (massa trivial: 1 payload) |
| `e4_cashflow` | 144 | 0 | 0/1 | −1 | NO-GO (cobertura) |
| `e4_investimentos` | 72 | 0 | 0/1 | −1 | NO-GO (cobertura) |
| `e4_fluxo_mensal` | 72 | 0 | 0/0 | −3 | NO-GO (cobertura) |
| `informe_base` | 312 | 0 | 0/0 | −4 | NO-GO (cobertura) |
| `e16_irpf_full` | 428 | 0 | 0/0 | −11 | NO-GO (cobertura) |
| `baseline_patrimonial` | 171 | 74 | 9/9 | −7 | NO-GO (cobertura) |

**D7 — O alvo do primeiro flip fica em aberto, e isso é o resultado honesto.** O
único `GO` com massa não-trivial é `e4_seguros`, que a [[ADR-409]] §B já recusara à mão
por massa (5 payloads distintos em 72 artefatos) — o predicado codificado não o
reprova, o julgamento sim, e esta ADR **não** o promove. `informe_base` era o candidato
natural pela massa (298 payloads, 63 runs, drift 0) e **cai** ao ser medido através de
`$ref`: 4 nós de `financeiro_pf` não declaram nada. A rota mais barata para o primeiro
flip passa a ser a lane irmã que aperta o item de `e4_cashflow` — melhor massa da fila
(144 payloads), drift 0, 12 chaves de vocabulário estável já medidas.

## Não-decisões (rejeitadas)

- **Publicar o grão sem gatear.** É a forma canônica de nascer inerte neste repo: o
  §1.2 do runbook **é** esse experimento — um ✅ escrito à mão afirmando cobertura de
  22/22 writers ficou verde e falso por meses, até a [[A40.l58]] medir e achar
  `generate_llm_fallback`. Critério em prosa ao lado de instrumento que imprime `GO`
  perde para o instrumento.
- **Gatear por contagem de `additionalProperties: false`.** Mede fecho, não cobertura;
  não é falsificável pelo corpus; é gamificável na direção perigosa; e produz
  falso-vermelho em 8 mapas de chave livre legítimos. Foi o protótipo desta lane, e
  caiu por medição.
- **Apertar `e4_cashflow`/`e4_investimentos` aqui.** É lane irmã, `owner:
  data-engineer`, e misturá-la a esta faria o PR decidir e executar a mesma coisa.
- **Vetar no exit code de `--gate`.** Ver D5.
- **Matar os passthroughs v2 do `BaselineNormalizer`.** A [[ADR-432]] §Não-decisões o
  deferiu explicitamente como decisão de compat, sem dono; e medido, o payload v2 **já
  reprovava** contra o contrato de antes desta lane (2 erros: as chaves v2 sobrevivem
  ao lado das renomeadas e batem no fecho de raiz da D4 da 432, e o `isinstance` do
  passthrough não filtra o não-dict). A incompatibilidade é **herdada**, não criada
  aqui — vira precondição de flip nomeada, não supersedure parcial de cláusula viva.

## Consequências

- O `baseline_patrimonial` sai de **grão 3/7** para **9/9** no item, e os 8 casos
  medidos passam a reprovar. O drift no corpus não se move — o aperto é detecção, não
  migração.
- **O token de `schema_version` muda para os DOIS produtores de uma vez**
  ([[ADR-427]] D3 fez os dois compartilharem o arquivo): `consolidate_baseline`/`E1.5c`
  e o balde `patrimonio` do E4. Quem auditar a coluna deve ler como aperto de contrato,
  não como regressão.
- **A fila fica sem alvo imediato.** O custo é real: o primeiro flip do repo escorrega
  mais uma lane. O ganho é que `GO` volta a significar "medido em profundidade" — e
  gatear do lado em que errar é barato: `GO` bloqueado se destrava com um humano
  apertando um contrato; `strict` publicado sobre guard que deixa `{}` passar é a
  afirmação de proteção sem a proteção.
- **Assimetria nomeada, não implícita:** o **write** passa a exigir grão; o **read** de
  item segue sem gate (`dev/check_artifact_read_keys.py` cobre chave de topo/bloco em
  `backend/app/application`, não item). Dívida de classe conhecida.
- `propertyNames: ^\d{4}$` em `patrimonio_por_ano` é a única cláusula do aperto que
  **restringe** em vez de declarar: uma chave agregadora futura (`total`,
  `consolidado`) passaria a abortar o write em `strict`. Mantida deliberadamente, com o
  caso negativo escrito em teste — o produtor emite `str(ano)` nos dois ramos, e chave
  agregadora ali seria mudança de contrato que **deve** ser vista.

## Critério de aceite

- [x] `required` + `additionalProperties` no item das 3 coleções e no objeto-do-ano.
- [x] 8 casos medidos flipam de `ATRAVESSA` para `reprova`; controle positivo (payload
      do produtor real) continua passando.
- [x] Não-inércia **por subconjunto**: cada mecanismo mutado sozinho, com igualdade do
      conjunto de casos que deixam de reprovar — mutação que derruba caso a mais acopla
      mecanismos; mutação que não derruba nenhum é linha inerte.
- [x] Completude por nível, nos dois produtores, provada por **mutação do produtor**
      (não do payload).
- [x] Veto de cobertura muda `is_go` e **não** muda o exit code de `--gate`; runbook
      §1.3 corrigido no mesmo PR.
- [x] Cada cláusula do D4 com teste que a nega.
