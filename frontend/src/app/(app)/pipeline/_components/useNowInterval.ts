"use client";

import { useEffect, useState } from "react";

/** Relógio reativo — re-renderiza a cada `ms` enquanto `active` for true.
 *  Usado para atualizar durations "ao vivo" em etapas em execução. */
export function useNowInterval(active: boolean, ms: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(id);
  }, [active, ms]);
  return now;
}
