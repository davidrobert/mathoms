/**
 * A32.l6 PR1 — card de review com identidade legível.
 * Critério: zero hash sha256 cru no corpo visível; artifact_key cru
 * só sob "Detalhes técnicos" (colapsado).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValidationErrorsPanel } from "@/app/(app)/pipeline/runs/[runId]/reviews/_components/ValidationErrorsPanel";
import type { ValidationIssue } from "@/lib/api/pipeline";

const HASHED_KEY = "f861374a39e9_c6bank_extratoconta_202604_202604";

function issue(over: Partial<ValidationIssue>): ValidationIssue {
  return {
    code: "dedup.sentinel_period",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "periodo implausivel na normalizacao E3",
    ...over,
  };
}

function resolvedIssue(): ValidationIssue {
  return issue({
    context: {
      artifact_key: HASHED_KEY,
      document_id: "doc-1",
      doc_bank_code: "c6bank",
      doc_type: "bank_statement",
      doc_e0_type: "extratoconta",
      doc_period: "202604",
      offending_value: "period=999999",
      expected: "YYYYMM plausivel",
    },
  });
}

/** Texto visível = fora de <details> fechado (summary continua visível). */
function visibleText(container: HTMLElement): string {
  const clone = container.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("details:not([open])").forEach((d) => {
    const summary = d.querySelector("summary");
    d.replaceWith(summary ? summary.cloneNode(true) : "");
  });
  return clone.textContent ?? "";
}

describe("<ValidationErrorsPanel /> — identidade legível (A32.l6)", () => {
  it("card com documento resolvido mostra 'Instituição · Tipo · Período'", () => {
    render(<ValidationErrorsPanel issues={[resolvedIssue()]} errorsLegacy={null} />);
    expect(screen.getByText(/C6 Bank/)).toBeInTheDocument();
  });

  it("zero hash sha256 cru no corpo visível do card", () => {
    const { container } = render(
      <ValidationErrorsPanel issues={[resolvedIssue()]} errorsLegacy={null} />,
    );
    expect(visibleText(container)).not.toMatch(/[0-9a-f]{12}_/);
  });

  it("artifact_key cru fica disponível sob 'Detalhes técnicos'", () => {
    const { container } = render(
      <ValidationErrorsPanel issues={[resolvedIssue()]} errorsLegacy={null} />,
    );
    expect(screen.getByText("Detalhes técnicos")).toBeInTheDocument();
    expect(container.textContent).toContain(HASHED_KEY);
  });

  it("ocorrência cross-doc sem artifact_key cai no grupo 'Sequência de contas'", () => {
    render(
      <ValidationErrorsPanel
        issues={[
          issue({
            code: "domain.balance_gap",
            severity: "warning",
            context: { artifact_key: "", offending_value: "gap detectado" },
          }),
        ]}
        errorsLegacy={null}
      />,
    );
    expect(screen.getByText("Sequência de contas")).toBeInTheDocument();
  });

  it("sem identidade resolvida, mostra artifact_key humanizado (sem hash)", () => {
    const { container } = render(
      <ValidationErrorsPanel
        issues={[issue({ context: { artifact_key: HASHED_KEY } })]}
        errorsLegacy={null}
      />,
    );
    expect(
      screen.getByText("c6bank_extratoconta_202604_202604"),
    ).toBeInTheDocument();
    expect(visibleText(container)).not.toMatch(/[0-9a-f]{12}_/);
  });
});
