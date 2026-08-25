---
id: A40.l63
type: lane
title: "Conversão ME→BRL não registra proveniência: taxa hardcoded indistinguível de taxa real, e saldo BRL rotulado como USD"
sprint: A40
plan: PLAN-report-trust
status: shipped
priority: P1
ship_pr: 1671
ship_date: "2026-08-24"
branch_slug: a40-l63-conversao-me-brl-sem-proveniencia
owner: data-engineer
adrs:
  - "[[ADR-090]]"
  - "[[ADR-245]]"
  - "[[ADR-390]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/money
---

# A40.l63 — `conversao-me-brl-sem-proveniencia`

> Aberta em 2026-08-15 no co-design do P0 nº 2 da [[A40.l50]]
> (`financial-planner` + `senior-cto`). **Nenhum destes achados estava no
> inventário da l50**, e nenhum pertence à [[A40.l39]] — ela resolve a
> superfície da tabela, não a conversão que a alimenta.

## Problema

Três produtores alimentam a mesma coluna de valor convertido, e **nenhum
registra a taxa que usou**. A informação de qual linha veio de onde existe
(`fonte`), mas a taxa não — então nenhum consumidor consegue fazer afirmação
verdadeira sobre a conversão, só afirmação falsa ou silêncio.

### 1 · Taxa hardcoded indistinguível de taxa real

`e5_analyzer_adapter.py:902-910` cai em `5.80` / `6.35` literais quando o
`ConfigStore` não resolve `market_rate`. Nada no payload E5 e nada no log
registra que isso aconteceu — `grep` no `e5_analysis.schema.json` confirma que
**a taxa corrente aplicada não é exposta em lugar nenhum**. Hoje ninguém sabe
com que frequência dispara.

### 2 · Fallback da [[ADR-245]] rotula BRL como USD

`_extract_me_caixa_from_baseline` (`e5_analyzer_adapter.py:1085-1129`) constrói
`CaixaDetalhe` com `saldo_original` **em BRL** e `moeda="USD"` (default
conservador em `:1082`), `fonte` no default `"extrato"`. O card renderiza a
linha secundária como `US$ <valor em BRL>`.

**Latente** — só dispara com `not has_foreign_in_e3` — e por isso **sem
sintoma**: mais grave que o rodapé PTAX que originou a investigação, e sem nada
que o denuncie.

### 3 · A assimetria é do produtor, não da linha

`posicao_31_12_builder.py:97-114` — a row do payload E5 **já tem** os três
campos de PTAX; `_posicao_from_extrato` os preenche com `None` explícito. Quem
não tem o que preencher é `CaixaDetalhe` (`patrimonio_types.py:195-208`), que
carrega `saldo_original`, `valor_brl`, `moeda`, `fonte` e `data_referencia` —
nenhum campo de taxa ou status.

### 4 · A cotação corrente está 106 dias defasada (2026-04-27)

Não é bug de conversão; é a ausência do rótulo que faria isso incomodar quem lê.

## Escopo

1. **Conversor único ME→BRL** devolvendo value object com `valor_brl`, `taxa`,
   `taxa_data`, `taxa_fonte` (enum fechado: `ptax_31_12` |
   `market_rate_corrente` | `default_hardcoded` | `nao_convertido`) e `status`.
   As três vias passam por ele. Fecha a classe **por tipo**, não por regex.
2. Matar o `5.80`/`6.35` hardcoded como valor silencioso — ele vira
   `taxa_fonte="default_hardcoded"` com `WARNING` estruturado e contagem de
   linhas afetadas (sem valor monetário no log).
3. Corrigir o fallback da [[ADR-245]]: `moeda` e `saldo_original` param de se
   contradizer.
4. **Gate.** O funil estrutural é o que fecha a classe — via nova não consegue
   produzir a coluna sem passar pelo conversor, porque o tipo não deixa.
   Backstop barato em pre-commit (multiplicação por `cambio*`/`ptax`/`quote.rate`
   fora do módulo conversor é ofensor) fecha a **sintaxe**, não a classe — não
   confundir os dois. Ratchet por allowlist **nominal** `(módulo, produtor) → WHY`,
   nunca contador de linhas.

## Fora de escopo

- **Qual taxa a coluna "31/12" usa** — é [[ADR-382]] e [[A40.l39]].
- **Matar `CaixaDetalhe.valor_brl: float`** — campo novo nasce `Decimal`, mas
  trocar o legado move centavos publicados e consome re-run por ganho ortogonal.
  Morre na lane de float-money, com `dev/golden_diff.py` e manifesto.

## Critério de aceite

- Golden de execução mostrando as três vias com `taxa_fonte` distinto.
- Caso `default_hardcoded` exercitado com `ConfigStore` sem `market_rate` — hoje
  ninguém sabe quando dispara.
- Regressão do fallback [[ADR-245]] provando que `moeda`/`saldo_original` param
  de se contradizer.
- Prova de mutação: reintroduzir a multiplicação crua num dos três produtores
  derruba o gate.
- Campo novo **não** entra em `required` no schema — leitor histórico é tolerante.

## Pendente de decisão

Fechado em 2026-08-17: [[ADR-390]] (Decidido). Conversor não escolhe a taxa;
fonte ≠ status; objeto `conversao` aninhado. A [[ADR-245]] L3 foi emendada
no mesmo PR.

## Ataque (2026-08-24) — a lane entregou há 7 dias e segue `open`; o funil estrutural nunca foi construído

> Medido contra `main` (`7ed61f04`) rodando os **produtores reais**
> (`_extract_me_caixa_from_baseline`, `_detalhe_from_conv`, `resolve_fx_input`,
> `compute_exposicao_cambial`) e o **próprio gate** (`_scan_file` de
> `check_conversao_me_funnel.py`), não reimplementações. Nada de código foi tocado.
>
> Estado de partida: gate `exit=0`, **93 testes verdes**. Nada aqui é "está
> quebrado" — é "está verde e a classe segue aberta".

### 0 · A lane está `shipped` no código e `open` no vault

O [#1494](https://github.com/davidrobert/mathoms/pull/1494) (`8ad3af9e`, mergeado
**2026-08-17**) entregou o escopo inteiro — conversor, três vias, gate, [[ADR-390]]
`Decidido`, emenda L3 da [[ADR-245]] — e marcou os **6 critérios de aceite `[x]`**
no corpo do PR. Ele **editou o arquivo desta lane** (só para somar `ADR-390` ao
frontmatter) e **não flipou `status`**. A linha 359 do `_README` da A40 segue com
`| — |` na coluna de PR.

Consequência operacional medida: `python3 dev/lane_pickup.py A40.l63` devolve
`status open · P1`. Um segundo agente refaria trabalho mergeado.

Isto é a **variante de transição AUSENTE** — não houve flip malfeito, houve
ausência de flip. O gate proposto pela [[A40.l59]] dispara *na transição para
`shipped`*, então **não pegaria este caso**: é o mesmo desenho pelo qual o
caso-bandeira da própria l59 fica verde.

> *Marcador 2026-08-25: o gate deixou de ser "proposto" — a [[A40.l59]] shipou
> (`lane-transition`, #1661). A análise acima **continua valendo**: o `T1` de
> fato não pega transição ausente. O que a l59 entregou a mais foi o `C1`, que lê
> estado em vez de diff — mas ele exige `ship_pr` declarado, e no instante medido
> aqui esta lane não tinha. É o limite declarado em [[ADR-413]] §Limite.*

### 1 · «porque o tipo não deixa» — o tipo deixa

O §Escopo 4 sustenta o fechamento da classe no funil estrutural: *"via nova não
consegue produzir a coluna sem passar pelo conversor, porque o tipo não deixa."*

`CaixaDetalhe.conversao` é `ConversaoMeBrl | None = None`
([`patrimonio_types.py:210`](../../../../pipeline/domain/services/patrimonio_types.py)).
Medido — produtor novo que esquece o carimbo:

```
CaixaDetalhe(conta="Novo Banco (corrente)", moeda="USD",
             saldo_original=1000.0, valor_brl=5800.0, tipo="moeda_estrangeira")
  constrói ....................... OK (default None)
  to_dict() traz "conversao"? .... False
  schema CaixaDetalhe ............ VALIDA
```

O payload publicado é **indistinguível de um artefato pré-390** — e isso é *por
desenho*: a descrição do `$defs/ConversaoMe` diz `"Ausência da chave = artefato
pré-390"`. **Os dois objetivos da lane estão em tensão e ela os trata como
compatíveis:** o §Critério *"campo novo não entra em `required`"* (correto — leitor
histórico é tolerante) é exatamente o que torna a omissão invisível. Uma única
ausência não pode codificar "legado" e "produtor novo esqueceu" ao mesmo tempo.
Fechar a classe exige um segundo sinal (writer-version no payload, ou `required`
escopado ao stage novo), não um campo opcional.

### 2 · O backstop sintático pega 3 de 10 mutações plausíveis

Bateria contra `_scan_file`, com idiomas tirados **deste** arquivo:

| mutação em produtor novo | gate |
| --- | --- |
| `saldo * cambio_usd` — a forma histórica (`e5_analyzer_adapter.py:961` pré-390) | **PEGA** |
| `saldo * quote.rate` | **PEGA** |
| `cambio_usd * saldo` (invertido) | **PEGA** |
| `saldo * self._cambio_usd_brl` — **o atributo que o adapter de fato carrega** | PASSA |
| `saldo * safe_float(self._taxas.get("cambio_usd_brl", 5.80))` — a linha 905 pré-390, inline | PASSA |
| `saldo * self._taxas["cambio_usd_brl"]` | PASSA |
| `valor_brl *= cambio_usd` | PASSA |
| `saldo * conv.taxa` — recomputar a partir do próprio carimbo | PASSA |
| `saldo * float(cambio_usd)` | PASSA |
| `saldo * usd_brl` (renomeado) | PASSA |

Três defeitos de construção, todos verificáveis no fonte:

- **`_RATE_ATTR` foi escrito a partir da assinatura, não do campo.** A lista tem
  `cambio_usd_brl` (nome do *parâmetro* de `__init__`); a instância guarda
  `self._cambio_usd_brl`, e `_RATE_NAME = ^(cambio|ptax)` não casa com `_cambio…`.
  O atributo que qualquer produtor novo multiplicaria é o único que o gate não vê.
- **`ast.AugAssign` não é visitado** — só `ast.BinOp`/`Mult`. E `total_brl += …` é
  o idioma dominante da própria função que o gate protege.
- **`ast.Subscript` e `ast.Call` não são desembrulhados** — `_is_rate_expr` só
  reconhece `Name` e `Attribute`, então qualquer resolução inline escapa.

A prova de mutação do #1494 (`saldo * cambio_usd`) usou a única forma que o gate
foi construído para enxergar. O §Critério *"reintroduzir a multiplicação crua num
dos três produtores derruba o gate"* é satisfazível por **uma instância** com a
classe aberta. A lane já avisava que este ratchet *"fecha a sintaxe, não a classe"*
— o defeito não é ele ser sintático, é a perna estrutural que cobriria o resto
não existir (§1).

Menores, do mesmo arquivo: `SCAN_ROOTS = (pipeline, scripts)` — **`backend/` não é
varrido**; e o sink é casado por `path.name`, então *qualquer* arquivo chamado
`conversao_me.py`, em qualquer pasta, fica isento.

### 3 · O enum fechado de `taxa_fonte` é declarado em três lugares e enforçado em zero

O §Escopo 1 pede `taxa_fonte` com *"enum fechado"*. Ele existe como `Literal`
Python (hint, não checado em runtime), como união em
`frontend/src/types/report-analysis.ts` (mão) e como **`description`** no schema —
nunca como `enum`. Medido:

| instância | schema |
| --- | --- |
| `taxa_fonte="ptax_31_12"` | VALIDA |
| `taxa_fonte="chute_do_agente"` | **VALIDA** |
| `taxa_fonte=""` | **VALIDA** |
| `taxa_fonte="MARKET_RATE_CORRENTE"` | **VALIDA** |
| `status="chutado"` *(controle)* | REPROVA — `status` é `enum` de verdade |

O controle importa: o schema **sabe** enforçar enum; `taxa_fonte` é omissão, não
limitação. Também não há restrição cruzada — `status="converted"` com `taxa=null`
e `taxa_fonte=null` valida, e `status="missing_rate"` **carregando** taxa valida.
O carimbo pode se contradizer e passar.

### 4 · «saldo BRL rotulado como USD» não morreu — mudou de endereço

Rodando os produtores reais sobre um item IRPF código 02 (`"DEPOSITO EM CONTA
CORRENTE EM DOLAR - BANK OF AMERICA"`, R$ 250.000 já em BRL):

```
patrimonio.caixa_detalhes[0]        moeda="BRL"  saldo_original=250000.0   coerente ✅
exposicao_cambial.detalhes[0]       moeda="USD"  saldo_original=250000.0   ← BRL rotulado USD
```

`_moeda_exposicao` reinfere a moeda por keyword na descrição
([`exposicao_cambial_analyzer.py:108`](../../../../pipeline/domain/services/exposicao_cambial_analyzer.py))
e `_detalhes_caixa` publica esse rótulo **ao lado do `saldo_original` em BRL**.
`saldo_original == valor_brl == 250000.0` ⇒ a linha implica câmbio 1,00.

Ser justo com o desenho: **`por_moeda` está certo** — o dinheiro é de fato
denominado em dólar e o IRPF só reporta o equivalente em BRL; reinferir a moeda
para efeito de *exposição* é o comportamento correto e está documentado no
docstring de `infer_declared_me_currency`. O defeito está confinado a `detalhes[]`,
que é a única sub-superfície que carrega `saldo_original`.

**E a premissa do §Problema 2 era falsa quando escrita.** Ele diz *"O card renderiza
a linha secundária como `US$ <valor em BRL>`"*, e classifica o achado como *"mais
grave que o rodapé PTAX"* com base nisso. Medido: `caixa_detalhes` tem **zero
renderizadores** no frontend — só duas declarações de tipo
(`generated/report-analysis.ts:319`, `types/report-analysis.ts:67`). Nenhum
componente lê `conversao`, `taxa_fonte` ou `taxa_data`. A emenda L3 da [[ADR-245]]
("o card deixa de imprimir `US$ <BRL>`") descreve um card que nunca imprimiu.
O raio real era **maior** e noutro lugar: a agregação por moeda, que é renderizada
(`ExposicaoCambialCard`, `PorMoedaTableV1`).

### 5 · `fonte="extrato"` na linha de IRPF — nomeado no §Problema, sobrevivente

Mesmo payload medido acima: `fonte: "extrato"` numa linha que veio do baseline
IRPF. O §Problema 2 listou os **três** campos que se contradizem
(`saldo_original`, `moeda`, `fonte`); o §Critério de aceite escreveu só
*"`moeda` ≡ unidade de `saldo_original`"*. O box foi marcado com honestidade e o
defeito passou pela fresta entre o problema e o critério.

Não há valor correto a escrever hoje: a [[ADR-238]] D5 fecha o vocabulário em
`"extrato" | "informe_31_12"`, e nenhum dos dois descreve baseline IRPF — falta um
terceiro termo. O schema também não ajuda (`fonte: {"type": "string"}`, livre).

### 6 · `taxa_data` é `null` justamente na via onde a defasagem mora

| via | `taxa` | `taxa_data` | `taxa_fonte` | `status` |
| --- | --- | --- | --- | --- |
| extrato USD · ConfigStore resolveu | 5.42 | **None** | `market_rate_corrente` | converted |
| extrato USD · só `taxas.json` legacy | 5.42 | **None** | `market_rate_corrente` | converted |
| extrato USD · nada resolveu | 5.80 | **None** | `default_hardcoded` | converted |
| extrato GBP · nada resolveu | None | None | None | missing_rate |
| informe 31/12 | 5.48 | `2024-12-31` | `ptax_31_12` | converted |

`taxa_data` só é preenchido pela via PTAX — que **já carregava** `ptax_data` antes
da ADR-390. O campo não adicionou informação nenhuma.

A causa é estrutural, não descuido do produtor: `resolve_fx_input` monta
`FxQuote(...)` sem `observed_at` porque **não tem de onde tirar**. O port é
`ConfigStore.get_market_rate(pair, observed_at) -> Decimal` — devolve só a taxa, e
a data da row efetivamente resolvida (*"última cotação em data <= observed_at"*,
[`db_config_store.py:128`](../../../../backend/app/services/db_config_store.py)) é
descartada na fronteira. Preencher `taxa_data` exige mudar a assinatura do port.

⇒ O §Problema 4 ("a cotação corrente está 106 dias defasada… é a ausência do rótulo
que faria isso incomodar quem lê") segue **integralmente aberto**. O rótulo virou
coluna; o número que a preencheria continua inalcançável.

### 7 · A linha `missing_rate` some da exposição em vez de aparecer como "sem cotação"

GBP 8.000 sem cotação, medido ponta a ponta:

```
payload E5 ......... valor_brl: 0.0   conversao.status: "missing_rate"
exposicao_cambial .. por_moeda: ()    tier: "empty"    detalhes: 1 linha
```

`_detalhe_from_conv` grava `0.0` (não `null`) quando `conv.valor_brl is None`, e
`_sum_caixa_estrangeiro` descarta `valor <= 0`. A família com £8.000 lê **"sem
exposição cambial"**. As duas sub-superfícies do mesmo card discordam: `detalhes`
tem a linha, `por_moeda` não.

O produtor acertou (não inventar BRL é o comportamento certo); **nenhum consumidor
foi ensinado o status novo**, então "desconhecido" renderiza como "zero".

### 8 · Não há golden de execução — os critérios fecharam sobre teste unitário

O §Critério 1 pede *"Golden de execução mostrando as três vias com `taxa_fonte`
distinto"*. Medido: **nenhum** golden cita `taxa_fonte` ou `conversao`, e
`tests/test_e5_golden_execution.py` não desce até `patrimonio.caixa_detalhes`. As
três vias estão cobertas por unitário (`test_conversao_me.py`), que exercita a
função — não o artefato que o pipeline escreve.

### Placar dos 6 critérios auto-declarados `[x]` no #1494

| # | critério | veredito medido |
| --- | --- | --- |
| 1 | golden de execução, três vias | **NÃO** — nenhum golden toca o campo (§8) |
| 2 | `default_hardcoded` exercitado + WARNING sem valor | **SIM** — status nomeado, `warn_hardcoded` sem monetário |
| 3 | regressão 245: `moeda` ≡ `saldo_original` | **SIM como escrito** — mas `fonte` (§5) e `exposicao_cambial.detalhes` (§4) seguem contraditórios |
| 4 | GBP → `missing_rate`, fora do total | **SIM no produtor** — some da exposição no consumidor (§7) |
| 5 | mutação derruba o gate | **1 de 10 formas plausíveis** (§2) |
| 6 | `conversao` fora de `required` | **SIM** — e é o que impede fechar a classe (§1) |

### Encaminhamento

Esta lane é o dono vivo — ela nunca fechou. Nada abaixo vira lane nova; tudo é
escopo remanescente dela, com uma exceção nomeada.

1. **Registrar `ship_pr: #1494`** no frontmatter e na linha 359 do `_README`,
   antes de qualquer outra coisa — hoje a lane é pegável e o trabalho mergeado
   seria refeito. **`status` fica `open`**: o placar acima mostra 2 dos 6
   critérios não satisfeitos, então `shipped` seria a afirmação errada. O que
   falta não é o flip — é a lane parar de parecer *não-começada* enquanto o
   conversor, o gate e a [[ADR-390]] já estão em `main`.
2. **§1 é a decisão que falta**: escolher o segundo sinal que distingue "artefato
   pré-390" de "produtor novo esqueceu". Sem isso o §Escopo 4 não é implementável
   como escrito, e reformulá-lo é mais honesto que persegui-lo.
3. **§3 é barato e fecha hoje**: `enum` de verdade em `taxa_fonte` (o `status` ao
   lado já prova que o schema enforça), mais a restrição cruzada `converted` ⇒
   `taxa` presente.
4. **§2**: `_cambio_usd_brl` no `_RATE_ATTR`, `ast.AugAssign` no visitor, `backend/`
   nos `SCAN_ROOTS`, sink por path e não por basename. Quatro linhas que levam o
   ratchet de 3/10 a algo defensável — sem confundir isso com fechar a classe.
5. **§4 (`exposicao_cambial.detalhes`) e §7 (a linha que some) pertencem à
   [[A40.l50]]**, que está `open` e é a investigação-mãe de exposição cambial. Não
   é redirecionamento de conveniência: `_moeda_exposicao` e `_sum_caixa_estrangeiro`
   são superfície dela, e o §Fora de escopo desta lane já se limita à conversão.
6. **§6 abre decisão de port**: `get_market_rate` devolver `(rate, observed_at)` é
   mudança de contrato em `pipeline/ports/config_store.py` com 3 implementações.
   Enquanto não acontecer, `taxa_data` é coluna morta na via corrente — e vale
   dizê-lo no schema, em vez de deixar o leitor inferir que a data existe.

**Fora de escopo confirmado no ataque:** `CaixaDetalhe.valor_brl: float` segue
`float` (§Fora de escopo da lane, correto — move centavos publicados); `taxa` sai
como *string* em `to_wire()` (`format(Decimal, "f")`), o que preserva precisão e
não é o defeito de float que a lane de float-money persegue.

## Fecho (2026-08-24) — o placar do ataque, re-medido depois das correções

> O §Ataque acima fica **como escrito**: é o retrato de `main` em 2026-08-24
> antes deste fecho, e snapshot datado que alguém reescreve deixa de ser
> evidência. Esta seção diz o que mudou desde ele.

### Placar re-medido

| # | critério | no ataque | agora |
| --- | --- | --- | --- |
| 1 | golden de execução, três vias | **NÃO** — nenhum golden tocava o campo | **SIM** — `tests/test_e5_golden_conversao_me.py`, 3 runs reais sobre o artefato E5 |
| 2 | `default_hardcoded` + WARNING sem valor | SIM | SIM, agora também no golden (exige remover o `taxas.json` do tenant) |
| 3 | regressão 245: `moeda` ≡ `saldo_original` | SIM como escrito, com `fonte` contraditório ao lado | **SIM inteiro** — `fonte="baseline_irpf"` ([[ADR-238]] §Emenda) |
| 4 | GBP → `missing_rate`, fora do total | SIM no produtor; some da exposição no consumidor | SIM no produtor; o consumidor é da [[A40.l50]] (§7 do ataque) |
| 5 | mutação derruba o gate | **1 de 10** formas plausíveis | **10 de 10**, bateria parametrizada com controle de polaridade |
| 6 | `conversao` fora de `required` | SIM — e era o que impedia fechar a classe | SIM na **leitura**; obrigatório na **escrita** (`TypeError`) |

### O que foi feito, por §

- **§1 (funil estrutural).** `CaixaDetalhe.conversao` passa a obrigatório e
  keyword-only. A tensão que o ataque isolou — a mesma ausência codificando
  "artefato pré-390" e "produtor esqueceu" — resolve-se separando os lados:
  tipo obrigatório na escrita, schema tolerante na leitura. [[ADR-390]] §E1.
- **§2 (ratchet).** `_cambio_usd_brl` no `_RATE_ATTR` (a lista vinha do nome do
  *parâmetro*, não do atributo), `ast.AugAssign` visitado, `Subscript`/`Call`
  desembrulhados, `backend/` nos scan roots, sink por path e não por basename.
  3/10 → 10/10, **zero** falso-positivo na árvore real.
- **§3 (enum).** `taxa_fonte` vira `enum` de verdade + restrição cruzada
  (`converted` ⇒ `taxa_fonte`; `missing_rate` ⇒ ambos nulos). `identity` fica
  livre de propósito. [[ADR-390]] §E2.
- **§5 (`fonte`).** `baseline_irpf` entra no vocabulário. Não era cosmético: a
  linha de IRPF entrava no card 31/12 com id `extrato:irpf_…` e `data_referencia`
  nula. [[ADR-238]] §Emenda 2026-08-24.
- **§6 (`taxa_data`).** Port ganha `get_market_quote` (aditivo). Era
  inpreenchível porque `get_market_rate` devolve só `Decimal` e descarta a data
  da row. Testado no caso que importa — cotação de 2026-04-27 lida em 08-11
  carimba `2026-04-27`. [[ADR-390]] §E3.
- **§8 (golden).** Três runs, porque as vias são mutuamente exclusivas por
  desenho. Prova de mutação medida nos dois produtores.

### Fica fora, com dono

- **§4 e §7 → [[A40.l50]]** (`open`, investigação-mãe de exposição cambial):
  `exposicao_cambial.detalhes` publica `moeda="USD"` ao lado de `saldo_original`
  em BRL, e a linha `missing_rate` some do card (`por_moeda: ()`, `tier: empty`)
  em vez de aparecer como "sem cotação". São superfície de consumo, não de
  conversão — o §Fora de escopo desta lane já se limitava à conversão.
- **Se e como o snapshot 31/12 do IRPF deve aparecer no card de posições →
  [[A40.l39]]** (`in_progress`). Hoje ele simplesmente não aparece, o que é
  honesto mas não necessariamente o que a família quer ver.
- **`CaixaDetalhe.valor_brl: float`** segue `float`, como o §Fora de escopo
  original manda — morre na lane de float-money.

### Verificação

```
dev/check_conversao_me_funnel.py    exit=0, zero ofensor
pytest tests                        7399 passed
pytest backend/tests                3611 passed
pre-commit code-style-baseline      sem regressão P1/P2/P7/P9
```

## Correção do closeout (2026-08-24) — o §7 do meu ataque foi medido na árvore errada

> O §Ataque e o §Fecho ficam **como escritos**. Esta seção corrige um número
> que publiquei falso, na forma que a própria lane pratica: acrescentar, nunca
> reescrever snapshot datado.

**O erro.** As probes do §4 e do §7 rodaram com
`sys.path.insert(0, "<repo>/mathoms.ai")` — o **repo principal**, não este
worktree. Aquela árvore estava em `agent/r7-priorizacao-decidida/20260819-0936`
(`e442dbad`, **2026-08-19**), e o [#1568](https://github.com/davidrobert/mathoms/pull/1568)
([[ADR-403]], componentes + cobertura da exposição cambial) mergeou em
**2026-08-21**. `grep -c "componentes|Cobertura"` naquela árvore: **0**. Medi
contra um estado dois dias velho e chamei de `main`.

**O que sobrevive à re-medição** (worktree em `main`, `b96cf3ca`):

| afirmação do §7 | re-medido |
| --- | --- |
| `por_moeda: ()` — a linha some | **confirmado** |
| `tier: "empty"` | **falso** — é `indeterminado` |
| *"a família lê «sem exposição cambial»"* | **exagerado** — `indeterminado` é exatamente a abstenção que a [[ADR-403]] construiu |

**O defeito real é outro, e mais afiado.**
`exposicao_cambial_analyzer._componentes` fixa a cobertura por constante:

```python
"caixa_fx": ComponenteExposicao(caixa, Cobertura.apurado),
```

Ela nunca consulta `conversao.status`. Medido com carteira apurada e uma linha
GBP de £8.000 em `missing_rate`: `caixa_fx = {"valor_brl": 0.0, "cobertura":
"apurado"}` — o componente **declara ter apurado** um caixa cambial que
descartou a única posição que tinha. Com USD ao lado, idem: `5800.0` e
`apurado`, com a GBP invisível. A [[ADR-403]] construiu o mecanismo que
distingue "sem base" de "zero medido"; a linha `missing_rate` não o alimenta.

O §4 **não muda**: re-medido em `main`, `exposicao_cambial.detalhes[0]` segue
`{"moeda": "USD", "saldo_original": 250000.0, "valor_brl": 250000.0}` — BRL
rotulado USD, câmbio implícito 1,00.

**Nada disto reabre esta lane** — segue `shipped`, e nenhum dos dois toca a
conversão. O que muda é o texto da rota na [[A40.l50]], corrigido no mesmo PR.

**Lição de método, custou o achado:** em worktree, probe que faz
`sys.path.insert` com caminho absoluto do repo principal mede a branch **daquele**
worktree, não a sua. Use `sys.path.insert(0, ".")` e rode do worktree. Mesma
família do que a [[A40.l58]] registrou ("a primeira passada usou a árvore do
repo principal, que estava numa branch de agosto/19").
