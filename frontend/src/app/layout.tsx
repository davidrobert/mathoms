import type { Metadata } from "next";
import "./globals.css";
import { Inter, Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import { cn } from "@/lib/cn";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "next-themes";

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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="pt-BR"
      className={cn(
        fontBody.variable,
        fontDisplay.variable,
        fontMono.variable,
      )}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background text-foreground antialiased font-body">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <Toaster position="bottom-right" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
