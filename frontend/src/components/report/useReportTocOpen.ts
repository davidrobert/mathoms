"use client";

import { useEffect, useState, useCallback } from "react";

/** Estado do TOC lateral do relatório (aberto/fechado), persistido em
 * localStorage. Só existe em `lg+`, onde o `<aside>` renderiza.
 *
 * Default fechado porque a coluna de leitura ganha por default — não porque a
 * faixa seja "a navegação primária", como este comentário afirmava até
 * A40.l104. A divisão real: a `ReportTopNav` responde **onde estou** (scroll-spy
 * + rótulo do chip ativo), o índice e o FAB do `FloatingNav` respondem **para
 * onde vou**. Abaixo de `lg` quem serve o índice é o FAB.
 *
 * Mesma convenção SSR-safe de `useReportFontScale`.
 */
const STORAGE_KEY = "mathoms:report:toc-open";
const DEFAULT_OPEN = false;

function readStoredOpen(): boolean {
  if (typeof window === "undefined") return DEFAULT_OPEN;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "true") return true;
    if (raw === "false") return false;
  } catch {
    // SecurityError em iframes com storage bloqueado — ignora silenciosamente
  }
  return DEFAULT_OPEN;
}

export function useReportTocOpen(): {
  open: boolean;
  setOpen: (next: boolean) => void;
  toggle: () => void;
} {
  const [open, setOpenState] = useState<boolean>(DEFAULT_OPEN);

  useEffect(() => {
    setOpenState(readStoredOpen());
  }, []);

  const persist = useCallback((next: boolean) => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // ignore
    }
  }, []);

  const setOpen = useCallback(
    (next: boolean) => {
      setOpenState(next);
      persist(next);
    },
    [persist],
  );

  const toggle = useCallback(() => {
    setOpenState((prev) => {
      const next = !prev;
      persist(next);
      return next;
    });
  }, [persist]);

  return { open, setOpen, toggle };
}
