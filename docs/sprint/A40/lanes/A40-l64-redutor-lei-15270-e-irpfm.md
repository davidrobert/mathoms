---
id: A40.l64
type: lane
title: "Redutor da Lei 15.270/2025 e IRPFM: a economia diferencial de PGBL está errada para AC2026 em diante"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l64-redutor-lei-15270-e-irpfm
owner: financial-planner
adrs:
  - "[[ADR-375]]"
  - "[[ADR-389]]"
depends_on:
  - "[[A40.l56]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l64 — `redutor-lei-15270-e-irpfm`

> ## ⚠️ Correção de premissa — 2026-08-17: **a recusa não existia**
>
> O cabeçalho abaixo afirma *"a recusa já lê o dado"*, e o §Enquanto esta lane não
> fecha repete *"a recusa lê a row"*. **Medido contra `main` em 2026-08-17: nenhum
> consumidor de `regime_completo` existia.** O marcador era escrito pela migration,
> parseado por `fiscal_parsers`, testado no parser — e ignorado por todo o domínio
> (`rg regime_completo` fora de `docs/`: migration, parser, dataclass, testes de
> parser; zero leitores de regra).
>
> **O efeito não era latente.** [`analyze_finances:2176`](../../../../scripts/analyze_finances.py)
> carrega a row do ano **corrente** (`date(TODAY.year, 1, 1)`), que hoje é AC2026 —
> a row marcada incompleta. O D5 publicava economia de IR sobre uma tabela que a
> própria row declara insuficiente. Para tributável até R$ 60k/ano o imposto já é
> zerado pelo redutor: **o número publicado era economia inexistente, em produção,
> sem nenhuma trava.**
>
> O seam era `PrevidenciaConfig.from_fiscal_parameters`, que recebia
> `FiscalParameters` inteiro e **descartava** o marcador.
>
> **Segundo achado, maior:** a [[ADR-375]] **D5** diz *"a economia passa a ser
> diferencial `IR(base) − IR(base − aporte)` … **encerra o `limite × marginal`**"*.
> O código em `previdencia_analyzer` ainda faz `restante × alíquota_marginal` — o
> instrumento que o D5 encerrou. **Não existe função `IR(base, ano)` no domínio**
> (`irpf_faixa_marginal` só resolve a faixa, D6). Ou seja: a lane descreve o D5
> como implementado-e-errado-para-2026; ele **nunca foi implementado**.
>
> ### Ordem de trabalho revista
>
> | PR | O quê | Estado |
> |---|---|---|
> | **PR1** | A recusa vira real: `regime_completo=false` retém `economia_ir_anual` e `aporte_mensal`, com motivo que cita a lei e o ano | ✅ **entregue 2026-08-17** — fecha o §Critério de aceite 1 |
> | **PR2** | `IR(base, ano)` existe e o D5 vira diferencial de fato — a dívida da [[ADR-375]] D5 | ⬜ |
> | **PR3** | Contrato tipado do redutor (bandas, coeficientes, vigência) + ADR própria | ⬜ |
> | **PR4** | IRPFM — confirmar base e abatimentos no texto da lei **antes** de implementar (§Escopo 2) | ⬜ |
>
> O §Critério 3 (`regime_completo` de AC2026 vira `true`) **não** é do PR1 e segue
> aberto: vira `true` só depois do PR3 + PR4.
>
> **Fica pendente de decisão do dono** (gatilho `financial-planner`, §Delegação do
> CLAUDE.md): o PR1 mantém `aliquota_marginal` publicada. Na banda R$ 60k–88,2k o
> redutor sai a `0,095575` por real, o que soma ~9,6 p.p. à alíquota **efetiva**
> marginal — então o número da tabela, sozinho, também engana nessa faixa. Retê-lo
> é mudança de card e não cabia no PR1 sem decisão de domínio.

> **Destravada em 2026-08-16** — a [[A40.l56]] shipou (#1483) e o marcador
> `regime_completo` existe na row de 2026 com
> `componentes_ausentes: ["redutor_lei_15270", "irpfm"]`. ~~A recusa já lê o dado~~
> (falso — ver correção acima); esta lane é quem torna o `true` possível.
>
> Aberta em 2026-08-15 no co-design da l56 (`financial-planner`; escopo fechado
> por `senior-cto`).

## Problema

A [[ADR-375]] fez a S8 dona única do limite PGBL publicado, e o D5 dela é a
economia diferencial `IR(base) − IR(base − aporte)`. **Essa fórmula está errada
para o ano-calendário corrente.**

A Lei 15.270/2025 (sancionada 26/11/2025, vigente para rendimentos pagos a
partir de 01/01/2026) **não alterou faixas nem parcelas** — a mensal de 2026 é
idêntica à de mai/2025. Ela criou duas coisas que a tabela progressiva não
modela:

### 1 · Redutor, aplicado depois do imposto da tabela

|  | banda 1 | banda 2 |
|---|---|---|
| **mensal** | até R$ 5.000,00 → redutor até R$ 312,89 (zera o IR) | R$ 5.000,01–7.350,00 → `978,62 − 0,133145 × rendimento` |
| **anual** | até R$ 60.000,00 → redutor até R$ 2.694,15 | R$ 60.000,01–88.200,00 → `8.429,73 − 0,095575 × rendimento` |

**O redutor é função do rendimento tributável BRUTO, não da base de cálculo** —
a RFB é explícita no exemplo 5. Isso significa que ele **não cabe em
`ir_brackets`**: é variável independente e pede objeto próprio.

Consequência para o D5: como o redutor não se move com o aporte, a fórmula
honesta é

```
economia = max(0, IR_tabela(base) − redutor(bruto))
         − max(0, IR_tabela(base − aporte_dedutivel) − redutor(bruto))
```

Quem tem tributável anual ≤ R$ 60.000 **já paga zero**, e a diferencial ingênua
publicaria uma economia que não existe. Na banda R$ 60k–88,2k a economia é
parcial e não-linear.

Não é caso de borda: é cônjuge ou dependente com renda modesta num
workspace-família — e workspace **é** família, não indivíduo.

### 2 · IRPFM pode anular a economia no ICP principal

Para renda total anual acima de R$ 600 mil, o imposto mínimo (escalonado até 10%
em R$ 1,2M) é calculado sobre a renda total e o IR devido pela tabela é abatido
dele. Reduzir o IR-tabela em R$ X aumenta o complemento em até R$ X — economia
líquida tendendo a zero enquanto o mínimo vincula.

Se o D5 publicar "economia de R$ N" para um cliente PJ nessa faixa, **o produto
está prescrevendo com o sinal errado** — e é exatamente o público do Mathoms.

## Escopo

1. Contrato tipado para o redutor (bandas, coeficientes, vigência), separado de
   `ir_brackets` porque a base é outra. Fonte e vigência declaradas, como a
   [[ADR-389]] exige das tabelas.
2. Modelagem do IRPFM: confirmar a composição exata da base e dos abatimentos no
   texto da lei **antes** de implementar.
3. D5 passa a compor redutor e IRPFM; `regime_completo` da row deixa de ser
   `false` para AC2026.
4. ADR própria — a [[ADR-389]] declara explicitamente que modelá-los é
   não-objetivo dela.

## Enquanto esta lane não fecha

A [[A40.l56]] entrega o desbloqueio do D5 **qualificado**: liberado para
`AC ≤ 2025`; `AC ≥ 2026` retido por `regime_completo: false` com
`componentes_ausentes: ["redutor_lei_15270", "irpfm"]`. ~~A recusa lê a row.~~

> **Corrigido em 2026-08-17:** a recusa **passou a** ler a row no PR1 desta lane.
> Até então o marcador era inerte e a retenção descrita neste parágrafo não
> acontecia — ver §Correção de premissa no topo.

## Critério de aceite

- Caso na banda do redutor (bruto anual R$ 70.000, AC2026) produz **"não se
  aplica" com motivo**, nunca um número.
- Caso acima de R$ 600k exercita o IRPFM e não publica economia que o mínimo
  absorve.
- `regime_completo` de AC2026 vira `true` só quando os dois componentes existem.

## Fora de escopo

- IRRF de 10% sobre dividendos acima de R$ 50 mil/mês por PJ pagadora, também
  criado pela Lei 15.270/2025. É material para o ICP e merece lane em S8, mas
  não toca o D5.
- **Simplificada vs. completa** (deferimento herdado da [[ADR-375]] condição 1):
  para quem declara simplificada, a economia real é
  `IR_simplificada − IR_completa_com_PGBL`, e é nesse contribuinte que o PGBL
  costuma valer mais. Publicar zero para ele é falso negativo, não erro.
