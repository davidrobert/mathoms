---
id: ADR-174
type: adr
title: "Off-site backup criptografado em Cloudflare R2 + restore drill"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-005]]", "[[ADR-038]]", "[[ADR-058]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 174"]
tags:
  - type/adr
  - status/proposto
size_lines: 36
---

# ADR-174 — Off-site backup criptografado em Cloudflare R2 + restore drill

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-005](#adr-005--vps-hetzner-para-produção), [ADR-038](#adr-038--docker-volume-para-storage-prod), [ADR-058](#adr-058--vps-cx32-para-sizing). **Origem:** SR-004 + BB-007 (W4-T01).

**Contexto:** Hoje backup de Postgres é só local (Hetzner CX32). Falha de DC (incêndio Strasbourg-style), corrupção de filesystem, ataque ransomware encriptando o disco — tudo isso seria **perda total**. RPO atual = ∞ off-site. LGPD exige plano de DR documentado para tratamento de dados pessoais. Storage ZIP do BlobStore (uploads) também não tem off-site.

**Alternativas avaliadas:**

1. **Hetzner Storage Box** — mesmo provider, mesmo continente; falha catastrófica do DC ataca ambos. Rejeitada.
2. **AWS S3 (eu-west)** — caro ($0.023/GB), egress cobrado, 3rd-party fora da Europa. Rejeitada.
3. **Cloudflare R2 (eu-central) (escolhida)** — $0.015/GB, **zero egress fees**, EU region (LGPD ok), S3-compatible API.
4. **Backblaze B2** — competitive pricing mas EU region only via reseller; menos integration. Avaliada como fallback.

**Decisão:** Adotar (3).

- **`dev/backup_postgres.sh` (NOVO):** cron daily 03:00 UTC. `pg_dump | gpg --encrypt --recipient backup@mathoms.ai | aws s3 cp - s3://mathoms-backups-eu/postgres/<date>.sql.gz.gpg`.
- **Retention:** 7 daily + 4 weekly + 12 monthly. Lifecycle policy R2.
- **Encryption:** GPG + key stored em vault separado (NOT no servidor) — passphrase em env de CI/CD humano-only.
- **Restore drill em staging trimestral:** `dev/restore_drill.sh` baixa último backup, restora em DB efêmero, roda 5 query-canário (count workspaces, latest pipeline_run, etc.). Resultado registrado em RUNBOOK §4.
- **RPO declarado:** **24h**. RTO: **4h** (pull de R2 + restore + smoke).
- **Same para BlobStore:** R2 cross-region replication (R2-to-R2) configurada se decisão de adotar R2 também para uploads (referenciar ADR-038 follow-up).

**Consequências:**

- ✅ DR multi-region — falha total Hetzner não é evento de extinção.
- ✅ Custo ~$3/mês para 200GB (escala linear).
- ✅ Compliance LGPD: plano de DR documentado e testado.
- ⚠️ GPG passphrase fora do servidor é "secret de bootstrap" — armazenamento humano (1Password vault Mathoms). Trade-off necessário.
- ⚠️ Restore drill trimestral é processo manual; automação opcional pós-W4-T05.
- ❌ R2 free tier 10GB; mensal real ~$3 — billing precisa estar configurada.

**Implementação:** lane W4-T01. Vira `Decidido (W4-T01)` no merge.

**Referências:** [plan/PLATFORM_REVIEW/_README.md §W4-T01](plan/PLATFORM_REVIEW/_README.md), findings SR-004, BB-007.
