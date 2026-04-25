import type { Metadata } from "next";
import "./globals.css";
import { Inter, Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { cn } from "@/lib/cn";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "next-themes";
import { getDir, isLocale, DEFAULT_LOCALE, type Locale } from "@/i18n/config";
import { localeFontHrefs } from "@/i18n/fonts";

// F9 · ADR-076 — Plus Jakarta Sans (display), Inter (body), JetBrains Mono
// (monetário + identificadores). As variáveis CSS abaixo são consumidas
// por design-tokens/tokens.json → frontend/src/styles/tokens.css.
const fontBody = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body",
});

const fontDisplay = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
});

const fontMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Mathoms AI — Análise Patrimonial",
  description: "Plataforma de análise e consolidação financeira patrimonial",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const rawLocale = await getLocale();
  const locale: Locale = isLocale(rawLocale) ? rawLocale : DEFAULT_LOCALE;
  const messages = await getMessages();
  const dir = getDir(locale);
  const fontHrefs = localeFontHrefs(locale);

  return (
    <html
      lang={locale}
      dir={dir}
      className={cn(
        fontBody.variable,
        fontDisplay.variable,
        fontMono.variable,
      )}
      suppressHydrationWarning
    >
      <head>
        {fontHrefs.map((href) => (
          <link
            key={href}
            rel="stylesheet"
            href={href}
            crossOrigin="anonymous"
          />
        ))}
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased font-body">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Toaster position="bottom-right" richColors />
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
