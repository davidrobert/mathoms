---
id: ADR-171
type: adr
title: "Fernet rotation operacionalizada via MultiFernet"
status: Decidido
phase: W3-T04
date: "2026-05-06"
amended_at: ["2026-08-21"]
relates_to: ["[[ADR-007]]", "[[ADR-015]]", "[[ADR-060]]", "[[ADR-109]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 171"]
tags:
  - area/auth
  - area/ops
  - area/security
  - status/decidido
  - type/adr
size_lines: 33
---

# ADR-171 — Fernet rotation operacionalizada via MultiFernet

**Status:** Decidido (W3-T04) • **Data:** 2026-05-06 • **Relaciona** [ADR-007](#adr-007--fernet-app-level-para-criptografia), [ADR-015](#adr-015--vault-por-workspace), [ADR-060](#adr-060--fernet-dual-key-para-secret-rotation), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a). **Origem:** SR-003 (W3-T04).

> **Correção do gate (2026-08-21):** `skipped` mistura três populações e
> nenhuma condição o lê; a checagem por `kid` valida um rótulo autodeclarado,
> não o ciphertext. Pós-rotação, `rotated=0 failed=0` é tautologia. Ver §Emenda.

**Contexto:** ADR-060 declarou dual-key como capacidade roadmap, mas hoje `backend/app/services/vault.py` usa `Fernet(MATHOMS_FERNET_KEY)` single-key. Não há procedure para rotacionar — chave comprometida = re-encrypt manual de todo o workspace. Sem runbook, sem dry-run, sem teste. Falha de compliance LGPD (rotation periódica de chaves criptográficas é exigência implícita do ANPD em segredos sensíveis tratados).

**Alternativas avaliadas:**

1. **Status quo (single-key, rotation manual ad-hoc)** — risco operacional alto, sem audit trail. Rejeitada.
2. **Re-encrypt eager (todos secrets na hora da rotation)** — janela de migration custosa, lock prolongado. Rejeitada.
3. **MultiFernet com re-encrypt lazy + Celery task batch (escolhida)** — `MultiFernet([new, old])` aceita decrypt com qualquer key; re-encrypt incremental em background.

**Decisão:** Adotar (3).

- **Env:** `MATHOMS_FERNET_KEYS=key_new,key_old` (CSV; primeiro = key de encrypt; demais = decrypt-only).
- **Vault**: `MultiFernet([Fernet(k) for k in keys])` substitui `Fernet`. Decrypts existentes funcionam; novos secrets usam `key_new`.
- **Celery task `rotate_fernet_secrets`:** itera `EncryptedSecret` em batches de 100; faz `decrypt → encrypt(key_new) → update`. Idempotente, resumível.
- **Runbook em `docs/reference/runbooks/fernet_rotation.md`:** procedure passo-a-passo (gerar key, deploy com 2 keys, rodar Celery, validar count, deploy com 1 key).
- **Drill em staging trimestral** registrado em RUNBOOK.

**Consequências:**

- ✅ Rotation sem downtime.
- ✅ Compliance LGPD/ISO 27001 atendido (rotation auditável).
- ✅ Runbook fecha gap operacional crítico para incidente.
- ⚠️ Janela de duas chaves ativas requer disciplina — env mismatch entre workers = decrypt fail intermitente. Mitigação: deploy synchronous via Coolify (W4-T02).
- ❌ Não cobre rotation automática agendada — operação manual com runbook é first iteration.

**Implementação:** lane W3-T04 (2026-07-02) — `MATHOMS_FERNET_KEYS` CSV em
`config.py` (validação prod contra defaults inseguros), `MultiFernet` +
`needs_rotation` em `vault.py`, `kid` de artifacts segue a key primária
(`crypto._key_id`), task `rotate_fernet_secrets` (colunas + sentinels ADR-231,
batches de 100, dry-run) e runbook
[fernet_rotation.md](../reference/runbooks/fernet_rotation.md).

**Referências:** [archive/PLATFORM_REVIEW_PLAN-2026-07-08.md §W3-T04](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md), finding SR-003.


## Emenda 2026-08-21 — `skipped` não é evidência, e `kid` é rótulo autodeclarado

Três cegueiras medidas no gate desta ADR, todas por construção:

1. **`skipped` mistura três populações** — row já na chave primária, row em
   plaintext, e row que não decifra com chave nenhuma (`needs_rotation`
   devolve `False` nos dois últimos casos, tornando o ramo `failed`
   inalcançável para as 4 colunas). Nenhuma condição do gate lê `skipped`, e
   foi dentro dele que 418 artifacts em plaintext ficaram escondidos por 3
   meses (aritmética na emenda de [[ADR-231]]).
2. **`kid` é rótulo autodeclarado.** `_rotate_artifact_row` sai cedo quando
   `payload["kid"] == current_kid`, **sem decriptar**. Logo "nenhuma row tem
   kid antigo" e `rotated=0` afirmam a mesma coisa, e nenhuma das duas afirma
   que o corpus **lê**. Row com kid correto e `ct` corrompido fecha o gate.
   Pós-rotação, `rotated=0 failed=0` é tautologia: nenhum byte de ciphertext é
   exercitado.
3. **O gate fechava sobre banco vazio** — corrigido em `4c51cfba` (PR #1563)
   com `empty_corpus_problem`: report todo-zero não fecha.

**Correções decididas:**

- **4º contador `plaintext`** como bucket próprio em `_rotate_artifacts` (não
  query re-derivada em outro lugar), e a métrica permanente mora em
  `ArtifactPruneReport.to_log_extra()`, que roda diário — não só no
  `fernet_rotation_gate`, que só existe dentro de uma janela aberta à mão.
- **O gate é sobre recência, não sobre o absoluto.** `plaintext > 0` fecharia
  para sempre depois do backfill e viraria regra morta. O gate é
  `plaintext com created_at > cutover de encryption > 0`, que detecta o modo
  de falha **vivo** (flag `ENCRYPT_PIPELINE_ARTIFACTS` desligada, ou writer
  contornando `DBArtifactStore.write`). O absoluto fica como métrica reportada.
- **Probe de integridade com a primária ISOLADA**, não via `MultiFernet`:
  dentro da janela o MultiFernet aceita a chave antiga, então row que só
  decifra com a velha **passa** o verify. Sem `json.loads` — a propriedade
  desejada é "todo ciphertext é legível", e o parse de 317 MB de JSON é o
  custo, não a prova. Passe separado, ao **fechar** a janela, fora do caminho
  crítico dos ~30 min. Amostragem recusada: row indecifrável clusteriza por
  `kid` e por era, então amostra prova sobre a população errada.

**Subcomando `window`** (mergeado em `4c51cfba`) cobre o vão pós-passo 7: o
`verify` exige 2 chaves e deixa de existir depois que a janela fecha.

**A armadilha do fallback**, também fechada em 2026-08-21: o §2 do runbook
manda deixar `MATHOMS_FERNET_KEY` intocada durante a janela, então ela guarda
a chave **antiga**; como `resolve_fernet_keys` é `FERNET_KEYS or FERNET_KEY`,
apagar só a CSV para "fechar a janela" tornaria a antiga efetiva e o corpus
inteiro ilegível. O invariante correto é **`FERNET_KEY` é sempre a primária
vigente**, e sob ele o passo 7 vira uma deleção segura por construção.
