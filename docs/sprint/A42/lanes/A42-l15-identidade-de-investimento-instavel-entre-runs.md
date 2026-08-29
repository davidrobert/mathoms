---
id: A42.l15
type: lane
title: "Identidade de investimento é hash de campos que o extrator LLM reescreve"
sprint: A42
status: in_progress
priority: P0
branch_slug: a42-l15-identidade-de-investimento-instavel-entre-runs
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-271]]"
  - "[[ADR-137]]"
  - "[[ADR-384]]"
  - "[[ADR-400]]"
  - "[[ADR-406]]"
tags:
  - type/lane
  - sprint/a42
  - status/in-progress
  - priority/p0
  - area/dados
  - area/pipeline
---

# A42.l15 — `identidade-de-investimento-instavel-entre-runs`

> **Origem:** `LC6-02` da rodada unificada **U2** ([[LEDGER-CERTIFY-active]] §r6,
> merge `47970706`).

## O medido

Dois runs `completed` do mesmo workspace, mesmo corpus documental:
`investimentos_consolidados` tem 61 ids num run e 60 no outro, com **23 em comum** (38 só-A,
37 só-B) ⇒ **23,5% de estabilidade**. No mesmo par, `property_id` é **100%** estável e
`veiculo_id` é **nulo em todos** os itens.

## Mecanismo, rastreado até o produtor

`pipeline/domain/services/investimentos_dedup.py:101` — `_investment_id` é
`sha256(tipo, normalize_descricao(instituicao), normalize_descricao(descricao))[:16]`.
`normalize_descricao` (`_tx_identity.py:90`) faz lowercase + strip + collapse + sufixo PIX, e
**não colapsa** variação de sufixo societário. Os três inputs vêm **crus do item E1.5** —
saída direta do LLM, **sem passar pelo `institution_catalog` que já existe no DB**
([[ADR-137]]).

## Já refutado — não re-litigue

- A [[ADR-271]] (`Decidido`) **já** declara *"não há identidade estável"* e *"não estável a
  rename de descrição"*, e **rejeitou** o resolver com persistência (§140: *"persistir
  identidade fuzzy-derivada é gravar palpite"*). **Não proponha um.**
- O que é **novo é a classe**: a ADR previu instabilidade entre **anos** (o banco mudou o
  texto do informe). O medido é entre **dois runs do mesmo documento** — o extrator
  reescrevendo a si mesmo. A ADR nunca considerou isso.
- `property_id` é estável por ser **UUID resolvido contra o DB**
  (`db_property_identity_resolver.py`, [[ADR-215]] P2) — categoria diferente, não "campo melhor".
- Severidade é **Alto** e não Crítico porque `rg investment_id backend/app/models/
  backend/alembic/` devolve **zero**: nenhum estado persistido é corrompido.


> ⚠️ **O 4º bullet acima é o único dos quatro que a medição corrigiu** (2026-08-29): o
> inventário estava incompleto. Os três primeiros seguem de pé e **não se re-litiga**.
> `investment_id` **é publicado** como `nao_classificado_itens[].locator` no artefato E5
> entregue ao cliente (`config/schemas/e5_analysis.schema.json:2137`, [[ADR-406]] D5) e
> congelado em `tests/fixtures/dedup/policy_parity_snapshot.json` (21 ocorrências). Não há
> coluna nem FK — o `rg` estava certo; o inventário é que parava cedo.

## Medição de abertura da lane — 2026-08-29, runs `c97b97c2` (U1) × `79a61e33` (U2)

Controle executado: **nenhum commit em `main` tocou o caminho de
classificação/consolidação/dedup/prompt entre os dois runs** (`git log --since` sobre
`asset_classifier.py`, `scoring.json`, `investimentos_dedup.py`, `consolidate_baseline.py`,
`_tx_identity.py`, `e15_baseline.py`, `extract_baseline.py` → vazio). O delta é do extrator.

### A rota do registro cai — e é a mudança de desenho desta lane

| chave | estabilidade |
|---|---|
| `(tipo, inst, desc)` — produção hoje | **23,5%** |
| canonicalizando `instituicao` (canonicalizador **hipotético** de sufixo societário) | 27,5% |
| **removendo `instituicao` inteira** | **29,9%** |

29,9% é **teto**, não estimativa: toda canonicalização é função daquela coordenada, colapsar
chaves só pode **aumentar fracamente** `|A∩B|/|A∪B|`, logo a função constante (remover o
campo) é o supremo. Um canonicalizador **perfeito** deixa ~70% churnando.

**E o resolver que existe no repo entrega ~0pp, não 27,5%.** Executado contra o catálogo real:

| forma medida | code resolvido | no catálogo? |
|---|---|---|
| `BANCO C6` / `C6 BANK` | `bancoc6` / `c6bank` | não / **sim** |
| `XP INVESTIMENTOS` / `XP INVESTIMENTOS CCTVM S/A` | `xpinvestimentos` / `xpinvestimentoscctvmsa` | **sim** / não |
| `ITAU UNIBANCO` / `ITAU UNIBANCO S.A.` / `Itaú` | `itauunibanco` / `itauunibancosa` / `itau` | não / não / **sim** |

**Cada par medido resolve para codes diferentes** — o hash continua churnando. A afirmação
do registro de que a rota *"resolve os dois exemplos medidos"* é falsa.

**E a rota é vetada em substância pela [[ADR-400]]** (`Decidido` 2026-08-19). §Decisão 1:
*"`instituicao` **sai da entrada** do classificador"*; §Contexto: sua forma canônica é
*"**propriedade de outro subsistema**"* e um renome lá *"reclassifica ativo no nosso — sem
diff, sem revisão e sem sinal"*; §Consequências: *"**A instituição deixa de mover número**"*.
A ADR fala do classificador; a extensão para a **chave de identidade** é *a fortiori* —
identidade é superfície mais durável que classificação.

### Onde a churn mora — `descricao`, não `instituicao`

86 itens de `baseline_patrimonial` pareados pela âncora `(cpf, ano, valor_brl)` → 72 pares 1:1.

| campo | o prompt E1.5… | divergem/72 |
|---|---|---|
| `secao` | **enumera** os 2 valores | **0** |
| `categoria_hint` | **enumera** os 7 | 1 |
| `instituicao` | diz "código canônico", **não lista** | 23 (32%) |
| `codigo` | dá exemplo, **não fixa forma** | 26 (36%) — `01`→`07-01` |
| `membro` | diz "key canônica", **não lista** | 28 (39%) |
| `descricao` | diz "como consta na declaração" | **40 (56%)** |

### O mecanismo, no grão do item — e `instituicao` é `None` nele

Mesmo ativo (US$ 6.524,00 = R$ 34.433,67):

- U1: **1 entry**, `{'2025': …, '2024': …}`, desc `'U$ 6524,00 - DEPOSITO EM MOEDA ESTRANGEIRA MANTIDA NO BRASIL'`
- U2: **2 entries** — `'U$ 6524,00'` `{'2025'}` + `'…MANTIDA EM BRASIL'` `{'2024'}`

`NO BRASIL` → `EM BRASIL` mais truncagem ⇒ hashes distintos ⇒ **o merge cross-year da
[[ADR-271]] falha**. A entry do ano corrente perde a keyword `"moeda estrangeira"`
(`asset_classifier.py:49-55`) e cai em `Outros`. **A rota do registro é inerte sobre toda
esta cadeia.**

### O efeito publicado — Σ conservado, distribuição não

| | U1 | U2 |
|---|---|---|
| `Internacional` | R$ 34.857,23 | **R$ 423,56** |
| `Outros` | R$ 52.487,13 | **R$ 86.920,80** |
| `nao_classificado_pct` | 3,93% | **6,51%** |

Demais classes idênticas ao centavo. **Totais publicados idênticos ao centavo**
(`liquido` 3.648.718,59 · `bruto` 3.879.177,72 · `investivel_financeiro` 1.311.003,45)
⇒ **não há inflação de patrimônio**. É redistribuição com Σ preservado — a classe que a
[[A40.l82]] documenta como cega aos invariantes de conservação, e que o próprio
`e5_analysis.schema.json:2137` nomeia: *"migração entre baldes preserva Σ, então nenhum
check de conservação alcança a classe"*.

### O dano de gate, remedido

O registro afirma que *"as duas pernas HARD disparam"*. Executadas sobre os snapshots reais:
**U1→U2** dispara só `_reclassificacao_regression` (`Internacional <-> Outros +2,58pp`);
`_identidade_regression` **não** (instituições **subiram** 18→24). **r8→U1** é o inverso: só
`_identidade_regression` (`24 → 18`, posições 61→61). A contagem oscila **24 → 18 → 24** com
o corpus parado ⇒ dispara em **todo par consecutivo, por perna diferente a cada vez** — o
operador lê duas causas distintas para um fenômeno só. E `_identidade_regression` é
**unidirecional** (`c_inst < b_inst`), cega em metade do ciclo. Consequência de desenho:
**consertar a chave não é observável nessas pernas**; a perna certa compara o **conjunto** de
`investment_id` (`|A∩B|/|A∪B|`), não totais.

## Rota — a âncora que a própria [[ADR-271]] §147 deferiu, e que hoje existe

A [[ADR-271]] §140 rejeitou **persistir identidade fuzzy-derivada** — e continua rejeitando.
§141 apenas **adiou** *"estender extrator LLM E1.5 p/ capturar CNPJ"*, e §147 nomeia o `PR3`:
*"extração de CNPJ/conta no E1.5 como chave estável a rename"*. Em 2026-08-12 a [[A40.l40]]
(#1404) entregou `institution_catalog.cnpj_raiz` + `cnpj_raiz_to_code()`. **A infraestrutura
que não existia em 2026-05-29 existe.** Extrair âncora declarada no documento **não é**
persistir palpite: §140 permanece intacta.

**A chave usa a raiz do CNPJ lida do documento, nunca o code do catálogo.** É o que mantém a
[[ADR-400]] intacta: um renome no catálogo não pode mover o hash porque o catálogo não entra
nele. O catálogo serve só a **exibição/cobertura**.

### Viabilidade da âncora — medida, porque a objeção "frágil" da §141 é testável

| | U1 | U2 |
|---|---|---|
| itens financeiros (por `categoria_hint`) | 67 | 67 |
| **com CNPJ na `descricao`** | **37 (55%)** | **25 (37%)** |

24 raízes distintas aparecem no texto; **6 estão no `institution_catalog`** (28 cadastradas).
Duas leituras, ambas operantes: a âncora **existe em ~metade** dos itens — muito acima do
`numero_contrato` (§Armadilha A) e longe de universal, logo a cascata **precisa de degrau de
recusa**, não de fallback mudo; e o extrator **está descartando a âncora** (55% → 37% no mesmo
corpus) porque ninguém a pede como campo.

## Armadilhas medidas — cada uma já matou uma entrega neste repo

**(A) Perna forte sem produtor é inerte, e o agregado irmão prova.**
`dividas_dedup.py:109-113` já tem a cascata `numero_contrato` ⊳ `(tipo, credor, desc)` com o
comentário certo. `rg numero_contrato` → **só o schema e o consumidor; zero produtores**.
Nasceu inerte e segue. É a classe que a [[A40.l88]] (#1755) acabou de gatear. **O produtor
entra antes da chave.**

**(B) Bump de `PROMPT_VERSION` sem política de era piora o que veio consertar.** Distribuição
real em `pipeline_artifacts` (stage E1.5a): `NULL` **441** · `1.2.0` **363** · `1.3.0` **55**.
Bumpar para 1.4.0 deixa **804/859 = 93,6%** no vocabulário antigo, e **não há ferramenta**:
`dev/reextract_stale_e2_llm.py` cobre só `E2-llm`, e a [[ADR-311]] D3 põe re-extração
automática em bump **explicitamente fora de escopo**. `_identity_key` compara literal ⇒ a
instabilidade nova seria **permanente**, não transitória.

**(C) `codigo` em forma `GG-CC` quebra dois consumidores em silêncio.**
`wise_fiscal_flags.py:32,35,38` compara `==` contra `"13"`, `"62"`, `"41"`; `06-41` faz o
bloco de flags fiscais de exterior virar `False` **sem warning**.
`db_property_identity_resolver.py:134,168` casa `codigo_rfb` estrito. A [[ADR-400]] mediu 99
itens já em `GG-CC` (1,46%), **todos ano-base 2025** — tendência de alta. **O argumento para
pinar `codigo` não é "codigo é fato"** (a [[ADR-400]] refutou: 48,2% de pureza semântica,
ruído intra-documento) — é que dois consumidores comparam string de 2 dígitos e **falham abertos**.

**(D) A métrica desta lane é gameável a uma linha.** `litellm_client.py:149` tem
`use_cache: bool = False`. Pôr `use_cache=True` no E1.5 leva a estabilidade run-a-run a ~100%
**sem consertar nada** — o merge cross-year continua quebrado, porque anos são documentos
diferentes e chaves de cache diferentes. **Estabilidade run-a-run não pode ser o critério de aceite.**

**(E) Não feche `instituicao` em `Literal`.** A [[ADR-384]] D3 fixa a cascata
`cnpj_raiz → token de nome → needs_review`; enum fechado remove o terceiro degrau e **força**
o falso-match. O molde correto já existe: `pipeline/llm/prompts/apolice.py:38` (escape aberto
+ registro em `notas` + telemetria).

## Escopo — quatro PRs, nesta ordem

- **PR0 — forma no contrato (zero LLM).** `pattern` em `codigo`
  (`e15_baseline_extract.schema.json:25`, hoje `{"type":"string"}`) e forma canônica em
  `instituicao`; reconciliar a grafia `codigo`/`codigo_rfb` com `e16_irpf_full`. Modo `warn`
  antes de `strict`, com cobertura medida.
- **PR1 — produtor da âncora.** E1.5 emite `cnpj_emissor` format-pinned `^\d{14}$` (molde
  `informe_pf.py:129`) + `codigo` na forma do PR0; catálogo injetado via
  `render_institution_catalog` (molde `apolice.py:38`) **para exibição/cobertura, não para a
  chave**. Bump `PROMPT_VERSION` 1.3.0 → 1.4.0 **com a política de era da armadilha (B) no
  mesmo PR**. Regra de formato em `descricao` (*"copie integralmente, sem truncar nem
  parafrasear"*) — é o braço que testa a hipótese.
- **PR2 — a chave.** Cascata `("cnpj", cnpj_raiz)` ⊳ `(tipo, descricao_norm)`, forma de
  `dividas_dedup.py:104-114`. `instituicao` **sai da chave** ([[ADR-400]] §1). Sem âncora
  forte **e** com descrição fraca, `_identity_key` devolve `None` + `review_reason` — nunca
  hash de texto livre (disciplina [[ADR-392]]/[[A40.l70]] portada para investimentos).
- **PR3 — os gates.** Ver §Critério de aceite.

**Forma da decisão: emenda datada à [[ADR-271]], não ADR nova.** O conteúdo é (a) executar o
follow-up que a própria §147 deferiu, (b) registrar que §140 permanece intacta, e (c) registrar
o veto à canonicalização de `instituicao` na chave com a citação da [[ADR-400]] — para a rota
não ser re-proposta na próxima rodada com a mesma medição de +4,0pp. Nada disso supersede a
ADR-271; tudo cabe no seu próprio escopo. **Nenhum id novo é alocado** — em 2026-08-29 seis
sessões da U2 estavam abertas e o teto era 419.

## Critério de aceite

1. **Passo 0, antes de qualquer token de LLM:** medição read-only sobre os **859** artefatos
   E1.5a existentes — `%` de `codigo` fora de `^\d{2}$` e `%` de `instituicao` fora do
   catálogo, **com numerador e denominador**. É falseável e pode **matar a lane barata**: se
   já der ~100% de fecho, a hipótese está errada. (Operacional: exige `MATHOMS_FERNET_KEYS`,
   não só `MATHOMS_FERNET_KEY`.) **Fecho ≠ estabilidade** — o doc tem de dizer isso.
2. **Cobertura de âncora medida no artefato publicado** (padrão `investimentos_cobertura`/
   [[ADR-406]]), não no estado em voo. É o invariante que mata o modo `numero_contrato`.
3. **Recusa em vez de palpite** (unit, zero runs): âncora forte ausente **e** descrição fraca
   ⇒ `None` + `review_reason`. Único invariante sobre a **decisão**, não sobre o número.
4. **Gate de acoplamento** (unit): reprova se `institution_catalog` entrar na derivação de
   `investment_id`. Ancora a [[ADR-400]] na identidade e trava a re-proposta.
5. **Identidade estável entre eras provada por mutação executada** — item de era 1.3.0 e item
   de era 1.4.0, mesma posição, mesmo hash; ou a política de era (B) escrita e implementada.
6. **Não aceitar como evidência** "a estabilidade subiu de 23,5% para X%" medida em mais um
   par de runs (armadilha D). O harness é offline, K≥5 amostras, ≥2 documentos, com
   `secao`/`categoria_hint` declarados **controle negativo** — se eles se moverem, o resultado
   inteiro é inválido.
7. **Rebaselines declarados no PR:** `tests/fixtures/dedup/policy_parity_snapshot.json` (via
   `dev/golden_diff.py` com manifesto) e o snapshot do harness. **Declarar se o run de cutover
   é full ou incremental** — em incremental ([[ADR-080]]/[[ADR-169]]) transcrições velha e
   nova coexistem e o mesmo ativo não funde.
8. `pytest tests -q` **e** `pytest backend/tests -q` verdes — o consolidador tem cobertura nas duas.

## Refutado por medição nesta lane — não re-litigar

- **A [[ADR-271]] §Identidade declara `descricao_norm` = lower + strip acento + collapse +
  remove sufixo numérico de conta/agência.** `normalize_descricao` (`_tx_identity.py:90`)
  implementa só lower + collapse (+ sufixo PIX). **O gap de contrato é real; o impacto é ZERO**
  neste corpus — implementar os dois passos faltantes deixa a estabilidade em **23,5%,
  idêntica**. E `normalize_descricao` é compartilhada com `cross_document_collapser.py:138` e
  `collapse_precondition.py:150` (âncora de override do dono): **mudá-la globalmente orfana
  overrides**. Se for conformada, que seja num normalizador local do baseline.
- **`membro` churnar 39% NÃO é defeito vivo — retratado pelo autor da medição.**
  `investment_id` não contém `membro`, e `consolidate_baseline.py:417-429` (`_resolve_member`)
  canonicaliza CPF-first ([[ADR-267]]). Medido: `proprietario` diverge em **0 de 42** pares, e
  os 3 itens que caem em `titular` são exatamente os **3 sem `cpf`**. A churn é absorvida antes
  de tocar o agrupamento. **Não roteie para a [[A40.l80]]** — ela é consumidora da resolução.
  ⚠️ **O escopo desta retratação é a CHURN entre runs, não `membro` em geral.** A [[A40.l96]]
  (`in_progress`, P0, #1823) mediu que `membro` **por posição** é defeito vivo e que *"o fix é
  no consolidator E4"* — caminho **disjunto** deste (`investments_consolidator.py:328-333`,
  sobre investimentos de origem E2; aqui é o baseline E1.5/E1.5c). As duas leituras convivem:
  a instabilidade **entre runs** é absorvida pela cascata CPF-first; a **cobertura** do campo
  não é. **Datum desta lane que serve à l96**, no caminho que ela não cobre: em
  `baseline_patrimonial` o `membro` sai em 6 formas (`david_robert`, `david`,
  `mariana_teixeira_ferreira`, `david_robert_camargo_de_campos`,
  `david_robert_camargo_ferreira_campos`, `titular`) e no run U2 **zero** itens casam com uma
  key canônica do registro de membros (`david`/`mariana`/`theo`) — é a mesma tese de
  **espaço de chave** que a l96 §234 levanta, medida no ramo E1.5.
- **Cardinalidade do codomínio não explica a churn.** `categoria_hint` tem 7 valores distintos
  (7/7 nos dois runs) e churna **1**; `membro` tem 6/5 — cardinalidade **menor** — e churna
  **28**. E `valor_brl` tem cardinalidade 61, **não é enumerado**, e é **100% estável**
  (verificado fora do pareamento: conjunto 61/61, Σ idêntico, e `resumo.total_ativos`/
  `total_passivos`/`patrimonio_liquido` idênticos ao centavo). O que separa não é o tamanho do
  codomínio: é o prompt pinar uma **superfície de renderização única**, por enum (`secao`,
  `categoria_hint`) **ou por regra de formato** (`valor_brl`: *"STRING decimal com ponto e 2
  casas"*; `cpf`: *"11 dígitos"*). Zero exceções nos 6 campos. **Consequência de desenho:
  `descricao` não precisa de enum — precisa de regra de formato.**
- **Cortar a cauda `CNPJ …` da `descricao` leva o combinado a 60,4% e é veneno.** Colapsa a
  população de 61 para 35 chaves (43%): compra estabilidade destruindo discriminação — o
  falso-positivo que a [[ADR-271]] §139 rejeitou (*"some patrimônio real"*). Pior: a cauda **é
  a âncora** que a §147 pediu para extrair. **60,4% não deve ser citado como alvo.**
- **Determinismo por config já está esgotado.** `extract_baseline.py:300-311` já passa
  `temperature=0.0` e `seed`; `pipeline/llm/deterministic_extraction.py` documenta que `seed`
  **não é suportado** pelo provider e é descartado antes da API. Não há sampling a desligar.
  Sobram duas frentes reais: o reask do Instructor (`max_retries=2`) **muda o prompt** e não é
  instrumentado, e o model default é **alias, não snapshot datado**.

## Rastro em lane alheia — não é escopo desta lane

A [[A40.l50]] (`open`, P1) fixa em prosa `Internacional = R$ 34.918,47 (4,19% da carteira)`.
No run corrente são **R$ 423,56**. A premissa dela **não reproduz**, e a causa é esta lane.
Quem pegar a l50 precisa re-medir antes de agir sobre aquele número.
