---
id: ADR-439
type: adr
title: "Balde de imóvel sem classificação apurada sai `null` com veredito, e zero só com evidência de zero"
status: Decidido
phase: A40.l113
date: "2026-10-08"
relates_to:
  - "[[ADR-433]]"
  - "[[ADR-215]]"
  - "[[ADR-431]]"
  - "[[ADR-394]]"
  - "[[ADR-412]]"
  - "[[ADR-420]]"
  - "[[ADR-353]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 439"
  - "veredito do balde de imóvel"
  - "zero de imóvel só com evidência de zero"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-439 — Balde de imóvel sem classificação apurada sai `null` com veredito, e zero só com evidência de zero

> Co-design 2026-10-08: `financial-planner` (regra de domínio), `data-engineer` (contrato e
> ordem dos PRs), `product-designer` (superfície). Executa o item 1 do §Deferimento da
> [[A40.l113]] e substitui o item 2 por um gate de teste. A [[ADR-433]] §D3 continua de pé;
> o que cai é a prescrição dela de suprimir "sobre a escada da [[ADR-353]]".

## Contexto

A [[ADR-433]] §D3 criou o estado `desconhecido` e uma função que mede a fatia,
`cobertura_classificacao_imovel`. **Nenhum código de produção a chamava** — só o teste. A fatia
não era publicada, e `residencia`/`imoveis_geradores` seguiam saindo `0,00` para *"não sei
qual é"*.

No run `U5`, já com o eixo de ano corrigido, `imoveis_geradores` sai zero com **quatro**
overrides `locado` gravados cujo `property_id` não aparece no run. Com `imoveis_no_if = true`
esse zero entra em `cat2_efetivo` e no IF.

A perda de identidade **não é churn aleatório**. Os dois runs anteriores sobre os mesmos três
PDFs (prompt E1.5a `1.3.0`) resolviam os quatro imóveis, com logradouro na descrição em 4 de 4.
O `U5` é o primeiro run na `1.4.1`, cuja regra de "transcrição literal da discriminação"
saiu com efeito declarado **não medido**; nele, nenhum dos 8 itens sem id traz logradouro. É
regressão viva desde 2026-09-01, e o conserto de causa (âncora estruturada) é lane própria.
**Esta ADR decide o que se publica enquanto a identidade falhar, por qualquer causa.**

Dois fatos de leitura fecham o quadro:

- `workspaces.residencia_status` (`owned | rented | undeclared`) — a [[ADR-215]] decidiu que
  `rented` esconde a linha e `undeclared` mostra `—` com CTA. O campo **nunca chegou** ao E5.
- Publicar `null` sem migrar leitor não funciona: `generate_narratives` soma
  `imoveis_investimento + residencia` (quebra), e o `HeroKpiGrid` e
  `_renda_passiva_fora_do_investivel` coagem `null` para 0 e repetem o zero falso.

## Decisão

### D1 — Veredito por balde, com produtor único

`veredito_balde_imovel.vereditos_de_imovel` decide; `patrimonio.cobertura_classificacao_imovel`
publica a partição do valor (residência, geradores e não-geradores **identificados** +
desconhecido, todos do mesmo laço), o `residencia_status` ecoado e, por balde,
`{status, motivo, piso}`. O `status` reusa o vocabulário de `cobertura_investimentos[]`
(`apurado | zero_apurado | nao_apurado`, [[ADR-394]] §Emenda (b) D7).

### D2 — Residência: zero numérico só com a palavra da família

| situação | publica | motivo |
|---|---|---|
| residência identificada (`> 0`) | número; `piso` se há imóvel em aberto | — |
| `rented` | `0` | — |
| override `residencia_principal` cujo imóvel não está no run | `null` | `nao_localizada` |
| override presente, imóvel sem valor (zero declarado ou não apurado) | `null` | `sem_valor` |
| `owned`, sem override | `null` | `nao_classificada` |
| `undeclared` ou status ausente | `null` | `nao_declarada` |

IRPF sem imóvel não prova ausência de casa: há holding, bem comum declarado só no IRPF do
cônjuge que não chegou, usufruto. A residência identificada sai como **piso**: sem
`property_id`, o dedup da [[ADR-246]] não roda, e a cota do cônjuge pode estar no balde
desconhecido.

### D3 — Geradores e não-geradores vão juntos

Imóvel **em aberto** é o de classificação desconhecida que pode valer algo: valor `> 0` ou não
apurado ([[ADR-431]]). Zero declarado em 31/12 é venda no ano, e não conta.

| situação | `imoveis_geradores` e `imoveis_nao_geradores` |
|---|---|
| nenhum imóvel em aberto, nenhum gerador sem valor | números (`apurado` / `zero_apurado`) |
| imóvel em aberto | ambos `null` — `vinculo_perdido` se há override gerador sem imóvel no run, senão `nao_classificados` |
| gerador presente sem valor | ambos `null` — `sem_valor` |

O par não publica piso: campo que às vezes é valor e às vezes é piso não tem leitor
correto. O piso sai com nome próprio no bloco (`geradores_identificados`).

### D4 — A escada da ADR-353 não decide aqui

A [[ADR-353]] está `Proposto` e foi calibrada para cobertura de categorização de **gasto**.
A residência é um item só, e qualquer fatia desconhecida pode contê-la: suprimir pela escada
apagaria uma residência verdadeira já identificada. O veredito é categórico.

### D5 — A partição monetária não se move

`bruto`, cat_2, concentração, a soma da composição e a imobilização ficam byte-idênticos
([[ADR-433]] §D3, [[ADR-420]] §D2). A linha "Residência" da composição mantém `valor: 0` na
partição e ganha `estado`/`motivo`; só some quando o zero é `rented` ([[ADR-215]] P5).
`valor: null` na linha quebraria a soma da composição e dois leitores (`validate_cross`
CV2 e `generate_narratives`).

### D6 — IF: piso declarado, sem supressão

A [[ADR-412]] §Emenda E3 vale: `if_pct`/`if_gap` nunca viram `None`, o cone não é suprimido,
e o prazo conservador é o mais longo. Com o desconhecido fora dos geradores, o IF publicado
**já é** esse extremo. `cat2_efetivo`/`investivel_efetivo` seguem número.

No regime `imoveis_no_if = false`, o termo de renda de fora do investível sai `None` em vez
de `sem_gerador_excluido`, que afirmava ausência. O contrato já lê a chave ausente como não
medido, então não nasce enum novo; o motivo mora no veredito do bloco. A meta não se move. A
sub-linha do KPI de investível lê o veredito e diz a direção do erro.

### D7 — O gate é de teste, não de runtime

O gate literal da lane (*"geradores zero com override `locado` gravado"*) dá falso-positivo
no imóvel de renda vendido: o override órfão persiste, porque `property_identity` não tem
`last_seen` e override só se grava. Um `raise` abortaria todo run do workspace, para sempre.
O gate vira teste, com oráculo tirado do estado de DB da fixture, mutação (publisher devolve
0 ⇒ vermelho) e matriz de regimes. Em runtime fica `review_reason` WARN
(`domain.classificacao_imovel_nao_apurada`, advisory) só quando há evidência contrária: para
geradores, override gerador sem imóvel no run **e** imóvel em aberto (`vinculo_perdido`); para a
residência, o override `residencia_principal` sem imóvel no run (`nao_localizada`) — que também
avisa quem vendeu a casa e não atualizou o status.

## Consequências

- **Números que mudam (PR do flip):** `residencia` vira `null` onde não foi declarada ou não
  foi localizada; o par de geradores vira `null` onde há imóvel em aberto. É correção de
  medição, não melhora. O changelog entre relatórios ([[ADR-190]]) compara
  `patrimonio.liquido`, `patrimonio.bruto` e afins — campos que a partição intacta não move —,
  então `comparison_base_changed` não precisa disparar, e nada aqui o liga.
  ⚠️ *Corrigido no closeout de 2026-10-08:* a versão mergeada dizia que o rebaseline "marca
  `comparison_base_changed`". O flag é derivado em runtime da presença de
  `consolidacao_cross_documento` nos dois lados do par; rebaseline nenhum o marca.
- `golden_diff.py` passa a enxergar número→`null`. Sem isso, a supressão (ou uma regressão
  para `null`) rebaselinaria sem waiver.
- **Expand→contract:** schema e leitores aceitam `null` antes de o produtor emitir.
- **Fora desta ADR:** a âncora estruturada (lane P0 nova); a normalização do `codigo_rfb`
  (`01-11` estoura o `VARCHAR(4)` no Postgres, PR próprio); a checagem de residência por
  `property_id` em `investimentos_classes`, `top_ativos` e `instituicoes`, que falha aberta;
  e o teste "classificação sobrevive ao re-upload", que a [[ADR-215]] declara e o repo não tem.

## Alternativas consideradas

1. **Escada da ADR-353** (o deferimento original) — rejeitada (D4).
2. **Gate literal com `raise`** — rejeitada (D7).
3. **Suprimir `if_gap`/prazo/cone por teste de sensibilidade** — rejeitada: contraria a
   [[ADR-412]] §E3, e o publicado já é o extremo conservador.
4. **`valor: null` na linha da composição** — rejeitada (D5).
5. **Só consertar a identidade** — rejeitada: a identidade falha por várias causas (prompt,
   grafia do código RFB, compra e venda). Sem publicação honesta, a próxima falha volta a
   publicar zero em silêncio.

## Gates

- `tests/unit/pipeline/test_veredito_balde_imovel.py` — a matriz de D2/D3, incluindo o imóvel
  de renda vendido (zero verdadeiro) e o desconhecido sem valor apurado (em aberto).
- `tests/test_veredito_imovel_gate_adr439.py` — o gate da D7: matriz de 7 regimes (U5, nada
  classificado, aluga, vendeu o imóvel de renda, tudo classificado, residência órfã, sem
  imóvel), oráculo tirado do estado de DB da fixture, e mutação do veredito para "sempre
  apurado" que deixa o gate vermelho.
- `tests/test_golden_discrimina_classificacao_de_imovel.py` — o regime `toda_classificada` é
  o único caso do golden com o par numérico; os outros dois o publicam `null`.
- `check_schema_manifest_drift`, `check_view_model_contract` e o `golden_diff`, que desde o
  #2051 cobra manifesto de campo monetário que vira `null`.
