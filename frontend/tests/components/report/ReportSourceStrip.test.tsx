/**
 * Colofão do relatório — a proveniência é fato do RUN, nunca do viewer.
 *
 * A "Revisão do sistema" (executor_revision, ADR-362) substitui o card
 * "Versão" da capa, que mostrava pkg.version do frontend no momento da
 * visualização. Ausência renderiza "—" — nunca um valor fabricado.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReportSourceStrip } from "@/components/report/ReportSourceStrip";

function renderStrip(executorRevision: string | null) {
  return render(
    <ReportSourceStrip
      reportPeriod="2026-04"
      analysisPeriod={null}
      generatedAtIso="2026-04-25T12:00:00Z"
      pipelineRunId="run-fixture"
      executorRevision={executorRevision}
      sourceDocumentCount={3}
      consumedDocumentCount={3}
    />,
  );
}

describe("ReportSourceStrip — Revisão do sistema", () => {
  it("mostra a revisão do executor quando o run a declarou", () => {
    renderStrip("a1b2c3d4e5f6");
    expect(screen.getByText(/Revisão do sistema/)).toBeInTheDocument();
    expect(screen.getByText("a1b2c3d4e5f6")).toBeInTheDocument();
  });

  it("renderiza — quando o executor não declarou (nunca fabrica)", () => {
    renderStrip(null);
    expect(screen.getByText(/Revisão do sistema/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
