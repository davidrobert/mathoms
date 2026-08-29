---
id: ADR-306
type: adr
title: "Política de base temporal de mensalização no E5 — janela canônica 12m + rótulo de janela por bloco"
status: Decidido
phase: A28
date: "2026-07-03"
amended_at: ["2026-07-31", "2026-08-11", "2026-08-14", "2026-08-29"]
relates_to:
  - "[[ADR-191]]"
  - "[[ADR-090]]"
  - "[[ADR-161]]"
aliases: ["ADR 306", "base temporal E5", "janela 12m canônica"]
tags:
  - type/adr
  - status/decidido
  - area/e5
  - sprint/a28
---

# ADR-306 — Política de base temporal de mensalização no E5

**Status:** Decidido (A28) • **Data:** 2026-07-03 • Co-design
`financial-planner` + `senior-cto` (2026-07-03). Relaciona [[ADR-191]]
(custo essencial), [[ADR-090]] (money), [[ADR-161]] (suggestions Cerbasi/Perini).

> **Emenda de precisão (A40.l3, 2026-07-31)** — duas obrigações operacionais que
> §Consequências deixava implícitas e que a A40.l3 mediu como **violadas em
> produção**:
>
> 1. **Rótulo em tooltip não conta.** Tooltip (`title=` nativo ou portal com
>    hover/focus) não sai no PDF, e o PDF é o artefato que a família guarda e leva
>    ao contador. O rótulo obrigatório é **texto impresso ao lado do número**.
>    Tooltip é complemento, nunca portador único da base.
> 2. **O rótulo é lido do campo `janela`** (vocabulário D2), nunca de campo
>    vizinho de nome parecido: `ratios.janela_referencia` é string de PERÍODO
>    ("2026-01 a 2026-01", `ratios_calculator.py`) e passá-la a um formatador de
>    rótulo funciona em fixture e quebra em produção.
>
> **Nota de leitura, sem valor normativo novo:** em §Decisão, o parêntese de D6
> ("`total_pontuais` **(tabela)** segue full-period") escopa D6 ao **inventário
> histórico**. Se o KPI de gastos pontuais deve migrar para a base de janela — por
> ser o termo que fecha a álgebra da folga, que D1 põe na família de 12m — é
> questão **aberta**, analisada em `docs/sprint/A40/lanes/A40-l15-consumo-consciente-base-janela.md`;
> exige co-change no E5 e rebaseline de snapshot. Enquanto a A40.l15 não fecha, o
> card exibe o acumulado full **rotulado** (mesma base da prosa que o E5 emite) e
> a folga rotulada com a janela — duas bases, dois rótulos impressos. Registrado
> aqui para o próximo revisor não re-litigar a fronteira D1/D6 do zero, como a
> A40.l3 fez.

> **Emenda 2026-08-11 (A40.l44) — a definição de "mês documentado" do D3 muda.**
> O proxy *"mês presente na série"* admite mês **futuro** e mês **em curso**, e os
> dois envenenam o denominador de mensalização. A definição passa a exigir
> **movimento**, **fechamento** e **não-posterioridade à data de corte do run** —
> ver §Emenda 2026-08-11 no fim desta nota, com o deferimento datado da cláusula
> de fechamento.

> **Emenda 2026-08-29 (A40.l94) — o termo de pontuais do D6 fica SUPERADO por
> [[ADR-422]].** A fórmula que D6 fixou (`… − (despesa_mensal_media − pontuais_janela/n)`)
> é `poupança_mensal + pontual_mensal`: ela devolvia o gasto pontual **realizado**
> ao numerador e publicava um SEGUNDO "quanto sobra" sobre o mesmo denominador da
> taxa de poupança, 19,4 pp acima dela. Ver §Emenda 2026-08-29 no fim desta nota.
> **O resto de D6 e a nota de leitura sobre a fronteira D1/D6 continuam de pé.**

> **Emenda de vocabulário (A40.l44, 2026-08-14).** O vocabulário canônico de
> D1/D2 continua `12m | full | irpf_<ano>`; a projeção descritiva e interativa
> `fluxo_caixa.janelas` da [[ADR-377]] acrescenta as chaves fechadas
> `3m | 6m | 12m | ytd`. Elas não criam novas bases para score, reserva,
> Cerbasi ou Perini: servem somente aos dois detalhamentos históricos da
> [[A40.l44]], sempre acompanhadas por `janela_meses`, `mes_inicio` e
> `mes_fim` impressos. Assim, “3M” nomeia a seleção; não promete três meses
> civis contíguos.

## Contexto

O payload E5 mensaliza sobre **duas bases sem rótulo** com valores 2× diferentes:
headline usa média full-period (40 meses no dogfood `72883bde`, diluída por meses
de 2023-24 com cobertura documental parcial — despesa 44,2k/mês) enquanto
`fluxo_caixa.janela_12m` mede 81,4k/mês. Consequências: reserva dimensiona pela
base diluída (cobertura superestimada); cobertura Perini oscila ~61%↔~33% conforme
a base; `consumo_consciente.folga_mensal` mistura bases (pontuais full-period ÷
janela 12m); Cerbasi classifica "Gastador" (97,5% presente) no mesmo relatório que
celebra 28% de poupança — aportes não contam como "futuro". FORMULAS.md tinha
três regras fragmentadas (reserva "trimestral" nunca implementada; ratios 12m;
headline full-period).

## Decisão

**D1 — Famílias de métrica e base canônica.**

| Família | Base | Rótulo `janela` |
|---|---|---|
| Ratios/KPIs, score, reserva, Perini (denominador), Cerbasi, folga | **Janela 12m** — últimos 12 meses **documentados** | `"12m"` |
| Agregados históricos (fluxo top-level, orçamento, charts) | Full-period, permitido **apenas rotulado** | `"full"` |
| Mensalizações fiscais (renda passiva, TRS — numerador Perini) | Ano-base IRPF ÷ 12 | `"irpf_<ano>"` |
| Valores mensais por natureza (`parcela_mensal`, `aporte_mensal`, `aporte_mensal_usado`) | Não são mensalização de série | **isentos** |

**D2 — Rótulo de janela por bloco (dois campos).** Todo dict do payload com campo
mensalizado derivado de série temporal carrega chaves irmãs `janela` (tipo
conceitual, vocabulário fechado acima) e `janela_meses` (int — meses documentados
reais; honestidade quando a janela conceitual tem menos dados, ex.: `janela: "12m",
janela_meses: 8`). Invariante testado em pipeline: campo `*mensal*` fora da lista
de isenção (frozenset com justificativa inline + assert anti-órfã) ⟹ `janela` no
mesmo dict. Schema `e5_analysis` exige `janela` em `fluxo_caixa`.

**D3 — Cobertura documental parcial no denominador.** Denominador conta apenas
**meses documentados** (presentes na série E4) — gap de calendário nunca entra como
zero. Política: mês abaixo de cobertura mínima sai do denominador; v1 operacionaliza
cobertura mínima como "mês presente na série" (proxy — a matriz conta×mês de E3
necessária para detecção fina é follow-up, par com [[A28.l9]]/[[A28.l8]]).
`janela_meses` expõe a contagem real para o banner de qualidade.

**D4 — Reserva de emergência** consome `janela_12m` (não mais a média full-period).
`despesa_mensal_media` da janela é **ponte transitória**: [[A28.l1]] troca para
`despesa_mensal_essencial` da **mesma janela** (FORMULAS.md §Reserva). 12m vence
"trimestral" (FORMULAS.md corrigida): sazonais essenciais (IPTU/IPVA/educação/13º
de mensalista) são despesa recorrente real; trimestral subdimensionaria a reserva.

**D5 — Cerbasi presente/futuro sobre renda, com poupança como "futuro".**
Base = janela 12m. `pct_futuro = (gasto_futuro_12m + poupança_12m) / base`;
`pct_presente = gasto_presente_12m / base`; poupança = `max(0, receita_recorrente_12m
− despesa_total_12m)` (residual — **fallback**; aporte observado de primeira classe
é follow-up quando E4 expuser); `base = gasto_presente + gasto_futuro + poupança`
(== renda recorrente no superávit; == despesa total no déficit; pcts somam 100).
Faixas inalteradas (≥30 Investidor, ≥20 Equilibrado, ≥10 Endividado consciente).
Mudança **intencional e não-versionada** de `pct_presente`/`pct_futuro` in-place —
o valor antigo (% sobre despesa, poupança invisível) era erro metodológico, não
contrato. Payload ganha `componentes` (gasto_presente, gasto_futuro, poupança,
base) para explicabilidade.

**D6 — Folga mensal reconciliável.** Gastos pontuais do cálculo da folga restritos
à janela 12m; `folga_mensal = receita_recorrente_mensal_12m −
(despesa_mensal_media_12m − pontuais_janela/n)` — derivável algebricamente da base
canônica (teste de reconciliação). `total_pontuais` (tabela) segue full-period.

> ⚠️ **A fórmula acima está SUPERADA desde 2026-08-29 ([[ADR-422]] D1).** O que
> permanece de D6: os pontuais da folga são os da **janela** (nunca full-period), e
> `total_pontuais` (tabela) segue full-period. Ver §Emenda 2026-08-29.

**D7 — Perini com bases mistas declaradas.** Cobertura = renda passiva mensal
(`irpf_<ano>`) ÷ despesa essencial (`12m`). Mistura aceita; rótulos obrigatórios
nos dois blocos + `defasagem_meses` já exposto modula confiança do parecer.

**D8 — Consumidores da base diluída corrigidos.** Reserva (D4),
`suggestion_rules::sugere_diversificar_renda_passiva` (prioridade invertida —
lia top-level antes da janela) e Cerbasi (D5). `_lineage` **não muda**: rastreia
totais full-period por design (rastreabilidade da soma, não mensalização).

## Consequências

- Golden re-snapshot único e explicado (dev/golden_diff.py) — antes de [[A28.l1]]
  re-snapshotar (evita duplo rebaseline). Invariantes de conservação intocados
  (identidades sobre totais).
- Goldens/eval do parecer que asserem rótulo Cerbasi antigo re-baseline no mesmo PR.
- UI nunca exibe duas mensalizações sem rótulo — render do badge é escopo [[A28.l9]].
- Follow-ups: aporte observado como componente "futuro" de primeira classe;
  cobertura fina conta×mês no denominador; migração do orçamento prospectivo
  para janela 12m.

## Alternativas rejeitadas

- **Janela trimestral para reserva** — perde sazonais essenciais; reatividade vira
  alerta separado, não base.
- **Rótulo `"<N>m"` dinâmico único** — colapsa tipo conceitual e contagem; força
  parsing de string. Dois campos (`janela` + `janela_meses`) resolvem.
- **`_janelas` metadata central no root** — descola o contrato do dado; frágil a
  rename; UI/LLM consomem por caminho direto.
- **Campos novos `pct_futuro_v2` + deprecação** — perpetua o valor errado para
  consumidor não-migrado; ambiguidade pior que correção.
- **Gap de calendário como zero no denominador** — reintroduz a diluição que
  originou o bug.

## Emenda 2026-08-11 — mês documentado exclui futuro e mês em curso

O **D3** operacionaliza "mês documentado" como *"mês presente na série E4"*, e
declara o proxy como tal. O proxy admite duas classes de mês que **não são
documentação de nada**:

| Classe admitida | Como entra | O que faz no denominador |
|---|---|---|
| **Mês futuro** | lançamento com data de **pagamento** à frente (parcela, agendamento, fatura futura) estica `meses_ordenados` além do mês corrente | infla o denominador com meses **sem atividade** — mensaliza sobre período que ainda não aconteceu |
| **Mês em curso** | o mês corrente entra parcial, com a fração de dias já decorrida | **dilui sempre para baixo**, e o viés é sistemático, não aleatório |

Os dois erram na mesma direção — subestimam a média mensal — e o erro é maior
quanto mais curta a janela. Foi o mecanismo dominante do RV4-01
([[REPORT-REVIEWS-active]] §r4): a âncora da janela interativa saía da última
label da série, e a série terminava no futuro.

**A definição passa a ser:** mês presente na série **com qualquer movimento**
(receita **ou** despesa), **fechado**, e **não posterior à data de corte do run**.

Isto **não** afrouxa o D3 nem reintroduz gap-como-zero: mês de calendário sem
movimento continua fora do denominador, como já estava. O que muda é que
*presença na série* deixa de bastar — presença passa a exigir movimento **e**
posição temporal válida.

### Deferimento datado — cláusula de fechamento (2026-08-11)

**Deferido:** a exclusão do **mês em curso**. **Dono:** `senior-cto` (owner dos
RV4-01/RV4-06), em **lane própria a abrir**, não nesta emenda e não em ADR nova.

**Por quê:** é **flip de denominador**. O corte de futuro — que a [[A40.l44]] PR1
entrega — já move a média mensal de toda janela; empilhar o corte do mês em curso
no mesmo PR produz um `↓` de golden **não atribuível**, e é precisamente a
prática que a §Débito de método da [[A40]] proíbe (delta declarado por causa, um
por vez).

**Condição de retomada:** a [[A40.l44]] fechada, com o delta do corte de futuro
declarado e conferido por `dev/golden_diff.py`.

**Estado até lá — declarado, não enforçado:** o código exclui futuro e exige
movimento; **não** exclui o mês em curso. Esta ADR descreve a política decidida,
e este parágrafo existe para que ninguém a leia como descrição do código vigente.

## Emenda A40.l44 — vocabulário das janelas interativas · 2026-08-14

O vocabulário canônico de D1/D2 continua `12m | full | irpf_<ano>`. A
projeção descritiva `fluxo_caixa.janelas` da [[ADR-377]] acrescenta as
chaves fechadas `3m | 6m | 12m | ytd`. Elas **não** criam bases novas para
score, reserva, Cerbasi ou Perini: servem só aos dois detalhamentos
históricos da [[A40.l44]], sempre acompanhadas de `janela_meses`,
`mes_inicio` e `mes_fim` impressos. “3M” nomeia a seleção; não promete
três meses civis contíguos.


## Emenda 2026-08-29 — o termo de pontuais do D6 (A40.l94 · [[ADR-422]])

D6 consertou uma **mistura de base** real: antes dele, `pontuais_janela` era o
acumulado full-period diluído por um denominador de 12 meses. Esse conserto está
de pé e não é reaberto.

O que D6 **não** examinou é se somar o pontual de volta ao numerador é certo. A
fórmula que ele fixou reduz-se a `folga_mensal ≡ poupança_mensal + pontual_mensal`
— o gasto pontual **realizado** reclassificado como sobra recuperável. O efeito
publicado é que a mesma página emite dois "quanto sobra" sobre o **mesmo**
denominador (`janela_12m.receita_recorrente == equilibrio_cerbasi.componentes.base`),
divergindo por exatamente `total_pontuais_janela` — 19,4 pp no corpus de dogfood — e
a **maior das duas é a que prescreve**, porque `teto_sugerido` sai da mesma
subtração e o parecer ancora conselho de contenção nela.

A [[ADR-422]] substitui o termo: `folga_mensal = receita_recorrente_mensal_12m −
despesa_consumo_mensal_12m` (base [[ADR-333]]), o que faz o invariante
`|folga − taxa_poupança × receita| ≤ ε` valer por construção. `teto_sugerido` sai
do contrato e `equivalente_meses_aporte` vira `equivalente_meses_poupanca`.

**Lição de método que vale além deste campo.** D6 pediu um "teste de reconciliação"
e ele foi escrito reconstruindo a própria fórmula
(`test_folga_mensal_reconcilia_com_base_canonica`, `tests/test_e5_janela_labels.py`):
teste e código compartilhavam a crença errada. E ele rodava sobre os dois únicos
goldens do repo, ambos com `total_pontuais_janela == 0` e `n_meses == 1` — com o
termo zerado, folga e poupança coincidem **qualquer que seja a fórmula**. Medido: o
invariante correto passa nos dois COM o defeito presente. Nenhuma fixture do repo
tinha um único gasto pontual ≥ R$ 2.000. Um invariante que reconstrói a expressão
do produtor não é segunda testemunha; e sem fixture que separe os termos, ele não é
gate nenhum.
