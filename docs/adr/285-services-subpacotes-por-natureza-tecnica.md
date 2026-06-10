---
id: ADR-285
type: adr
title: "backend/app/services/: subpacotes por natureza técnica, nunca por domínio de negócio"
status: Proposto
phase: "Débito técnico"
date: "2026-06-09"
relates_to:
  - "[[ADR-101]]"
  - "[[ADR-089]]"
  - "[[ADR-097]]"
  - "[[ADR-111]]"
supersedes: []
superseded_by: []
aliases: ["ADR 285", "services taxonomy", "services por natureza"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/architecture
---

# ADR-285 — `backend/app/services/`: subpacotes por natureza técnica, nunca por domínio de negócio

**Status:** Proposto (Débito técnico) • **Data:** 2026-06-09 • **Relaciona**
[[ADR-101]] (R15 — Application layer por domínio), [[ADR-089]]/[[ADR-097]]
(ISP em services de domínio), [[ADR-111]] (stateless — singletons lazy).

## Contexto

`backend/app/services/` chegou a ~100 entries (97 módulos flat + `classification/`
+ `internal_ops/`), crescimento orgânico sem critério de agrupamento. Surgiu a
recomendação de "quebrar em subpacotes por domínio". A avaliação (senior-cto,
2026-06-09) identificou falha de premissa: **a taxonomia de domínio já existe**
em `backend/app/application/` (28 subpacotes — `goal/`, `document/`, `task/`,
`transaction/`… — padrão R15/ADR-101, um use case por endpoint). Replicar
domínio dentro de `services/` criaria dois eixos de organização concorrentes
(`application/goal/` vs `services/goal/`) e ambiguidade permanente de "onde
mora X" — pior que flat.

O que `services/` mistura de fato são **duas naturezas**: (a) adapters/infra
cross-cutting (`crypto`, `vault`, `db_artifact_store`, `events`, `llm_cache`,
rate limits…) e (b) lógica de use-case represada (`goal_service`,
`task_service`, `document_processor`…) cujo destino canônico é
`application/<domain>/`.

## Decisão

1. **Regra de classificação:** subpacotes de `services/` agrupam **por natureza
   técnica** (o que o módulo *é*), nunca por domínio de negócio (sobre o que
   ele *fala*). Domínio de negócio por subpacote é exclusividade de
   `application/<domain>/` (R15).
2. **Frente 1 — split por natureza (lane futura, quando `services/` esfriar):**
   `services/security/` (crypto, vault, password_vault_reader,
   brute_force_lockout, register_rate_limit, protection_pii, access_audit) ·
   `services/storage/` (db_artifact_store, artifact_reader, storage, llm_cache,
   category_cache, fiscal_cache) · `services/pipeline/` (pipeline_adapter,
   pipeline_client, pipeline_service, document_pipeline_sync,
   pipeline_failure_reasons, stage_duration_estimator, events, retry_config) ·
   `services/documents/` (document_*, content_classifier, canonical_routing —
   consolidação com `classification/` avaliada na lane). Demais módulos de
   domínio **ficam flat** até a Frente 2.
3. **Frente 2 — drenagem oportunística (boy-scout, débito AR no
   PLATFORM_REVIEW):** lane que já toca `*_service.py` de domínio avalia migrar
   a lógica de use-case para `application/<domain>/`, deixando em `services/`
   só adapter fino. Não é projeto dedicado.
4. **Execução da Frente 1:** incremental, 1 subpacote por PR, com **shim de
   re-export temporário** no path antigo (imports em PRs em voo continuam
   resolvendo); remoção do shim + codemod final em PR separado após os PRs
   ativos em `services/` mergearem.

## Alternativas rejeitadas

- **Split por domínio dentro de `services/`** — duplica a taxonomia de
  `application/`, cria eixo concorrente; rejeitada.
- **Big-bang `git mv` de 97 módulos** — conflito de rebase garantido com 5+
  PRs em voo tocando `services/` (2026-06); rejeitada.
- **Status quo sem regra** — flatness vira débito sem critério e o próximo
  agente recria a ambiguidade; rejeitada.

## Consequências

- ✅ "Onde mora X" vira decidível: use case → `application/`, infra/adapter →
  `services/<natureza>/`.
- ✅ Shim elimina conflito com PRs em voo; codemod final é mecânico
  (~558 import lines, 5 patch-strings dotted em testes).
- ⚠️ Shims/`__init__` de subpacote não podem materializar singleton na
  importação ([[ADR-111]]) — paths de singletons lazy que mudarem entram no
  `STATELESS_AUDIT.md` §2.
- ⚠️ `pipeline-service/` tem namespace homônimo `app.services` (pacote Python
  independente) — fora do escopo de qualquer codemod.
- ⚠️ Discernimento por módulo na Frente 2 — não é codemod cego.

**Implementação:** Frente 1 em lane futura (gate: `services/` sem PRs em voo);
Frente 2 via débito registrado no
[plan/PLATFORM_REVIEW/_README.md](../plan/PLATFORM_REVIEW/_README.md). Esta ADR
flippa para `Decidido` no merge do primeiro PR de subpacote da Frente 1.
