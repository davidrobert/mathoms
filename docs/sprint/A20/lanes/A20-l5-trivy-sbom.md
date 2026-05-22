---
id: A20.l5
type: lane
title: "Docker dev↔prod parity — L5 Trivy image scan blocking + SBOM CycloneDX"
sprint: A20
status: open
priority: P0
branch_slug: a20-l5-trivy-sbom-blocking
depends_on:
  - "[[A20.l4]]"
parallel_with: []
adrs_canonical:
  - "[[ADR-251]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/ci
  - area/security
---

# A20.L5 — Trivy image scan blocking + SBOM CycloneDX

> **Onda C** em [[MOC-sprint-a20]] — depende rigidamente de [[A20.l4]]
> (precisa de imagem publicada no GHCR para escanear). Complementa
> [[ADR-230]] (filesystem scan já mergeado) com **image scan blocking**.

## Resumo

Job CI `trivy-image-scan` roda sobre imagens publicadas por [[A20.l4]]
(`runtime-<sha>` + `playwright-<sha>`). Severity `HIGH`/`CRITICAL` com
`fixed-version` disponível → `exit 1` (bloqueia merge). SBOM CycloneDX
gerado como artefato CI (`trivy image --format cyclonedx`). Policy
`.trivyignore` versionada com justificativas datadas + revisão mensal.

## Escopo IN

- `.github/workflows/security.yml` ganha job `trivy-image-scan` rodando após
  `release-backend.yml` (`needs: build`).
- Configuração:
  - `severity: HIGH,CRITICAL`
  - `ignore-unfixed: true` (não bloqueia CVE sem fix disponível)
  - `exit-code: 1` em find positivo
  - Matrix sobre os 2 targets (runtime, playwright)
- SBOM CycloneDX gerado em separate step e uploaded como artifact CI.
- `.trivyignore` versionado em `.github/.trivyignore` com formato:
  ```
  CVE-XXXX-YYYY  # libname — justificativa + data revisão + dono
  ```
- Pre-commit hook simples valida formato `.trivyignore` (CVE-* + comentário
  obrigatório).
- Runbook `docs/reference/runbooks/trivy_findings.md`:
  - Como reproduzir scan localmente
  - Como adicionar exceção (`.trivyignore`)
  - Como escalar para `sre-devops` review
  - Política de revisão mensal

## Escopo OUT

- Cosign signing / SLSA L3 — FU.
- Multi-tool scan (Snyk, Grype, Aqua) — Trivy é suficiente para V1.
- Scan de containers de produção em runtime (ECR/GHCR continuous monitoring).

## Pré-requisitos

- [[ADR-251]] mergeada como `Proposto`.
- [[A20.l4]] mergeada (imagens existem em GHCR).
- Trivy CLI ≥0.50.0 (suporta CycloneDX 1.5).

## Critério de aceite

1. PR de teste com `Pillow==9.0.0` (CVE conhecida) é **bloqueado** pelo job
   `trivy-image-scan` com mensagem clara mostrando CVE + fixed-version.
2. PR limpo passa scan em <2min total (ambos os targets).
3. SBOM CycloneDX disponível como artefato no run CI (`gh run download <id>
   --name sbom-cyclonedx`).
4. SBOM contém ≥150 dependências (proxy de transitividade completa).
5. `.trivyignore` com 1 entry sintética (CVE-2024-XXXX `# placeholder` —
   datada 2026-05-22, dono `sre-devops`) é respeitada (não bloqueia).
6. Pre-commit hook bloqueia entry em `.trivyignore` sem comentário/dono/data.

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-251]] promovida `Proposto → Decidido (A20.L5)`.
- [ ] Runbook `trivy_findings.md` em `docs/reference/runbooks/`.
- [ ] `.github/.trivyignore` versionado com política documentada.
- [ ] Primeiro PR de teste injetado e validado.
- [ ] Política de revisão mensal de `.trivyignore` agendada (issue recorrente
      ou calendário).
- [ ] [[ADR-228]] §G3 (operational gates) atualizada com referência a A20.L5.
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Trivy bloqueia merge legítimo (CVE sem fix em base oficial)** —
   mitigação: `ignore-unfixed: true` (não bloqueia o que não tem patch);
   `.trivyignore` documenta exceções com expiração e revisão mensal.
2. **SBOM grande retém storage em GH Actions** — retention 90d default;
   mitigação: ajustar para 30d se quota apertar.
3. **Trivy DB stale** — Trivy puxa DB próprio. Mitigação: cache não estendido
   além de 24h (`TRIVY_CACHE_DIR` com TTL); fail se DB > 7d antigo.

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — review da policy + thresholds + escape hatch
  (`.trivyignore`) + integração com [[ADR-230]] (filesystem scan).

## Detalhe operacional

Track prompt opcional em `docs/agent_prompts/track_a20_<slug>.md` quando a lane for pickedup — segue padrão dos sprints anteriores.
