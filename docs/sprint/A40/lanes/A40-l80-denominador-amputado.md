---
id: A40.l80
type: lane
title: "Denominador amputado: metade da carteira não tem dono, o investível a exclui e o bruto a inclui — cinco superfícies medem 'de quanto se sabe o dono'"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l80-denominador-amputado
adrs:
  - "[[ADR-335]]"
  - "[[ADR-340]]"
  - "[[ADR-394]]"
  - "[[ADR-406]]"
  - "[[ADR-412]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
  - area/report
---

# A40.l80 — Denominador amputado (RV8-02 · RV8-03 · RV8-04 · RV8-06 · RV8-10)

> **O primeiro entregável é a DECISÃO, não o código.** O fix aparente é somar um
> termo. A decisão real é *qual base cada número mede*, e ela reabre a
> [[ADR-335]] (§Emenda, autonomia), a [[ADR-340]] (concentração) e o co-design de
> 2026-05-18 que fixou o denominador da banda cambial. Abra **ADR `Proposto`
> antes do PR de implementação** (CLAUDE.md §Política operacional). Co-design
> `financial-planner` (a decisão de domínio) + `data-engineer` (enum/contrato)
> **antes** de escrever o fix.

## Correções à lane (2026-08-25 · re-medição no run `d0f6260a`)

> A decisão está fechada em **[[ADR-412]]** (`Proposto`). Esta seção retrata o que
> a re-medição refutou — nada abaixo foi apagado, e onde o texto original diverge,
> **esta seção prevalece**.

**A tese central se sustenta** (fatia órfã = 48,13% de `investimentos.total_financeiro`;
concentração 66,79% → 50,62% na base cheia, delta 16,17 p.p.). O que não reproduziu:

| # | Está escrito | Medido | Leia assim |
|---|---|---|---|
| C1 | "a banda cambial cruzou para **verde**" | `tier == "indeterminado"`. **Verde é estruturalmente inalcançável**: `_tier` (`exposicao_cambial_analyzer.py:133-136`) curto-circuita porque `carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` incondicionalmente (`:287-292`) desde o #1568 ([[ADR-403]]) — `_tier_from_pct` é código morto em produção | o **pct** cruzou o limiar verde (12,55% ≥ `THRESHOLD_VERDE_PCT`); quem publicou "faixa verde" foi a **prosa do parecer**, não o campo |
| C2 | "o denominador caiu **44,4%**" | 44,4% é razão **cross-run** (r7→r8) e mistura amputação com crescimento de corpus | **dentro do r8 a amputação é 49,03%** (base atual = 50,97% da cheia). Não são intercambiáveis |
| C3 | "a banda volta de verde para amarelo"; "não conserte a banda de volta para verde" | **inobservável** — sob o fix `tier` não se move, segue `indeterminado` | procure o movimento em `pct_investivel_financeiro` (12,55% → 6,40%) e na prosa do parecer. A ausência de flip em `tier` **não** significa que o fix não pegou |
| C4 | corte "composição × runway" | o corte é **domiciliar × por-pessoa** — reserva e autonomia têm denominador de despesa do **domicílio**, logo querem base cheia | [[ADR-412]] §D0. E **neste caso é somar um termo**: `git log -L` mostra regressão do #1550, não escolha de design |
| C5 | §Raio de explosão | omite o **bloco IF inteiro** (`investivel_efetivo:219` → `if_projector`, cone MC, `cenarios_conjuge`), `exposicao_cambial_v2.py:286` (recomputa no read) e `HeroKpiGrid.tsx:85-88` | autonomia e IF movem **mais** que a concentração |
| C6 | "`kpi_targets[].base` não é honrado pelos produtores" | os 10 targets **têm** `base` preenchida — e ela é **incoerente**: `concentracao_imobiliaria` declara `carteira_produtiva` e `exposicao_cambial` declara `investivel_financeiro` para denominadores que compartilham o mesmo termo amputado | o problema é o **vocabulário** do campo, não o preenchimento. Senão o fix vira "preencher o campo" |
| C7 | RV8-06: "abrir o enum `membro` + terceira `CoberturaMembro`" | `CoberturaStatus(linha.get("status"))` (`:144,236`) levanta `ValueError` em **leitor antigo lendo artefato novo**; e `cobertura_investimentos` particiona **pessoas**, a órfã particiona **dinheiro** | **rejeitado** — eixo separado `patrimonio.atribuicao_investimentos` + `Papel` ternário ([[ADR-412]] §D2/§D5) |
| C8 | §Corretude: identidade da reserva | **já fecha hoje, em 0,00%, sobre o defeito** — fecha *porque* a órfã foi absorvida sob rótulo de membro | gate de soma contra defeito que preserva soma. O predicado que discrimina é **partição por item** |
| C9 | — | **o terceiro resolver não está na lane** — ver §abaixo | driver primário do RV8-06 |
| C10 | §Rastro | [[ADR-394]] §D8 declara denominador de 35 sites em 4 arquivos; `reserva_liquidez.py` não está nele | é o inventário do **regex**, não da classe. Emenda datada devida ao flipar a [[ADR-412]] |

### C9 — o terceiro resolver (achado desta sessão, ausente do texto original)

`reserva_liquidez.py:177-191` (`_positions_for_member`) resolve titularidade por
conta própria, com convenção **invertida** — o docstring `:180` declara: *"sem membro
atribuído → titular (convenção legado)"*. É a afirmação que `atribuir_por_membro`
documenta ter removido (`investimentos_cobertura.py:177`).

Medido executando `_filter_liquid` sobre os itens reais, delta 0,00:

- **58,64%** do que a reserva rotula "titular" é dinheiro sem dono
- `composicao_liquida.investimentos_titular` = **2,42×** `patrimonio.investimentos_titular`
- `cobertura_meses` publica **43,9** contra **25,4** na partição correta — **18,5 meses
  inflados**, sob veredito `avaliacao_liquidity: "Excessiva"` (alvo 18)
- ramo culpado: `elif not membro and member_key == identity.titular_key` (`:189-190`) —
  15 das 18 posições têm `membro` vazio e carregam 68,1% do valor

**Sinal oposto ao do patrimônio:** o patrimônio **exclui** a órfã sem declarar; a
reserva a **inclui sob rótulo de pessoa**. No mesmo payload, a composição publica a
linha "Investimentos sem titular identificado" (16,6% do bruto, maior que os dois
membros nomeados somados) enquanto a reserva chama esse dinheiro de titular. As duas
correções são opostas e precisam ser decididas juntas — uma sozinha reabre a outra.

Um único commit na história (`b1df6d64`, 2026-07-06, A28.l1 #787), **nenhum teste**,
**zero menções no vault**. O gate `dev/check_member_key_substring.py` varre o arquivo
e sai `0` porque identifica a chave pelo **nome da variável**
(`_KEY_SUFFIXES = ("titular_key","conjuge_key")`) e ali ela se chama `member_key` —
verde por 7 semanas sobre instância viva da classe que [[ADR-394]] §D8 fechou.

**Não** troque a substring de `:187` por `matches_member_key` como o fix: com
`membro == ""` a substring é `False`, e **100% do excedente vem do ramo `:189-190`**.
Seria fix mal-mirado com gate verde por cima.

## O fato, medido no r8 (run `d0f6260a`)

`patrimonio.investimentos_nao_atribuidos` é **48,1% de `investimentos.total_financeiro`** —
quase metade da carteira financeira sem titular identificado. E as duas funções
que consomem esse valor discordam **dentro do mesmo arquivo**:

| | `pipeline/domain/services/patrimonio_calculator.py` | inclui `nao_atribuidos`? |
|---|---|---|
| `investivel_financeiro` | `:209-212` | **não** |
| `_compute_bruto` | `:403-416` | **sim** |

O valor está no escopo das duas. A exclusão não é declarada em lugar nenhum —
nenhuma superfície diz ao leitor que a base encolheu.

**Não confie nestes números: re-meça.** Eles vêm do r8 e o corpus muda.
`.venv/bin/python dev/dump_artifact.py --run <run> --stage analyze_finances --key analise_financeira --raw`
e recomponha as razões. Achado com medição citada se re-mede antes de virar fix.

## Por que isto não é "somar um termo em cinco lugares"

**Os consumidores não querem a mesma base.** Esta é a decisão que a lane tem de
fechar, e prescrever "inclui em todo lugar" seria errado:

- **Composição** — `ratios.concentracao_imobiliaria` ([[ADR-340]]) e
  `exposicao_cambial.pct_investivel_financeiro` perguntam *que fração da carteira
  é X*. Excluir a fatia órfã do denominador **infla artificialmente** a fração:
  no r8 a concentração publica 66,8% quando sobre a base cheia dá ~50,6%, e a
  banda cambial cruzou para **verde com o total em ME byte-idêntico ao run
  anterior** — o percentual subiu porque o denominador caiu 44,4%, não porque a
  proteção aumentou. Estes querem a base **cheia**.
- **Runway** — `ratios.autonomia_financeira_meses` ([[ADR-335]] §Emenda)
  pergunta *por quantos meses a família se sustenta*. Incluir dinheiro cujo dono
  o sistema não sabe **infla o fôlego** com ativo que pode não ser sacável pelo
  titular. Este talvez queira a base **certificada** — e talvez queira publicar
  as duas.

Se as duas leituras coexistirem, elas **têm de ser nomeadas**: dois números com
o mesmo rótulo e bases diferentes é o defeito RV8-02 recriado um nível acima.
Hoje já há **quatro** bases distintas para "carteira financeira" no mesmo payload.

## Ordem obrigatória: o vocabulário antes do número

**RV8-06 vem primeiro.** Não dá para publicar ressalva de base nem terceiro balde
de reserva enquanto o vocabulário não tiver célula para "sem dono":

- `cobertura_de_membros` (`pipeline/domain/services/investimentos_cobertura.py:207-222`)
  itera **papéis**, e é chamada em `patrimonio_calculator.py:371-375` só com
  `titular=` e `conjuge=`. O balde órfão que `atribuir_por_membro` (`:179-195`)
  acumula sob chave `""` não tem parâmetro.
- `cobertura_investimentos[].membro` é enum **fechado** em `["titular","conjuge"]`
  (`config/schemas/e5_analysis.schema.json:357-360`).
- `review_reasons_da_cobertura` (`:228`) só projeta `nao_apurado` — com as duas
  linhas em `apurado`/`motivo: null`, nada dispara sobre 48,1% da carteira.

Abrir o enum + emitir a terceira `CoberturaMembro` acima do piso de 0,50% já
decidido na [[ADR-406]] é o que **destrava** RV8-02/03/04/10. Feito isso, a razão
dispara e o run passa a reter — comportamento desejado, mas que precisa de
rollout controlado (há precedente de flag: `cobertura_enforcement_ligado()`).

## Escopo por achado

| Achado | Superfície | O que fecha |
|---|---|---|
| **RV8-06** | `investimentos_cobertura.py:207-222` · `e5_analysis.schema.json:357` | terceira linha de cobertura para a fatia órfã; razão dispara acima do piso |
| **RV8-02** | `patrimonio_calculator.py:209-212` vs `:403-416` | base decidida e **declarada** por consumidor; assimetria intra-arquivo eliminada ou justificada em docstring + ADR |
| **RV8-03** | `exposicao_cambial_analyzer.py` (`_pct_sobre`, `:282-308`) | banda recomputada sobre a base decidida; regra pós-LLM que barra `pontos_fortes` cuja banda dependa de base com fatia órfã acima do piso |
| **RV8-04** | `reserva_emergencia_calculator.py:231` + `reserva_liquidez.py` | terceiro componente em `composicao_liquida`; **nenhum valor sem dono sob rótulo de membro** |
| **RV8-10** | `frontend/src/components/report/utils/visibleCompositionRows.ts:47-51,75-79` | `kind`/estado próprio no produtor; a lacuna sai das fatias do donut e vira anotação |

## Raio de explosão — mapeado, e move a capa

Alterar `investivel_financeiro` move, em cascata: `patrimonio.investivel_efetivo`
(`:219`) · `ratios.autonomia_financeira_meses` · `ratios.concentracao_imobiliaria`
· `exposicao_cambial.pct_investivel_financeiro` **e a banda** ·
`financial_score_calculator` (`concentracao_imobiliaria` é **componente de score**)
· `kpi_target_catalog.py:81-82` · e o valor projetado ao LLM em
`config/prompts/parecer_planejador.yaml:183`.

**Armadilha que vai parecer defeito e não é.** Corrigido o denominador, o
`dev/compare_reviews.py` vai reprovar em massa: a concentração cai ~16 p.p., a
banda cambial volta de verde para amarelo e o score se move. **Isso é a correção,
não regressão** — o r7 já ensinou essa lição (o compare leu correção como
regressão e congelar o baseline teria aprovado a corrupção). Declare os paths
esperados no PR. E **não** "conserte" a banda de volta para verde.

## Critério de aceite

**Corretude** — a identidade da reserva se preserva com o terceiro componente:
`composicao_liquida.{titular + conjuge + sem_titular} + excluido_da_reserva.investimentos_nao_liquidos`
== `patrimonio.{investimentos_titular + investimentos_conjuge + investimentos_nao_atribuidos}`.
Teste em `tests/test_e5_conservation_invariants.py`, tolerância zero.

**Completude** — nenhum consumidor do denominador fica na base antiga por
omissão. Gate: teste que enumera os consumidores de `investivel_financeiro` e
falha se algum não declarar sua base. Consumidor novo nasce obrigado a declarar.

**Consistência** — nenhum par de superfícies do mesmo payload publica o mesmo
conceito sobre bases diferentes sem nomeá-las. Verificação empírica: as quatro
bases de "carteira financeira" hoje existentes viram uma canônica + derivadas
declaradas.

**Precisão** — a base de cada número é **campo**, não prosa: `kpi_targets[].base`
já existe e não é honrado pelos produtores; `motivo` deixa de ser `null` quando a
fatia órfã cruza o piso. Afirmação em prosa envelhece no rebase; campo não.

**Prova de fecho** — o predicado que o r9 vai medir: `cobertura_investimentos`
contém linha para a fatia órfã sempre que ela é > piso; a banda cambial recomputa
sobre a base declarada; e **nenhum** `pontos_fortes` do parecer se apoia em banda
cuja base tenha fatia órfã acima do piso.

## Rebaseline consciente

`backend/tests/test_report_view_model_snapshot.py` e as baselines visuais de print
vão precisar de rebaseline. **Olhe as imagens** — baseline commitada sem olhar já
passou defeito neste repo. O hook `Rebaseline de golden isolado de código de
produção (G-c)` exige commits separados. Se algum DTO mudar,
`make update-openapi-snapshot`. Se o manifest do parecer mudar, bump de
`PROMPT_VERSION`.

## Ao abrir a ADR

**Nunca reserve ID.** Aloque na escrita (`ls docs/adr/ | tail -1`) — citar
"ADR-NNN" em prosa para segurar número não funciona e o próximo agente rouba.
Declare supersedência bidirecional se emendar [[ADR-335]] ou [[ADR-340]].

## Rastro

Achados do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`, 2026-08-24),
cluster "Denominador amputado". Cru e números de instância em
`storage/<uuid>/reviews/20260824-2235-d0f6260a/` (off-git).
