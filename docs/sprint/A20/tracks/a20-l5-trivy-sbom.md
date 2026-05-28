---
id: TRACK-a20-l5-trivy-sbom
type: track
title: "Track A20.L5 — Trivy image scan blocking + SBOM CycloneDX"
lane: "[[A20.l5]]"
sprint: A20
status: ready
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/ci
  - area/security
---

# Track A20.L5 — Trivy image scan blocking + SBOM CycloneDX

> **Lane canônica:** [[A20.l5]] (config Trivy, formato `.trivyignore`, runbook, critério de aceite).
> · **ADR canônica:** [[ADR-251]] (`Proposto`). Complementa [[ADR-230]] (filesystem scan já mergeado).
> · **Branch prefix:** `agent/a20-l5-trivy-sbom-blocking/*`
> · **Onda C** — **depende rigidamente de [[A20.l4]]** (precisa de imagem publicada no GHCR p/ escanear).
>
> ⚠️ **BLOQUEADA INDIRETAMENTE POR CONFIRMAÇÃO EXTERNA** — depende de [[A20.l4]] (GHCR), que requer confirmação do owner. Não executável até L4 publicar imagem.

## Briefing

Job `trivy-image-scan` em `security.yml` (`needs: build` de [[A20.l4]]) escaneia `runtime-<sha>` + `playwright-<sha>`. `HIGH`/`CRITICAL` com `fixed-version` → `exit 1` (bloqueia merge); `ignore-unfixed: true`. SBOM CycloneDX como artefato CI. `.trivyignore` versionado em `.github/.trivyignore` com `CVE-XXXX # libname — justificativa + data + dono`, revisão mensal.

## Pré-flight (documentar no PR)

```bash
git fetch origin && git worktree list
ls docs/adr/251-*.md
git log origin/main --oneline | grep -i a20-l4   # L4 mergeada (imagens existem)
trivy --version                                   # >=0.50.0 (CycloneDX 1.5)
```

## Execução (resumo — detalhe em [[A20.l5]])

1. `security.yml` ganha job `trivy-image-scan` (matrix 2 targets, severity HIGH/CRITICAL, ignore-unfixed, exit-code 1).
2. Step SBOM CycloneDX → upload artifact.
3. `.github/.trivyignore` + pre-commit hook validando formato (CVE + comentário/dono/data obrigatórios).
4. Runbook `docs/reference/runbooks/trivy_findings.md`.
5. PR de teste com CVE conhecida (ex.: `Pillow==9.0.0`) deve ser **bloqueado**.
6. Atualizar [[ADR-228]] §G3.

## Especialista pre-PR

- **`sre-devops`** (obrigatório) — policy, thresholds, escape hatch `.trivyignore`, integração com [[ADR-230]].

## Definition of Done

Ver [[A20.l5]] §"Definition of Done". Resumo: PR em `main` CI verde; [[ADR-251]] `Decidido`; runbook `trivy_findings.md`; `.trivyignore` versionado; PR de teste validado; revisão mensal agendada; [[ADR-228]] §G3.

## Ligações

- **Lane:** [[A20.l5]] · **ADR:** [[ADR-251]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Upstream:** [[A20.l4]] (imagens GHCR) · **Relacionada:** [[ADR-230]] (fs scan) · **Downstream:** [[A20.l9]] (smoke usa imagens escaneadas).
