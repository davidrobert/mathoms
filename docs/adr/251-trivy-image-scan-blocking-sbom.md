---
id: ADR-251
type: adr
title: "Trivy image scan blocking + SBOM CycloneDX — Sprint A20"
status: Proposto
phase: A20.l5
date: "2026-05-22"
relates_to:
  - "[[ADR-228]]"
  - "[[ADR-230]]"
  - "[[ADR-248]]"
  - "[[ADR-249]]"
  - "[[ADR-250]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 251"
  - "Trivy image scan"
  - "SBOM CycloneDX"
tags:
  - type/adr
  - status/proposto
  - area/infra
  - area/ci
  - area/security
  - phase/a20
---

## Contexto

[[ADR-230]] (mergeada em A11.w4-t02) entregou **Trivy filesystem scan**
em `.github/workflows/security.yml` cobrindo dependências Python e Node.
Ainda em `continue-on-error: true` enquanto sem GHAS (GitHub Advanced
Security).

O gap explícito de [[ADR-230]] e do W4-T02 de [PLATFORM_REVIEW](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md): **scan
de imagem Docker publicada**. Sem isso, qualquer CVE em base OS (kernel libs,
glibc, libnss) ou em layer Chromium (Playwright em [[ADR-248]]) passa
despercebido — `trivy fs` não vê o estado final da imagem.

Pré-condição: [[ADR-250]] entrega imagem em GHCR. Sem registry, não há
imagem para escanear.

## Decisão

Job CI `trivy-image-scan` em `security.yml` que roda **após**
`release-backend.yml` publicar imagens em GHCR. Configuração:

- `severity: HIGH,CRITICAL`
- `ignore-unfixed: true` (não bloqueia CVE sem fix disponível)
- `exit-code: 1` em find positivo (gate blocking)
- Matrix sobre os 2 targets ([[ADR-248]]: `runtime`, `playwright`)
- SBOM CycloneDX gerado em step separado (`trivy image --format cyclonedx`)
  uploaded como artifact CI

**Escape hatch:** `.github/.trivyignore` versionado com formato:

```
CVE-XXXX-YYYY  # libname — justificativa + data revisão + dono
```

Pre-commit hook valida formato (CVE-* + comentário obrigatório com data +
dono). Política: revisão **mensal** das exceções; entries sem revisão >30d
geram alerta automático.

Job runtime budget: <2min total para os 2 targets em CI.

## Alternativas consideradas

### Opção A — Continuar só com `trivy fs` (status quo)

**Rejeitada.** Cobertura parcial — não vê base OS, não vê layers binárias.
Combinado com [[ADR-248]] (Chromium em playwright target), CVE em Chromium
passa silencioso.

### Opção B — Snyk Container

**Rejeitada.** Custo $25/dev/mês (Team plan). Boa interface, mas Trivy
cobre as features críticas (CVE database, SBOM, blocking) gratuitamente.

### Opção C — Aqua Security (Trivy commercial)

**Rejeitada.** Trivy open-source é suficiente. Aqua adiciona policy
engine + dashboard, valor incremental baixo para single-host Mathoms.

### Opção D — Grype + Syft (Anchore)

**Rejeitada.** Alternativa válida; Trivy escolhido por (1) integração GH
Actions mais estabelecida, (2) [[ADR-230]] já usa Trivy fs (consistência),
(3) SBOM CycloneDX é nativo.

## Consequências

### Positivas

- **Cobertura completa:** base OS + Python deps + Chromium libs.
- **CVE bloqueia merge** se HIGH/CRITICAL com fix disponível.
- **SBOM CycloneDX** publicado como artifact — auditável, compliance-ready.
- **Política de exceção rastreável** via `.trivyignore` versionado com
  metadados.

### Negativas

- **Falsos positivos / CVE sem fix** podem ofuscar `.trivyignore` —
  mitigado por `ignore-unfixed: true`.
- **Build time +2min** por release (matrix 2 targets).
- **GHCR storage adicional** com SBOM artifact — ~1MB/release, dentro do
  free tier.

## Validação

Critérios em [[A20.l5]] §"Critério de aceite" (6 critérios).

## Migração

Fases em [[A20.l5]] §"Escopo IN":
1. Workflow `trivy-image-scan` mergeado em `security.yml`.
2. PR de prova com CVE injetada (sintética) é bloqueado.
3. Primeiro release pós-A20 gera SBOM.
4. `.trivyignore` (vazio inicialmente) versionado.
5. Política de revisão mensal agendada.

## Riscos

- **Trivy bloqueia merge legítimo** — escape hatch `.trivyignore`.
- **DB Trivy stale** — TTL <24h em cache; fail se >7d antigo.
- **SBOM grande retém storage** — retention 30d.

## Métricas

- % de PRs bloqueados por CVE HIGH+ com fix (target: 100% se aplicável).
- Tempo médio de scan (target <2min).
- Número de entries em `.trivyignore` (target <10, revisado mensal).
- SBOM artifact size por release (~1MB).

## Referências externas

- [Trivy docs](https://aquasecurity.github.io/trivy/)
- [CycloneDX format](https://cyclonedx.org/specification/overview/)
- [GitHub — `aquasecurity/trivy-action`](https://github.com/aquasecurity/trivy-action)
