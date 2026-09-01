---
id: A40.l95
type: lane
title: "Numerador da concentração imobiliária inclui bem que o motor declara não-gerador"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1932
ship_date: "2026-09-01"
priority: P0
branch_slug: a40-l95-numerador-de-concentracao-inclui-nao-gerador
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-235]]"
  - "[[ADR-340]]"
  - "[[ADR-420]]"
  - "[[ADR-412]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l95 — `numerador-de-concentracao-inclui-nao-gerador`

> **Origem:** `RR6-02` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). Aritmética reproduzida e verificada pelo loop principal.

## O defeito

```
publicado:          imoveis_fisicos_brl / investivel_efetivo             = 50,62%
sem o não-gerador:  (imoveis_fisicos_brl − imoveis_nao_geradores) / …    = 49,08%
kpi_targets.concentracao_imobiliaria: limiar 50,0 · operador '<'
```

`patrimonio.imoveis_nao_geradores` é a nu-propriedade que
`real_estate.excluded_properties[1]` exclui do cálculo de renda com o motivo **literal**
*"não gera caixa nem está disponível para venda livre"*. A subtração fecha exata contra
`real_estate.valor_total_imoveis`.

**O KPI inverte de veredito** ao remover do numerador um ativo que o próprio motor exclui
duas seções antes.

## Raio — o que este único ativo aciona hoje

`pontos_urgentes[1]` · um risco de severidade **Alta** no parecer §S4 ·
`real_estate.alertas[1] concentracao_alta` · KPI vermelho na tabela de métricas ·
`score.componentes[4]` nota 4,0/10 com peso 12,5%.
O alerta `spread_critico` (piso 45%) **sobrevive**; os demais não.

## Confirmação independente

O braço cego da mesma rodada, **sem ver esta análise**, marcou a alavanca
`indeterminado-por-viés`: o disparo tem margem de **0,62 pp** sobre o limiar, e a base
declarada (`carteira_produtiva_fixa`) não reconstrói a partir de nenhum escalar do payload.
Duas rotas independentes no mesmo alvo.

## Leia antes de abrir escopo

[[A40.l80]] §C6 já mediu que os 10 `kpi_targets` **têm** `base` preenchida e ela é
**incoerente**: *"o problema é o vocabulário do campo, não o preenchimento — senão o fix
vira 'preencher o campo'"*. Confira se a l80 já é dona disso.

## Julgamento de domínio a fechar

As três metodologias de referência medem concentração sobre carteira **produtiva** — ativo
sem caixa e sem liquidez não pertence ao numerador de "imóveis **de renda**". Se a intenção
for medir **iliquidez total**, é **outro KPI**, com outro rótulo e outro limiar. Decida qual,
com o `financial-planner` no planejamento.

Agravante de rótulo na mesma peça: a prosa imprime uma contagem de imóveis de investimento
**menor** que a que o numerador soma.

## Critério de aceite

- Numerador e rótulo concordam sobre o que é medido.
- Se o KPI mudar de veredito, as 5 superfícies que ele aciona mudam **juntas**.
- Emenda datada à ADR canônica do limiar, ou ADR nova se o KPI mudar de identidade.


---

## Correções à lane (2026-08-29 · medição no run `79a61e33`, o da própria U2)

> A decisão está aberta em **[[ADR-420]]** (`Proposto`). Esta seção retrata o que a
> re-medição corrigiu — nada acima foi apagado, e onde o texto original diverge,
> **esta seção prevalece**.

**A tese central se sustenta** e o mecanismo ficou mais nítido. O que não reproduziu:

| # | Está escrito acima | Medido | Leia assim |
|---|---|---|---|
| K1 | `publicado = imoveis_fisicos_brl / investivel_efetivo` | **falso.** `investivel_efetivo = investivel_financeiro + imoveis_geradores` **exato** — ele **já exclui** o não-gerador. O denominador publicado é `investivel_efetivo + imoveis_nao_geradores` | o campo `imoveis_fisicos_brl` não existe; o numerador é `patrimonio.imoveis_investimento` (cat_2), e `cat_2 = geradores + nao_geradores` **exato**. A fração corrigida é `geradores / (financeiro + geradores)` |
| K2 | braço cego: *"a base declarada não reconstrói a partir de nenhum escalar do payload"* | **obsoleto.** O PR4 da [[A40.l80]] (#1782) criou `patrimonio.bases.carteira_produtiva_fixa.valor_brl`, que reconstrói ao centavo | o que sobra é mais afiado: o denominador **publicado** tem **1** representante no payload — uma base criada para este KPI e usada por mais ninguém —, e o **corrigido** tem **3**, entre eles o `investivel_efetivo` que o hero imprime |
| K3 | *"caem juntos … uma nota 4,0/10 com peso 12,5%"* | a nota vai a **4,2**; o composto vai de **7,438 → 7,463**, e **arredonda 7,4 nos dois** | o score é **materialmente insensível**. Quem se move são as **quatro** superfícies de limiar binário. Não prometa movimento de score no critério de aceite |
| K4 | *"as três metodologias medem concentração sobre carteira produtiva — ativo sem caixa não pertence ao numerador de imóveis de renda"* | o discriminador em que as três convergem **não é fluxo de caixa**, é **rebalanceabilidade** | o corte **não** é `geradores` vs `nao_geradores`: `especulacao` **fica** e `uso_pessoal` **sai**. Ver [[ADR-420]] §D1 |
| K5 | §Julgamento: *"se a intenção for medir iliquidez total, é OUTRO KPI"* | correto, e o KPI já tinha dono documental **não-financiado**: [[ADR-235]] §Decisão item 4 decidiu em 2026-05-20 que nu-propriedade entra em concentração **total** (denominador PL) e **não** em "de renda" | nunca implementada — confirmei por três fontes que não há produtor, o payload publica uma única chave de concentração, e o item 4 não é citado em lugar nenhum da vault. [[ADR-420]] §D3 a **financia** |
| K6 | §"Leia antes de abrir escopo": *"confira se a l80 já é dona"* | **não é.** Título e §Escopo por achado da l80 nomeiam **denominador**; nenhuma das 5 linhas cita numerador. Trocar o numerador **converge** `carteira_produtiva_fixa` sobre `carteira_produtiva_familia` — o ramo que a [[ADR-412]] §E5 fechou. E a l80 se declarou **número-neutra** neste eixo, usando isso como prova para não bumpar `BASE_VERSAO_CORRENTE` | a l80 é dona do **vocabulário de base**; esta lane é dona do **numerador**. **Um** item volta para lá: ver §Devolvido à l80 |
| K7 | *"Emenda datada à ADR canônica do limiar, ou ADR nova se o KPI mudar de identidade"* | o KPI **muda de identidade** (numerador redefinido + irmão publicado) ⇒ **ambos**, e não um ou outro | emenda de **retratação** na [[ADR-340]] (que aponta, não decide) + [[ADR-420]] que decide, com `supersedes: []`. Regra de fronteira em [[ADR-420]] §Alternativas (D) |

### O ofensor, nomeado — o gate que precedia a ADR

Censo do workspace, fechando ao centavo: **4 × `locado`** (soma == `imoveis_geradores`) +
**1 × `residencia_principal`** (cat_1, o splitter faz `continue`) + **1 × `nu_proprietario`**
com override **explícito** (valor == `imoveis_nao_geradores`). Os outros quatro destinos do
`else` — `uso_pessoal`, `especulacao`, `desconhecido` e sem-override — estão **vazios** aqui.
⇒ **defeito metodológico, não de captura.** A hipótese alternativa (o delta vir de imóvel sem
classificação, que tornaria a ADR resposta à pergunta errada) está **refutada por medição**.

### O sinal é fixo, e é algébrico

`f(m) = m/(financeiro+m)` é estritamente crescente ⇒ o publicado é **sempre ≥** o corrigido,
com igualdade sse `imoveis_nao_geradores = 0`. O defeito **só infla** concentração: produz
falso alarme, **nunca** falso negativo. Vale para todo workspace, não só para este.

### O rótulo é o vetor, e ele é anterior à [[ADR-340]]

"Imóveis de renda" nomeia cat_2 (ou número derivado dele) em **sete** sítios — balde de
composição, rótulo da dimensão do score, docstring do SSOT, descrição do alias no schema,
painel de metodologia, tabela de maiores ativos e card de yield. E o hero
(`HeroKpiGrid.tsx:158`) usa o **mesmo rótulo** para `imoveis_geradores`: número diferente,
mesma página. **Corrigido de "oito" no closeout** — a formulação anterior contava o hero
entre os que incluem não-geradores, e ele é justamente o que não inclui. A origem é a [[ADR-215]] P3, cujo rename do balde cat_2
(`patrimonio_composicao.py:52-53`) se justifica literalmente por *"comunicar o critério
econômico real (geração de caixa)"*. A [[ADR-340]] herdou a crença; não a criou.

O agravante de contagem confirma-se no call-site: `RealEstateYieldCard.tsx:97-99` imprime o
percentual (numerador de **5** imóveis) e `data.imoveis.length` (= **4** geradores) **na mesma
frase**, e o card ainda diz *"2 imóveis não incluído(s) no cálculo"* — um dos dois está dentro
do percentual ao lado. Os motivos da exclusão vivem num `<details>`, logo **não aparecem no
print nem no PDF**.

## Bloqueante: a fixture é o gate, e ela está cega — ao contrário do que eu supus

Supus que o golden tivesse `imoveis_nao_geradores = 0`. Medido em
`backend/tests/snapshots/dogfood_view_model.json`, é o **inverso exato**:
`imoveis_geradores = 0` e `imoveis_nao_geradores` = **100% de cat_2** (concentração 82,19%),
com `residencia = 0`, `veiculos = 0` e **`real_estate` inteiro `null`**.

**Nenhuma fixture end-to-end do repo tem `imoveis_geradores > 0`.** A fixture não é cega ao
*delta* — a mutação reprova o snapshot com diff grande —, é cega à **pergunta**: com
`geradores ≡ 0` as duas leituras são extremos degenerados, e verde depois do conserto provaria
só que geradores é zero. É extensão maior que o §Follow-up declarado da [[ADR-340]], porque
alcança também o alias, o alerta `concentracao_alta`, o co-threshold `spread_critico` e
`excluded_properties` — nenhum exercitado por golden.

## Ordem obrigatória

1. **Declarar o numerador no payload** (número-neutro) — §Devolvido à l80, abaixo.
2. **Fixture ganha ≥1 `locado` e ≥1 `especulacao`** com valores distintos e não-nulos.
3. Só então o fix de [[ADR-420]] §D1/D3 — antes disso é inobservável.

Inverter 2 e 3 é escrever o gate contra a fixture que não discrimina: o modo de falha que a
própria l80 pagou duas vezes (#1782 e o C19).

## Roteamento e amarra — conferidos, e um deles muda

- **Fica na A40**, dentro da **cláusula de reinício do contador** (`_README.md:119-124`): a
  sprint já nomeou esta lane entre as que mutam E3/E5 a montante, e o contador está em
  **0/2**. São **quatro**, não três: a [[A40.l96]] entrou pela medição de 2026-08-29
  (`_README.md:128-133`), e o "três" escrito aqui envelheceu num rebase limpo no mesmo dia. O precedente de rotear para a [[A42]] (`_README.md:200-203`, fix de paridade da
  ledger) **não** se aplica: lá o argumento era não zerar um contador em curso.
- **A l80 não bloqueia esta lane.** O §Ordem e amarra dela (`:502-508`) declara **isenção
  própria** ("toca `dev/`, `config/schemas/`, `backend/tests/snapshots/` — não `pipeline/`…
  logo não muta E5"), não uma proibição sobre terceiros. O closeout dela é irrelevante aqui.

## Devolvido à [[A40.l80]] — precondição desta lane, escopo daquela

O payload **não nomeia o numerador em lugar nenhum**, e o gate compensa fixando
`numerador = patrimonio["imoveis_investimento"]` em `tests/test_cobertura_de_base.py`. É o
**C14** daquela lane (*"declarada ≠ usada"*) deslocado um campo, na classe que o **C19** provou
fechar pela ordem "o produtor publica primeiro, o gate enxerga e fica vermelho sozinho".
Ela é dona assinada de C14, de C19 e do arquivo. Número-neutro, cabe no closeout.
**Não editei o arquivo dela** — está `OCUPADA` por sessão viva.

## Follow-ups nomeados, fora desta lane

- **Colateral grave, com lane própria:** a auditoria cláusula-a-cláusula da [[ADR-235]]
  feita a partir desta lane achou que `batch_alter_table(copy_from=)` apagou **38 índices**
  em 13 migrations, 3 deles UNIQUE que derrubavam invariante de negócio. Não é sobre
  concentração nem sobre nu-propriedade — ver [[ADR-423]] e [[A40.l97]].

- **Regime default de classificação — sem lane id alocado.** `split_imoveis_with_overrides` só
  reconhece cat_1 com override **explícito**, e o `else` do splitter recebe também imóvel **sem
  override nenhum**. No golden (regime default) isso põe 100% de cat_2 no numerador; reclassificar
  um imóvel para `residencia_principal` o tira de numerador **e** denominador, movendo 82,19 → 0,00.
  **Classe distinta desta lane** — captura, não metodologia; o fix é estado ternário + cobertura
  ([[ADR-412]] §D2), com critério de aceite próprio. ⚠️ **A prevalência em produção é NÃO-MEDIDA:**
  a evidência é uma fixture sintética, e o dogfood tem os 6 imóveis classificados. Registre como
  exposição **estrutural**, não como incidência. Precedência: metodologia primeiro (a regra de
  cobertura precisa saber qual é o numerador), sem bloqueio — as duas ADRs escrevem-se em paralelo.
- **Terceira cópia desatualizada do limiar.** `docs/reference/rules/rule-concentracao-imobiliaria.md`
  ainda diz *"alerta S4 >40% **do patrimônio**"* — errada nas duas dimensões (limiar 40, base
  patrimônio). Reconciliar junto com `FORMULAS.md` §219 no PR de implementação.
- **`risk_trigger_registry` usa `<=` e o catálogo publica `<`**, divergindo em **50,00 exato** —
  o comentário do registry declara a escolha. Território da [[A40.l90]]/[[A40.l92]], não desta.

## Critério de aceite — prevalece sobre o de cima

O de [[ADR-420]] §Critério de aceite, com uma adição: **a copy não narra o flip para verde como
melhora.** A queda para 49,08% é correção de medição, e o `spread_critico` (piso 45) **sobrevive**
ao conserto — é ele que segue dizendo o risco real desta família.

---

## Entregue — as duas precondições da §Ordem obrigatória (2026-08-31)

> O passo 3 (o fix de [[ADR-420]] §D1/§D3) **não** entrou. Esta seção registra o que
> fechou, o que a execução refutou e o que resta decidir.

### Passo 1 — o numerador declarado · PR [#1901](https://github.com/davidrobert/mathoms/pull/1901)

**O item estava órfão.** A §Devolvido à [[A40.l80]] apostava que ela absorveria o D5 no
closeout; ela encerrou em [#1835](https://github.com/davidrobert/mathoms/pull/1835)
(`shipped`, 2026-08-30) **sem absorvê-lo** — `tests/test_cobertura_de_base.py` seguia
fixando `patrimonio["imoveis_investimento"]`. Reassumido aqui, número-neutro.

`concentracao_imobiliaria.CHAVE_DO_NUMERADOR` passa a ser lida pelo SSOT **e** publicada
por `ratios` como `numerador_concentracao_imobiliaria`: declaração e leitura saem da mesma
constante e não podem divergir; o enum fechado do schema é o que separa redefinição
declarada de drift silencioso.

**A fixture do próprio gate não discriminava o numerador.** Com `caixa_total_brl = 50k`, a
carteira financeira somava **900.000** — o mesmo valor de `imoveis_investimento` —, então
`investivel_financeiro` reproduzia a concentração tão bem quanto o numerador de verdade. O
gate novo teria nascido vacuoso. `60k` separa o eixo.

Não-inércia medida: fórmula lendo outra chave **3 vermelhos**; redefinição coerente da
constante sem mover o schema **4**; o contrafactual da fixture em 50k **2**; controle 16
verdes.

### Passo 2 — a fixture que discrimina o destino de cat_2

O split **conserva o bruto**: o imóvel opaco de R$600.000 vira **cinco** com destino
declarado somando os mesmos R$600.000, e `bruto`, `liquido` e `imoveis_investimento` ficam
byte-idênticos. O apartamento (R$190k) fica **sem override** de propósito — o regime default
é a classe de defeito distinta do §Follow-up, e apagá-la aqui perderia a cobertura.

| destino | imóvel | valor | hoje | pós-§D1 |
|---|---|---|---|---|
| `locado` | sala comercial | 150.000 | gerador | alocação |
| `especulacao` | terreno | 100.000 | **não-gerador** | **alocação** |
| `nu_proprietario` | casa | 90.000 | não-gerador | fora |
| `uso_pessoal` | casa de praia | 70.000 | não-gerador | **fora** |
| sem override | apartamento | 190.000 | não-gerador | alocação |

`imoveis_geradores` sai de **0 → 150.000** (era zero em toda fixture end-to-end do repo) e
`cat2_efetivo` de **0 → 150.000**, o que move o investível efetivo e o bloco IF. Manifesto de
rebaseline com ~~**12 entradas**~~ **13** (a 13ª entrou com a correção de ordenação, abaixo), `golden_diff` exit 0.

**Mecânica, e o que ela custou medir:** `property_id` só é cunhado com resolver +
`workspace_id` injetados, e é `uuid4` — fixá-lo na fixture divergiria da regra de mint da
produção, o modo de falha que o próprio substrato documenta em `_dados_efetivos`.
`endereco_canonical` é a ponte determinística, e o mapa de overrides monta-se **depois** do
E1.5c. Medido **antes** de adotar: injetar identidade deixa o E5 **byte-idêntico** e nenhum
uuid vaza para o payload.

A discriminação é guardada por `test_a_classificacao_declarada_e_LOAD_BEARING` (contrafactual
sem override colapsa geradores a zero), **não** por assert dentro do substrato: `run_dogfood_pipeline`
também é o runner de baselines próprios (`test_e5_reserva_formula_canonica`), e falhar ali era
falso positivo — medido, cinco erros.

### O que bloqueia o passo 3, e o bloqueio é documental

[[ADR-420]] §D2 declara: *"o piso reusa a escada de [[ADR-353]], que está `Proposto`: a
dependência é declarada, não presumida, e esta ADR não flippa antes dela"*. Medido hoje:

1. **A escada da [[ADR-353]] está em produção.** `NAO_IDENTIFICADO_PARCIAL_PCT = 10` /
   `_INSUFICIENTE_PCT = 30`, `_confianca_nivel`, e `diagnostico_confianca` publicado no
   payload (`{"nivel": "alta", "share_nao_identificado_pct": …}` no golden), lido por
   `kpi_target_catalog`. Falta o **consumidor de frontend**, não o mecanismo.
2. **O flip da [[ADR-353]] pende da [[A40.l11]]**, que está `planned` e é **P2**. O passo 3
   desta lane é **P0**.
3. **O precedente de reusar régua de ADR `Proposto` já foi aberto — e por decisão mais nova.**
   A [[ADR-425]] (`Decidido`, 2026-08-30) importa as constantes da [[ADR-353]]
   explicitamente (*"importando as constantes da [[ADR-353]] (nunca redeclarando-as)"*),
   com ela ainda `Proposto`.

⚠️ **Não emendei a [[ADR-420]].** A cláusula é dela e cai por medição, mas relaxar gate de
dependência é decisão com dono — e a regra de fronteira da própria §Alternativas (D) manda
**emenda datada de retratação**, não edição silenciosa. Fica como decisão aberta: ou a
[[A40.l11]] sobe de prioridade e a [[ADR-353]] flippa, ou a §D2 ganha emenda restringindo a
dependência ao **piso de cobertura** (que é o que ela de fato usa) em vez de ao flip inteiro.

### Correção ao §Critério de aceite 2 da [[ADR-420]]

O critério pede *"teste irmão de `test_a_fixture_discrimina_as_bases`"*. Entregue como
`tests/test_golden_discrimina_classificacao_de_imovel.py`, com **dois** irmãos e não um: o
eixo do numerador precisava do seu (`test_a_fixture_discrimina_o_NUMERADOR`, no arquivo do
gate) além do eixo de classificação. O critério escrito supunha um eixo só.

### Duas correções pós-merge (2026-08-31, closeout)

**A ordem dos `itens` da fixture é load-bearing, e não é óbvia.** `golden_diff` compara
listas **posicionalmente**. A primeira versão inseria os quatro imóveis novos no meio,
o que empurrava o `FINANCIAMENTO IMOVEL FICTICIO` do índice 3 para o 7 — e o diff lia
isso como *"o financiamento (−150.000) virou a sala comercial (+150.000)"*: dois
`value_delta` monetários **fabricados**, que só um waiver falso no manifesto silenciaria
(o que o docstring do `golden_diff` proíbe nominalmente). CI vermelho no passo *"Delta de
golden declarado"*, consertado pela **ordem**: o apartamento muta in place no índice 2 e
os novos são **append**. Quem editar esta fixture de novo: **não insira no meio**.

**O manifesto de rebaseline é waiver transitório, e eu o deixei permanente.** As 13
entradas ficaram em `main` depois do merge. `golden_diff` reprova entrada **órfã** — a
que não casa `value_delta` do PR corrente —, então elas fariam o **próximo** PR que
tocasse qualquer um dos dois goldens falhar com 13 erros sobre um rebaseline alheio.
Medido por simulação antes de agir: PR futuro tocando `dogfood_view_model.json` sem mover
dinheiro → `exit 1`, **12 órfãs**; com o manifesto drenado → `exit 0`; e PR que **move**
dinheiro segue reprovando (`exit 1`), então drenar não afrouxa o gate.

O #1904 foi o **primeiro** rebaseline a de fato usar o manifesto — ele era `[]` desde que
nasceu, em 2 commits —, e por isso o passo de drenagem nunca tinha sido exercido por
ninguém. A regra ficou escrita no cabeçalho do próprio arquivo.

**Confirmado no mundo real, não só na simulação (2026-08-31):** enquanto este PR estava
aberto, a [[A40.l111]] **drenou o manifesto dentro do #1917** — outra lane bateu na mina
antes de a correção mergear. A simulação previu a classe; o #1917 é a ocorrência. O que
este PR contribui deixa de ser a drenagem e passa a ser o **porquê durável** no cabeçalho
do arquivo, que é o que impede a terceira ocorrência.

**Follow-up proposto, sem dono ainda:** nada **força** a drenagem. Um gate que reprove
manifesto não-vazio em `main` fecharia a classe; a extensão natural é
`dev/check_lane_transition.py` ou o passo de CI que já lê o arquivo — **não** um gate
novo (§"Não reconstrua o gate"). Decisão do dono.

## Passo 3 — a primeira metade entregue: §D3 (2026-08-31)

`ratios.imobilizacao_patrimonial_pct` publicado, **sem alvo**. Com ele a [[ADR-235]]
§Decisão item 4 — `Decidido` desde 2026-05-20 e **sem produtor** — deixa de ser cláusula
não-financiada.

**Por que este pedaço primeiro, e não é conveniência.** São duas razões independentes:

1. A [[ADR-420]] §D3 declara o irmão **obrigatório antes** do estreitamento. Estreitar o
   numerador sozinho **apaga** a nu-propriedade de toda superfície de risco — troca falso
   alarme por **silêncio**, e o silêncio é o erro mais caro dos dois numa família com
   sucessão ativa.
2. É o **único** pedaço do passo 3 que não depende do bloqueio documental da [[ADR-353]]:
   sem limiar, não há piso de cobertura, logo não há escada a reusar. O §D1/§D2 seguem
   esperando a decisão registrada acima.

**Órfã por desenho, não por refutação** — é a sexta de `_ORFAOS_DOMINIO` e a única assim.
Doutrina de imobilização varia com idade, renda e sucessão; inventar teto aqui promoveria
número interno a doutrina, que é o que a [[ADR-419]] proíbe.

**`None` com PL ≤ 0, nunca 0,0.** Razão sobre denominador não-positivo é indefinida, e
0,0 leria como *"nada imobilizado"* exatamente na família insolvente — sinal trocado.

**Nasce com as duas pontas declaradas** (base + numerador, este em **lista** por ter dois
termos): razão nova sem numerador nomeável repetiria no dia um o C14 que esta lane acabou
de fechar na concentração.

No dogfood sai **103,45%** — a família tem mais imóvel do que patrimônio líquido, porque
o financiamento entra no PL e não no numerador. É o sinal que o irmão existe para não
deixar sumir.

**Não-inércia, 4 mutações:** numerador perde um termo (1 vermelho) · PL≤0 devolve 0,0 (1) ·
a razão deixa de ser órfã declarada (1) · contrafactual com `residencia = 0` (2). Controle
20 verdes.

**Limite declarado:** no golden a perna `residencia` é **zero** (nenhum imóvel tem override
`residencia_principal`), então quem exercita o numerador de dois termos é a fixture de
`test_cobertura_de_base`, com as duas pernas não-nulas e distintas. O golden é segunda
testemunha, não a primeira.

**Refactor que veio junto, em commit separado:** `kpi_target_catalog.py` estava em **499**
linhas — uma abaixo do teto de 500 — e o rationale das órfãs respondia por ~1/4 dele.
Qualquer órfã nova o estourava. Extraído para `kpi_orfaos_dominio.py` (365 + 144), sem
mudança de comportamento.

**O que do passo 3 continua aberto:** §D1 (estreitar o numerador), §D2 (o `desconhecido` e
a supressão da prescrição), §D4 (reconciliar o rationale de `FORMULAS.md` §219 e de
`rule-concentracao-imobiliaria.md`) e §D6 (bump de `BASE_VERSAO_CORRENTE`). Os quatro
esperam a decisão sobre a dependência da [[ADR-353]], registrada acima.

## Passo 3 fechado — o flip e o que a medição mudou nos critérios (2026-08-31)

**§D1/§D4/§D6 entregues.** O numerador corta por rebalanceabilidade, a base acompanha, e
`BASE_VERSAO_CORRENTE` bumpa 1 → 2. No dogfood a concentração vai de **82,19% → 77,19%**
com `bruto`, `liquido`, `imoveis_investimento` e `investivel_efetivo` **byte-idênticos** —
o fix não move dinheiro, como o §Critério 1 exige.

A **§D2 foi emendada** antes: a dependência da [[ADR-353]] vale para o **piso de
cobertura**, não para o flip desta nota. A escada dela já está em produção; o que falta é
o consumidor de frontend, preso na [[A40.l11]] (`planned`, P2). O piso segue **deferido
com dono e condição de retomada**.

### O colateral que só o bump revelou

Três testes do card cambial passaram a receber `indeterminado`, com a falha apontando
para o **câmbio** — que não tinha nada a ver. A causa era a fixture: parâmetro chamado
`serie_corrente` gravando `base_versao = 1` no corpo. Ela parou de ser corrente **em
silêncio** no primeiro bump de série. É *"declarada ≠ usada"* um andar abaixo, a mesma
classe que esta lane fechou no numerador — e ninguém a teria achado sem o bump.

### Critério 5 — a medição o reescreveu, e para melhor

O critério pedia *"o número de imóveis exibido ao lado do KPI é o do conjunto somado no
numerador; hoje o card diz 4 e o numerador soma 5"*. Medido: o card conta
`INVESTMENT_CLASSIFICATIONS` = {locado, comercial, especulacao} e o numerador novo é
**esse conjunto ∪ {desconhecido}**. Logo:

- no corpus medido (6 imóveis, todos classificados) as duas cardinalidades **coincidem
  depois do flip** — o `nu_proprietario` saiu do numerador e o card já não o contava. O
  defeito do critério 5 **fecha pelo §D1**, sem código de contagem novo.
- a divergência remanescente é **exatamente** o imóvel não-classificado, que é o
  §Follow-up de regime default já declarado. Encodada em
  `test_paridade_numerador_e_contagem_do_card.py`, que a **nomeia** em vez de deixá-la
  implícita.

O card também deixou de colar as duas afirmações na mesma frase: o percentual é sobre os
ilíquidos, e a contagem passa a dizer explicitamente *"cap rate sobre N imóveis com renda
apurada"*. Era a colagem que fazia o leitor tomar o 4 como cardinalidade do percentual.

### Critério 6 — parcial, e o resto tem motivo declarado

**Feito** — os rótulos que descrevem **a concentração**, que é o número que mudou:
`_DIMENSION_LABELS` do score (*"concentração em imóveis de renda"* → *"concentração
imobiliária na carteira"*), a descrição do alias no schema E5, o racional do
`scoring.json` e a frase do card.

**Não feito, e não por esquecimento:** o balde `"Imóveis de Renda"` de
`patrimonio_composicao`, o `Top15AtivosCard`, o `RealEstateBreakdownPanel` e as duas
telas de config. Eles rotulam **cat_2 completo** — que segue incluindo não-alocação —,
então o rótulo continua falso ali. Três razões para não fazê-lo neste PR:

1. É **copy de produto** em superfície visível, gatilho de `product-designer` pelo
   §Protocolo de delegação — e esta sessão está proibida de invocar subagente.
2. O balde tem **paridade Py ↔ TS enforçada** (gate da [[A40.l71]]) e é chaveado por
   string em fixtures e testes: renomear é mudança cross-cutting, não edição de texto.
3. O rótulo do balde é **anterior** a esta lane — vem da [[ADR-215]] P3, cujo rename se
   justificou por *"comunicar o critério econômico real (geração de caixa)"*. Corrigi-lo
   é reabrir aquela decisão, não fechar esta.

**Fica como follow-up nomeado, sem lane id:** *"o balde cat_2 e as 4 superfícies que o
rotulam dizem 'de renda' sobre número que inclui não-alocação"*. Dono natural:
`product-designer` + `senior-cto` (a paridade). A alocação é do rito de abertura da sprint.

### O que sobra na lane, e é só isso

| item | estado |
|---|---|
| §D1 numerador · §D3 irmão · §D4 rationale · §D5 declaração · §D6 contrato | ✅ |
| §D2 — piso de cobertura | ⏸ deferido, dono [[A40.l95]], condição: flip da [[ADR-353]] |
| Critério 6 — balde cat_2 e as 4 superfícies | ⏸ follow-up, sem lane id |
| Regime default (imóvel sem override) | ⏸ follow-up, sem lane id |

## Fecho — 2026-09-01

**`shipped`** em 6 PRs mergeados: #1901 (numerador declarado) · #1904 (fixture que
discrimina) · #1911 (manifesto drenado) · #1924 (§D3, imobilização) · #1926 (emenda da
§D2) · #1928 (partição publicada) · #1932 (o flip + rótulos). A [[ADR-420]] flipou para
`Decidido`.

O **#1931 foi fechado como redundante**, não mergeado: ramifiquei a branch dos rótulos a
partir da branch do flip em vez de `origin/main`, e o squash do #1932 carregou os três
commits daquele junto. Verifiquei artefato a artefato em `main` antes de fechar. É erro de
método meu, e o registro fica aqui para a próxima sessão não repetir: **branch de PR sai
de `origin/main`**, não da branch anterior.

### Critério 6 fechou inteiro, e a lista da ADR tinha um engano

As quatro superfícies que diziam "de renda" sobre número que inclui não-alocação foram
corrigidas **por subtração** do qualificador falso, não por vocabulário novo. O balde
cat_2 virou **"Outros imóveis"** — diz literalmente o que ele é (todo imóvel que não é a
residência, que é a linha logo acima) e não faz afirmação econômica que o número não
sustenta. ⚠️ Copy de superfície visível escolhida por subtração; vale confirmar com
`product-designer` na próxima passada de copy.

As duas que **não** mudaram — `HeroKpiGrid` e `MarketValueSection` — filtram
`{locado, comercial}`. Ali "imóveis de renda" é **verdade**, e a lista do §Critério 6 as
contava por engano. O closeout já tinha corrigido o hero; a medição de hoje confirmou o
mesmo na segunda superfície.

### O manifesto de rebaseline reincidiu no mesmo dia

O #1911 documentou que waiver de rebaseline é transitório e drenou o manifesto; o #1932
deixou uma entrada nova, e a mina voltou. Drenado de novo aqui, e a **mensagem de erro do
`golden_diff` passa a nomear o remédio** — quem lê a falha quase nunca é quem criou a
entrada. Não construí gate: a proposta de forçar a drenagem segue sem dono, e é extensão
do passo de CI que já lê o arquivo, nunca gate novo.

## Rotas de saída — nada fica sem dono

- **Piso de cobertura do §D2** → re-roteado na própria [[ADR-420]] para **quem executar a
  [[A40.l11]]**, que é quem destrava o flip da [[ADR-353]]. Deferimento hospedado em lane
  terminal seria órfão, e este não fica.
- **Imóvel sem classificação no numerador** → **próximo dono** é a [[A40.l112]], aberta
  hoje com escopo, medição e critério de aceite próprios. Classe distinta: captura, não
  metodologia.
- **Forçar a drenagem do manifesto** → proposta sem dono, registrada acima.
