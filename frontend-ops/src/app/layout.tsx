import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mathoms · Console interno",
  description: "Console operacional interno (IA-0). Acesso restrito.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
