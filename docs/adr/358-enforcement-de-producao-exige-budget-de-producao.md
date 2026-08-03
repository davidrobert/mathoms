---
id: ADR-358
type: adr
title: "Enforcement em produção exige budget de produção — e KR no plano onde ele age"
status: Proposto
phase: "A40"
date: "2026-08-03"
relates_to:
  - "[[ADR-304]]"
  - "[[ADR-296]]"
  - "[[ADR-295]]"
  - "[[ADR-294]]"
  - "[[ADR-081]]"
supersedes: []
superseded_by: []
aliases: ["ADR 358", "G1 enforcement doctrine", "budget de producao"]
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/pipeline
  - phase/a40
---

# ADR-358 — Enforcement em produção exige budget de produção

**Status:** Proposto (A40) • **Data:** 2026-08-03 • **Relaciona** [[ADR-304]]
(a doutrina que falhou), [[ADR-296]] (a decisão contrariada), [[ADR-295]]
(máquina de enforcement per-item), [[ADR-294]] (guardrails que rebaixam),
[[ADR-081]] (regex→LLM→needs_review).

## Contexto

O enforcement de `number_in_prose` (PR #875, autorizado pela [[ADR-304]] §2)
destruiu um run completo e apagou conselho verificado em 7 runs (16 itens).
A taxa depende de `prompt_version` e a decomposição por janela vive na
[[ADR-304]] §Evidência — não é repetida aqui de propósito. A análise
da causa não achou um bug de implementação: achou **três defeitos de método**,
todos reprodutíveis por qualquer futuro enforcement.

**1. Decisão `Decidido` condicionada a validação futura, sem gancho.** A
[[ADR-304]] §3 escreveu: *"construir o enforcement quando a A27 for promovida +
**validar contra tráfego real** — o resíduo em dados reais pode ser diferente"*.
A A27 seguiu `candidate`; a validação nunca aconteceu; o enforcement shipou. O
vault não tem campo para "decisão condicional", e nenhum gate lê prosa. O
resultado é uma ADR `Decidido` que autoriza algo cujas pré-condições ela mesma
declarou e ninguém drenou.

**2. Gate medido num plano, aplicado em outro.** O KR1 da A27 é definido *"== 0
sobre todas as gerações do **holdout**"* — corpus de eval sintético. O
enforcement foi aplicado no **caminho de produção**. Um gate de produção não
move um KR de holdout; só destrói entregável. Erro de categoria.

**3. Budget calibrado com régua errada.** O "61→7 (↓88%)" da [[ADR-304]] §1 foi
medido por um detector que conta *matches* (não valores distintos), inspeciona
3 campos de prosa dos 8+ que a regra cobre, e é cego a `US$`. O número que
autorizou a doutrina estava inflado na fonte, e ninguém podia saber sem ler o
detector.

O custo composto: doutrina errada aplicada com raio de dano subestimado ~20×
(4,2% projetado no holdout vs 87,5% medido sob o prompt 2.2.0 — sob 2.1.0 a
taxa era 9,1%; ver [[ADR-304]] §Evidência).

## Decisão

Nenhuma camada de enforcement entra em caminho de produção sem as três:

1. **ADR própria.** Não herdar a máquina de outra camada por analogia. A
   [[ADR-304]] roteou `number_in_prose` para a máquina da [[ADR-295]] sem
   re-derivar se a justificativa transferia — e não transferia: a [[ADR-295]]
   pressupõe *número errado sendo emitido*, enquanto `number_in_prose` tem a
   âncora verificada. Reuso de mecanismo exige re-derivação explícita da
   premissa, na ADR nova.
2. **Budget de produção declarado e medido em tráfego real**, com o instrumento
   de medição auditado. Um enforcement `==0` sobre sinal estocástico é
   inatingível por construção (o parecer roda em `temperature: 0.1`); o que se
   declara é o budget e o que se mede é a distribuição, não o ideal.
3. **KR definido no mesmo plano onde o enforcement age.** Se o KR vive no eval,
   o gate vive no eval.

**Corolário de forma.** Decisão cujo enforcement depende de evidência futura
nasce `Proposto` — ou nasce `Decidido` com o gate registrado em
`docs/_MOC/OWNER-GATED-active.md`, o único lugar do vault que alguém drena.
`Decidido` + "validar depois" é o antipadrão que produziu este incidente.

**Doutrina de proporcionalidade.** O padrão default para defeito de forma em
output LLM é o da [[ADR-294]]/A28.l11 — *"rebaixam/removem, nunca
`needs_review`"*. Escalar para `needs_review` exige que publicar seja **o dano**
(sigilo §13, vazamento de PII), não que a apresentação esteja fora do contrato.

**Auditável.** Enumerar `_HARD_LAYERS` / `_CORRECTNESS_LAYERS` e exigir ADR +
budget declarado por entrada.

## Alternativas rejeitadas

- **Confiar no protocolo de supersedure existente.** O conflito [[ADR-296]] ↔
  [[ADR-304]] passou por revisão e por todos os gates de doc. A raiz não foi
  indisciplina de supersedure: foi a ausência de gancho verificável para uma
  condição escrita em prosa. Protocolo de linking não resolve.
- **Gate automatizado que lê a condição da prosa da ADR.** NLP sobre ADR para
  extrair pré-condição é frágil e cria falso-verde. O registro explícito em
  `OWNER-GATED-active.md` é barato e já tem dono.

## Consequências

- Custo: ~1 entrada em `OWNER-GATED-active.md` por decisão condicional, e a
  disciplina de nascer `Proposto` quando a evidência falta.
- Ganho: a classe de falha "ADR autoriza enforcement cuja pré-condição nunca foi
  drenada" deixa de ser possível silenciosamente.
- Esta ADR é a razão pela qual a reversão de [[A40.l16]] não é reversível pelo
  mesmo raciocínio que a produziu — sem ela, a [[ADR-304]] §2 continuaria
  afirmando que "o caminho canônico para o KR1 é enforcement".
