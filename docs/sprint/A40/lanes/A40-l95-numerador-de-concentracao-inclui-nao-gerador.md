---
id: A40.l95
type: lane
title: "Numerador da concentração imobiliária inclui bem que o motor declara não-gerador"
sprint: A40
plan: PLAN-report-trust
status: in_progress
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
  - status/in-progress
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
