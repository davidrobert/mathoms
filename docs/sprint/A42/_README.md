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

## Por que esta sprint existe (e não é lane da A40)

O `_README` da [[A40]] §Fora do sprint declara os achados de E0→E2 explicitamente
**fora dela por camada** ("pertence a `PLAN-data-lineage` ou a uma rodada de
`parse-certify`. Não roteado."). Há um handoff escrito e sem dono. A42 o absorve.

O corte é por **camada**, não por severidade: entra o que é ingestão (E0→E2),
razão (E3/E4), contrato de store/artefato, ou instrumento de certificação. Fora
dessas quatro não entra — ainda que seja P0. Ver §Critério de admissão.

## KR — provabilidade, com duas linhas de contagem

Todo KR aqui é binário e medido por harness existente. Cada um tem uma segunda
linha de contagem porque a métrica óbvia é gamificável.

| KR | Métrica | Instrumento | Anti-Goodhart |
|---|---|---|---|
| **KR-A · fidelidade discriminada** | Todo parser line-oriented emite âncora de linhas de origem; o veredito separa *fidelidade do parser* de *completude da fonte*. `coberto-sem-verificação` cai de 80 | `dev/certify_parse_local.py --compare` | Contar em **duas linhas** — `fidelidade_provada` e `teto_estrutural`. A queda só conta pela primeira: reclassificar vocabulário não é progresso |
| **KR-B · instrumento que não dá verde falso** | Nenhum check que não consegue avaliar desaparece da conta: todo check emite `pass\|fail\|skipped(motivo)` com piso de contagem por check-id; registry de balde do razão com default `não-verificável` | `scripts/validate_cross.py` + `dev/ledger_certify_core.py` | **Prova por mutação**: remover o input do check ⇒ exit ≠ 0. O KR não mede número de checks; mede que a ausência morde |
| **KR-C · identidade sob cobertura redundante** | Nenhum par de grupos do razão da mesma conta *period-free* com chaves de artefato distintas; nenhum artefato onde o sentinela de ausência é indecidível do literal | `dev/certify_ledger_local.py` | Escopo é a classe **latente** nativo↔nativo. O P0 de duplicação cross-documento é KR-B da [[A40]] e **não conta aqui** — senão A42 colhe o trabalho da [[A40.l2]] |
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

## Lanes (12)

| Lane | O quê | Prio | Onda | Dep |
|---|---|---|---|---|
| [[A42.l1]] | Stage de unlock aborta o run inteiro, e o secret dele é inalcançável em deploy limpo | **P0** | 0 | — |
| [[A42.l3]] | Harness de certificação: falso-verde para dentro | P1 | 1 | — |
| [[A42.l4]] | Check que não consegue avaliar evapora em vez de virar `skipped` | P2 | 1 | — |
| [[A42.l2]] | Parsers line-oriented: âncora de fidelidade + supressão vira verdict do gate | P1 | 1 | [[A42.l3]] |
| [[A42.l6]] | Contrato do store: política de escopo, retenção de órfão e validação de artefato | P1 | 2 | [[A42.l5]] |
| [[A42.l7]] | Registro de custo de LLM é fonte de verdade que perde row e vaza filename | P1 | 2 | [[A40.l19]] |
| [[A42.l5]] | Chave de agrupamento do razão carrega o período do documento | P1 | 2 | [[A40.l2]] |
| [[A42.l8]] | Mês vazio por falha de extração conta como mês documentado | P1 | 2 | [[A40.l15]] · [[A40.l11]] |
| [[A42.l9]] | Vocabulário do checksum de fatura: separar dívida acionável de teto estrutural | P1 | 3 | [[A42.l2]] |
| [[A42.l10]] | Misclassificação na classificação amplifica o carrier de duplicação | P1 | 3 | [[A41.l2]] |
| [[A42.l11]] | Enforce do checksum cross-source fatura ↔ débito de pagamento | P1 | 3 | [[A40.l2]] |
| [[A42.l12]] | Estado de extração do documento: predicado único e stages derivados do registry | P2 | 3 | [[A42.l2]] |

Capacidade decidida: teto de 14 lanes. **Fechou em 12** — 11 na abertura, mais a l12
nascida do **split da l6** por decisão do `senior-cto` (eram dois agregados empacotados,
com bloqueio e reversibilidade distintos). Os slots restantes não foram preenchidos de
propósito: padding para bater um número é a forma mais barata de Goodhart num plano.

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
**mensurável** depois da [[A42.l3]], porque a perna de volume do gate
anti-regressão está morta hoje. Instrumento primeiro é pré-condição do critério de
saída, não preferência.

**Onda 0 — parar a sangria** ([[A42.l1]]). Solo. Não é instrumento e não compartilha
arquivo com a Onda 1; o gate dela é **externo** (o defeito não morde no dogfood, onde
o arquivo de senha existe e o run completa — morde em deploy limpo e no segundo
usuário). Fica fora da Onda 1 para não competir por pickup com instrumento nem
sugerir bloqueio que não existe.

**Onda 1 — instrumento** ([[A42.l3]] e [[A42.l4]] livres; [[A42.l2]] atrás da l3).
**Não são disjuntas — partição declarada.** A l4 é solo em arquivo. A l2 e a l3 tocam
ambas `dev/certify_parse_local.py`, e no mesmo ratchet: a **l3 é a dona do arquivo** e
entrega a cláusula que a l2 precisa — cláusula que agora está no **critério de aceite da
l3**, não só na prosa da l2. Uma versão anterior deste plano afirmava disjunção aqui: era
falso, e duas lanes P1 reescrevendo o mesmo ratchet em paralelo é exatamente o cenário que
a onda diz evitar.

**Onda 2 — identidade, contrato e base** ([[A42.l5]] → [[A42.l6]]; [[A42.l7]] e
[[A42.l8]] independentes entre si). A l5 e a l6 são **sequenciais**, não paralelas: o
guard "por expectativa" da l6 conta grupos cujo keying a l5 muda, e o escopo da listagem
da l6 muda o conjunto de pernas do merge da l5 — logo o `titular` que vai ao hash. A l8
entra na fila de rebaseline do snapshot do view-model, compartilhada com a [[A40.l15]].

**Onda 3 — o que depende de terceiros** ([[A42.l9]], [[A42.l10]], [[A42.l11]],
[[A42.l12]]). A l12 está aqui, e não na 2, porque depende do enum de verificabilidade que
a l2 cria: escrever o predicado contra o mundo de dois estados e receber o terceiro depois
acenderia o selo de qualidade sobre conservação não provada — o falso-verde da tese,
produzido pela lane que existe para matá-lo.

**Amarra obrigatória das dependências cross-sprint.** Seis lanes dependem de lane de
outra sprint. Na promoção, **re-ler a disposição de cada dependência**, com **três**
ramos — não um:

1. dependência `cancelled` ⇒ a lane A42 **absorve o escopo** e declara a absorção no
   corpo. Sem isso, uma A40 que fecha `done` com [[A40.l15]] `cancelled` deixa a
   [[A42.l8]] esperando um evento que nunca chega;
2. dependência `shipped` ⇒ a dependência é morta, remover e anotar o PR;
3. dependência ainda `open`, **carregada por plano vivo** — caso real da [[A40.l2]] sob
   o plano de report-trust, e o ramo **mais provável** dos três: a lane sobrevive ao
   fechamento da sprint, porque a cláusula 4 do §Critério de admissão diz que plano é dono
   de tese além da sprint. Nesse ramo a lane A42 permanece `blocked` e a condição de
   destravamento é o **merge do PR nomeado**, não o fechamento da A40. A versão anterior
   desta amarra só cobria o ramo 1.

Precedente: cláusula de entrega parcial da [[A40.l27]].

## Relação com a A39

A [[A39]] tem a mesma tese (`ingest-trust`) e nunca foi fechada: 12 de 13 lanes
`shipped`, `sprint_status: candidate` desde 2026-07-23. Manter duas sprints
`candidate` com a mesma tese, sobre os mesmos arquivos, criaria as duas fontes de
verdade que o roteamento desta sprint existe para evitar. **A A42 abre no mesmo PR
que flipa a A39 para `done`**, com disposição item a item:

| Resíduo da A39 | Blocker declarado | Disposição |
|---|---|---|
| [[A39.l3]] c2 (opt-in de fatura) + [[A39.l8]] (parser determinístico) | A §Deferido da A39 (escrita 2026-07-23) os declara bloqueados na identidade do checksum | **Nada a adotar — já entregues.** A [[ADR-342]] §Emenda **2026-07-24** decidiu a identidade (por seção) e ligou os dois parsers com o corpus fechando a cent, zero falso-fire. O deferimento durou um dia; a §Deferido da A39 nunca foi reescrita. A [[A42.l9]] atende **PC12**, que é defeito próprio e posterior (vocabulário: `faltando` conflaciona dívida com teto em 31 de 41 documentos) — **não** o resíduo da A39 |
| [[A39.l6]] residual (traço positivo do checksum) | — | **Adotado** por [[A42.l3]] — o traço já é emitido e escrito no schema; o harness não o lê |
| §Deferidos — propagação E2→E5 e selo de qualidade, gated por [[ADR-345]] | ADR `Roadmap`, adoção deferida | **Gatilho registrado** por [[A42.l2]]. A condição de retomada da nota é "quando um achado de revisão demonstrar número de origem degradada chegando ao usuário sem sinal" — o §r2 é esse achado. Registrar o gatilho é docs-only; **promover a nota exige design** ([[ADR-358]]) e não é escopo desta sprint |
| [[A39.l13]] (`planned`) — re-route da classificação pelo choke-point de LLM | — | **`cancelled`** por duplicação: é a [[A41.l2]], que já é dona dos mesmos arquivos |

Efeito no inventário: o conjunto `candidate` vai de {A39, A41} para {A41, A42} —
**não cresce**, e os resíduos deferidos ganham destino nomeado. Precedente exato: a
própria A39 fazendo isso com a cauda da A38.

## Fora do sprint (disposição explícita)

Sem esta seção, o silêncio lê como "cobrimos os 74 achados". Não cobrimos — e o
corte é declarado por **classe**, não como "cauda".

**Roteado para lane ou plano que já é dono do arquivo** (a regra é: quem possui a
superfície possui o achado):

| Achado | Destino | Motivo |
|---|---|---|
| Duplicação cross-documento do razão (P0, ~19% da receita) | [[A40.l2]] | É o KR-B da A40, com instrumento shipado ([[A40.l1]]) e escopo em 5 PRs. A trilha do próprio achado aponta para lá. **Ressalva registrada:** o §r4 mediu que **4 dos 5 desenhos de fix foram eliminados**, e o desenho sobrevivente (colapsador por transação, chave provenance-free day-exact) **não está escrito** nos PRs atuais da l2 — o P0 tem dono e não tem fix escrito. Isto é aviso à A40, não escopo da A42 |
| Débito de âncora estável de override manual + eixo member-level do lineage em zero | [[A40.l2]] PR3 | Mesma causa; a trilha de ambos diz "não abrir lane" |
| Limiar de confiança + canal de pausa inalcançável | [[A40.l21]] | A trilha diz "acoplar a A40.l21" |
| Decisão registrada pelo dono descartada da única seção que responde "o que fazer" (**P0**) | [[A40.l10]] | Ver §Nota sobre o P0 de entrega abaixo |
| Termo de marca metodológica vazando para o índice web | [[A40.l7]] | l7 já é dona do YAML de layout e do shell; alcança o usuário hoje |
| Projeção de exclusão inerte por construção (override do dono sem efeito monetário) | [[PLAN-pipeline-review-r2]] Onda D | É a escalação de um achado que já vive lá, agora de `consistência` para `correção` |
| Meta de independência conservadora descartada pelo adapter · cascade de custo de imóvel não plumbada · truncamento silencioso do bloco denso do parecer · alíquota ancorada em exercício incompleto | [[A40]] / [[PLAN-pipeline-review-r2]] | Eixos com dono ativo (l8/l25/l28/l30) |
| YAML de layout que não governa o render · gate de chart que derruba a seção inteira | [[A40.l7]] | l7 já possui essas superfícies |
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

## Gatilho de promoção a `current`

Evento, não calendário: **[[A40]] → `done`**. Enquanto a A40 é `current`, duas
sprints `current` são hard fail em `build_doc_index.py --check`, e as 11 lanes
nascem `planned` — **escritas, não autorizadas para pickup**. Padrão [[A41]].

## ADRs exigidas antes de PR de implementação

Política do CLAUDE.md: task P0/P1 com escopo arquitetural abre ADR `Proposto` antes
do PR de implementação.

| Lane | Forma | Por quê |
|---|---|---|
| [[A42.l2]] | **Emenda datada à [[ADR-342]]** — não ADR nova | Mesma decisão com o eixo refinado (separar fidelidade do parser de completude da fonte). Precedente: a emenda de 2026-07-27, também nascida desta skill |
| [[A42.l5]] | Corolário da emenda [[ADR-354]] | O repo já tem a definição period-free certa e agrupa pela errada |
| [[A42.l6]] | Emenda [[ADR-291]] | Política de escopo do store: listagem e leitura discordam. Toca também [[ADR-278]] e [[ADR-212]] |
| [[A42.l12]] | **ADR nova** `Proposto` | Onde mora o predicado único de extração é decisão de **boundary** (`backend/` ↔ `pipeline/`) — uma emenda de política de escopo não pode ser o veículo dela |
| [[A42.l8]] | **ADR nova** `Proposto` + emenda datada à [[ADR-306]] D3 | Piso de publicação por classe de métrica e dimensionamento conservador são **regra nova**; a política vigente decide o divisor, nunca piso nem conservadoria. A emenda aponta para a ADR nova |
| [[A42.l1]] | **ADR nova** `Proposto` | Provisionamento de secret em tenant limpo — co-design `senior-cto` + `sre-devops` |
| [[A42.l7]] | Coordenar com [[ADR-357]] §7 | Migration + contrato de coluna; serializada atrás de [[A40.l19]] na cadeia alembic |

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
