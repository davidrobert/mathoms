---
id: TRACK-a20-fu-chromium-headless-shell
type: track
title: "Track A20.FU — Slim playwright target via chromium-headless-shell"
lane: "[[A20.l1]]"
sprint: A20
status: ready
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/ready
  - priority/p2
  - area/infra
  - area/docker
  - area/devops
---

# Track A20.FU — Slim `playwright` target via `chromium-headless-shell`

> **Follow-up de [[A20.l1]]** (não bloqueia nada). Origem: durante a entrega de
> L1 ([[ADR-248]]), o target `playwright` mediu ~2.72GB arm64 — ~956MB são o
> browser Chromium full. O `chromium-headless-shell` (~110MB) é uma alavanca de
> slimming de ~840MB, mas **muda o comportamento de render** — por isso saiu do
> escopo de L1.
> · **Branch prefix:** `agent/a20-fu-headless-shell/*`
> · **Prioridade:** P2 (FinOps/DX, não bloqueia produção).

## Por que não foi feito em L1

[`backend/app/services/pdf_renderer.py`](../../../../backend/app/services/pdf_renderer.py)
usa `p.chromium.launch(headless=True)` — o Chromium **full** em modo headless.
Trocar para o shell exige `p.chromium.launch(channel="chromium-headless-shell")`
**e** `python -m playwright install chromium-headless-shell` no Dockerfile.
Isso é uma mudança de engine de render: precisa de validação de paridade
visual do PDF (tabelas, gráficos, ícones, fontes) antes de adotar — não é
um refactor mecânico de infra.

## Escopo

1. **Dockerfile** (stage `playwright`): trocar `python -m playwright install
   chromium` por `python -m playwright install chromium-headless-shell`
   (ou instalar ambos se houver caso que ainda precise do full — medir).
2. **`pdf_renderer.py`**: `launch(channel="chromium-headless-shell", headless=True)`.
   Confirmar que o launch arg é compatível com a versão de Playwright pinada
   em `requirements.lock`.
3. **Audit/runbook**: atualizar `dev/audit_backend_image.sh` e
   [`docs/reference/runbooks/docker_images.md`](../../../reference/runbooks/docker_images.md)
   §6 (a alavanca de slimming vira "feito") se adotado.

## Gate de aceite (obrigatório — é mudança de render)

- **Paridade visual do PDF**: renderizar 3 relatórios sintéticos completos
  (tabelas + gráficos + `MonetaryValue` + ícones + fontes Plus Jakarta/Inter/
  JetBrains Mono) com full vs headless-shell e comparar pixel-diff. Tolerância
  a definir com `product-designer` — fonts e antialiasing são os suspeitos.
- **Smoke**: `/reports/{id}/pdf` retorna `application/pdf` >50KB sem stack trace.
- **Medição**: documentar o tamanho do target `playwright` antes/depois.

## Especialistas pre-PR

- **`product-designer`** (obrigatório) — validar paridade visual do PDF
  (o render é o produto; regressão de fonte/layout é inaceitável).
- **`sre-devops`** (consultivo) — confirmar que o slimming não quebra os
  invariantes do dual-target ([[ADR-248]]).

## Risco

- `chromium-headless-shell` é um binário diferente; bugs de render headless
  específicos do shell (já reportados upstream em casos de `print-to-pdf`
  complexos) podem só aparecer em relatório real, não em smoke trivial. Por
  isso o gate de paridade visual é obrigatório, não opcional.
