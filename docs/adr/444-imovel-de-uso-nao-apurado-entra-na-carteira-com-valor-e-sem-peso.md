---
id: ADR-444
type: adr
title: "Imóvel de uso não apurado entra na carteira com valor e sem peso, e nenhuma prescrição recai sobre o que pode ser a residência"
status: Decidido
phase: A40.l122
date: "2026-10-08"
amended_at: ["2026-10-09"]
relates_to:
  - "[[ADR-439]]"
  - "[[ADR-433]]"
  - "[[ADR-193]]"
  - "[[ADR-215]]"
  - "[[ADR-420]]"
  - "[[ADR-412]]"
  - "[[ADR-431]]"
  - "[[ADR-390]]"
  - "[[ADR-337]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 444"
  - "imóvel com uso não apurado"
  - "com valor e sem peso"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-444 — Imóvel de uso não apurado entra na carteira com valor e sem peso

> **Corrigida 2026-10-09 (PR-B #2233 mergeado):** a D6 e a D8 põem o manifesto do parecer no
> expand, e nenhum PR da lane o tocou; o §Deferimento tinha a lane como dona de tudo. O texto
> original fica como evidência; a correção está em §Correção 2026-10-09. Nenhuma decisão
> (D1–D8) muda.

> Co-design 2026-10-08: `financial-planner` (a regra), `data-engineer` (o contrato e a ordem
> dos PRs), `product-designer` (a copy, que aqui é chave gravada). Executa o que a
> [[ADR-439]] deixou "Fora desta ADR": a checagem de residência por `property_id` em
> `investimentos_classes`, `top_ativos` e `instituicoes`, que falha aberta. Lane [[A40.l122]].

## Contexto

A [[ADR-439]] tornou o `patrimonio` honesto: `residencia` sai `null` com motivo quando não é
apurada. A tabela de classes e o ranking não liam esse veredito: decidiam "é a residência?" só
por `pid in residencia_property_ids`. Imóvel sem `property_id`, ou sem override, caía em
"Imóveis Investimento" — inclusive a casa.

Isso acontece em dois regimes vivos: a residência perde o id no run (a era `1.4.1` do prompt
E1.5a, [[ADR-440]]; no dogfood 8 de 9 imóveis perderam o id, e a residência só sobreviveu
porque a descrição dela tem via e número), e o workspace que nunca marcou a residência — o
default de todo workspace novo.

**Medido no run `40d1af2a` (só traços).** Ali a residência tem id e override; o defeito é
latente. No contrafactual em que só ela perde o id: `total` ×1,555,
`total_imoveis_investimento` ×1,742, o `pct` das classes financeiras desaba (Renda Fixa
22,70 → 14,60) e a casa vira **#1 do ranking como "Imóvel de investimento"**, 35,7% da
carteira, com "considere diversificação" escrito embaixo.

**Premissa recebida e refutada.** O registro da [[A40.l113]] atribuía a este elo
`total_financeiro` encolhendo e `nao_classificado_pct` subindo 3,93 → 5,61 pp. Medido: razão
1,0000 e 5,61 nos dois lados — a base dos dois já exclui imóvel físico (A37.l9). O dano não
está em KPI de base financeira; está no que se **afirma** sobre a casa: o "total investido"
que o card, o parecer e o resumo do S3 exibem, o ranking e a prescrição.

## Decisão

### D1 — Roteamento único, sobre o classificador do patrimônio

`imovel_na_carteira.classe_do_imovel_na_carteira` decide a classe de cada imóvel com o mesmo
`classificacao_do_imovel` dos splitters ([[ADR-433]] §D3); `CLASSES_IMOVEL_FISICO` é o único
conjunto lido por `pct_carteira_financeira`, `total_financeiro` e alocação. Classe de imóvel
fora dele some calada de um dos três.

### D2 — O predicado é o veredito publicado, não um quarto splitter

A residência "pode estar no desconhecido" sse `patrimonio.cobertura_classificacao_imovel
.residencia.status == nao_apurado` — os quatro motivos da [[ADR-439]] D2, **inclusive
`sem_valor`**: zero em 31/12 é venda no ano, e quem vendeu a casa marcada e comprou outra tem a
casa nova no desconhecido. O analyzer recebe o predicado como argumento tipado de `analyze()`
(é dado do run, não config), derivado do bloco que o frontend e o parecer leem.

### D3 — Com o predicado, o desconhecido entra **com valor e sem peso**

Imóvel `desconhecido` vai para a linha **"Imóveis com uso não apurado"**: aparece com o valor,
fora de `total` e de toda base de carteira, com `pct = null` e `pct_carteira_financeira = null`.
`total_imoveis_uso_nao_apurado` é publicado quando a linha existe — ausente sem ela, porque
zero chegaria ao parecer como "R$ 0,00". Valem as duas identidades, em centavos:
`total = total_financeiro + total_imoveis_investimento` e
`total + total_imoveis_uso_nao_apurado = Σ tabela`. Dentro de `total`, o "total investido"
seguiria ×1,555 com a casa dentro.

### D4 — Ranking: posição por valor, sem peso, nome pela classificação

O item mantém a posição por valor; `classe` é a linha nova, `pct_carteira = null`, e a base
dos demais o exclui. Todo item imóvel publica `classificacao_imovel`. O `nome` (rótulo sem PII,
[[ADR-337]]) segue a **classificação**, não a classe: imóvel `desconhecido` é "Imóvel com uso
não apurado" em qualquer regime — "de investimento" reafirmaria o qualificador que a
[[ADR-420]] §D1 tirou da composição.

### D5 — Nenhuma prescrição de diversificação recai sobre o que pode ser a residência

Item sem peso não concentra carteira: o alarme (25%) passa ao maior item **com peso**, e no
lugar dele entra um CTA pelo motivo — em `nao_localizada` o CTA não pede "marque", porque o
override existe. Sob `piso`, o desconhecido no #1 também não recebe "considere
diversificação": pode ser a cota da casa. Fora dos dois casos o alarme fica: o desconhecido
**sabidamente** não-residência (família que aluga) é o não-classificado do KPI de risco, e fica
no lado conservador ([[ADR-420]] §D2). Os dois produtores determinísticos da prosa
(`deriveInsight` e `charts_narrator`) leem o mesmo payload — `pct_carteira`,
`classificacao_imovel` e o `piso` publicado: a prosa morre no produtor ([[ADR-412]] §E3).

### D6 — O resíduo `apurado` + `piso` fica fora, e é declarado onde o leitor lê

Com a residência identificada, o desconhecido é não-residência **por eliminação do bem
identificado** e segue em "Imóveis Investimento". A cota do cônjuge sem id pode estar ali — é o
`piso` da [[ADR-439]] D2. Incluí-la no predicado não serve: na era `1.4.1` o `piso` liga em quase
todo run com desconhecido, e o predicado viraria "sempre", trocando um resíduo limitado a uma
cota por silêncio sistemático sobre todo imóvel de renda que perdeu o vínculo ([[ADR-420]]
§D3). A definição por eliminação e o resíduo entram na `description` do schema e no rótulo do
manifesto do parecer; o `piso` dispara o texto próprio da D5; uma fixture nomeia o resíduo.

### D7 — Contrato

Enum aditivo em `tabela_classes[].categoria` e `top_ativos[].classe`, fora de `BUCKETS`
([[ADR-193]] segue com 10). Nulidade **discriminada** por `if/then` — `pct` só é `null` na linha
nova, `pct_carteira` só no item dela (precedente: `missing_rate ⇒ taxa null`, [[ADR-390]]
§E2); alargar o tipo das dez classes cegaria o modo `strict`. Alocação ingere toda classe física como imóvel
(base patrimônio), com teste de exaustividade sobre o enum do schema. `OutrosExcessivoWarning`
mede sobre `total`, a mesma base do `pct` publicado.

### D8 — Expand → contract

O nome do enum é permanente (chave gravada e rótulo exibido). PR-A: schema, TS, leitores
null-safe, copy e manifesto, sem produtor emitindo. PR-B: produtor, gate e rebaseline.

> ⚠️ *Corrigido em 2026-10-09:* o manifesto do parecer não entrou no PR-A nem no PR-B —
> §Correção 2026-10-09, item 1.

## Consequências

- **U5 não move número.** A residência é identificada; só o `nome` dos itens desconhecidos e
  a prosa do insight mudam.
- **Regime default e residência perdida:** `total` encolhe para financeiro + imóvel
  sabidamente não-residência; a linha nova carrega o resto. É correção de medição, não melhora
  — rebaseline com `comparison_base_changed` ([[ADR-190]] §Emenda 2026-08-10).
- O golden dogfood (sem `residencia_status`, um apartamento sem override) migra esse
  apartamento para a linha nova.

## Alternativas rejeitadas

Teto com ressalva (o rótulo segue afirmando investimento e o total segue ×1,555); excluir o
desconhecido (silêncio sobre os quatro `locado` órfãos do U5); linha nova dentro de `total`
("total investido" com a casa); predicado `not publicavel or piso` (vira "sempre" na era
`1.4.1`, D6); campo extra em vez de classe (campo que nega o rótulo não tem leitor correto, e
o LLM seguiria lendo "Investimento"); eco do veredito em `investimentos` (veredito duplicado
diverge — os produtores leem o bloco publicado e a `classificacao_imovel` por item).

## Deferimento datado — 2026-10-08 (dono: [[A40.l122]])

> ⚠️ *Corrigido em 2026-10-09:* destinos por item em §Correção 2026-10-09, item 3. O item 6
> nasceu em 2026-10-09, com o #2233.

1. `uso_pessoal` e `nu_proprietario` saem do ranking ([[ADR-420]] §D1) — o subtítulo do card
   promete isso e é falso hoje. Destrava com D4 entregue.
2. Base certa do `OutrosExcessivoWarning` é `total_financeiro` (lacuna da A37.l9); pode mover o
   dogfood, então pede medição própria.
3. `golden_diff`: item `new`/`removed` com folha monetária não nula passa a exigir manifesto —
   hoje a migração entre linhas da tabela só é cobrada pela origem e pelo escalar.
4. `MemberAnalyzer` tem o mesmo defeito e não roda em produção: deleção.
5. **Superfícies LLM (PR-C, com `prompt-engineer` + `financial-planner`).** O parecer e o
   resumo da S3 recebem a tabela e o ranking; falta: regra em `narrative_hints` (sobrevive à
   evicção) que mantém a medida de concentração com a ressalva — o desconhecido segue no
   numerador ([[ADR-420]] §D2) e a red line de concentração cobra o risco —, projeção do
   regime da residência (`status` + `piso`), exceção na regra de tom da S3, guarda
   determinística contra prescrição sobre a linha sem peso, e eval do dono (2.20.0 × 2.21.0)
   num bump só do manifesto. O PR-B já melhora essas superfícies sem tocá-las: hoje elas
   recebem a casa como "Imóvel de investimento" com percentual.
6. **Baseline de print com a linha sem peso no #1** (`product-designer`). O badge "Imóveis
   com uso não apurado" é o único rótulo longo o bastante para estourar a caixa A4; ele
   quebra linha e as classes curtas seguem `nowrap`, então nenhuma baseline existente se
   move. Falta a baseline do regime, que pede fixture própria gerada no runner Linux.

## Gates

`test_imovel_na_carteira.py` (roteamento e conjunto únicos) e, no PR-B, o gate de efeito:
oráculo do estado de DB da fixture ([[ADR-439]] D7), matriz de regimes (identificada,
identificada + desconhecido, `rented`, os quatro motivos, `sem_valor` nas duas formas),
mutação do predicado (sempre verdadeiro e sempre falso), conservação em centavos e coerência
entre a classe do item no ranking e a linha da tabela.

## Correção 2026-10-09 — o manifesto ficou fora do expand, e o adiado ganha destino

1. **D6 e D8.** Nem o #2096 nem o #2233 tocaram `config/prompts/`: o manifesto do parecer não
   declara a linha nova nem o resíduo. O que a D6 põe no rótulo do manifesto e a D8 no PR-A vai
   para o bump único do manifest, na [[A40.l8]]. A `description` do schema e a fixture entraram.
2. **Item 5 reconciliado.** A [[A40.l123]] (#2117, manifest 2.21.0) já leva ao parecer o veredito
   da residência (`status` e `motivo`) e a ressalva da concentração. O eval 2.20.0 × 2.21.0 não
   existe mais: o eval do dono acompanha o bump da l8.
3. **Destinos.** Item 1: PR-D da [[A40.l122]], P1. Do item 5, o alcance (escape de
   `total_imoveis_uso_nao_apurado`, hint de `ratios`, regra em `narrative_hints`, bump) vai para a
   [[A40.l8]]; a guarda determinística, a exceção de tom da S3 e os itens 2, 3, 4 e 6 vão para
   [[PLAN-report-trust]] §Deferimentos da A40.l122.
