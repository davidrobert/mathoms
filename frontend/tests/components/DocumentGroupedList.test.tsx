/**
 * A32.l6 PR3 — visão por documento default + ações MVP (Q3).
 * "Ver documento" navega para o documento; "Dispensar" esconde o card
 * (client-side, restaurável). Botão "Reprocessar" NÃO existe (dead UI
 * proibida — decisão Q3).
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { ValidationErrorsPanel } from "@/app/(app)/pipeline/runs/[runId]/reviews/_components/ValidationErrorsPanel";
import type { ValidationIssue } from "@/lib/api/pipeline";

function issue(over: Partial<ValidationIssue>): ValidationIssue {
  return {
    code: "dedup.sentinel_period",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "msg",
    ...over,
  };
}

function docIssue(docId: string, code: string, severity: "error" | "warning" = "error") {
  return issue({
    code,
    severity,
    context: {
      document_id: docId,
      artifact_key: `f861374a39e9_c6bank_extratoconta_${docId}`,
      doc_bank_code: "c6bank",
      doc_type: "bank_statement",
      doc_e0_type: "extratoconta",
      doc_period: "202604",
      offending_value: "banco=''",
    },
  });
}

const ORPHAN_3_CODES = [
  docIssue("doc-orfao", "extract.missing_required_field"),
  docIssue("doc-orfao", "dedup.sentinel_period"),
  docIssue("doc-orfao", "domain.anachronic_transaction", "warning"),
];

describe("<ValidationErrorsPanel /> — visão por documento (A32.l6 PR3)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("visão por documento é o default; 3 codes do mesmo doc = 1 card", () => {
    render(
      <ValidationErrorsPanel
        issues={ORPHAN_3_CODES}
        errorsLegacy={null}
        reviewId="rev-1"
      />,
    );
    expect(screen.getByText("1 documento com itens para conferir")).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Documentos com itens para conferência" })
        .children,
    ).toHaveLength(1);
  });

  it("toggle 'Por tipo de item' troca para a visão por code", async () => {
    const user = userEvent.setup();
    render(
      <ValidationErrorsPanel
        issues={ORPHAN_3_CODES}
        errorsLegacy={null}
        reviewId="rev-1"
      />,
    );
    await user.click(screen.getByRole("button", { name: "Por tipo de item" }));
    expect(
      screen.getByRole("list", { name: "Itens agrupados para conferência" }).children,
    ).toHaveLength(3);
  });

  it("'Ver documento' aponta para o documento; 'Reprocessar' não existe", () => {
    render(
      <ValidationErrorsPanel
        issues={ORPHAN_3_CODES}
        errorsLegacy={null}
        reviewId="rev-1"
      />,
    );
    expect(screen.getByRole("link", { name: "Ver documento" })).toHaveAttribute(
      "href",
      "/documents?doc=doc-orfao",
    );
    expect(screen.queryByText(/Reprocessar/i)).not.toBeInTheDocument();
  });

  it("'Dispensar' esconde o card e permite restaurar; persiste por review", async () => {
    const user = userEvent.setup();
    render(
      <ValidationErrorsPanel
        issues={ORPHAN_3_CODES}
        errorsLegacy={null}
        reviewId="rev-1"
      />,
    );
    await user.click(screen.getByRole("button", { name: "Dispensar" }));
    expect(
      screen.queryByRole("link", { name: "Ver documento" }),
    ).not.toBeInTheDocument();
    expect(window.localStorage.getItem("reviews:dismissed:rev-1")).toContain(
      "doc:doc-orfao",
    );
    await user.click(
      screen.getByRole("button", { name: /1 item dispensado · restaurar/ }),
    );
    expect(screen.getByRole("link", { name: "Ver documento" })).toBeInTheDocument();
    expect(window.localStorage.getItem("reviews:dismissed:rev-1")).toBeNull();
  });

  it("issues sem referência de documento (E1/E1.5) caem direto na visão por code", () => {
    render(
      <ValidationErrorsPanel
        issues={[issue({ code: "e1.members.empty", context: {} })]}
        errorsLegacy={null}
        reviewId="rev-1"
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Por documento" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Itens agrupados para conferência" }),
    ).toBeInTheDocument();
  });
});
