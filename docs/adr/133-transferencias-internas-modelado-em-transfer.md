---
id: ADR-133
type: adr
title: "`transferencias_internas` modelado em `transfer_configs` (workspace-scoped)"
status: Decidido
date: "2026-04-25"
relates_to: ["[[ADR-082]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 133"]
tags:
  - area/backend
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 79
---

# ADR-133 — `transferencias_internas` modelado em `transfer_configs` (workspace-scoped)

**Status:** Decidido • **Data:** 2026-04-25 • **Relaciona**
[ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
(blobs DB-first com materialização para o pipeline),
[ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e) (use case
puro, router monta dependências),
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)
(elimina leitura de disco em request-path),
[ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco)
(padrão DB-first com fallback global).

**Contexto:** O bloco `transferencias_internas` em
`config/family_members.json` (recipients/patterns para
`InternalTransferDetector`) era **único globalmente** — vivia só no
repo, sem modelagem em DB. Consequências práticas:

1. Bug original que motivou esta decisão: PIX entre contas próprias da
   família apareciam no card "Consumo Consciente" como gastos pontuais
   porque o E4 caía em `nao_identificado` (config global desatualizada
   ou divergente do workspace) — usuário não tinha como corrigir.
2. `serialize_family_members` em `config_materializer.py` re-emitia
   `family_members.json` com `membros`/`banco_membro` do DB, mas o
   bloco `transferencias_internas` era preservado **só** porque
   `_copy_global` copiava o arquivo antes do override. Mudança trivial
   (renomear arquivo, dropar `_copy_global`) quebraria o E4 em silêncio.
3. O use case `list_consumo_pontuais` lia `family_members.json` e
   `categorization.json` diretamente do disco — quebra de SRP/ISP e
   roça com [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)
   (request-path tocando filesystem para regra de domínio).

Alternativas:

- **(a) Estender `FamilyMember`** com campos `recipients`, `patterns_pix`,
  etc. Misturar entidades semanticamente diferentes (membro físico ×
  config de transferência) em uma tabela, com complicação extra para
  `patterns_bank_specific` (chave variável).
- **(b) Acoplar a `categorization.json`** (que já tem
  `internal_transfer_patterns`). Quebra coesão: `transferencias_internas`
  é família-específico (recipients são pessoas/contas), não
  categorização genérica.
- **(c) JSON-blob dedicado `TransferConfig`**, igual aos outros 3 blobs
  (`PipelineConfig`, `InstitutionConfig`, `ReportLayout`). Estrutura
  análoga, repo paramétrico já existe — custo marginal mínimo.

**Decisão:** Adotar (c). Nova tabela `transfer_configs` com
`workspace_id` único + `config_json` (4 campos: `patterns_pix`,
`patterns_global`, `patterns_bank_specific`, `recipients`).

`ConfigBlobRepository` ganha o novo modelo no Union/TypeVar (cobre 4
modelos isomórficos). Use cases `get_transfer_config` /
`update_transfer_config` no slice `application/config_blob/`. Endpoints
`GET/PUT /workspaces/{id}/config/transfer`. Materializer ganha
`_override_transfer_config` que aplica overlay no `family_members.json`
**depois** de `_override_family_members` (rede de proteção: sem row no
DB, recupera o bloco do global pra compensar o overwrite que
`serialize_family_members` faz).

`list_consumo_pontuais` deixa de ler disco; recebe
`InternalTransferDetector` injetado pelo router via
`resolve_internal_transfer_detector(workspace_id, repo, defaults)` —
DB-first, fallback para `ConfigDefaultsLoader` quando não há row.

**Consequências:**

- ✅ Cada workspace pode customizar recipients/patterns (família,
  conjuge, contas próprias variam por usuário).
- ✅ Use case puro alinhado com [ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e);
  zero I/O de disco em request-path
  ([ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)).
- ✅ Pipeline E4 continua lendo `family_members.json` materializado —
  zero mudança no contrato de scripts.
- ⚠️ Workspace sem row em `transfer_configs` cai no global silencio-
  samente. Documentado como comportamento esperado (sem regressão vs.
  pré-ADR-133).
- ⚠️ UI de edição fica como ADR-133b (sessão dedicada) — backend
  destrava edição via curl/admin agora.
