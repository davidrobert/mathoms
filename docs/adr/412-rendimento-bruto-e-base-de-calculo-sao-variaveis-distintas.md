---
id: ADR-412
type: adr
title: "Rendimento bruto e base de cálculo são variáveis distintas, e o PGBL usa a declarada"
status: Decidido
phase: A40.l64
date: "2026-08-25"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-157]]"
  - "[[ADR-305]]"
  - "[[ADR-375]]"
  - "[[ADR-389]]"
  - "[[ADR-402]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 412"
  - "bruto vs base de cálculo"
  - "base declarada do PGBL"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-412 — Rendimento bruto e base de cálculo são variáveis distintas, e o PGBL usa a declarada

## Contexto

A [[ADR-375]] D5 pôs a economia de PGBL como diferencial `IR(base) − IR(base − aporte)`,
implementada em `pgbl_economia_ir.economia_diferencial` ([[A40.l64]] PR2, #1672).
O call-site passa `cap.renda_tributavel_anual` — o **rendimento tributável bruto** —
para um parâmetro que a função trata como **base de cálculo**.

Sem redutor, a conflação distorce o nível: o imposto sai maior do que o devido,
porque incide sobre o bruto em vez da base. **Com o redutor da Lei 15.270/2025 ela
deixa de ser questão de nível e vira erro de faixa**, porque as duas grandezas
indexam objetos diferentes:

| objeto | indexado em | fonte |
| --- | --- | --- |
| tabela progressiva (`ir_brackets_anual`) | **base de cálculo** | [[ADR-389]] |
| redutor da Lei 15.270/2025 | **rendimento bruto** | RFB, Exemplos de Aplicação nº 4 |

A prova de que são duas variáveis está na própria tabela do redutor, e fecha ao
centavo contra a row AC2026 semeada pela migration `adr389tabelas`:

| teto declarado do redutor | reconstrução | resultado |
| --- | --- | --- |
| mensal R$ 312,89 | `IR_mensal(5.000 − 607,20)` = `4.392,80 × 22,5% − 675,49` | **312,89** |
| anual R$ 2.694,15 | `IR_anual(60.000 − 12.000)` = `48.000 × 22,5% − 8.105,85` | **2.694,15** |

Os dois tetos são o **imposto devido no piso da banda, sobre a base após o desconto
simplificado** — enquanto a banda em si é definida sobre o **bruto** (R$ 5.000 /
R$ 60.000). A tabela do redutor **só fecha num modelo de duas variáveis**.
Implementá-lo sobre a variável única faria o redutor disparar na banda errada para
todo mundo.

Medido: `IRPFAnalyzer` **não expõe** base de cálculo, e o domínio inteiro tem
**zero** ocorrências de `base_calculo_brl` — o insumo existe no corpus e é ignorado.

## Decisão

### D1 · Bruto e base são variáveis distintas no domínio

Quem indexa na base: tabela progressiva, imposto devido, alíquota marginal.
Quem indexa no bruto: o redutor da Lei 15.270/2025 e o IRPFM. Nenhuma função
recebe uma e chama de outra; o nome do parâmetro declara qual das duas é.

### D2 · A base vem DECLARADA, não derivada

`imposto_apurado.base_calculo_brl` é `required` no schema `e16_irpf_full`. A base
do ano é a **soma** desse campo sobre as declarações que compõem a capacidade
daquele ano-base — mesma partição que já produz `renda_tributavel_anual`.

**Derivar a base (bruto − desconto simplificado, ou bruto − deduções legais) foi
recusado.** O desconto simplificado é **escolha do contribuinte**, e a declaração
já registra o resultado dessa escolha; recalcular substituiria um fato por uma
suposição, e erraria exatamente em quem optou pelo modelo completo com deduções
altas — o público do produto. Ver §Alternativas.

**A base é obrigatória no VO, não opcional.** `base_calculo_brl` é `required` no
schema, então declaração que parseia sempre a tem — e `CapacidadePgblIRPF` só
existe se alguma parseou. Representá-la como `Decimal | None` criaria um ramo que
**não dispara**, e a primeira versão desta implementação fez exatamente isso: o
ramo de ausência publicava `economia = None` **sem motivo**, violando o invariante
da [[ADR-402]] (`campo null ⟺ motivo não-null`) num caminho que nenhum teste
parametrizado alcança. A garantia passou a ser do construtor. O fallback para o
bruto continua proibido — ele é o defeito que esta ADR fecha.

### D3 · A reconciliação `IR_tabela(base) ↔ ir_devido_brl` é observabilidade, não gate

A declaração traz **os dois**: a base e o imposto apurado. Recomputar o imposto
pela tabela sobre a base declarada e comparar com `ir_devido_brl` é o cross-check
natural — mas ele **não vira guardrail** nesta ADR.

Motivo medido, não conservadorismo: em 2026-08-21 o guardrail `_soma_retidos_irpf`
do E1.6 estava **saturado** (disparava em 100% das runs) e por isso era inútil,
capando confidence sempre. Ligar um segundo guardrail sobre extração que ainda
churna repete a classe. Sai `WARNING` estruturado com a divergência; promover a
gate exige a distribuição medida primeiro.

### D4 · O redutor compõe dentro de `economia_diferencial`, com as duas variáveis

Escopo da [[A40.l64]] PR3, desbloqueado por esta ADR. O redutor entra **dos dois
lados** da diferença (não se move com o aporte, por indexar no bruto), e a
clipagem em zero é **por lado** — é ela que produz toda a não-linearidade. O
contrato tipado do redutor é co-localizado em `FiscalParameters`, com o teto de
banda **derivado**, nunca armazenado: guardá-lo reproduziria na row a capacidade
de discordar de si mesma.

### D5 · IRPFM fica fora

Base própria (renda **total** recebida, não tributável) e deduções próprias.
[[A40.l64]] PR4, ADR separada.

## Consequências

- `CapacidadePgblIRPF` ganha `base_calculo_anual`; `IRPFAnalyzer` ganha o agregador.
- A economia publicada **muda de valor** para quem tem deduções — para menos, porque
  a base é menor que o bruto e o imposto marginal cai. É correção, não regressão.
- A `aliquota_marginal` passa a resolver a faixa que contém a **base**, não o bruto.
  Corrige o defeito que a [[A40.l34]] registrou (*"o param já se chama
  `base_calculo_anual_brl_cents` e o call-site passa o bruto"*) sem tocar no D6 da
  [[ADR-375]], que sempre falou de base.
- Golden e snapshot que citarem economia ou marginal precisam de rebaseline
  declarado.

## Limitação que esta ADR NÃO fecha, e torna visível

`base_calculo_anual(ano)` soma a base de **todas** as declarações do ano, igual ao
`rendimentos_tributaveis(ano)` que ela substitui no cálculo. Aplicar a tabela
progressiva sobre a soma familiar **não é como o IRPF funciona** — cada declarante
apura na própria base, e a progressividade não é aditiva: `IR(a + b) ≥ IR(a) + IR(b)`.

A conflação é **pré-existente** (o bruto já era familiar) e esta ADR não a piora —
mas ao trocar o nível pela grandeza certa ela deixa de estar escondida atrás de um
erro maior. O fix é apurar por declaração e somar depois, que é o que
`pgbl_capacidade_dedutivel` já faz para o teto ([[ADR-402]] D3) e o que o
`financial-planner` nomeou como a unidade correta: **a declaração, não o CPF nem a
família**.

Fica com a [[A40.l65]] §Escopo 2, que é dona da âncora de declarante — sem ela não
há por onde particionar. Enquanto não fechar, a economia publicada é **teto
superior** para família com dois declarantes: superestima, nunca subestima.

## Alternativas consideradas

**Derivar a base pelo desconto simplificado (20%, teto R$ 16.754,34).** Recusada:
inventa a escolha do contribuinte. Mede errado justamente o modelo completo, e o
`financial-planner` mediu que na banda do redutor a escolha simplificada×completa
**domina** o resultado — em bruto R$ 70.000 sem outras deduções, o aporte de 12%
perde para o desconto simplificado e a economia real é zero **por escolha de
modelo**, não por redutor.

**Usar `ir_devido_brl` declarado como primeiro termo da diferencial.** Recusada:
mistura valor declarado com valor computado, e o segundo termo
`IR(base − aporte)` só existe computado. A diferença entre dois regimes de origem
não é interpretável; o D3 preserva o valor declarado como testemunha, que é o
papel dele.

**Manter o bruto e ajustar o redutor.** Recusada: não há ajuste possível. As bandas
do redutor são definidas em bruto e os tetos em base — nenhum coeficiente único
reconcilia as duas, e foi tentar isso que produziu a leitura de que a tabela da
norma "não fecha".
