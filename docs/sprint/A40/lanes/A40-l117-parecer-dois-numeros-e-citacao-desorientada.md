---
id: A40.l117
type: lane
title: "O parecer publica dois números para a mesma coisa, cita a seção errada em 4 de 11 riscos, e o prompt se contradiz sobre ter ferramentas"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l117-parecer-dois-numeros-e-citacao-desorientada
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-199]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend]
---

# A40.l117 — `parecer-dois-numeros-e-citacao-desorientada`

> **Origem:** `RR9-08` + `RR9-11` + `RR9-14` da rodada unificada **U5**
> ([[PIPELINE-REVIEWS-active]] §r13). Três sintomas com a mesma raiz: **prosa autoral do
> modelo não passa por invariante**.

## Os três sintomas

1. **Dois valores para "renda fixa na carteira" na mesma seção**, com **4,15 pp** de
   spread: um autoral do modelo, o outro carimbado pela máquina. Nada reconcilia porque
   `parecer_prose_money.py:16` declara que **percentuais ficam fora** do invariante —
   medido: **27 percentuais em 47 campos de prosa, 0 sob invariante**.
2. **4 de 11 riscos citam a seção errada:** dois riscos de **proteção** citam a seção de
   imóveis (existe seção de seguros dedicada), o de **sucessão** cita a seção de renda do
   IRPF (existe seção de riscos e sucessão), e o de rentabilidade cita a de carga
   tributária. **REFUTADO** na mesma medição: a alegação de "âncora morta" — as **27
   citações resolvem, 27 de 27**. O link funciona; o destino é que está errado.
3. **O prompt se contradiz sobre `tools`:** a linha 441 do YAML convida o modelo a chamar
   `get_e5_section`; a **179 do mesmo arquivo** afirma que ele não tem ferramentas. O
   convite morto é **injetado no corpo sob budget** e é a causa proximal dos 3
   `campos_faltantes`.

## Por que os três juntos

O eixo é o mesmo: **o que o modelo escreve não é confrontado com o que a máquina sabe**.
Percentual fora do invariante, seção escolhida por prosa em vez de mapa declarado, e
ferramenta prometida sem existir são três formas de a autoria do modelo passar sem gate.

## Medição que fecha o mecanismo de (2)

Ler como o campo de seção do risco é atribuído no manifest. Se vem do LLM em vez de um mapa
declarado, é a classe *"nome vindo da prosa, não do produtor"*.

## Critério de aceite

1. Percentual em prosa entra no invariante monetário (ou a exclusão é decidida por ADR com
   o custo escrito — hoje ela está num comentário).
2. `section_id` do risco vem de **mapa declarado** por tema, não da prosa.
3. O convite a `tools` sai do prompt **ou** as ferramentas passam a existir; as duas linhas
   do YAML não podem discordar.
4. Gate de coerência: dois valores para a mesma grandeza na mesma seção reprova.
