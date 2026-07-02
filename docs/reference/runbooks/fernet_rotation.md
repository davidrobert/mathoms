---
type: runbook
title: "Rotação de chave Fernet (MultiFernet) — procedure operacional"
tags:
  - type/runbook
  - area/security
  - area/ops
---

# Runbook — Rotação de chave Fernet (ADR-171 · W3-T04)

> **Quando usar:** rotação periódica trimestral (compliance LGPD/ISO 27001),
> suspeita de comprometimento da `MATHOMS_FERNET_KEY`, ou offboarding de
> pessoa com acesso a secrets de produção.
>
> **O que é cifrado com Fernet:** `family_members.cpf_encrypted`,
> `llm_configs.api_key_encrypted`, `password_vault.encrypted_password`,
> `protections.policy_ref`, `pipeline_artifacts.content_json` (sentinel
> ADR-231, com `kid` = sha256(key primária)[:8]).

## Pré-requisitos

- Backup recente do Postgres confirmado (drill G1, [[ADR-228]]) — rotação
  reescreve todas as linhas cifradas.
- Acesso ao env de deploy (Coolify) para editar variáveis do backend **e**
  do worker Celery — env mismatch entre eles causa decrypt fail intermitente.
- Janela sem deploy concorrente.

## Procedure

1. **Gerar a key nova** (não substitui a antiga ainda):

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Abrir a janela de rotação** — setar em TODOS os serviços (API + worker),
   com a key **nova primeiro**:

   ```
   MATHOMS_FERNET_KEYS=<key_nova>,<key_antiga>
   ```

   Manter `MATHOMS_FERNET_KEY` intocada (fallback). Redeploy síncrono de
   API + worker (ADR-171: deploy assimétrico = decrypt fail intermitente).

3. **Validar a janela** — smoke: login, abrir um relatório, criar/ler um
   secret novo (ex.: password de PDF). Novos encrypts já usam a key nova;
   ciphertexts antigos continuam legíveis.

4. **Dry-run da rotação** (só conta, nada escreve):

   ```bash
   celery -A backend.app.worker call rotate_fernet_secrets --kwargs '{"dry_run": true}'
   ```

   Inspecionar o report no log do worker: `rotated` esperado > 0,
   `failed` deve ser **0**. `failed` > 0 = ciphertext ilegível pelas duas
   keys — **PARE** e investigue antes de prosseguir (provável key antiga
   errada na CSV).

5. **Rodar a rotação real**:

   ```bash
   celery -A backend.app.worker call rotate_fernet_secrets
   ```

   Idempotente e resumível — re-rodar após interrupção é seguro (valores já
   na key primária são skip).

6. **Verificar conclusão** — re-rodar o dry-run: todos os targets com
   `rotated: 0` e `failed: 0`. Query de conferência dos artifacts:

   ```sql
   SELECT content_json->>'kid' AS kid, count(*)
   FROM pipeline_artifacts
   WHERE content_json->>'_encrypted' = 'true'
   GROUP BY 1;
   -- esperado: apenas o kid da key nova
   ```

7. **Fechar a janela** — após ≥1 ciclo de uso normal sem `decrypt fail` nos
   logs (`mathoms.crypto.artifact_decrypt_failed`):

   ```
   MATHOMS_FERNET_KEY=<key_nova>
   MATHOMS_FERNET_KEYS=            # remover/esvaziar
   ```

   Redeploy síncrono. Descartar a key antiga do gerenciador de secrets.

## Rollback

- **Antes do passo 5:** reverter `MATHOMS_FERNET_KEYS` e redeploy — nenhum
  dado foi reescrito.
- **Depois do passo 5:** NÃO remover a key antiga da CSV até o passo 7 —
  o MultiFernet mantém tudo legível com as duas keys. Rotação parcial não é
  estado de erro (re-rodar completa).
- **Key nova comprometida durante a janela:** gerar terceira key e repetir
  a procedure com `MATHOMS_FERNET_KEYS=<key_3>,<key_nova>,<key_antiga>`.

## Drill

Trimestral em staging (registrado em [docs/reference/RUNBOOK.md](../RUNBOOK.md)):
executar passos 1–7 completos com dado sintético e cronometrar. RTO alvo da
procedure inteira: < 30min para volume de staging.
