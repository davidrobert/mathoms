// F12.1 · ADR-130 — next-intl getRequestConfig: lê cookie NEXT_LOCALE,
// valida contra whitelist, faz fallback para DEFAULT_LOCALE, e carrega
// messages/<locale>.json.

import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale, type Locale } from "./config";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const candidate = cookieStore.get(LOCALE_COOKIE)?.value;
  const locale: Locale = isLocale(candidate) ? candidate : DEFAULT_LOCALE;

  const messages = (await import(`./messages/${locale}.json`)).default;

  return { locale, messages };
});
