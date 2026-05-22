---
id: A20.l7
type: lane
title: "Docker dev↔prod parity — L7 Makefile targets + SETUP.md revisado"
sprint: A20
status: open
priority: P1
branch_slug: a20-l7-makefile-onboarding
depends_on:
  - "[[A20.l6]]"
parallel_with:
  - "[[A20.l1]]"
  - "[[A20.l4]]"
  - "[[A20.l8]]"
adrs_canonical:
  - "[[ADR-252]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p1
  - area/dx
  - area/docs
---

# A20.L7 — Makefile targets + SETUP.md revisado

> **Onda B** em [[MOC-sprint-a20]] — depende de [[A20.l6]] (compose dev existir).
> Foco em DX (developer experience): `make dev-up-docker` é o north star do
> sprint.

## Resumo

Adiciona targets ao `Makefile` para onboarding via Docker:

- `make dev-up-docker` — sobe stack completa (depende de [[A20.l6]])
- `make dev-down` — para tudo, preserva volumes
- `make dev-reset` — para tudo + apaga volumes (`docker-compose down -v`)
- `make dev-shell` — shell drop no container `api`
- `make dev-rebuild` — rebuild imagem após mudança em deps
- `make dev-logs` — `docker-compose logs -f` em todos os services

Revisa [SETUP](../../../reference/SETUP.md) posicionando Docker como caminho recomendado;
uvicorn local mantido como fallback documentado. Mede TTFR baseline ANTES do
PR + TTFR final no PR como evidência.

## Escopo IN

- 6 targets novos no `Makefile` (com `make help` listando todos com descrição).
- `make help` melhorado (separação em sections: Dev / CI / Deploy / Docs).
- [SETUP](../../../reference/SETUP.md) reescrita: seção "Onboarding em <5min" no topo, passos
  para Docker, depois seção "Caminho legado (uvicorn local)".
- README do repo atualizado: badge `[Docker | uvicorn]` + link para SETUP.
- TTFR medido por 1 dev real em clone fresh (PM ou CEO) e registrado no PR
  inicial como comentário; medido novamente após PR mergeado.

## Escopo OUT

- Deprecar uvicorn local — non-goal A20.
- Targets para deploy (`make deploy-staging`, `make deploy-prod`) — débito
  separado (relacionado a [[A20.l4]]).
- Substituir Makefile por just/task — bikeshed não-prioritário.

## Pré-requisitos

- [[A20.l6]] mergeada (compose dev existe).
- [[ADR-252]] mergeada (cobre Makefile + compose dev).

## Critério de aceite

1. `make help` lista todos os 6 targets dev com 1 linha de descrição.
2. `time make dev-up-docker` em clone fresh + `curl --fail
   localhost:8000/health` em **<120s wall-clock** (medido em 3 execuções,
   p95 reportado).
3. `make dev-shell` drop em container `api` em <3s, mostra prompt
   `mathoms@<container-id>:/app$`.
4. `make dev-rebuild` em diff de deps regenera imagem em <60s warm.
5. [SETUP](../../../reference/SETUP.md) seção "Onboarding em <5min" tem comando único pra começar.
6. Testado em macOS + Linux por 1 dev real, registrado no PR.

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] [[ADR-252]] referencia esta lane (sub-decisão de Makefile + SETUP).
- [ ] [SETUP](../../../reference/SETUP.md) atualizada com Docker como caminho recomendado.
- [ ] README atualizado com badge + link.
- [ ] TTFR baseline e final registrados no PR (comentários inicial + final).
- [ ] [CHANGELOG](../../../CHANGELOG.md) entry registrada.

## Riscos top 3

1. **Makefile incompatível em Windows** — Mathoms target é macOS + Linux; WSL2
   funciona como Linux. Mitigação: documentar requisito macOS/Linux no SETUP;
   Windows nativo é non-goal.
2. **TTFR varia por hardware** — primeira medição em macOS Air M2; pode não
   refletir Linux server. Mitigação: medir em 2 ambientes (macOS Air + Linux
   x86_64) e reportar ambos.
3. **`make dev-up-docker` falha em rede ruim** — `docker pull` pode demorar.
   Mitigação: target `make dev-pull` separado para pre-fetch; documentar.

## Especialistas pre-PR

- **`product-designer`** (consultivo) — review da DX do `SETUP.md` (clareza
  para novo dev — narrativa, exemplos, anti-patterns).
- **`sre-devops`** (consultivo) — review dos targets (robustez, sem
  side-effects destrutivos sem confirmação).
