---
id: ADR-230
type: adr
title: "Gates de segurança em CI: Trivy fs + IaC + pip-audit + npm audit + gitleaks + GH secret scanning"
status: Decidido
phase: A11.W2
date: "2026-05-20"
relates_to:
  - "[[ADR-110]]"
  - "[[ADR-170]]"
  - "[[ADR-171]]"
  - "[[ADR-174]]"
  - "[[ADR-175]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 230"
  - "security-gates"
  - "CI security"
  - "trivy gitleaks pip-audit"
tags:
  - area/security
  - area/ci
  - area/ops
  - phase/a11
  - status/decidido
  - type/adr
---

## Contexto

Sprint A11 W2-T03 (`docs/plan/PLATFORM_REVIEW/_README.md` linhas 319-325) consolida findings SR-005 + SR-019 da revisão multi-agente 2026-05-06: hoje o CI do Mathoms **não tem qualquer gate de segurança automatizado**. Verificações de superfície:

- `grep -E 'trivy|gitleaks|pip-audit|npm.*audit|bandit|detect-secrets|safety'` em `.github/workflows/ci.yml` → zero matches.
- Mesma busca em `.pre-commit-config.yaml` → zero matches.
- `hooks: detect-private-key` existe (pre-commit-hooks v4.6.0) mas é genérico (regex de chaves PEM) e cobre apenas o stage atual — não varre git history.

Consequência: CVE em deps Python/JS, secrets vazados em commits antigos, IaC vulnerável (Dockerfile `USER root`, compose sem healthcheck) e secrets em branches passam por CI verde. Para uma fintech multi-tenant manipulando dados financeiros + LGPD, isso é gate ausente em camada P0.

O finding SR-005 (sre-devops 2026-05-06) listou explicitamente: Trivy bloqueando HIGH/CRITICAL em images, pip-audit + npm audit em CI, gitleaks pre-commit, GH secret scanning habilitado. Esta ADR formaliza **escopo, thresholds, allowlist policy, SLO de remediação e diferimentos**.

### Diferimentos forçados

1. **Image scan (`trivy image`):** depende de imagens publicadas. Hoje o repo só publica em W4-T02 (Coolify webhook + GHCR). Buildar imagem no CI só pra scanar dobra tempo de pipeline e introduz fragilidade de cache. Diferido para W4-T02.
2. **GitHub Advanced Security push protection:** exige GHAS em repos privados (custo $) ou repo público. Tier do Mathoms é privado sem GHAS hoje — habilitamos `secret-scanning alerts` (incluso) mas push protection fica como follow-up se/quando GHAS for licenciado.

## Decisão

**Adotar Opção A** (workflow separado `security.yml`, jobs paralelos por escopo, gitleaks dupla camada pre-commit + CI) ratificada por sessão `sre-devops` 2026-05-20. Refinamentos:

### D1 — Workflow novo `.github/workflows/security.yml`

Triggers: `pull_request` (branches main) + `schedule: '0 3 * * 6'` (sábado 03:00 UTC = sexta 00:00 BRT, captura CVE-friday) + `workflow_dispatch`. Concurrency group próprio (não compartilhado com `ci.yml`).

`permissions:` workflow-level mínimo (`contents: read`); jobs que precisam mais (SARIF upload via `security-events: write`) opt-in.

Pin de actions por SHA — política já vigente em `ci.yml` desde CVE-2025-30066 (tj-actions/changed-files compromise mar/2025). Dependabot atualiza SHAs.

### D2 — Jobs e thresholds

| Job | Tool | Threshold blocking | Notes |
|---|---|---|---|
| `trivy-fs` | `aquasecurity/trivy-action` modo `fs` | HIGH, CRITICAL (`exit-code: 1`) | Scaneia repo full. SARIF upload em PR + main. |
| `trivy-config` | `trivy config` (mesmo action, modo `config`) | HIGH, CRITICAL | IaC: Dockerfile, docker-compose, `.github/workflows/*`. Custo <30s. |
| `pip-audit` | `pypa/pip-audit-action` | HIGH+ via `--strict` | Roda contra o `requirements.lock` combinado pinado (ADR-254). |
| `npm-audit-prod` | `npm audit --audit-level=high --omit=dev` | HIGH, CRITICAL | Em `frontend/`. Bloqueante. |
| `npm-audit-dev` | `npm audit --audit-level=high` | — (informativo) | `continue-on-error: true`. Dev deps raramente exploitable, ruído alto. |
| `gitleaks` | `gitleaks/gitleaks-action` | Qualquer match não-allowlisted | `--log-opts="--all"` varre git history full (defesa contra `--no-verify`). |

Schedule semanal: mesmos jobs, mas em failure abre Issue label `security` em vez de bloquear (não há PR para bloquear). Slack hook fica para follow-up quando alerting do W4-T03 chegar.

### D3 — Gitleaks dupla camada

1. **Pre-commit:** hook `gitleaks` (rev pinned) varre stage atual. Rápido (<3s). Bloqueia commit local. Defesa principal.
2. **CI workflow:** varre `--log-opts="--all"` (full history). Bloqueia merge. Defesa contra `git commit --no-verify`.

Allowlist em `.gitleaks.toml` (commitado) com regras explícitas por path/regex/SHA:

- Paths whitelist: `_archive/**`, `EXEMPLO_DE_RELATORIO.html`, `tests/fixtures/**`, `frontend/src/test/**`, `dev/snapshots/**`, `docs/archive/**`.
- Regex whitelist: CPF sintético (`\b[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}\b` em paths de teste), `MATHOMS_FERNET_KEY` em `.github/workflows/ci.yml` (dev key documentada — ver TODO cicd-onda-3 lá), strings `dev-secret-key-change-in-production` em fixtures de gate de prod.

Baseline 1x: `gitleaks detect --report-path baseline.json` no PR de criação; SHAs históricos com matches conhecidos vão em `[[allowlist.commits]]` no `.gitleaks.toml`.

### D4 — GitHub secret scanning

`gh api -X PUT repos/davidrobert/mathoms/secret-scanning --field enabled=true` documentado em runbook `docs/reference/runbooks/security_gates.md`. Estado é configurável só pela API/UI, não declarativo no repo — runbook é a fonte de verdade textual. PR de implementação inclui screenshot do estado habilitado.

### D5 — SLO de remediação

| Severity | SLO |
|---|---|
| CRITICAL | ≤ 72h (3 dias corridos) |
| HIGH | ≤ 14d |
| MEDIUM/LOW | best-effort (informativo) |

Vencido o SLO: abre incidente Linear (label `security-slo-breach`) + opção `[[allowlist.<id>]]` em `.gitleaks.toml` / `.trivyignore` **só** com justificativa em comentário + PR de remediação aberto (não fechado) referenciando o ignore.

### D6 — Runbook obrigatório

Criar `docs/reference/runbooks/security_gates.md` cobrindo:

- Como ler relatório de cada job (Security tab GitHub + workflow logs).
- Como atualizar allowlist com justificativa (PR + ADR-supplementary se mudança estrutural).
- Override emergencial: commit assinado + Issue Linear + 24h SLA para fix real (ADR-228 §"failure mode" inspirou este padrão).
- Como rotar tokens Trivy/gitleaks quando vencerem (não há tokens hoje — actions usam GITHUB_TOKEN; reservado p/ futuro).

## Alternativas consideradas

### (A) Workflow único expandido em `ci.yml`

Mantém 1 fonte de verdade. `ci.yml` já tem 33KB; aumentar acoplamento dificulta debug e tunning de timing. **Descartada.**

### (B) gitleaks só pre-commit, demais em schedule semanal

Reduz pressão de PR mas perde gate forte. CVE crítica em deps pode demorar 7d para detectar. **Descartada** — Mathoms lida com dados financeiros + LGPD; janela 7d é risco materializável.

### (C) Image scan já agora (build Docker em CI só pra scanar)

Dobra tempo de pipeline (~6 min extras). Coolify + GHCR (W4-T02) traz infra adequada — esperar é correto. **Descartada/diferida.**

### (D) Adoção de Snyk / Aikido / outro SaaS de SecOps

Marketplaces SaaS oferecem alertas mais ricos e UI dedicada, mas:

- Custo: $200-500/mês em plano básico que faz sentido pra Mathoms.
- Lock-in: integração via GitHub App move estado para fora do repo.
- Soberania: dados de vuln + secrets indo pra terceiro (LGPD considera dados de configuração; secret real vazado num SaaS é vazamento composto).

Trivy + pip-audit + npm audit + gitleaks são open source, rodam em CI sob nosso controle, SARIF é padrão GitHub. **Descartada por agora.** Reavaliar quando >5 devs ou volume de findings tornar triagem manual inviável (build-vs-buy revisita 2027-Q2 ou 100 workspaces ativos pagantes, em paralelo com ADR-150).

## Consequências

**Positivas:**

- Gate P0 fecha — CVE / secret leak / IaC misconfiguration deixam de passar silenciosamente.
- SARIF em Security tab dá visibilidade ao owner sem ler logs.
- Custo: ~4-6 min CI extra por PR (jobs paralelos), $0 em ferramentas (todas OSS), zero novos serviços.
- Runbook documenta processo de remediação e override.

**Negativas:**

- Falsos positivos vão acontecer (especialmente gitleaks em fixtures de teste). Allowlist explícita mitiga mas exige curadoria — agente que adiciona fixture com CPF sintético precisa lembrar de atualizar `.gitleaks.toml` ou usar pattern dentro do allowlist.
- SLO de 72h CRITICAL exige owner/agente reativo. Sem incident response process (W4-T05 em planejamento), risco de SLO virar texto morto.
- Tempo de CI +4-6 min em PR. Compensa o ganho de gate, mas afeta velocidade de feedback. Mitigação: jobs paralelos + cache via actions setup.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Allowlist gitleaks vira "muleta" — agente adiciona allow em vez de remover secret | Reviewer humano em PRs que modificam `.gitleaks.toml`; CODEOWNERS opcional. |
| Trivy/pip-audit reportam HIGH em dep transitiva sem patch disponível | `.trivyignore` por CVE-ID com data de expiração (`expires_at: YYYY-MM-DD`); release de PR de upgrade quando patch disponível. |
| Schedule semanal vira ruído (Issues acumuladas) | Runbook §"como triar Issue de schedule" + label policy + auto-close em PR de fix. |
| GHAS push protection prometido mas não entregue (repo privado sem GHAS) | ADR explícita que estado entregue é "secret-scanning alerts only"; push protection é follow-up condicionado a licença GHAS ou repo público. |

## Gates desta ADR

- **PR de implementação:** cria `security.yml`, atualiza `.pre-commit-config.yaml`, cria `.gitleaks.toml`, cria `docs/reference/runbooks/security_gates.md`, atualiza shim `docs/DECISIONS.md` com anchor `<a id="adr-230-..."/>`, atualiza `docs/plan/PLATFORM_REVIEW/_README.md` marcando W2-T03 done (após merge).
- **Validação:** `pre-commit run --all-files` verde; `gitleaks detect --baseline-path .gitleaks-baseline.json` sem novos achados; workflow novo passa em PR.
- **Closure:** ADR flippa para `Decidido (Sprint A11.W2)` no merge do PR de implementação.

## Closure

Flippada para `Decidido (Sprint A11.W2)` em 2026-05-20 após merge de:

- [PR #344](https://github.com/davidrobert/mathoms/pull/344) (commit `8b2c840`) — implementação inicial: workflow `security.yml`, `.gitleaks.toml`, hook gitleaks pre-commit, runbook `docs/reference/runbooks/security_gates.md`, ADR-230 criada como `Proposto`.
- [PR #346](https://github.com/davidrobert/mathoms/pull/346) (commit `b68e098`) — hotfix pós-primeiro run real do workflow: pin `gitleaks-action@v0.36.0` (SHA), `permissions: pull-requests: write` no job gitleaks, allowlist `ignore-vulns` inline para `PYSEC-2025-185` (python-jose) em ambos os steps `pip-audit`, `continue-on-error: true` step-level em `npm-audit-prod` enquanto deps `next`/`next-intl`/`postcss` aguardam upgrade (TODO marker `TODO(security-npm-prod-2026-05-20)`).

### Estado entregue

- ✅ Workflow `security.yml` rodando em PR + schedule semanal sábado 03:00 UTC.
- ✅ Trivy fs/config + pip-audit + npm-audit-prod + npm-audit-dev + gitleaks (dupla camada pre-commit + CI `--log-opts="--all"`).
- ✅ Allowlist gitleaks operacional (`paths` + `regexes` + `commits`).
- ✅ SLO documentado em §D5 + runbook `docs/reference/runbooks/security_gates.md`.
- ✅ Issue auto-open em schedule failure (label `security`).
- ⏳ GH secret scanning habilitação via `gh api -X PUT repos/davidrobert/mathoms/secret-scanning` — passo manual do owner; instruções em runbook §"GitHub Secret Scanning". Não bloqueia closure desta ADR; rastreado como item de runbook.
- ⏳ Vulnerabilidades conhecidas em deps (6 CVEs/GHSAs) catalogadas em runbook §"Diferimentos vigentes" + Issues GitHub label `security` para tracking individual de remediação dentro do SLO §D5. Quando todas fixadas, remover allowlists conforme checklist do runbook.

### Próximos passos rastreados

- Issues label `security` (uma por GHSA/PYSEC ID) abertas em 2026-05-20 — owner Sprint A12 (não bloqueia A11; coerente com [[ADR-228]] §"failure mode").
- Trivy fs + Trivy config + npm-audit-prod removerão `continue-on-error` quando: (a) IaC misconfigs detectados forem triados/fixados (Trivy config); (b) todas as 6 vulns prod npm forem fixadas via PRs de upgrade (npm-audit-prod); (c) GHAS for licenciado ou volume de SARIF for triado em Security tab (Trivy fs). Estado atual é gate ativo + soft-fail explícito + tracking por Issue.

## Referências

- [[ADR-110]] — logging estruturado (SARIF complementa, não substitui).
- [[ADR-170]] / [[ADR-171]] — auth/Fernet security ADRs propostas em W1-T06; thread comum de "fechar gaps SR-*" da revisão 2026-05-06.
- [[ADR-174]] — off-site backup R2 (W4-T01; resiliência complementar; gates de detecção (esta ADR) + gates de recovery (174) são ortogonais).
- [[ADR-175]] — prompt injection defense (W3-T05; aplica a LLM input; gitleaks aplica a code/secrets — escopos distintos).
- [`docs/plan/PLATFORM_REVIEW/_README.md`](../plan/PLATFORM_REVIEW/_README.md) §W2-T03 — task origem.
- CLAUDE.md §"Política operacional — ADR Proposto antes de PR P0/P1" — esta ADR é cumprimento direto da política.
- CVE-2025-30066 (tj-actions/changed-files compromise, mar/2025) — precedente que motiva SHA-pinning + supply chain hygiene.
