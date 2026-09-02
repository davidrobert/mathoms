---
id: A40.l114
type: lane
title: "O ano de referência afirma um 31/12 que ainda não fechou, e o eixo zera imóveis, veículos e a dívida do titular"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1961
ship_date: "2026-09-01"
priority: P0
branch_slug: a40-l114-ano-de-referencia-sem-documento-atras
owner: data-engineer
depends_on: []
adrs: ["[[ADR-301]]", "[[ADR-401]]", "[[ADR-431]]", "[[ADR-420]]", "[[ADR-433]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p0, area/pipeline, area/financial-planning]
---

# A40.l114 — `ano-de-referencia-sem-documento-atras`

> ⚠️ **O slug do arquivo carrega a premissa falsa** e foi mantido porque é
> identificador (`branch_slug`, PRs, links). O ano espúrio **tem** documento atrás —
> ver §Medição. O `title:` foi corrigido; o filename, não.

> **Origem:** `RR9-02` (Cadeia B) da rodada unificada **U5**
> ([[REPORT-REVIEWS-active]] §r9). **CONFIRMADO** por medição A/B entre dois runs sobre
> corpus idêntico, com o mecanismo lido no produtor.

## O que está publicado

`endividamento.total_dividas` sai **zero** enquanto `endividamento.dividas` lista
**4 financiamentos imobiliários** com saldo. `percentual_patrimonio` sai **zero** junto, e
`score.componentes[taxa_endividamento]` sai `valor=0,0 · peso=1,5 (**18,8%** do score) ·
**nota=10,0** · status="emitted"`. A superfície publica *"Endividamento Mínimo/Nulo"* como
**Ponto Forte** em 2 inventários. `patrimonio.liquido` fica **idêntico ao bruto**.

Nas três rodadas unificadas anteriores o total saía correto. **Três totais de dívida
coexistem nos artefatos deste run**: o publicado (zero), o da lista de itens, e o de
`patrimonio_por_ano.total_dividas` — três valores distintos para a mesma pergunta.

## Medição 2026-09-01 — a premissa do enunciado está REFUTADA em dois pontos

> Reproduzido ponta a ponta sobre os artefatos do run `40d1af2a` (os 10 `E1.5a`, o
> `consolidate_baseline` e o `analyze_finances`), com as funções do produtor chamadas
> direto sobre o baseline decifrado.

O enunciado abaixo dizia: *"O LLM carimbou o **ano seguinte** ao da declaração mais
recente do corpus. Nenhum documento é desse ano."* **Os dois pontos são falsos.**

1. **O LLM acertou as três declarações.** Exercício 2026 → `ano_referencia=2025`;
   exercício 2025 → 2024; exercício 2024 → 2023. A conversão exercício→ano-calendário
   saiu correta em 3 de 3. O ano espúrio **não nasce de erro de IRPF**.
2. **O `2026` vem de um documento que É de 2026.** É o
   `2ef2565f3634_itau_informe_previdencia_privada_202603_202603`, e o próprio
   `_meta.notes` do extrator descreve o que ele é: *"tela de posição consolidada de
   investimentos do Itaú (extrato online), capturada em **29/03/2026**"*. Ele carimba
   `resumo.ano_referencia=2026` e 3 itens com `ano=2026`, que na consolidação viram
   `valores_31_12: {"2026": …}` com `ano_base: null`.

**O defeito real é de tipo, não de alucinação:** uma posição de **29/03/2026** foi
rotulada como posição de **31/12/2026** — um 31/12 que ainda não ocorreu (a medição é de
2026-09-01). `valores_31_12[ano]` afirma posição em 31/12 fechado; março não é 31/12.

**Consequência para o critério de aceite nº 1**, que prescrevia *"se excede o máximo
observado nos documentos, o observado prevalece"*: esse corte é **inerte neste caso** —
`2026` **é** o máximo observado. Implementado como escrito, o gate passa verde e o número
publicado não se move. O invariante que pega a classe é **temporal**, não documental.

### O elo que faltava na cadeia

`resolve_value_year` não propaga o ano do resumo: ele devolve `_max_value_year`, o **maior
ano entre os itens**. Ele chega a `2026` porque `investimentos_consolidados` tem chave
`2026` — os 3 itens da tela de março. É por aí que o ano espúrio entra no eixo, e é por
isso que consertar só o `resumo.ano_referencia` **não bastaria**.

| medida | valor |
|---|---|
| anos em `imoveis_consolidados` / `veiculos_consolidados` / `dividas` | 2023–2025 / 2024–2025 / 2024–2025 |
| anos em `investimentos_consolidados` | 2023–**2026** |
| `_resolve_summary_year` | `2026` |
| `resolve_value_year` | `2026` |
| `anos_base_por_membro` | titular `2026` · cônjuge `2023` |
| `_split_dividas(…, "2026")` | **`(0.0, 0.0)`** |
| `_split_dividas(…, "2025")` | `(230459.13, 0.0)` |
| publicado: `endividamento.total_dividas` | `0.0` — com 4 itens somando `230459.13` |

## A cadeia, elo a elo

1. `pipeline/stages/extract_baseline.py:96` — `"ano_referencia": output.reference_year`,
   com `_meta.source: "E1.5-llm"`. **É saída crua do LLM, e nada a confronta com os anos
   que os documentos têm.** O valor derivado do documento é computável **no mesmo arquivo,
   linha 173** (`max(years) if years else 0`).
2. O LLM carimbou o **ano seguinte** ao da declaração mais recente do corpus. Nenhum
   documento é desse ano.
3. `scripts/consolidate_baseline.py` **re-rotula** `patrimonio_por_ano` para o ano novo com
   o conteúdo **byte-idêntico** ao do run anterior (`total_bens` e `total_dividas` iguais).
   O ano mudou; os números, não. Cada dívida mantém o `ano_referencia` **correto** e
   `saldo_31_12` com as chaves dos anos que existem.
4. `resolve_value_year` propaga o ano carimbado.
5. `pipeline/domain/services/patrimonio_resolvers.py:561` `_split_dividas` faz
   `safe_float(saldo.get(ano_ref, 0))` — **sem fallback** ⇒ zero nas quatro.

## O irmão do mesmo campo TEM fallback — e é por isso que o relatório se contradiz

`_resolve_saldo` (`pipeline/domain/services/endividamento_analyzer.py:140`, [[ADR-401]])
lê o mesmo `saldo_31_12` e **cai para `anos[-1]`** quando `ano_ref` falta. Daí a lista de
itens continuar somando o valor certo **na mesma página** em que o total sai zero: **dois
leitores do mesmo campo discordam sobre o que fazer quando o ano não existe**, e cada um
alimenta uma superfície diferente.

## Correção de atribuição herdada de comentário

O comentário em `endividamento_analyzer.py:138` nomeia `patrimonio_resolvers._total_dividas_for`
como *"defeito vivo"*. Ele **é** defeito real — `safe_float` sobre o objeto por ano
([[ADR-301]]) devolve zero — mas está **dormente**: este corpus segue
`build_members_from_consolidated`, que usa `_split_dividas`. A prova de que
`_total_dividas_for` não é a causa **deste** zero: `saldo_31_12` já era objeto por ano no
run anterior, quando o número saiu **certo**. Quem for consertar deve tratar os dois — o
que dispara e o que espera.

## Por que é P0, e por que a ADR da própria sprint dá o remédio

A [[ADR-431]] decidiu que **publicar zero onde o valor não foi apurado é afirmação sobre o
patrimônio da pessoa** e deve virar `null` + declarado. O total de dívida faz exatamente o
proibido, na direção **inversa** — subdeclara **passivo** em vez de ativo — e ainda credita
**nota máxima** por isso. Amortizar-vs-investir é a decisão que o relatório existe para
informar, e ela sai invertida.

## Entregue 2026-09-01 — medição A/B sobre os MESMOS artefatos do run publicado

> Reprocessamento de `E1.5c` para a frente sobre os 288 artefatos do run `40d1af2a`,
> sem re-rodar o `E1.5` (a extração churna por item entre runs, e re-rodar misturaria
> o efeito do conserto com churn de extração).

| campo publicado | run `40d1af2a` | depois | delta |
|---|---:|---:|---|
| `patrimonio.bruto` | 2.012.174,02 | **3.879.177,72** | +92,8% |
| `patrimonio.dividas` | 0,00 | **230.459,13** | — |
| `patrimonio.liquido` | 2.012.174,02 (= bruto) | **3.648.718,59** | ≠ bruto |
| `patrimonio.veiculos` | 0,00 | **227.476,00** | — |
| `patrimonio.imoveis_investimento` | 701.170,57 | **2.340.698,27** | +233,8% |
| `ratios.taxa_endividamento_pct` | 0,0 | **5,94** | — |
| `endividamento.total_dividas` | 0,00 | **230.459,13** | = Σ dos 4 itens |
| Ponto Forte de dívida | *"Endividamento Mínimo"* | *"Endividamento Controlado"* | — |

**Correção de atribuição na manchete do `U5` — e correção da minha própria correção.**
A rodada creditou `patrimonio.bruto −48,1%` ao conjunto das duas cadeias. A medição
isola o eixo de ano como causa: 2.012.174,02 ÷ 3.879.177,72 = **0,519**, o `−48,1%`
publicado ao centésimo.

**Mas o crédito não é desta lane.** A [[A40.l113]] mergeou (`c551e832`, [[ADR-433]])
enquanto esta estava em revisão, e a eleição de ano-base **por classe de ativo** que ela
introduziu resolve o corpus **sozinha**. Medido, pós-rebase, neutralizando os meus dois
consertos um a um sobre os mesmos 288 artefatos: os números publicados ficam
**idênticos** com qualquer um deles desligado. São dois consertos independentemente
suficientes, e o que chegou primeiro leva.

O que **permanece** zero depois de tudo é `patrimonio.residencia` e
`patrimonio.imoveis_geradores` — a classificação de imóvel, também da [[A40.l113]].

### O que esta lane entrega depois disso, e é dela

A tabela acima descreve o **defeito**, não o crédito. Com a [[ADR-433]] viva, o filtro
temporal fica **inerte neste corpus** — ele guarda o eixo do **domicílio**, que é o
fallback de classe sem ano declarado, e não a eleição por classe. O que sobra e é
genuinamente desta lane:

- os **dois leitores divergentes** do mesmo `saldo_31_12` viram um produtor único
  (`saldo_divida_resolver`), com a Rota C — a contradição estrutural morre, e não só
  este sintoma;
- o **tripwire** de contradição interna, que pega a classe **independentemente da causa**;
- a **supressão no score** (`dividas_nao_apuradas`, `nota: null`, `status: suprimido`,
  peso fora do denominador, `piso`) e os dois analyzers que reintroduziam o zero;
- `_total_dividas_for`, o defeito **dormente** que a lane pediu explicitamente;
- o `review_reason` `domain.ano_referencia_nao_fechado`.

### Residual descoberto e não consertado (território da [[ADR-433]])

A eleição por classe isola as classes entre si, mas **não protege uma classe de si
mesma**: um item da própria classe rotulado num 31/12 não fechado ainda elege o ano dela
e zera os irmãos. Tentei filtrar dentro de `_anos_do_membro_na_classe` e **recuei** — o
filtro sacrifica o item de meio de ano quando a classe **só** tem ele, e escolher qual
item sacrificar é decisão da [[ADR-433]], que é `Decidido`. Fica como follow-up com dono
nomeado, não como mudança silenciosa em ADR alheia.

### O que NÃO foi feito, e por quê (as duas rotas medidas e recusadas)

1. **Rebaixar o ano no produtor** (`extract_baseline` carimbando 2025 no lugar de 2026)
   — recusado. Publicaria a posição de 29/03/2026 como se fosse de 31/12/2025, com 9
   meses de aporte e rendimento embutidos, num campo que alimenta série temporal e IF.
   É o pior dos desfechos: plausível e auditável só contra o documento original. O item
   segue rotulado com o ano que ele **de fato tem**; o que muda é que esse ano não
   define mais o eixo.
2. **Filtrar o documento da varredura do E1.5** (ele tem stage próprio,
   `extract_informes_anuais` · [[ADR-238]]) — recusado **por medição**. Aquele caminho
   captura só a fatia de previdência (`saldo_31_12: "18715.24"`) e a **mislabela** como
   `ano_base: 2025` — o mesmo erro de tipo, na direção oposta. O CDB-DI (116.374,26) e
   os Cofrinhos (206.491,70) não são capturados por caminho nenhum: **R$ 322.865,96**
   sairiam do baseline. Filtrar trocaria o defeito de lugar.

### Follow-ups medidos, sem lane (inventário)

- **INV-B (evidencial).** O invariante temporal não pega posição de **30/06/2025** lida
  hoje: `2025 ≤ 2025` passa, e vira "posição de 31/12/2025" — a mesma mentira, um ano
  atrás e **invisível**. Foi o calendário que tornou este caso visível. O carimbo
  `31/12/AAAA` deveria exigir evidência no documento ([[ADR-394]] D1 aplicada ao eixo
  **tempo**, que hoje não tem autoridade declarada).
- **O prompt do E1.5 autoriza o defeito.** `pipeline/llm/prompts/e15_baseline.py` fecha
  com *"Se o valor de 31/12 do ano-base estiver disponível, use-o. **Senão, use o valor
  mais recente**"*. O LLM não errou — obedeceu, sobre um documento que não é declaração.
  Mudar a linha exige bump de `PROMPT_VERSION` ([[ADR-233]]) — escopo do `prompt-engineer`.
- **`extract_informes_anuais` mislabela a mesma tela** (item 2 acima): `ano_base: 2025`
  sobre captura de 29/03/2026.
- **`scoring.json` declara `taxa_endividamento` com `unidade: "% renda mensal
  comprometida"` e `range 5–50`** (régua de renda comprometida), mas o que a alimenta é
  `dívidas ÷ patrimônio bruto`. São grandezas diferentes: a nota deste componente é de
  qualidade duvidosa **mesmo com o input certo**.
- **`taxa_juros_aa` é `null` em todo run medido**, então a prescrição amortizar-vs-investir
  segue incompleta depois deste conserto — o saldo é necessário, a taxa é o que decide.
  O `indexador` do baseline (que separa TR de IPCA+, e resolve teto-vs-piso no
  carimbo de carry-forward) também não é lido pelo E5.

## Critério de aceite

1. ~~`ano_referencia` do LLM é **reconciliado** contra os anos presentes nos documentos: se
   excede o máximo observado, o valor observado prevalece e a divergência é declarada
   (`review_reason`), nunca silenciosa.~~ **Re-especificado 2026-09-01** — o corte por
   "anos observados nos documentos" é **inerte** (ver §Medição): o remédio tem de ser o
   invariante **temporal** — chave de `valores_31_12`/`saldo_31_12` e `resumo.ano_referencia`
   afirmam 31/12 **fechado**, logo não podem alcançar ano ainda em curso. O eixo tem de ser
   corrigido onde ele é **resolvido** (`resolve_value_year`/`_max_value_year`), não só no
   `resumo`. Divergência declarada em `review_reason`, nunca silenciosa.
2. `_split_dividas` **não publica zero** por ano ausente: ou cai para o ano mais recente
   disponível como o irmão `_resolve_saldo`, ou declara `não apurado` no espírito da
   [[ADR-431]]. As duas rotas exigem decisão do `financial-planner` — subdeclarar passivo
   e omitir passivo têm consequências diferentes na prescrição.
3. `score.componentes[taxa_endividamento]` **não emite nota** sobre total suprimido:
   `status` reflete a supressão, e o peso sai do denominador.
4. Tripwire: `total_dividas == 0` com `len(dividas) > 0` é **contradição interna** e reprova
   antes de publicar. Custa uma linha e pega a classe inteira.
5. Regressão: fixture com `ano_ref` fora das chaves de `saldo_31_12`; asserção de que o
   total publicado **não** é zero silencioso e que os três produtores concordam.
