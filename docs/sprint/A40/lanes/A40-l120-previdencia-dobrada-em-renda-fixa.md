---
id: A40.l120
type: lane
title: "O parecer chama de renda fixa uma soma que inclui previdência, e o número com que ele deveria concordar não chega até ele"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l120-previdencia-dobrada-em-renda-fixa
owner: financial-planner
depends_on: []
adrs: ["[[ADR-141]]", "[[ADR-399]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l120 — `previdencia-dobrada-em-renda-fixa`

> **Origem:** desmembrada da [[A40.l117]] por arbitragem do `senior-cto` (2026-09-01).
> Dona registrada no [[PIPELINE-REVIEWS-active]] §r13 `PV13-08` em 2026-09-02 — a linha
> nascera com a l117, e lá também está a refutação do enunciado causal dela.
> Era o "sintoma 1" daquela lane (`RR9-08`/`PV13-08` da **U5**). Sai porque é o único dos
> três que **move número publicado** e exige rebaseline de golden + veredito de domínio —
> misturá-lo com mudança de contrato de LLM tornaria o diff do golden inatribuível.

## O defeito, já medido

O parecer publica **dois valores para a fatia de renda fixa** na mesma seção (S1), com
**4,15 pp** de spread. Medido no run `40d1af2a`, com o discriminador que o
`financial-planner` desenhou:

| `categoria` | `pct_carteira_financeira` |
|---|---|
| Renda Fixa | **90,25** |
| Previdência | **4,14** |
| Caixa | **0,0** |

`Caixa = 0` ⇒ a hipótese do **denominador está refutada**: `carteira_financeira ≡
carteira_liquida` neste corpus. E `90,25 + 4,14 = 94,39` = o carimbo
(`goals.alocacao_alvo.derived.renda_fixa_atual_pct`) ao centésimo. **O spread É a linha
Previdência.**

## As duas causas

1. **Decisão de domínio não declarada.** `alocacao_alvo_deviation.py:17`
   (`_BUCKET_TO_COMPARABLE`) mapeia `"Previdência" → "renda_fixa"`: **toda** previdência
   vira renda fixa. PGBL/VGBL é *wrapper*, não classe — o subjacente pode ser multimercado
   ou ações. O `rotulo` diz só "Alocação em renda fixa (carteira líquida)" e **não declara**
   que dobra previdência dentro. As metodologias de referência do produto divergem do
   carimbo em duas frentes: duas delas classificam pelo **ativo subjacente**, e uma terceira
   trata previdência como instrumento de **sucessão/proteção**, fora da conta de alocação.
   O default conservador ("previdência de varejo brasileira é majoritariamente renda fixa")
   é defensável — mas tem de estar no rótulo.
2. **O modelo nunca recebeu o número.** `$.goals` é projetado num **único** lugar
   (`parecer_planejador.yaml:742`, seção `plano_acao_atual`, `eviction_priority: 10`) e essa
   seção **foi evictada neste run**. O `narrative_hint` da linha 357 manda usar
   `pct_carteira_financeira` e nomeia "RF". **O modelo obedeceu o prompt.** É defeito de
   projeção, não de prosa.

## Ordem do conserto (a ordem é a decisão)

1. **Projetar** `$.goals.alocacao_alvo.derived` na S1 e S3, com a base no `title` do bloco.
   Há folga: a eviction ocorreu com **42,9% do orçamento ocioso** (`PV13-17`).
2. **Corrigir o hint 357** — separar *composição* (`pct_carteira_financeira`) de *alocação
   vs alvo* (`derived`).
3. **Só então** o gate de coerência. Ligá-lo antes reprova o insolúvel, e o remédio vira
   reask storm ([[ADR-292]]).

## Tolerância do gate — derivada, não inventada

Nenhum limiar novo nasce aqui. A tolerância é **meio passo da precisão que o modelo
escreveu**, semântica que já existe projetada e nunca exercida em
`parecer_prose_money.py:65-67` (`half_step_cents`): `"94%"` passa (half-step 0,5 > 0,4);
`"cerca de 90%"` e `"90,25%"` reprovam. Arredondamento legítimo passa **porque o modelo
declarou a precisão**. Zero absoluto seria errado — reprovaria boa escrita que a persona
pede.

Três condições, senão o gate vira o defeito: **por unidade** (`if_prazo_ano` é ano,
`reserva_cobertura_meses` é meses, `protecao_custo_premio` é razão 0–1 — comparar half-step
de pp contra eles fabrica falso positivo); **atribuição conservadora** (só dispara com o
termo canônico da grandeza no mesmo campo e no mesmo `section_id` do carimbo); e **reprova
o item, não o parecer**.

## Priorização por grandeza

Critério: *existe mais de uma base publicada para o conceito, e o carimbo usa uma que o
modelo não recebe ou que um hint contradiz?*

- **P0:** `alocacao_renda_fixa` (medido) · `concentracao_imobiliaria` (tem limiar canônico
  50%/75% — errar a base atravessa limiar e troca "Crítica" por "Alta") · `exposicao_cambial`
  (3 conceitos vizinhos; a base inclui a fatia sem dono).
- **P1:** `taxa_endividamento` (dívida/PB vs dívida/PL; limiar 30% muda a manchete) ·
  `reserva_cobertura_meses` (dois denominadores publicados) · `taxa_poupanca_recorrente`
  (dois limiares divergentes sem precedência) · `protecao_custo_premio` (risco é de
  **unidade**: entra como requisito do gate, não como risco de prosa).

## Critério de aceite

1. `renda_fixa_atual_pct` aparece no exec context de um **run real** — verificável na saída
   do `parecer_distiller`, não por leitura do YAML.
2. Contrafactual do gate, **as duas pernas**: prosa "94%" com carimbo 94,4 ⇒ **passa**;
   prosa "90,25%" com spread de 4 pp ⇒ **reprova**, com `metrica_key` e `section_id` na
   mensagem.
3. Teste explícito de **não-disparo por unidade** sobre `if_prazo_ano` e
   `protecao_custo_premio`.
4. Nenhum limiar novo. Toda tolerância deriva da precisão escrita ou de constante com leitor
   único; número que precise ser escolhido vai para ADR.
5. **Veredito do `financial-planner` sobre a pergunta 1** (previdência é renda fixa?),
   registrado aqui. Se a resposta for "depende do subjacente", `extract_informes_anuais`
   ([[ADR-238]]) provavelmente já traz o insumo para classificar — e aí o rótulo muda junto
   com a regra.
6. Golden rebaselinado em **commit separado** do commit de lógica.


## Veredito de domínio (2026-09-02) — critério 5 respondido

**Decisão: (a) com qualificação obrigatória.** Previdência **permanece** agregada em
`renda_fixa` no comparável — mas pelo critério da própria [[ADR-141]] §Emenda, não por
consenso metodológico: o bucket que já saiu da carteira líquida (imóveis) saiu por **não
ser rebalanceável por aporte**, e previdência **é** (redirecionar contribuição e
portabilidade são as duas alavancas mais baratas do público-alvo).

**Nenhuma das três metodologias de referência afirma que previdência É renda fixa** — duas
mandam classificar pelo subjacente e uma a trata como sucessão/proteção. O default é
aproximação de conveniência, e é exatamente por isso que ele **tem** de estar escrito.

**(b) classificar pelo subjacente — REJEITADA por falta de insumo, verificada:**
`informe_previdencia.schema.json` e o extrator têm certificado, regime, contribuições,
saldos e IR — **zero** campo de fundo ou composição. E `asset_classifier.py:32-45` põe
`Previdência` **antes** de `acoes`/`renda fixa` no `EVALUATION_ORDER`, então o sinal do
subjacente, quando existe no nome, é descartado por desenho. Não é "lane de ingestão": é
ingestão de **outro documento** (regulamento/extrato do plano), com cobertura incerta.

**(c) tirar do comparável — REJEITADA:** encolher o denominador infla o `atual_pct` de
**todas** as demais classes — troca um viés declarável por um viés difuso em quatro linhas.

### Correção de citação que este veredito produziu

O mapping está em `alocacao_alvo_deviation.py:**17**`; a linha 18 é `"Ações BR"`. Eu havia
escrito `:18` em **4 sítios** (registro `§r13`, `_README` da A40, lane l117 e esta) —
corrigidos.

## O que foi entregue

1. **Projeção** (critério 1) — `$.goals.alocacao_alvo.derived` entra na seção `patrimonio`
   com a base na label. Medido num run real: `renda_fixa_atual_pct` = **94,39%** chega ao
   exec context, na seção **mantida**, e a eviction não muda.
2. **Rótulo** — o KPI passa a *"Alocação em renda fixa, previdência inclusa (% da carteira
   líquida)"*, e o hint do manifest declara que a linha `Previdência` da tabela é
   **subconjunto** do KPI.
3. **Gate de coerência** (critérios 2-4) — `parecer_prose_coerencia.py`. Tolerância =
   **meio passo da precisão escrita**, semântica que `half_step_cents` projetava e nunca
   exerceu. Rebaixa o **item**, nunca derruba o parecer ([[ADR-292]]).

### Atribuição: apertada por medição, não por gosto

A 1ª versão disparou **11 vezes** no corpus real e **7 eram outra coisa** — as demais
linhas da tabela de classes e um **limiar de meta** lido como afirmação. Apertei para *"o
percentual mais próximo do termo, na mesma cláusula"*, e a janela é **medida**:
verdadeiro-positivo cai em **13-37** chars da menção, falso em **48-307**. O corte a 40
fica dentro do vão — e é o vão que justifica o número. Resultado: **5 divergências, 2
riscos rebaixados**, incluindo as 3 do defeito-alvo (90,25% vs 94,4%) e 2 de
`aliquota_efetiva_ir` que a medição revelou de quebra.

### Limites declarados

- **O percentual não é citável.** O catálogo de citação é *money-only* (`_is_money_key`),
  então `renda_fixa_atual_pct` é **projetado e legível, não ancorável**. O hint diz "sai
  de", não "cite" — a regra de âncora vale para `R$`. Torná-lo ancorável é território da
  [[ADR-296]], não desta lane.
- **O corpus sintético não tem `derived`**, então as 6 folhas novas entraram em
  `paths_projetados_sem_dado_no_corpus` (que já tinha 38). O golden não exercita o bloco
  novo; a prova do critério 1 é o **run real**, como a lane exige.

## Roteado, NÃO entregue: o guarda de flip

O veredito nomeia um segundo defeito, e ele **muda cálculo**, logo exige ADR própria:
`_next_aporte` só considera classes com `desvio_pp < 0`, então todo workspace cujo desvio
de RF esteja em `(0, +prev_pct]` tem RF **desqualificada** como destino do aporte quando,
pelo subjacente, ela está *subalocada*. Neste corpus `prev = 4,14` e as bandas de
severidade são 2/5 pp — **a faixa de flip cobre uma banda inteira**.

Decisão de uma linha que a ADR registraria:

> *A prescrição de próximo aporte é suprimida quando o default de classificação inverte o
> sinal do desvio de renda fixa — teste de sinal sobre números já computados, sem limiar
> novo.*

Fica fora desta lane porque move `next_aporte_classe`/`motivo_supressao` e exige rebaseline
de golden com contrafactual de duas pernas.

## Achado adjacente: `componentes` é emissor sem leitor

`AlocacaoComparableRow.componentes` carrega `["Renda Fixa", "Previdência"]`, atravessa
schema e o tipo do front (`alocacaoCardParts.tsx:16`) — e **nenhum componente React o
renderiza**. É a classe que a [[A40.l88]] fechou. Ligar o fio daria ao card o label
derivado ("Renda Fixa + Previdência") sem inventar dado. Fora do escopo — é frontend, e a
lane é do parecer.
