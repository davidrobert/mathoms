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

1. **Decisão de domínio não declarada.** `alocacao_alvo_deviation.py:18`
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
