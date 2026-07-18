---
id: ADR-337
type: adr
title: "Rótulo de exibição sem PII para ativos — sanitização na fonte E5 (React + prompt)"
status: Decidido
date: "2026-07-15"
relates_to:
  - "[[ADR-332]]"
  - "[[ADR-319]]"
  - "[[ADR-216]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
  - area/report
---

# ADR-337 — Rótulo de exibição sem PII para ativos

> Cluster **PD-02** (P0, + subsume **H1**) da onda R2 do PLAN-dogfood-report-fix.
> Co-desenho `codesign-review-wave` (product-designer + senior-cto + red-team, 2026-07-15).

## Contexto

`investimentos.top_ativos[].nome` carrega a **descrição cartorial crua** do ativo — matrícula,
IPTU, endereço e, em ≥1 linha, o **CPF de um terceiro** (vendedor do imóvel) **não mascarado**.
Esse campo é lido por **duas** superfícies:

1. o card React `Top15AtivosCard.tsx:201` (`{r.nome}` verbatim) — quebra o layout e expõe PII ao
   dono do relatório;
2. o **prompt do parecer** (`config/prompts/parecer_planejador.yaml:147` lê `$.top_ativos[*]`) —
   **egresso de PII de terceiro para um LLM de terceiro**, fora do boundary do tenant. Este é o
   vetor de **maior** risco (LGPD), e não estava coberto pela proposta original de PD-02 (só UI).

Investimentos ainda aparecem com rótulo genérico `"Investimento"` + `instituicao=""`.

## Decisão

**Sanitizar `top_ativos[].nome` na FONTE E5** (`top_ativos_analyzer`/payload E5) — um **boundary
único** que subsume a superfície React (esta ADR) **e** a do prompt (irmã [[ADR-332]]). Regras:

1. Rótulo derivado, **granularidade estrita na fonte**: `imóvel → classe` **apenas** (padrão
   [[ADR-332]], sem bairro); `investimento → classe + instituição` (ou classe se instituição
   ausente). O valor monetário é preservado intacto.
2. **Nenhum** CPF/CNPJ/matrícula/IPTU/endereço de terceiro chega ao payload E5 — a string PII é
   removida **na origem**, não mascarada na UI.
3. Enriquecimento de display (ex.: bairro/cidade) é **downstream**, só na projeção view-model/React,
   **nunca** upstream do input do prompt (senão vaza localização adicional ao LLM).
4. O gate PII-scan (existente para o superset público, [[ADR-319]]) é **estendido** ao view-model
   **e ao contexto efetivo do LLM** (distiller + saída de tools sobre `top_ativos`).

## Rationale

PII de terceiro é PII mesmo no relatório da própria família — e o egresso a um LLM de terceiro
sai do tenant, o pior vetor. Sanitizar na fonte é o único ponto que cobre React **e** prompt sem
duplicar lógica; mascarar só na UI deixaria o prompt vazando. Granularidade estrita na fonte
respeita a decisão deliberada da [[ADR-332]] de não dar localização ao LLM.

## Alternativas consideradas

- **Sanitizar só na UI (React).** Rejeitada: o prompt continua egressando PII de terceiro (H1
  aberto) — não fecha o gate de PII de beta.
- **Mascarar (não remover) o CPF.** Rejeitada: a descrição cartorial inteira é ruído + risco;
  derivar um rótulo curto resolve legibilidade **e** privacidade de uma vez.
- **Enriquecer com bairro/cidade na fonte** (proposta de display). Rejeitada na fonte: daria mais
  PII de localização ao LLM que a [[ADR-332]] proíbe; fica só no view-model.

## Consequências

- Muda o **input** do prompt do parecer → cache pode invalidar. Exige **prova**: (a) rótulo
  estável (texto idêntico entre runs) ⇒ neutralidade; ou (b) orçar 1 eval, coordenado com a lane
  paralela de parecer (manifest 1.8→1.9). Não presumir "zero eval".
- Bump: `schema_e5` aditivo (campo `top_ativos[].nome` normalizado) — batelado no bump único da
  onda R2.1 (âncora [[ADR-338]]).
- Owner confirma que o CPF é de terceiro (evidência sugere sim) e o grau do rótulo de imóvel no
  **display**.

## Critério de aceite (4 lentes)

- **Completude** — nenhum slot (view-model) nem o `exec_context` do LLM emite CPF/CNPJ/matrícula/
  IPTU/endereço; cobre `top_ativos[].nome` e o distiller.
- **Corretude** — rótulo classe-only na fonte; valor monetário idêntico ao pré-fix.
- **Consistência** — mesmo abstrator em React e prompt; granularidade de display só downstream.
- **Precisão** — teste com regex de PII zero-hit em `top_ativos[].nome` **e** no contexto do
  distiller; neutralidade de prompt provada ou 1 eval orçado.
