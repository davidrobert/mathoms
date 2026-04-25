/**
 * F12.1 · ADR-130 — Smoke da fundação i18n.
 *
 * Garante que:
 * 1. Os 11 locales suportados têm arquivo de mensagens com `header.title`
 *    + `_meta.locale` consistente.
 * 2. `NextIntlClientProvider` carrega messages e `useTranslations()`
 *    resolve a chave nos 11 locales.
 * 3. Helpers `getDir()` / `RTL_LOCALES` retornam `rtl` apenas para `ar`.
 * 4. `localeFontHrefs()` injeta Noto Sans secundárias só nos locales
 *    que precisam de glifos fora de Latin Extended-A.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Override do mock global em tests/setup.ts: aqui queremos `useTranslations`
// real para provar que `NextIntlClientProvider` resolve as chaves dos 11
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

import ar from "@/i18n/messages/ar.json";
import bn from "@/i18n/messages/bn.json";
import en from "@/i18n/messages/en.json";
import es from "@/i18n/messages/es.json";
import fr from "@/i18n/messages/fr.json";
import hi from "@/i18n/messages/hi.json";
import id from "@/i18n/messages/id.json";
import ptBR from "@/i18n/messages/pt-BR.json";
import ptPT from "@/i18n/messages/pt-PT.json";
import ru from "@/i18n/messages/ru.json";
import zhCN from "@/i18n/messages/zh-CN.json";

const MESSAGES: Record<Locale, Record<string, unknown>> = {
  "pt-BR": ptBR,
  en,
  "pt-PT": ptPT,
  "zh-CN": zhCN,
  hi,
  es,
  ar,
  fr,
  bn,
  ru,
  id,
};

function HeaderProbe() {
  const t = useTranslations("header");
  return <h1>{t("title")}</h1>;
}

describe("F12.1 i18n foundation", () => {
  it("LOCALES tem exatamente os 11 locales planejados", () => {
    expect(LOCALES).toHaveLength(11);
    expect(LOCALES).toContain(DEFAULT_LOCALE);
    expect(DEFAULT_LOCALE).toBe("pt-BR");
  });

  it("isLocale aceita whitelist e rejeita fora dela", () => {
    expect(isLocale("pt-BR")).toBe(true);
    expect(isLocale("ar")).toBe(true);
    expect(isLocale("xx")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
    expect(isLocale(123)).toBe(false);
  });

  it("RTL_LOCALES contém apenas ar; getDir retorna rtl só para ar", () => {
    expect(Array.from(RTL_LOCALES)).toEqual(["ar"]);
    for (const locale of LOCALES) {
      expect(getDir(locale)).toBe(locale === "ar" ? "rtl" : "ltr");
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

  it("localeFontHrefs carrega Noto secundária apenas em zh-CN/hi/bn/ar", () => {
    const needsExtra: ReadonlySet<Locale> = new Set(["zh-CN", "hi", "bn", "ar"]);
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
