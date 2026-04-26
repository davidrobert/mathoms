import { useEffect, useState } from "react";

/** v2.E.3 — `true` quando a página está em `@media print`.
 *
 * Charts usam para esconder controles interativos (PeriodToggle, slide
 * window) e fixar a janela em "12m" — texto + visual ficam estáveis no
 * PDF gerado por `pdf_renderer.py` (Playwright server-side).
 *
 * Em jsdom (vitest) `matchMedia` retorna `matches: false` por default
 * (ver `tests/setup.ts`), então o estado inicial é `false` — adequado
 * para tests que não exercitam print explicitamente.
 */
export function useIsPrint(): boolean {
  const [isPrint, setIsPrint] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("print");
    setIsPrint(mql.matches);
    const handler = (e: MediaQueryListEvent): void => setIsPrint(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isPrint;
}
