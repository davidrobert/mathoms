---
id: A40.l50
type: lane
title: "Abertos da investigação de exposição cambial: inventário verificado do que não foi atacado"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l50-abertos-exposicao-cambial
adrs:
  - "[[ADR-379]]"
  - "[[ADR-380]]"
  - "[[ADR-224]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/report
  - area/pipeline
  - area/financial-planning
---

# A40.l50 — `abertos-exposicao-cambial`

> **Origem:** investigação do card Exposição Cambial (2026-08-12, dogfood `5@5.com`,
> report `7a7d7115`, run `ee124571`). O P0 fechou no **PR #1393** (`d1b7c97c`). Esta
> lane é o **inventário do que sobrou** — nada aqui está sendo atacado.

Todos os itens passaram por **refutação adversarial independente**: 20 achados
julgados, 18 sobreviveram, 2 refutados. Onde o refutador estreitou o enquadramento, o
texto abaixo registra a versão **corrigida**, não a alegação original — vários números
da primeira rodada estavam certos no mecanismo e errados na moldura.

## Já fechou — não reabrir

Entregue em `d1b7c97c`: V2 lê a chave que o E5 emite; "sem base" deixou de ser "zero"
(campos `null`); precedência do card por **dado**, não por resposta; **pinagem por run**
(83 de 84 relatórios exibiam outro momento patrimonial); gate
`dev/check_artifact_read_keys.py`; [[ADR-380]], [[ADR-379]] e retratação da emenda
RV2-08 da [[ADR-224]].

## Abertos que mordem hoje

### ~~P0 · `consolidate_baseline` re-consolida o run anterior~~ — FECHADO em 2026-08-12

> **Re-medido em 2026-08-14: já estava corrigido quando esta lane nasceu.** O
> #1395 (`608163ef`, A40.l42) mergeou às 09:24Z — **16 min depois** do #1409
> que abriu esta lane (09:08Z). A l50 declarava "nada aqui está sendo atacado";
> o item 1 estava sendo atacado em paralelo, sem que nenhum dos dois lados
> soubesse.
>
> O fix inverteu a ordem: `consolidate_baseline.py:763` lê `extract_baseline`
> **primeiro** e só cai em `consolidate_baseline` quando não há E1.5 no
> workspace. Trava de regressão em
> `tests/test_consolidate_baseline_stage_direct.py::test_rerun_consolida_e15_fresco_nao_o_proprio_output_anterior`,
> que exige safra 2025 no `itens` de saída — 5 testes verdes.
>
> A prova citada abaixo (`load(15152)['itens'] == load(14649)['itens']`) mediu
> artefatos do run `ee124571`, **anterior** ao fix. O diagnóstico estava certo;
> o alvo já não existe. Texto original preservado — snapshot datado não se
> reescreve.


`scripts/consolidate_baseline.py:725` lê `store.read("consolidate_baseline", …)`
**antes** de `extract_baseline` (727). O stage está em `_WORKSPACE_SCOPED_STAGES`
(`db_artifact_store.py:207`), então `read()` cai em `_get_latest_in_workspace` e devolve
o consolidado de um run anterior; `consolidate()` vê `itens` presente e re-consolida
material velho.

Prova direta: `load(15152)['itens'] == load(14649)['itens']` é **True** — o consolidado
do run `ee124571` é byte-idêntico ao do run de 2026-08-05, cujo `_meta` descreve a
declaração **ano-calendário 2024**. O extract fresco do mesmo run (15151) tem 89 itens
`{2025:45, 2024:33, 2023:11}`; o consolidado tem 67 `{2024:52, 2023:11, 2025:4}`.

**Chega à tela:** `patrimonio.dividas` = R$ 234.792,61 — o total de **2024** (a
declaração 2025 traz R$ 230.459,13).

*Enquadramento corrigido:* congela a via E1.5→E1.5c (itens, consolidados, dívidas,
resumo). Duas vias seguem frescas — `extract_irpf_full` alimenta `irpf_kpis`, e
`informe_pf_saldos_31_12` vem de `extract_informes_anuais`. Título honesto: **bens e
dívidas do IRPF 2025 nunca entram**, não "a declaração inteira".

É o achado mais grave do lote e **não tem relação com o card** — merece lane própria.

### P0 · Rodapé de PTAX — ROTEADO para a [[A40.l39]] em 2026-08-14

> **Re-medido em 2026-08-14, com co-design `financial-planner` + `senior-cto`.**
> O defeito é real e está vivo, mas **não é lane desta**: a [[A40.l39]] —
> *"o header '31/12' mente para 10 de 16 linhas — separar visão corrente da
> fiscal"* ([[ADR-382]]) — está `in_progress` com duas branches e já deleta esta
> tabela. Abrir PR aqui conflita no arquivo que ela está partindo.
>
> **Correção de enquadramento que a l39 herda:** a linha de extrato tem **dois**
> erros, não um — taxa errada *e* **data errada**. O saldo é do fim do último
> período reconciliado (26/03, 22/07, 11/08/2026), não de 31/12. Por isso
> *"converter tudo pela PTAX de 31/12"* está **vetado**: aplicar PTAX de
> 31/12/2025 a saldo de agosto/2026 não aplica a regra fiscal, fabrica um número
> que não corresponde a posição nenhuma, com aparência de autoridade fiscal.
> Só o par (saldo de 31/12 × PTAX de 31/12) é defensável sob o nome da coluna.
>
> **Os R$ 4.308,60 não são queda de patrimônio.** São artefato de comparar duas
> datas; o patrimônio corrente deve seguir em cotação corrente. Não cabe ressalva
> de "seu patrimônio foi corrigido" — cabe nota de não-aditividade entre as duas
> visões, que a spec do PR-b da l39 já prevê.
>
> **Regra fiscal, para o registro:** saldo em ME em 31/12 usa **PTAX de compra do
> último boletim de fechamento do ano** — já sementada em `market_rates`
> (`a33l2ptax3112_seed_ptax_compra_31_12.py`, USD 5,5018 · EUR 6,4679 em
> 31/12/2025). Taxa de venda é para aquisição de bem; **rendimento** recebido usa
> outra regra ainda (PTAX compra do último dia da 1ª quinzena do mês anterior) —
> não replicar a taxa de 31/12 em card de renda.
>
> Texto original preservado abaixo — snapshot datado não se reescreve.


`PosicaoInformeCard.PtaxFootnote` dispara pelo `ano_base` das linhas de informe (todas
BRL) e cobre visualmente as 4 linhas em moeda estrangeira, que vêm de **extrato** e
foram convertidas pela taxa corrente (5,80/6,35), não pela PTAX de 31/12/2025.

Medido no report `7a7d7115`: sob "Valor em 31/12" aparecem R$ 83.820,33 em USD onde a
PTAX daria R$ 79.510,80 — **R$ 4.308,60 a mais**, com uma afirmação falsa de
proveniência ao lado.

Não é falta de dado: a PTAX 31/12/2025 (5,5018 USD · 6,4679 EUR) **está no DB**. É o
caminho de extrato que não a consulta. `CaixaDetalhe` (`patrimonio_types.py:175-181`)
não tem campo para taxa nem data, enquanto `baseline_informe_merger._convert_to_brl`
grava `taxa_ptax_aplicada`/`ptax_data`/`ptax_status`.

### P1 · Duas respostas para "quanto está fora do real" na mesma página

`investimentos.tabela_classes` traz `Internacional = R$ 34.918,47` (4,19% da carteira
financeira), renderizado por `InvestimentosClasseCard.tsx:25`; `exposicao_cambial` traz
R$ 83.869,92 (6,45% do investível), com 4 detalhes, todos `tipo=caixa`. Nenhum contém o
outro.

Causa reproduzida: `classify_asset` sobre as 18 posições do E4 dá Ações BR 6, Renda Fixa
5, Cripto 5, Fundos 2 e **zero Internacional** — o braço de ativos contribui 0. O bucket
"Internacional" vem de `investimentos.fonte = 'irpf_bens'`.

*O fix não é somar.* São recortes de datas diferentes com sobreposição não medida: o
IRPF é foto de 31/12/2025 (quando os extratos FX somavam ~US$ 4.813) e o card usa saldos
correntes. O item "DEPÓSITO EM MOEDA ESTRANGEIRA — U$ 6.524,00" é provavelmente a mesma
conta já contada. **Reconciliar e rotular as duas visões**, não adicioná-las.

### P2 · Uma cotação de 2026-04-27 para saldos de três datas diferentes

`TODAY` (`analyze_finances.py:188`) é o único argumento de data que chega em
`get_market_rate`, e `get_latest_on_or_before` devolve a linha de 2026-04-27. Os saldos
convertidos por ela têm `periodo_cobertura.fim` de 26/03, 22/07 e 11/08.

*Precisão do refutador:* não é "a mais recente da tabela" por desenho — é
`get_latest_on_or_before(pair, TODAY)`, que coincide com a mais recente só porque não há
linha posterior. Semear uma cotação futura muda o comportamento sem mudar o código.

Hoje são **106 dias** de defasagem, e **não existe mecanismo de atualização de câmbio**
no produto — a linha veio de seed de migration. Não flipa o tier deste workspace
(exigiria +55% em USD/BRL), mas o câmbio alimenta a meta `dolarizacao`, e ali o erro
vira **valor de aporte**. Solução: refresh de PTAX no padrão Celery + TTL do FIPE
(ADR-239 D7 / A18.l3); a escada de defasagem (≤30 normal · 31-180 `defasado` · >180 tier
suprimido) é rede de segurança, não substituto.

**Não vira `needs_review`** — esse estado pede que o *usuário* conserte dado que é dele;
aqui quem não buscou a cotação foi a plataforma ([[A40.l22]]).

### P2 · Os dois goldens mais caros são cegos a este eixo

`dogfood_view_model.json:304` tem `exposicao_cambial` vazio, `:517` `caixa_detalhes []`
e `:519` `caixa_me_brl 0` — a fixture não tem **um centavo** em moeda estrangeira, então
o estado correto e o bugado são o mesmo byte.

*Estreitamento do refutador:* o produtor **tem** cobertura viva
(`test_exposicao_cambial_analyzer.py`, 8 testes; `test_e5_analyzer_adapter.py:875-915`
fixa a conversão USD), e o bug de 3 meses morava no **consumidor**, que golden de
produtor não cobriria por desenho. O buraco real é mais estreito:

1. a fiação `adapter → compute_exposicao_cambial → payload` não tem teste unitário;
2. `exposicao_cambial` **não está em `required`** do `e5_analysis.schema.json`
   (`required = [score, patrimonio, fluxo_caixa]`), então nem a validação strict pega a
   remoção do bloco — só o diff do snapshot.

Remédio: **uma conta em USD na fixture**, não reprojetar os goldens.

### P2 · `has_foreign_in_e3` é all-or-nothing por workspace

`e5_analyzer_adapter.py:954` — se **qualquer** extrato tem moeda USD/EUR, o fallback
[[ADR-245]] não roda, e a conta de Ilhas Cayman (sem extrato nenhum nos 111 artefatos de
reconcile) fica fora por construção.

*Correções do refutador:* (1) os R$ 34.918,47 citados são valores de **2024**, herdados
do baseline stale do achado acima — na declaração 2025 os mesmos itens dão ~R$ 34,8 mil;
(2) o dinheiro **não é descartado do relatório** — esses itens são o bucket
"Internacional" da S3. O defeito é de granularidade: o anti-double-count deveria ser por
`(instituição, moeda, conta)`, não por workspace.

### P3 · "Caixa e Moeda Estrangeira" vale o dobro do card ao lado

`patrimonio.composicao[5]` = R$ 168.561,73 (é `caixa_total_brl`, não `caixa_me_brl`),
duas posições acima do card que diz R$ 83.869,92. Os dois rótulos compartilham a
expressão "Moeda Estrangeira" e diferem por 2×.

*Ressalva:* o produtor citado na primeira rodada (`analyze_finances.py:1123`) é **script
legado morto**; o valor vivo vem de outro caminho. A coexistência na tela é real; a
linha apontada, não.

## Achados novos do co-design de 2026-08-14 — precisam de lane própria

> Levantados por `financial-planner` + `senior-cto` ao decidir o item do rodapé
> PTAX. **Nenhum estava neste inventário** e nenhum pertence à [[A40.l39]], que
> resolve a superfície e não a conversão. Prioridade/onda são gatilho de
> `product-manager` — não classifiquei.

**1. Taxa hardcoded `5.80`/`6.35` é indistinguível de taxa real.**
`e5_analyzer_adapter.py:902-910` cai em literal quando o `ConfigStore` não
resolve `market_rate`. Um run publica valor convertido por constante e **nada no
payload ou no log diz que isso aconteceu** — o E5 não expõe a taxa aplicada em
lugar nenhum. Hoje ninguém sabe com que frequência dispara.

**2. Fallback da [[ADR-245]] rotula BRL como USD.**
`_extract_me_caixa_from_baseline` (`e5_analyzer_adapter.py:1085-1129`) constrói
`CaixaDetalhe` com `saldo_original` **em BRL** e `moeda="USD"` (default em
`:1082`), `fonte` no default `"extrato"`. O card renderiza `US$ <valor em BRL>`.
Latente — só dispara com `not has_foreign_in_e3` —, e por isso **sem sintoma**:
mais grave que o rodapé e sem nada que o denuncie.

**3. A cotação corrente está 106 dias defasada** (2026-04-27). Não é bug de
conversão; é a ausência do rótulo que faria isso incomodar quem lê.

**4. A assimetria está no produtor, não na linha.**
`posicao_31_12_builder.py:97-114` — a row do E5 **já tem** os três campos de
PTAX; `_posicao_from_extrato` os preenche com `None` explícito. Quem não tem o
que preencher é a via a montante: `CaixaDetalhe` não carrega taxa.

**Forma sugerida do fix (não decidida):** um único conversor ME→BRL devolvendo
value object com `valor_brl`, `taxa`, `taxa_data`, `taxa_fonte` (enum fechado:
`ptax_31_12` | `market_rate_corrente` | `default_hardcoded` | `nao_convertido`)
e `status`; as três vias passam por ele. Fecha a classe por **tipo**, não por
regex. Pede ADR própria (~60 linhas): nenhuma vigente cobre — a [[ADR-090]]
decide representação, a [[ADR-238]] D5 decide precedência (e a [[ADR-382]] D4 já
a mata), e a [[ADR-387]] D3 é a mesma classe escopada a proteção. Campo novo
nasce `Decimal`; `CaixaDetalhe.valor_brl: float` **fica** — trocá-lo move centavos
publicados e consome re-run por ganho ortogonal.

**As 4 linhas em ME estão duplicadas hoje:** aparecem no card de Exposição
Cambial (R$ 83.869,92) e em caixa, além da tabela sob o header falso. Nada se
perde ao removê-las do S1.

### Desfecho dos 4 achados acima (2026-08-24) — e o que **voltou** para esta lane

Os quatro viraram a [[A40.l63]] + [[ADR-390]]. Fechados lá: taxa hardcoded vira
`taxa_fonte="default_hardcoded"` com WARNING; `moeda` passa a ser a unidade de
`saldo_original`; `taxa_data` carrega a data da row (o port ganhou
`get_market_quote` — `get_market_rate` devolvia só `Decimal` e descartava a
data, o que tornava o achado nº 3 inendereçável); `CaixaDetalhe.conversao` é
obrigatório por tipo.

**Correção ao enum sugerido acima:** a [[ADR-390]] fechou em `ptax_31_12` |
`market_rate_corrente` | `default_hardcoded` | **`irpf_ja_em_brl`**.
`nao_convertido` **não** é fonte — virou `status="missing_rate"`. Quem ler o
parágrafo "Forma sugerida do fix" acima vai implementar o enum errado.

**Correção ao achado nº 2:** *"O card renderiza `US$ <valor em BRL>`"* é falso.
Medido no §Ataque da l63: `patrimonio.caixa_detalhes` tem **zero**
renderizadores no frontend — só duas declarações de tipo. O raio real era maior
e noutro lugar (a agregação por moeda, que é renderizada).

**Dois achados voltam para cá**, porque são superfície de **consumo** de
exposição cambial e a l63 se limitava à conversão:

1. **`exposicao_cambial.detalhes` ainda publica BRL rotulado como USD.**
   `_detalhes_caixa` emite `moeda=_moeda_exposicao(d)` (reinferida por keyword
   na descrição) **ao lado do `saldo_original` em BRL**, com
   `saldo_original == valor_brl` ⇒ câmbio implícito 1,00. A contradição que a
   l63 matou em `caixa_detalhes` mudou de endereço, não morreu. Ressalva de
   desenho: `por_moeda` está **certo** — o dinheiro é denominado em dólar e o
   IRPF só reporta o equivalente em BRL; reinferir a moeda para efeito de
   *exposição* é o comportamento correto. O defeito é confinado a `detalhes[]`,
   a única sub-superfície que carrega `saldo_original`.

2. **`caixa_fx` declara `apurado` sobre um caixa cambial que descartou posição.**
   `_componentes` fixa a cobertura por constante —
   `ComponenteExposicao(caixa, Cobertura.apurado)` — e **nunca consulta
   `conversao.status`**. Medido em `main` (`b96cf3ca`), carteira apurada, uma
   linha GBP de £8.000 em `missing_rate`: `caixa_fx = {"valor_brl": 0.0,
   "cobertura": "apurado"}`. Com USD ao lado: `5800.0` + `apurado`, GBP
   invisível. `_sum_caixa_estrangeiro` descarta `valor <= 0` e a linha some de
   `por_moeda`, enquanto `detalhes` a mantém — as duas sub-superfícies do card
   discordam. A [[ADR-403]] construiu exatamente o mecanismo que distingue "sem
   base" de "zero medido"; **a linha `missing_rate` não o alimenta**.

   > **Correção datada 2026-08-24.** A primeira redação deste item (PR #1671)
   > dizia `tier: "empty"` e *"a família lê «sem exposição cambial»"*. Ambos
   > falsos: aquela medição rodou contra a árvore do repo principal, em
   > `agent/r7-priorizacao-decidida/20260819-0936` (**2026-08-19**), dois dias
   > antes do #1568 mergear. Em `main` o `tier` é `indeterminado` — que é a
   > abstenção correta, não uma asserção de ausência. Ver §Correção do closeout
   > da [[A40.l63]].

## Abertos latentes

- **Fallback de câmbio sem proveniência.** `e5_analyzer_adapter.py:861-869` embute
  5,80/6,35 como default; `MarketRateNotFound` é engolido por um `except Exception` que
  só faz `print`. As constantes são **numericamente idênticas** às rows do DB, então em
  produção ninguém distingue os dois caminhos. Classe [[ADR-359]]: deve falhar alto ou
  declarar ausência, nunca emitir número bonito. *(A suíte distingue; a produção não.)*
- **Cripto: V1 exclui, resolver do V2 dá `USD`.** Divergência de R$ 4.564,40 medida
  alimentando o agregador na mão. **Hoje não morde** — o V2 não recebe posição alguma
  (o E5 publica agregados). Vira P1 no instante em que a fonte de posições ligar, e é a
  dependência que **bloqueia** [[ADR-379]]: separar stablecoin de cripto volátil exige
  coluna nova em `asset_catalog`, porque ambos têm `asset_class = "Cripto"`.
- **Moeda fora de `{USD, EUR}` convertida a taxa 1,0.** O ramo `else` existe e rotula a
  linha como ME. *Inalcançável hoje:* `e2_extract.schema.json` e
  `e2_llm_artifact.schema.json` fixam `moeda` num enum de três valores. Rebaixado a P3 —
  quem adicionar uma moeda **tem** de editar essa função, porque as taxas chegam em dois
  parâmetros nomeados.
- **`valor_atual` sem unidade declarada.** Posições do E4 não têm campo de moeda.
  *Somar em BRL e rotular `USD` é o contrato*, não bug — `moeda` ali é lastro, não
  denominação. O risco real: extrator novo de corretora estrangeira que grave valor
  nativo entra 1:1 como reais.
- **`liquidez_usd_pct` é um nome que mente.** A meta declarada no DB é **10%**, não 3% —
  o `3,0` do E5 é `caixa_pct` renomeado por `pipeline_adapter.py:286`. O split
  70/30 é heurística aprovada (ADR-141 §emenda item 5). O defeito residual é só o nome.
- **Float no caminho de conversão** (erro medido 1e-11, dívida legada),
  **cópia morta em `analyze_finances.py`** (já divergiu do vivo pela [[ADR-376]] — não é
  espelho), **narrativa `s6` órfã** (existe, mas não é um terceiro número nem custa
  LLM), **`excluido_da_reserva.caixa_moeda_estrangeira`** (bate com a exposição; "nenhum
  consumidor" é forte demais).
- **Conta Global Wise (Reino Unido) gravada como R$ 0,00 "por falta de dado", sem
  `needs_review`.** O silêncio é real e o E5 não emite alerta nenhum. *Mas* a
  consequência medida na primeira rodada era sobre `caixa_me_detalhe`, que **não tem
  consumidor no frontend**; o detalhamento que o usuário vê (`posicao_31_12`) está
  populado.

## Questões de domínio sem dono

Nenhuma foi coberta pelo co-design de 2026-08-12. Exigem `financial-planner` antes de
virar código:

1. **Fundos BDR.** "Alaska Black FIC de FIA - BDR NÍVEL I" (R$ 41.846,29) e "Western
   Asset BDR FIF" (R$ 28.764,28) somam R$ 70.610,57 e classificam como `Fundos` → BRL.
   BDR replica ativo estrangeiro. Se contarem, a exposição deste workspace quase dobra.
2. **Catálogo inerte.** Nenhuma das 18 posições do dogfood casou o catálogo (21
   entradas) — todas resolveram por `fallback_classe`, enquanto o rodapé do card promete
   "ativos com lastro econômico não-BRL".
3. **`IVVB11` classifica como `FIIs`.** Só não morde porque o catálogo tem o ticker;
   qualquer ETF internacional fora do catálogo cai em `FIIs` → BRL → fora da exposição.
4. **Tier contradiz a própria [[ADR-224]] §6.** O analyzer chama ≥10% de "adequado"; a
   ADR diz que a faixa ICP é 20-30% e <10% é sub-diversificado. Um usuário a 11% lê
   "adequado" enquanto o documento canônico o chama de abaixo da faixa.
5. **Alvo genérico vs meta declarada.** Quando o workspace tem meta `dolarizacao` com
   `meta_usd`, o alvo do card deveria ser ela, não a faixa universal.

## Ordem obrigatória

Ligar o braço de ativos **antes** do eixo de elegibilidade entrega 6,80% contando BTC
como proteção cambial. Medido: só caixa 6,45% · com ativos 6,80% · com ativos e cripto
volátil fora **6,45%** (não muda — a mudança é de mecanismo, não de tier).

Regra que vale para qualquer PR desta lane: registrar o percentual **antes e depois**
com o denominador corrigido. Nenhuma mudança pode ser aceita por "o tier melhorou".

## Refutados — não reabrir

- *"Zero cobertura de frontend na precedência V2>V1."* Havia cobertura em
  `frontend/tests/` — e um dos testes asseverava a frase falsa como correta. Corrigido
  em `d1b7c97c`. A lição durável: teste e código podem compartilhar a mesma crença.
- *"Não existe caminho executável para lastro EUR."* Existe um quarto caminho, e é por
  ele que o EUR deste workspace já passa: o braço de caixa lê `moeda` do extrato direto.
- *"`% Internacional` tem dois valores com denominadores diferentes."* Bases distintas
  por desenho; o `file:line` citado não produz nenhum dos dois valores.
