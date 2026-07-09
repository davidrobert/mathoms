---
id: ADR-321
type: adr
title: "Atribuição de membro no E3 — titular slug canônico como discriminante K4"
status: Proposto
date: "2026-07-08"
relates_to:
  - "[[ADR-226]]"
  - "[[ADR-278]]"
  - "[[ADR-279]]"
  - "[[ADR-282]]"
  - "[[ADR-287]]"
  - "[[ADR-134]]"
  - "[[PLAN-data-lineage]]"
supersedes: []
superseded_by: []
aliases: ["ADR 321", "member attribution E3", "titular slug K4"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/data-lineage
---

# ADR-321 — Atribuição de membro no E3 — titular slug canônico como discriminante K4

**Status:** Proposto • **Data:** 2026-07-08 • **Relaciona** [[ADR-226]], [[ADR-278]],
[[ADR-279]], [[ADR-282]], [[ADR-287]], [[ADR-134]], [[PLAN-data-lineage]].

## Contexto

Diagnóstico 2026-07-08 (dogfood, run `6eb0cc8c`): **3.865/4.212 linhas E4** (92%)
sem `natural_key` — o gate classe-c (`_has_discriminants`, [[ADR-278]]) falha porque
`titular` chega vazio. Três quebras empilhadas, verificadas empiricamente:

1. **E2 roda cego de membros** (regressão desde A7/[[ADR-134]]): `scripts/e2/common.py::_init_config`
   lê `family_members.json` de disco; pós-A7.5 o `ConfigMaterializer` só materializa
   `pipeline.json`+`llm_config.json` — o mapa é DB-only via `config_overrides`, que o
   wrapper `pipeline/stages/e2.py` não repassa. `detect_member_from_text` retorna
   sempre `None`.
2. **`BankStatement.from_e2_dict` descarta `titular`**: mapeia `member_key` só de
   `documento_titular`/`member_key`/`membro` (`document.py:167`). Sobreviventes (8%):
   BTG (emite `documento_titular` = **CPF em plaintext**, que vira `titular` no payload
   E3 **e entra no hash K4** — vazamento de PII + identidade mista CPF/slug) e
   artifacts E2-llm (`membro`, fix A32.l2 #828).
3. **`AccountResolver` ([[ADR-226]] §3) não roda no fluxo de caixa** — só em
   investimentos/E1. No dogfood seria inócuo hoje: `bank_accounts` vazia e cobertura
   de `account_number` no E3 = 0%.

A [[ADR-287]] registrou o dogfood como classe-c "sem mapa de membros, by design
PII-zero" — premissa falsa (3 `FamilyMember` com CPF no DB); emenda datada corrige o
registro. Impacto: `member_hashes`/reverse-lineage ([[ADR-279]]) cobrem 8% das linhas;
dedup v2 sem discriminação por membro (casal no mesmo banco colapsa tx idênticas —
o cenário que a [[ADR-226]] quis matar); o passo "natural_key obrigatório" da
estratégia B4 ([[ADR-278]]) fica estruturalmente inalcançável.

## Decisão

- **D1 — Resolução no E3, não no E2.** Domain service novo (`member_attribution`)
  recebe **catálogo tipado por construtor** (VO derivado de `family_members`;
  conversão `ctx` → VO é do adapter, [[ADR-097]] D2/D3 — nunca `ctx`/dict/`Path` no
  domínio) e constrói CPF-map/name-map **por-run**, sem estado de módulo nem
  `@lru_cache` ([[ADR-111]]). Cadeia determinística:
  `AccountResolver(banco, account_number_norm)` → CPF-map (`documento_titular` cru do
  E2 × CPFs do catálogo) → name-map (hint de nome cru × `nome_completo`/`nome_curto`/
  `variantes_nome`, **match exato normalizado apenas** — fuzzy é follow-up, disciplina
  da [[ADR-271]]). Todos convergem para o **slug**; `ambiguous`/`unknown` → `titular`
  vazio + `review_reason` (projeção A29, nunca chute). Conta conjunta segue o V1 da
  [[ADR-226]]: owner-of-record **único** (`member_id` da conta); rateio/`co_titulares`
  é V2 — sem label composto "casal" no fluxo de caixa (o label da [[ADR-246]] é do
  eixo imóveis, não de identidade K4).
- **D2 — E2 permanece emissor de sinal cru.** Parsers emitem hints estruturais quando
  extraíveis (`documento_titular` CPF, `numero_conta`, nome do titular cru) e **não**
  re-acoplam o catálogo de membros (alinhado à extração de-leak de
  [[PLAN-data-lineage]]). `from_e2_dict` transporta os hints sem resolvê-los.
  Auditoria por parser (espelho do PR2 da [[ADR-226]]) faz parte da lane.
- **D3 — CPF nunca propaga nem entra no hash — sanitização incondicional em F1.**
  `titular` emitido no E3 e ingerido pelo hash K4 é sempre o slug. O strip CPF→slug
  das linhas BTG é **fix de segurança, não comportamento de negócio**: pousa em F1
  fora da flag (fecha o leak imediatamente). Gate: zero sequências de 11 dígitos em
  `titular`/`titulares` de payloads E3/E4.
- **D4 — Rollout atrás de flag por workspace** (mesmo mecanismo da [[ADR-287]]; DB
  soberana, DEFAULT registrado no mesmo PR). A flag gateia a **população de `titular`
  resolvido** no E3: flag-OFF preserva o comportamento atual byte-idêntico, **exceto**
  o strip de CPF (D3, incondicional) — exceção justificada que perturba apenas as
  linhas BTG, reancoradas em F2. Pré-requisitos do flip, nesta ordem:
  (a) reancoragem dos overrides ancorados em hash com titular vazio (runbook Fase E
  da [[ADR-282]], #873) — a atribuição muda os hashes v2 em massa; (b) rebaseline
  manifestado (G-c, `dev/golden_diff.py`) — a mudança altera **cardinalidade** do
  dedup (casais separam linhas), não só hashes; invariantes de conservação E5
  (`tests/test_e5_conservation_invariants.py`) são gate, totais monetários imóveis;
  (c) G-f: diff dogfood inspecionado pelo owner.
- **D5 — Cobertura medida antes do flip.** Telemetria por `confidence`
  (`strict`/`fallback_bank`/`cpf`/`name`/`ambiguous`/`unknown`) no E3, emitida via
  **logging estruturado/métrica** (`mathoms.member_attribution.*`, [[ADR-111]] — nunca
  counter in-memory); o flip do workspace exige cobertura de atribuição reportada,
  não presumida. Substrato mais robusto é conta cadastrada (`/config` ou prefill IRPF
  via E1) — o dogfood começa com `bank_accounts` vazia.

## Alternativas rejeitadas

- **Re-wire do catálogo no E2** (restaurar `family_members.json` para os parsers):
  conserta o sintoma re-criando o acoplamento parser↔catálogo que a extração de-leak
  quer eliminar; o E3 já tem catálogo + `account_number` + é choke point único para
  parsers nativos e E2-llm. Rejeitado (co-design `data-engineer` 2026-07-08).
- **Emendar [[ADR-278]] normalizando 92% classe-c como esperado**: contradiz a
  estratégia B4 (nullable → obrigatório) e deixa lineage/dedup/override degradados no
  cenário-núcleo do ICP (família multi-membro). Rejeitado.
- **CPF como token de identidade no hash** (estado atual do BTG): PII em artefato
  encriptado-at-rest mas plaintext no payload, e identidade mista CPF/slug — mesmo
  gênero do bug do consolidador E1.5c (membro por slug vs CPF). Rejeitado.

## Consequências

- ✅ Cobertura de `natural_key` no E4 salta de ~8% para ~cobertura-de-membro;
  `member_hashes`/reverse-lineage ([[ADR-279]]) passam a cobrir o fluxo de caixa.
- ✅ Dedup v2 e override v2 ganham discriminação por membro; leak de CPF eliminado.
- ⚠️ Hashes v2 mudam em massa nas linhas atribuídas → overrides existentes órfãos
  sem a reancoragem prévia (D4a); rebaseline E3/E4/E5 + view-model esperado (D4b).
- ⚠️ Sem conta cadastrada e sem hint estrutural, a linha permanece classe-c —
  honesto por design; a telemetria D5 expõe o resíduo em vez de escondê-lo.

## Sequenciamento (lane única, 4 fases)

| Fase | Conteúdo | Gate |
| --- | --- | --- |
| F1 | Resolver no E3 flag-OFF + strip CPF incondicional (D3) + hints crus E2 (auditoria por parser) + telemetria D5 | flag-OFF byte-idêntico **exceto** strip de CPF (só linhas BTG, reancoradas em F2); zero CPF em `titular` desde F1; testes de domínio da cadeia de resolução |
| F2 | Pré-flip dogfood: cadastro de contas (owner) + reancoragem de overrides (#873) | cobertura D5 reportada; zero órfãos pós-reancoragem |
| F3 | Flip dogfood: G-f diff + rebaseline manifestado + conservação E5 | goldens verdes pós-manifesto; conservação E5 tolerância zero |
| F4 | Flip default + follow-up `natural_key` obrigatório ([[ADR-278]] B4 passo final) | `natural_key` presente em ≥0.98 das linhas E4 de workspaces flippados (espelha o 0.98 da [[ADR-282]] §7) por ≥1 sprint |

## Referências

- Diagnóstico + números: sessão 2026-07-08 (workspace dogfood, run `6eb0cc8c`).
- Co-design: `data-engineer` 2026-07-08 (resolução no E3; slug sempre; PII do BTG;
  cardinalidade ≠ só-hashes; flag obrigatória).
- [[ADR-226]] — `AccountResolver` + `account_number` como discriminador (substrato).
- [[ADR-282]] §7 + runbook Fase E (#873) — reancoragem de overrides.
- [[ADR-287]] — flip dedup v2 + emenda 2026-07-08 (registro corrigido).
