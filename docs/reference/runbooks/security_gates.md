# Runbook — Gates de segurança em CI

> Operação dos gates definidos em [[ADR-230]] (Sprint A11 W2-T03).
> Cobre: leitura de relatórios, atualização de allowlist, override
> emergencial, ativação de GitHub secret scanning.

## Workflow `security.yml`

Roda em todo PR contra `main` + schedule sábado 03:00 UTC + manual.

| Job | Bloqueia merge? | Output |
|---|---|---|
| `trivy-fs` | Sim (HIGH/CRITICAL) | SARIF upload em Security tab. |
| `trivy-config` | Sim (HIGH/CRITICAL) | SARIF upload em Security tab. |
| `pip-audit` | Sim (HIGH+, exceto `ignore-vulns` declarados inline) | Workflow logs. |
| `npm-audit-prod` | **Temporariamente não** — `continue-on-error` step-level até PRs de upgrade fixarem `next`, `next-intl`, `postcss` (vulns identificadas no primeiro run pós-merge ADR-230). Volta a bloquear quando todos fixados. | Workflow logs. |
| `npm-audit-dev` | Não (informativo) | Workflow logs. |
| `gitleaks` | Sim (qualquer match não-allowlisted) | Workflow logs. |

Schedule failure abre Issue label `security` (job `open-issue-on-schedule-failure`).

### Diferimentos vigentes (revise periodicamente)

| Vuln | Onde | Tipo | SLO | Issue |
|---|---|---|---|---|
| `PYSEC-2025-185` | `python-jose 3.5.0` (DoS via JWE) | `pip-audit ignore-vulns` inline | HIGH ≤14d | TBD |
| `GHSA-wfc6-r584-vfw7` | `next` cache poisoning | `npm-audit-prod continue-on-error` global | HIGH ≤14d | TBD |
| `GHSA-267c-6grr-h53f`, `GHSA-36qx-fr4f-26g5` | `next` Middleware bypass | idem | HIGH ≤14d | TBD |
| `GHSA-4c35-wcg5-mm9h` | `next-intl` prototype pollution | idem | MEDIUM best-effort | TBD |
| `GHSA-qx2v-qp2m-jg93` | `postcss` XSS via stringify | idem | MEDIUM best-effort | TBD |

**Quando todas as vulns acima forem fixadas via PRs de upgrade:**
1. Remover `continue-on-error: true` do step `npm-audit (prod, HIGH+)` em `.github/workflows/security.yml`.
2. Remover TODO marker `TODO(security-npm-prod-2026-05-20)`.
3. Remover `ignore-vulns: "PYSEC-2025-185"` dos dois steps `pip-audit` (ou substituir se outras vulns acumulararem).
4. Atualizar esta tabela.

## SLO de remediação

| Severity | SLO |
|---|---|
| CRITICAL | ≤ 72h corridas |
| HIGH | ≤ 14 dias corridos |
| MEDIUM/LOW | best-effort |

SLO vencido → abre Issue Linear `security-slo-breach` + PR de remediação aberto (não fechado) referenciando o ignore + ADR-supplementary se mudança estrutural.

## Como triar achado de Trivy

1. Abra Security tab → Code scanning alerts.
2. Filtre por categoria (`trivy-fs` ou `trivy-config`).
3. Para cada alert:
   - CVE em dep direta com patch disponível: abrir PR de upgrade.
   - CVE em dep transitiva sem patch: adicionar entry `.trivyignore` com `expires_at:` 30d futuro + Issue Linear de follow-up.
   - IaC misconfig (Dockerfile, compose): aplicar correção; raramente é false positive.
4. SARIF é frozen — alert só fecha quando próximo scan não detecta mais.

### Formato `.trivyignore`

```
# CVE-YYYY-NNNNN
# Motivo: <justificativa>
# Expires: YYYY-MM-DD (revisar quando vencer)
# Issue: LIN-NNN
CVE-YYYY-NNNNN
```

Não existe `.trivyignore` no repo hoje — criar no PR que precisar do primeiro ignore.

## Como triar achado de pip-audit / npm-audit

1. Workflow logs → linha "Found <N> known vulnerabilities".
2. Cada CVE traz GHSA-ID. Verifique no GitHub Advisory Database.
3. Patch disponível: bump da dep no `requirements.txt` / `package.json` → regen lockfile → PR.
4. Sem patch: ignore via flag específica:

### Ignorar CVE em pip-audit

Adicionar no step do workflow:

```yaml
with:
  inputs: backend/requirements.txt
  ignore-vulns: "GHSA-xxxx-yyyy-zzzz"
```

Em PR separado, com justificativa em comentário + Issue de follow-up.

### Ignorar CVE em npm audit

Não use `npm audit --skip` arbitrário. Use override no `package.json`:

```json
"overrides": {
  "dep-vulneravel": "^1.2.3-fixed"
}
```

Ou aceite explicitamente em PR com justificativa e SLO no comentário.

## Como triar achado de gitleaks

1. Workflow logs mostram path + linha + rule (`api-key`, `private-key`, etc.).
2. **Se é secret real:** trate como incidente.
   - Rotacione o secret imediatamente.
   - Use `git filter-repo` para remover do history (apenas para repos pequenos com poucos colaboradores; coordene com o owner).
   - Force-push apenas com aprovação owner explícita.
3. **Se é false positive:**
   - Adicione entry em `.gitleaks.toml` (path/regex/commit) com `description = "..."` claro.
   - PR + reviewer humano em PRs que tocam `.gitleaks.toml` (CODEOWNERS opcional).

### Atualizar `.gitleaks.toml`

Tipos de allowlist (ver arquivo):

- `paths = ["..."]` — globs de paths a ignorar.
- `regexes = ["..."]` — padrões dentro do conteúdo (CPF sintético, dev keys documentadas).
- `commits = ["sha"]` — SHAs históricos com matches conhecidos.

**Nunca** allow generalizado em `^backend/` ou `^pipeline/` — código de produção que vaza secret é incidente, não false positive.

### Baseline inicial

Após merge desta ADR, gerar baseline:

```bash
gitleaks detect --report-path .gitleaks-baseline.json
```

Revisar manualmente. SHAs com matches **legítimos** (key documentada já no histórico, fixture antiga) vão em `[[allowlists]] commits=[...]`. SHAs com secret **real** disparam incidente.

## Como triar Issue de schedule

Issues label `security` criadas por `open-issue-on-schedule-failure`:

1. Abra a run linkada (URL em `Run: ...`).
2. Identifique job que falhou.
3. Aplique triagem específica acima (Trivy / pip-audit / etc.).
4. Cole resumo no Issue + linke PR de remediação.
5. Feche Issue quando PR mergeado + próximo schedule passar verde.

## Override emergencial (CTO call)

Quando bypass é a única opção (release crítica, exploit já público, gate falso-positivo em rotina):

1. Commit assinado (`git commit -S`) com mensagem explicando bypass.
2. Issue Linear `security-slo-breach` criada **antes** do merge.
3. SLA 24h para fix real (PR aberto, não fechado).
4. Pre-commit override: `git commit --no-verify` aceitável **só** em emergência declarada via Issue.
5. CI override: aprovação owner explícita em PR + admin merge via Ruleset bypass (auditado).

Documentar override em pós-mortem na Issue.

## GitHub Secret Scanning

Habilitar 1x via API (não declarativo no repo):

```bash
gh api -X PUT repos/davidrobert/mathoms/secret-scanning \
  --field enabled=true
```

Verificar estado:

```bash
gh api repos/davidrobert/mathoms/secret-scanning
```

### Push protection (condicional)

Push protection bloqueia push de secret antes de chegar ao remoto. **Exige GitHub Advanced Security** em repos privados (licença paga) OU repo público.

Mathoms é privado sem GHAS hoje — push protection NÃO está habilitado. Estado entregue: "secret-scanning alerts only".

Se/quando GHAS for licenciado:

```bash
gh api -X PUT repos/davidrobert/mathoms/secret-scanning-push-protection \
  --field enabled=true
```

Atualize esta seção e abra PR `chore(security): habilita push protection`.

## Rotação de tokens em CI

Hoje os jobs usam apenas `GITHUB_TOKEN` (provisionado por Actions, expira ao fim do run). Não há tokens persistidos de terceiros.

Se futuramente Snyk / Aikido / outro SaaS for adotado:

1. Token vai em GitHub Secrets (`gh secret set SNYK_TOKEN`).
2. Rotação anual via SOP — Issue label `chore-rotation` em janeiro.
3. Documentar SOP nesta seção.

## Referências

- [[ADR-230]] — decisão canônica.
- [[ADR-228]] — pattern de "failure mode é normal e esperado" para gates operacionais.
- [`docs/plan/PLATFORM_REVIEW/_README.md`](../../plan/PLATFORM_REVIEW/_README.md) §W2-T03 — task origem.
- [`.github/workflows/security.yml`](../../../.github/workflows/security.yml) — workflow.
- [`.gitleaks.toml`](../../../.gitleaks.toml) — allowlist.
- [`.pre-commit-config.yaml`](../../../.pre-commit-config.yaml) — hook gitleaks local.
