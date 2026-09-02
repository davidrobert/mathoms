---
id: A27.l3
type: lane
title: "A cobertura de lineage é medida contra a fixture e não contra a produção: três raízes monetárias ficam fora do universo do gate (a quarta era contagem lida como R$)"
sprint: A27
status: shipped
ship_pr: 1971
ship_date: "2026-09-01"
priority: P1
branch_slug: a27-l3-cobertura-de-lineage-medida-contra-a-fixture
owner: data-engineer
depends_on: []
adrs: ["[[ADR-281]]"]
tags: [type/lane, sprint/a27, status/shipped, priority/p1, area/dados]
---

# A27.l3 — `cobertura-de-lineage-medida-contra-a-fixture`

> **Origem:** `PV13-12` da rodada unificada **U5** ([[PIPELINE-REVIEWS-active]] §r13).
> Sucessora da [[A27.l2]], que **entregou** o gate com controle positivo — o defeito é no
> **universo**, não no mecanismo.

## O defeito

O gate fixa o conjunto de raízes monetárias sobre o payload da **fixture** de dogfood:
**14** raízes. O payload **real** deste run tem **18**. As **4 raízes a mais ficam fora do
universo do gate** — não são medidas como descobertas, e não contam como descobertas.

Efeito no número publicado: a cobertura sai **36%**; medida sobre o universo real é
**28%**. O viés é **otimista**, e cresce sozinho: raiz nova entra na produção sem entrar no
denominador.

## Por que não invalida a A27.l2

O controle positivo dela é real e o mecanismo funciona. O que esta lane conserta é o
**sujeito da medição** — exatamente a distinção que a [[A42.l14]] estabeleceu para
conservação. O gate mede bem o que decidiu medir; decidiu medir a fixture.

> ⚠️ **Closeout 2026-09-02 — o número que esta lane publicou era, ele mesmo, otimista.** Um
> `data-engineer` atacou a entrega e dois defeitos passaram pela medição, ambos da **mesma
> classe que a lane existe para fechar** (universo cego ⇒ viés otimista), deslocada de
> *origem* para **tipo** e **tempo**. **Fechados no mesmo dia** — ver §Fecho. O número
> publicado é **5/20 = 25,0%**; `29,4%` era teto, e `35,7%` era a fixture.

## O que foi medido (2026-09-01)

O enunciado **reproduz**, e a composição dele **não**. Medido sobre o artefato
`analyze_finances/analise_financeira` do run `40d1af2a` (ws `1b9f2cf5`), decifrado do
`pipeline_artifacts`:

| Medida | Enunciado (`PV13-12`) | Medido |
| --- | --- | --- |
| Universo da fixture dogfood | 14 | **14** ✓ |
| Universo do payload de produção | 18 | **18** ✓ (e 1 deles é falso-positivo — ver abaixo) |
| Cobertura publicada | 36% | **35,7%** ✓ |
| Cobertura real | 28% | **29,4%** (5/17, não 5/18) |

A fixture é subconjunto **estrito** da produção — as 14 dela estão todas nas 18. As 4 a
mais são `previdencia_pgbl`, `real_estate`, `tributario` e `narrativas`; as três primeiras
são dinheiro de verdade (a fixture dogfood não tem IRPF, imóvel locado nem PJ, então nunca
as emite). O viés é otimista, como o enunciado diz.

**A quarta não é raiz monetária.** A única folha que põe `narrativas` no denominador é
`narrativas.charts.wise_fiscal_flags.pontos_revisao`, que
[`tributario_narrator.py`](../../../../pipeline/domain/services/narrativas/tributario_narrator.py) (linha 233)
computa como `sum(1 for f in flags if f.get("needs_review"))` — **contagem**, lida como R$
pelo monetário-por-default. É a mesma classe já registrada em `golden_diff` para `n_*`,
`prob_*` e `score.*`. Corrigido no classificador (token `pontos`, mais `contagem`, que
`consumo_consciente_calculator.py:162` publica ao lado do irmão que é dinheiro). Raio medido
sobre schema E5 + payload de produção (1.008 nomes): 4 nomes mudam de classe, nenhum
numérico além de `pontos_revisao`; zero tocam `*_brl` ou `valor`.

Com isso o denominador honesto é **17**, e a cobertura publicada cai de **35,7% → 29,4%**.

> Os números desta seção são a medição de **2026-09-01** e ficam como registro datado. O
> closeout do dia seguinte achou que `29,4%` também era otimista — denominador **20**,
> cobertura **25,0%**. Ver §Fecho.

## O universo: roster de origens, não o que uma fonte emite

A A27.l2 derivava o universo do payload da fixture — o que estava certo como *mecanismo* e
errado como *sujeito*. O universo agora é um **roster** (`dev/snapshots/lineage_coverage_baseline.json`):
cada raiz guarda **as origens em que foi observada**, e o número publicado é sobre o
universo inteiro.

| Origem | O que é | Raízes monetárias | Cobertas |
| --- | --- | --- | --- |
| `schema` | piso **declarado** pelo contrato E5, recomputado a cada run do gate | 18 | 5 |
| `fixture` | chão que o CI reproduz sozinho (dogfood determinística) | 15 | 5 |
| `producao:40d1af2a` | observação datada de um run real | 19 | 5 |
| **Roster publicado** | a união | **20** | **5** → **25,0%** |

Nenhuma origem cobre o universo sozinha, e isso é asseverado
(`test_o_universo_e_maior_que_qualquer_origem_sozinha`): o `schema` não alcança `irpf_kpis`
(declara 5 campos, o E5 emite 20); a `fixture` e a produção não alcançam workspace não medido.
Se alguma passar a cobrir tudo, o roster virou um dos lados disfarçado de universo.

A fixture aparece com **15**, não com as 14 que esta lane mediu em 2026-09-01: o conserto do
§D1 revelou `protecao_patrimonial` **também ali** — ela publica prêmio como string decimal, e
o classificador antigo a escondia nas duas origens. O viés de tipo não era só da produção.

**Por que não o schema E5.** Medido e **rejeitado**: caminhando
`config/schemas/e5_analysis.schema.json` com o mesmo predicado, ele declara monetário em 14
raízes que **não são superconjunto da produção** — não declara `tributario`, que a produção
emite por `additionalProperties: true` — e declara `proventos_por_ativo`, que **nenhum** dos
40 artefatos E5 do DB emite. Seria teto inalcançável de novo, que é justamente o que a
A27.l2 evitou ao recusar as 38 raízes cruas.

> ⚠️ **As duas pernas deste parágrafo caíram no closeout (2026-09-02). A decisão sobrevive;
> a justificativa, não.** (1) `tributario` **passou a ser declarado** pelo [#1967](https://github.com/davidrobert/mathoms/pull/1967)
> (`9582364a`), aberto por esta lane. (2) As "14 raízes" e o "não é superconjunto" eram
> **artefato do meu walker**, que **não resolve `$ref`**: `goals`, `reserva_emergencia` e
> `consumo_consciente` são `{"$ref": "#/$defs/..."}` e declaram `number` lá dentro. Com
> `$ref` resolvido o schema-monetário é **18** e **é** superconjunto das 17 da produção.
> (3) `proventos_por_ativo` não é raiz morta: tem produtor (`e5_analyzer_adapter.py:862`),
> consumidor (`S3InvestimentosSection.tsx`) e teste e2e vivos — o que há é **zero** informe
> `proventos_acoes` **neste workspace**. Chamar isso de "teto inalcançável" é a mesma
> conflação que esta lane atacou, deslocada de *fixture vs. produção* para *este workspace
> vs. os workspaces*. O motivo que **sobrevive** é outro e está em [[ADR-281]]
> §Emenda 2026-09-02: o schema não alcança `irpf_kpis` (declara 5 campos, o E5 emite 20, e
> todo o dinheiro está entre os 15 não declarados). Piso declarado e chão medido têm buracos
> diferentes — o universo defensável é a **união**, não um dos dois.

> **Superado em 2026-09-02 (§Fecho D3):** o schema deixou de ser alternativa recusada e
> virou **origem** — piso declarado ao lado do chão medido. O parágrafo abaixo fica como
> registro do que se sabia no dia.

**Limite declarado.** O roster cobre o que já foi **medido**. Raiz que só apareça num
workspace ainda não medido fica fora até alguém rodar o CLI sobre aquele artefato — e é
para isso que ele reprova por raiz-fora-do-roster. O DB local tem **1** workspace; a
estabilidade foi medida em 40 artefatos E5 (as 17 aparecem em 38–40 deles; `ratios` em 4,
porque é recente).

## Critério de aceite

- [x] **1. O universo é derivado do payload sob medição, não de constante.** O roster é
      construído por `Roster.observing(origem, measure_coverage(payload))` — fixture pelo
      rebaseline do pytest, produção pelo CLI. Nenhuma raiz é digitada à mão.
- [x] **2. Raiz monetária presente na produção e ausente do universo reprova.**
      `Roster.outside()` + `test_nenhuma_raiz_monetaria_fora_do_roster` (fixture, no CI) e
      `dev/lineage_coverage.py <payload> --origem <x>` (produção, exit 1). Falsificado:
      payload sintético com `raiz_nova_de_producao.total_brl` ⇒ CLI reprova com a raiz
      nomeada; run `7d860f0b` (outro run de produção) ⇒ exit 0, o roster generaliza.
- [x] **3. O número publicado declara denominador e origem.** `cobertura_publicada`
      no roster (`numerador`/`denominador`/`ratio_pct`/`origens`), asseverado contra a
      medida por `test_o_numero_publicado_declara_denominador_e_origem`, que também exige
      **≥2 origens** — roster de origem única é o defeito voltando.
- [x] **4. A queda é registrada como correção.** 35,7% → **29,4%**, propagada para
      [[ADR-281]], [[A27.l2]], o `_README` da sprint e o `PV13-12`.

## A prova de não-inércia

`test_o_denominador_publicado_nao_e_o_da_fixture` é o contrafactual que discrimina os dois
desenhos: ele exige que o roster conheça raiz além das da fixture **e** que a medida
só-fixture seja **mais alta** que a publicada — o viés, com sinal. Falsificado ponta-a-ponta:
reconstruído o roster single-origin do desenho anterior, ele reproduz exatamente
**5/14 = 35,7%** e **2 dos 6 testes reprovam** (este e o de origem/denominador declarados);
os outros 4 passam, porque o mecanismo da A27.l2 estava certo.

## Achado roteado — **fechado** pelo #1967 (2026-09-02)

`tributario` era emitido pelo E5 e **não era declarado** em
`config/schemas/e5_analysis.schema.json` — passava por `additionalProperties: true` com 15
folhas monetárias. Roteado como defeito de contrato do E5, não de lineage. **Fechado** no
[#1967](https://github.com/davidrobert/mathoms/pull/1967) (`9582364a`), que mediu a varredura
completa (a raiz é emitida em **52 de 54** artefatos e era a **única** emitida e não
declarada), derivou o conjunto de `dataclasses.fields(CascataOutput)` em vez do corpus — que
teria fabricado 6 campos `"type": "null"` — e achou um segundo defeito atrás do primeiro:
`cascata_to_dict` devolvia `tuple` em `triggers`/`signals`, que sobrevive ao `json.dumps` mas
reprova no jsonschema, que valida **antes** de serializar.

## O que esta lane NÃO fecha

As raízes monetárias sem rastro continuam sem rastro — a lane conserta o **denominador**,
não a cobertura. A dívida contável passa de **9** (o que a A27.l2 publicava) para **12**:
`previdencia_pgbl`, `real_estate` e `tributario` sempre estiveram sem rastro, e agora
aparecem. Não são 13 porque `narrativas` nunca foi dívida — nunca publicou dinheiro.

## Fecho dos achados do closeout — 2026-09-02

Dois defeitos **na entrega desta lane**, achados pelo closeout, mais dois limites que ele
expôs. Registrados como deferimento e **fechados no mesmo dia**, no PR do fecho. Cada um tem
o contrafactual que o mata — todos falsificados por mutação, com o teste indo a vermelho
contra o código antigo e voltando a verde na reversão.

### D0 ✅ — o artefato publicado declara origem e data de cada observação

`dev/snapshots/lineage_coverage_baseline.json` publica `cobertura_publicada: 29,4%` **sem**
dizer que é teto. Quem ler o arquivo não vê esta lane. Não foi corrigido à mão de propósito:
o campo é **gerado** por `Roster.dump()`, então edição manual some no próximo rebaseline — a
ressalva tem que nascer do produtor, e isso é código, não doc.


**Fechado.** `Roster.dump()` passa a emitir `observado_em` por origem, e o `_doc` do arquivo
nomeia o que cada origem é. A ressalva nasce do produtor, não de edição manual — que era o
motivo de não a ter corrigido à mão.

### D1 ✅ — o classificador de folha passa a ver dinheiro em string decimal

`_is_monetary_leaf` (`dev/lineage_coverage.py`) exige `isinstance(obj, (int, float))`. Medido
sobre o payload de `40d1af2a`: **284** folhas monetárias serializadas como string decimal, e
**duas raízes existem só por elas** — `irpf_kpis` (`ir_pago_total_brl`,
`renda_anual_familiar_brl`, `dedutiveis_aplicados.*.utilizado_brl`) e `protecao_patrimonial`
(`premio_total_anual_brl`, declarado `{"type":"string","pattern":"^-?\\d+(\\.\\d{1,2})?$"}`
em `protecao_patrimonial.schema.json`). Denominador verdadeiro **19**, não 17 ⇒ o número
publicado seria **5/19 = 26,3%**.

A ironia registrada: a docstring do módulo já dizia que `_lineage` "serializa valor como
string e não cairia no predicado de qualquer forma". Eu vi o comportamento num lugar e não o
levei para o denominador.

**Critério:** mutar `ir_pago_total_brl` de string para número **não** move o denominador — se
mover, a raiz entrou pelo tipo, não pelo caminho.


**Fechado.** `MONEY_STR = ^-?\d+(\.\d{1,2})?$`; folha é monetária se `is_monetary(path)` e o
valor é número **ou** string decimal. Denominador da produção: 17 → **19**.
**Falsificado:** revertido o predicado para `int|float`,
`test_dinheiro_em_string_decimal_entra_no_denominador` vai a **vermelho**; revertida a
mutação, volta a verde. O teste é o contrafactual do enunciado — a raiz entra pelo
**caminho**, não pelo tipo: trocar a string por número **não** move o denominador.

### D2 ✅ — `Roster.observing` não encolhe o universo sem autorização explícita

`_merge` **retira** a origem das raízes ausentes na nova observação. Re-observar o **mesmo
rótulo** com um payload mais pobre encolhe o universo e **sobe** a cobertura. Medido nos dois
sentidos sobre artefatos reais do DB, com a suíte **6 passed** em ambos:

| Re-observação de `producao:40d1af2a` | Denominador | Número | Suíte |
| --- | --- | --- | --- |
| run `7aae4799` (2026-05-29, 16 raízes) | 17 → **18** | 29,4% → 27,8% | 6 passed |
| run `40d1af2a` sobre esse roster de 18 | 18 → **17** | 27,8% → **29,4%** | 6 passed |

O guard só morde no extremo em que a produção encolhe **exatamente** até as 14 da fixture;
encolhimento parcial passa mudo — e a direção otimista é a que passa.

**Critério:** `observing()` monotônico por rótulo (só acrescenta; encolher exige rótulo novo,
e `producao:<run8>` já é um rótulo por run), ou `--update` reprovando queda de denominador
sem flag explícita. O contrafactual de não-inércia é a segunda linha da tabela acima.


**Fechado.** `_merge` levanta `RosterEncolheria` nomeando as raízes que sairiam, com o
denominador antes/depois e a direção do número. Encolher exige `--permitir-encolher` (CLI) ou
`MATHOMS_UPDATE_LINEAGE_COVERAGE=encolher` (rebaseline).
**Falsificado:** desarmado o guard, `test_o_roster_nao_encolhe_sem_autorizacao` vai a
**vermelho** — e o teste assevera as duas metades, que o guard morde e que a válvula de escape
abre.

### D3 ✅ — o piso vem do contrato, e toda origem declara quando foi observada

Nada no CI ou no `nightly.yml` roda `dev/lineage_coverage.py --update`. A lane declarou o
limite na dimensão **workspace** ("workspace ainda não medido") e não na dimensão **tempo no
workspace já medido**, que tem taxa medida: `equilibrio_cerbasi` entrou em 2026-07-06 e
`ratios` em 2026-08-29 — só os 4 runs mais recentes de 71 a emitem. Raiz nova só-produção
depois de `40d1af2a` mantém o denominador em 17 e nenhum gate reprova.


**Fechado por dois lados.** (1) O **contrato E5** entra como a origem `schema` — piso
declarado, recomputado a cada run do gate: raiz monetária nova no schema **reprova** até
alguém rebaselinar, então o denominador cresce sozinho sem depender de ninguém rodar o
pipeline. É o que fecha a cegueira de *workspace não medido* que a lane havia só declarado:
`proventos_por_ativo` entra no denominador com origem `schema`, e a origem diz **por quê** —
ela tem produtor (`e5_analyzer_adapter.py:862`), consumidor (`S3InvestimentosSection.tsx`) e
teste e2e vivos, com zero informe `proventos_acoes` neste workspace. (2) Toda origem carrega
`observado_em`, o CLI imprime as datas, e o gate exige que exista **alguma** observação de
produção — sem isso o universo volta a ser só o que o CI mede.

**O que continua sem gate, e é declarado:** a *idade* da observação de produção não reprova o
CI. Gate de calendário fica vermelho num dia arbitrário e bloqueia PR alheio; a re-observação
é passo da rodada unificada, que é onde um run real acontece.

### Fora do escopo desta lane, roteado

`config/schemas/e5_analysis.schema.json` declara **5** campos em `properties.irpf_kpis` e o
E5 emite **20** — 15 fora do contrato, com todo o dinheiro entre eles. É dívida de contrato
(`config/schemas/`), irmã da que o #1967 fechou para `tributario`.

## Correção de amostra (2026-09-02)

Onde esta lane diz "40 artefatos E5 do DB", o DB tem **71** — 54 sob o stage descritivo
`analyze_finances` e **17** sob o legado `E5`. Consultei um só dos dois nomes, apesar de a
paridade legacy↔descritivo estar no CLAUDE.md. A conclusão que a amostra sustenta não muda
(a união sobre os 71 dá 18 raízes, e `proventos_acoes` é 0 em 312 informes), mas o número
citado estava subdeclarado.
