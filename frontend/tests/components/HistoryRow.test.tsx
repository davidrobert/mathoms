/**
 * A40.l21 — a linha do histórico de um run degradado não pode oferecer
 * afordância de falha, e a ação primária ("Ver relatório") não pode depender
 * de hover: não existe hover em toque, e o link não era revelado no foco.
 */
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";

import { HistoryRow } from "@/app/(app)/pipeline/_components/HistoryRow";
import { makePartialRun, makeRun, makeStageLog } from "../factories";

/** A40.l22 — run que ENTREGOU o parecer com itens retidos: `completed`, sem
 *  stage degradado. Sem os dois, o teste passaria pelo caminho do
 *  `partial_failure`, que já tinha linha de contexto antes desta lane. */
function runComParecerParcial(dropped = 2) {
  return makeRun({
    status: "completed",
    report_id: "report-parcial-1",
    stage_logs: [
      makeStageLog({ stage: "analyze_finances", status: "completed" }),
      makeStageLog({
        stage: "review_finances_holistic",
        status: "completed",
        output_summary: { evidencia_verification: { items_dropped: dropped } },
      }),
    ],
  });
}

vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

function assertNoSeriousViolations(results: any) {
  const blocking = (results.violations ?? []).filter(
    (v: any) => v.impact === "critical" || v.impact === "serious",
  );
  if (blocking.length > 0) {
    const msg = blocking
      .map((v: any) => `  - [${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} nodes)`)
      .join("\n");
    throw new Error(`a11y violations (critical/serious):\n${msg}`);
  }
}

function renderRow(run: ReturnType<typeof makeRun>) {
  return render(
    <HistoryRow run={run} onRetry={vi.fn()} onRetryFrom={vi.fn()} triggering={false} />,
  );
}

describe("<HistoryRow /> — run parcial (ADR-357)", () => {
  it("badge diz 'Concluído com ressalva', não 'Parcial' nem 'Falhou'", () => {
    renderRow(makePartialRun());
    expect(screen.getByText("Concluído com ressalva")).toBeInTheDocument();
    expect(screen.queryByText(/Falhou/)).not.toBeInTheDocument();
  });

  it("linha de contexto nomeia a lacuna, sem dizer que falhou", () => {
    renderRow(makePartialRun());
    expect(
      screen.getByText("Relatório gerado, sem o parecer do planejador."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Falhou antes de iniciar uma etapa/)).not.toBeInTheDocument();
  });

  it("oferece 'Ver relatório' — afordância positiva, sem hover", () => {
    const run = makePartialRun({ report_id: "report-77" });
    renderRow(run);
    const link = screen.getByRole("link", { name: /ver relatório/i });
    expect(link).toHaveAttribute("href", "/reports/report-77");
    expect(link.className).not.toMatch(/opacity-0/);
  });

  it("não oferece 'Reprocessar' — o run entregou e re-rodar re-paga tudo", () => {
    renderRow(makePartialRun());
    expect(screen.queryByRole("button", { name: /Reprocessar/i })).not.toBeInTheDocument();
  });

  it("não pinta a borda de perda", () => {
    const { container } = renderRow(makePartialRun());
    expect(container.querySelector(".border-loss\\/20")).toBeNull();
  });

  it("nenhum texto vermelho de perda na linha", () => {
    const { container } = renderRow(makePartialRun());
    expect(container.querySelector(".text-loss")).toBeNull();
  });
});

describe("<HistoryRow /> — regressão: run falhado continua tratado como falha", () => {
  const failedRun = makeRun({
    status: "failed",
    failed_at_stage: "reconcile_transactions",
    report_id: null,
    stage_logs: [makeStageLog({ stage: "reconcile_transactions", status: "failed" })],
  });

  it("badge 'Falhou' + contexto da etapa + ação Reprocessar", () => {
    renderRow(failedRun);
    expect(screen.getByText("Falhou")).toBeInTheDocument();
    expect(screen.getByText(/Falhou em/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reprocessar/i })).toBeInTheDocument();
  });

  it("mantém a borda de perda", () => {
    const { container } = renderRow(failedRun);
    expect(container.querySelector(".border-loss\\/20")).not.toBeNull();
  });
});

describe("<HistoryRow /> — run completed não regride", () => {
  it("'Ver relatório' deixou de ser hover-only também para completed", () => {
    renderRow(makeRun({ status: "completed", report_id: "report-9" }));
    const link = screen.getByRole("link", { name: /ver relatório/i });
    expect(link.className).not.toMatch(/opacity-0/);
  });
});

describe("<HistoryRow /> — a11y com run parcial", () => {
  afterEach(() => {
    document.documentElement.classList.remove("dark");
    vi.restoreAllMocks();
  });

  it("light: 0 violações critical/serious", async () => {
    const { container } = renderRow(makePartialRun());
    assertNoSeriousViolations(await axe(container));
  });

  it("dark: 0 violações critical/serious", async () => {
    document.documentElement.classList.add("dark");
    const { container } = renderRow(makePartialRun());
    assertNoSeriousViolations(await axe(container));
  });
});

describe("<HistoryRow /> — ícone distingue os dois status warning", () => {
  beforeEach(() => vi.clearAllMocks());

  it("parcial e needs_review não são distinguíveis só por cor", () => {
    const { container: partial } = renderRow(makePartialRun());
    const { container: review } = renderRow(
      makeRun({ status: "needs_review", report_id: null }),
    );
    const iconOf = (c: HTMLElement) =>
      c.querySelector("[data-slot='badge'] svg")?.getAttribute("class") ?? "";
    expect(iconOf(partial)).not.toBe("");
    expect(iconOf(review)).not.toBe("");
    expect(partial.querySelector("[data-slot='badge'] svg")?.outerHTML).not.toBe(
      review.querySelector("[data-slot='badge'] svg")?.outerHTML,
    );
  });
});

describe("<HistoryRow /> — parecer parcialmente retido @A40.l22", () => {
  beforeEach(() => vi.clearAllMocks());

  it("run `completed` com itens retidos ganha linha de contexto", () => {
    renderRow(runComParecerParcial(2));
    const linha = screen.getByTestId("history-parecer-retido");
    expect(linha).toHaveTextContent("2 itens do parecer retidos na conferência");
    expect(linha).toHaveTextContent("o parecer deste relatório está incompleto");
  });

  it("badge segue 'Concluído' — o run entregou, não é ressalva de execução", () => {
    renderRow(runComParecerParcial(2));
    expect(screen.queryByText(/Falhou/)).not.toBeInTheDocument();
    expect(
      screen.queryByText("Relatório gerado, sem o parecer do planejador."),
    ).not.toBeInTheDocument();
  });

  it("run íntegro não ganha linha — o gate `completed` tinha de ser aberto", () => {
    // Sem o termo novo em `hasContextLine`, a linha existiria e nunca
    // renderizaria; sem este par negativo, o teste acima passaria mesmo se
    // a linha aparecesse em TODO run.
    renderRow(makeRun({ status: "completed", report_id: "report-ok" }));
    expect(screen.queryByTestId("history-parecer-retido")).not.toBeInTheDocument();
  });

  it("não vaza vocabulário de operador do `output_summary`", () => {
    const run = runComParecerParcial(2);
    run.stage_logs[1].output_summary = {
      evidencia_verification: { items_dropped: 2 },
      reason: "evidencia unverified (severidade alta): risco:3",
      retention_reason: "parecer.citacao_nao_confirmada",
      reason_class: "llm_output_invalid",
    };
    const { container } = renderRow(run);
    const html = container.innerHTML;
    for (const leak of [
      "evidencia unverified",
      "parecer.citacao_nao_confirmada",
      "llm_output_invalid",
      "items_dropped",
    ]) {
      expect(html).not.toContain(leak);
    }
    expect(html).not.toMatch(/risco:\s*\d/i);
  });

  it("a11y: linha nova sem violação critical/serious", async () => {
    const { container } = renderRow(runComParecerParcial(2));
    assertNoSeriousViolations(await axe(container));
  });
});
