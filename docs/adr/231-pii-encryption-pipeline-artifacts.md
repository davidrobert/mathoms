---
id: ADR-231
type: adr
title: "Encryption at-rest de PII em pipeline_artifacts via Fernet wrapper (hook em DBArtifactStore)"
status: Decidido
phase: A11.W2
date: "2026-05-20"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-109]]"
  - "[[ADR-110]]"
  - "[[ADR-111]]"
  - "[[ADR-171]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 231"
  - "PII encryption"
  - "pipeline_artifacts encryption"
  - "Fernet artifact"
tags:
  - area/security
  - area/pipeline
  - area/db
  - phase/a11
  - status/decidido
  - type/adr
---

## Contexto

`pipeline_artifacts.content_json` (JSONB) hoje guarda **plaintext PII pesado** em vários stages: CPF, nome completo de family members (E1/E1.5/E1.5c), payload IRPF inteiro (E1.6), raw text extraído de PDFs/imagens (E2-llm), descrições de transações com PII de terceiros ("TED PARA FULANO CPF XXX" em E3/E4), agregados monetários (E5). Hoje a única proteção é controle de acesso via tenancy (workspace_id) — leak de DB ou backup vaza tudo em plaintext.

Sprint A11 W2-T01 (`docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` linhas 300-309) atribui prioridade P0 ao fechamento desse gap. Finding origem DE-003 (data-engineer 2026-05-06).

Hoje a base Fernet já existe em produção via [`backend/app/services/vault.py`](../../backend/app/services/security/vault.py) — singleton com `MATHOMS_FERNET_KEY`, fail-fast se ausente, usado para PDF passwords + LLM keys + `workspaces.cpf_encrypted`. W3-T04 ([[ADR-171]]) propõe MultiFernet rotation cobrindo essa chave.

### Trade-offs

| Eixo | Opção A — All stages encrypted by default | Opção B — Lista PII_BEARING_STAGES seletiva |
|---|---|---|
| Drift risk | Zero (novo stage → encrypted auto) | Alto (extract_informe_aluguel adicionado recente; auditoria periódica vira tech debt) |
| Custo CPU | Fernet ~1ms/row × ~5-50k rows/run = 5-50s/run (despreciável vs schema validation + I/O JSONB) | Idem para subset; ganho real é só nos stages "puros" |
| Mental model | Simples: "tudo no pipeline_artifacts é encrypted" | Complexo: "depende do stage + entender PII inventário" |

Encryption at-rest via PostgreSQL TDE / pgcrypto column-level foi avaliada e descartada — chave fica no DB (`pgp_sym_encrypt(data, key)`), dificulta rotation cross-region, gargalo de CPU no Postgres. App-level Fernet com KMS-backed key é padrão fintech defensável e mantém chave em env/KMS sob controle do operador.

## Decisão

**Adotar Opção A — encrypt all pipeline_artifacts by default**, via hook em `DBArtifactStore.write` que aplica encryption após o JSON-schema validation hook existente, e hook em `DBArtifactStore.read` que decripta automaticamente.

### D1 — Sentinel format

Quando criptografado, `content_json` é substituído por:

```json
{
  "_encrypted": true,
  "v": 1,
  "kid": "abc12345",
  "ct": "<base64-fernet-token>"
}
```

- `_encrypted: true` — flag idempotente (backfill skipa se já encriptado).
- `v: 1` — versão do contrato (permite evolução para field-level v2 sem breaking).
- `kid` — fingerprint da chave Fernet (`hashlib.sha256(key).hexdigest()[:8]`). Permite W3-T04 progress tracking (`WHERE content_json->>'kid' = '<old>'`) sem decrypt-probe (refino sugerido por `data-engineer` + `sre-devops`).
- `ct` — Fernet ciphertext base64.

Schemas em `config/schemas/*.schema.json` **não** mudam — rejeitam sentinel naturalmente porque nenhum schema declara `_encrypted` em `properties`. Garante que `validate_dict` (hook `SCHEMA_BY_STAGE` em [[ADR-212]] PR3) roda **antes** de encrypt sobre o dict de domínio, não sobre o sentinel.

### D2 — Chave Fernet

**Reusar `MATHOMS_FERNET_KEY`** via wrapper `backend/app/services/crypto.py`:

```python
from backend.app.services.vault import get_vault

def encrypt_artifact_payload(payload: dict) -> dict:
    fernet_key = settings.FERNET_KEY.encode()
    kid = hashlib.sha256(fernet_key).hexdigest()[:8]
    ciphertext = get_vault().encrypt(json.dumps(payload))
    return {"_encrypted": True, "v": 1, "kid": kid, "ct": ciphertext}
```

Justificativa: blast radius já é compartilhado de fato (vault guarda PDF passwords + LLM keys + CPF de workspace; perda da chave já é incidente máximo). Chave dedicada `MATHOMS_PIPELINE_FERNET_KEY` dobra a operação de rotation em W3-T04 sem reduzir risco real. Wrapper `crypto.py` isolado permite separar chaves no futuro (compliance LGPD exigir HSM, por exemplo) sem refactor de consumidores — mudança fica interna ao wrapper.

### D3 — Order of operations

**Write:**
1. Schema validation hook ([[ADR-212]] PR3 — `SCHEMA_BY_STAGE`).
2. Encrypt hook (este ADR) — se flag global `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS=true` (default).
3. INSERT/UPDATE em `pipeline_artifacts`.

**Read:**
1. SELECT do row.
2. Detect sentinel (`_encrypted: true`) — **sempre** decripta, independente do estado da flag global (compat com rows já encriptadas em revert).
3. Return dict plaintext ao consumidor.

### D4 — Kill switch / rollback flag

Setting `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS` (default `true`):

- `write()` bypass de encrypt se `false` (grava plaintext).
- `read()` **sempre** decripta sentinel detectado — flag não controla read.
- Read em mode disabled com row encriptada loga `WARNING` (`mathoms.crypto.read_in_disabled_mode`) para detectar config drift.

**Rollback é one-way:** uma vez encriptado, flag em `false` não desencripta histórico — só protege novos writes. Reverso (decrypt-backfill) é mudança de design + ADR própria.

### D5 — Backfill

Script `dev/migrate_encrypt_existing_artifacts.py`:

- **Idempotente:** filtra `WHERE content_json->>'_encrypted' IS NULL OR content_json->>'_encrypted' = 'false'`.
- **Batch:** 500 rows por commit (evita WAL explosion + lock contention).
- **Cursor em arquivo:** `_scratch/backfill_<workspace>_cursor.txt` permite resume após erro/SIGTERM.
- **`--dry-run` default:** reporta count + ETA + sample SHA-256 antes/depois.
- **`--apply`** exige confirmação interativa.
- **`--workspace <id>`** restringe escopo.
- **Pós-backfill:** sugestão de `VACUUM (ANALYZE) pipeline_artifacts` (JSONB update reescreve row inteira em MVCC; bloat ~2x antes do vacuum).

**Backfill operacional em prod (futuro):** quando W3-T04 aterrissar MultiFernet rotation, a primeira execução de rotation é equivalente a backfill (encrypt rows com `_encrypted: false` usando nova chave). Logo, evolução natural: script `dev/` cobre staging/dev; Celery task `rotate_pipeline_artifacts` (W3-T04) cobre prod com checkpoint persistido + `pg_advisory_lock(workspace_id)`. ADR-171 [[ADR-171]] deve mencionar explicitamente esse hand-off.

### D6 — Observability

Logging estruturado (ADR-110 conventions, namespace `mathoms.crypto.*`):

- `mathoms.crypto.artifact_encrypted` — INFO (rate-limited, ~1/run para evitar log spam).
- `mathoms.crypto.artifact_decrypted` — INFO (rate-limited).
- `mathoms.crypto.artifact_encrypt_failed` — **ERROR / P0** (pipeline parado — abort).
- `mathoms.crypto.artifact_decrypt_failed` — **ERROR / P0** (chave perdida ou DB corrompido — alert).
- `mathoms.crypto.read_in_disabled_mode` — **WARNING / P2** (config drift; flag em `false` mas row encriptada lida).

Alertas reais (Sentry / Coolify webhook / Slack) vêm em W4-T03. Runbook DR para "chave perdida" fica em `docs/reference/runbooks/incidents/crypto_failure.md` (follow-up).

### D7 — Não-afeta

- **Auth portability ([[ADR-109]]):** `vault.py` mantém interface intacta. `crypto.py` apenas **consome** `get_vault().encrypt/decrypt`. `backend/tests/test_auth_portability.py` continua verde sem alteração.
- **Schema validation ([[ADR-212]] PR3):** roda antes de encrypt em write; consumidor recebe plaintext em read — validate vê shape correto, payload nunca corrompido sem detectar.
- **Pipeline boundaries (`dev/check_pipeline_boundaries.py`):** `crypto.py` vive em `backend/app/services/` (ok — pipeline lê apenas via `DBArtifactStore` que já é backend-side via SQLAlchemy).
- **Golden tests (`tests/test_e{3,4,5}_golden_execution.py`):** usam `InMemoryArtifactStore`, não passam pelo hook. Continuam transparentes.
- **Stateless rigoroso ([[ADR-111]]):** `crypto.py` é singleton lazy idempotente (`get_vault()` é singleton; novo helper apenas thin-wraps). Mesma classificação que `vault.py` em `STATELESS_AUDIT.md` §2.

## Alternativas consideradas

### (A) PostgreSQL pgcrypto column-level (`pgp_sym_encrypt`)

Auditor-friendly (visível no schema), mas:
- Chave no DB ou via `SET LOCAL` — key management acoplado ao Postgres, dificulta rotation cross-region.
- Performance: cada SELECT decripta no DB (CPU do Postgres, gargalo em escala).
- Não-portável entre engines (vendor lock-in ao Postgres).

**Descartada.** App-level Fernet + KMS-backed key é padrão fintech moderna.

### (B) Lista PII_BEARING_STAGES seletiva

`PII_BEARING_STAGES = {"E1", "E1.5", "E1.6", "E2-llm", "E3", "E4"}`. Mais cirúrgico, mas drift comprovado em A12 (`extract_informe_aluguel` adicionado sem ninguém pensar em PII). Custo CPU evitado é desprezível. **Descartada** (recomendação convergente de `data-engineer` + `sre-devops`).

### (C) Chave dedicada `MATHOMS_PIPELINE_FERNET_KEY`

Reduz blast radius marginalmente — mas blast radius **operacional** é o mesmo (perda da chave = incidente máximo). Dobra operação de rotation. Wrapper `crypto.py` permite separar no futuro sem breaking. **Descartada para MVP**, opção em aberto se LGPD requirement futuro (auditor exigindo segregação) chegar.

### (D) Field-level encryption (`cpf`, `nome` campos específicos)

Mais delicado: exige schema awareness do encrypt path. Quebra schemas se campo não declarado. **Descartada para MVP** — pode ser introduzido como `v: 2` do sentinel se necessário (ex.: indexação seletiva de campos não-PII).

## Consequências

**Positivas:**

- ✅ Encryption at-rest fecha gap LGPD em `pipeline_artifacts` (PII em CPF, nome, IRPF full payload, raw text bancário).
- ✅ Schema validation continua funcionando (order: validate → encrypt → write).
- ✅ Backward-compat via kill switch + read sempre tolerante.
- ✅ `kid` no sentinel destrava progress tracking em W3-T04 sem migrations adicionais.
- ✅ Pattern reutilizável: futuras tabelas com PII podem adotar o mesmo wrapper.

**Negativas:**

- ⚠️ Custo CPU adicional (~5-50s/run em workspaces grandes; mensurar em smoke pós-merge).
- ⚠️ Backfill em prod (futuro W3-T04) requer janela operacional + `VACUUM ANALYZE` posterior; bloat MVCC pode ~2x temporariamente.
- ⚠️ Debugging de DB diretamente vê ciphertext — devs precisam usar `DBArtifactStore.read()` ou helper de decrypt em scripts ad-hoc.
- ⚠️ Rollback de encryption é one-way (revert restaura plaintext em writes novos, mas histórico encriptado permanece).

**Riscos:**

| Risco | Mitigação |
|---|---|
| Chave perdida em prod = artefatos inacessíveis | `MATHOMS_FERNET_KEY` em backup encrypted-at-rest (R2 W4-T01 cobre); restore drill quarterly. |
| Race em backfill (pipeline writes paralelos) | Backfill em janela low-traffic + batch curtos; race window é segundos, `pipeline_run_id × stage × artifact_key` unique constraint resolve via last-write-wins (aceitável — backfill perde para write paralelo, próxima rotation recupera). |
| Performance regressão em prod | Smoke test pós-merge mede p95 stage; rollback flag bypass se necessário; benchmark em staging antes do cutover. |
| Goldens quebram | Confirmado em PR: goldens usam `InMemoryArtifactStore`, hook não dispara. |

## Gates desta ADR

- **PR de implementação:**
  - Cria `backend/app/services/crypto.py` (encrypt_artifact_payload + decrypt_artifact_payload + kid helper).
  - Adiciona setting `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS` em `backend/app/core/config.py`.
  - Patch `backend/app/services/storage/db_artifact_store.py` (encrypt em write pós-validate; decrypt em read).
  - Cria `dev/migrate_encrypt_existing_artifacts.py` (idempotent, batch, --dry-run default).
  - Tests:
    - `backend/tests/test_crypto_artifact.py` (roundtrip + kid stable + fail-safe sem key).
    - `backend/tests/test_db_artifact_store_pii_encryption.py` (encrypt on write + decrypt on read + kill switch + backward-compat read).
    - `backend/tests/test_migrate_encrypt_existing_artifacts.py` (dry-run + idempotência + batch + cursor).
- **Validação:**
  - `pre-commit run --all-files` verde.
  - `pytest backend/tests -q` verde.
  - `pytest tests -q` verde (pipeline não regrediu).
  - `pytest backend/tests/test_auth_portability.py -v` verde (não-regression ADR-109).
- **Closure:** flippa para `Decidido (Sprint A11.W2)` no merge do PR de implementação. Backfill operacional em prod fica em W3-T04 ([[ADR-171]]).

## Closure

Flippada para `Decidido (Sprint A11.W2)` em 2026-05-20 após merge de:

- [PR #359](https://github.com/davidrobert/mathoms/pull/359) (commit `d096107`) — implementação completa: `backend/app/services/crypto.py` (encrypt/decrypt + sentinel com `kid`), hook em `DBArtifactStore.write/read`, setting `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS`, `dev/migrate_encrypt_existing_artifacts.py`, 21 tests novos, todos os AC §"Gates desta ADR" verdes.

### Estado entregue

- ✅ Sentinel `{"_encrypted": true, "v": 1, "kid": "<sha256[:8]>", "ct": "<base64>"}` ativo em todos os stages que passam por `DBArtifactStore.write` (write-all-by-default).
- ✅ `kid` (key fingerprint) operacional — destrava progress tracking em W3-T04 via `WHERE content_json->>'kid' = '<old>'`.
- ✅ Kill switch `MATHOMS_ENCRYPT_PIPELINE_ARTIFACTS` operacional; default True; `read()` sempre decripta sentinel independente da flag (compat revert).
- ✅ Schema validation (ADR-212 PR3) preserva ordem `validate → encrypt → write` — schemas em `config/schemas/` não tocados (rejeitam sentinel naturalmente).
- ✅ Backfill staging/dev em `dev/migrate_encrypt_existing_artifacts.py` (idempotente, --dry-run default, batch 500 + cursor para resume).
- ✅ Logging estruturado namespace `mathoms.crypto.*` (encrypt_failed P0, decrypt_failed P0, read_in_disabled_mode P2).
- ✅ Auth portability (ADR-109) intacta — vault.py contrato preservado, wrapper apenas consome `get_vault().encrypt/decrypt`.

### Próximos passos rastreados

- **Backfill operacional em prod** — fica em W3-T04 ([[ADR-171]]) combinado com 1ª execução de MultiFernet rotation (re-encrypt rows com `kid` antigo é semanticamente equivalente). Celery task + checkpoint persistido em DB + `pg_advisory_lock(workspace_id)` ficam para esse momento.
- **Runbook DR** `docs/reference/runbooks/incidents/crypto_failure.md` — follow-up quando W4-T03 (Sentry) chegar; pattern para `decrypt_failed` P0 alert.

## Referências

- [[ADR-090]] — Money never float (encrypt preserva precisão; sentinel é flag + base64, não toca tipos).
- [[ADR-109]] — Auth portability (não afetado; vault.py contrato intacto).
- [[ADR-110]] — Logging estruturado (`mathoms.crypto.*` namespace).
- [[ADR-111]] — Stateless rigoroso (`crypto.py` é singleton lazy idempotente — mesma classe que vault.py).
- [[ADR-171]] — Fernet rotation MultiFernet (W3-T04; consome `kid` para progress tracking; hand-off de backfill prod via Celery task).
- [[ADR-212]] — ArtifactStore DB-only (PR3 — schema validation hook é o precedente direto deste ADR).
- [`docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md`](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) §W2-T01 — task origem.
- Finding DE-003 (revisão multi-agente 2026-05-06).
- CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1" — esta ADR é cumprimento direto da política.
