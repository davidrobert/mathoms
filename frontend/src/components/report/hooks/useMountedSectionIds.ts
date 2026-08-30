"use client";

import { useEffect, useMemo, useState } from "react";

const SEP = " ";

/* Por que este hook existe (A40.l104).
 *
 * `ReportTopNav` e `ReportToc` montam ANTES de o fetch do relatório resolver.
 * O efeito de scroll-spy dos dois chamava `getElementById` para todos os ids,
 * recebia `null` em todos, saía no `elements.length === 0` — e nunca mais
 * rodava, porque as deps (`groups`, `flatEntries`, `mode`) não mudam quando o
 * dado chega. Medido: varrendo 12 pontos do documento a 1600px, nenhum chip da
 * faixa ficava `data-active`; o índice tinha o mesmo defeito sempre que montava
 * junto com o load, que é o caso do usuário que volta (`toc-open` é persistido).
 *
 * Um sinal único de "dado pronto" não bastaria: `S_parecer` e `S_PROTECAO` têm
 * fetch próprio e montam depois das demais.
 */

/** Subconjunto de `ids` presente no DOM, re-avaliado quando o relatório monta
 * seções novas. */
export function useMountedSectionIds(
  ids: readonly string[],
): readonly string[] {
  const wanted = ids.join(SEP);
  const [present, setPresent] = useState("");

  useEffect(() => observeMountedIds(wanted, setPresent), [wanted]);

  return useMemo(() => (present ? present.split(SEP) : []), [present]);
}

function observeMountedIds(
  wanted: string,
  setPresent: (update: (prev: string) => string) => void,
): (() => void) | undefined {
  if (typeof document === "undefined") return;
  const ids = wanted.split(SEP).filter(Boolean);
  const sync = () => setPresent((prev) => nextOrSame(prev, ids));
  sync();
  if (ids.length === 0) return;
  return watchReportMain(sync);
}

function nextOrSame(prev: string, ids: readonly string[]): string {
  const next = ids
    .filter((id) => document.getElementById(id) !== null)
    .join(SEP);
  return next === prev ? prev : next;
}

/** Escopado ao `#report-main` para não reagir a tooltip/popover do chrome. */
function watchReportMain(sync: () => void): () => void {
  let frame = 0;
  const onMutation = () => {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      sync();
    });
  };
  const observer = new MutationObserver(onMutation);
  const root = document.getElementById("report-main") ?? document.body;
  observer.observe(root, { childList: true, subtree: true });
  return () => {
    observer.disconnect();
    if (frame) window.cancelAnimationFrame(frame);
  };
}
