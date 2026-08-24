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

> ## ⚠️ Ataque medido — 2026-08-24: **a recusa desarma sozinha em 2027-01-01**
>
> Medido contra `main` (`7ed61f04`). Nada implementado — só medição. O PR1 segue
> entregue e correto **para 2026**; o que abaixo se mede é o que ele não cobre.
>
> ### 1 · A recusa é fail-open no eixo do ano, e a data do desarme já está marcada
>
> A seed de `fiscal_parameters` cobre **2024–2026** com `effective_to = date(year, 12, 31)`
> (`y3z4a5b6c7d8_seed_fiscal_2024_2026.py:74`), e
> [`list_covering_period`](../../../../backend/app/repositories/fiscal_parameter_repository.py)
> não tem clamp: o predicado é `effective_from <= início AND (effective_to IS NULL
> OR effective_to >= fim)`. Rodado sobre SQLite com as 3 rows da seed:
>
> | período pedido | resultado |
> |---|---|
> | 2026 | row `year=2026` |
> | **2027** | **`FiscalParameterNotFound`** |
> | 2028 | `FiscalParameterNotFound` |
>
> [`analyze_finances:2183`](../../../../scripts/analyze_finances.py) captura
> `except Exception`, imprime um `[warn]` e deixa `fiscal_parameters = None` — o
> construtor vira `PrevidenciaConfig.from_fiscal(FISCAL_CONFIG)`, e `FISCAL_CONFIG`
> lê `config/parametros_fiscais.json`, **path proibido** e inexistente desde a
> A7.2b ⇒ `{}` ⇒ `irpf_faixas=()` e `regime_completo=True` (default do dataclass).
>
> Medido no caso exato do §Critério de aceite 1 (bruto anual R$ 70.000):
>
> | config | `economia_ir_anual` | `aporte_mensal` | `aliquota_marginal` |
> |---|---|---|---|
> | AC2026 · row presente (hoje) | **ausente** com motivo | ausente | ausente |
> | **AC2027 · row ausente** | **R$ 630,00** | R$ 700,00 | 7,5% (fallback) |
> | AC2027 · row semeada sem o marcador | R$ 2.310,00 | R$ 700,00 | 27,5% |
>
> O default `True` está **certo** para o dict legado — o comentário em
> `PrevidenciaConfig` argumenta isso e o argumento se sustenta. O defeito é que
> **"row ausente" cai no mesmo ramo que "legado sem defeito medido"**: um ano sem
> seed é indistinguível de um workspace pré-A7.2b, e o silêncio favorece publicar.
>
> ### 2 · O golden que certifica a recusa não pode ficar vermelho nesse eixo
>
> `fiscal_store_do_seed(year)` ([`tests/pipeline_golden_substrate.py:143`](../../../../tests/pipeline_golden_substrate.py))
> faz `tabelas[max(a for a in tabelas if a <= year)]` e devolve
> `InMemoryConfigStore(fiscal_by_year={year: fiscal})`. Rodado:
>
> | `fiscal_store_do_seed(ano)` | `regime_completo` |
> |---|---|
> | 2026 | `False` |
> | 2027 | `False` |
> | 2030 | `False` |
>
> **O clamp é invenção da fixture; a produção não o tem.** A fixture foi endurecida
> contra exatamente o rollover que a produção ainda sofre — e o comentário dela
> nomeia o risco (*"`{2026: fp}` passa hoje e vira KeyError silencioso em 2027 —
> engolido pelo `except Exception`"*). Consertaram a fixture, não o caminho de
> produção. Logo `test_regime_incompleto_retem_a_economia_no_payload` fica **verde
> para sempre** nesse eixo: instrumento cego ao efeito por construção.
>
> ### 3 · O §Critério de aceite 1 já passa — e passa cego à banda
>
> A retenção chaveia no marcador do **ano**, não na banda do redutor. Medido com
> bruto anual R$ 300.000 (fora da banda, onde a diferencial ingênua está **certa**):
> AC2026 retém igual, com o mesmo `regime_fiscal_incompleto`. Ou seja, o critério
> não distingue "redutor modelado certo" de "redutor não modelado" — e continuaria
> passando com o PR2/PR3 implementados **errados**.
>
> ### 4 · O §Critério 1 contradiz o invariante da [[ADR-402]] assim que o redutor existir
>
> Modelado o redutor, a resposta honesta para bruto R$ 70.000 é **economia = R$ 0,00**
> (o redutor zera o IR com e sem o aporte). Mas o invariante da [[ADR-402]] —
> declarado no `e5_analysis.schema.json` e enforçado por
> `test_zero_publicado_nunca_carrega_motivo_de_ausencia` — é `campo == 0 ⇒ motivo is None`:
> o zero legítimo sai **como número, sem motivo**. É exatamente o que o §Critério 1
> proíbe (*"'não se aplica' com motivo, nunca um número"*).
>
> ⇒ **§Critério 1 e §Critério 3 estão em tensão**: o 3 pede que o regime fique
> completo; o 1 proíbe a saída que um regime completo produz. Um dos dois muda antes
> do PR3, e é decisão de domínio (`financial-planner`), não de implementação.
>
> ### 5 · O PR2 é mais barato do que a lane sugere — o insumo já está no contrato
>
> `IRPFBracket` carrega `deducao_brl_cents`, então `IR(base) = base × alíquota − dedução`
> sai de `FiscalParameters.ir_brackets_anual` **hoje**. Não falta contrato: falta a
> função. `resolve_faixa_marginal` devolver só a alíquota é escolha do D6, não
> limitação. Confirmada a dívida do D5: `_economia` segue
> `restante × alíquota_marginal / 100`
> ([`previdencia_analyzer.py`](../../../../pipeline/domain/services/previdencia_analyzer.py)).
>
> ### 6 · A tabela do redutor **nesta lane** não fecha no piso da banda anual
>
> Conferidas as duas bandas contra os próprios coeficientes da lane:
>
> | banda | no piso | topo declarado | diferença |
> |---|---|---|---|
> | mensal (`978,62 − 0,133145 × R`) | R$ 312,895 em R$ 5.000 | R$ 312,89 | **R$ 0,005** |
> | anual (`8.429,73 − 0,095575 × R`) | R$ 2.695,23 em R$ 60.000 | R$ 2.694,15 | **R$ 1,08** |
>
> As duas zeram no teto da banda (R$ 7.350 / R$ 88.200). A mensal fecha ao centavo;
> a anual não. O §Escopo 1 pede contrato tipado com bandas e coeficientes — quem
> transcrever precisa **decidir qual dos dois números é o piso anual**, e um teste
> de continuidade na borda reprova a tabela como está escrita aqui. Não é conferência
> do texto da lei: é a tabela desta lane discordando de si mesma.
>
> ### Encaminhamento
>
> Os itens 1 e 2 **não são desta lane**: valem mesmo que o redutor nunca seja
> modelado. E **não têm dono declarado** — a [[A40.l56]] está `shipped`, e o
> §Deferimento dela é sobre conferir os valores de 2024-2026 no DOU, não sobre
> semear anos futuros. Rotear para lá fecharia ciclo sobre lane morta. Precisa de
> lane própria, e o conserto barato não é semear 2027: é **fechar o fail-open** —
> "row ausente" tem de ser distinguível de "dict legado", porque a seed vai
> envelhecer de novo em 2028.
>
> Os itens 3, 4 e 6 são desta lane e são de **decisão**, não de código — o 4 precisa
> do `financial-planner` antes do PR3.

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
