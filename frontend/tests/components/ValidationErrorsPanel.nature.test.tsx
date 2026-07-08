/**
 * A32.l6 PR2 — selo de natureza no card + valor ofensor traduzido.
 * WCAG: distinção legível sem cor (ícone + rótulo + forma); decisão Q4:
 * selo na review principal, warnings não-bloqueantes incluídos.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValidationErrorsPanel } from "@/app/(app)/pipeline/runs/[runId]/reviews/_components/ValidationErrorsPanel";
import type { ValidationIssue } from "@/lib/api/pipeline";

function issue(over: Partial<ValidationIssue>): ValidationIssue {
  return {
    code: "dedup.sentinel_period",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "msg tecnica",
    ...over,
  };
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

describe("<ValidationErrorsPanel /> — selo de natureza (A32.l6 PR2)", () => {
  it("card de code nosso mostra selo com rótulo e ícone (não só cor)", () => {
    const { container } = render(
      <ValidationErrorsPanel issues={[issue({})]} errorsLegacy={null} />,
    );
    const badge = screen.getByText("Falha na nossa leitura");
    expect(badge).toBeInTheDocument();
    const badgeEl = badge.closest("[data-slot='badge']") ?? badge.parentElement!;
    expect(badgeEl.querySelector("svg")).not.toBeNull();
    expect(container.textContent).toContain("Falha na nossa leitura");
  });

  it("warning não-bloqueante também recebe selo (Q4: sem aba separada)", () => {
    render(
      <ValidationErrorsPanel
        issues={[
          issue({
            code: "domain.temporal_gap",
            severity: "warning",
            context: { artifact_key: "" },
          }),
        ]}
        errorsLegacy={null}
      />,
    );
    expect(screen.getByText("Documento faltando")).toBeInTheDocument();
  });

  it("hedge 'provável' nos codes de atribuição incerta", () => {
    render(
      <ValidationErrorsPanel
        issues={[issue({ code: "extract.missing_required_field" })]}
        errorsLegacy={null}
      />,
    );
    expect(
      screen.getByText("Provável falha na nossa leitura"),
    ).toBeInTheDocument();
  });

  it("offending_value cru é traduzido no corpo visível; raw fica nos detalhes", () => {
    const { container } = render(
      <ValidationErrorsPanel
        issues={[
          issue({
            code: "extract.missing_required_field",
            context: {
              artifact_key: "f861374a39e9_c6bank_extratoconta_202604",
              offending_value: "banco=''",
            },
          }),
        ]}
        errorsLegacy={null}
      />,
    );
    const visible = visibleText(container);
    expect(visible).toContain(
      "O campo de instituição veio em branco na nossa leitura.",
    );
    expect(visible).not.toContain("banco=''");
    expect(container.textContent).toContain("banco=''");
  });

  it("datas ISO do offending_value aparecem em formato humano", () => {
    const { container } = render(
      <ValidationErrorsPanel
        issues={[
          issue({
            code: "domain.temporal_gap",
            severity: "warning",
            context: {
              artifact_key: "",
              offending_value:
                "9 dias sem extrato em c6bank/corrente/-/BRL (2026-04-30 → 2026-05-09)",
            },
          }),
        ]}
        errorsLegacy={null}
      />,
    );
    const visible = visibleText(container);
    expect(visible).toContain("30/04/2026");
    expect(visible).not.toContain("2026-04-30");
  });
});
