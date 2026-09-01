---
id: A42.l15
type: lane
title: "Identidade de investimento é hash de campos que o extrator LLM reescreve"
sprint: A42
status: shipped
ship_pr: 1939
ship_date: "2026-09-01"
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
  - status/shipped
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

## Rota ENTREGUE — a âncora do §147 da [[ADR-271]], executada em #1939

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

## Harness ENTREGUE — PR #1919 (`b11d5bfd`), 2026-08-31 · e ele corrige a Armadilha (B) pelo campo medido

`dev/measure_e15_identity_stability.py`. Replay offline de artefatos `E1.5a`: agrupa por
`(documento, era)`, exige K≥5, e mede `|A∩B|/|A∪B|` sobre o conjunto de `investment_id`
produzido pelo **caminho real** (`consolidate_from_itens` ⊳ `dedup_investimentos_consolidados`).

### Baseline medido — 28 grupos válidos, 19 documentos, K até 38

⚠️ **Números de corpus vivo — rode o harness, não releia a tabela.**
Nos documentos com carteira substantiva (~23–25 identidades), a estabilidade fica entre
**22,43% e 53,13%**, o que **contém** os 23,5% da abertura e os põe num intervalo com
denominador. Exemplo de um mesmo documento ao longo das eras: `1.0.0` 35,48% · `1.1.0`
37,37% · `1.2.0` 53,13% · `1.3.0` 22,43%. ⚠️ **A era move a estabilidade**, então ela é
**confundidor** de qualquer medida antes/depois — comparar eras diferentes não mede fix.

### Três estados, porque dois colapsam causas distintas

A 1ª execução real reprovou o desenho: `sem investimento` (documento sem ativo financeiro
nenhum — 14 grupos) saía rotulado como **falha de controle negativo**, e o operador leria
alarme onde não há nada a medir. É a patologia que a própria lane registra em §O dano de
gate. Hoje são três: **medido** · **CONTROLE MOVEU** (5 grupos, resultado suprimido —
`estabilidade_pct` devolve `None`, não um número anotado) · **SEM INVESTIMENTO**.
E o relatório carrega a **cardinalidade média**: `100%` sobre 1 id não é `100%` sobre 25,
e o corpus tem exatamente esse caso (`~1.0 ids`, 7 pares byte-idênticos).

### Correção da §Armadilha (B) — ela mediu a COLUNA, e a coluna é cega a 47% do corpus

A distribuição que a armadilha cita (`NULL` 441 · `1.2.0` 363 · `1.3.0` 55) é a da **coluna**
`pipeline_artifacts.prompt_version`. Medido 2026-08-31 nos 836 artefatos `E1.5a`:

| fonte | distribuição |
|---|---|
| **coluna** `prompt_version` | `NULL` 436 · `1.2.0` 330 · `1.3.0` 70 |
| **payload** `prompt_version` | `1.0.0` **154** · `1.1.0` **190** · `1.2.0` 380 · `1.3.0` 70 · `NULL` **42** |

Divergem em **394/836 = 47,1%**, e **sempre no mesmo sentido**: coluna `NULL` onde o payload
sabe a era. ⚠️ **Corpus vivo, como o do Passo 0** — re-medido em 2026-08-31 23h (idêntico),
mas não releia estes números: rode `dev/measure_e15_identity_stability.py` e o comparador de
coluna×payload de novo. **Duas eras inteiras — `1.0.0` e `1.1.0`, 344 artefatos — são invisíveis na
coluna.** A conclusão da armadilha **sobrevive** (recomputado no payload, 766/836 = **91,6%**
ficariam em vocabulário antigo após um bump; era 93,6%), mas a **política de era do PR1 não
pode selecionar por essa coluna** — ela não distingue três das cinco eras. O harness agrupa
pelo payload por isso.

## Armadilhas medidas — cada uma já matou uma entrega neste repo

**(A) Perna forte sem produtor é inerte, e o agregado irmão prova.**
`dividas_dedup.py:109-113` já tem a cascata `numero_contrato` ⊳ `(tipo, credor, desc)` com o
comentário certo. `rg numero_contrato` → **só o schema e o consumidor; zero produtores**.
Nasceu inerte e segue. É a classe que a [[A40.l88]] (#1755) acabou de gatear. **O produtor
entra antes da chave.**

**(B) Bump de `PROMPT_VERSION` sem política de era piora o que veio consertar.**
⚠️ **Os números deste parágrafo saem da COLUNA `prompt_version`, que é cega a 47% do corpus
— ver §Harness ENTREGUE.** A conclusão sobrevive (91,6% no payload); a **seleção** por essa
coluna, não. Distribuição da coluna (stage E1.5a): `NULL` **441** · `1.2.0` **363** ·
`1.3.0` **55**. Bumpar para 1.4.0 deixa **804/859 = 93,6%** no vocabulário antigo, e **não há ferramenta**:
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

## Passo 0 EXECUTADO — 2026-08-30 · e ele **corrigiu duas coisas que eu mesmo publiquei**

`dev/audit_e15_vocab_closure.py` (read-only, zero token de LLM; núcleo puro em
`tests/dev/test_audit_e15_vocab_closure.py`). **900 artefatos, zero falha de decifragem.**

> ⚠️ **Retratação — a 1ª publicação deste Passo 0 (#1837) misturou duas populações.**
> `E1.5a` é a extração **por documento**; `E1.5`/`extract_baseline` são o **agregado
> consolidado, que re-emite os mesmos itens**. Somá-los conta cada item duas vezes e ainda
> dilui a taxa da extração com a do agregado. Os números certos, por população:

| população | itens | `codigo` fora de `^\d{2}$` | `instituicao` fora do catálogo |
|---|---|---|---|
| **`E1.5a` — extração (é este o número)** | **7.039** | **131 = 1,86%** | **2.295/5.218 = 44,0%** |
| `E1.5` (agregado) | 3.286 | 99 = 3,01% | 1.116/2.474 = 45,1% |
| `extract_baseline` (agregado) | 3.820 | 32 = 0,84% | 1.199/2.793 = 42,9% |
| ~~soma (o que o #1837 publicou)~~ | ~~10.859~~ | ~~163 = 1,5%~~ | ~~3.494/8.011 = 43,6%~~ |

A soma **não descrevia nenhuma das três**. O instrumento agora separa por população e o
headline é sempre a extração — com teste que mata a mutação que reintroduz a soma.

> **Os números acima são de um corpus VIVO** e envelhecem: o run `3a5b9c7d` (2026-08-30
> 08:47) entrou entre a medição e o closeout e levou a extração a 131/7.126 = **1,84%** e
> 2.329/5.285 = **44,07%** — numerador de `codigo` **idêntico**, denominador maior. Não
> releia a tabela: rode `python3 dev/audit_e15_vocab_closure.py`.

### O `instituicao` sobrevive à correção; a conclusão do `codigo` **não**

`instituicao` é robusto: **42,9%–45,1% em todas as populações**, e as formas fora do
catálogo são variantes de instituições **que já estão nele** — `BANCO SANTANDER`,
`ITAU UNIBANCO S.A.`, `BANCO C6`, `XP INVESTIMENTOS CCTVM S/A` contra os 42 codes que
incluem `santander`, `itau`, `c6bank`, `xpinvestimentos`. **Não é cobertura faltando; é
alias faltando** — a metade de baixo resolve-se **no catálogo**, não no resolver.

**O `codigo`, não.** Eu escrevi que *"`^\d{2}$` é a forma canônica com 98,5% do corpus"*.
**Está invertido.** Nos 26 pares em que `codigo` diverge entre U1 e U2 (pareados pela âncora
`(cpf, ano, valor_brl)`), **25 têm o 2-dígitos do U1 como o SUB-código do `GG-CC` do U2** —
`02`→`04-02`, `04`→`07-04`, `01`→`02-01`, `11`→`01-11`, `99`→`06-99` — e **zero** o têm como
grupo. Os dois formatos **não são duas renderizações do mesmo valor**: um é estritamente
menos informativo, com o **grupo perdido**. Pinar `^\d{2}$` carimbaria a convenção
semanticamente pobre como a válida, e rejeitaria a completa. **A decisão de forma do PR0
não está tomada** — ela exige ler o documento-fonte, e não o corpus.

### Emenda ao Critério 1 — ele não pode nem matar nem salvar a hipótese

O critério diz que ~100% de fecho **mata a lane barata**. Não mata, e o motivo é estrutural:
**`codigo` não entra em `_identity_key`** (`investimentos_dedup.py:91-98` = `(tipo, inst,
desc)`). A única porta é indireta (`codigo`→`_classify_investimento`→`tipo`), e ela foi
medida: fixar `tipo` move a estabilidade **de 28 para 28 chaves idênticas — delta 0 pp**.
O critério 1 vale como **medição de contrato**, não como gatilho de kill da hipótese de
identidade. Quem o executar não deve concluir nada sobre estabilidade a partir dele.

⚠️ **Fecho ≠ estabilidade.** Um extrator pode ser 100% fechado e ainda alternar entre dois
codes do catálogo entre runs.

## O que falta em cada PR — levantado e verificado em 2026-08-30

**Passo 0 — feito.** Resíduo: existe instrumento canônico vizinho
(`dev/measure_schema_drift.py`, com `--gate`/`--days`/`--paths`) cujo **exit code do `--gate`
não consulta `is_go`** (janela vazia ⇒ exit 0), contra a [[ADR-409]] §B. **Dono é o
§Deferimento da [[A40.l58]]**, não este PR — mas sem isso o `--gate` não pode ser fiado.

**PR0 — três bloqueios, e a perna `instituicao` sai.**
1. **Decidir a forma de `codigo` exige o documento-fonte** (acima). O corpus não decide:
   2025 emite as duas formas, 2023–2024 só a de dois dígitos. Custo medido pelo predicado do
   gate: `^\d{2}$` → **NO-GO** (2 artefatos na janela, e derruba também `e16_irpf_full`, hoje
   0/416 → 36/416); `^\d{2}(-\d{2})?$` → GO, **mas fecha 100% por construção e não pode
   reprovar nada**.
2. **A perna `instituicao` do PR0 morre**: um `pattern` `^[a-z0-9]+$` faria **657 dos 911
   artefatos (72,1%)** passarem a ter ≥1 item em violação — medido isolando o efeito do
   campo. ⚠️ **Correção do que publiquei antes:** os *"85,2% (767/900)"* eram o drift do
   **schema inteiro** com o pattern acrescentado, e portanto incluíam o drift pré-existente
   de outros paths (`valor_brl`/`resumo.*`, pré-`payload_version`) — atribuí à `instituicao`
   um numerador que não era dela. A conclusão não muda; o mecanismo sim. A perna também
   contradiz o PR2 desta lane (*"`instituicao` sai da chave"*) e a [[ADR-400]] §1, e não
   existe warn por campo — `mode_overrides` é per-schema. **Cortar do escopo.**
3. **`additionalProperties: false`** em `e15_baseline_extract.schema.json:23` — abrir espaço
   para `cnpj_emissor` é **pré-requisito duro do PR1** e a lane não o atribuía a ninguém.
   O lado simétrico não bloqueia: `baseline_patrimonial.schema.json` é objeto aberto.

Corrige-se também a premissa `codigo`/`codigo_rfb`: em **bens** é falso (o
`e16_irpf_full.schema.json:279` já usa `codigo`); em **dívidas** é verdadeiro; e o eixo que a
lane **omitia** é que a grafia troca **dentro** do E1.5→E1.5c (`consolidate_baseline.py:558`
grava `codigo_rfb`), lido por comparação estrita em
`backend/app/services/db_property_identity_resolver.py:134,168` — o path que a lane escreve
sem o prefixo `backend/app/services/` **não existe**.

**PR1 — o pino de forma tem de ir também no Pydantic.** `pipeline/llm/schemas/e15_baseline.py`
não tem `pattern` nem `min_length` em `code`/`description`/`institution`/`member_key`, e nem
espelha o `minLength: 1` do JSON schema. Com `mode=warn`, `pattern` só no JSON schema é
**inerte**. O e16 espelha campo a campo; o e15 é a única ponta com drift entre as camadas. E
**nenhum teste schema-valida a saída real de `_output_to_baseline_json`** — só um literal.

> ⚠️ **A segunda metade deste parágrafo caiu na execução do PR0 (2026-08-31) — ver
> §PR0 EXECUTADO.** O teste do produtor real era gap verdadeiro e foi fechado. **O mirror
> de `min_length` no Pydantic, não:** ele é redundante em cobertura e, pior, troca o *modo
> de falha*. O pino de **forma** com normalizador (o `cnpj_emissor` deste PR1) segue de pé —
> a distinção medida está na seção nova.

**PR2 — um bloqueio duro e uma expectativa a corrigir.** `review_reason` **não existe** em
`investimentos_dedup.py` nem em `dividas_dedup.py` (`git grep` vazio): hoje `None` só ocorre
com `desc` vazia e não carrega motivo, então o critério 3 **constrói o mecanismo inteiro**.
E são **duas normalizações, não uma**: colapsar `GG-CC`→`GG` conserta `_classify_investimento`,
mas `codigo_rfb` quer o **sub**código — um conserto quebra o outro em silêncio se
compartilharem nome.

**PR3 — ~~nenhum~~ dois dos cinco gates existem.** Entregues: **gate de acoplamento
(critério 4)** e **harness offline (critério 6)**, ambos sem depender de produtor. Restam
três (critérios 2, 3 e 5), e os três **dependem** do produtor do PR1.

## PR0 EXECUTADO — PR #1909 (`4df49130`), 2026-08-31 · uma das duas pernas caiu por medição

Entregue: `cnpj_emissor` declarado em `e15_baseline_extract.schema.json`
(opcional, `pattern` `^\\d{14}$`) + `tests/test_e15_contrato_ancora_cnpj.py`. **Cortado: a
perna do mirror de `min_length` no Pydantic** — pelas duas medições abaixo.

**A precondição do PR1 era real e foi provada, não suposta.** Com o schema pré-PR0,
um item carregando `cnpj_emissor` devolve *"Additional properties are not allowed"*:
`additionalProperties: false` tornava o produtor da [[ADR-271]] §147 uma mudança
impossível de mergear sozinha. Risco de declarar: **zero dos 7.213 itens `E1.5a`** do
corpus carregam qualquer chave fora das declaradas, logo é puramente aditivo.

### O mirror de `min_length` no Pydantic **morre** — redundante E nocivo

**Redundante.** `validate_e15_output` já cobre os três campos, um a um:
`e15.item.empty_code` (`validators.py:454`), `e15.item.empty_description` (`:462`),
`e15.item.missing_member_key` (`:483`), todos com teste em
`test_validation_issues_e1_e15_e2llm.py`. Cobertura que o mirror acrescenta: **nenhuma**.

**E não é o mesmo constraint noutra camada — é outro raio de dano.** `PatrimonialItem` é o
`output_schema` do `service.call` (`extract_baseline.py:305`): falha de Pydantic acontece
**dentro** do Instructor ⇒ reask (`max_retries=2`) ⇒ exaustão derruba **o documento
inteiro**. `validate_e15_output` roda **depois** (`:322-335`) e emite issue **por item** +
`review_reason`. Espelhar converteria sinal item-level em falha document-level —
exatamente o que a [[ADR-292]] recusa, e que
`test_secao_fora_do_vocabulario_avisa_sem_derrubar_o_documento` enforça **neste mesmo
schema**. Medido: `codigo`/`descricao`/`membro` têm **0 vazios e 0 ausentes** nos 7.213
itens, então o mirror é inerte hoje; o único efeito é o modo de falha de amanhã.

⚠️ **A distinção que sobrevive, e que o PR1 precisa:** pino **normalizador** é seguro no
boundary (o `cnpj_emissor` tem `field_validator(mode="before")` que descarta a máscara —
molde `informe_aluguel.imobiliaria_cnpj`, [[ADR-288]]; falhar ali é dado genuinamente
inutilizável). Pino de **vacuidade** não é — não há o que normalizar, só o que rejeitar.
Não leia "o pino de forma vai no Pydantic" como "toda constraint vai no Pydantic".

### O consolidador E1.5c **descarta** chave de item não enumerada — e a lane não atribuía isso a ninguém

`consolidate_baseline.py` monta `entry` **campo a campo** nos **três** sítios que constroem
entry (`:247`, `:327`, `:547`); das chaves do item, só `instituicao` é copiada, e só no
terceiro (`:552-553`). `_aggregate_baselines`
(`extract_baseline.py:144`) passa o item **inteiro** (`all_items.extend`), então o agregado
E1.5 carrega — **o corte é no E1.5c**, entre o produtor e a chave.

**Consequência: o PR1 sozinho nasce inerte para o PR2.** É a [[A42.l15]] §Armadilha (A)
(*"perna forte sem produtor é inerte"*) na direção inversa — produtor sem caminho até o
consumidor. A carreta pertence ao **PR1** (*"o produtor entra antes da chave"*), com unit
sobre item sintético; nenhum dos quatro PRs a nomeava. Classe conhecida: construtor
campo-a-campo perde campo.

### Cobertura da âncora no corpus inteiro — 38,7%, e o denominador NÃO é o da abertura

CNPJ no texto de `descricao` em **2.792/7.213 itens `E1.5a` (38,7%)**. A medição de
abertura desta lane deu 55%/37% sobre **itens financeiros de dois runs**; esta é sobre
**todos os itens de 900+ artefatos**, imóveis e veículos incluídos — onde a âncora não
tem por que existir. **Não são números comparáveis**; o corpus corrobora a ordem de
grandeza e reafirma o §Armadilha: a âncora existe em ~metade dos casos elegíveis, logo a
cascata precisa de **degrau de recusa**, não de fallback mudo. `instituicao` está ausente
em **1.861/7.213 (25,8%)** — `Optional` é a forma certa.

### Drift de schema: a declaração não move o gate

`dev/measure_schema_drift.py --schema e15_baseline_extract.schema.json --all` pós-PR0:
**427/922 = 46,3%, NO-GO** — e **nenhum** dos paths de drift é o campo novo. Os 427 são
`$.itens[].valor_brl` e `$.resumo.*` em payloads v1 (number), drift **pré-existente** que a
própria descrição do schema documenta, com último caso em **2026-06-22**. Campo que nenhum
artefato carrega não pode gerar drift; o `pattern` só passa a medir quando o PR1 emitir.

### Ordem, com o que paraleliza

1. Registro do Passo 0 + emenda do critério 1 *(este PR)*.
2. ~~**PR0 reduzido**~~ **ENTREGUE — PR #1909 (`4df49130`)** — e reduzido de novo na execução: só a
   declaração de `cnpj_emissor` + o teste do produtor real. O mirror de `min_length` foi
   **cortado por medição** (§PR0 EXECUTADO), juntando-se ao `pattern` em `codigo` e à perna
   `instituicao` já cortados no planejamento. **Novo item obrigatório do PR1:** a carreta de
   `cnpj_emissor` no `consolidate_baseline.py` — sem ela o produtor não alcança o PR2.
3. Ler o documento-fonte → decidir `GG-CC` vs `GG` → só então o `pattern`, com o custo de
   fila (e15 + e16) e a política de era juntos.
4. PR1 → 5. PR2 (medido **junto** com o braço de `descricao`; a porta `tipo` dá 0 pp) →
   6. PR3.

**Paralelo desde já:** ~~gate de acoplamento~~ (**feito**) · ~~harness offline~~ (**feito**)
· alias no `institution_catalog` · leitura do documento-fonte. **Não paraleliza:** PR2 depois do PR1; qualquer número de
estabilidade depois do harness (§Armadilha D).

## O bloqueio do PR1 DISSOLVEU — 2026-09-01 · e ele nunca exigiu o documento-fonte

A lane travou o PR1 numa decisão humana: *"ler uma declaração IRPF de origem para decidir
se `codigo` é `GG-CC` ou `GG`"*. **A pergunta estava mal-posta, e o corpus mais o próprio
repo a respondem** — sem ler documento com PII.

**A variável operante não é a forma que o extrator emite; é o que o consumidor lê.** Os dois
consumidores que interpretam `codigo` são indexados por **grupo**:
`_classify_investimento` (`consolidate_baseline.py:746`) ramifica em `'03'/'04'/'06'/'07'/'99'`,
e o catálogo `config/prompts/e15_secoes_rfb_2024.yaml` (fonte declarada: *Manual DIRPF 2025*)
tem chaves de 2 dígitos lidas por `BaselineCatalog.subtipo` com `dict.get` estrito.

### As três opções, medidas — e as duas que a lane considerava perdem

| rota | efeito medido |
|---|---|
| pinar `GG` (2 dígitos) | emite o **subcódigo** (25 de 26 pares divergentes assim) ⇒ 60 itens viram `renda_fixa` em vez de `fundo_investimento`. **Erra em silêncio.** |
| pinar `GG-CC` só no contrato | nenhum consumidor parseia ⇒ os 102 itens seguem no balde genérico. **Inerte.** |
| **`GG-CC` + consumidor lendo o grupo** | 96 itens `07-*` viram `fundo_investimento`; 5 `renda_fixa`; 1 `outros`. **Zero no genérico.** |

Nos **131** itens compostos, **107 (81,7%)** resolvem para subtipos **diferentes** conforme se
leia `GG` ou `CC`, e a leitura por `CC` é demonstravelmente errada: `'07-01'` (fundo) daria
`imovel`; `'04-02'` (ouro) daria `veiculo`. Dois consumidores independentes concordam que o
par da frente é o grupo — o YAML (`"07": fundo`) e o `_classify_investimento` (`grupo == "07"`
→ `fundo_investimento`). **Não é convenção adotada; é o que o repo já afirma em dois lugares.**

### Corpus — 836 artefatos `E1.5a`, 7.213 itens, medido 2026-09-01

⚠️ **Corpus vivo.** Rode as sondas, não releia a tabela.

| | itens | % |
|---|---|---|
| `codigo` plano `^\d{2}$` | 7.082 | 98,18% |
| `codigo` composto `^\d{2}-\d{2}$` | 131 | 1,82% |

Compostos são **ano-base 2025 apenas** — 4,3% dos itens de 2025, **zero** em 2023–2024.
Distribuição: `07-04` 60 · `07-01` 36 · `06-99` 13 · `04-02` 5 · `06-01` 4 · `02-01` 3 ·
demais 1–2. Por `categoria_hint`: `investimento` 102 · `conta_corrente` 16 · `imovel` 4 ·
`veiculo` 3 · `outros` 3 · `poupanca` 2 · `previdencia` 1.

## ENTREGUE — o parse do grupo · `grupo_rfb` (A42.l15)

`grupo_rfb()` em `baseline_item_classifier.py` (domínio, sem ciclo — `pipeline/llm/rfb_codes.py`
já importa de lá). `normalize_grupo` delega; `BaselineCatalog.subtipo` ganha fallback por grupo
**depois** do exato. Cinco mutações executadas (sem parse · lendo `CC` · fallback antes do
exato · fallback inventando resposta · `zfill` removido), cada uma derrubando a perna certa.

**A perna do catálogo move ZERO item hoje** — não há composto na ficha `dividas_onus`, e
`subtipo` só é lido no ramo `PASSIVO` (`consolidate_baseline.py:541`). É **guarda declarada**,
não perna viva; a viva é a de `normalize_grupo`. Registrar isso é a §Armadilha (A) aplicada a
mim mesmo. O fallback é **aditivo** (exato primeiro), então não pode mudar lookup que já
acertava.

### ⚠️ O fix NÃO move a estabilidade — medido, não suposto

A/B hermético pelo harness do critério 6 (monkeypatch do comportamento pré-fix, árvore
intocada), 836 artefatos, 28 grupos medidos:

| | pré-fix | pós-fix |
|---|---|---|
| grupos medidos | 28 | 28 |
| mediana | 29,19% | 29,19% |
| pooled `\|A∩B\|/\|A∪B\|` | **37,68%** | **37,68%** |
| interseção / união | 33.417 / 88.676 | 33.417 / 88.676 |

**Idêntico ao dígito.** O motivo é estrutural: o fix torna cada forma internamente correta,
mas um item que sai `04` num run e `07-04` no outro continua com `tipo` diferente
(`renda_fixa` × `fundo_investimento`) ⇒ mesma perda de interseção. **Este PR é correção de
classificação, não de identidade** — e não deve ser citado como progresso do KR da lane.
O pooled de 37,68% é dado novo: a lane só tinha o intervalo 22,43–53,13% dos documentos com
carteira substantiva.

### Três afirmações da lane que esta medição corrige

1. **"A decisão exige ler o documento-fonte, e não o corpus"** — falso. O corpus + o catálogo
   RFB do próprio repo decidem, e nenhum documento com PII foi aberto.
2. **"`codigo` não entra em `_identity_key` … fixar `tipo` dá delta 0 pp"** — o **delta medido**
   estava certo; a **razão** não. `codigo` alcança sim `_identity_key`, por
   `_classify_investimento` → `entry["tipo"]` no ramo `categoria_hint == "investimento"`
   (`consolidate_baseline.py:581-584`). Os 0 pp eram propriedade daquele par de runs, não
   independência estrutural — e o A/B acima reconfirma 0 pp por um caminho diferente.
3. **A carreta de `cnpj_emissor` é em UM sítio, não três.** Os sítios `:247` e `:328` vivem em
   `consolidate()`, que delega para `consolidate_from_itens` em `:191` assim que `itens[]`
   existe: eles nunca veem item do E1.5 (leem `bens[].grupo` e `imoveis_xlsx`). Só o `:549`
   pode carregar a âncora. A conclusão do PR0 (*"o PR1 sozinho nasce inerte para o PR2"*)
   sobrevive; o escopo da carreta encolhe de três para um.

## O que ainda BLOQUEIA a lane

**Nada humano.** O PR1 pode andar: a forma de `codigo` está decidida por medição (emitir
`GG-CC`; o consumidor já lê o grupo). Resta, tudo técnico e sem dono ainda:

- **PR1 — âncora.** `cnpj_emissor` no Pydantic (`Optional`, `pattern ^\d{14}$`,
  `field_validator(mode="before")` — molde `informe_aluguel.imobiliaria_cnpj`, [[ADR-288]]);
  prompt pedindo a âncora; a carreta no `:549`; bump `PROMPT_VERSION` 1.3.0 → 1.4.0 **com a
  política de era** da §Armadilha (B) — 91,6% do corpus fica em vocabulário antigo e a
  [[ADR-311]] D3 exclui re-extração automática.
- **PR1 (braço da hipótese)** — regra de formato em `descricao`. É o campo que churna 56% e
  o único dos três que está em `_identity_key` sem substituto.
- **PR2 / critérios 2, 3, 5** — dependem do produtor do PR1.
- **Sem bloqueio, sem dono:** alias no `institution_catalog`.

### Resíduo da §Armadilha (C) — roteado para fora da lane

**dono:** `_README` da [[A42]] §Fora do sprint (disposição explícita) — a superfície que
já possui achado cortado por classe. Não vira lane: é **latente, não vivo**, e a regra de
admissão desta sprint reserva lane nova a P0/P1 que alcança o usuário sem dono vivo.

O eixo é **consumidor que compara código de 2 dígitos estritamente e falha aberto**, e
sobraram três pontas depois do #1937:

- `codigo` composto em item `imovel` (4 itens: `01-11` ×2, `01-12` ×2) vai cru para
  `entry["codigo_rfb"]` (`consolidate_baseline.py`), lido por comparação estrita em
  `db_property_identity_resolver.py:134,168`. `'01-11'` e `'11'` são o mesmo apartamento
  em duas grafias. **Latente:** `property_id` é UUID resolvido contra o DB e mede 100% de
  estabilidade.
- `wise_fiscal_flags.py:32,35,38` compara `==` contra `"13"`/`"62"`/`"41"`; `06-41` faz o
  bloco de flags fiscais de exterior virar `False` **sem warning**.
- `dividas_dedup` tem a **mesma exposição** que o critério 4 gateou para investimentos e
  **não** está coberto — limite já declarado no #1916.


## ENTREGUE — PR1 (produtor) + PR2 (a chave) · 2026-09-01

### A medição que decidiu o desenho, e que corrigiu o plano da lane

Variantes de chave sobre o corpus (836 artefatos `E1.5a`, 28 grupos K≥5, controles
parados), com **cardinalidade média junto** — porque comprar estabilidade colapsando
chaves é o veneno que a §Refutado já registra:

| variante | pooled `\|A∩B\|/\|A∪B\|` | card. média |
|---|---|---|
| `(tipo, inst, desc)` — produção até aqui | 37,68% | 9,7 |
| sem `instituicao` | 47,95% | 9,7 |
| **`("cnpj", raiz)` ⊳ `(tipo, inst, desc)` — ENTREGUE** | **61,78%** | 9,7 |
| `("cnpj", raiz)` ⊳ `(tipo, desc)` | 69,20% | 9,4 |
| `("cnpj", raiz, tipo)` ⊳ … | 63,49% | 9,7 |
| subconjunto ancorado sozinho | **91,71%** | 4,5 |

Cobertura da âncora nas entradas consolidadas: **50,9%** (173/340).

**Três coisas que a medição virou de cabeça para baixo:**

1. **A âncora não precisa de token de LLM, e é isso que mata a §Armadilha (B).** O CNPJ
   **já está no texto** da `descricao` em metade dos casos. A cascata lê `cnpj_emissor`
   quando existe e o texto quando não — as duas rotas dão a mesma raiz, logo item de era
   1.3.0 e item de era 1.4.0 **colidem no mesmo hash**. O bump não deixa 91,6% do corpus
   órfão e não precisa da re-extração que a [[ADR-311]] D3 exclui. A política de era
   deixou de ser um problema em aberto: ela é uma consequência do desenho da chave.
2. **`instituicao` FICA na perna fraca — contra o que a lane planejava.** Tirá-la mede
   69,20% (+7,4pp), e o custo em cardinalidade neste corpus é ~3%. Mas
   `test_different_institution_does_not_merge` reprovou: "Tesouro Selic 2029" na XP e o
   da BTG viram **uma** entrada, e R$ 1.000 **somem**. É exatamente o falso-positivo que
   a [[ADR-271]] §139 rejeita. ⚠️ **A minha medição de "custo 0 em cardinalidade" era
   propriedade DESTE corpus** (que não tem o caso), não do desenho — o mesmo erro que
   esta lane já tinha cometido com os "0 pp" do `tipo`. Quem pegou foi o teste, não eu.
   A [[ADR-400]] §1 segue respeitada: o que entra na chave é a string crua do item, nunca
   o code do catálogo — status quo, não acoplamento novo (gate do critério 4, PR #1916).
3. **A âncora não se compõe com `tipo`.** `("cnpj", raiz, tipo)` mede 63,49% contra
   69,20% da âncora sozinha no mesmo braço: `tipo` ainda churna e contamina a perna forte.
   Compor parece mais conservador e entrega menos.

### PR1 — o produtor

`cnpj_emissor` no Pydantic (`Optional`, `pattern ^\d{14}$`, `field_validator(mode="before")`
normalizando máscara — molde [[ADR-288]], pino NORMALIZADOR e nunca de vacuidade);
`_output_to_baseline_json` emite; **a carreta no `:549`**, o único dos três sítios que vê
item do E1.5. Bump `PROMPT_VERSION` 1.3.0 → **1.4.0** com a política de era no comentário.

### PR2 — a chave, e os critérios que ela fecha

Cascata em `investimentos_dedup._identity_key`, âncora em
`pipeline/domain/services/ancora_cnpj.py`. **Oito mutações executadas**, cada uma
derrubando a perna certa: sem a perna da âncora · âncora só do campo · âncora só do texto ·
recusa sem motivo · recusa não-idempotente · `instituicao` fora · raiz de 14 dígitos ·
cobertura contando grupos.

> ⚠️ **O controle é que denunciou uma medição falsa.** As oito mutações rodaram primeiro
> num laço zsh sem `${=T}`, e **todas** devolveram `no tests ran` — inclusive o controle.
> Lidas sem o controle, teriam passado por "oito de oito pegas".

- **Critério 2 — cobertura no artefato publicado.** `investimentos_ancora_cobertura`
  (`total`/`com_ancora`/`por_descricao`/`sem_identidade`/`pct_ancora`), declarada no
  `baseline_patrimonial.schema.json` e emitida pelos **dois** caminhos de consolidação.
  Denominador é o **item**, não o grupo — medida antes do dedup. `com_ancora: 0` publicado
  é o sinal que faltava ao `numero_contrato` da §Armadilha (A).
- **Critério 3 — recusa em vez de palpite.** Sem âncora **e** sem descrição:
  `investment_id` é `None` **e** a entrada carrega `dedup.identidade_sem_ancora` (código
  novo no enum + no `review_reason.schema.json`). Idempotente, porque o dedup roda sobre a
  própria saída. E a perna forte **não depende da fraca**: âncora sem descrição identifica
  — o molde de `dividas_dedup` exige `desc` antes de olhar o contrato, e esse defeito não
  foi replicado.
- **Critério 5 — era não move a chave**, provado por mutação executada: item de era antiga
  (CNPJ só no texto) e o mesmo item de era nova (campo declarado) produzem o mesmo hash
  **e fundem entre si**.
- **Critério 7 — rebaselines declarados.** `tests/fixtures/dedup/policy_parity_snapshot.json`:
  12 de 31 casos mudaram, **todas as contagens `before`/`after`/`dropped` idênticas** (nenhum
  merge ganho ou perdido), campos que diferem são só `investment_id` e `review_reasons`, e os
  19 casos `imovel::` ficam intactos. É a única baseline do repo que carrega `investment_id`;
  o harness não guarda snapshot. **Cutover:** o `investment_id` muda para todo o corpus, e em
  modo incremental ([[ADR-080]]/[[ADR-169]]) artefatos velhos mantêm o id antigo até
  re-consolidar. O raio é limitado porque não há coluna nem FK ([[A42.l15]] §Já refutado): o
  que envelhece é o `nao_classificado_itens[].locator` de relatório já publicado.
- **Critério 8** — `pytest tests -q` **8278 passed** · `pytest backend/tests -q` verde.

### O braço da hipótese — regra de formato em `descricao`, no MESMO bump

Vai junto de propósito. A regularidade medida em 72 pares é sem exceção em 6 campos: o
que o prompt pina numa superfície única de renderização é estável (`secao` 0/72 e
`categoria_hint` 1/72 por **enum**; `valor_brl` 100% e `cpf` por **regra de formato**), e
o que ele deixa livre churna (`descricao` 56%, `membro` 39%, `codigo` 36%, `instituicao`
32%). `descricao` tem codomínio aberto, então não cabe enum — cabe regra: *"copie
INTEGRALMENTE, sem truncar, resumir nem parafrasear"* + *"duas extrações do mesmo
documento devem produzir a MESMA string caractere a caractere"*.

⚠️ **Efeito NÃO medido, e não vou fingir que está.** Mudança de prompt só se mede com
runs novos; a §Armadilha (D) proíbe usar estabilidade run-a-run como critério de aceite,
e o replay offline não alcança prompt que ainda não rodou. O caminho de validação já
existe e não precisa de ferramenta nova: `dev/measure_e15_identity_stability.py` agrupa
por era, então a era 1.4.0 **acumula amostra sozinha** conforme o dogfood roda — com
K≥5 ela vira um grupo medido e comparável às eras anteriores.

**Por que no mesmo bump:** adiar custaria um `1.5.0` depois e uma **segunda** fronteira
de era. A âncora é era-free por desenho (campo ⊳ texto dão a mesma raiz), mas a perna
fraca **não é**: mexer em `descricao` move toda chave que caia nela. Uma transição é
melhor que duas.

## Fechamento — 2026-09-01 · `shipped`

Cinco PRs: **#1909** (contrato da âncora) · **#1916** (critério 4, gate de acoplamento) ·
**#1919** (critério 6, harness offline) · **#1937** (parse do grupo `GG-CC`) · **#1939**
(PR1 produtor + PR2 chave + regra de formato). Os **8 critérios de aceite** estão fechados.

**O número da lane:** estabilidade do `investment_id` de **23,5%** (medição de abertura, um
par de runs) → **61,78%** pooled sobre 28 grupos com denominador. A abertura e o fecho não
são o mesmo instrumento — o 23,5% era um par, o 61,78% é `|A∩B|/|A∪B|` agregado sobre todos
os pares de 19 documentos. O comparável é o **37,68%** que o mesmo harness media antes.

**Emenda datada à [[ADR-271]]** (não ADR nova, como a lane decidiu): o `PR3` da §Próximos
passos foi executado; §140 permanece intacta; e a rejeição a `instituicao` ficou registrada
no seu alcance real — vale para o **code do catálogo**, não para o campo cru na perna fraca.

### Deliberadamente NÃO feito — cada um com o motivo

- **Regra de formato em `descricao`: entregue, efeito não medido.** Só runs novos a medem, e
  a §Armadilha (D) proíbe estabilidade run-a-run como critério. O harness já agrupa por era,
  então a era 1.4.0 acumula amostra sozinha até K≥5.
- **`codigo` composto em `imovel`** (4 itens: `01-11`, `01-12`) vai cru para
  `entry["codigo_rfb"]`, lido por comparação estrita em
  `db_property_identity_resolver.py:134,168`. Latente, não vivo — `property_id` é UUID
  resolvido contra o DB e mede 100% de estabilidade. Mesmo eixo da §Armadilha (C), junto com
  `wise_fiscal_flags.py:32,35,38` (`==` contra `"13"/"62"/"41"`).
- **`dividas_dedup` tem a MESMA exposição** que o critério 4 gateou para investimentos, e
  **não** está coberto — declarado como limite no PR #1916 e ainda de pé.
- **Alias no `institution_catalog`** (§Passo 0: a metade de baixo do `instituicao` fora do
  catálogo é alias faltando, não cobertura). Sem bloqueio, sem dono.
- **A rota da [[A40.l50]]** (`open`, P1) fixa `Internacional = R$ 34.918,47` em prosa; o
  número não reproduz e a causa era esta lane. Quem pegar precisa **re-medir** — a chave
  mudou de novo aqui.

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
2. ✅ **ENTREGUE (PR2)** — **Cobertura de âncora medida no artefato publicado** (padrão `investimentos_cobertura`/
   [[ADR-406]]), não no estado em voo. É o invariante que mata o modo `numero_contrato`.
3. ✅ **ENTREGUE (PR2)** — **Recusa em vez de palpite** (unit, zero runs): âncora forte ausente **e** descrição fraca
   ⇒ `None` + `review_reason`. Único invariante sobre a **decisão**, não sobre o número.
4. ~~**Gate de acoplamento**~~ **ENTREGUE — PR #1916 (`132f97f8`)** — `tests/unit/pipeline/test_investment_id_acoplamento.py`.
   Três pernas, porque uma só seria cega: **fecho transitivo** de imports (hoje 9 módulos,
   zero de catálogo — import direto pega, mas o acoplamento entraria por um helper a um
   salto); **aridade de `_identity_key`**, a rota que import nenhum revela (catálogo
   *injetado* como parâmetro); e **anti-vacuidade**, com âncoras nomeadas que reprovam se
   um renome fizer o padrão parar de casar módulo real — senão o gate passaria sobre
   conjunto vazio. Seis mutações executadas (direto · transitivo · diferido em função ·
   aliasado · injetado · renome), cada uma derrubando a perna certa. **Limites declarados:**
   o fecho é estático, então `importlib.import_module` com nome montado em runtime e
   `getattr` sobre módulo já importado ficam fora; e `dividas_dedup` tem a **mesma
   exposição** e **não** está coberto.
5. ✅ **ENTREGUE (PR2)** — **Identidade estável entre eras provada por mutação executada** — item de era 1.3.0 e item
   de era 1.4.0, mesma posição, mesmo hash; ou a política de era (B) escrita e implementada.
6. ~~**Não aceitar como evidência**~~ **ENTREGUE — PR #1919 (`b11d5bfd`)** — `dev/measure_e15_identity_stability.py`
   + núcleo puro em `tests/dev/test_measure_e15_identity_stability.py`. **Zero token de LLM:**
   a variação já está no corpus, e replay de artefato histórico é imune à §Armadilha D
   (aqueles foram gravados com o cache desligado). Para o regime futuro o harness conta
   **pares byte-idênticos** e os reporta separado — ao 23,5% medido, par idêntico é anomalia.
   Nove mutações executadas. O critério é atendido: **19 documentos** com K≥5 (o corpus
   sustenta até **K=38**), contra o mínimo de 2.
7. ✅ **ENTREGUE (PR2)** — **Rebaselines declarados no PR:** `tests/fixtures/dedup/policy_parity_snapshot.json` (via
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
