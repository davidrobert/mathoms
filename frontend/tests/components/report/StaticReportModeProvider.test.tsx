/**
 * ADR-124 · Fase 11.1 — StaticReportModeProvider.
 *
 * Render estático (SSR `/api/reports/[id]/export`) precisa funcionar sem
 * hooks de router. Este teste garante que:
 * - O provider expõe o `mode` recebido por prop.
 * - `setMode` é no-op (não explode, não troca state).
 * - `renderToStaticMarkup` completa sem erro (não toca `next/navigation`).
 */
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { render, screen } from "@testing-library/react";
import { StaticReportModeProvider } from "@/components/report/StaticReportModeProvider";
import { useReportMode } from "@/components/report/ReportModeContext";

function Probe() {
  const { mode, setMode } = useReportMode();
  return (
    <button type="button" onClick={() => setMode("estrategico")}>
      mode:{mode}
    </button>
  );
}

describe("StaticReportModeProvider", () => {
  it("expõe mode da prop", () => {
    render(
      <StaticReportModeProvider mode="estrategico">
        <Probe />
      </StaticReportModeProvider>,
    );
    expect(screen.getByRole("button")).toHaveTextContent("mode:estrategico");
  });

  it("setMode é no-op (não explode)", () => {
    render(
      <StaticReportModeProvider mode="estrategico">
        <Probe />
      </StaticReportModeProvider>,
    );
    const btn = screen.getByRole("button");
    expect(() => btn.click()).not.toThrow();
    expect(btn).toHaveTextContent("mode:estrategico");
  });

  it("renderToStaticMarkup funciona sem next/navigation", () => {
    const html = renderToStaticMarkup(
      <StaticReportModeProvider mode="estrategico">
        <Probe />
      </StaticReportModeProvider>,
    );
    expect(html).toContain("mode:estrategico");
  });
});
