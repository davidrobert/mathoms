---
id: ADR-399
type: adr
title: "Alvo de KPI tem procedência declarada; o LLM seleciona identidade, não autora número"
status: Decidido
phase: r7.PE-2/FP-6
date: "2026-08-19"
amended_at: ["2026-08-27"]
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-134]]"
  - "[[ADR-143]]"
  - "[[ADR-191]]"
  - "[[ADR-202]]"
  - "[[ADR-294]]"
  - "[[ADR-296]]"
  - "[[ADR-340]]"
  - "[[ADR-387]]"
  - "[[ADR-396]]"
tags:
  - type/adr
  - status/decidido
  - area/llm
  - area/dominio
aliases:
  - "ADR 399"
  - "procedência do alvo de KPI"
---

# ADR-399 — Alvo de KPI tem procedência; o LLM seleciona, não autora

> **Decidido em 2026-08-19** na remediação de **PE-2** + **FP-6** (P1) do §r7 de
> [[PIPELINE-REVIEWS-active]]. Implementação **em ondas** — ver §Estado de
> implementação antes de §Consequências.
>
> ⚠️ **Emendada em 2026-08-27** ([[A40.l89]]): o vocabulário fecha em **13 chaves**
> (entram `renda_passiva_cobertura`, `if_prazo_ano`, `aliquota_efetiva_ir`;
> `protecao_cobertura` vira `protecao_custo_premio`), o enum passa a ser **fechado de
> verdade** — sem chave de escape —, e a correção alcança o artefato **congelado** por
> supressão na leitura. Ver §Emenda 2026-08-27.

## Contexto

`metricas[].target` do parecer — o valor-alvo que a família deve perseguir — era
string livre autorada pelo LLM. Dois defeitos medidos em runs armazenados:

**PE-2 — o alvo migra sobre dado byte-idêntico.** `ratios.concentracao_imobiliaria`
= 34,86 nos dois runs; o alvo publicado foi `< 30%` e depois `< 35%`,
**atravessando o valor observado**. Violação virou conformidade sem nada ter
mudado no patrimônio. O limiar canônico do repo é **50%** ([[ADR-340]]): os dois
números do LLM estavam errados, em direções opostas — não é viés, é ruído. E no
run em que disse `< 30%`, o produto afirmou violação a uma família que, pelo
próprio canon, estava conforme.

**FP-6 — o alvo é mais frouxo que a meta declarada.** Para renda fixa, a família
declarou `alvo_pct = 51,55`; o parecer publicou `≤ 55%`. Pior, o `valor_atual`
publicado (76,0%, base carteira financeira) vinha de base diferente do alvo
(82,30%, base carteira líquida): **dois denominadores para o mesmo conceito no
mesmo payload**. O desvio implícito saía ~21pp contra os 30,75pp que o motor já
havia calculado em `desvio_pp`.

A causa não é instrução ruim de prompt. A persona **já** diz "não invente
números" (R1) e o modelo violou em 8 dos 10 casos, porque o schema declarava
`target` **obrigatório, string livre**: um campo required cujo valor não existe no
payload é uma máquina de fabricação. A prova pelo contrário está na única métrica
cujo alvo bate com o canon ao dígito — reserva de emergência, o único cujo valor
**já é publicado no E5**. Quando o número existe no payload, o modelo copia.

Instrução não é gate. E `seed` também não resolve: [[ADR-396]] registra que ele é
descartado em `anthropic/*`.

## Decisão

**D1 — `target` e `valor_atual` são derivados; o LLM emite `metrica_key`.** O
trabalho do modelo muda de *autorar o alvo* para *selecionar a identidade do KPI*
num vocabulário fechado (`METRICA_KEYS`). KPI fora do enum não pode ser emitido —
é o cap estrutural na fabricação. Padrão [[ADR-081]] (determinístico primeiro) e
mesma forma do `valor_renderizado` de [[ADR-296]], escrito pelo finalize.

`valor_atual` entra junto e **não** é escopo extra: derivar só o alvo deixaria o
par incoerente (alvo de uma base ao lado de observado de outra) e fecharia o FP-6
apenas pela metade — o desvio seguiria subestimado. Cada KPI declara `base`, e as
duas pontas saem da mesma.

**D2 — Precedência: alvo declarado pela família vence limiar de doutrina.** Na
metodologia dona desta métrica, o desvio só é definido contra o alvo declarado — substituir `alvo_pct` por
número de config não torna o conselho mais correto, **destrói a métrica**, porque
`desvio_pp` é o que decide para onde vai o próximo aporte. E publicar alvo mais
frouxo que o compromisso da família é o produto absolvendo-a da própria meta.
Quando o declarado viola um limiar canônico, publica-se o declarado como `target`
e o limiar vira `risco` — nunca um meio-termo fabricado.

**D3 — Alvo sem fonte única é órfão: publica sem `target`, com `motivo`.** Nunca
número inventado, nunca `needs_review` (ausência de meta é fato esperado e
frequente; usar o canal de retenção para o caso comum queima o canal), e nunca
omitir a métrica — a linha segue publicada como observacional para não perder o
sinal. Quatro órfãos **por decisão de domínio**, não por lacuna:

| KPI | Por quê |
|---|---|
| `carteira_trs` | [[ADR-191]] §D5: TRS efetiva é yield observado e não tem comparador. `≥ IPCA+4%` e `≥ 6% real` diferem em 2pp reais **e** comparam yield de fluxo com retorno total, induzindo "vender growth para perseguir DY" — o erro de iniciante que a métrica existe para evitar |
| `protecao_cobertura` | [[ADR-387]] proíbe afirmar capital ideal sem inventário confirmado. O publicado (`≥ 60 meses`) era 2 a 4× mais frouxo que o canon (10× renda anual × fator + dívidas), na métrica cujo erro é irreversível para os dependentes |
| `taxa_poupanca_recorrente` | RV2-24: `poupanca_referencia_pct` (25) e `pontos_fortes_taxa_poupanca_min_pct` (30) descrevem o mesmo conceito sem precedência declarada |
| `if_progresso` | O alvo é o par (ano declarado, 100%); o ano sozinho promete estado futuro sem a probabilidade do cone (persona R20) |

**Regra de segurança:** o resolver encontrando duas fontes para o mesmo conceito
**não escolhe** — publica órfão. Escolher seria inventar regra de domínio com
carimbo de procedência, pior que o alvo do LLM por parecer autoritativo.

**D4 — Leitor único do limiar **na rota do `target` publicado**, no produtor.** O
catálogo vive em `pipeline/domain/services/kpi_target_catalog.py` e é o leitor
único **do alvo que o parecer publica**. Precisa ser o produtor porque só ele
conhece a config **efetiva** após override por workspace ([[ADR-134]]) —
`concentracao_alerta_pct` entra por parâmetro, não por global; um leitor no
backend teria de reimplementar a resolução ([[ADR-143]], methodology = code).

**O escopo é essa rota, não o repo.** Os leitores pré-existentes de
`endividamento_maximo_pct` (`pontos_fortes_analyzer.py:66` e
`pontos_urgentes_analyzer.py:65`, com o default inline `20` duplicado nos dois) e
de `concentracao_alerta_pct` (`real_estate_metrics_aggregator.py:142`)
**permanecem** — não foram unificados e não estão no escopo desta ADR. Redação
anterior dizia "leitor único de cada constante", o que a medição refuta: o
catálogo é um **terceiro** leitor. Unificar os demais é trabalho à parte.

## Estado de implementação (2026-08-21)

`Decidido` refere-se à **decisão**, não à cobertura. Registro de fato, **não**
emenda — nenhuma decisão acima mudou.

**Em produção, o parecer continua publicando `target` autorado pelo LLM.** O
defeito que PE-2 e FP-6 descrevem segue vivo no relatório entregue.

| decisão | estado em `main` |
|---|---|
| **D1** — `target`/`valor_atual` derivados, LLM emite `metrica_key` | **não construído.** `Metrica` não tem `metrica_key`, `target` segue required-string, e nada estampa o alvo no pós-LLM |
| **D2** — precedência declarado > doutrina | refletida no catálogo (#1557, `13deaa8f`); **sem consumidor** enquanto D1 não existir |
| **D3** — órfão publica `motivo`, nunca número | idem D2 — o invariante vive no catálogo e no `e5_analysis.schema.json` |
| **D4** — leitor único na rota do `target` | catálogo é o leitor único **do alvo publicado** (#1557). Os leitores pré-existentes citados em D4 **permanecem** |
| publicação de `kpi_targets` no payload E5 | #1591 — **habilita** D1, não o entrega |

Dono, faltantes (a)–(d) e condição de retomada: **§Deferimento D3 (2026-08-21)**
em [[PIPELINE-REVIEWS-active]].

## Consequências

- Cobertura **do catálogo** medida sobre o payload do run r7: **6/10 resolvem,
  4 órfãos documentados** (não é cobertura do parecer publicado — ver §Estado). A premissa "toda métrica % vira drop → a seção esvazia" não se
  materializa: nenhuma métrica é omitida.
- O bloqueio declarado do **catálogo KPI não se aplica a este eixo** — ver
  §Bloqueio abaixo.
- `Metrica` **passará a ter** `metrica_key`, com `target` `Optional` (D1 — ver §Estado). Bump do schema de
  saída + `PROMPT_VERSION` ([[ADR-396]] D3 explica por que o bump é load-bearing).
- O LLM emite **menos** tokens (perde `target` e `valor_atual`, ganha um enum
  curto).

## Bloqueio do catálogo KPI: não procede para o eixo `target`

O PE-2 estava registrado como bloqueado pela dependência do catálogo KPI (RV2-01),
sob o argumento de que `parecer_citation_catalog.py` é money-only e sem catálogo
curado toda métrica % viraria drop. **A dependência não existe no código, e está
invertida.** Evidência:

1. `metricas[]` **não tem campo de âncora** — nem `evidencia_path`, nem
   `ancoras[]`. O catálogo de citação alimenta riscos/sugestões/pontos_fortes; não
   tem superfície de contato com `metricas[]`.
2. O catálogo é **input-side**: seu único consumidor renderiza um bloco markdown
   para dentro do prompt. O verificador de saída não o importa — resolve por
   `get_e5_jsonpath`. O catálogo decide o que o LLM é *informado* que pode citar,
   não o que *resolve*.
3. Âncora é afirmação **sobre o payload** ("este número está em `$.path`"); alvo é
   afirmação **normativa** ("deveria ser X"). Prescrição não se ancora em JSONPath
   — ancora-se em config/goals. Eixos ortogonais.

**Inversão:** um registro `metrica_key → {observado_path, target}` entrega à
RV2-01 o path resolvível por métrica **sem** tocar `monetary_only`. Este trabalho
**destrava** a ancoragem de percentual; não é destravado por ela. O **PE-1**
(rota de âncora de citação) segue aberto por mérito próprio, mas deixa de ser
bloqueante — e encolhe, porque perde a exigência de curar limiar normativo.

## Emenda 2026-08-27 — o enum fecha em 13 chaves, e a leitura subtrai

> **A D1 não muda: o LLM seleciona, não autora.** O que muda é o *tamanho* do
> vocabulário, o *nome* de uma chave, e o *alcance* da correção.

**E1 — corrigir o vocabulário, não abrir exceção.** Das 10 métricas publicadas no run
da U1, **4 estavam fora** do enum de 10 chaves. Fechar sem corrigir apagaria 4 linhas do
painel; abrir uma chave de escape genérica devolveria ao modelo os campos que a D1
fechou — a máquina de fabricação **realojada de `target` para `valor_atual`**, num campo
que a D1 fechou de propósito e junto ("renda passiva mensal *projetada*" é R$/mês **sem
produtor no payload**, publicado ao lado de números derivados e lido como medido).

Regra de admissão, agora explícita: admite-se chave quando **(a)** existe fonte
determinística única para o limiar, **ou (b)** a ausência de alvo é ela própria regra de
domínio decidida e vale publicar ao usuário.

| chave | veredito |
|---|---|
| `renda_passiva_cobertura` | **admitida** por (a) — limiar **100 `>=`**, que não é doutrina: é o **ponto fixo da razão** (numerador = denominador), o único número que não seria uma escolha. Base declarada `despesa_essencial_mensal_12m`; `status != "ok"` ⇒ órfã, **nunca 0%** |
| `if_prazo_ano` | **admitida** por (b) — o "atual" só existe como percentil de cone, e [[ADR-361]] intercala a flag de censura ao lado de cada ano |
| `aliquota_efetiva_ir` | **admitida** por (b) — "monitorar tendência" *é* a regra; alíquota efetiva é descritiva, e o limiar dependeria do regime |
| renda passiva mensal *projetada* | **recusada** — sem produtor no payload, não entra |

**E2 — `protecao_cobertura` → `protecao_custo_premio`.** A chave nomeava um conceito que
o payload **não publica**: não existe agregado de capital segurado no schema, por desenho
— é a própria [[ADR-387]]. O que `pct_renda_anual` entrega é prêmio/renda. Medido:
6.022,27 / 0,005686 ⇒ renda ≈ 1,06 MM, logo **razão 0–1** declarada como `pct`; quem
lesse pelo contrato publicaria 0,0057% no lugar de 0,57%. Agora `unidade: ratio_0_1`,
base `renda_anual_liquida`.

**E3 — `rotulo` entra no catálogo.** O nome da métrica carrega domínio e rótulo autorado
não é gateável: cobrir 100% da despesa **essencial** é o marco de segurança, não a
independência (medida contra o custo de vida total). Publicar sem o qualificador ensina a
família a se declarar independente cedo demais.

**E4 — a correção alcança o artefato congelado, por SUPRESSÃO.** A D1 corrige o
write-path e não toca os **51 pareceres persistidos**, dos quais 42 publicam alvo
prescritivo para métrica que este catálogo declara órfã. A leitura passa a servir `target`
apenas quando o artefato traz `metrica_key`. **Backfill e derivação-na-leitura ficam
recusados**: o artefato é o registro forense do regime em que foi gerado ([[ADR-204]]
§D1/§D7), e recomputar o catálogo no backend reimplementaria a resolução de config
efetiva por workspace — o que a D4 existe para impedir — além de carimbar config de hoje
sobre E5 antigo. A regra é subtrativa: **a leitura só remove afirmação, nunca acrescenta
número a documento entregue.**

**E5 — o cap estrutural é o enum, e ele não tem escape.** Métrica fora do vocabulário
**não é emitível**. Chave nova exige passar pela regra de admissão acima — nunca um
número escolhido na hora, nunca um balde genérico.

**Fora desta emenda, com endereço:** o alvo determinístico do plano de ação
(`suggestion_rules.trs_target_pct`) e a prosa da E5 que entrega limiar ao modelo são
**leitores isentos pela D4** e migram para a [[A40.l90]], sob emenda própria — ver
§Deferimento datado 2026-08-27 da [[A40.l89]].
