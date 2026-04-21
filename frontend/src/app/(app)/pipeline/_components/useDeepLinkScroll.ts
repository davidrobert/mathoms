"use client";

import { useEffect, useState } from "react";
import type { PipelineRunResponse } from "@/lib/api";

/** F11.4a — deep link desde o relatório: `/pipeline?run=<uuid>`.
 *  Quando presente, scrolla até o card correspondente e destaca por 3s. */
export function useDeepLinkScroll(runs: PipelineRunResponse[], loading: boolean) {
  const [highlightedRunId, setHighlightedRunId] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    const params = new URLSearchParams(window.location.search);
    const runParam = params.get("run");
    if (!runParam) return;
    requestAnimationFrame(() => {
      const el = document.getElementById(`pipeline-run-${runParam}`);
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      setHighlightedRunId(runParam);
      setTimeout(() => setHighlightedRunId(null), 3000);
      const url = new URL(window.location.href);
      url.searchParams.delete("run");
      const next = url.pathname + (url.search ? url.search : "");
      window.history.replaceState({}, "", next);
    });
  }, [loading, runs]);

  return highlightedRunId;
}
