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

> ⚠️ **Closeout 2026-09-02 — o número que esta lane publica é, ele mesmo, otimista.** Um
> `data-engineer` atacou a entrega e dois defeitos passaram pela medição, ambos da **mesma
> classe que a lane existe para fechar** (universo cego ⇒ viés otimista), deslocada de
> *origem* para outros dois eixos. Registrados em §Deferimento datado abaixo. `29,4%` deve
> ser lido como **teto**: o piso medido é **26,3%**.

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

## O universo: roster de origens, não o que uma fonte emite

A A27.l2 derivava o universo do payload da fixture — o que estava certo como *mecanismo* e
errado como *sujeito*. O universo agora é um **roster** (`dev/snapshots/lineage_coverage_baseline.json`):
cada raiz guarda **as origens em que foi observada**, e o número publicado é sobre o
universo inteiro.

| Origem | Raízes monetárias | Cobertas |
| --- | --- | --- |
| `fixture` (dogfood determinística) | 14 | 5 |
| `producao:40d1af2a` | 17 | 5 |
| **Roster publicado** | **17** | **5** → **29,4%** |

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

## Deferimento datado — 2026-09-02 · dono: `data-engineer` (pickup do dono)

Dois defeitos **na entrega desta lane**, achados pelo closeout. Não são doc: são código, e
por isso não entram no PR de correção documental. O número publicado fica declarado como
**teto** até fecharem.

### D1 — o classificador de folha não vê dinheiro em string decimal

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

### D2 — `Roster.observing` não é monotônico, e o encolhimento sobe o número calado

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

### D0 — enquanto D1/D2 não fecham, o artefato publicado não carrega a ressalva

`dev/snapshots/lineage_coverage_baseline.json` publica `cobertura_publicada: 29,4%` **sem**
dizer que é teto. Quem ler o arquivo não vê esta lane. Não foi corrigido à mão de propósito:
o campo é **gerado** por `Roster.dump()`, então edição manual some no próximo rebaseline — a
ressalva tem que nascer do produtor, e isso é código, não doc.

### D3 — sem re-observação, o roster envelhece sempre para o lado otimista

Nada no CI ou no `nightly.yml` roda `dev/lineage_coverage.py --update`. A lane declarou o
limite na dimensão **workspace** ("workspace ainda não medido") e não na dimensão **tempo no
workspace já medido**, que tem taxa medida: `equilibrio_cerbasi` entrou em 2026-07-06 e
`ratios` em 2026-08-29 — só os 4 runs mais recentes de 71 a emitem. Raiz nova só-produção
depois de `40d1af2a` mantém o denominador em 17 e nenhum gate reprova.

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
