---
id: ADR-118
type: adr
title: "Flip do default `MATHOMS_USE_DB_ARTIFACTS` para `True`"
status: Decidido
phase: "A6"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 118"]
tags:
  - type/adr
  - status/decidido
size_lines: 45
---

# ADR-118 — Flip do default `MATHOMS_USE_DB_ARTIFACTS` para `True`

**Status:** Decidido (A6) • **Data:** 2026-04-23

**Contexto:** Cutover DB do `ArtifactStore` (ADR-083, ADR-106) está completo:
`DBArtifactStore` validado em produção, `dev/compare_disk_vs_db.py --strict`
verde nos workspaces piloto (A6b/A6-human), goldens de paridade estáveis.
O flag `MATHOMS_USE_DB_ARTIFACTS` permanecia com default `False` apenas por
conservadorismo, forçando cada novo deploy a opt-in explícito. Mantê-lo em
`False` convida regressão silenciosa — caminho DB deixa de ser exercitado
em CI e em dev local por omissão, mesmo sendo o alvo operacional.

**Decisao:** Flipar o default de `USE_DB_ARTIFACTS` em
`backend/app/core/config.py` de `False` → `True`. CI consolidado roda
`backend/tests/` **apenas** com `MATHOMS_USE_DB_ARTIFACTS=true` (caminho
`False` deixa de ser gate — permanece como fallback de rollback, validado
ad-hoc se necessário). Override por-workspace
(`workspaces.use_db_artifacts_override`) continua disponível em ambos os
sentidos (forçar disco para debug; forçar DB em workspace que queira antecipar
cutover antes de redeploy global — reverso ficou NOOP após flip).

**Consequencias:**
- ✅ CI exercita o caminho-alvo por default; regressões no `DBArtifactStore`
  aparecem em PR (antes eram mascaradas pelo job `continue-on-error` de
  pre-validação — removido em favor do gate único).
- ✅ Dev local reproduz produção sem `.env` especial — `make dev` já roda
  em modo DB.
- ✅ Eliminado job CI duplicado (`backend-tests-db-artifacts`) — ~15min/push
  economizados.
- ⚠️ **Rollback:** setar `MATHOMS_USE_DB_ARTIFACTS=false` + redeploy
  (runbook `docs/runbooks/cutover.md §Rollback`). Runbook mantido como
  referência histórica e procedimento de emergência.
- ⚠️ Workspaces com `use_db_artifacts_override=TRUE` ficam com valor
  redundante mas correto — limpeza é housekeeping opcional, não obrigatório.
- ❌ Caminho `DiskArtifactStore` deixa de ter gate CI dedicado; se rollback
  for necessário em produção, paridade precisará ser revalidada manualmente
  via `dev/compare_disk_vs_db.py`.

Supersedes: marca A6b/A6c/A6-human como concluídos no que se refere ao
default global; atualiza o trade-off ⚠️ documentado em
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6),
que registrava o default `False` da época. Override per-workspace
(ADR-106) continua válido.
