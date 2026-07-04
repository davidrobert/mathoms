# Runbook — Disaster Recovery (Postgres + Fernet vault)

> **ADRs:** [[ADR-174]] (off-site backup R2 + restore drill) · [[ADR-228]] G1
> (restore drill real, gate de go-live) · [[ADR-212]] (rollback de deploy —
> caminho distinto, ver abaixo).
> **Plano:** [[PLAN-launch-trust]] F2 wave 2.1 (KR4) · lane A21.l9.
> **Owner:** SRE on-call.
> **SLOs:** RPO ≤ 24h · **RTO de DR ≤ 4h**.
> **Drill de mecanismo (CI):** `dev/restore_drill.py` via job
> `backup-restore-drill` em `.github/workflows/nightly.yml`.
> **Drill real (R2 → prod-like):** ☐ gate G1 de [[ADR-228]], pós-cutover.

---

## DR ≠ rollback de deploy — não confundir os dois RTOs

| Cenário | O que aconteceu | Caminho | RTO | ADR |
|---|---|---|---|---|
| **Rollback de deploy** | Deploy de código ruim; dado íntegro | revert PR + downgrade de migration | **≤ 30min** | [[ADR-212]] |
| **Disaster recovery** | Perda de host/FS, corrupção, ransomware | pull backup off-site (R2) + `pg_restore` + smoke | **≤ 4h** | [[ADR-174]] |

Este runbook cobre **só DR** (perda de dado). Para reverter um deploy ruim
com o dado intacto, use [pipeline_rollback.md](pipeline_rollback.md).

---

## Por que este runbook existe

Hoje o Postgres roda single-host (Hetzner CX32, [[ADR-058]]). Falha
catastrófica de DC, corrupção de filesystem ou ransomware encriptando o
disco = **perda total** se não houver backup off-site restaurável. LGPD
exige plano de DR documentado e testado para tratamento de dado pessoal.

O risco silencioso não é o backup falhar — é o backup **existir e não
restaurar**: schema drift (migration não aplicada no destino), ou — pior —
ciphertext Fernet que não descriptografa porque a `MATHOMS_FERNET_KEY`
mudou ou se perdeu. Backup que restaura linhas mas não decifra o vault é
perda total disfarçada de sucesso.

---

## 1. Custódia da chave Fernet (pré-requisito absoluto)

`MATHOMS_FERNET_KEY` cifra todo dado sensível em repouso ([[ADR-231]],
`backend/app/services/vault.py`). **Sem ela, o backup é lixo cifrado.**

- A chave vive **fora do host** de produção — 1Password vault Mathoms,
  nunca no mesmo disco que o backup.
- Backup do Postgres e custódia da chave são **dois cofres separados**.
  Quem rouba o disco do servidor não tem a chave; quem rouba o backup R2
  não tem a chave.
- Rotação de chave usa `MultiFernet` ([[ADR-171]]) — DR após rotação exige
  a chave **vigente no momento do `pg_dump`**, não a mais recente. Registre
  qual key-id cifrou cada backup.

---

## 2. RPO/RTO declarados

- **RPO ≤ 24h** — backup daily (cron 03:00 UTC, [[ADR-174]]). Perda máxima
  aceita = 1 dia de transações.
- **RTO de DR ≤ 4h** — pull de R2 + `pg_restore` + smoke + religar app.

Backup off-site real (`dev/backup_postgres.sh` → R2; nome indicativo —
o script ainda não existe, confirmar ao materializar, [[ADR-228]] G2) e replicação do
BlobStore são **diferidos** ([[ADR-228]] G2): exigem billing R2 + prod
pública. O que existe hoje é a **prova do mecanismo de restore** em CI.

---

## 3. Drill de mecanismo (CI — automatizado)

`dev/restore_drill.py` roda em `nightly.yml` (job `backup-restore-drill`,
cron seg/qua/sex 06:00 UTC + `workflow_dispatch` + label `backup-drill`).
Prova, com dado sintético zero-PII, que o **ciclo dump→restore preserva
tudo**:

1. `alembic upgrade head` num Postgres limpo.
2. Seed sintético (`dev/drill_seed.py`) — CPF inválido, timestamps fixos,
   1 segredo cifrado via Fernet.
3. **Manifesto pré** — row-count + `sha256` de conteúdo por tabela-chave
   (`workspaces`, `workspace_members`, `pipeline_artifacts`).
4. `pg_dump -Fc` → `createdb` de um DB **separado** → `pg_restore
   --exit-on-error`.
5. **Manifesto pós** + asserts:
   - row-count e `sha256` idênticos (sem perda/corrupção);
   - `alembic_version` == head (sem drift de schema);
   - `vault.decrypt(ciphertext)` devolve o plaintext original
     (**round-trip Fernet** — o teste que separa "restaurou" de
     "restaurou e é usável");
   - tempo de restore < 60s (sanity de mecanismo, **não** o RTO de prod).

Falha do job → issue automática (label `ops`). O drill prova o mecanismo;
**não** substitui G1 (drill real contra snapshot R2, [[ADR-228]]).

```bash
# Reproduzir local (precisa de Postgres + MATHOMS_FERNET_KEY no env):
python3 dev/drill_seed.py --dsn "$DATABASE_URL"
python3 dev/restore_drill.py --source-dsn "$DATABASE_URL" --restore-db fin_restore
```

---

## 4. Procedimento de DR real (manual, RTO ≤ 4h)

Quando o host de produção é perdido:

1. **Provisionar host novo** (Hetzner ou alternativa) + Postgres 16.
2. **Recuperar a chave Fernet** do 1Password — confirmar o key-id que
   cifrou o backup-alvo.
3. **Pull do último backup** de R2 (`aws s3 cp s3://mathoms-backups-eu/...`)
   + decrypt GPG.
4. `createdb` + `pg_restore --exit-on-error` do dump.
5. **`alembic upgrade head`** se o backup for de schema anterior ao código
   em deploy.
6. **Smoke / queries-canário** (5, conforme [[ADR-174]]):
   - `SELECT count(*) FROM workspaces;` bate com o esperado;
   - `SELECT max(created_at) FROM pipeline_runs;` ≤ 24h do incidente;
   - **round-trip Fernet** num segredo conhecido (decrypt devolve plaintext);
   - `SELECT count(*) FROM workspace_members;` consistente;
   - login de smoke (auth funciona com hash restaurado).
7. **Religar app** apontando para o DB restaurado; validar `/health` 200.
8. **Registrar** tempo medido (RTO real), key-id usado e resultado das
   canário neste runbook (seção de histórico) + postmortem se houve perda.

---

## 5. Itens diferidos (rastreados em ADR-228 G2 — gate de go-live)

- Backup real agendado `pg_dump` → R2 (precisa de billing R2 + cron em prod).
- Backup off-site do `mathoms_storage`/BlobStore (uploads).
- Restore drill **real** contra snapshot R2 em ambiente prod-like (G1).
- Medição de RTO/RPO em incidente sintético real (não só sanity de CI).

Até o cutover `dev.mathoms.ai` → `app.mathoms.ai`, esses itens permanecem
`Proposto`. O drill de mecanismo em CI cobre a regressão silenciosa do
caminho de restore enquanto o drill real não roda.

---

## Histórico de drills reais

| Data | Tipo | RTO medido | Resultado | Postmortem |
|---|---|---|---|---|
| _(nenhum ainda — G1 pendente pós-cutover)_ | | | | |
