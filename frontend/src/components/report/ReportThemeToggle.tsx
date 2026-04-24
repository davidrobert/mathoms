"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

/** ADR-117 — theme toggle do relatório premium.
 *
 * Wrappa `next-themes` (já configurado em layout.tsx com attribute="class").
 * Renderiza um controle segmentado Light|Dark matching EXEMPLO_DE_RELATORIO.html
 * §theme-toggle (linhas 562-568). Integração na top-nav fica para Fase 4.
 */
type ThemeValue = "light" | "dark";

export function ReportThemeToggle({
  className,
}: {
  className?: string;
}) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const current: ThemeValue =
    mounted && resolvedTheme === "dark" ? "dark" : "light";

  return (
    <div
      className={className}
      role="group"
      aria-label="Tema do relatório"
      data-report-theme-toggle
    >
      {(["light", "dark"] satisfies ThemeValue[]).map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => setTheme(value)}
          aria-pressed={current === value}
          data-active={current === value}
          data-theme-value={value}
        >
          {value === "light" ? "Light" : "Dark"}
        </button>
      ))}
    </div>
  );
}
