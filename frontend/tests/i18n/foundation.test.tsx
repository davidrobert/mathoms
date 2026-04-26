/**
 * F12.1e · ADR-130 revisado 2026-04-26 — Smoke da fundação i18n.
 *
 * Garante que:
 * 1. Os 10 locales suportados têm arquivo de mensagens com `header.title`
 *    + `_meta.locale` consistente.
 * 2. `NextIntlClientProvider` carrega messages e `useTranslations()`
 *    resolve a chave nos 10 locales.
 * 3. Helpers `getDir()` / `RTL_LOCALES` retornam sempre `ltr` no escopo
 *    atual (sem locales RTL — `RTL_LOCALES` vazio).
 * 4. `localeFontHrefs()` injeta Noto Sans secundárias só nos 3 locales
 *    CJK (zh-CN, ja, ko).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Override do mock global em tests/setup.ts: aqui queremos `useTranslations`
// real para provar que `NextIntlClientProvider` resolve as chaves dos 10
// dicionários. Outros testes seguem usando o mock identity em setup.ts.
vi.doUnmock("next-intl");
const { NextIntlClientProvider, useTranslations } =
  await vi.importActual<typeof import("next-intl")>("next-intl");

import {
  DEFAULT_LOCALE,
  LOCALES,
  RTL_LOCALES,
  getDir,
  isLocale,
  type Locale,
} from "@/i18n/config";
import { localeFontHrefs } from "@/i18n/fonts";

import de from "@/i18n/messages/de.json";
import en from "@/i18n/messages/en.json";
import es from "@/i18n/messages/es.json";
import fr from "@/i18n/messages/fr.json";
import ja from "@/i18n/messages/ja.json";
import ko from "@/i18n/messages/ko.json";
import ptBR from "@/i18n/messages/pt-BR.json";
import ptPT from "@/i18n/messages/pt-PT.json";
import ru from "@/i18n/messages/ru.json";
import zhCN from "@/i18n/messages/zh-CN.json";

const MESSAGES: Record<Locale, Record<string, unknown>> = {
  "pt-BR": ptBR,
  en,
  "pt-PT": ptPT,
  "zh-CN": zhCN,
  es,
  fr,
  ru,
  de,
  ja,
  ko,
};

function HeaderProbe() {
  const t = useTranslations("header");
  return <h1>{t("title")}</h1>;
}

describe("F12.1 i18n foundation", () => {
  it("LOCALES tem exatamente os 10 locales planejados", () => {
    expect(LOCALES).toHaveLength(10);
    expect(LOCALES).toContain(DEFAULT_LOCALE);
    expect(DEFAULT_LOCALE).toBe("pt-BR");
  });

  it("isLocale aceita whitelist e rejeita fora dela", () => {
    expect(isLocale("pt-BR")).toBe(true);
    expect(isLocale("de")).toBe(true);
    expect(isLocale("ja")).toBe(true);
    expect(isLocale("ko")).toBe(true);
    // Locales removidos pela revisão de escopo (ADR-130 2026-04-26).
    expect(isLocale("hi")).toBe(false);
    expect(isLocale("ar")).toBe(false);
    expect(isLocale("bn")).toBe(false);
    expect(isLocale("id")).toBe(false);
    expect(isLocale("xx")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
    expect(isLocale(123)).toBe(false);
  });

  it("RTL_LOCALES está vazio; getDir retorna ltr em todos os 10 locales", () => {
    expect(Array.from(RTL_LOCALES)).toEqual([]);
    for (const locale of LOCALES) {
      expect(getDir(locale)).toBe("ltr");
    }
  });

  it.each(LOCALES.map((l) => [l]))(
    "messages/%s.json tem _meta.locale e header.title",
    (locale) => {
      const msgs = MESSAGES[locale] as {
        _meta?: { locale?: string };
        header?: { title?: string };
      };
      expect(msgs._meta?.locale).toBe(locale);
      expect(msgs.header?.title).toBeTruthy();
      expect(typeof msgs.header?.title).toBe("string");
    },
  );

  it.each(LOCALES.map((l) => [l]))(
    "useTranslations resolve header.title em %s",
    (locale) => {
      render(
        <NextIntlClientProvider
          locale={locale}
          messages={MESSAGES[locale] as Record<string, unknown>}
        >
          <HeaderProbe />
        </NextIntlClientProvider>,
      );
      const heading = screen.getByRole("heading", { level: 1 });
      expect(heading.textContent).toBeTruthy();
      expect(heading.textContent).toBe(
        (MESSAGES[locale] as { header: { title: string } }).header.title,
      );
    },
  );

  it("localeFontHrefs carrega Noto secundária apenas em zh-CN/ja/ko", () => {
    const needsExtra: ReadonlySet<Locale> = new Set(["zh-CN", "ja", "ko"]);
    for (const locale of LOCALES) {
      const hrefs = localeFontHrefs(locale);
      if (needsExtra.has(locale)) {
        expect(hrefs).toHaveLength(1);
        expect(hrefs[0]).toContain("fonts.googleapis.com");
      } else {
        expect(hrefs).toHaveLength(0);
      }
    }
  });
});
