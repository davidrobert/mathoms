---
id: MOC-sprint-a42
type: moc
title: "Sprint A42 — Provabilidade da ingestão e do razão: fechar o falso-verde do instrumento"
aliases: ["A42", "Sprint A42"]
sprint_status: candidate
date: "2026-08-04"
theme: "ingest-ledger-trust"
---

# Sprint A42 — Provabilidade da ingestão e do razão (2026-08-04)

> **Origem:** três certificações do mesmo workspace dogfood em 2026-08-04 —
> [[PARSE-CERTIFY-active]] §r2 (ingestão E0→E2, 9 abertos + PC07 do r1),
> [[LEDGER-CERTIFY-active]] §r4 (razão E3/E4, 10 abertos) e
> [[PIPELINE-REVIEWS-active]] §r4 (run completo + relatório, 74 achados).
> Skills [[ADR-302]]; disciplina de estado durável [[ADR-343]].

> **Sucessora declarada da [[A39]]** (mesma tese `ingest-trust`). A A39 executou 12 de
> 13 lanes e nunca foi fechada; esta sprint abre **no mesmo PR** que a flipa para
> `done`, com disposição item a item — ver §Relação com a A39.

## Tese

**O corpus não regrediu em dado; regrediu em capacidade de provar que o dado está
certo.** As três certificações convergem no mesmo achado estrutural: os
instrumentos que deveriam denunciar perda passaram a dar verde sem medir.

Três formas do mesmo defeito, uma por camada:

- **Ingestão** — o gate de conservação de um parser foi suprimido por uma
  *conclusão que o próprio parser emite*, e 29% do corpus está em caminho
  line-oriented sem nenhuma âncora de fidelidade.
- **Razão** — a skill de certificação carimbou `coberto` sobre a dimensão que
  carrega 62,5% do peso do score, e nunca exercitou a P0 nº 1 da própria rubrica
  em quatro rodadas.
- **Execução** — um check que não consegue avaliar **evapora** da conta em vez de
  aparecer como `skipped`, e a perna de volume do gate anti-regressão está morta.

Nenhum desses é bug de cálculo. Todos são **instrumento mentindo**, que é o defeito
que precede e esconde todos os outros — daí a Onda 1 ser instrumento, não fix.

> ### O `ledger-certify` r5 do rito de abertura **já rodou** — 2026-08-26
>
> A rodada unificada **U1** ([[ADR-416]]) executou o `ledger-certify` em modo entregue sobre
> um run real: [[LEDGER-CERTIFY-active]] §r5. **O r5 que esta sprint exige antes do primeiro
> pickup existe**, e o achado que ele produziu é insumo do rito, não a 13ª lane.
>
> **`LC5-01` (Crítico) carimba duas lanes:**
>
> - **[[A42.l5]]** — `sobrevive`, com escopo estreitado. Continua dona da chave de artefato
>   *period-free*; **deixa de ser** a lane que fecha a classe cross-documento.
> - **[[A42.l10]]** — `sobrevive`, com a atribuição de fecho **falsificada** (ver o bloco
>   datado lá). A leitura *"amplifica, não causa"* segue de pé.
>
> **O que o r5 mediu e nenhuma lane cobria:** colapsador e detector derivam `direction` de
> funções distintas, e o residual do numerador da KR-B da [[A40]] é **100% ponto cego do
> remediador** — rodar o colapsador até convergir não move o número. O alvo do fix deixa de
> ser whitelist e passa a ser **paridade de chave**.
>
> **Consequência para a [[A40]], owner-gated:** a KR-B é medida no modo entregue e, com o
> ponto cego, a métrica literal **tem piso** e não fecha. As duas saídas honestas são
> declarar a KR-B com o ponto cego nomeado e classificado como *explicado*, roteando o fix
> para cá; ou declarar a KR-B não atingida. O fix **não** é saída dentro da A40 — mutaria E3
> e zeraria o contador de re-runs, que é o caso adversarial que esta sprint codifica.
>
> A ampliação de escopo da [[A42.l3]] (itens 6–9) veio da mesma rodada e está registrada lá.

## Por que esta sprint existe (e não é lane da A40)

O `_README` da [[A40]] §Fora do sprint declara os achados de E0→E2 explicitamente
**fora dela por camada** ("pertence a `PLAN-data-lineage` ou a uma rodada de
`parse-certify`. Não roteado."). Há um handoff escrito e sem dono. A42 o absorve.

O corte é por **camada**, não por severidade: entra o que é ingestão (E0→E2),
razão (E3/E4), contrato de store/artefato, ou instrumento de certificação. Fora
dessas quatro não entra — ainda que seja P0. Ver §Critério de admissão.

**A fusão foi avaliada de novo em 2026-08-05, a pedido do dono, e recusada — com um
motivo mecânico que a versão original desta seção não tinha.** O argumento anterior era
de camada e de handoff sem dono; ele continua válido, mas não é o decisivo. O decisivo
é que **os dois gates de saída são adversariais**, não só heterogêneos:

- a A40 fecha com 2 re-runs **completos consecutivos** E0→E6 e **nenhum P0/P1 novo
  aberto nesses 2 re-runs**;
- a A42 fecha rodando `parse-certify` r3 + `ledger-certify` r5 — instrumentos cuja
  **função é achar achado novo** — contra baseline congelado **antes** de qualquer
  mutação.

Fundidas: toda lane A42 muta E0→E4, que é upstream de todo run E0→E6, logo **cada merge
da A42 zera o contador de re-runs consecutivos da A40**; e as rodadas que fecham a A42
abrem os P0/P1 que a cláusula da A40 proíbe na janela. Somando, a sprint fundida só
fecharia numa janela em que ninguém merga lane da A42 — que é, exatamente, a sequência
que a separação já codifica. Três consequências menores, todas medidas: dois baselines
do mesmo corpus com datas de freeze diferentes forçariam re-freeze pós-mutação (o
anti-padrão que as duas sprints nomeiam como lição da [[A39]]); o anti-Goodhart do KR-C
perderia referente (num agregado de 9 KRs, "aqui" e "lá" viram o mesmo lugar, e a sprint
sobre dupla contagem contaria o próprio KR duas vezes); e a `date_target` da A40 — único
gatilho computável do tripwire de revert da [[A40.l21]] — viraria ficção.

E a fusão **não compra o que parece comprar**: medido em cópia isolada da vault **em
2026-08-05**, mover as 12 lanes de então para `docs/sprint/A40/lanes/` mudava
`SPRINT_CURRENT.md` em **zero linhas** (as 12 eram `planned`; o renderer só lê
`{ready, open, in_progress}`). **Pelo mesmo critério, hoje seriam ≥3 linhas** —
[[A42.l7]] `open`, [[A42.l14]]/[[A42.l15]] `in_progress`. A recusa da fusão **não
depende deste número**: o motivo decisivo é a adversariedade dos dois gates de saída. O ganho de pickup exige
flipar status, que é decisão de liberação — **ortogonal à fusão**. Ver §Gatilho de
promoção para a porta que entrega esse ganho sem os custos.

## Três P0 novos da rodada `U2` (2026-08-29) — e a ativação é decisão do dono

A rodada unificada **U2** ([[LEDGER-CERTIFY-active]] §r6 · [[PIPELINE-REVIEWS-active]] §r10,
merge `47970706`) abriu três P0 cuja causa-raiz cai **exatamente** na tese desta sprint:

- [[A42.l14]] — os vereditos de conservação da `ledger-certify` certificam a **re-derivação**,
  não o artefato entregue. É o falso-verde do instrumento que dá nome à sprint, medido em
  produção pela primeira vez: a skill vinha sendo citada como propriedade do que o run
  publicou, e o próprio relatório dela mede que os dois substratos divergem.
- [[A42.l15]] — `investment_id` é hash de campos que o extrator LLM reescreve, com **23,5%**
  de estabilidade entre dois runs do mesmo documento. Dano vivo, remedido em 2026-08-29: o
  comparador dispara em **todo par consecutivo, por perna diferente a cada vez** (não as duas
  juntas), e no relatório `Internacional` cai de R$ 34.857,23 para **R$ 423,56** com os totais
  publicados **idênticos ao centavo**.
- [[A42.l16]] — o check de cobertura cambial converte *"não sei o tier"* em *"passou"*, contra
  a política escrita 400 linhas acima no mesmo módulo. **`shipped` 2026-08-29 (#1827) — e a
  lane refutou este enunciado:** o caso perigoso (banda afirmada sobre cobertura incompleta)
  **já reprovava**, com teste desde o #1568; o que o `or` deixa passar é o estado
  **sancionado** pela [[ADR-403]], e a política do CV5 citada aqui **não se aplica** a esse
  ponto (não há ausência quando o tier é `indeterminado`). O defeito real é de outro sinal —
  os dois disjuntos eram `P` e `¬P` e o termo **não discriminava nada**; medido, o produtor
  emite uma única forma e CV18 reprovava em **0 de 60** combinações de input.

**Estado (2026-08-29, na abertura):** as três entram como `planned`, seguindo o padrão das
13 anteriores — lanes planejadas numa sprint `candidate`.

> **Atualização 2026-08-29:** a [[A42.l16]] foi executada **fora** da sprint corrente e
> está `shipped` (#1827). As outras duas seguem `planned`. A decisão sobre `sprint_status`
> abaixo **não mudou** — continua do dono.
>
> **Emenda 2026-08-30:** [[A42.l14]] e [[A42.l15]] estão `in_progress` (#1825/#1832 e
> #1824/#1831). Só as 12 anteriores seguem `planned`.
 **Não flipei `sprint_status` para `current`:** só existe
uma sprint corrente por vez ([[A40]]), e duas são **erro duro** em
`dev/build_doc_index.py::_multi_current_error`. Ativar a A42 exigiria pausar ou encerrar a
A40 — cujo §Gate de saída **não está satisfeito** (contador em 0/2, ver o §Gate de saída da
[[A40]]). A decisão é do dono, e é a que destrava executar estas três dentro da sprint em vez
de fora dela.

**Consequência cruzada registrada na A40:** a [[A42.l15]] muta E3/E1.5c a montante de todo
run, logo entra na **cláusula de reinício do contador** da A40 pelo mesmo argumento mecânico
que estendeu a cláusula à l34 e à l35.

## KR — provabilidade, com duas linhas de contagem

Todo KR aqui é binário e medido por harness existente. Cada um tem uma segunda
linha de contagem porque a métrica óbvia é gamificável.

| KR | Métrica | Instrumento | Anti-Goodhart |
|---|---|---|---|
| **KR-A · fidelidade discriminada** | Todo parser line-oriented emite âncora de linhas de origem; o veredito separa *fidelidade do parser* de *completude da fonte*. `coberto-sem-verificação` cai pela linha `fidelidade_provada` | `dev/certify_parse_local.py --compare` | Contar em **duas linhas** — `fidelidade_provada` e `teto_estrutural`. A queda só conta pela primeira: reclassificar vocabulário não é progresso. O "cai de 80" da abertura (2026-08-04) é **fotografia**, não denominador vigente — re-medir na abertura |
| **KR-B · instrumento que não dá verde falso** | Nenhum check que não consegue avaliar desaparece da conta: todo check emite `pass\|fail\|skipped(motivo)` com piso de contagem por check-id; registry de balde do razão com default `não-verificável` | `scripts/validate_cross.py` + `dev/ledger_certify_core.py` | **Prova por mutação**: remover o input do check ⇒ exit ≠ 0. O KR não mede número de checks; mede que a ausência morde |
| **KR-C · identidade sob cobertura redundante** | Nenhum par de grupos do razão da mesma conta *period-free* com chaves de artefato distintas; nenhum artefato onde o sentinela de ausência é indecidível do literal | `dev/certify_ledger_local.py` | Escopo é a classe **latente** nativo↔nativo. O P0 de duplicação cross-documento é KR-B da [[A40]] e **não conta aqui** — senão A42 colhe o trabalho da [[A40.l2]]. Pontua **só a linha rotulada `[sombra · enforce omitido]`** (E2→E3, pré-colapso); a linha `[numerador KR-B]` (E3 persistido do run pinado) **não pontua o KR-C**. O critério é o **rótulo emitido** (`_SOMBRA_LABEL`/`_KR_B_LABEL` em `dev/ledger_cross_group_render.py`), não o nome do flag: sob a [[ADR-421]] D1/D2 o sujeito default muda e os rótulos permanecem |
| **KR-D · base mensal honesta** | A janela de 12 meses tem teto na data de análise; nenhum mês entra no divisor de média sem transação observada ou declarado como lacuna | invariante em teste + `dev/golden_diff.py` | Delta declarado `↑`/`↓`/`=` no golden. Rebaseline silencioso é reprovação |

**KRs rejeitados, explicitamente:** "N achados fechados" (burn-down contaria o
float-em-classificador igual ao gate suprimido) e "% completo" isolado (escalar
tudo bate a meta com zero valor verificado).

## Gate de saída da sprint

A42 não fecha por burn-down. Fecha quando **a rodada seguinte das próprias skills,
sobre o mesmo corpus, prova o fechamento**:

1. `parse-certify` r3 + `ledger-certify` r5 rodadas após as Ondas 1–2, com **zero
   achado novo da classe `saúde-harness`/falso-verde** — é a classe que esta sprint
   existe para matar; achado novo dela significa que não fechou.
2. `--compare` **exit 0** contra o baseline congelado **antes** de qualquer mutação
   (regra da [[A39.l1]]/[[A40.l1]]).
3. `coberto-sem-verificação` caiu pela linha `fidelidade_provada`.
4. Os itens de teto estrutural estão **declarados como teto**, não como dívida
   aberta.

Precedente de DoD por re-execução da skill: A32, A37, [[A39]] KR-E.

> ### ⚠️ A rodada unificada `U4` (2026-08-30) abriu 2 achados **da classe que fecha esta sprint**
>
> O critério 1 acima exige *"zero achado novo da classe `saúde-harness`/falso-verde — é a
> classe que esta sprint existe para matar; achado novo dela significa que não fechou"*.
> A `U4` ([[LEDGER-CERTIFY-active]] §r8 · [[PIPELINE-REVIEWS-active]] §r12 ·
> [[REPORT-REVIEWS-active]] §r8) **foi** um re-run completo E0→E6 sobre o mesmo corpus, e
> abriu:
>
> - [[A42.l18]] — a perna de **valor** da conservação E3→E4 é **inerte por construção**
>   (`dups` literal `0`; `abs()` sobre a mesma população pré-dedup dos dois lados);
> - [[A42.l19]] — o guard de escrita do E4 resolve por **stage** e tem ramo **placeholder**;
>   o `patrimonio` real **reprova** e é gravado sob `warn`, e o razão imprime *coberto* para ele.
>
> Ambos são falso-verde de instrumento. **O critério 1 não é satisfeito e a sprint não
> fecha.** A `U4` também mediu que o critério 3 (*"`coberto-sem-verificação` caiu pela linha
> `fidelidade_provada`"*) **andou para trás por consequência de método**: o rebaixamento da
> [[A42.l18]] moveu `fluxo_caixa` e `reserva_emergencia` de `conservado` **para**
> `coberto-sem-verificação-de-valor`.

**Rito de abertura (auditoria 2026-08-14).** O gate acima fecha a sprint. A
**promoção** (`[[A40]] → done`) começa com `parse-certify` r3 + `ledger-certify` r5
**antes do primeiro pickup**, carimbando cada uma das lanes não-terminais
`sobrevive` / `absorvido` / `morreu`. Achado novo da classe falso-verde entra;
achado de entrega vai para [[PLAN-report-trust]], não vira `A42.l14`. Sem esse
passo o plano executa fotografia de 2026-08-04 contra um E3 que a [[A40.l2]] já
mutou. A auditoria de mesa abaixo **não** substitui esse rito — só deixa o
grafo honesto até lá.

## Lanes (22)

| Lane | O quê | Prio | Onda | Dep |
|---|---|---|---|---|
| [[A42.l1]] | Stage de unlock aborta o run inteiro, e o secret dele é inalcançável em deploy limpo | **P0** | 0 | — |
| [[A42.l3]] | Harness de certificação: falso-verde para dentro — **+4 itens da U1** (`layer_ok` verde sobre ponto cego, checksum auto-consistente, resíduo E2→E3 não computado, CV de severidade constante) | P1 | 1 | — |
| [[A42.l4]] | Check que não consegue avaliar evapora em vez de virar `skipped` | P2 | 1 | — |
| [[A42.l2]] | Parsers line-oriented: âncora de fidelidade + supressão vira verdict do gate | P1 | 1 | [[A42.l3]] |
| [[A42.l6]] | Contrato do store: política de escopo, retenção de órfão e validação de artefato | P1 | 2 | [[A42.l5]] |
| [[A42.l7]] | Registro de custo de LLM é fonte de verdade que perde row e vaza filename | P1 | 2 | — |
| [[A42.l5]] | Chave de agrupamento do razão carrega o período do documento | P1 | 2 | — |
| [[A42.l8]] | Mês vazio por falha de extração conta como mês documentado | P1 | 2 | [[A40.l15]] · [[A40.l11]] · [[A40.l44]] |
| [[A42.l9]] | Vocabulário do checksum de fatura: separar dívida acionável de teto estrutural | P1 | 3 | [[A42.l2]] |
| [[A42.l10]] | Misclassificação na classificação amplifica o carrier de duplicação | P1 | 3 | [[A41.l2]] |
| [[A42.l11]] | Enforce do checksum cross-source fatura ↔ débito de pagamento | P1 | 3 | — |
| [[A42.l12]] | Estado de extração do documento: predicado único e stages derivados do registry | P2 | 3 | [[A42.l2]] |
| [[A42.l13]] | Completude por ficha: `não-shell` é fraco demais para sustentar `completo` | P1 | 2 | — |
| [[A42.l14]] | Conservação certifica a **re-derivação**, não o artefato entregue — `_conservation` recebe `fresh_e3`, e o persistido só alimenta o drift · **U2 `LC6-01`** | **P0** | 1 | — |
| [[A42.l15]] | `investment_id` é hash de campos que o extrator LLM reescreve — **23,5%** de estabilidade entre runs; o comparador dispara uma perna diferente a cada par consecutivo · **U2 `LC6-02`** | **P0** | 1 | — |
| [[A42.l16]] | O check de cobertura cambial converte *"não sei o tier"* em *"passou"*, contra a política escrita no mesmo módulo · **U2 `PV10-01`** · ✅ **#1827** — **enunciado refutado pela própria lane**; o defeito real é o termo `P ∨ ¬P` que não discriminava nada (P1 recomendado, re-triagem com o `r11`) | **P0** | 1 | — |
| [[A42.l17]] | Parser de banco chama o SDK LLM fora do contrato — sem temperatura, sem telemetria — e a saída livre vira **chave natural** · **U3 `LC7-01`** · ✅ **#1846** — defeito procede; o gate que devia pegá-lo era cego em **3** eixos e os 2 sítios crus do repo moravam na interseção. Eixo novo: **rotear pelo choke-point não compra determinismo** (`use_cache` é `False` por default), logo o *delete-and-delegate* da [[A41.l3]] passaria os 5 critérios dela com o churn intacto | **P0** | 1 | — |
| [[A42.l18]] | A perna de **valor** da conservação E3→E4 é inerte: `dups` é `0` **literal** na linha 265 (a linha 160, E2→E3, passa a variável real) e os dois lados somam `abs()` sobre a **mesma população pré-dedup** ⇒ `Δvalor = 0` é invariante a inversão de sinal **e** às 858 rows do dedup · **U4 `N1`** · ✅ **#1870** — defeito procede nas duas causas; o produtor passa a **declarar** o valor do destino ([[ADR-426]]) e o harness lê a declaração. Mas o **controle positivo obrigatório do enunciado era insatisfazível**: nas 62 tx das fixtures nenhuma declara `tipo`, a direção é *derivada* do sinal, logo não há testemunha independente contra a qual detectar inversão — a linha condenaria qualquer conserto correto e foi corrigida. Eixo novo: **entregar só o harness seria pior que hoje** (4/4 do gate falham nesse subconjunto — as duas metades são conjuntamente necessárias) | P1 | 1 | — |
| [[A42.l19]] | O guard de escrita do E4 resolve por **stage**, nunca por `artifact_key`, e o `oneOf` tem ramo **placeholder** (`{status}`) que um balde transacional casaria; medido: `patrimonio` (87 itens) **reprova em `$`** e é gravado sob `warn`, e a jusante o razão imprime *coberto · 0 itens* para ele · **U4 `N2`** | P1 | 1 | — |
| [[A42.l20]] | `_e3_count` soma só `transacoes_total + transacoes_duplicadas_removidas` e **ignora `remocoes`**, que a função duas acima lê; canal declarado e reconciliável ao inteiro sai como *count divergente* com **duas causas declaradas, ambas falsas** · **U4 `LC8-03`** | P2 | 1 | — |
| [[A42.l21]] | O `X5` da rodada unificada **só pode sair vermelho** e agrega 3 causas distintas sob 1 rótulo (skip mal-carimbado · escreve sob outra key por desenho · read-only); conjunto **constante** em U2/U3/U4 ⇒ poder discriminante zero · **U4 `PV12-04`** | P2 | 1 | — |
| [[A42.l22]] | A **ETA exibida durante o run** é subdeclarada em até **72%**: a mediana filtra `status==completed` e mistura no-ops de milissegundos com execuções de minutos · **U4 `PV12-01`** — único P2 da rodada com consequência medida na superfície do usuário | P2 | 1 | — |

Capacidade decidida: teto de 14 lanes. **Fechou em 12** — 11 na abertura, mais a l12
nascida do **split da l6** por decisão do `senior-cto` (eram dois agregados empacotados,
com bloqueio e reversibilidade distintos). Uma 13ª (proveniência do executor) foi
admitida e **promovida para a [[A40]] no mesmo dia** — ver §Lanes promovidas. Os slots
restantes não foram preenchidos de propósito: padding para bater um número é a forma
mais barata de Goodhart num plano.

> **O parágrafo acima é fotografia de 2026-08-05** — o último commit que o manteve foi o
> `7215daf3` (#1209), com 12 lanes na mesa e 2 slots de folga. Não o reescreva: ele
> registra a decisão de capacidade como ela foi tomada.

**Estado da capacidade — 2026-08-30 (re-medido na rodada unificada `U4`).** A sprint tem
**22 lanes**: o `## Lanes (22)` acima, 22 linhas na tabela e 22 arquivos em
`docs/sprint/A42/lanes/` — os três substratos concordam, e o `check_lane_counter` do
`lane-closeout` só compara esses três. As duas últimas ([[A42.l18]], [[A42.l19]]) nascem
da `U4` e são **da classe que dá nome à sprint** — falso-verde de instrumento —, o que é
por si o argumento de que a sprint não fechou. As três seguintes ([[A42.l20]]–[[A42.l22]]) são
os P2 da mesma rodada, alocados a pedido do dono em 2026-08-30. **O teto de 14 está excedido em 8, e o rompimento
nunca foi decidido:** as cinco lanes acima de 12 entraram uma a uma, em PRs distintos, sem
que o parágrafo acima fosse relido.

> **Por que o número estava em 16.** Este parágrafo nasceu correto no #1842 e ficou falso
> no #1843, que criou a [[A42.l17]] sem reler a contagem — o mesmo modo de falha que ele
> próprio denuncia, uma volta depois. A frase afirmava três substratos "concordam" em 16
> quando os três estavam em 17: o predicado sobrevivia, o número não.

| Lane | Entrou | Por quê | PR |
|---|---|---|---|
| [[A42.l13]] — completude por ficha | 2026-08-21 | a [[ADR-266]] foi falsificada por emenda datada e o predicado substituto precisava de casa. **Reusa o id da 13ª promovida** — ver §Lanes promovidas | #1624 (lane) · #1747 (linha na tabela) |
| [[A42.l14]] · [[A42.l15]] · [[A42.l16]] | 2026-08-29 | três P0 da rodada `U2` — [[LEDGER-CERTIFY-active]] §r6 · [[PIPELINE-REVIEWS-active]] §r10 | #1821 |
| [[A42.l17]] | 2026-08-30 | P0 da rodada `U3` (`LC7-01`) — [[LEDGER-CERTIFY-active]] §r7 | #1843 (lane) · #1846 (entrega) |

**Nenhuma das quatro é padding** — que é o único abuso que o teto existia para impedir.
Mas o teto foi decidido contra outra evidência — *"nenhuma sprint acima de ~11 lanes
fechou pelo próprio gate na história do repo"* ([[SPRINTS-active]] §A42) — e essa evidência
**não foi re-medida**. Elevar o teto para 16 aqui seria escolher o número **depois** de
conhecer o ofensor.

**Decisão pendente, do dono** (mesma porta do `sprint_status`): (a) elevar o teto com
rationale novo e datado; (b) manter 14 e **dividir**, promovendo lanes pela porta de
nível-lane do §Gatilho de promoção; ou (c) declarar o teto **advisory** — sinal de que a
sprint pediu re-triagem, não gate de admissão. Até a decisão, **a contagem vigente é 16 e
este bloco é a fonte dela**.

**Ordem dentro da tabela reflete pickup, não numeração.** A l3 vem antes da l2 porque a
l2 consome o ratchet que a l3 entrega; a l5 vem antes da l6 pela mesma razão. Nenhuma
lane tem `depends_on: []` só porque a dependência estava em prosa — a [[A40]] mediu
exatamente essa armadilha (`SPRINT_CURRENT` apresenta como pegável em qualquer ordem, e
shipar o writer antes do reader entrega pior que hoje), e a A42 a reproduziria uma sprint
depois se `parallel_with` fosse o veículo. `parallel_with` não é lido por consumidor de
máquina nenhum.

## Ondas

Ordenadas por **alavancagem**, não por severidade: sem detecção, todo fix abaixo
regride em silêncio e fecha verde. A ordem não é estética — o KR-B só é
**mensurável** depois da [[A42.l14]] **e** da [[A42.l3]], nessa ordem: a perna de
volume do gate anti-regressão está morta hoje (l3), e o registry de balde que o KR-B
nomeia carimbaria veredito **sobre o universo errado** enquanto a l14 não corrigir o
sujeito ([[ADR-421]]). Uma versão anterior desta linha citava só a l3. Instrumento primeiro é pré-condição do critério de
saída, não preferência.

**Onda 0 — parar a sangria** ([[A42.l1]]). Solo. Não é instrumento e não compartilha
arquivo com a Onda 1; o gate dela é **externo** (o defeito não morde no dogfood, onde
o arquivo de senha existe e o run completa — morde em deploy limpo e no segundo
usuário). Fica fora da Onda 1 para não competir por pickup com instrumento nem
sugerir bloqueio que não existe.

**Onda 1 — instrumento** ([[A42.l4]] livre; [[A42.l3]] livre desde 2026-08-14 — a
aresta para [[A40.l2]] morreu no #1368; [[A42.l2]] atrás da l3).
**Não são disjuntas — partição declarada.** A l4 é solo em arquivo. A l2 e a l3 tocam
ambas `dev/certify_parse_local.py`, e no mesmo ratchet: a **l3 é a dona do arquivo** e
entrega a cláusula que a l2 precisa — cláusula que agora está no **critério de aceite da
l3**, não só na prosa da l2. Uma versão anterior deste plano afirmava disjunção aqui: era
falso, e duas lanes P1 reescrevendo o mesmo ratchet em paralelo é exatamente o cenário que
a onda diz evitar.
**A [[A42.l14]] entrou na Onda 1 em 2026-08-29 e reabre a mesma questão em outro arquivo.**
Ela e a l3 tocam ambas `dev/ledger_certify_core.py`, e não são paralelas: a l14 corrige
**de qual universo** vêm as peças que todos os vereditos leem, e o registry de checkers do
item 1 da l3 reescreve `_non_ledger_verdict` **sobre essas peças**. **A l14 precede os
itens 1–5 da l3** — aplicar o registry antes produz um `não-verificável` corretamente
tipado sobre o universo errado, que é pior que o `coberto` de hoje porque *parece*
consertado e passaria no critério de mutação da l3. Não é `depends_on`: a l3 tem itens
6–9 entregáveis antes. Rationale em [[ADR-421]] §Lane e arestas declaradas.

**Onda 2 — identidade, contrato e base** ([[A42.l5]] → [[A42.l6]]; [[A42.l7]] livre;
[[A42.l8]] atrás de [[A40.l15]], [[A40.l11]] e [[A40.l44]]). A l5 e a l6 são
**sequenciais**, não paralelas: o guard "por expectativa" da l6 conta grupos cujo
keying a l5 muda, e o escopo da listagem da l6 muda o conjunto de pernas do merge
da l5 — logo o `titular` que vai ao hash. A l8 entra na fila de rebaseline do
snapshot do view-model, compartilhada com a [[A40.l15]], e **não reabre** o D3 da
[[ADR-306]] que a [[A40.l44]] já emendou — ver §Auditoria de mesa.

**Onda 3 — o que depende de terceiros** ([[A42.l9]], [[A42.l10]], [[A42.l11]],
[[A42.l12]]). A l12 está aqui, e não na 2, porque depende do enum de verificabilidade que
a l2 cria: escrever o predicado contra o mundo de dois estados e receber o terceiro depois
acenderia o selo de qualidade sobre conservação não provada — o falso-verde da tese,
produzido pela lane que existe para matá-lo.

**Amarra obrigatória das dependências cross-sprint.** **Duas lanes carregam quatro
arestas** vivas (auditoria 2026-08-14): [[A42.l8]] → [[A40.l15]] · [[A40.l11]] ·
[[A40.l44]] · [[A42.l10]] → [[A41.l2]]. Quatro arestas morreram no ramo 2 (dep
`shipped`): [[A42.l3]]/[[A42.l5]]/[[A42.l11]] → [[A40.l2]] (#1368) e [[A42.l7]] →
[[A40.l19]] (#1241). A aresta nova [[A42.l8]] → [[A40.l44]] é colisão de arquivo
(`fluxo_caixa_enricher.py`) + demarcação do D3 — ver §Auditoria. Na promoção,
**re-ler a disposição de cada dependência** — por **aresta**, não por lane — com
**três** ramos, não um:

1. dependência `cancelled` ⇒ a lane A42 **absorve o escopo** e declara a absorção no
   corpo. Sem isso, uma A40 que fecha `done` com [[A40.l15]] `cancelled` deixa a
   [[A42.l8]] esperando um evento que nunca chega;
2. dependência `shipped` ⇒ a dependência é morta, remover e anotar o PR;
3. dependência ainda `open`/`planned`/`in_progress`, **carregada por plano vivo** —
   caso residual da [[A40.l15]]/[[A40.l11]]/[[A40.l44]] e da [[A41.l2]]. A lane A42
   permanece `blocked` e a condição de destravamento é o **merge do PR nomeado** (ou
   `cancelled` → ramo 1), não o fechamento da sprint dona. A [[A40.l2]] saiu deste
   ramo em 2026-08-11.

Precedente: cláusula de entrega parcial da [[A40.l27]].

**Furo desta amarra, fechado 2026-08-05 e quitado 2026-08-14.** Ela cobria só a
direção `A42 → A40`: "a dependência escorregou, e agora?". Faltava a direção inversa
— **lane A42 que põe em risco entrega viva da A40**. Em 2026-08-05 isso era a
[[A42.l3]] reescrevendo
[`dev/ledger_certify_core.py`](../../../dev/ledger_certify_core.py) — o arquivo que
produzia o numerador de 261 (fotografia) contra o qual a [[A40.l2]] provava o
fix. A l2 shipou (#1368); a aresta morreu. **Cautela que sobrevive sem ser dep:**
o residual da l2 declara que o instrumento **continua cego ao enforce** por
construção e ainda reporta 261 na sombra. Quem reescrever o item 1 da l3 pina
comparabilidade do `cross_group` ou re-freeze — não trata o 261 como denominador
vigente. **Regra que generaliza:** antes de promover, verificar também se alguma
lane desta sprint **escreve no instrumento** de uma lane viva de outra.

## Auditoria de mesa 2026-08-14

> Cruzamento das 12 lanes contra `origin/main` (`6c68723a`). Sem re-execução de
> skill. **Não reabre** a fusão A42→A40. Números da abertura (261, ~19% da
> receita, `coberto-sem-verificação` = 80, 31/41 faturas) são **fotografia de
> 2026-08-04**, anteriores ao enforce da [[A40.l2]].

**Veredito.** A tese sobrevive. Os 12 mecanismos ainda estão no código. O que
envelheceu é o grafo, três âncoras de linha, e o item 2 da [[A42.l8]].

| Lane | Âncora hoje | Dep | Carimbo |
|---|---|---|---|
| [[A42.l1]] | `unlock_documents.py:395` ainda chama `load_passwords()` antes do glob; `llm_call_log` é outro assunto | — | **sobrevive** |
| [[A42.l2]] | `_c6_csv_apply_conservation_flags` (`c6bank.py:112-130`) ainda suprime o gate por conclusão do parser | [[A42.l3]] | **sobrevive** |
| [[A42.l3]] | `_non_ledger_verdict` agora em `ledger_certify_core.py:170` (era `:161`); default ainda `COBERTO_SEM_VALOR`. `certify_parse_local.py` ainda não lê `checksum_ok` | — (era [[A40.l2]], #1368) | **sobrevive**; cautela de instrumento no §Amarra |
| [[A42.l4]] | `_CONSERVATION_CHECKS` em `validate_cross.py:611`; `compare_reviews.py:179` ainda busca `transacoes_total` | — | **sobrevive** |
| [[A42.l5]] | `generate_legacy_filename` (`e3_serialization.py:139-144`) ainda embute `inicio_ym`/`fim_ym` na chave | — (era [[A40.l2]], #1368) | **sobrevive** (classe latente nativo↔nativo). LC04: âncoras originais **não resolvem** — o default de `account_type` agora é `"extrato"`, não `"desconhecido"`; re-medir na abertura |
| [[A42.l6]] | `list_keys` (`db_artifact_store.py:379`) segue workspace-wide; `SCHEMA_BY_STAGE` ainda sem `review_finances_holistic` nem `extract_members` | [[A42.l5]] | **sobrevive** |
| [[A42.l7]] | `LLMCallLog.stage` segue `String(64)` (`llm_call_log.py:26`) | — (era [[A40.l19]], #1241) | **sobrevive** |
| [[A42.l8]] | `_compute_janela_12m` ainda fatia `meses[-n:]` (`fluxo_caixa_enricher.py:497`); a série que chega já passou por `split_provisionado(data_corte)` | [[A40.l15]] · [[A40.l11]] · **[[A40.l44]]** | **sobrevive em parte** — ver demarcação abaixo |
| [[A42.l9]] | vocabulário de checksum de fatura inalterado | [[A42.l2]] | **sobrevive** |
| [[A42.l10]] | classificação E0 ainda amplifica o carrier; arquivos ainda da [[A41.l2]] | [[A41.l2]] (`planned`) | **sobrevive** |
| [[A42.l11]] | [[ADR-350]] segue `Proposto`; measure-only #1087 | — (era [[A40.l2]], #1368) | **sobrevive** |
| [[A42.l12]] | `_E2_DB_STAGES` hardcoded em 3 (`document_pipeline_sync.py:36`); predicado ainda não inspeciona payload. Path moveu para `backend/app/services/pipeline/` | [[A42.l2]] | **sobrevive** |

Nenhuma lane **morreu**. Nenhuma foi absorvida inteira.

### Demarcação [[A42.l8]] ↔ [[A40.l44]]

A [[ADR-306]] §Emenda 2026-08-11 (commitada) já redefiniu D3: mês documentado
exige movimento, fechamento e não-posterioridade à `data_corte` do run. A
[[A40.l44]] PR1 entrega o corte de **futuro** via `split_provisionado` **antes**
de `_compute_janela_12m`. O corte do **mês em curso** está deferido pela própria
l44, dono `senior-cto`, **lane própria depois da l44** — não é esta.

| Eixo | Dono | Estado 2026-08-14 |
|---|---|---|
| Mês futuro no denominador (RV4-04, item 2 da l8) | [[A40.l44]] + emenda D3 | **absorvido** — l8 não reabre |
| Mês em curso no denominador | deferido da [[A40.l44]] | **fora da l8** |
| Zero por falha de extração fantasiado de observação (PC11) | [[A42.l8]] | aberto |
| União receita+despesa com zero-fill (RV4-05) | [[A42.l8]] | aberto |
| Piso de publicação por classe + fonte única de categoria | [[A42.l8]] | aberto |

A l8 **ganha** `depends_on: [[A40.l44]]` por colisão de arquivo
(`fluxo_caixa_enricher.py`) e para não emendar o D3 por cima da l44.

### O que a A40 comeu na borda (e não é desta sprint)

[[A40.l38]] (caixa canônico), [[A40.l40]] (CNPJ-raiz), [[A40.l41]] (frescor
cross-pool) e [[A40.l42]] (baseline pegajoso do E1.5c) tocam identidade/ingestão
e nasceram depois desta sprint. Nenhuma das 12 lanes daqui é dona desses
arquivos. Ficam na A40. Não é fato novo que reabra fusão — é a cerca da cláusula
1 do §Critério de admissão funcionando no sentido inverso.

## Relação com a A39

A [[A39]] tem a mesma tese (`ingest-trust`) e **já está `done`** (fechada na
abertura desta sprint). A disposição item a item abaixo é histórica — o conjunto
`candidate` deixou de incluir a A39. Mantida aqui porque os resíduos deferidos
ainda apontam para lanes desta sprint:

| Resíduo da A39 | Blocker declarado | Disposição |
|---|---|---|
| [[A39.l3]] c2 (opt-in de fatura) + [[A39.l8]] (parser determinístico) | A §Deferido da A39 (escrita 2026-07-23) os declara bloqueados na identidade do checksum | **Nada a adotar — já entregues.** A [[ADR-342]] §Emenda **2026-07-24** decidiu a identidade (por seção) e ligou os dois parsers com o corpus fechando a cent, zero falso-fire. O deferimento durou um dia; a §Deferido da A39 nunca foi reescrita. A [[A42.l9]] atende **PC12**, que é defeito próprio e posterior (vocabulário: `faltando` conflaciona dívida com teto em 31 de 41 documentos) — **não** o resíduo da A39 |
| [[A39.l6]] residual (traço positivo do checksum) | — | **Adotado** por [[A42.l3]] — o traço já é emitido e escrito no schema; o harness não o lê |
| §Deferidos — propagação E2→E5 e selo de qualidade, gated por [[ADR-345]] | ADR `Roadmap`, adoção deferida | **Gatilho registrado** por [[A42.l2]]. A condição de retomada da nota é "quando um achado de revisão demonstrar número de origem degradada chegando ao usuário sem sinal" — o §r2 é esse achado. Registrar o gatilho é docs-only; **promover a nota exige design** ([[ADR-358]]) e não é escopo desta sprint |
| [[A39.l13]] (`planned`) — re-route da classificação pelo choke-point de LLM | — | **`cancelled`** por duplicação: é a [[A41.l2]], que já é dona dos mesmos arquivos |

Efeito no inventário (já ocorrido): o conjunto `candidate` foi de {A39, A41} para
{A41, A42} — **não cresceu**, e os resíduos deferidos ganharam destino nomeado.
Precedente exato: a própria A39 fazendo isso com a cauda da A38.

## Fora do sprint (disposição explícita)

Sem esta seção, o silêncio lê como "cobrimos os 74 achados". Não cobrimos — e o
corte é declarado por **classe**, não como "cauda".

**Roteado para lane ou plano que já é dono do arquivo** (a regra é: quem possui a
superfície possui o achado):

| Achado | Destino | Motivo |
|---|---|---|
| Duplicação cross-documento do razão (P0, ~19% da receita — fotografia 2026-08-04) | [[A40.l2]] | **Shipou 2026-08-11 (#1368):** colapsador enforce, 453 rows cortadas, E3 6256→5803. O aviso de 2026-08-04 ("P0 tem dono e não tem fix escrito") **não vale mais**. Residual da própria l2: o instrumento `certify_ledger_local` agora emite a linha `[numerador KR-B]` sobre o E3 persistido, que pontua a KR-B da A40; o KR-C daqui lê **só** a linha `[sombra · enforce omitido]` (261 no cru, fotografia 2026-08-04). O persistido **não conta** no KR-C |
| Débito de âncora estável de override manual + eixo member-level do lineage em zero | [[A40.l2]] PR3 | Mesma causa; a trilha de ambos diz "não abrir lane" |
| Limiar de confiança + canal de pausa inalcançável | [[A40.l21]] | A trilha diz "acoplar a A40.l21" |
| Decisão registrada pelo dono descartada da única seção que responde "o que fazer" (**P0**) | [[A40.l10]] | Ver §Nota sobre o P0 de entrega abaixo |
| Termo de marca metodológica vazando para o índice web | [[A40.l7]] | l7 já é dona do YAML de layout e do shell; alcança o usuário hoje |
| Projeção de exclusão inerte por construção (override do dono sem efeito monetário) | [[PLAN-pipeline-review-r2]] Onda D | É a escalação de um achado que já vive lá, agora de `consistência` para `correção` |
| Meta de independência conservadora descartada pelo adapter · cascade de custo de imóvel não plumbada · truncamento silencioso do bloco denso do parecer · alíquota ancorada em exercício incompleto | [[A40]] / [[PLAN-pipeline-review-r2]] | Eixos com dono ativo (l8/l25/l28/l30) |
| ~~YAML de layout que não governa o render~~ · gate de chart que derruba a seção inteira | [[A40.l7]] | l7 já possui essas superfícies. **A 1ª metade fechou** em 2026-08-10 (#1355): `ReportSection` perdeu o prop `title` e deriva de `sectionHeading(id)`, com o `id` como união literal do codegen — o YAML passou a governar o heading, e re-hardcodar é erro de compilação. Segue aberto o gate de chart |
| Base do gráfico de despesas divergindo da conclusão | [[A40.l15]] | A trilha diz "deduplicar contra A40.l15 item 1, não abrir lane nova" |
| Componente de proteção ausente do score | [[A40.l11]] | A trilha diz "não duplicar" |
| Número monetário em formato en-US na prosa gerada | [[A40.l13]] | l13 já cria o gate de render monetário |
| Cobertura de citação e limiar sem fonte no repo | [[A40.l30]]/[[A40.l31]] | l30 é o instrumento de ancorabilidade; paralelo colidiria no catálogo |
| `else` exaustivo do equilíbrio presente/futuro (percentual publicado **inverte** sob a lista declarada) · input de contrato sem leitor · convenção de unidade quebrada · campos sem consumidor | [[PLAN-pipeline-review-r2]] | É domínio e contrato de view-model, não a camada desta sprint. O primeiro é o de maior materialidade dos quatro e pede posição na Onda A, não no fim da cauda |

**Cauda não alocada — contada, não estimada.** A revisão de pipeline tem **73
achados codificados** (o 74º é de instância e ficou off-git, sem código, logo não é
roteável). Deles: 22 em lane A42, 20 roteados nominalmente acima, 9
refutados/positivos, e **22 sem destino individual** — 12 P2 e 10 P3.

Duas dimensões inteiras estão **fora da sprint por camada**, e é honesto nomeá-las
com a contagem em vez de diluí-las em "cauda": **`qualidade-llm` (13 achados abertos,
zero na A42)** e **`clareza-ux` (10 abertos, zero na A42)**. Juntas são 36% dos
abertos. O corte é o §Critério de admissão cláusula 3 — nenhuma das duas é ingestão,
razão, contrato de store ou instrumento de certificação — e o destino é
[[A40.l30]]/[[A40.l31]] (citação e parecer), [[A40.l13]] e [[A40.l7]] (render), ou o
[[PLAN-pipeline-review-r2]].

Dos 22 sem destino individual, **8 não caem em nenhuma dessas classes** e ficam
explicitamente para `aceito-wontfix` com rationale no MOC da skill, na próxima
re-triagem (r5). Um deles merece nota: há um P3 de **egresso de fragmento de
identificador fiscal mascarado ao provedor**, duplicado em dois campos — é P3 pela
materialidade, mas é vazamento, e não deve morrer na cauda anônima.

**Refutados e positivos** ficam registrados nos MOCs de origem com rationale e
**não viram lane**: no §r2, 1 refutado + 1 não-acionável; no §r4 do razão, 2
refutados + 1 confirmação fechada; no §r4 da revisão, 6 refutados + 3 positivos.

### Nota sobre o P0 de entrega

A decisão registrada pelo dono não chega à única seção do relatório que responde
"o que fazer" — é P0 e alcança o usuário hoje. **Não é lane nova na A40 nem espera
aqui:** a [[A40.l10]] já é dona da ordenação do plano de ação e o critério de
aceite dela diz literalmente que recomendação não-computável nunca desaparece sem
rastro. É a mesma superfície, o mesmo dono. Entra como item no escopo da l10, que
flipa para `open` (a dependência dela shipou) — o P0 fica pescável hoje **sem
admissão nova na A40**.

## Critério de admissão (fecha a §Pendência de decisão nº 10 da A40)

A A40 pergunta se "nada sai da A40" vale para lane nascida depois. Cinco cláusulas,
em ordem de precedência:

1. **Destino é quem já possui o arquivo ou a superfície.** Se uma lane ou onda
   **viva** já é dona do arquivo, o achado é **item dela** — nunca lane nova. É o
   tie-break primário e é a mesma regra de agrupamento que A40 e A42 declaram.
2. **A A40 admite apenas por adoção.** Depois de 2026-08-03, nada nasce lane nova
   nela: achado sem dono de arquivo vai para A42 ou para plano temático, **mesmo
   sendo P0**. Exceção única e nomeada: P0 que alcança o usuário, sem dono de
   arquivo em nenhuma lane viva, **e** cuja espera até a promoção da A42 se mede em
   semanas — nesse caso lane nova, com o custo registrado em §Fora do sprint.
3. **A A42 admite por camada, e só quatro:** ingestão (E0→E2), razão (E3/E4),
   contrato de store/artefato, instrumento de certificação. Fora dessas quatro não
   entra, ainda que seja P0.
4. **Plano temático vivo tem precedência sobre sprint** quando o achado é
   continuação de tese já ownada. Sprint é janela de execução; plano é dono de tese.
5. **O que não passa em 1–4 recebe disposição explícita** no MOC da skill.

"Consumidor datado", operacionalizado: existe artefato citável — track, plano ou
gate — que declara que algo **para** até isso existir. "É importante e urgente" não
qualifica.

## Lanes promovidas para fora desta sprint

| Lane | Destino | Quando | Por quê |
|---|---|---|---|
| Proveniência do executor (nasceu `A42.l13`) | **[[A40.l32]]** | 2026-08-05 | Decisão do dono, pela porta de nível-lane do §Gatilho de promoção. Instrumento sem custo de API, sem dependência das ondas da A42, e o gate da A42 (`A40 → done`) travaria por ~2 semanas trabalho que o dono pediu para destravar |

**A l13 não foi reciclada.** O id fica queimado: renumerar lane viva por economia de
número é o que produz resíduo em prosa. Próxima lane desta sprint é a l14.

> **Falsificado em 2026-08-21 (#1624):** o id **foi** reciclado —
> `A42-l13-completude-por-ficha.md` nasceu com `id: A42.l13`, 16 dias depois da promoção.
> A regra acima não foi revogada; foi violada em silêncio, porque o PR que criou a lane
> não tocou este `_README` (a linha só entrou na tabela seis dias depois, no #1747).
> Consequência viva: a §Lanes promovidas ancora `A42.l13` no referente **antigo** e a
> tabela §Lanes o ancora no **novo**.

## Gatilho de promoção a `current`

Evento, não calendário: **[[A40]] → `done`**. Enquanto a A40 é `current`, duas
sprints `current` são hard fail em `build_doc_index.py --check`, e as lanes desta sprint
nascem `planned` — **escritas, não autorizadas para pickup**. Padrão [[A41]]. (A contagem
vive num lugar só: o `## Lanes (N)` da §Lanes, que é o único com gate. Hoje 12 das **22**
seguem `planned`; [[A42.l7]] e [[A42.l18]]–[[A42.l22]] estão `open`,
[[A42.l14]]/[[A42.l15]] `in_progress`, [[A42.l16]]/[[A42.l17]] `shipped`.)

**Dois níveis, decisão do dono 2026-08-05.** A pergunta "faz sentido fundir a A42
dentro da A40?" foi avaliada e **recusada** (§Por que esta sprint existe, agora com o
motivo mecânico registrado lá). O que a fusão comprava de legítimo era uma coisa só —
tirar lane individual da fila quando ela passa a importar antes do fechamento da A40 —
e para isso já existe porta, com precedente executado:

- **Nível sprint:** [[A40]] → `done` (inalterado). Promove de uma vez todas as lanes
  não-terminais da sprint (hoje 15).
- **Nível lane:** **promoção individual para a sprint corrente por *consumidor
  datado***, reparentando a lane (`sprint: A40` + `git mv`). Precedente exato:
  [[A40.l24]], que nasceu `A41.l1` e foi promovida assim por decisão do dono em
  2026-08-03 — a única dos follow-ups com consumidor datado. **Reparentar é o que a
  torna visível:** `_filter_sprint_lanes` em
  [`dev/_sprint_current_renderer.py`](../../../dev/_sprint_current_renderer.py) filtra
  por `lane.sprint ∈ {corrente}`, então flipar uma lane A42 para `open` **não** a faz
  aparecer no `SPRINT_CURRENT`.

Isto **não** reabre a cláusula 2 do §Critério de admissão (*"nada nasce lane nova na
A40, mesmo sendo P0"*), por uma distinção de verbo: aquela cláusula governa achado
**novo sem dono**. Lane que já nasceu, em outra sprint, com dono e com ADR exigida, é
**promovida** — operação diferente, gate mais estreito (consumidor datado, que exige
artefato citável declarando que algo *para* até isso existir; "é importante e urgente"
não qualifica). Manter os dois verbos distintos é o que impede deriva de precedente.

## ADRs exigidas antes de PR de implementação

Política do CLAUDE.md: task P0/P1 com escopo arquitetural abre ADR `Proposto` antes
do PR de implementação.

| Lane | Forma | Por quê |
|---|---|---|
| [[A42.l2]] | **Emenda datada à [[ADR-342]]** — não ADR nova | Mesma decisão com o eixo refinado (separar fidelidade do parser de completude da fonte). Precedente: a emenda de 2026-07-27, também nascida desta skill |
| [[A42.l5]] | Corolário da [[ADR-354]] (`Decidido` desde o merge da [[A40.l2]]) | O repo já tem a definição period-free certa e agrupa pela errada. Se a tupla da chave de **artefato** exigir mudança de decisão, a forma é emenda datada — a ADR já não está `Proposto` |
| [[A42.l6]] | Emenda [[ADR-291]] | Política de escopo do store: listagem e leitura discordam. Toca também [[ADR-278]] e [[ADR-212]] |
| [[A42.l12]] | **ADR nova** `Proposto` | Onde mora o predicado único de extração é decisão de **boundary** (`backend/` ↔ `pipeline/`) — uma emenda de política de escopo não pode ser o veículo dela |
| [[A42.l8]] | **ADR nova** `Proposto` + emenda datada à [[ADR-306]] **só no eixo que sobra** | Piso de publicação por classe e dimensionamento conservador são **regra nova**. O D3 já foi emendado em 2026-08-11 pela [[A40.l44]] (mês documentado exige movimento, fechamento e não-posterioridade à data de corte). Esta lane **não reabre** futuro nem mês em curso — o segundo está deferido pela própria l44. A emenda daqui cobre só "zero por falha de extração ≠ observação" |
| [[A42.l1]] | **ADR nova** `Proposto` | Provisionamento de secret em tenant limpo — co-design `senior-cto` + `sre-devops` |
| [[A42.l7]] | Coordenar com [[ADR-357]] §7 | Migration + contrato de coluna; a [[A40.l19]] (#1241) já está na cadeia — esta lane é a próxima, não mais "atrás de alguém em voo" |

**Armadilha de forma:** heading de emenda **não leva wikilink** — o gate
`check_adr_amendment_signal.py` pula heading que contém `[[ADR-NNN]]` diferente do
id próprio, e a emenda passa sem exigir `amended_at`. Escreva
`## Emenda A42.lN — <o quê> · AAAA-MM-DD` e ponha `amended_at` no frontmatter no
mesmo commit.

## Regras de execução

1. **Corretude:** bug → teste de regressão **antes** do fix, com fixture sintética
   PII-zero. Documento real nunca entra em git, fixture, CI ou log não-mascarado.
   Dinheiro nunca é float ([[ADR-090]]); conservação e checksum em **cents,
   tolerância zero**.
2. **Detecção antes de fix.** Nenhuma lane de correção shippa sem o sinal que
   provaria a regressão no mesmo PR. É a lição que esta sprint inteira encarna.
3. **Prova por mutação onde o critério é "o gate morde".** Asserção que sobrevive à
   remoção do mecanismo que ela nomeia é asserção vácua — foi assim que o §r2
   descobriu que o golden de um PR anterior não exercitava o próprio mecanismo.
4. **Delta de número exibido é declarado.** Todo PR que altera número que chega ao
   usuário declara o sinal (`↑`/`↓`/`=`) e o gate confere. Rebaseline silencioso de
   golden é reprovação.
5. **Escalar é correto.** Corretude > cobertura: na dúvida, escale. Mas escalação
   **não é segura no tier sem LLM** — ver [[A42.l8]].
