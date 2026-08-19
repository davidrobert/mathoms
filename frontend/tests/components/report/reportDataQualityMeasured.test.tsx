/**
 * PD-6 (RV6-22) — o banner não afirma "sem pendências" sobre número que não mediu.
 *
 * Diferente de `ReportDataQualityBanner.test.tsx`, que mocka os hooks e testa a
 * derivação, aqui os hooks são os REAIS: o que está sob teste é o caminho de
 * falha de fetch, que colapsava para `0` e ficava indistinguível de zero medido.
 *
 * O controle positivo (fetch OK com zero real → a barra aparece) é obrigatório:
 * sem ele, `not.toBeInTheDocument()` passaria também se o banner não montasse.
 */
import { describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";

import { ReportDataQualityBanner } from "@/components/report/ReportDataQualityBanner";
import type { ReportAnalysisData } from "@/lib/api";

const listDocuments = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/documents")>()),
  listDocuments,
}));

/** Payload E5 sem nenhum sinal derivado — isola o sinal client-side sob teste. */
function limpoData(): ReportAnalysisData {
  return { fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } } };
}

/** Documento sintético já classificado e extraído — não conta como incerto. */
function documentoResolvido() {
  return {
    id: "doc-1",
    status: "ready",
    needs_review: false,
    classification_confidence: 0.99,
    pipeline_e2_extract_ok: true,
  };
}

function renderBanner() {
  render(
    <ReportDataQualityBanner
      data={limpoData()}
      workspaceId="ws-1"
      runOutcome="complete"
    />,
  );
}

/** Drena os microtasks do fetch mockado e aplica o setState resultante. */
async function flushFetch() {
  await act(async () => {});
}

describe("<ReportDataQualityBanner /> — contagem medida vs. não medida", () => {
  it("fetch falha: NÃO afirma 'sem pendências'", async () => {
    listDocuments.mockRejectedValue(new Error("boom"));

    renderBanner();
    await flushFetch();

    expect(listDocuments).toHaveBeenCalledWith("ws-1");
    expect(screen.queryByTestId("data-quality-clean")).not.toBeInTheDocument();
    // E também não inventa pendência: não medir não é achar problema.
    expect(screen.queryByTestId("data-quality-banner")).not.toBeInTheDocument();
  });

  it("controle positivo — fetch OK com zero real: continua afirmando", async () => {
    listDocuments.mockResolvedValue({ documents: [documentoResolvido()] });

    renderBanner();
    await flushFetch();

    const bar = screen.getByTestId("data-quality-clean");
    expect(bar.textContent).toMatch(/sem pendências/);
  });
});
