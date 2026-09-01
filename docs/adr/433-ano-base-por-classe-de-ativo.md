---
id: ADR-433
type: adr
title: "O ano-base 31/12 é eleito dentro da classe de ativo, e `property_id` ausente é um terceiro estado"
status: Proposto
phase: A40.l113
date: "2026-09-01"
relates_to:
  - "[[ADR-274]]"
  - "[[ADR-383]]"
  - "[[ADR-394]]"
  - "[[ADR-410]]"
  - "[[ADR-420]]"
  - "[[ADR-431]]"
  - "[[ADR-215]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 433"
  - "ano-base por classe de ativo"
  - "eleição do ano 31/12 por classe"
  - "estado ternário de classificação de imóvel"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
---

# ADR-433 — O ano-base 31/12 é eleito dentro da classe de ativo, e `property_id` ausente é um terceiro estado

## Contexto

A rodada unificada `U5` publicou, sobre **corpus documental idêntico** ao das três
rodadas anteriores, um relatório com `patrimonio.residencia = 0,00`,
`patrimonio.imoveis_geradores = 0,00`, `patrimonio.veiculos = 0,00` e
`endividamento.total_dividas = 0,00` — este último com **4 financiamentos listados na
mesma página**, e portanto `patrimonio.liquido` idêntico ao `bruto`. O run terminou
`completed`, sem sinal bloqueante.

O registro atribuiu o colapso a churn de identidade de imóvel ([[A40.l113]]) e, em
cadeia separada, ao ano cru do LLM ([[A40.l114]]). **A medição refutou as duas
atribuições** e encontrou uma raiz comum.

### O que foi medido

Executando os produtores reais contra o artefato `consolidate_baseline` do próprio run,
o publicado foi reproduzido ao centavo (`split_imoveis_with_overrides` → `(0.0,
701170.57)`).

1. `anos_base_por_membro` elegia o ano-base do membro como `max()` sobre a **união** de
   `imoveis_consolidados`, `investimentos_consolidados`, `veiculos_consolidados` e
   `dividas`, e aplicava o vencedor a **cada** lista.
2. O titular tinha 3 posições de investimento em **2026** (saldo de CDB, cofrinho e
   previdência — dado bancário corrente e legítimo). Imóveis, veículos e dívidas dele
   param em **2025**.
3. `_resolve_item_valor_e_ano` fazia `valores_31_12.get("2026")`, não achava, e caía em
   `safe_float(item.get("valor", 0))` → **0,00** para as três classes.

A residência é o caso que fecha o argumento: ela **tem** `property_id` e **tem** override
`residencia_principal` gravado. Saiu zero por **valor**, não por identidade.

Contrafactual, sobre o mesmo payload: com o ano eleito por classe, `residencia`
0,00 → **996.821,46** e `total_dividas` 0,00 → **230.459,13**.

### Duas afirmações do registro que caem

- O §r9 de [[REPORT-REVIEWS-active]] declara `RR9-01` e `RR9-02` **"duas cadeias
  independentes"**. Compartilham esta linha.
- A [[A40.l114]] atribui o zero da dívida ao `ano_referencia` cru do LLM. Passar `1999`
  — ou a string `zzz` — como `ano_domicilio` produz **o mesmo** resultado, porque o
  parâmetro só é consultado quando o membro não declarou ano nenhum. O critério 1
  daquela lane não moveria o número neste corpus.

## Decisão

### D1 — o grão da eleição do ano é `(membro × classe de ativo)`

`CLASSES_DE_ATIVO` particiona `CONSOLIDATED_LIST_KEYS` em imóveis, investimentos,
veículos e dívidas; `anos_base_por_classe` devolve um `AnosBaseDoMembro` por membro, e
cada `_split_*` resolve no ano da **sua** classe.

É a continuação do movimento que a [[ADR-274]] fez de *domicílio* → *membro*, um grão
abaixo — o comentário em `patrimonio_resolvers.py` já descrevia esta família de defeito
("quem não tem item no ano escolhido cai no fallback e vira 0,00").

**O veto da [[ADR-274]] §Alternativas item 2 continua de pé.** Aquele veto é ao máximo
**por-item**, que ressuscitaria ativo vendido. Aqui a população de eleição segue sendo
um **conjunto** de itens; o item que sumiu da declaração continua sem casar.

Isto foi verificado, não suposto: neste corpus o carry-forward por item somaria
**642.706,24** em duplicata — as três propriedades aparecem em 2025 **e** em 2024 —, e o
discriminador que o tornaria seguro (baixa registrada como zero **declarado**) **não
existe em nenhum item deste corpus**.

### D2 — o crédito de resíduo ao titular exige que todo ano usado seja o do resumo

O predicado era `ano_titular == ano_conjuge`. Com o eixo por classe ele poderia passar a
valer sobre um sintético **multi-ano**, **ligando** um crédito hoje inerte e fabricando
patrimônio — a família do `unattributed → titular` que a [[ADR-394]] §D8 cortou. Passa a
exigir que todo ano **efetivamente usado** para resolver valor seja igual ao ano do
resumo.

O predicado conta o ano *efetivo*, não o *eleito*: no formato legado (`valor_YYYY`)
nenhuma classe elege ano e tudo resolve no fallback, caso em que o crédito é legítimo e
segue disparando.

### D3 — `property_id` ausente é `desconhecido`, não "não é residência"

`classificacao_do_imovel` passa a ser o **produtor único** do estado: sem `pid`, ou com
`pid` sem rótulo, a classificação é `CLASSIFICATION_DESCONHECIDO` — uma constante que já
estava declarada e exportada no módulo e que **nenhum ramo usava**.

`cobertura_classificacao_imovel` mede a fatia desconhecida em **valor e contagem**. O
eixo de decisão é o **valor**: neste corpus a contagem diz 8 de 9 (89%) e o valor diz
**57,4%**, porque a residência é o maior item isolado — a contagem sozinha mente.

**A partição monetária não se move.** O valor do imóvel desconhecido continua somando
exatamente onde somava: em `bruto`, em cat_2 e no numerador da concentração. A
[[ADR-420]] §D2 — *ausência de rótulo não compra verde num KPI de risco* — fica intacta,
e a [[A40.l95]] não reabre. O que muda é a **afirmação de inventário**, não a soma.

O princípio da §D2 não se estende a `residencia`/`imoveis_geradores` porque ele depende
de **monotonicidade**: `m/(fin+m)` é estritamente crescente, e por isso existe um lado
conservador. Estes baldes não são monótonos em risco — o mesmo `pid` nulo infla cat_2 (falso
alarme) e zera a renda imobiliária (falso alarme de sinal **oposto**), enquanto
`investimentos_classes_analyzer` falha **aberto** com o mesmo dado. Não há escolha
conservadora aqui; há escolha honesta.

## Consequências

- `residencia` e `total_dividas` deixam de sair zero neste corpus; o número publicado
  **muda**, e a mudança é correção de medição, não melhora — a copy do changelog do
  relatório não pode narrá-la como ganho ([[ADR-419]]).
- `titular_data["ano_base"]` passa a ser o **menor** ano eleito entre as classes (frescor
  nunca superestimado, [[ADR-410]] D6), com `ano_base_por_classe` ao lado — que é a
  "datas por linha" da [[ADR-383]] §6.
- A fatia desconhecida fica mensurável. **Publicá-la como supressão do agregado**
  (`residencia`/`imoveis_geradores` saindo `null` + motivo em vez de `0,00`, sobre a
  escada de limiares da [[ADR-353]]) exige mudar o schema E5 e o tipo TS — fica
  **deferido**, com dono e condição de retomada na §Deferimento da [[A40.l113]].

## Alternativas consideradas

1. **Fallback para o ano mais recente do próprio item.** Rejeitada: é o veto literal da
   [[ADR-274]], e a medição mostrou que duplicaria 642.706,24 neste corpus.
2. **Resolver o ano item a item, com a data viajando no payload.** Rejeitada: a
   [[ADR-383]] D3 fixou o grão do árbitro em *fonte inteira, nunca ativo isolado*, e a
   troca de semântica ("posição em 31/12/X" → "posição mais recente conhecida") é decisão
   de produto já alocada ao árbitro de data-alvo.
3. **Filtrar ano futuro na eleição** (`31/12/2026` ainda não ocorreu). Complementar, não
   alternativa: sozinha não fecha o caso do cônjuge, que declara 2023 sem nenhum ano
   futuro envolvido. Fica deferida junto da política de data-alvo.
4. **Manter o `else` e emitir aviso.** Rejeitada: este run emitiu 2 avisos e terminou
   `completed` com 95 de 400 escalares movidos. Aviso ao lado de número falso não impede
   o número falso de circular — a [[ADR-431]] já recusou essa forma.

## Gates

- `tests/unit/pipeline/test_ano_base_por_classe_adr433.py` — 8 asserções, das quais **4
  reprovam** contra o produtor anterior (A/B medido), incluindo a de que o crédito de
  resíduo **não** dispara com classes em anos distintos.
- Teste de não-inércia explícito: `anos_base_por_membro` (produtor antigo) ainda elege
  `2026` na mesma fixture — sem ele, a correção poderia ser inerte e o teste passaria.
- Conservação: `residencia + outros` e `geradores + não-geradores` ao centavo, e a
  partição monetária byte-idêntica sob o estado ternário.
