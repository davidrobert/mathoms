// F12.1 · ADR-130 — Middleware de locale (cookie-based, sem prefixo URL).
//
// Lê NEXT_LOCALE; se ausente ou inválido, escreve DEFAULT_LOCALE no cookie
// para que próximas requisições e o servidor convirjam. Nunca redireciona
// (preserva contrato URL canônico ADR-108).

import { NextResponse, type NextRequest } from "next/server";
import {
  DEFAULT_LOCALE,
  LOCALE_COOKIE,
  isLocale,
} from "@/i18n/config";

export function middleware(request: NextRequest) {
  const candidate = request.cookies.get(LOCALE_COOKIE)?.value;
  if (isLocale(candidate)) {
    return NextResponse.next();
  }

  const response = NextResponse.next();
  response.cookies.set(LOCALE_COOKIE, DEFAULT_LOCALE, {
    path: "/",
    sameSite: "lax",
    httpOnly: false,
    maxAge: 60 * 60 * 24 * 365,
  });
  return response;
}

export const config = {
  // Ignora rotas internas do Next, _next/static, _next/image, favicon e API.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
