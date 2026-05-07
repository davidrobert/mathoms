---
id: ADR-171
type: adr
title: "Fernet rotation operacionalizada via MultiFernet"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-007]]", "[[ADR-015]]", "[[ADR-060]]", "[[ADR-109]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 171"]
tags:
  - type/adr
  - status/proposto
size_lines: 33
---

# ADR-171 — Fernet rotation operacionalizada via MultiFernet

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-007](#adr-007--fernet-app-level-para-criptografia), [ADR-015](#adr-015--vault-por-workspace), [ADR-060](#adr-060--fernet-dual-key-para-secret-rotation), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a). **Origem:** SR-003 (W3-T04).

**Contexto:** ADR-060 declarou dual-key como capacidade roadmap, mas hoje `backend/app/services/vault.py` usa `Fernet(MATHOMS_FERNET_KEY)` single-key. Não há procedure para rotacionar — chave comprometida = re-encrypt manual de todo o workspace. Sem runbook, sem dry-run, sem teste. Falha de compliance LGPD (rotation periódica de chaves criptográficas é exigência implícita do ANPD em segredos sensíveis tratados).

**Alternativas avaliadas:**

1. **Status quo (single-key, rotation manual ad-hoc)** — risco operacional alto, sem audit trail. Rejeitada.
2. **Re-encrypt eager (todos secrets na hora da rotation)** — janela de migration custosa, lock prolongado. Rejeitada.
3. **MultiFernet com re-encrypt lazy + Celery task batch (escolhida)** — `MultiFernet([new, old])` aceita decrypt com qualquer key; re-encrypt incremental em background.

**Decisão:** Adotar (3).

- **Env:** `MATHOMS_FERNET_KEYS=key_new,key_old` (CSV; primeiro = key de encrypt; demais = decrypt-only).
- **Vault**: `MultiFernet([Fernet(k) for k in keys])` substitui `Fernet`. Decrypts existentes funcionam; novos secrets usam `key_new`.
- **Celery task `rotate_fernet_secrets`:** itera `EncryptedSecret` em batches de 100; faz `decrypt → encrypt(key_new) → update`. Idempotente, resumível.
- **Runbook em `docs/runbooks/fernet_rotation.md`:** procedure passo-a-passo (gerar key, deploy com 2 keys, rodar Celery, validar count, deploy com 1 key).
- **Drill em staging trimestral** registrado em RUNBOOK.

**Consequências:**

- ✅ Rotation sem downtime.
- ✅ Compliance LGPD/ISO 27001 atendido (rotation auditável).
- ✅ Runbook fecha gap operacional crítico para incidente.
- ⚠️ Janela de duas chaves ativas requer disciplina — env mismatch entre workers = decrypt fail intermitente. Mitigação: deploy synchronous via Coolify (W4-T02).
- ❌ Não cobre rotation automática agendada — operação manual com runbook é first iteration.

**Implementação:** lane W3-T04. Vira `Decidido (W3-T04)` no merge.

**Referências:** [PLATFORM_REVIEW_PLAN.md §W3-T04](PLATFORM_REVIEW_PLAN.md), finding SR-003.
