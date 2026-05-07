---
id: ADR-130
type: adr
title: "Internacionalização com `next-intl` + persistência em `users.locale`"
status: Proposto
phase: "F12"
date: "2026-04-25"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 130"]
tags:
  - type/adr
  - status/proposto
size_lines: 127
---

# ADR-130 — Internacionalização com `next-intl` + persistência em `users.locale`

**Status:** Proposto (F12) • **Data:** 2026-04-25 • **Revisão:**
2026-04-26 (escopo de locales reduzido de 11 → 10; substitui
hi/ar/bn/id por de/ja/ko)

**Contexto:** Plataforma é hoje 100% pt-BR. Usuário pediu suporte a
múltiplos idiomas — escopo final: **10 locales** (top 7 globais +
pt-PT + de/ja/ko por requisito de produto APAC/EU/DACH). Decisões a
tomar: biblioteca de i18n, estratégia de URLs, persistência da
escolha, suporte a CJK (zh-CN, ja, ko), pluralização (ru 4 formas),
e como integrar com o codegen do `report_layout.yaml`.

A revisão de 2026-04-26 retira `hi`/`ar`/`bn`/`id` do escopo F12
(reentram via §11 do I18N_PLAN.md quando re-priorizados) e adiciona
`de`/`ja`/`ko`. Sem `ar` no escopo atual, RTL deixa de ser
pré-requisito; com `ja`/`ko` entrando, CJK expande de 1 para 3
scripts mas as fontes seguem condicionais.

Alternativas consideradas:

- **Biblioteca:** `next-intl` (App Router-native, server components,
  ICU MessageFormat nativo) vs `react-intl` (mais maduro mas
  client-only) vs `i18next` (genérico, integração Next mais manual)
  vs `lingui` (menor adoção).
- **URL:** prefixo `/<locale>/...` (SEO-friendly) vs cookie
  `NEXT_LOCALE` (preserva URLs canônicas ADR-108).
- **Persistência:** só cookie/localStorage vs coluna `users.locale`
  no DB.
- **Tradução:** humana from-scratch (~360h) vs MT (DeepL Pro) +
  revisão humana (~135h total + ~$4.050 custo externo).

**Decisão:**

1. **`next-intl@^3`** como biblioteca i18n no frontend.
2. **Cookie `NEXT_LOCALE`** sem prefixo de URL (preserva ADR-108,
   `app.mathoms.ai`).
3. **Coluna `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'`**
   no DB + claim `locale` em JWT (cobre cross-device).
4. **10 locales** suportados — top 7 globais por contagem de
   speakers (Ethnologue 2024) + pt-PT + de/ja/ko por requisito de
   produto:

   `pt-BR` (default), `en`, `pt-PT`, `zh-CN`, `es`, `fr`, `ru`,
   `de`, `ja`, `ko`.

5. **`<html lang>`** dinâmico; `dir="ltr"` fixo no escopo atual
   (sem locales RTL ativos). `RTL_LOCALES` permanece exportado como
   `Set` vazio para extensão futura sem refactor. CSS logical
   properties (`margin-inline-start`, etc.) ficam **recomendadas**
   em código novo (não obrigatórias) — preparam reentrada de RTL
   sem ESLint rule custom enforcing.
6. **Fontes secundárias condicionais**: Noto Sans SC (zh-CN), Noto
   Sans JP (ja), Noto Sans KR (ko) carregadas via `<link>` apenas
   quando o locale ativo precisa (preserva bundle ~420kb totais).
7. **ICU MessageFormat** para plurais e seleção (necessário para
   `ru` com 4 formas; `zh-CN`/`ja`/`ko` têm plural único; infra
   preservada para ar 6 formas quando RTL voltar).
8. **Tradução: pipeline MT (DeepL Pro) → glossário fintech →
   revisão humana por nativo**. Locales com MT ratio > 5%
   permanecem em "beta" com banner explícito; promovidos a
   produção quando ratio < 5%.
9. **Codegen do `report_layout.yaml`** muda para emitir apenas
   `i18n_key`s (sem strings inline) — labels migram para
   `frontend/src/i18n/messages/<locale>.json`. Teste de paridade de
   chaves entre 10 locales bloqueia merge se faltar entrada.
10. **Strings dinâmicas concatenadas proibidas** em JSX — ESLint
    rule custom força ICU MessageFormat (`{count, plural, ...}`).

JWT payload mudar (claim novo) é breaking segundo ADR-109; abre-se
**ADR-A6f.5b** dedicada antes do commit, com golden atualizado de
`backend/tests/test_auth_portability.py`.

A fundação F12.1 foi mergeada em 2026-04-25 contra a lista antiga
de 11 locales (`hi`/`ar`/`bn`/`id` incluídos; `de`/`ja`/`ko`
ausentes). A correção é rastreada em [BACKLOG F12.1e](BACKLOG.md#f12--internacionalização-i18n-10-locales)
como **P0 bloqueante** — precisa fechar antes das demais lanes
F12.2/3/4/5 começarem.

Detalhamento operacional, fases (F12.1–F12.8), critérios de aceite,
riscos e estimativas em [docs/I18N_PLAN.md](I18N_PLAN.md).

**Consequências:**

- ✅ 10 locales cobrem ~4,3 bilhões de speakers globais (~55% da
  população mundial), com forte cobertura em APAC/EU/DACH via
  zh-CN/ja/ko/de.
- ✅ Suporte a CJK em 3 scripts (Han Simplified, Han + Kana,
  Hangul) desde o dia 1.
- ✅ URLs canônicas (ADR-108) intactas — sem redirect, sem prefixo.
- ✅ Persistência cross-device via JWT claim + DB.
- ✅ Stateless (ADR-111) preservado: locale resolve por contexto/JWT,
  não cache mutável.
- ✅ ICU MessageFormat torna pluralização correta possível em todos
  os 10 locales (relevante para `ru`).
- ⚠️ Custo externo de tradução (~$4.050) + 45h revisão humana antes
  de promoção a produção (9 locales não-pt-BR).
- ⚠️ Fontes CJK (Noto SC + JP + KR) adicionam ~420kb totais ao
  bundle (mas só carregam quando o locale ativo precisa).
- ⚠️ Refactor de `format.ts` toca ~80 call sites; commit único
  facilita revisão.
- ⚠️ pt-BR + en saem prontos no primeiro release; outros 8 locales
  podem ficar em "beta" até revisão humana fechar.
- ⚠️ F12.1 mergeada com lista antiga; F12.1e é P0 bloqueante para
  ressincronizar `config.ts`/`fonts.ts`/`messages/`/`middleware.ts`/
  `tests/i18n/foundation.test.tsx` antes das demais lanes.
- ❌ RTL (`ar`/`he`) sai do escopo F12 — reentra como ticket
  dedicado quando re-priorizado (ver §11 do I18N_PLAN.md).
- ❌ Indic (`hi`/`bn`) e SE-Asia (`id`) saem do escopo F12 — mesma
  via de reentrada.
- ❌ SEO multilíngue não suportado (cookie-based). Aceito — app é
  autenticado; landing pública é F8 Growth.
- ❌ Conversão de moeda (BRL → CNY/EUR/JPY/KRW/...) fora de escopo;
  símbolo R$ mantém em todos locales (formatação muda).
- ❌ Tradução de narrativas LLM (E5, E7) e de dados do usuário
  (categorias custom, nomes de instituições) ficam para fase 2 com
  ADR dedicada.

Relaciona-se a: ADR-053 (Intl nativo para datas — agora parametrizado
por locale), ADR-076 (design system), ADR-097 D1 (warnings tipados —
aplicado a `UserFacingError` no backend), ADR-102 R18 (response_model
explícito — aplicado ao endpoint `PATCH /users/me/preferences`),
ADR-108 (URLs canônicas — preservadas), ADR-109 (auth portability —
exige ADR-A6f.5b por mudança no JWT payload), ADR-111 (stateless —
locale via contexto, não cache).
