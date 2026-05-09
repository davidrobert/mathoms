---
id: TRACK-gtm-landing-publish-static
type: track
title: "Track GTM Landing Publish Static — PR-D-A Fase 4.B COMPETITIVE_PIERRE"
sprint: A11
plan: PLAN-competitive-pierre
status: ready
created_at: "2026-05-09"
consumed_at: null
agent_role: "CEO + product-designer (com revisão sre-devops + product-manager)"
relates_to:
  - "[[ADR-183]]"
  - "[[ADR-184]]"
  - "[[PLAN-competitive-pierre]]"
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/marketing
  - area/ops
  - phase/a11
  - methodology/positioning
---

# Track GTM Landing Publish Static — PR-D-A Fase 4.B COMPETITIVE_PIERRE

> **Lane ID:** `gtm-landing-publish-static`
> **Branch prefix:** `agent/gtm-landing-publish-static/<yyyyMMdd-HHmm>`
> **Depende de:** [[ADR-184]] mergeado como `Proposto` · [[ADR-183]] mergeado como `Proposto` (#141) · `docs/_marketing/landing-copy-draft-v1.md` (#144)
> **Paralelo com:** nenhum (pickup exclusivo da lane `gtm-landing-publish-*`)
> **Conflita com:** outra sessão `agent/gtm-landing-publish-static/*` ativa
> **Onda:** independente (GTM, não toca eng produtivo do produto)
> **Sprint:** A11 (lane `A11.competitive-pierre` em [SPRINTS-active](../../../_MOC/SPRINTS-active.md))
> **Time-box:** 3-5 dias úteis (S-M)
> **Owner sugerido:** CEO direto + delegação a `product-designer` para implementação Hugo + revisão `sre-devops` (DNS/TLS/CF Pages config)
> **Fonte de verdade das regras:** [CLAUDE.md](../../../../CLAUDE.md) · [[ADR-184]] · [docs/reference/COPY_GUIDELINES.md §13](../../../reference/COPY_GUIDELINES.md)

---

## 1. Goal

Publicar a landing pública `mathoms.ai` reescrita conforme [[ADR-183]]
(pilares P1-P4) e copy v1 (`docs/_marketing/landing-copy-draft-v1.md`)
como **site estático 100% client-side**, usando a stack fixada em
[[ADR-184]] (Hugo + Tailwind via CLI standalone + Cloudflare Pages + CF
Web Analytics + CTA mailto:).

PR-D-A é a primeira **publicação pública** da Mathoms e o primeiro
componente em produção. Não estreia nenhum backend (Cloud Run / Hetzner /
Neon / etc) — toda decisão de backend está postergada para ADR futura
([[ADR-184]] §"Decisão futura").

---

## 2. Escopo

- **Materializar** `services/landing/` com Hugo + Tailwind via CLI
  standalone + estrutura `config.yaml`, `layouts/`, `content/`, `static/`.
- **Importar copy v1** de `docs/_marketing/landing-copy-draft-v1.md` para
  `services/landing/content/` (Markdown nativo).
- **Estender** `design-tokens/build.py` para emitir
  `services/landing/static/tokens.css` (CSS variables) — preserva
  invariante de fonte única ([[ADR-076]]).
- **Implementar microcopy de escassez** sob CTA hero conforme [[ADR-184]]
  §D8: "Beta fechado por convite. Onboarding pessoal, vagas limitadas a
  cada mês."
- **CTA primário** `Pedir convite` aponta para `mailto:hello@mathoms.ai`
  (endereço final TBD pelo CEO no momento da implementação) com subject
  template `Convite Mathoms — [seu nome]`.
- **Header sem botão "Entrar"** (Opção A) — só logo + CTA `Pedir
  convite`. Justificativa em [[ADR-184]] §D7.
- **Configurar CF Pages** apontando para `services/landing/` no mono-repo;
  branch previews automáticos em PRs.
- **Configurar DNS apex** `mathoms.ai` → CF Pages (proxy ON) + redirect
  301 `www.mathoms.ai` → apex.
- **TLS** Universal SSL automático do Cloudflare (não exige Let's
  Encrypt — a landing apex não depende de [[ADR-005]] / [[ADR-108]] §5).
- **CF Web Analytics** habilitado via dashboard CF Pages.
- **Smoke test humano** com 3-5 visitantes-cobaia (CEO + cônjuge + 1-3
  amigos HENRY) confirmando render desktop/mobile, copy legível, CTA
  mailto: funcional.
- **Adicionar `make landing-dev`** (alvo no Makefile raiz) que sobe Hugo
  server local + watcher de design-tokens em paralelo.

---

## 3. Não-objetivos (escopo explicitamente excluído)

- ❌ **Backend de leads** (Cloud Run / Fly.io / Hetzner / Neon / Postgres
  / outros) — escopo de ADR futura, gatilho em [[ADR-184]] §"Decisão
  futura".
- ❌ **Form server-side** (CF Pages Functions / Tally / Go API) — `mailto:`
  é a única captura em V1.
- ❌ **Analytics DIY** (tracker JS modular + endpoint próprio + DB events
  + IntersectionObserver dwell/scroll) — postergado.
- ❌ **ICP scorecard interativo** — postergado para futuro PR-D-B.
- ❌ **Página `/privacidade`** — débito declarado em [[ADR-184]] §D9;
  entra com PR-D-B futuro.
- ❌ **`app.mathoms.ai`** (área logada do produto) — track separado, fora
  de PR-D.
- ❌ **Comparativo público com concorrente** — Fase 4.E (gated por Fase 2
  MCP live).
- ❌ **Narrativa AI conversacional** — gated por Fase 3 chat beta.
- ❌ **Pricing tiers** (R$ 99-149) — Fase 4.C ([[PLAN-competitive-pierre]]
  §3).
- ❌ **Decisão sobre stack/CMS** alternativa — Hugo + CF Pages fixados em
  [[ADR-184]] §D1-D2.
- ❌ **Promover [[ADR-005]] / [[ADR-058]]** de `Proposto` → `Decidido` —
  apex landing **não depende** de hosting backend; ver [[ADR-108]] §5
  (revisada 2026-05-09).

---

## 4. Dependências

| Dependência | Status | Bloqueia |
|---|---|---|
| [[ADR-184]] mergeada como `Proposto` | 🚧 PR-D-pré (este PR) | PR-D-A |
| [[ADR-183]] mergeada como `Proposto` | ✅ #141 (2026-05-08) | PR-D-A |
| Copy v1 em `docs/_marketing/landing-copy-draft-v1.md` | ✅ #144 (2026-05-09) | PR-D-A |
| Track skeleton (PR-B) | ✅ #143 (2026-05-08) | PR-D-A |
| Edits a [[ADR-005]] / [[ADR-058]] / [[ADR-108]] | 🚧 PR-D-pré (este PR) | PR-D-A consistente com ADRs |
| Cloudflare Pages habilitado para o repo `davidrobert/mathoms` | ⬜ pendente — PR-D-A | publicação CF Pages |
| Domínio `mathoms.ai` apontando para CF Pages | ⬜ pendente — PR-D-A | acesso público |
| Endereço de email canônico (`hello@mathoms.ai` ou similar) | ⬜ pendente — CEO decide na implementação | CTA mailto: funcional |

---

## 5. Critério de aceite

### 5.1 Para PR-D-pré (este PR — ADR + edits + track skeleton)

- [ ] [[ADR-184]] criada em `docs/adr/184-landing-static-stack-2026.md`
      como `Proposto`.
- [ ] [[ADR-005]] flippada `Decidido` → `Proposto` com nota de revisão.
- [ ] [[ADR-058]] flippada `Decidido` → `Proposto` com nota de revisão.
- [ ] [[ADR-108]] §5 ganha nota cross-ref que destino A record é
      condicional a [[ADR-005]] / [[ADR-058]] (`Proposto`).
- [ ] Track materializado em `docs/sprint/A11/tracks/gtm-landing-publish-static.md`
      com `status: ready`.
- [ ] Frontmatter validado por `dev/validate_frontmatter.py`.
- [ ] Wikilinks resolvendo via `dev/check_doc_links.py`.
- [ ] Anchors históricos via `dev/check_adr_anchors.py`.
- [ ] Índices regenerados via `dev/build_doc_index.py --check`.
- [ ] PR-D-pré mergeado em `main` (CI verde — docs-only).

### 5.2 Para PR-D-A completo (escopo principal desta lane)

- [ ] `services/landing/` materializado com Hugo + Tailwind CLI standalone.
- [ ] `design-tokens/build.py` estendido para emitir
      `services/landing/static/tokens.css`.
- [ ] Copy v1 importada para `services/landing/content/` em Markdown.
- [ ] Microcopy de escassez sob CTA hero implementada conforme [[ADR-184]]
      §D8.
- [ ] CTA primário `Pedir convite` → `mailto:hello@mathoms.ai`
      (endereço final TBD CEO) com subject template.
- [ ] Header sem botão "Entrar" (Opção A).
- [ ] CF Pages projeto criado e conectado ao repo (`Build directory:
      services/landing`, `Build command: hugo --minify && tailwind ...`).
- [ ] DNS apex `mathoms.ai` apontando para CF Pages (proxy ON) +
      `www.mathoms.ai` → 301 apex.
- [ ] TLS ativo (CF Universal SSL); validação via `curl -I
      https://mathoms.ai | grep strict-transport-security`.
- [ ] CF Web Analytics habilitado e capturando pageviews.
- [ ] `make landing-dev` funcional (Hugo server + tokens watcher em
      paralelo).
- [ ] Smoke humano: 3-5 visitas reais (CEO + cônjuge + 1-3 amigos HENRY)
      confirmam render desktop/mobile, copy legível, CTA mailto: abre
      cliente de email com subject pré-preenchido.
- [ ] Auditoria sigilo: `python3 dev/check_sigilo_terms.py services/landing/content/**/*.md`
      → exit 0.
- [ ] PR-D-A mergeado em `main` (CI verde — código + docs).

### 5.3 Para a lane completa (PR-E, fora desta task)

- [ ] 30-60 dias pós-launch: ≥ 4 dos 6 leading indicators de [[ADR-183]]
      em sinal positivo (mesmo com cobertura parcial — pageview/visitor
      via CF Web Analytics + qualitativo via entrevistas 4.A). Se < 4:
      considerar refresh narrativo OU acelerar PR-D-B futuro.
- [ ] PR-E: flip [[ADR-183]] e [[ADR-184]] de `Proposto` → `Decidido
      (Sprint XX.Y)` com `phase:` registrada.

---

## 6. Priorização

### 6.1 RICE (primário)

| Componente | Valor | Justificativa |
|---|---|---|
| **Reach** | ~1.500 | Visitantes HENRY-fit únicos da landing reescrita em janela de 60 dias pós-launch (estimativa conservadora). |
| **Impact** | 3 (high) | Primeira presença pública da Mathoms; reposicionamento de marca afeta toda signup downstream + qualificação ICP + fundamento para tier R$ 99-149 (Fase 4.C). Multiplicador para 4.D/4.E/4.F. |
| **Confidence** | 0.85 | Stack enxuto (Hugo + CF Pages, free tier estável), pilares decididos pelo CEO ([[ADR-183]]), copy v1 já mergeada, zero estreia de backend. Risco residual: aprovação de convites manual + indicadores 1/2 sem cobertura completa. |
| **Effort** | 0.15 PM | 3-5 dias úteis distribuídos (designer implementa Hugo + CEO valida + smoke humano). |

**RICE = (1500 × 3 × 0.85) / 0.15 ≈ 25.500 pts** — top-tier de
priorização (alta confidence + baixíssimo effort + impact alto).

### 6.2 WSJF (secundário, sanity check)

- **Business Value:** 8/10 — habilita janela de medição da narrativa
  reescrita; sem PR-D-A, copy v1 fica em rascunho indefinidamente.
- **Time Criticality:** 9/10 — janela competitiva 12-18 meses
  ([[PLAN-competitive-pierre]] §2 P5).
- **Risk Reduction / Opportunity Enablement:** 7/10 — destrava 4.C
  (pricing), 4.D (conteúdo), 4.E (SEO), 4.F (parcerias).
- **Cost of Delay** = 8 + 9 + 7 = **24**.
- **Job Size** = 2/10 (~0.15 PM).

**WSJF = 24 / 2 = 12** — top-tier, alinhado com RICE.

---

## 7. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **`mailto:` derruba conversão HENRY mobile** ([[ADR-184]] §D6 trade-off) | M-A | M | CEO aceita risco V1; subject template guia o lead; gatilho (c) de [[ADR-184]] §"Decisão futura" reabre form server-side se sinal negativo |
| **Indicators 1/2/6 sem cobertura completa** em V1 ([[ADR-184]] §D5 trade-off) | A | B | CF Web Analytics cobre pageview/visitor agregado; qualitativo via entrevistas 4.A complementa; revalidar em PR-E |
| **Aprovação de convites manual sobrecarrega CEO** se volume escalar | B | M | Threshold subjetivo: se >20 leads/semana, abrir track de automação; débito declarado em [[ADR-184]] §"Consequências negativas" |
| **CF Pages free tier limit** (500 builds/mês) atingido em deploys frequentes | B | B | 500 builds/mês = 16/dia, folga grande; mitigação: skip Pages deploy em PRs draft |
| **Vocabulário canônico desrespeitado por implementação** — risco de copy reintroduzir termos §13.1 do COPY_GUIDELINES | B | A (legal/IP) | `dev/check_sigilo_terms.py services/landing/content/**/*.md` no smoke pré-merge; reviewer obrigatório |
| **Drift entre copy implementada e copy v1** — designer altera copy durante implementação Hugo sem atualizar `docs/_marketing/landing-copy-draft-v1.md` | M | M | Cláusula explícita: implementação Hugo **espelha** copy v1; alterações exigem PR separado em `docs/_marketing/` antes da merge de PR-D-A |
| **Domínio `mathoms.ai` apontando incorretamente** durante cutover de DNS | B | A | Pre-requisito: smoke em CF Pages preview URL (`<hash>.<proj>.pages.dev`) **antes** de mexer no apex; cutover de DNS é última etapa |
| **Sem `/privacidade`** abre risco LGPD não-zero ([[ADR-184]] §D9) | B | M | Mitigação: copy explícita perto do CTA mailto: ("ao enviar email, você concorda…"); `/privacidade` entra com PR-D-B futuro |

---

## 8. Sequência operacional (mapa do plano `competitive-pierre`)

| Ordem | Owner | Entregável | Status | Gate de saída |
|---|---|---|---|---|
| **PR-A** | orquestrador | [[ADR-183]] mergeada como `Proposto` | ✅ #141 | merge em `main` |
| **PR-B** | `product-manager` | Track `gtm-landing-copy-rewrite.md` | ✅ #143 | track materializado |
| **PR-C** | `product-designer` | Copy v1 em `docs/_marketing/` | ✅ #144 | copy mergeada com sigilo OK |
| **PR-D-pré** | orquestrador | [[ADR-184]] + edits a [[ADR-005]] / [[ADR-058]] / [[ADR-108]] + este track | 🚧 este PR | merge em `main` (docs-only) |
| **PR-D-A** | CEO + designer | Implementação Hugo em `services/landing/` + deploy CF Pages + DNS apex `mathoms.ai` ON | ⬜ pendente | landing live em `mathoms.ai` |
| **PR-D-B (futuro)** | TBD | Backend leads + analytics DIY + form + `/privacidade` + ICP card | ⬜ pendente | gatilho [[ADR-184]] §"Decisão futura" |
| **PR-E** | orquestrador | Flip [[ADR-183]] e [[ADR-184]] `Proposto` → `Decidido` | ⬜ pendente | ≥ 4/6 indicators ≥ 30 dias positivos |

---

## 9. Estimativa

- **PR-D-pré (este PR):** **XS** (1-2h) — ADR + 3 edits a ADRs existentes + track skeleton + validação.
- **PR-D-A (escopo principal):** **S-M** (3-5 dias úteis) — implementação Hugo + Tailwind CLI standalone + design-tokens extension + import copy + CF Pages config + DNS cutover + smoke humano.

---

## 10. Coordenação com lanes paralelas

Não há lanes paralelas. PR-C (`gtm-landing-copy-rewrite`) já mergeou (#144). Lane [A11.w5 Frontend + Methodology](../lanes/A11-w5-frontend-methodology.md) (cleanup de terminologia user-facing) é tangente — vocabulário canônico de [[ADR-183]] §"Decisão" é fonte única tanto para a landing (PR-D-A) quanto para o cleanup user-facing.

**Protocolo:** se PR-D-A descobrir gap no vocabulário canônico durante implementação, abrir issue/PR separado em [[ADR-183]] §"Decisão" antes de inventar termo paralelo.

---

## 11. Notas de execução para implementador

### 11.1 Inputs canônicos (ler nesta ordem)

1. **[[ADR-184]]** — stack fixado, invariantes de modularidade, decisão futura (gatilho de revisão).
2. **[[ADR-183]]** — pilares P1-P4, vocabulário canônico, ICP scorecard (referência mental, não interativo em V1), anti-personas.
3. **`docs/_marketing/landing-copy-draft-v1.md`** — copy v1 a importar para Hugo content.
4. **[[ADR-076]]** — design tokens fonte única; estender `design-tokens/build.py`.
5. **[§13 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md)** — sigilo metodológico.
6. **[CLAUDE.md](../../../../CLAUDE.md) §"Code style"** — convenções gerais (idioma, dados sensíveis, formatação).

### 11.2 Estrutura proposta de `services/landing/`

```
services/landing/
├── config.yaml              # Hugo config (baseURL, theme, params)
├── content/
│   ├── _index.md            # hero P1 + sections P2/P3/P4 (importado de copy v1)
│   └── ...                  # adicionais quando necessário
├── layouts/
│   ├── index.html           # template do _index.md
│   ├── partials/
│   │   ├── head.html
│   │   ├── header.html      # logo + CTA Pedir convite (sem Entrar)
│   │   └── footer.html
│   └── _default/
│       └── baseof.html
├── static/
│   ├── tokens.css           # gerado por design-tokens/build.py
│   └── analytics.html       # CF Web Analytics snippet (se não auto-injetado por Pages)
├── assets/
│   └── tailwind.css         # input Tailwind (apenas @import + theme inline com tokens)
├── public/                  # output Hugo (gitignored)
└── README.md                # como rodar local + deploy
```

### 11.3 Build pipeline

```bash
# Local dev (make landing-dev)
hugo server -D --bind 0.0.0.0 --port 1313 &
tailwindcss -i services/landing/assets/tailwind.css -o services/landing/static/tailwind.css --watch &
python3 design-tokens/build.py --watch &
wait

# Build de produção (CF Pages roda)
python3 design-tokens/build.py --target services/landing/static/tokens.css
tailwindcss -i services/landing/assets/tailwind.css -o services/landing/static/tailwind.css --minify
hugo --minify --source services/landing
```

### 11.4 Gates editoriais antes de submit

```bash
# Sigilo
python3 dev/check_sigilo_terms.py services/landing/content/**/*.md
# expected: exit 0

# Pre-commit completo
pre-commit run --all-files
```

### 11.5 Output esperado de PR-D-A

- `services/landing/` materializado e funcional
- CF Pages projeto criado e deploy automático em `main`
- DNS apex `mathoms.ai` ativo
- Smoke humano documentado em comentário do PR (3-5 nomes + dispositivos
  testados + observações)

---

## 12. Fora de escopo — pointer para destinos corretos

| Pergunta | Onde resolver |
|---|---|
| "Que CMS usar?" | Decidido em [[ADR-184]] §D1: Hugo. Sem reabertura. |
| "Form nativo no lugar de mailto:?" | Postergado para PR-D-B futuro; gatilho [[ADR-184]] §"Decisão futura" (c) |
| "Analytics DIY com tracker JS?" | Postergado para PR-D-B futuro |
| "ICP scorecard interativo?" | Postergado para PR-D-B futuro |
| "Página `/privacidade`?" | Débito declarado [[ADR-184]] §D9; entra com PR-D-B |
| "Tier free vs trial 30d? R$ 99 ou R$ 149?" | Fase 4.C — abrir track `gtm-pricing-repositioning.md` + ADR `pricing-repositioning-2026` ([[PLAN-competitive-pierre]] §5) |
| "Comparativo público com Pierre?" | Fase 4.E — gated por Fase 2 (MCP) live |
| "Hero conversacional / chat na landing?" | Fora de escopo; entra como P5 ou refresh do P4 quando Fase 3 (chat) beta |
| "Programa de embaixadores CFP / contadores?" | Fase 4.F |
| "SEO long-tail sobre keywords Pierre?" | Fase 4.E (parcial) |
| "Pesquisa de segmento qualitativa (10-15 entrevistas HENRY)?" | Fase 4.A — track [`gtm-segment-research.md`](../../A11/tracks/) (a criar) |

---

## 13. Definição de feito (deste PR-D-pré)

1. Arquivos criados:
   - `docs/adr/184-landing-static-stack-2026.md`
   - `docs/sprint/A11/tracks/gtm-landing-publish-static.md` (este)
2. Arquivos editados:
   - `docs/adr/005-vps-hetzner-para-producao.md` (status flip + nota)
   - `docs/adr/058-vps-cx32-para-sizing.md` (status flip + nota)
   - `docs/adr/108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md` (§5 cross-ref note)
3. `dev/validate_frontmatter.py` passa sem erros nos 5 arquivos.
4. `dev/check_doc_links.py` passa (todos os wikilinks resolvem).
5. `dev/check_adr_anchors.py` passa (anchors históricos preservados).
6. `dev/build_doc_index.py --check` passa (índices `_generated/` sincronizados).
7. Pre-commit verde nos arquivos staged.
8. PR-D-pré aberto contra `main` com `--squash --auto`; CI verde
   (docs-only — sem suíte pytest exigida).
9. Merge confirmado: `gh pr view <N> --json mergeCommit,mergedAt` retorna
   data; `git log origin/main --oneline` mostra o commit-merge.

---

## 14. Referências

### Internas

- [[ADR-184]] — Stack da landing estática (origem desta lane)
- [[ADR-183]] — Pilares narrativos da landing
- [[ADR-005]] — VPS Hetzner (`Proposto`)
- [[ADR-058]] — CX32 sizing (`Proposto`)
- [[ADR-108]] — URLs canônicas
- [[PLAN-competitive-pierre]] — plano canônico (§3 Fase 4.B)
- [`docs/sprint/A11/tracks/gtm-landing-copy-rewrite.md`](gtm-landing-copy-rewrite.md) — track-pai (PR-B mergeado)
- [`docs/_marketing/landing-copy-draft-v1.md`](../../../_marketing/landing-copy-draft-v1.md) — copy v1 (PR-C mergeado)
- [`docs/reference/COPY_GUIDELINES.md`](../../../reference/COPY_GUIDELINES.md) §13 — sigilo metodológico

### Sprint placement

- [SPRINTS-active](../../../_MOC/SPRINTS-active.md) — lane `A11.competitive-pierre`
- [Sprint A11 _README](../../A11/_README.md) — contexto da sprint corrente
