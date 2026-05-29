---
id: TRACK-a20-l10-python-lockfile
type: track
title: "Track A20.L10 — Python lockfile com hashes (pip-tools vs uv)"
lane: "[[A20.l10]]"
sprint: A20
status: consumed
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/consumed
  - priority/p0
  - area/infra
  - area/python
  - area/devops
---

# Track A20.L10 — Python lockfile com hashes

> **Lane canônica:** [[A20.l10]] (escopo IN/OUT, fases F1-F6, critério de aceite, DoD completos lá).
> · **ADR canônica:** [[ADR-254]] (`Proposto`, já em `main`).
> · **Branch prefix:** `agent/a20-l10-python-lockfile/*`
> · **Onda A** — sem deps cruzadas com L3/L6; **destrava [[A20.l1]]** (Gate A).
> · **Conflito de arquivo:** toca `Dockerfile` + `requirements*` — coordene com [[A20.l2]] (serializar; L10 primeiro).

## Briefing

Sem lockfile com hashes, `pip install` resolve transitivamente — SHA pin de base ([[A20.l2]]) trava só o ponto de partida. Esta lane adota `requirements.in` (human-edited) → `requirements.lock` (com `--hash=sha256:`) para build determinístico bit-a-bit, em **dois** arquivos: raiz (`requirements.txt`, pipeline) e `backend/requirements.txt`.

**Decisão de tooling já materializável em [[ADR-254]]** — recomendação inicial do PM é `pip-tools` (maturidade > velocidade; saída é `requirements.txt`-shaped sem lock-in). `uv` revisitável em A22+ se velocidade CI virar gargalo. Confirme a decisão da ADR antes de gerar lockfile.

## Pré-flight (documentar no PR como comentário inicial)

```bash
git fetch origin && git worktree list   # nenhum agente em a20-l10/a20-l2
ls docs/adr/254-*.md                     # ADR-254 em main
python3 --version                        # 3.12.x
pip install pip-tools                     # ou conforme ADR-254
```

## Execução (resumo — detalhe em [[A20.l10]] §"Plano de execução em fases")

1. **F2** — `requirements.txt` → `requirements.in` (raiz + backend); `pip-compile --generate-hashes` gera os `.lock`. Additive, não muda Dockerfile ainda.
2. **F3** — CI roda `pip install --require-hashes -r requirements.lock` em job paralelo; troca quando estável 3 runs.
3. **F4** — Dockerfile consome `--require-hashes` (coordenado com [[A20.l1]]; ver snippet na lane L1). Flip [[ADR-254]] `Proposto → Decidido (A20.L10)` neste PR.
4. **F5** — runbook `docs/reference/runbooks/python_dependencies.md` + `.github/dependabot.yml` (target `.in`) + hook regen `.lock`.
5. **F6** — sunset refs a `requirements.txt` em README/SETUP.
6. Hook `dev/check_lockfile_sync.py` + registro em `.pre-commit-config.yaml`.

## Especialistas pre-PR

- **`build-vs-buy`** (blocking) — pip-tools vs uv via [[ADR-254]]. Briefing: tabela de decisão em [[A20.l10]] §"Decisão" + perfil Mathoms (CI 6 jobs, dev Mac M-series + Linux, prod Coolify amd64 single-host).
- **`sre-devops`** (após decisão) — integração Dockerfile + Dependabot + CI gating; blast radius de hash mismatch em prod, rollback se lockfile corrompido.

## Definition of Done

Ver [[A20.l10]] §"Definition of Done" (8 itens). Resumo: `.in`+`.lock` (raiz+backend) em `main`; CI hash-only estável; runbook; Dependabot validado; hook `check_lockfile_sync.py` verde; [[ADR-254]] `Decidido`.

## Ligações

- **Lane:** [[A20.l10]] · **ADR:** [[ADR-254]] · **Sprint MOC:** [[MOC-sprint-a20]]
- **Downstream:** [[A20.l1]] (consome o lockfile no Dockerfile) · **Coordenar:** [[A20.l2]] (mesmo Dockerfile).
