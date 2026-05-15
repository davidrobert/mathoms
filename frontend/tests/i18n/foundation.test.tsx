/**
 * ADR-130 revisado 2026-05-15 — Smoke da fundação i18n.
 *
 * Escopo F12 reduzido para 3 locales (pt-BR + en + es), alinhado ao ICP
 * de brasileiros nômades digitais morando fora do Brasil. Locales
 * pt-PT/zh-CN/fr/ru/de/ja/ko removidos — reentram apenas se ICP mudar
 * (mercado global) via nova ADR.
 *
 * Garante que:
 * 1. Os 3 locales suportados têm arquivo de mensagens com `header.title`
 *    + `_meta.locale` consistente.
 * 2. `NextIntlClientProvider` carrega messages e `useTranslations()`
 *    resolve a chave nos 3 locales.
 * 3. Helpers `getDir()` / `RTL_LOCALES` retornam sempre `ltr` no escopo
 *    atual (sem locales RTL — `RTL_LOCALES` vazio).
 * 4. `localeFontHrefs()` retorna `[]` em todos os 3 locales (Plus Jakarta
 *    + Inter + JetBrains Mono cobrem Latin Extended-A; sem fontes
 *    secundárias no escopo F12).
 * 5. Locales fora do escopo F12 são rejeitados por `isLocale()`.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Override do mock global em tests/setup.ts: aqui queremos `useTranslations`
// real para provar que `NextIntlClientProvider` resolve as chaves dos 3
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

import en from "@/i18n/messages/en.json";
import es from "@/i18n/messages/es.json";
import ptBR from "@/i18n/messages/pt-BR.json";

const MESSAGES: Record<Locale, Record<string, unknown>> = {
  "pt-BR": ptBR,
  en,
  es,
};

function HeaderProbe() {
  const t = useTranslations("header");
  return <h1>{t("title")}</h1>;
}

describe("F12.1 i18n foundation", () => {
  it("LOCALES tem exatamente os 3 locales planejados", () => {
    expect(LOCALES).toHaveLength(3);
    expect(LOCALES).toContain(DEFAULT_LOCALE);
    expect(DEFAULT_LOCALE).toBe("pt-BR");
    expect(LOCALES).toEqual(["pt-BR", "en", "es"]);
  });

  it("isLocale aceita whitelist e rejeita fora dela", () => {
    expect(isLocale("pt-BR")).toBe(true);
    expect(isLocale("en")).toBe(true);
    expect(isLocale("es")).toBe(true);
    // Locales removidos pela revisão de escopo (ADR-130 2026-05-15).
    expect(isLocale("pt-PT")).toBe(false);
    expect(isLocale("zh-CN")).toBe(false);
    expect(isLocale("fr")).toBe(false);
    expect(isLocale("ru")).toBe(false);
    expect(isLocale("de")).toBe(false);
    expect(isLocale("ja")).toBe(false);
    expect(isLocale("ko")).toBe(false);
    expect(isLocale("xx")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
    expect(isLocale(123)).toBe(false);
  });

  it("RTL_LOCALES está vazio; getDir retorna ltr em todos os 3 locales", () => {
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

  it("localeFontHrefs retorna [] em todos os 3 locales (escopo F12 só Latin)", () => {
    for (const locale of LOCALES) {
      expect(localeFontHrefs(locale)).toEqual([]);
    }
  });
});
