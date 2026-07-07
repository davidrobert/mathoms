---
id: A33.l8
type: lane
title: "InstitutionCatalogProvider (protocol) + códigos RFB do e16 em YAML anual versionado (W4-T01/T02)"
sprint: A33
plan: PLAN-llm-prompts-hardening
status: shipped
ship_pr: 836
ship_date: "2026-07-07"
priority: P2
branch_slug: a33-l8-catalogo-injection-rfb
adrs: ["[[ADR-137]]"]
depends_on: []
parallel_with: ["[[A33.l7]]"]
tags:
  - type/lane
  - sprint/a33
  - status/shipped
  - priority/p2
  - area/llm
  - area/pipeline
---

# A33.l8 — `catalogo-injection-rfb` (W4-T01/T02 do [[PLAN-llm-prompts-hardening]])

## Problema

Listas de bancos/seguradoras estão hardcoded nos system prompts
(`e1_members`, `e2_llm`, `apolice` — matriz do plano, coluna "Catálogo
hardcoded"), driftando do `institution_catalog` versionado em DB
([[ADR-137]]). Códigos RFB do `e16_irpf_full` mudam anualmente (Manual
DIRPF, sem API pública) e vivem inline no prompt. Pré-requisito W4-T00
(seed expandido) já shipou como [[A17.l5]] (#451).

## Escopo

1. Protocol `InstitutionCatalogProvider` definido no consumer
   (`pipeline/llm/`) — pipeline não importa backend; adapter concreto em
   `backend/app/services/`.
2. Injection do catálogo no **user prompt** (não system) nos 3 prompts
   com lista hardcoded; system prompt perde as listas.
3. Códigos RFB → `config/prompts/e16_codigos_rfb_<ano_base>.yaml`
   versionado + loader; runbook curto de atualização anual (fevereiro)
   em `docs/reference/runbooks/` (forma: co-design
   `information-architect`).
4. `PROMPT_VERSION` bump nos prompts alterados + goldens atualizados.

## Critérios de aceite

1. `grep` de nomes de banco em `pipeline/llm/prompts/*.py` retorna zero
   lista hardcoded (sobra só o placeholder de injection).
2. Teste: adicionar instituição no catálogo reflete no prompt gerado sem
   editar código.
3. Loader YAML falha-fast com mensagem contendo valor ofensor se o ano
   solicitado não existe.
4. PR(s) mergeado(s) em `main` (squash) com CI verde.
