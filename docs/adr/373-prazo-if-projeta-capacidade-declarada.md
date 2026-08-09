---
id: ADR-373
type: adr
title: "Prazo até a IF projeta capacidade declarada; aporte ausente é retenção nomeada, não inviabilidade"
status: Decidido
date: "2026-08-08"
relates_to: ["[[ADR-360]]", "[[ADR-369]]", "[[ADR-143]]", "[[ADR-167]]"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-373 — Prazo até a IF projeta capacidade declarada

## Contexto

`IFProjector._solve_prazo` resolvia `n` em `PV·(1+r)^n + PMT·((1+r)^n−1)/r = FV`
**apenas** no ramo `r > 0 and aporte_mensal > 0`. Todo o resto virava ausência,
empacotando três situações distintas num único `None` e num único motivo
("prazo até a IF não projetável com as premissas atuais").

| Caso | Verdade matemática | Antes |
|---|---|---|
| `r > 0`, `aporte > 0` | forma fechada | projeta |
| `r == 0`, `aporte > 0` | `n = (FV − PV)/PMT` | ausência |
| `aporte == 0`, `r > 0` | `n = ln(FV/PV)/ln(1+r)` | ausência |
| `aporte == 0`, `r == 0` (ou `PV == 0`) | não converge | ausência |

O [#1158](https://github.com/davidrobert/mathoms/pull/1158) trocou a sentinela
`999` (que virava "IF aos 1040 anos") por ausência honesta, mas não mexeu na
cobertura — item 6 do §Deferimento da [[ADR-360]].

Três fatos medidos ao abrir a decisão mudaram o enquadramento:

1. **`aporte == 0` nunca é declaração.** `goal.aporte_mensal.schema.json` exige
   `exclusiveMinimum: 0` e o DTO usa `gt=0` — a família **não consegue**
   declarar R$ 0. O zero só pode ser ausência de Goal, campo nulo ou config
   ausente.
2. **`retorno_real_anual_pct == 0` É declarável.** `goal.if.schema.json` aceita
   `minimum: 0` — é a postura "poupo e não conto com o mercado".
3. **Ausência de retorno virava 0% declarado.** `_serialize_if_goal` emite a
   chave com `None` quando o Goal não a traz, então
   `goals_cfg.get("retorno_real_anual_pct", 6.0)` **nunca dispara o default** e
   `_safe_float(None)` devolve `0.0`. Os dois estados eram indistinguíveis.

E, no perfil do dogfood (PV ~13 M, meta 100 M, 6% real, aporte 0), o caso
retido converge em **~35 anos** — número que o produto sabe calcular e nunca
mostrou.

## Decisão

**O prazo realista projeta capacidade declarada.** Três consequências:

### D1 — `r == 0` com aporte declarado passa a projetar

`n = (FV − PV)/PMT`. Retorno real zero é premissa legítima e declarável;
recusar a projeção seria o produto ser **mais pessimista que o pessimismo
declarado da própria família**. É a projeção mais conservadora possível.

### D2 — Aporte não declarado continua ausente, e o motivo nomeia o insumo

`n = ln(FV/PV)/ln(1+r)` converge, mas não sai sob `prazo_anos_realista`.
Publicá-lo seria o produto **escolher a premissa "você não aporta"** em nome da
família e reportar a consequência como o prazo dela — mais perto de
fabricação-por-default que de disclosure. Duas razões independentes:

- **Contrato.** `prazo_anos_realista` é metade do par travado pela
  [[ADR-369]] D2: *prazo declarado* (compromisso) vs *prazo realista*
  (capacidade), com a folga `declarado − determinístico` movendo
  `prob_if_ate_prazo_declarado`. Aporte zero não é capacidade — é capacidade
  não exercida. Escrever ali redefiniria a folga de todo workspace sem aporte.
- **Metodologia.** Prazo até a IF é leitura de **alavanca**: quanto o
  comportamento da família muda o horizonte. A versão a aporte zero é a única
  em que esse comportamento é definicionalmente irrelevante, e ocuparia o slot
  reservado a "quanto tempo dado o seu plano". Sem PMT também não há
  rebalanceamento por aporte a executar — o instrumento do método.

O motivo deixa de ser um só. **Nenhum dos dois diz "não projetável"** — a
redação antiga nomeava a nossa incapacidade em vez do insumo que falta, e era
literalmente falsa no caso comum:

| Estado | Motivo |
|---|---|
| Aporte não declarado | "você ainda não declarou quanto pretende aportar por mês, e o prazo até a meta é consequência direta desse número" |
| Sem trajetória (`r == 0` **e** aporte 0) | "com o patrimônio parado (retorno real zero) e sem aporte mensal declarado, não há trajetória até a meta" |

Só o segundo pode afirmar inviabilidade.

### D3 — Ausência de retorno cai no default; `0` declarado permanece `0`

`default_if_absent(val, 6.0)` no boundary: `None` → 6,0 (o default que a
docstring de `IFProjectorConfig` já prometia e que estava inalcançável), valor
explícito → ele mesmo, inclusive `0`. Sem isto, D1 passaria a **projetar** um
prazo linear sobre uma premissa que ninguém declarou — a fabricação que a
[[ADR-360]] fechou, reaberta por outra porta.

Não é `raise`: o campo é `required` no schema, então a ausência só ocorre em
Goal legado, e derrubar o run inteiro por causa dela inverteria o trade.

### D4 — Fonte única do prazo

`solve_prazo_anos` passa a ser a única implementação da fórmula.
`CenariosConjugeAnalyzer._compute_prazo` era uma segunda cópia com o mesmo
guard; preencher um ramo só de um lado faria a S7 dizer "N anos" e o Apêndice C
"não projetável" para a mesma família, com as mesmas premissas.

## Consequências

- `prazo_anos_realista`, `ano_if`, `idade_titular_if` e `idade_conjuge_if`
  continuam `null` no dogfood — o hero KPI e a stat "Ano projetado" seguem "—".
- Workspace com retorno real 0% e aporte declarado passa a **ganhar** prazo
  onde antes tinha ausência.
- Workspace cujo Goal não traz `retorno_real_anual_pct` passa de 0% para 6%
  — muda `retorno_esperado_pct_aa` no payload e, por tabela, o gatilho de
  carry-trade de `rule_endividamento_perigoso`.
- Mudança de valor no E5 invalida o cache do parecer dos workspaces afetados
  (`sha256(json.dumps(e5_data))`). Nenhuma chave nova entra, então o
  workspace não afetado não paga re-geração.
- A conclusão do `waterfall_if` (S1) deixa de afirmar que aportes disciplinados
  fecham o gap quando não há aporte declarado. Era defeito **preexistente**,
  visível antes desta ADR ("R$ 0,00/mês = R$ 0,00 em N/D anos"), e teria ficado
  fluente — e portanto pior — se D1 entrasse sozinha.

## Alternativas rejeitadas

- **Projetar aporte zero sob `prazo_anos_realista`.** Corrompe o par da
  [[ADR-369]] D2 e endossa como plano um cenário que a metodologia de
  referência não reconhece como plano.
- **Chave nova (`prazo_anos_sem_aporte_novo`) já nesta decisão.** O número só
  é honesto **dentro da frase** que nomeia a premissa e a alavanca; chave sem
  frase é âncora solta, e `$.goals` vai cru para o LLM do parecer. Deferido
  com dono — ver §Deferimento na [[A40.l26]].
- **`needs_review` para `r == 0`.** É mecanismo de documento/categorização; não
  existe neste stage e seria padrão estrangeiro.
- **`raise` no boundary para retorno ausente.** Ver D3.

## Deferido (2026-08-08)

O **piso a aporte zero exibido dentro do motivo** (o "~35 anos" do dogfood),
a decisão simétrica sobre o cone Monte Carlo — que **já publica** sob PMT = 0,
com `prob_if_ate_horizonte_simulado` medido em 0,58 no dogfood — e a grade de
sensibilidade da premissa de retorno. Condição de retomada e dono em
[[A40.l26]] §Deferimento; pareia com a **metade deferida** da [[A40.l25]] —
que shipou o #1338 e segue `in_progress` pelo mesmo bloqueio: número novo na
tela exige a nota de recalibração da §Nota one-shot desta ADR-360, e ela
cobre o cone e o prazo de uma vez só.
