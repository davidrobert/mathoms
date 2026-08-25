---
id: ADR-400
type: adr
title: "Transcrição não é mais confiável que classificação — a forma da dependência é que decide"
status: Decidido
phase: DE-1
date: "2026-08-19"
amended_at: ["2026-08-21", "2026-08-25"]
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-137]]"
  - "[[ADR-141]]"
  - "[[ADR-193]]"
  - "[[ADR-272]]"
  - "[[ADR-384]]"
  - "[[ADR-394]]"
supersedes: []
superseded_by: []
aliases:
  - "transcrição não é mais confiável que classificação"
  - "autoridade declarada no classificador de ativos"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/de-1
---

# ADR-400 — Transcrição não é mais confiável que classificação

> **Emendada em 2026-08-21** (§Emenda — o gatilho é re-extração, não o #1521).

> **Emenda 2026-08-25 (§Degrau 1 bloqueado).** O r8 refutou empiricamente a ordem
> declarada no §Decisão item 3: com `PRESUNTIVO` no degrau 1 e `KEYWORD` no degrau 2,
> o degrau 1 **reproduziria o RV8-01 com etiqueta melhor**. A causa não é a ordem —
> é `_classify_investimento` emitir default e fato no mesmo campo. **Não construa o
> degrau 1 antes de ler a §Emenda ao final.**

## Contexto

`classify_asset(tipo, descricao, instituicao)` decide a classe de um ativo por
keyword sobre um haystack de texto livre. Entre r5 e r7 do dogfood, `Caixa` foi
de 4,49% para 3,65% e `Outros` de 0,00% para 0,84% — compensatório, com os outros
sete baldes byte-idênticos e **sem um único diff no classificador** (último commit
seis semanas antes). Causa: uma instituição de 6 caracteres que **é** keyword de
`Caixa` foi reemitida em forma canônica de 13 caracteres com `_`;
`_normalize_haystack` troca `_` por espaço, o token vira dois, nenhuma keyword
bate, o item cai em `Outros`.

O defeito não é a keyword. É que `instituicao` é o único input do classificador
cuja forma canônica é **propriedade de outro subsistema** (`institution_catalog`,
[[ADR-137]]/[[ADR-384]]). Renomear `nubank` → `nu_pagamentos` está **certo** no
domínio dele e reclassifica ativo no nosso — sem diff, sem revisão e sem sinal.
É um contrato implícito entre dois catálogos que ninguém declarou.

Mais fundo: `conta_bancaria` e `fundo_investimento`, sozinhos, já caem em `Outros`
hoje. `Caixa` e `Fundos` só funcionavam por sorte de marca — as keywords de
`Fundos` são cinco nomes de casas de fundo.

## Decisão

**A classe de ativo é decidida pelo sinal mais forte disponível, e o resultado
declara quem decidiu.**

1. `instituicao` **sai da entrada** do classificador. Custódia responde "quem
   guarda", não "o que é". Onde a custódia é resposta legítima — lastro cambial —
   ela vira lista explícita e nomeada **no módulo que faz a pergunta**
   (`exposicao_cambial_analyzer._CUSTODIA_ESTRANGEIRA`).
2. O retorno vira value object tipado `AssetClassification(classe, autoridade,
   moeda, lastro, warnings)`, construído em **site único**. `moeda`/`lastro`
   nascem no shape para não haver segunda mudança de contrato nos consumidores.
3. `autoridade` é enum fechado em duas camadas de degrau 1 (`CONCLUSIVO`,
   `PRESUNTIVO`), degrau 2 (`KEYWORD`, `TICKER`) e ausências (`SEM_MATCH`,
   `SEM_HAYSTACK`, `SEM_MAPA`).
4. `SEM_HAYSTACK` é violação de contrato do produtor → `review_reason` sempre;
   é raro e é bug a montante. `SEM_MATCH` é **agregado** e escala só pelo limiar
   graduado — o cap de cardinalidade da [[ADR-272]] aplicado desde o desenho, não
   remendado depois.
5. O padrão `XXXX11` deixa de decidir sozinho. Ele é sufixo compartilhado por FII,
   ETF, UNIT e BDR: qualquer sinal textual explícito vence, e ticker fora da
   allowlist mínima vira `SEM_MATCH` **declarado** em vez de `FIIs` mudo.
6. A prescrição de alocação é suprimida em três degraus pela fração não
   classificada da carteira financeira: `<2%` publica tudo · `2–10%` derruba
   `next_aporte_classe` · `≥10%` derruba também `desvio_max_pct`. Os limiares não
   são novos — 2pp é `SEVERITY_ALINHADO_MAX_PP` e 10pp é o da [[ADR-141]] item 9.
   Critério: **a incerteza de classificação não pode ser maior que a menor
   diferença que o produto trata como acionável.**

## Por que o degrau 1 é `tipo` e tem duas camadas

Metade do codomínio de `tipo` (`renda_fixa`, `acao`, `participacao_societaria`,
`fundo_investimento`) sai de `_classify_investimento(normalize_grupo(codigo), …)`
e **herda a degeneração de `codigo` medida abaixo**. A outra metade
(`poupanca`, `conta_bancaria`, `previdencia`, `moeda_estrangeira`) sai do hint
sozinho, que é enum fechado de sete. Tratar os dois grupos igual repetiria o erro
um nível acima. `moeda_estrangeira` fica em conclusivo apesar do grupo 06 porque o
ramo que a produz exige keyword na descrição, não o código.

## Alternativa considerada e recusada: catálogo `(secao, codigo)` como degrau 1

O desenho inicial era reusar a chave do `e15_secoes_rfb_<ano>.yaml` ([[ADR-394]]
D2). A medição **M1** (2026-08-19, 786 artefatos `E1.5a`, 81 runs, **6.780
itens**, zero falha de decrypt) recusa essa chave:

| medida | resultado | leitura |
| --- | --- | --- |
| `codigo` presente | **6780/6780 (100,00%)** | cobertura de **campo** é total |
| `codigo` semanticamente puro (≥95% um `categoria_hint`) | **3271 (48,2%)** | cobertura de **significado** não é |
| `codigo` degenerado (<95%) | **3509 (51,8%)** | maioria do corpus |
| `01` — o código mais frequente (2004 itens, 29,6%) | investimento 29,9% · conta_corrente 25,6% · **veiculo 24,4%** · poupanca 11,6% · imovel 8,6% | o mesmo código nomeia cinco coisas |
| artefatos onde `01` recebe ≥3 hints distintos **no mesmo IRPF** | **207/398** | não é "dois sistemas por era", é ruído intra-documento |
| `codigo == índice+1` (hipótese ordinal) | **88/6780 (1,3%)** | hipótese **refutada** |
| `secao` presente | **174 (2,57%)** | a chave que desambigua quase não existe |
| catálogo `(secao,codigo)` consultável | **172 itens (2,54% do corpus)**, 98,9% de acerto sobre os consultados | o catálogo está certo; o insumo é que falta |
| `codigo` distintos | 27 — 24 em 2 dígitos, 3 em `GG-CC` (99 itens, 1,46%, só ano-base 2025) | dois formatos convivendo |
| `"10"` (entrada `criptoativo` do YAML) | 23 itens (0,34%), 100% hint `investimento`, só 2024, **zero com `secao`** | entrada nunca consultada; cripto é grupo 08 e `08` não aparece no corpus |
| ticker `XXXX11` na descrição | **0 ocorrências** | o fix do ticker tem efeito **zero** nesta população |

E o insumo **morre antes do ponto de decisão**: em `consolidate_baseline.py` o
`entry` que vai para `investimentos_consolidados[]` carrega `descricao`,
`proprietario`, `valores_31_12`, `instituicao` e `tipo` — `codigo_rfb` só é
gravado para imóveis. `classify_asset` nunca vê o código.

Já existe um catálogo-por-código informal e ele confirma o diagnóstico:
`_classify_investimento` conhece apenas `03/04/06/07/99`, só roda quando o
**hint** diz `investimento` (circular), e `normalize_grupo("07-04")` devolve
`"07-04"`, que não bate ramo nenhum — os 88 itens do grupo 07 em forma `GG-CC`
caem em `"investimento"` genérico.

**A tese que sobra:** transcrição não é mais confiável que classificação — a
**forma da dependência** é que decide. `codigo` é campo *copiado* do formulário;
`categoria_hint` é rótulo *escolhido* de um enum de sete. A intuição diz que
copiar é mais seguro. Medido: o campo copiado é degenerado em 51,8% e se
contradiz dentro do mesmo documento em 207 de 398 artefatos, enquanto o rótulo
escolhido atravessa um funil determinístico de codomínio finito que nós possuímos.

## Os dois eixos têm hierarquias diferentes, e isso não é inconsistência

No eixo **ativo × passivo** ([[ADR-394]]) `secao` decide, e o sinal (valor
negativo) é veto genuíno — o IRPF declara saldo devedor positivo na ficha de
dívidas, então "positivo" não prova patrimônio, mas "negativo" prova passivo.

No eixo **classe**, `secao` cobre 2,57% e **não existe análogo do veto**: nenhum
atributo do item prova classe por si. Por isso a hierarquia aqui é `tipo` →
keyword → ticker → ausência declarada, e não `secao` → catálogo → sinal.

Sem este parágrafo, quem ler a [[ADR-394]] "conserta" a assimetria reintroduzindo
o catálogo `(secao, codigo)` — exatamente o que a M1 acabou de fechar.

## Consequências

- **A instituição deixa de mover número.** Renomeio no `institution_catalog`
  passa a ser inerte para classificação — que é o que a lane fechou.
- **Ticker de FII real fora da allowlist** (`MXRF11`, `KNRI11`) deixa de ir para
  `FIIs` e passa a `SEM_MATCH` → `Outros` declarado. É o desenho funcionando
  (declarado > mudo); impacto medido **zero** no corpus `E1.5a` (0 tickers), mas
  pode aparecer na população E4 e será lido como regressão por quem não ler isto.
- **O fix do ticker não move `tabela_classes` derivada do baseline.** `IVVB11` e
  `SCHP11` entram por informe/E4; o movimento aparece em `top_ativos` e
  `exposicao_cambial`. Ler "não moveu" como defeito e "consertar" seria regressão.
- **`Outros` continua classe legítima.** `nao_classificado` é derivado da
  `autoridade`, nunca do rótulo — nenhum enum muda, frontend e design tokens
  ficam intocados.
- **Conservação de Σ não prova nada aqui.** Reclassificação entre baldes preserva
  a soma por construção: `tests/test_e5_conservation_invariants.py` verde é
  esperado e não é evidência sobre esta mudança.
- `CONCLUSIVO`, `PRESUNTIVO` e `SEM_MAPA` nascem declarados **sem produtor**;
  quem os emite é o degrau 1, em rodada posterior. Membro de enum inalcançável é
  dívida quando ninguém sabe que é deliberado — o comentário no enum e o teste de
  ausência são o registro.
- **Deferido, datado (2026-08-19) · dono `data-engineer`:** marca como keyword
  sobrevive em `Caixa` (`picpay`, `nubank`) e `Fundos` (cinco casas de fundo).
  São keywords sobre a **descrição do próprio item**, não sobre forma canônica de
  terceiro, então não têm o modo de falha desta ADR — mas são degrau 2 frágil e
  saem quando o degrau 1 entrar.

## Emenda 2026-08-21 — o gatilho é *qualquer* re-extração, não o #1521

O §r7 registrava o DE-1 atribuindo a migração de classe ao bump de
`PROMPT_VERSION` do **#1521**. Esta ADR nunca fez essa atribuição — e a medição
mostra que ela é falsa como **causa**:

| medida | resultado |
| --- | --- |
| commits na história de `-L '/Instituição financeira/,+1'` (`pipeline/llm/prompts/e15_baseline.py`) | **1** — `6219acd5`, 2026-04-14 |
| o #1521 (`3a7aca05`) tocou o arquivo? | sim |
| o #1521 tocou **a linha** que produz o rótulo de instituição? | **não** |

A instrução que produz o rótulo não mudou desde abril. O que o #1521 fez foi
forçar **re-extração** — e é a re-extração, não o conteúdo do prompt, que
reemite a instituição em forma canônica e move a classe.

**Consequência prática:** o conjunto de gatilhos é maior do que o §r7 sugeria —
retry de stage, documento reprocessado, troca de model, `reextract_stale_e2_llm.py`
e qualquer bump de `PROMPT_VERSION`. Uma guarda desenhada a partir da redação
antiga cobriria a minoria dos casos. A decisão desta ADR **não muda**: o remédio
já é a autoridade declarada no resultado, que independe do gatilho. O que muda é
onde procurar quando a classe migrar sem diff no classificador.

## Emenda 2026-08-25 — presunção derivada de *default* não é presunção derivada de *fato*

O **RV8-01** do r8 (run `d0f6260a`) mediu: propagar `tipo` ao classificador move
**11 de 61 posições** de `Fundos` para `Renda Fixa` — R$ 174.636,71 — com
`autoridade: "keyword"` e zero `review_reason`. Contido pela [[A40.l82]].

### O que esta ADR já sabia, e o que faltava

O §"Por que o degrau 1 é `tipo` e tem duas camadas" **já nomeia** `renda_fixa` como
metade do codomínio que "herda a degeneração de `codigo`" — cinco dias antes do
incidente, com o valor exato escrito. O conhecimento existia; o que faltava era um
**gate ligando a declaração à entrada da função**. Enquanto
`classify_asset_outcome(tipo: str, …)` aceitar string nua naquele slot, qualquer
produtor passa uma presunção e recebe `KEYWORD` de volta.

### A ordem declarada está com um degrau no lugar errado

O §Decisão item 3 põe `CONCLUSIVO` e `PRESUNTIVO` no **degrau 1**, e `KEYWORD`/`TICKER`
no **degrau 2**. Sob essa ordem, quando o degrau 1 nascer, `tipo="renda_fixa"` (uma
presunção) venceria `descricao="…FIC FIM"` (uma keyword) — **exatamente o RV8-01**,
com rótulo mais bonito. O r8 é a evidência empírica de que a estratificação declarada
em 2026-08-19 não sobrevive ao corpus real.

### A decisão, e ela não é "reordenar o enum"

**Presunção derivada de default não é presunção derivada de fato.**
`_classify_investimento` (`scripts/consolidate_baseline.py:711`) tem **três `return`
de ignorância** — `renda_fixa` (grupo 04), `participacao_societaria` (grupo 03) e
`investimento` (fall-through) — e nenhum é distinguível, do outro lado do contrato,
de um `return` por evidência. Logo:

**O degrau 1 não pode ser construído enquanto o produtor não separar default de
evidência.** Até lá `PRESUNTIVO` não tem produtor legítimo, e qualquer produtor
erguido sobre o `tipo` de hoje estaria **fabricando autoridade**. `PRESUNTIVO` abaixo
de `KEYWORD` é **consequência** dessa separação, não a decisão — reordenar sem separar
troca um rótulo errado por outro.

Isso responde por escrito a pergunta de contrato que o co-design da [[A40.l82]]
levantou: **sim, é defeito de contrato, e o conserto é do produtor, não do
classificador.**

### Supersede o §Deferido de 2026-08-19 sobre marca como keyword

Aquele deferimento dizia que as cinco casas de fundo em `Fundos` "saem quando o degrau
1 entrar". **Saíram antes**, em 2026-08-25, com evidência nova: são corpus-fitting que
acerta um domicílio e erra calado no próximo — zero cobertura para B2B2C. Medido no
corpus do r8, das cinco só **`CONSTELLATION INSTITUCIONAL`** dependia de marca; as
outras têm token de instrumento (`fia`, `fic `, ` fim`) na descrição. Cair em
`SEM_MATCH` é o desfecho **correto**: o produto não sabe o que é aquela string e deve
dizê-lo.

`picpay`/`nubank` em `Caixa` **permanecem** — não foram medidas neste corpus, e cortar
sem medir é a mesma classe de erro na direção oposta.

### Uma segunda fonte de verdade, agora gateada

As mesmas cinco marcas viviam **também** em `config/scoring.json::asset_class_keywords`,
e `merge_asset_keywords` deixa o scoring **sobrescrever a classe inteira**. Medido:
cortar só o default seria **no-op em produção**. `test_scoring_do_repo_nao_diverge_do_default`
passa a travar a divergência.

## Deferimentos (2026-08-25)

**`classify_asset_outcome` deixar de aceitar `tipo: str` posicional — dono
`data-engineer`, janela J5.** Value object tipado no boundary ([[ADR-089]]/[[ADR-097]]
D2): enquanto a assinatura aceitar string nua, o próximo produtor repete o RV8-01 sem
saber. É **pré-condição do degrau 1**, não trabalho paralelo a ele.

**`tipo` volta a ser autoritativo quando o degrau 1 existir — dono `data-engineer`.**
Até lá o gate `tests/unit/pipeline/test_classe_de_ativo_nao_le_tipo.py` mantém o campo
fora do caminho de classificação da E5. **Sem relógio de propósito**: waiver que vence
travando o repo é dívida pior que a que ele cobre — a condição é a existência do
degrau 1, verificável, não uma data.

**`tipo_proveniencia` como campo companheiro — dono `data-engineer`, aditivo.** Enum
fechado derivado mecanicamente de qual `return` disparou (`declarado`,
`derivado_de_evidencia`, `default_de_grupo`, `desconhecido`). **Não** muda o valor de
`tipo`, que entra no hash de identidade (`_identity_key` → `investment_id`, publicado
como `locator` durável). É o produtor que falta para `CONCLUSIVO`/`PRESUNTIVO`.
