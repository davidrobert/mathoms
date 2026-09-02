---
id: ADR-412
type: adr
title: "Base canônica única para carteira financeira, `Papel` ternário e produtor único do eixo de posições atuais"
status: Decidido
phase: A40.l80
date: "2026-08-25"
amended_at: ["2026-08-25", "2026-08-28", "2026-09-01"]
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
  - status/decidido
  - area/pipeline
  - area/financial-planning
  - area/report
---

# ADR-412 — Base canônica única para carteira financeira, `Papel` ternário e produtor único do eixo de posições atuais

> **Emendada 2026-08-25** (co-design `senior-cto` + `financial-planner`): a **D5
> perde a retenção** — a razão nasce advisory; a **D6(b) troca de régua**; a **D7
> ganha objeto explícito** (suprime veredito e prescrição, nunca a medida); a **D8
> ganha obrigação recíproca** para superfície read-time.
>
> **Emenda 7 (2026-09-01):** a §E3 apoiava-se em `neutralize_autocontradicao` para NÃO
> suprimir `avaliacao_liquidity`. Medido: aquela perna estava **inerte** — o guardrail
> casava por `section_id` literal e disparou em **0 de 14 runs** pós-#1800. A decisão
> **fica**, sustentada pela perna independente do `HeroKpiGrid`. Ver §E13.

> **Emenda 6 (2026-08-28):** o §Escopo do flip listava como fora-de-escopo **três** itens
> que PRs posteriores da própria lane fecharam em horas — lista de escopo é snapshot, e
> esta envelheceu no mesmo dia. Ver §E12.
>
> **Emenda 5 (2026-08-28):** a §D8 mandava a superfície read-time **ler** o marcador de
> série e degradar — e não proibiu **recomputar** o número que o marcador rotula. Foi por
> esse vão que o card cambial publicou 2,0% contra os 12,0% do produtor. Ver §E10.
>
> **`Decidido` em 2026-08-28**, com **§Escopo do flip** declarando em lista fechada o que
> esta decisão cobre e o que **não** cobre. As duas emendas que o cabeçalho exigia foram
> escritas ([[ADR-335]] §Emenda 2, [[ADR-394]] §Emenda 2026-08-28). A lane continua `open`:
> o que falta é dívida de **prova**, e prova mora no §Critério de aceite dela, não aqui.
>
> **Emenda 4 (2026-08-28):** a §E5 mede "interseção vazia" entre `BaseFinanceira` e
> `kpi_targets[].base`. **Refutado** — o #1782 criou a colisão. Ver §E11.
>
> **Emenda 3 (2026-08-28):** a tabela da **§D1 descrevia 3 dos 6 membros** do enum —
> faltavam `carteira_produtiva_com_titular_identificado` (#1710) e
> `carteira_produtiva_fixa` (#1782), e ela ainda listava `despesa_essencial_domicilio`,
> que a §E6 removeu. Ver §E9.
>
> **Emenda 2, mesmo dia** (medido no PR1 #1710): a **§D9 mandava afrouxar o que a
> §D1 manda fechar**; `despesa_essencial_domicilio` **sai** do enum; e o enum
> **não** trava sozinho a omissão do terceiro caso. Ver as duas §Emenda no fim.

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
| **PR1** | `BaseFinanceira`, `PapelMembro`, `$defs`, chaves **opcionais**, `additionalProperties` **mantido** (ver §Emenda E5) | **não** |
| **PR2** | **núcleo**: `CarteiraPorPapel` injetado; morte de `_positions_for_member` e `role_of`; restauração do termo; `patrimonio.bases`; `exposicao_cambial_v2.py:286` no mesmo PR | **sim** |
| **PR3** | `atribuicao_investimentos`, code de retenção, piso, supressões, intervalos | sim (retenção) |
| **PR4** | `required` + gates; `kpi_targets[].base` **não** estreita ao enum (§Emenda E5) | não |
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

## Emenda — co-design `senior-cto` + `financial-planner` (2026-08-25)

Duas premissas do texto original caíram na verificação, e o repo mudou **embaixo
da ADR** entre a redação e o merge.

### E1 — a retenção sai da D5: a razão nasce **advisory**

O texto original manda emitir `domain.investimento_sem_titularidade` como razão de
**retenção**, e o §Riscos aceita "o PR3 retém o run do dogfood por desenho". As duas
frases **contradizem a D7**, e o mecanismo é duro:

- `scripts/analyze_finances.py:2001` — `"valid": not reasons`. **Qualquer** razão do
  E5 retém, independente de `BLOCKING_CODES`. O E5 é produtor divergente de política
  de pausa e não está caracterizado em `tests/unit/pipeline/test_validation_block_policy.py`.
- `backend/app/tasks/pipeline_task.py:1797-1798` — `if paused_for_review: return`,
  antes de `_finalize_run` e `_run_post_processing`. Run retido **não cria row em
  `reports`**, e pausar em `analyze_finances` mata `generate_narratives`,
  `validate_cross` e `review_finances_holistic` — os três artefatos que o r9 lê.

Logo o PR3, como escrito, **torna a D7 inalcançável exatamente no run que a motivou**:
o intervalo não é renderizado, a supressão não é vista, o parecer não roda. E a
"Prova de fecho" da [[A40.l80]] (nenhum `pontos_fortes` apoiado em banda com fatia
órfã) fica **inverificável por construção**.

**O argumento que sustentava a retenção venceu há dois commits.** [[ADR-406]] §D4
retinha porque advisory seria *inerte* — *"`record_review_reasons` só roda quando
`validation.valid` é falso"*. Desde `954f892f` ([[ADR-411]], A40.l81, mergeada
2026-08-25), `pipeline_task.py:1331` chama `_record_stage_diagnostics` na **última
linha do caminho de sucesso**, em run `completed`. O canal advisory existe.

**Decisão:** a razão vai para coleção irmã no `detail`, **fora de
`validation.review_reasons`**; `harvest_review_reasons` a colhe e persiste no
desfecho `completed`. O `locator` distingue as classes — **não** invente campo
`severity`. A retenção **sai do PR3**. Quem quiser retenção abre PR6 depois do r9
medido, e aí é o DE-3 decidindo a política de pausa do E5 inteira.

**Follow-up obrigatório:** emenda datada em [[ADR-406]] §D4 — o rationale está
factualmente vencido, e sem a emenda a próxima lane reinstala retenção pelo mesmo
argumento morto. E caracterize o E5 em `test_validation_block_policy.py`: é o
produtor divergente que ninguém cobre.

### E2 — a D8 fica, mas ganha obrigação recíproca

Mantida **sem flag de runtime**. A premissa "multi-tenant, o PR2 move todos os
workspaces de uma vez" que motivava reabrir a D8 é **falsa hoje**:
`docs/reference/RUNBOOK.md:118` — *"Pré-produção, Mathoms roda single-tenant"*.
Kill-switch instantâneo contém dano a usuário em produção; não há usuário. E flag
na base poria `os.environ` dentro do cálculo de um domain service, contra
CLAUDE.md §Dependências e contra a [[ADR-089]]/[[ADR-097]] D2 que a própria D3 invoca.

**O buraco real da D8 não era a falta de flag — é a superfície read-time.**
`backend/app/application/exposicao_cambial_v2.py:53-60` tem `_tier_from_pct`
**sem a perna `indeterminado`** que o E5 tem em `exposicao_cambial_analyzer.py:133-136`.
O card **já hoje** publica veredito de faixa que o E5 recusa, na mesma tela. Flag
nenhuma consertaria: ela recomporia artefato antigo com código novo — o híbrido sem
rótulo que a D8 diz evitar.

**Acrescente à D8:** *superfície read-time que consome base canônica lê
`patrimonio.bases`/`base_versao` do artefato e degrada para `indeterminado` quando a
série é anterior à corrente.* E `_tier_from_pct` do card **entra no PR2** junto de
`:286`. Gate que fecha classe: enumerar **produtores de tier de exposição cambial** e
falhar se algum não tiver a perna de supressão — enumerar leitores de
`investivel_financeiro` não pega este, porque ele lê a chave, não a função.

### E3 — a D7 ganha objeto: suprime-se veredito e **prescrição dimensionada**, nunca a medida

Correção de premissa: **25,4 meses não é "o número correto"** — é o **extremo
inferior** de um intervalo. A D0 rejeita trocar de denominador e a D4 mantém a fatia
dentro de `total_liquido`; o par é *medida = base cheia declarada / avaliação =
extremo conservador*.

**Regra geral** (substitui as supressões ad-hoc): medida publicada como intervalo
declarado; **veredito avaliado no extremo conservador em relação à ação que ele
autoriza**; prescrição dimensionada suprimida quando o spread cruza o degrau
acionável (E4). Reserva ("realocar", reduz liquidez) e autonomia → extremo inferior;
prazo de IF → o prazo mais longo; exposição cambial ("protegido") → pct menor.

**O cone de IF NÃO é suprimido** — é desenhado no extremo conservador e rotulado
como piso. Errar para "vai demorar mais" faz poupar mais; suprimir o cone custa o
artefato mais mobilizador do relatório sem ganho de honestidade.

**A prosa morre no produtor, não em regra pós-LLM.**
`pipeline/domain/services/pontos_fortes_analyzer.py:178-181` escreve
`f"Cobertura de {cobertura:.0f} meses, acima do alvo de {meses_alvo:.0f} meses — o
excedente pode ser realocado"`. É texto determinístico já pronto: regra pós-LLM não
o alcança. E `parecer_planejador.yaml:299-301` projeta `$.reserva_emergencia` inteiro
em `format: raw` — campo `motivo_supressao` ao lado seria inerte, que é `tier:
indeterminado` outra vez. **Número suprimido sai da projeção**, e **legenda de limiar
nunca acompanha número suprimido**.

**Piso de utilidade — regra de composição, não limiar:** com **≥3 vereditos
suprimidos pela mesma causa**, o relatório promove a causa a **manchete única com
tarefa única** na capa, e para de repetir ressalva por card. Cinco ressalvas
espalhadas ensinam que *o relatório está quebrado*; uma manchete ensina que *falta um
dado da família*. É isto — e não a pausa do E5 — que entrega "pedir o dado antes":
o relatório existe e carrega o pedido.

Permanecem **íntegros e sem ressalva** (dependem só do denominador, não contaminado):
`custo_essencial_mensal`, `meses_alvo`, `alvo_brl`, `nivel_6_meses`/`nivel_12_meses`.
Suprimi-los junto seria supressão por atacado.

### E4 — a D6(b) troca de régua: **meses da quantidade acionável**

O braço (b) original ("1 mês em reserva/autonomia") dispara sempre a 44 meses de
cobertura — gate que sempre dispara é gate morto. E o critério de flip de rótulo é
**cego por construção em faixa aberta**: `"Excessiva"` não tem teto
(`config/scoring.json:124`, `minimo_meses: 24`), logo nenhum erro flipa nada acima
de 24 meses — a mesma cegueira estrutural que deixou `check_member_key_substring.py`
verde por 7 semanas.

A régua passa a medir **o que vira ação**: excedente sobre o alvo (piso **6 meses**,
um degrau de `niveis_meses`, constante que o relatório já publica) ou déficit até o
alvo (piso **1 mês**, onde o original estava certo). Materialidade **automática**
quando o intervalo cruza o alvo.

**Medido no run:** o erro na cobertura é 1,73×, mas o erro na **quantidade acionável**
é **3,50×** (excedente 25,9 vs 7,4 meses) — subtrair o alvo amplifica. E a folga sobre
o corte cai de **83% para 5,8%**: o rótulo é invariante, mas a redundância que o
sustenta cai pela metade (a 25,4 o segundo braço `cobertura >= meses_alvo * 2` **não**
dispara, e é correto que não dispare). Spread de 18,5 meses = **3 degraus** ⇒ suprime
a prescrição com folga. O rótulo qualitativo **permanece** (invariante nos dois
extremos, e o custo de oportunidade de reserva grande demais é real — calar
completamente também erraria).

**Dívida adjacente descoberta, não resolvida aqui:** `config/methodology.md:216-217`
condiciona "realocar excedente" a **duas** condições — excedente material **E** desvio
de alocação acima de `desvio_max_pct`. A segunda **não está implementada**
(`pontos_fortes_analyzer.py:173` dispara só com `excessiva`). O produto prescreve
rebalanceamento por aporte sem checar a condição de desvio que ele mesmo escreveu.
§Deferido datado com dono.


## Emenda 2 — o que o PR1 mediu e a §D9 errava (2026-08-25)

### E5 — a §D9 mandava afrouxar o que a §D1 manda fechar

O PR1 (#1710) **declarou** as chaves novas e **manteve** `additionalProperties: false`.
A §D9 pedia o contrário, e afrouxar seria regressão — é a guarda que sustenta os
dois melhores gates do PR (mutação: afrouxar `bases` ou remover o `enum` de
`status` deixa exatamente 2 testes vermelhos).

Medido: `properties.patrimonio` **não declara** `additionalProperties` (= `true`),
logo `bases` e `atribuicao_investimentos` **já eram aceitos** antes do PR —
declará-los não afrouxou nada, e `bases` chega **fechado** nas chaves do enum,
região **mais restritiva** que o status quo. O único afrouxamento real foi
`investimentos_nao_atribuidos` em `$defs.ReservaComposicaoLiquida`. A §D1 sempre
disse `additionalProperties: false` sobre o enum; **a §D9 é que estava errada**.

Consequências que corrigem a tabela: `atribuicao_investimentos` **antecipou-se do
PR3 para o PR1** (schema-only, número-neutro); e `kpi_targets[].base` **não pode
ser "estreitado ao enum" no PR4** — os dois vocabulários são **disjuntos**
(interseção medida: vazia). `BaseFinanceira` cobre o **eixo de posições**;
`kpi_targets[].base` nomeia denominadores de outra natureza
(`patrimonio_bruto`, `renda_anual_ativa`, `receita_recorrente`…), a maioria sem
membro representável. Unificar exigiria mover campo `required` e publicado — fora
do contrato número-neutro. Registrar a disjunção é a decisão; convergir, não.

### E6 — `despesa_essencial_domicilio` sai do enum

A tabela da §D1 a listava entre as bases "já existentes". Medido, ela descreve
**dois denominadores diferentes**: a reserva cai para `despesa_mensal_media` no
fallback (`base_denominador="despesa_total"`, `custo_essencial=0`,
`reserva_emergencia_calculator.py:310-316`) e a autonomia divide por
`despesa_consumo_brl / n_meses` (ex-aporte, [[ADR-333]],
`ratios_calculator.py:285-288`). Declarar um termo só seria afirmação falsa.

Isso expõe um vão na §D0: ela agrupou reserva e autonomia como "domiciliares"
**sem medir** que não compartilham denominador. **§Deferido datado (2026-08-25):**
decidir se são uma base com fallback declarado ou duas bases distintas — dono da
[[A40.l80]], condição de retomada: antes de qualquer superfície declarar
`base` para reserva ou autonomia.

### E7 — o enum não trava a omissão do terceiro caso sozinho

A §D2 dizia que `Papel` faz "omitir o terceiro caso virar erro de tipo em todo
call-site". **Falso neste repo:** não há `mypy` nem `pyright` em pre-commit ou CI,
e o mixin `str` mantém `PapelMembro.titular == "titular"` verdadeiro — um
`if/else` binário segue funcionando calado depois da migração. Quem trava é o
**teste de exaustividade sobre `set(PapelMembro)`**, que o PR2 traz junto com a
morte de `role_of`. O enum é condição necessária, não suficiente.

Corolário para o PR2: `reserva_liquidez.py:62` e `patrimonio_types.inv_key`
montam a chave por f-string sobre o papel; com enum isso vira
`investimentos_PapelMembro.sem_dono`. O PR1 já entregou `chave_de_componente`
para isso — **use o mapa, nunca a f-string**.

### E8 — tripwire nomeado

`tests/test_bases_financeiras_contrato.py::test_tripwire_role_of_ainda_e_binaria_ate_o_pr2`
fica **vermelho** quando o PR2 aplica o fix da §D2. A ação correta é **deletar o
teste junto com `role_of`** — nunca relaxar o assert.

## Emenda 3 — a tabela da §D1 não descrevia o enum que shipou (2026-08-28)

### E9 — o enum tem SEIS membros; a §D1 lista três certos

A tabela da §D1 é a descrição canônica de `BaseFinanceira`, e divergiu do código em
três pontos ao mesmo tempo — dois por omissão de base que shipou, um por listar base
que a própria ADR removeu:

| membro (código, 2026-08-28) | na tabela §D1? |
|---|---|
| `carteira_financeira_familia` | ✅ |
| `carteira_produtiva_familia` | ✅ |
| `carteira_com_titular_identificado` | ✅ |
| `carteira_produtiva_com_titular_identificado` | ❌ **ausente** — shipou no PR1 (#1710) |
| `carteira_produtiva_fixa` | ❌ **ausente** — shipou no PR4 (#1782) |
| `patrimonio_liquido` | ✅ |
| `despesa_essencial_domicilio` | ⚠️ **listada e inexistente** — a §E6 a removeu |

`carteira_produtiva_fixa` = `carteira_financeira_familia + imoveis_investimento`. Ela
existe porque o denominador da concentração imobiliária ([[ADR-340]]) **não é** a
`carteira_produtiva_familia`: aquela soma `cat2_efetivo`, que conta só imóveis
**geradores** e zera com `include_real_estate_in_if` off, enquanto a concentração usa
cat_2 **completo** e é toggle-independente por decisão. Medido no dogfood: **73.000.000
contra 13.000.000**, 5,6× — dois denominadores sob o mesmo nome "carteira produtiva".
Publicá-la é número-neutro; o gate `tests/test_cobertura_de_base.py` recompõe
`numerador ÷ base declarada` em cents e a exige.

**Por que a divergência sobreviveu a 12 PRs:** a paridade enum↔schema É gateada
(`test_chaves_de_bases_no_schema_sao_exatamente_o_enum`), mas a paridade **enum↔ADR**
não é gateada por nada — tabela em prosa não tem detector. Base nova toca três lugares
enforçados (enum, `TERMOS_DA_BASE`, schema) e um não-enforçado (esta tabela), e é o
não-enforçado que envelhece calado.

## Escopo do flip para `Decidido` (2026-08-28)

`status` é propriedade da **decisão**, não do grau de enforcement da implementação. Treze
PRs mergeados — dois deles movendo dinheiro — são a evidência de que a decisão foi tomada.
Manter `Proposto` dava cobertura retórica para reabrir a §D0 ou a §D4 alegando
provisoriedade, e isso **já aconteceu**: a §Consequências refutou por escrito a formulação
da §Completude e ela foi **reinscrita dois dias depois** (`a28055a7`, #1758).

**Cobre:** D0–D9 conforme emendadas, incluindo `carteira_produtiva_fixa` (§E9) e a
disjunção corrigida (§E11).

**NÃO cobre** — cada item com dono, e nenhum deles é dúvida sobre esta decisão:

| fora do escopo | dono |
|---|---|
| razão fabricada em consumidor TS (`WaterfallIfChart` re-deriva `if_pct` suprimido; `HeroKpiGrid` inventa razão sobre 5ª base) | [[A40.l80]] + gate em `check_view_model_contract.py` |
| `kpi_targets[].base` deixar de ser `type: string` — como **par discriminado** `{eixo, membro}`, nunca enum plano | **sem dono vivo**: a [[A40.l89]] arquivou (`shipped`) — ver §E12 |
| ~~o numerador cambial em disputa entre E5 e card read-time~~ | **FECHADO no #1794** — ver §E12 |
| §Deferimento §E6 (reserva × autonomia são duas bases distintas — a medição do C14 já respondeu) | [[A40.l80]] |
| cone de Monte Carlo (§Deferido datado 2026-08-26) | [[A40.l80]] |
| ~~`BASE_VERSAO_CORRENTE` nunca bumpado~~ | **FECHADO no #1799** — ver §E12 |

## Emenda 4 — a disjunção da §E5 não existe mais (2026-08-28)

### E11 — o #1782 criou a colisão que a §E5 media como impossível

A §E5 decidiu **não convergir** `BaseFinanceira` e `kpi_targets[].base`, e sustentou a
decisão numa medição: *"interseção medida: vazia"*. **A decisão continua certa; a medição
não.** Ao criar `carteira_produtiva_fixa` (§E9) para desambiguar o denominador da
concentração, o #1782 deixou o catálogo declarando `"carteira_produtiva"` — string que
**não é membro do enum**, cujo vizinho mais próximo vale **5,6× menos** — para o **mesmo**
`observado_path` que o produtor passou a declarar corretamente. Duas declarações
divergentes do mesmo número, no mesmo payload. Corrigido no #1788, com gate que compara as
duas superfícies derivando o par pela convenção do produtor.

**O que isso ensina sobre a §E5, e é o que fica:** os eixos são legítimos e não devem
fundir — `carteira_financeira ÷ despesa` não é comparável a `renda_alvo_bruta`. Mas
`kpi_targets[].base` **não é um quarto eixo**: é uma união **não-tipada** de quatro
(posições, meta de IF, despesa, renda) mais uma entrada que nem base é (`cone_monte_carlo`
é procedência ocupando o campo de denominador). Fechá-lo "num enum próprio" **cunharia** o
quarto vocabulário que a §E5 temia. A forma correta é par discriminado `{eixo, membro}`,
validado contra o enum daquele eixo — e o dono é quem tem a janela de rebaseline do
catálogo, a [[A40.l89]].

**E o que impede um quinto aparecer, hoje: nada.** O payload já carrega dez campos de base
em três vocabulários. O detector correspondente — todo campo cujo nome case
`^base($|_)|_base$` tem `enum`/`$ref` ou consta de allowlist com o eixo nomeado — é lane
nova, dono `data-engineer`. É o mesmo mecanismo que a §E9 já nomeou: *base nova toca três
lugares enforçados e um não-enforçado, e é o não-enforçado que envelhece calado.*

## Emenda 5 — o vão da §D8: ler o marcador não basta (2026-08-28)

### E10 — superfície read-time só recomputa a perna que tem input read-time

A §D8 construiu `base_versao` para impedir "híbrido sem rótulo" e mandou a superfície
read-time **ler** o marcador e degradar. `exposicao_cambial_v2.py` fazia isso — e
**recomputava o numerador ao mesmo tempo**, que é o híbrido com aparência de rotulado: o
marcador rotula a computação do **produtor**, e a superfície o colava na sua própria.

**Medido:** o E5 publicava **12,0%** e o card **2,0%** para a mesma família, no mesmo badge.
O card filtrava a perna de caixa por `moeda != "BRL"`, usando como classificador de
exposição o campo que a [[ADR-245]] §L3 decidiu ser **unidade de medida** — a linha
`moeda_estrangeira_irpf` nasce em BRL porque o saldo já vem convertido.

O erro não é "conservador": a linha continua no **denominador** de todas as bases, então
`(N−x)/D` fica **estritamente abaixo** das duas leituras coerentes. E o custo é de conselho —
dizer "você tem 2%" empurra **compra** de moeda forte (IOF, spread, evento tributário) para
uma família que já tem 12%.

**A regra:** superfície read-time **só recomputa a perna que tem input read-time**; toda
outra ela **consome** do artefato. Corolário: importar o predicado do produtor **não basta**
quando o produtor é predicado **+ inferência** — aqui, importar só `_is_caixa_me` faria 83%
da exposição sair rotulada `BRL` no `por_moeda`.

**Consequência para a [[ADR-403]] §D1:** o bloco `componentes`/`por_moeda` deixa de ser
apenas evidência publicada e passa a ser **contrato consumido** por uma segunda superfície.
Mudança de blast radius, registrada por emenda de uma linha lá.

**O que esta emenda NÃO fecha, e tem dono:** a perna de posições do card é **código morto** —
`_posicoes_do_payload` lê `investimentos["dados"]`, chave que o schema de `investimentos` não
tem, então ela devolve `[]` sempre. Hoje é inofensiva; vira híbrido no dia em que a fonte for
ligada ([[ADR-224]] §5). Dono: `data-engineer`.

## Emenda 6 — o §Escopo do flip envelheceu no mesmo dia (2026-08-28)

### E12 — lista de escopo é snapshot, e três das seis linhas caíram em horas

O §Escopo do flip (2026-08-28) declarou em lista fechada o que esta decisão **não** cobre.
Foi o instrumento certo — e envelheceu no mesmo ciclo, porque PRs da própria [[A40.l80]]
fecharam três dos itens listados:

| linha do §Escopo | o que aconteceu |
|---|---|
| numerador cambial em disputa (12,0% × 2,0%) | **fechado no #1794**: o card passou a CONSUMIR o `por_moeda` do artefato — a regra da §E10 |
| `BASE_VERSAO_CORRENTE` nunca bumpado | **fechado no #1799**, e **não por bump**: `bases_reproduzem` degrada sobre o defeito, e o congelamento de `TERMOS_DA_BASE` exige bump só em base existente |
| dono de `kpi_targets[].base` = [[A40.l89]] | a l89 **arquivou** (`shipped`, `ship_pr: 1779`). O item continua aberto e agora **sem dono vivo** |

Correção de ponteiro no mesmo ato: a linha do `BASE_VERSAO_CORRENTE` dizia *"ver §E11"*, e
a §E11 é sobre a disjunção de vocabulários — **zero menções** a `base_versao`. Ponteiro
para seção que não trata do assunto é pior que ponteiro ausente: quem segue conclui que leu.

**A lição, e é por que esta emenda existe em vez de uma edição silenciosa:** a lista de
escopo é mais forte que "vibe" (era esse o argumento do flip) e mais frágil que invariante —
ela é **datada e precisa de releitura a cada PR da lane que a cita**. Um item que fecha não
some da lista; ele é riscado com o PR que o fechou, senão o próximo leitor herda um mapa de
trabalho que já foi feito. Mesma família do que o §"Agravante de processo" desta ADR já
registrou sobre o #1758 reinscrever a formulação refutada.

## Emenda 7 — a §E3 citava um mecanismo que não rodava (2026-09-01)

### E13 — a perna do guardrail estava inerte; a decisão sobrevive pela outra

A §E3 e os dois comentários que a citam em código
(`reserva_emergencia_calculator.py:241-243`, `supressao_por_atribuicao.py:5-7`)
justificavam manter `avaliacao_liquidity` publicado com **duas** pernas: suprimi-lo faria
`HeroKpiGrid.reservaQuality` re-derivar "excelente" por fallback local **e** desarmaria
`neutralize_autocontradicao`.

**A segunda perna era falsa quando foi escrita.** A [[A40.l116]] mediu 14 runs do mesmo
corpus, com `temperature=0`: o guardrail casava o ponto forte por `section_id` contra um
literal, e o modelo rotula o item de liquidez com **S3 em 9 runs e S4 em 5** — nunca com o
`S1` que o #1800 fixou. `autocontradicao_removidos` saiu **0 nos 5 runs** posteriores àquele
PR — nos anteriores a chave de telemetria nem existia, e o único disparo medido (`1`, em
2026-08-24) foi com a constante ainda em `S4`. Um mecanismo que não dispara não pode ser
desarmado, então ele não pesava nada no argumento.

**A decisão de não suprimir `avaliacao_liquidity` fica de pé** — a perna do `HeroKpiGrid`
é independente, foi medida na própria [[A40.l80]] e não depende do guardrail. O que cai é
a *justificativa dupla*: a §E3 alegava dois apoios e tinha um.

A partir da [[A40.l116]] a segunda perna passa a **existir**: o guardrail casa por
`tema_canonico` e o sinal do E5 arbitra, sem literal de seção no caminho. O argumento da
§E3 volta a ter os dois apoios que sempre afirmou ter — mas por conserto, não por acerto
retroativo. **O registro datado da [[A40.l80]] não se reescreve**: ele é evidência do que
se acreditava então.
