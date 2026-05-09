---
id: ADR-184
type: adr
title: "Stack da landing estática (Hugo + CF Pages)"
status: Proposto
phase: A11
date: "2026-05-09"
relates_to:
  - "[[ADR-005]]"
  - "[[ADR-058]]"
  - "[[ADR-076]]"
  - "[[ADR-108]]"
  - "[[ADR-113]]"
  - "[[ADR-129]]"
  - "[[ADR-143]]"
  - "[[ADR-183]]"
supersedes: []
superseded_by: []
aliases: ["ADR 184", "Landing static stack"]
tags:
  - area/marketing
  - area/ops
  - phase/a11
  - status/proposto
  - type/adr
---

> ADR longa por design: consolida stack mínimo de publicação da landing
> estática + boundary explícita do que **NÃO** entra (toda decisão de
> backend, form server-side, analytics DIY, página `/privacidade`,
> `app.mathoms.ai`). Split em sub-ADRs criaria peças órfãs sem contexto
> cruzado.

## Contexto

A Fase 4.B do plano [[PLAN-competitive-pierre]] entrega o reposicionamento
de marca da Mathoms. Pilares narrativos + ICP scorecard + anti-personas
foram fixados em [[ADR-183]]; copy v1 vive em
`docs/_marketing/landing-copy-draft-v1.md` (PR-C mergeado em #144).

PR-D do plano publica a landing reescrita em `mathoms.ai`. A proposta
inicial (sessão 2026-05-09) cobria deploy completo: frontend Hugo + backend
Go (`landing-api`) + analytics DIY + ICP scorecard interativo + `/privacidade`.
Após revisão de 4 subagentes (`build-vs-buy`, `senior-cto`, `sre-devops`,
`gtm-strategist`), o CEO recolheu o escopo para **landing 100% estática
client-side**, desacoplando a publicação da copy da decisão de "primeiro
backend de produção" — decisão arquitetural maior que conflita com
[[ADR-005]] / [[ADR-058]] (ambas voltadas a `Proposto` em 2026-05-09 para
refletir realidade) e [[ADR-108]] §5 (topology DNS sob revisão).

Esta ADR fixa o stack mínimo para publicar a landing estática como V1,
preservando modularidade para evolução futura (form server-side, analytics
próprio, ICP card interativo) sem comprometer a decisão de backend.

ADRs vigentes que esta decisão respeita:

- [[ADR-076]] (design tokens fonte única — `tokens.json` → CSS).
- [[ADR-108]] §1-4, §6-8 (subdomain strategy + cookies + CORS).
- [[ADR-129]] (sem renderer HTML server-side — landing é estática, não SSR).
- [[ADR-143]] (methodology = code — landing comunica método sem nomear autores §13.2 [COPY_GUIDELINES](../reference/COPY_GUIDELINES.md)).
- [[ADR-183]] (pilares + vocabulário canônico que a copy v1 já respeita).

## Decisão

### D1. SSG: Hugo

Hugo (Go-based static site generator) gera landing como HTML/CSS puro.

**Trade-off considerado:** Hugo é "buy" (framework externo), não "build".
Alternativas avaliadas:
- **SSG Go in-house** — 3-5 dias extras de plumbing sem ganho técnico real
  para landing de 5 seções; rejeitado por NIH.
- **Next.js Static Export** — reaproveitaria design tokens via React mas
  adiciona Node toolchain ao build da landing; landing não precisa de
  componentes React complexos (leitura linear), rejeitado.
- **Astro / 11ty** — Node-based, mesma objeção; rejeitado.

**Justificativa:** builds sub-segundo, binário único Go (alinha em
espírito com [[ADR-113]]), zero JS runtime no cliente, output 100% HTML
estático portátil, lock-in baixo (output é HTML/CSS puro; copy em Markdown
migra trivial — esforço de saída ~1-2 dias se um dia migrarmos).

### D2. Hosting: Cloudflare Pages

Free tier ilimitado de bandwidth + 500 builds/mês + edge cache global +
branch previews automáticos (URL única por PR). Domínio `mathoms.ai` já
está na Cloudflare ([[ADR-108]]) — zero fricção de DNS.

Aderente a [[ADR-108]] §1-4, §6-8 (subdomain strategy estável). [[ADR-108]]
§5 ganha nota cross-ref: a landing estática (`mathoms.ai` apex via CF Pages)
**não depende** de [[ADR-005]] / [[ADR-058]] — apex aponta para CF Pages
direto, independente do hosting de backend que está sob revisão.

### D3. CSS: Tailwind via CLI standalone

Tailwind CSS Standalone CLI (binário Go, mantido pela Tailwind Labs)
processa `*.html` e templates Hugo sem Node toolchain. Bundle final ~10-30KB
após `tailwind --minify`. Integração via `make` target acoplado ao build do
Hugo.

**Trade-off considerado:** Tailwind via PostCSS no Hugo Pipes exige Node.
Tailwind via CDN tem performance inferior. Standalone CLI é o sweet spot.

### D4. Design tokens: reuso de `design-tokens/build.py`

Estender `design-tokens/build.py` para emitir
`services/landing/static/tokens.css` (CSS variables) consumido pelo Tailwind
config (modo `@theme inline`). Preserva invariante "tokens.json é fonte
única; CSS é a única saída do build" ([[ADR-076]]).

**Alternativa rejeitada:** duplicar tokens em config Hugo — viola DRY,
alto risco de drift entre landing e produto futuro.

### D5. Analytics V1: Cloudflare Web Analytics

Script tag built-in CF Pages, cookieless, privacy-first, sem coleta de
PII. Cobre pageview/visitor agregado mas **não cobre** dwell por seção
(indicator 1 de [[ADR-183]] §"Leading indicators") nem scroll depth
(indicator 2). Aceito como cobertura parcial — instrumentação completa
entra com decisão futura (§"Decisão futura").

**Alternativas rejeitadas:** Plausible/Umami self-hosted (exige backend),
PostHog (vendor extra + cookies), DIY (exige backend Go ou CF Pages
Function — postergado).

### D6. CTA primário: `mailto:`

Hero CTA `Pedir convite` aponta para `mailto:hello@mathoms.ai` (endereço
final TBD pelo CEO). Subject template guia o lead:
`Convite Mathoms — [seu nome]`.

**Trade-off considerado:** form nativo via Cloudflare Pages Functions
(serverless edge, free, escreve em CF KV) cobriria captura estruturada,
mas adiciona vendor lock-in CF Pages Functions e complexidade de função
edge. Análise GTM (`gtm-strategist`, sessão 2026-05-09) apontou risco de
perda de 30-50% de leads HENRY mobile com `mailto:` (cliente de email mal
configurado). CEO aceita risco em V1; revisita se sinal qualitativo for
negativo (ver §"Decisão futura" gatilho c).

**Mitigação:** subject template pré-preenchido reduz fricção; aprovação
manual de convites pelo CEO em V1 (sem fluxo automatizado — débito
declarado).

### D7. Header sem botão "Entrar"

`app.mathoms.ai` (área logada do produto) ainda não existe em produção.
Botão "Entrar" no header sem destino válido violaria invariante UX
"landing nunca quebra". Opção A escolhida pelo CEO (sessão 2026-05-09):
header só com logo + CTA `Pedir convite`. Quando `app.mathoms.ai` for
promovido a produção (track separado, fora desta ADR), link "Entrar" entra
no header com diff de 1 linha.

### D8. Microcopy de escassez sob CTA hero

Sugestão atual:

> Beta fechado por convite. Onboarding pessoal, vagas limitadas a cada mês.

Comunica escassez deliberada, reforça posicionamento HENRY (rejeita
mass-market — coerente com [[ADR-183]] §"Anti-personas"), evita jargão
técnico ("workspace") que pode confundir lead não-tech.

### D9. LGPD V1: cookieless, sem `/privacidade`

CF Web Analytics não usa cookies; `mailto:` não persiste estado client-side;
não há coleta de PII via form em V1. **Não é necessário cookie banner**
para PR-D-A.

`/privacidade` (LGPD art. 9 — aviso prévio à coleta de email) é **débito
declarado**. Mitigação imediata: copy explícita perto do CTA mailto:
indicando finalidade do contato. Página entra na sprint subsequente quando
form server-side ou analytics DIY entrarem (gatilho da §"Decisão futura").

### D10. Localização: `services/landing/`

Mono-repo, alinhado com convenção `services/<name>/` (CLAUDE.md
§"Estrutura"). Build artifact `services/landing/public/` é gitignored. CF
Pages aponta para sub-diretório (`Build directory: services/landing`,
`Build command: hugo --minify`).

Quando a landing precisar virar serviço autônomo (extração futura),
`services/landing/` move para outro repo trivialmente — output já é
HTML/CSS puro, sem dependência cruzada com `pipeline/` ou `backend/`.

### D11. Modularidade — invariantes para extração futura

1. **Tokens** consumidos via CSS variables (não via Tailwind config
   customizado dependente do build); migrar Hugo→Astro/11ty preserva 100%
   dos tokens.
2. **Copy em Markdown puro** (frontmatter mínimo); independente de
   qualquer engine.
3. **Static output** é HTML/CSS portátil — qualquer host que sirva
   estáticos (Netlify, Vercel, S3+CloudFront, nginx) consegue servir.
4. **Form action em V1 = `mailto:`** (não acopla a backend); quando virar
   form server-side, swap em 1 atributo HTML.
5. **Analytics em V1 = CF Web Analytics** (script tag); swap para
   PostHog/Plausible/DIY = remover/substituir 1 script tag.

## Out of scope (decisões NÃO feitas aqui)

- ❌ **Backend de leads** (Cloud Run / Fly.io / Hetzner / Neon / Postgres /
  outros) — postergado até gatilho da §"Decisão futura". [[ADR-005]] e
  [[ADR-058]] permanecem `Proposto`.
- ❌ **Form server-side** (CF Pages Functions / Tally / Go API) — postergado.
- ❌ **Analytics DIY** (tracker JS + endpoint próprio + DB events +
  IntersectionObserver scroll/dwell) — postergado.
- ❌ **ICP scorecard interativo** — postergado para futuro PR-D-B.
- ❌ **Página `/privacidade`** — débito declarado, entra com PR-D-B
  futuro.
- ❌ **`app.mathoms.ai`** (área logada do produto) — track separado, fora
  de PR-D.
- ❌ **Email open rate** (indicator 5 de [[ADR-183]]) — suspenso por CEO.
- ❌ **Comparativo público com concorrente** — Fase 4.E (gated por Fase 2
  MCP live).
- ❌ **Narrativa AI conversacional** — gated por Fase 3 chat beta.

## Decisão futura — gatilho de revisão

A decisão de "primeiro backend de produção" será fechada em ADR futura
(provável `ADR-NNN — Primeiro backend de produção`) quando **um dos
gatilhos** disparar:

- **(b)** Backend Python `api.mathoms.ai` for promovido a produção
  (decisão estrutural maior, requer ADR própria);
- **(c)** `mailto:` começar a derrubar conversão da landing
  qualitativamente (sinais: CEO observa drop em leads/mês, ou entrevistas
  da Fase 4.A reportam fricção mobile recorrente).

Quando o gatilho disparar, a ADR futura decide:

- Hosting backend (Hetzner CX32 [[ADR-005]] / Cloud Run / Fly.io / outro).
- DB managed (Postgres self-hosted / Neon / Supabase / outro).
- Form server-side (CF Pages Functions / Go API).
- Analytics DIY (modular, 3-4 boundaries: API JS, schema versionado,
  endpoint, dedupe).
- ICP scorecard interativo (widget vanilla JS / Alpine / similar).
- Página `/privacidade` (LGPD).
- Reativação de [[ADR-005]] / [[ADR-058]] como `Decidido` ou supersedere
  por nova decisão.

## Consequências

### Positivas

- **Time-to-V1 enxuto:** ~3-5 dias úteis (sem backend Go, sem CI/CD
  complexo, sem migrations, sem secrets).
- **Custo $0/mês:** CF Pages free, Hugo free, CF Web Analytics free.
- **Aderente a [[ADR-108]]:** apex `mathoms.ai` via CF Pages é compatível
  com subdomain strategy decidida.
- **Nenhuma decisão sobre backend** — não cria padrão prematuro. [[ADR-005]] /
  [[ADR-058]] permanecem `Proposto` (sugestão forte sob revisão).
- **Modularidade preservada** para evolução: Hugo output portátil; mailto:
  → form server-side é swap de 1 atributo HTML; analytics CF → DIY é swap
  de 1 script tag.
- **Reuso `design-tokens/build.py`** mantém invariante de fonte única
  ([[ADR-076]]).

### Negativas

- **Sem indicators 1, 2 e 6 de [[ADR-183]] em V1** (dwell hero, scroll
  depth, % trials ICP ≥ 12). Cobertura parcial via CF Web Analytics
  (pageview/visitor agregado). Aceito; janela de 30-60 dias para
  revalidar com PR-D-B futuro.
- **`mailto:` pode perder leads HENRY mobile** (estimativa GTM 30-50%).
  CEO aceita risco V1; mitigação por subject template + microcopy. Reabre
  se sinal qualitativo for negativo (ver §"Decisão futura" gatilho c).
- **Sem `/privacidade` em V1** — risco LGPD baixo (coleta via mailto:
  voluntária e óbvia, sem persistência server-side de PII em V1) mas
  não-zero. Débito declarado.
- **Aprovação de convites manual** (CEO responde email a email).
  Aceitável até volume justificar automação.
- **Tailwind como dependência de build** (binário standalone) — terceira
  ferramenta no toolchain (ao lado de Hugo + Python). Aceito; standalone
  CLI dispensa Node.

### Risco assimétrico

Esta ADR é deliberadamente **enxuta** porque a maior decisão arquitetural
(primeiro backend de produção) está postergada. O risco assimétrico é
tomar uma decisão de backend prematura: ADR-184 evita isso publicando a
landing sem comprometer hosting de backend, preservando otimização da
decisão posterior com mais informação real (volume de leads, comportamento
mobile, sinal qualitativo de fricção).

## Sequência operacional

| Ordem | Owner | Entregável | Status |
|---|---|---|---|
| **PR-A** | orquestrador | [[ADR-183]] mergeada como `Proposto` | ✅ #141 |
| **PR-B** | `product-manager` | Track skeleton `gtm-landing-copy-rewrite.md` | ✅ #143 |
| **PR-C** | `product-designer` | Copy v1 em `docs/_marketing/landing-copy-draft-v1.md` | ✅ #144 |
| **PR-D pré** | orquestrador | Esta ADR-184 + edits a [[ADR-005]]/[[ADR-058]]/[[ADR-108]] + track `gtm-landing-publish-static.md` | 🚧 este PR |
| **PR-D-A** | CEO + designer | Implementação do site Hugo em `services/landing/` + deploy CF Pages + DNS apex `mathoms.ai` ON | ⬜ pendente |
| **PR-D-B (futuro)** | TBD | Backend de leads + analytics DIY + form + `/privacidade` + ICP card — gatilho da §"Decisão futura" | ⬜ pendente |
| **PR-E** | orquestrador | Flip [[ADR-183]] e esta ADR-184 para `Decidido (Sprint XX.Y)` quando 4.B publicar e ≥ 4/6 indicators ≥ 30 dias positivos | ⬜ pendente |

## Referências

### ADRs relacionadas

- [[ADR-005]] — VPS Hetzner (`Proposto`, sugestão atual de hosting backend)
- [[ADR-058]] — CX32 sizing (`Proposto`, acoplada a 005)
- [[ADR-076]] — Design tokens fonte única
- [[ADR-108]] — URLs canônicas (apex `mathoms.ai` para landing)
- [[ADR-113]] — Convenções Go (preparação stack futura)
- [[ADR-129]] — Sem renderer HTML server-side
- [[ADR-143]] — Methodology = code
- [[ADR-183]] — Pilares narrativos da landing (ADR-pai desta lane)

### Plano canônico

- [[PLAN-competitive-pierre]] — Fase 4.B publicação da landing reescrita

### Artefatos de execução

- `docs/_marketing/landing-copy-draft-v1.md` — copy v1 (PR-C mergeado)
- `docs/sprint/A11/tracks/gtm-landing-publish-static.md` — track operacional PR-D-A
- `docs/sprint/A11/tracks/gtm-landing-copy-rewrite.md` — track-pai (PR-B mergeado)
