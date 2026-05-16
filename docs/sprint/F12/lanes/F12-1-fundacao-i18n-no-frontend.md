---
id: F12.1
type: lane
title: "Fundação i18n no frontend"
sprint: F12
plan: PLAN-i18n
status: shipped
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/shipped
  - priority/p0
---


# F12.1 — Fundação i18n no frontend


> ✅ **F12.1e fechada em 2026-04-26 (commit `94cf939`).** F12.1a-d
> ressincronizadas com a lista revisada de 10 locales; lanes
> F12.2/F12.3/F12.4/F12.5 desbloqueadas.

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.1a | Instalar `next-intl@^4` (Next 16 não aceita v3) + `frontend/src/i18n/{config,request,plural,fonts}.ts` + arquivos `messages/<locale>.json` com `_meta` + `header.title` (lista corrigida em F12.1e). | P0 | 4h | ✅ |
| F12.1b | `frontend/middleware.ts` cookie-based + matcher whitelist (lista corrigida em F12.1e); wrap `app/layout.tsx` em `NextIntlClientProvider` com `<html lang>`; plugin `next-intl/plugin` em `next.config.ts`. | P0 | 4h | ✅ |
| F12.1c | `src/i18n/fonts.ts` injeta Noto Sans SC (`zh-CN`) / Noto Sans JP (`ja`) / Noto Sans KR (`ko`) via `<link rel="stylesheet">` no `<head>` quando o locale ativo precisa; fallback `[lang]` em `globals.css`. | P0 | 4h | ✅ |
| F12.1d | `AppShell` consome `useTranslations("header").title`; smoke Vitest (`tests/i18n/foundation.test.tsx`, 24 asserts) cobre paridade JSON × 10 locales, render real via `NextIntlClientProvider`, `getDir`/`isLocale`/`localeFontHrefs`. | P0 | 4h | ✅ |
| F12.1e | Sincronizar F12.1 com lista de 10 locales (ADR-130 revisado 2026-04-26). `config.ts` remove `hi`/`ar`/`bn`/`id`, adiciona `de`/`ja`/`ko`, `RTL_LOCALES = new Set()` (vazio). `fonts.ts`: Noto SC/JP/KR (sem Devanagari/Bengali/Arabic). `messages/`: `de.json`/`ja.json`/`ko.json` substituem `hi`/`ar`/`bn`/`id`. `globals.css` ajusta seletores `html[lang=...]`. `foundation.test.tsx` recalibra asserts. Suíte Vitest 571 passed; lint clean. | P0 (blocker) | 4h | ✅ (commit `94cf939`) |
