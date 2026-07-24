---
id: ADR-348
type: adr
title: "Determinismo da classificação LLM: temperature=0 + validação estrita de dest_group"
status: Decidido
phase: A39.l11
date: "2026-07-24"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-289]]"
  - "[[ADR-296]]"
  - "[[ADR-349]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
---

# ADR-348 — Determinismo da classificação LLM (temp=0 + dest_group estrito)

**Status:** Decidido (A39.l11) · **Data:** 2026-07-24 · **Lane:** [[A39.l11]]

## Contexto

`scripts/route_documents.py::classify_by_llm` é o fallback LLM do padrão canônico
[[ADR-081]] (regex→LLM→needs_review) e a **via compartilhada de classificação de
TODO upload** em produção (`document_classification.classify_document` a chama).
A certificação 2026-07-23 apontou dois defeitos:

1. **Não-determinismo.** A chamada rodava em `temperature=1.0` (default — não
   passava `temperature`). Certificar um classificador não-determinístico **mede
   ruído, não cobertura**; e o gate de `needs_review` (confidence < 0,7) oscila:
   o mesmo documento pode pontuar 0,75 numa run e 0,65 na seguinte, entrando/
   saindo de revisão por sorteio.
2. **Misroute silencioso.** `dest_group` (saída do LLM) dirige o diretório de
   destino em `dest_dir_for_group` — `base / "data" / group` com o valor **cru**.
   Um `dest_group` alucinado (fora do conjunto fechado) põe o documento em
   `data/<lixo>/`, **invisível aos globs de E1/E2 = perda silenciosa**; além de um
   mini path-traversal (`"../x"` não era sanitizado).

## Decisão

1. **`temperature=0`** na via compartilhada, como **constante nomeada
   `_LLM_TEMPERATURE = 0.0` fora do `_llm_cfg`** — invariante, não parâmetro
   tunável. Classificação é tarefa **discriminativa** (labels em enums fechados);
   amostrar abaixo do argmax é uma classificação menos provável de estar certa, e
   config-flag institucionalizaria um botão de não-determinismo sem caso de uso.
   Conforma a um invariante já estabelecido no repo (`section_summary_orchestrator`
   já usa `temperature=0`).
2. **Validação estrita de `dest_group`** contra o conjunto fechado `_DEST_GROUPS`
   (fonte única no módulo; inclui `comprovantes`, dir consumido por [[ADR-239]],
   além dos 6 do prompt). Miss → trata como baixa confiança (`return None` →
   `nao_identificados/`, caminho já existente). `doc_type` fica **guard não-fatal**
   (o prompt trata a lista como aberta — "etc.") — dirige filename, não diretório.
3. **`model` como família (não snapshot)** permanece ([[ADR-289]]) — o contrato de
   determinismo registra a família (via re-route [[ADR-349]]) para bump ser
   atribuível; snapshot-pin seria bomba de 404 no EOL, fora de escopo.

**Enquadramento do invariante:** `temperature=0` = decodificação argmax/greedy =
**quase-determinístico**. Anthropic não expõe `seed`; flip residual provider-side
(batching/hardware) é possível — é o que o golden de N amostras mede ([[ADR-296]]
já observou resíduo→0 a temp=0). O ADR **não** afirma "determinístico".

## Fora de escopo (declarado)

- **Telemetria/budget/cache/enum-via-Instructor** não são cabeados à mão no path
  cru — exigiriam levantar fatia do scaffolding do choke-point para deletar depois
  (build-then-delete). Vêm com o **re-route pelo `LLMService`** ([[ADR-349]],
  `Proposto`, lane própria P1), feitos uma vez e corretos.
- **`scripts/e2/banks/caixa.py::_classify_via_vision`** tem a mesma omissão de
  `temperature` numa **extração por visão** (não classificação) — peixe maior
  (muda números, não rótulos), outro dono/golden. Follow-up separado.
- **Eval golden real-LLM** (N amostras, 0 flips de `dest_group`+`doc_type`) é
  owner-gated (custo de API) — roda em workflow dedicado, não no gate por-PR.

## Consequências

- Classificação reproduzível → certificação mede cobertura, não ruído; gate de
  `needs_review` para de flipar.
- Documento com `dest_group` alucinado escala para revisão em vez de sumir.
- **Gate anti-regressão:** teste offline com spy nomeado sobre o client afirma
  `temperature == 0` no payload + `dest_group` inválido/traversal → `None`
  (`tests/test_route_documents_llm_determinism.py`), custo zero, roda por-PR.
- A lacuna de observabilidade (custo/volume/drift da chamada de maior volume)
  **permanece** até [[ADR-349]] — aceita conscientemente; é a justificativa do
  re-route, não algo para meio-consertar num P2.

## Alternativas rejeitadas

- **Config-flag `LLM_CLASSIFY_TEMPERATURE`** — foot-gun (alguém põe 0,7 "para
  melhorar ambíguo" e quebra gate + golden), sem caso de uso legítimo.
- **Cabear telemetria no path cru agora** — build-then-delete; `LLMCallLog` nem
  funciona no path CLI-isolado (exige DB session). Rejeitado (VETO senior-cto).
- **Snapshot-pin do model** — reverte [[ADR-289]] (família-gerida-por-EOL) e agenda
  404. Fora de escopo.
