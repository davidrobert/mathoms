---
id: ADR-412
type: adr
title: "Base canônica única para carteira financeira, `Papel` ternário e produtor único do eixo de posições atuais"
status: Proposto
phase: A40.l80
date: "2026-08-25"
relates_to:
  - "[[ADR-279]]"
  - "[[ADR-335]]"
  - "[[ADR-340]]"
  - "[[ADR-394]]"
  - "[[ADR-403]]"
  - "[[ADR-406]]"
  - "[[ADR-410]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 412"
  - "base canônica de carteira financeira"
  - "Papel ternário"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
  - area/report
---

# ADR-412 — Base canônica única para carteira financeira, `Papel` ternário e produtor único do eixo de posições atuais

> **Proposto.** Abre a implementação da [[A40.l80]] (RV8-02/03/04/06/10). Ao flipar
> para `Decidido`: emenda datada em [[ADR-335]] §Emenda (autonomia vira intervalo
> com veredito suprimido), emenda datada em [[ADR-394]] §D8 (o denominador de 35
> sites é o inventário do regex, não da classe) e supersedência bidirecional se
> alguma delas for reaberta. Acima de 150 linhas por cobrir D0–D9 de uma decisão
> que a lane exige fechar num ato — separar viraria decisão parcial citável.

## Contexto

`patrimonio.investimentos_nao_atribuidos` — posições cujo membro o resolver não
canonicalizou — é **48,1% de `investimentos.total_financeiro`** e **61,0% de**
`(investimentos_titular + investimentos_conjuge + investimentos_nao_atribuidos)`
no run de dogfood `d0f6260a`. Três defeitos convivem sobre essa fatia:

**(a) Assimetria intra-arquivo.** Em `pipeline/domain/services/patrimonio_calculator.py`,
`investivel_financeiro` (`:209-212`) **exclui** o termo e `_compute_bruto`
(`:403-416`) o **inclui**. `git log -L` mostra que não é escolha de design: o termo
entrou em `_compute_bruto` no commit `93d824a4` (#1550, [[A40.l69]]/[[ADR-394]] §D8)
e `investivel_financeiro` não foi tocado no mesmo PR. É **regressão**, e a exclusão
não é declarada em superfície nenhuma.

**(b) Terceiro resolver, com convenção invertida.** `reserva_liquidez.py:177-191`
(`_positions_for_member`) resolve titularidade por conta própria e o docstring
declara a convenção: *"sem membro atribuído → titular (convenção legado)"*. É
exatamente a afirmação que `atribuir_por_membro` documenta ter removido
(`investimentos_cobertura.py:177`: *"Chave que não casa titular nem cônjuge NÃO é
do titular. Somar ao titular afirmava posse que ninguém mediu"*).

Medido no mesmo run, executando `_filter_liquid` sobre os itens reais: **58,6% do
que a reserva rotula "titular" é dinheiro sem dono**; `composicao_liquida.investimentos_titular`
é **2,42×** `patrimonio.investimentos_titular`; `cobertura_meses` publica **43,9**
contra **25,4** na partição correta — **18,5 meses inflados**, sob veredito
`avaliacao_liquidity: "Excessiva"` (alvo 18 meses). O ramo culpado é
`elif not membro and member_key == identity.titular_key` (`:189-190`): 15 das 18
posições têm `membro` vazio e carregam 68,1% do valor. A substring `member_key in membro`
(`:187`) contribui **zero** neste run — `"" in x` é `False` — e o fallback
`agregado_sem_itens` é inalcançável com 18 itens.

O ramo tem **um único commit** na história (`b1df6d64`, 2026-07-06, A28.l1 #787),
**nenhum teste** e **zero menções no vault**. O gate `dev/check_member_key_substring.py`
varre o arquivo e sai `0` porque identifica a chave pelo **nome da variável**
(`_KEY_SUFFIXES = ("titular_key","conjuge_key")`) e ali ela se chama `member_key`
— verde por 7 semanas sobre instância viva da classe que [[ADR-394]] §D8 fechou.

**(c) Veredito suprimido no código, republicado pela prosa.** `_tier`
(`exposicao_cambial_analyzer.py:133-136`) devolve `"indeterminado"` de propósito —
*"superestimar diz 'está protegido' a quem não está"*. Mas
`config/prompts/parecer_planejador.yaml:182-184` projeta ao LLM o `pct` cru **junto
com a legenda** `"verde >=10% / amarelo 5-10% / vermelho <5%"`, e o LLM reconstrói
a faixa que o código recusou — sobre um percentual que a base amputada dobrou
(**12,55%** na base atual, **6,40%** na cheia).

## Decisão

### D0 — Existe UMA base canônica; o que varia é se o veredito sobrevive

O eixo não é *composição × runway* — é **domiciliar × por-pessoa**.
`reserva.cobertura_meses` e `ratios.autonomia_financeira_meses` têm denominador de
**despesa do domicílio**, logo são domiciliares e querem a base cheia como qualquer
composição. A fatia órfã não é dinheiro ausente nem de outra unidade econômica: é
dinheiro **medido cuja etiqueta de pessoa faltou** (`sum(dados)/sum(total_por_membro)
= 1,000000` — patrimônio e reserva leem o mesmo universo e só o particionam
diferente). Consumidor que não tolera a incerteza **para de assinar veredito**;
não troca de denominador. Trocar o denominador responderia *"de quanto eu sei o
dono"* sob o rótulo *"quanto a família tem"* — o RV8-02 com sinal invertido.

Só superfície **por-pessoa** (`investimentos_titular`, divisão de `cenarios_conjuge`)
é por-membro, e essa **nunca** recebe a órfã.

### D1 — `BaseFinanceira`: enum fechado com termos declarados em dados

Novo `pipeline/domain/services/bases_financeiras.py`:

| valor | termos |
|---|---|
| `carteira_financeira_familia` **(canônica)** | `investimentos_titular + investimentos_conjuge + investimentos_nao_atribuidos + caixa_total_brl` |
| `carteira_produtiva_familia` | `carteira_financeira_familia + cat2_efetivo` |
| `carteira_com_titular_identificado` | base atual amputada — **uso restrito ao extremo inferior de intervalo declarado; proibida como denominador de número publicado sozinho** |
| `patrimonio_liquido` · `despesa_essencial_domicilio` | já existentes |

`patrimonio.bases` vira bloco publicado (`{<base>: {termos, valor_brl}}`,
`additionalProperties: false` sobre o enum): a base passa a ser auditável **só do
payload**, sem ler código-fonte.

### D2 — `Papel` ternário mata a causa-raiz no nível de tipo

`Papel = titular | conjuge | sem_dono`. `MemberIdentity.role_of`
(`patrimonio_types.py:175-176`) **morre**: é `"conjuge" if key == conjuge_key else
"titular"` — função **binária sobre domínio ternário**, e o `else` é o mesmo
`→ titular` de `reserva_liquidez.py:189-190` escrito uma segunda vez. Com `Papel`,
omitir o terceiro caso vira **erro de tipo em todo call-site** ([[ADR-410]] §Gate:
impossível por construção, não vigiado por gate). Custo: 3 call-sites.

### D3 — Produtor único do **eixo B**, injetado

[[ADR-410]] resolve o eixo A (baseline consolidado, `bens[]`). `_positions_for_member`
lê `investimentos_atuais["dados"]` — **eixo B**, universo distinto; migrar para
`resolve_members` produziria um terceiro significado para "membro resolvido". A
regra canônica do eixo B **já existe** (`_papel_da_chave` + `matches_member_key`);
falta **grão e injeção**.

VO frozen `CarteiraPorPapel`, por `Papel`: `total_brl` (de `total_por_membro`,
autoritativo), `posicoes`, `divergencia_item_vs_agregado`. Construído **uma vez** em
`e5_analyzer_adapter.analyze_via_store` e **injetado** em `PatrimonioInputs` e
`EmergencyReserveCalculator.calculate`. Os dois grãos coexistem porque o agregado
**não é derivável dos itens** (`investments_consolidator.py:440-457` usa `total_fonte`
e cai para `positions_sum` só na ausência) — o VO **nomeia** a divergência em vez
de escondê-la. `_positions_for_member` é **deletada**; com ela somem o ramo
`elif not membro → titular` **e** a substring de `:187`. O balde `sem_dono` **não
tem fallback IRPF** — não há pessoa a consultar.

### D4 — A órfã ENTRA em `total_liquido` da reserva

`cobertura_meses` **não se move**: mudam a decomposição e o veredito, não a
magnitude. (i) `ReservaLiquida.componentes()` (`:58-71`) tem invariante
`total_liquido == Σ componentes` exato ([[ADR-279]]); (ii) `excluido_da_reserva` só
tem balde de **não-líquido** e a fatia órfã é medidamente **mista** — jogá-la lá
recria o defeito de rótulo num terceiro lugar; (iii) excluí-la criaria uma **quinta**
base para "carteira líquida". Terceira chave `investimentos_nao_atribuidos` em
`ReservaComposicaoLiquida` — **mesmo nome do patrimônio, sem sinônimo**.

### D5 — Vocabulário: eixo separado, não pessoa-fantasma

**Rejeitado** o RV8-06 como escrito na lane ("abrir o enum
`cobertura_investimentos[].membro` + emitir terceira `CoberturaMembro`):
`investimentos_cobertura.py:144,236` faz `CoberturaStatus(linha.get("status"))` —
valor novo levanta `ValueError` em **leitor antigo lendo artefato novo**, e artefato
vive indefinidamente em `pipeline_artifacts`. Pior: `cobertura_investimentos`
particiona **pessoas** (*"este membro foi medido?"*) e a fatia órfã particiona
**dinheiro** — ortogonais. Está medido: as duas linhas estão `apurado`/`motivo: null`
**e** a maior parte da base não tem dono. E `motivo_supressao_por_cobertura` emitiria
`offending_value="membro=sem_titular"`, que lê como **nome de pessoa** na UI.

No lugar: campo irmão `patrimonio.atribuicao_investimentos`
(`{status, pct_carteira_financeira, piso_pct, motivo}`), com `status` reusando o
vocabulário já fechado de `componente_exposicao_cambial` ([[ADR-403]]):
`apurado | parcial | indeterminado`. `cobertura_investimentos[].membro` e
`CoberturaStatus` permanecem fechados.

Retenção com code **próprio**: `domain.investimento_sem_titularidade`, família de
`domain.instituicao_ausente`. **Nunca** `domain.membro_nao_apurado` — `nao_apurado`
é *ausência de medição de pessoa que existe* (fica **fora** da base);
`nao_atribuido` é *presença de medição sem etiqueta* (fica **dentro**). Confundi-los
torna a base não-reconstituível do publicado, e a remediação difere: um pede
**documento**, o outro pede **reconciliação de titularidade** ([[ADR-406]] §D3).

### D6 — Piso de materialidade: três degraus, sem inventar quarta política

1. **Ignorar em silêncio** — `< 0,5%` por item **E** `< 1%` agregado: herda
   [[ADR-406]] §D1 tal e qual.
2. **Nomear** — a partir de `1%` agregado: linha própria, componente próprio,
   `motivo` não-nulo, `base` declarada.
3. **Suprimir veredito** — **não tem piso de tamanho; tem teste de sensibilidade.**
   Cai quando recomputar sem a fatia órfã (a) muda a faixa/label **OU** (b) move o
   número mais que a menor diferença acionável da superfície (**2 p.p.** percentual,
   `SEVERITY_ALINHADO_MAX_PP`; **1 mês** reserva/autonomia; **1 ano** prazo de IF).
   O braço (b) existe porque o critério de flip é cego aqui: `avaliacao_liquidity`
   é "Excessiva" **nas duas** partições, com razão 1,73× entre elas — veredito que
   sobrevive a erro dessa ordem no próprio input não mede o que diz medir.
4. **Sem piso nenhum:** *nenhum valor sem dono sob rótulo de pessoa* — em qualquer
   magnitude, porque é afirmação sobre pessoa, não estimativa de valor.

### D7 — Vereditos suprimidos, medidas publicadas

`autonomia_financeira_meses`, `goals.if_pct`/`if_gap`, o cone `if_monte_carlo`,
prazos de `cenarios_conjuge` e `avaliacao_liquidity` passam a **suprimir veredito**
acima do piso (via `motivo_supressao_por_cobertura`), publicando medida como
intervalo `[carteira_com_titular_identificado ; carteira_financeira_familia]` — onde
o **spread é o diagnóstico**. `exposicao_cambial.tier` ganha **segunda perna**
([[ADR-403]] §D2): fatia não-atribuída acima do piso ⇒ `indeterminado`.

O manifest do parecer (`parecer_planejador.yaml:182-184`) **para de reensinar o
limiar** na label, e ganha regra pós-LLM que barra `pontos_fortes` apoiado em banda
cuja base tenha fatia órfã acima do piso.

### D8 — Sem flag de runtime

Env var que altera dinheiro publicado significa dois workers produzindo relatórios
diferentes sobre o mesmo corpus **sem o artefato registrar qual** — o híbrido sem
rótulo que [[ADR-403]] construiu `definicao_versao` para impedir. Rollout via
`base_versao` no artefato + **fronteira de série no comparador**; rollback via revert
de PR. `cobertura_enforcement_ligado()` é reusado **apenas** onde já governa
(review_reason e retenção).

### D9 — Ordem de PRs: permissivo → produtor → obrigatório

Derivada de dois mecanismos opostos: `additionalProperties: false` exige **schema
permissivo antes do produtor**; `required` + `MATHOMS_PIPELINE_SCHEMA_MODE=strict`
na suíte (`tests/conftest.py:29`) exige **`required` depois**.

| PR | Conteúdo | Move número? |
|---|---|---|
| **PR0** | esta ADR | não |
| **PR1** | `BaseFinanceira`, `Papel`, `$defs`, chaves **opcionais**, `additionalProperties` afrouxado | **não** |
| **PR2** | **núcleo**: `CarteiraPorPapel` injetado; morte de `_positions_for_member` e `role_of`; restauração do termo; `patrimonio.bases`; `exposicao_cambial_v2.py:286` no mesmo PR | **sim** |
| **PR3** | `atribuicao_investimentos`, code de retenção, piso, supressões, intervalos | sim (retenção) |
| **PR4** | `required` + `kpi_targets[].base` estreitado ao enum + gates | não |
| **PR5** | manifest do parecer + `PROMPT_VERSION` + regra pós-LLM + donut + `HeroKpiGrid`/`WaterfallIfChart` + DTO/OpenAPI | prosa/UI |

`exposicao_cambial_v2.py:286` **não é efeito colateral**: é segundo produtor do mesmo
pct em read-time; corrigir só o E5 instala divergência card↔relatório. **Rejeitado**
o andaime "política de inclusão legada por consumidor" para tornar PR1 número-neutro
— é "manter os dois com contrato escrito" disfarçado. A atribuibilidade vem de graça
do D4: como a re-atribuição na reserva **não move Σ**, o único produtor de delta no
PR2 é a restauração do termo.

## Consequências

**O critério de Corretude escrito na lane já passa hoje, sobre o defeito.** A
identidade de Σ fecha em **0,00%** no run defeituoso — fecha **porque** a órfã foi
absorvida sob rótulo de membro (excedente líquido no balde titular `40,4 p.p.` +
`excluido_da_reserva.investimentos_nao_liquidos` `20,6 p.p.` = `61,0 p.p.`, a fatia
órfã exata). É gate de soma contra defeito que preserva soma por construção. O
predicado que discrimina é **partição por item**: nenhum componente rotulado por
papel contém item cuja chave não case aquele papel por `matches_member_key`.

**O critério de Completude escrito na lane fecha só instância.** "Enumerar os
consumidores de `investivel_financeiro`" tem três fugas medidas: `investivel_efetivo`
(`:219`, hub do bloco IF inteiro), parâmetro renomeado
(`if_projector.project(investivel=...)`) e denominador **remontado dos termos sem
citar o nome** (`e5_analyzer_adapter.py:775-783`, `exposicao_cambial_v2.py:286`).
**Não enumere leitores — enumere números publicados.**

Gates que fecham **classe**: injeção obrigatória de `base` keyword-only sem default;
`Papel` ternário sob type-check; cobertura de base no payload (toda razão publicada
reproduz ao recomputar numerador ÷ base declarada, em cents); coerência entre
superfícies que declaram a mesma base; mutação bilateral (reverter o ramo deixa
vermelho o teste da reserva **e** o do patrimônio); e o rider que faz
`check_member_key_substring.py` classificar pela **origem do valor**, não pelo nome
da variável.

**Movimento esperado, não regressão** (declarar no PR **antes** de medir): concentração
`66,79% → 50,62%` (−16,17 p.p.); `pct_investivel_financeiro` `12,55% → 6,40%`;
autonomia e o bloco IF movem mais que a concentração; o score se move sem bump de
`score_version` (refinamento de input, não de fórmula) mas **com** marcador em campo
— score que sobe porque o denominador foi consertado não é a família melhorando.
`dev/compare_reviews.py` ganha fronteira de série por `base_versao`; **rejeitado**
supressor amplo ("base mudou → ignore tudo"), que troca falso-vermelho por
**falso-verde permanente**.

**Riscos aceitos.** O r9 sai com vários vereditos suprimidos — não é relatório
degradado, é o primeiro que diz a manchete verdadeira desta família ([[ADR-406]] §D4
é o precedente de aceitar isso). O PR3 **retém o run do dogfood por desenho**;
declarar no corpo do PR, senão o próximo agente lê retenção como falha. Perde-se o
kill-switch instantâneo em prod — mitigação é revert de PR, honesta porque flip de
flag produziria run cujos números não batem com baseline de versão nenhuma.

**Dívida vizinha que esta ADR não abre:** no run medido o balde do cônjuge vem de
fallback IRPF (frescor 2023) enquanto o do titular vem de posições atuais (2025) — a
base canônica mistura fontes de frescor distinto. Fica como §Deferido datado na lane.

## Alternativas rejeitadas

- **Trocar `member_key in membro` por `matches_member_key` como o fix.** Medido:
  com `membro == ""` a substring é `False` para qualquer chave não-vazia; **100% do
  excedente vem do ramo `:189-190`**. Seria fix mal-mirado com gate verde por cima.
  A substring morre como **consequência** da deleção, não como correção.
- **Abrir `cobertura_investimentos[].membro`/`CoberturaStatus`** — quebra dura de
  leitor e publica pessoa que não existe (D5).
- **Transformar razão escalar em objeto `{valor, base}`** — é funil de tipo e quebra
  codegen TS, charts, manifest e snapshot de uma vez. A regra do repo é aditivo com
  escrita obrigatória e leitura tolerante; sidecar satisfaz, funil não.
- **Publicar duas leituras do mesmo conceito como KPIs irmãos** — a família escolhe
  a maior e o relatório terá ensinado a escolher. Intervalo declarado, onde o spread
  é o diagnóstico, é outra coisa.
- **Excluir a órfã do total da reserva** — subdeclara fôlego por defeito de dado; o
  número menor não é mais verdadeiro, só mais assustador.
- **Veredito com caveat textual** — não sobrevive à sumarização do parecer
  ([[ADR-335]] §Alternativas); este run acabou de demonstrar de novo, com o parecer
  republicando "faixa verde" apesar de `tier: indeterminado` no campo.
- **Recalibrar bandas para absorver a mudança de base** ([[ADR-403]] §D6) — seria
  calibrar o instrumento para não ver o efeito da correção.
- **Allowlistar `reserva_liquidez.py:187` no gate** — fecha instância e mantém a
  cegueira estrutural; o próximo parâmetro se chama `chave` ou `mk`.
