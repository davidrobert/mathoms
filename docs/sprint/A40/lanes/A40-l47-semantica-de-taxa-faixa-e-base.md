---
id: A40.l47
type: lane
title: "Três números do relatório cuja semântica não bate com o rótulo: taxa de retirada, faixa comportamental e base da reserva"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l47-semantica-de-taxa-faixa-e-base
owner: financial-planner
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/frontend
---

# A40.l47 — `l47-semantica-de-taxa-faixa-e-base`

> **Aberta em 2026-08-12**, da revisão r4 registrada em [[REPORT-REVIEWS-active]]
> §r4 (report `7a7d7115` sobre run `ee124571`). Dono: `financial-planner`.
> Agrupada **por domínio de dono**, não por severidade: os achados aqui precisam
> do mesmo especialista para fechar, e lane com donos distintos não fecha.

## Problema

Três achados de domínio da r4. Nenhum é erro de cálculo — os três são o **rótulo
discordando do que o número mede**, que é pior: o cálculo confere, então nenhum
invariante de conservação acusa.

1. **Taxa de retirada publicada como meta de rentabilidade.** O campo de
   rentabilidade guarda a TRS efetiva (renda passiva ÷ patrimônio gerador) e a
   "meta" ao lado é a premissa de saque do número da IF — não uma meta de
   **retorno**. O parecer leu o payload fielmente e amplificou: emitiu risco de
   severidade alta *"rentabilidade abaixo da meta"* + métrica-alvo. A [[ADR-191]]
   registra as duas taxas **coexistirem**; não autoriza promover uma a meta da
   outra. Consequência de produto: empurra yield-chasing numa carteira em
   acumulação, contra a alocação-alvo publicada no mesmo relatório.
2. **Duas réguas comportamentais no mesmo documento.** As faixas do classificador
   comportamental no código divergem da legenda publicada no apêndice: um rótulo
   que o código emite **não existe** na legenda, e uma faixa da legenda **não
   existe** no código. A família recebe rótulo de topo de escala estando no meio
   da escala que o próprio relatório imprime.
3. **A base da reserva é maior que a carteira exibida.** A composição líquida da
   reserva conta base acima do total da seção de investimentos — a reserva se
   apoia em ativos que a seção nem mostra. E o acoplamento entre "reduzir a classe
   sobre-alocada" e "manter a cobertura" não é divulgado em nenhuma das duas
   superfícies. (Residual de um cluster **refutado** na r4: o "excedente
   inexecutável" caiu, este sobreviveu.)

## Achados cobertos

RV4-13 (Alto) · RV4-15 (Médio) · RV4-18 (Médio). Registro:
[[REPORT-REVIEWS-active]] §r4.

## Escopo

**PR1 — a taxa de retirada deixa de ser meta de retorno.** Decidir, com aval de
domínio, se o campo é renomeado, se a "meta" sai, ou se as duas viram métricas
separadas com rótulo próprio. Exige **emenda datada na [[ADR-191]]** antes do
código: é mudança no que o número afirma. Aceite: o parecer não pode mais emitir
risco de rentabilidade a partir de TRS — teste sobre o manifest.

**PR2 — uma régua só.** Faixas do código e legenda do apêndice passam a derivar da
**mesma fonte**. Aceite: gate que falha se existir rótulo no enforcer sem entrada
na legenda, ou faixa na legenda sem rótulo no enforcer — o gate fecha a classe, não
a instância.

**PR3 — base da reserva declarada.** A superfície declara qual base a cobertura
usa e o que foi excluído (os campos já existem no payload e têm **zero
consumidores**). Aceite: os campos de base e exclusão passam a ter leitor.

## Critério de aceite da lane

Cada um dos três números passa a **declarar sua base na própria superfície**, e
nenhum rótulo afirma uma grandeza diferente da que mede. Divergência que
sobreviver é decisão registrada em ADR, não drift.

## Não-objetivos com rota declarada

Recalcular TRS, cap rate ou cobertura: os cálculos conferem. Mexer na ordenação do
plano — é RV4-13 adjacente mas outro eixo, e a ordenação sem critério encodado
está registrada em RV3-07(b).

## Ataque 2026-08-14 — o que a medição mudou

> Ataque à lane **antes** do primeiro PR: cada afirmação do §Problema foi medida
> contra o código. Os três achados **procedem**; dois têm o **mecanismo trocado** e
> um está **subcontado**. O §Escopo abaixo é revisado por isto — o texto original
> fica como registro.

> **Remedição 2026-08-14, no mesmo dia:** o item 1 abaixo está **errado no ponto
> principal** e fica como registro. Ele conclui, da [[ADR-191]], que `meta_pct` "não é a
> premissa de saque" e que **não** era preciso emenda nova. As duas conclusões caem
> contra o schema canônico — ver §Remedição do item 1. O §Problema original da lane
> estava **certo**; foi o ataque que errou. Itens 2 e 3 seguem válidos.

### 1 — o mecanismo do RV4-13 não é o descrito (o §Problema erra a raiz)

`ratios.rentabilidade.meta_pct` **não é** "a premissa de saque do número da IF". É
`RentabilidadeConfig.meta_pct` — `Decimal("5.0")` congelado
([ratios_calculator.py:81](../../../../pipeline/domain/services/ratios_calculator.py)).
`RatiosCalculator()` é construído sem config em
[e5_analyzer_adapter.py:350](../../../../pipeline/domain/services/e5_analyzer_adapter.py),
e o parâmetro `ratios_calculator=` **nunca é passado** — nem em produção nem em
teste. É o **único** analyzer da fábrica do E5 sem fiação: os irmãos todos recebem
`EquilibrioCerbasiConfig.from_scoring` / `DiagnosticoComportamentalConfig.from_scoring`
/ `PontosFortesConfig.from_scoring` / `ConsumoConscienteConfig.from_configs`.

**Já registrado:** [FORMULAS.md §117](../../../reference/FORMULAS.md) diz isto com
todas as letras — *"o número exibido não é o da família (residual declarado em
A40.l4)"*. PR1 **fecha ou roteia** esse residual; não o redescobre.

Há **três** portadores de "meta TRS", dois vivos e desconectados:

| Portador | Fonte | Estado |
|---|---|---|
| `RentabilidadeConfig.meta_pct` | constante `5.0` no código | **vivo** — card S3 + sublabel S7 + parecer |
| `IfProjectorConfig.if_trs_pct` | `goals.trs_pct` ([if_projector.py:132-138](../../../../pipeline/domain/services/if_projector.py)) | **vivo** — converte a meta de IF em renda mensal (`:342`) |
| `PassiveIncomeConfig.trs_meta_pct` | `goals.trs_pct` ([e5_analyzer_adapter.py:1226](../../../../pipeline/domain/services/e5_analyzer_adapter.py)) | **morto** — 2 hits no repo: a declaração e o construtor. Ninguém lê |

**Consequência que a lane não nomeia:** família que configure `trs_pct = 4` lê "com
TRS de 4%" na narrativa da IF **e** "Yield-alvo 5,0%" no S7
([S7IndependenciaSection.tsx:405-406](../../../../frontend/src/components/report/sections/S7IndependenciaSection.tsx)),
com o KPI colorido `critical` contra 5 no S3
([RentabilidadeCard.tsx:225](../../../../frontend/src/components/report/cards/RentabilidadeCard.tsx)
`pickVariant`). É o aceite da emenda 2026-07-15 da [[ADR-191]] violado — *"Nenhuma
superfície rotula a mesma taxa como 4% e 5%"* — **por construção**, não por drift.

**Onde "taxa de retirada" é de fato publicada como o sentido do número:** o glossário
do próprio relatório define **TRS = "Taxa de Retirada Segura … Referência: 4–5% a.a."**
([ApendiceASection.tsx:8](../../../../frontend/src/components/report/sections/ApendiceASection.tsx),
vivo via `MigratedSection.tsx:87`). A emenda da ADR-191 mandou **nunca colapsar** os
dois conceitos; o glossário os colapsa numa linha, com faixa que cobre os dois. A
lane não menciona esta superfície — e ela é a que ensina a família a ler o número.

**Logo PR1 não precisa de emenda nova na [[ADR-191]].** A pergunta ("yield-alvo 5% ≠
SWR 4%, nunca colapsar") **já foi decidida** em 2026-07-15. Falta **aplicar** a
decisão ao glossário e à constante congelada. Emendar de novo para repetir o já
decidido é no-op: o registro certo de pendência é §Deferimento datado com dono, não
emenda que repete a decisão anterior.

**Sobre o aceite "teste sobre o manifest":** o manifest publica `meta_pct` **duas
vezes** ao LLM — bloco escalar `$.ratios.rentabilidade` (raw, 800 chars) **e** bloco
`key_value` com `$.ratios` raw ([parecer_planejador.yaml §context_sections/ratios](../../../../config/prompts/parecer_planejador.yaml)).
Despublicar exige os dois. E os `narrative_hints` existentes vetam a comparação com
meta só em `sem_irpf` / `gerador_zero` / `suspeito` — em `status: ok` a comparação
está **implicitamente autorizada**. Um 4º hint negativo não é gate
(instrução negativa nomeia o mecanismo sem exercitá-lo); o movimento enforçável é
despublicar a folha, no padrão do PR3b da [[A40.l34]].

### 2 — RV4-15 procede e está subcontado: 4 discrepâncias, não 2

Enforcer vivo ([equilibrio_cerbasi_analyzer.py:85-88](../../../../pipeline/domain/services/equilibrio_cerbasi_analyzer.py)
via `from_scoring` ← [scoring.json:145-148](../../../../config/scoring.json)):
`≥30 Investidor · ≥20 Equilibrado · ≥10 Endividado consciente · ≥0 Gastador`.
Legenda viva ([ApendicesSections.tsx:163-165](../../../../frontend/src/components/report/sections/ApendicesSections.tsx),
dentro de `ApendiceBSection`): `Gastador (<10%), Equilibrado (20–40%), Poupador (>40%)`.

1. Rótulos que o código emite e a legenda não nomeia: **dois** — `Investidor` **e**
   `Endividado consciente`. A lane diz "um".
2. Rótulo que a legenda nomeia e nenhum produtor emite: `Poupador`.
3. **O rótulo comum discorda da própria faixa**: código `Equilibrado = [20, 30)`;
   legenda `20–40%`. A 35% de futuro o código imprime "Investidor" e a legenda da
   mesma página diz que aquilo é "Equilibrado".
4. A legenda deixa **10–20% sem entrada** (Gastador `<10`, Equilibrado começa em 20)
   — família nessa faixa lê legenda que não tem linha para o rótulo que recebeu.

**Sítios da faixa: 3 no código + 1 legenda**, não 2. `scoring.json:145-148` (fonte
viva), `_DEFAULT_CLASSIFICACAO` (fallback do enforcer) e
[analyze_finances.py:2041-2044](../../../../scripts/analyze_finances.py) — **cópia
morta**: `analyze_equilibrio_cerbasi` é definida e **nunca chamada** (mesma classe da
cópia morta triada na [[A40.l50]]). O gate do PR2 tem de **declarar qual é o
enforcer**, senão fecha verde contra o espelho morto
(gate que não declara o alvo fecha instância, não classe).

`config/report_spec.md:1239` carrega um 5º vocabulário ("Pendendo para Futuro"…),
mas o cabeçalho o marca **LEGADO, não fonte de verdade** — não conta como sítio.

### 3 — RV4-18: mecanismo confirmado, fixture cega, e uma chave já refutada

**Mecanismo (confirmado, e é por construção):** o numerador da reserva lê
`patrimonio[identity.inv_key(member)]`
([reserva_liquidez.py:104](../../../../pipeline/domain/services/reserva_liquidez.py))
mais o caixa do E3 — o **agregado patrimonial**, não a seção de investimentos, que
renderiza `investimentos.tabela_classes` de outro produtor. `base(reserva) ⊄ carteira
exibida` **por construção** — daí nenhum invariante de conservação acusar, exatamente
como o §Problema diagnostica.

**A fixture não reproduz o achado.** Em `backend/tests/snapshots/dogfood_view_model.json`,
`composicao_liquida.total_liquido` bate **exatamente** com a linha "Renda Fixa" de
`tabela_classes`, e `composicao_liquida.caixa == 0`. Gate construído sobre essa
fixture é cego ao efeito (instrumento cego ao efeito por construção). A
fixture **serve** para o aceite de leitor (tem `excluido_da_reserva.caixa_nao_classificado > 0`),
mas **não** para a divergência — que precisa de fixture própria.

**"Zero consumidores" vale para 2 dos 3 campos, e o 3º já foi refutado.**
`excluido_da_reserva` e `base_denominador` não têm leitor em `frontend/src`;
`composicao_liquida` **tem** (`HeroKpiGrid.tsx`). E a [[A40.l50]] já triou
`excluido_da_reserva.caixa_moeda_estrangeira` como *"'nenhum consumidor' é forte
demais"* — bate com a superfície de exposição cambial. PR3 não reabre essa chave como
se fosse órfã (achado com medição citada em outra lane exige remedir, não reabrir).

### Remedição do item 1 — o ataque errou, a lane estava certa

Fui checar `goals.trs_pct` na fonte antes de ligar a fiação. **Três fontes canônicas
dizem que é taxa de saque**, e são elas que governam — não a prosa da ADR:

- `goal.if.v2.schema.json` §inputs: *"Taxa de Retirada Segura operacional… Trinity
  Study clássico"*; §derived: `if_meta_bruta_brl = renda × 12 ÷ (trs_pct/100)` — o
  divisor da regra ×25;
- wizard da Meta IF, passo 2: coleta sob o rótulo **"Taxa de Retirada Segura (TRS)"**
  (*"percentual do patrimônio que você pode sacar por ano"*);
- o mesmo schema tem campo **separado** para retorno: `retorno_real_anual_pct`.

Logo o §Problema desta lane estava certo: a "meta" ao lado da TRS efetiva **é** premissa
de saque. A emenda de 2026-07-15 da ADR-191, que atribuiu `goals.trs_pct` ao card como
yield-alvo, é a outlier — e é ela que registra a promoção. Duas correções ao item 1:
**precisa** de emenda datada (feita: §Emenda 2026-08-14), e a fiação que eu já tinha
escrito (`meta_pct ← goals.trs_pct`) **teria completado o defeito** em vez de corrigi-lo
— pegaria o número que a família digitou como "quanto posso sacar" e o imprimiria como
alvo contra o qual pintar o KPI de `critical`.

O que **sobrevive** do item 1: a constante congelada (`RatiosCalculator()` sem config,
`ratios_calculator=` nunca passado) é real e é o que **mascarava** a promoção; o campo
morto `PassiveIncomeConfig.trs_meta_pct` é real; a dupla publicação no manifest é real; e
o glossário definindo TRS como "Taxa de Retirada Segura" é real — só que ele estava
**certo sobre `trs_pct`** e errado por usar a mesma sigla do card. Virou duas entradas.

### Escopo revisado

- **PR1 ✅** (`c416ac90`, em `main` via #1452 `ae2b2453`) — `meta_pct` sai do payload, do domínio, do schema E5, do tipo
  TS e do comparador das duas superfícies; KPI fica neutro. Removidos junto o campo
  morto `trs_meta_pct`, `trsTone` e `readYieldAlvoPct`. Emenda datada na [[ADR-191]]
  (§D6) + glossário separando "TRS (Taxa de Retirada Segura)" de "TRS efetiva" +
  `FORMULAS.md`. Gate é de **ausência na superfície**, provado por mutação.
  Deferido sem dono: `goals.yield_alvo_pct` para a família configurar alvo próprio —
  abre schema + migration + wizard, não cabe nesta lane.
- **PR2 ✅** (`5022e8ec`) — o E5 publica `equilibrio_cerbasi.classificacao_faixas` (a
  régua que de fato classificou) e a legenda do apêndice renderiza dela. Escolhido
  **publicar no payload** em vez de codegen a partir do `scoring.json` global: override
  de `scoring` por workspace mantém legenda e enforcer casados, o que codegen não
  garantiria. Gate fecha a classe — régua custom aparece inteira, rótulo emitido tem de
  estar na régua, e sem régua no payload não se inventa nenhuma. Cópia morta
  (`analyze_equilibrio_cerbasi`, 81 linhas) deletada.
- **PR3 ✅** (`6cd78488`) — o card da reserva declara a base do denominador e o que
  ficou fora, com o acoplamento explícito ("reduzir uma classe sobre-alocada pode
  derrubar a cobertura"). `base_denominador` + `excluido_da_reserva` ganham leitor.
  **Todas as três** chaves de exclusão são exibidas, inclusive
  `caixa_moeda_estrangeira`: a [[A40.l50]] refutou a afirmação de que ela não tem
  consumidor, não a de que deva ser divulgada aqui. `BASE_LABEL` cobre só o vocabulário
  fechado do produtor — o gate do [[ADR-306]] D1 expôs um terceiro rótulo inventado.

### Fixture continua sem expressar a divergência

O aceite entregue é **declaração de base**, que a fixture do dogfood exercita
(`excluido_da_reserva.caixa_nao_classificado > 0`). A divergência
**base-da-reserva > carteira exibida** segue sem fixture que a reproduza — o
`dogfood_view_model.json` tem `composicao_liquida.total_liquido` batendo exato com a
linha "Renda Fixa" de `tabela_classes`. Isso é **deferido sem dono**: exige fixture
sintética própria, e nenhum gate atual a alcança.
