import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PartialRunBanner } from "@/app/(app)/pipeline/_components/PartialRunBanner";
import { ActiveRunCard } from "@/app/(app)/pipeline/_components/ActiveRunCard";
import { makePartialRun, makeRun, makeStageLog } from "../factories";

vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

describe("<PartialRunBanner />", () => {
  it("declara a lacuna e oferece o relatório", () => {
    render(<PartialRunBanner run={makePartialRun({ report_id: "report-5" })} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Relatório gerado, sem o parecer do planejador.",
    );
    expect(screen.getByRole("link", { name: /ver relatório/i })).toHaveAttribute(
      "href",
      "/reports/report-5",
    );
  });

  it("afirma que o restante está completo quando é verdade", () => {
    render(<PartialRunBanner run={makePartialRun()} />);
    expect(screen.getByRole("status")).toHaveTextContent(/restante da análise está completo/);
  });

  // O banner de free tier, logo ao lado, diz que documentos podem estar
  // incompletos — a reasseguração fixa contradiria o vizinho.
  it("cala a reasseguração quando o mesmo run pulou etapas por free tier", () => {
    const run = makePartialRun({
      stage_logs: [
        makeStageLog({ stage: "extract_with_llm", status: "skipped_free_tier" }),
        makeStageLog({ stage: "review_finances_holistic", status: "degraded" }),
      ],
    });
    render(<PartialRunBanner run={run} />);
    expect(screen.getByRole("status")).not.toHaveTextContent(
      /restante da análise está completo/,
    );
  });

  it("sem callback de retomada, não oferece botão", () => {
    render(<PartialRunBanner run={makePartialRun()} />);
    expect(screen.queryByRole("button", { name: /Reprocessar/ })).not.toBeInTheDocument();
  });

  it("dispensa só aparece quando dispensável", () => {
    const { rerender } = render(<PartialRunBanner run={makePartialRun()} redirecting />);
    expect(screen.queryByRole("button", { name: /Fechar aviso/ })).not.toBeInTheDocument();
    rerender(<PartialRunBanner run={makePartialRun()} onDismiss={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Fechar aviso/ })).toBeInTheDocument();
  });
});

describe("<ActiveRunCard /> — contador de etapas conhece `degraded`", () => {
  it("etapa degradada conta como terminada no contador de detalhes", () => {
    const run = makeRun({
      status: "running",
      current_stage: "validate_cross",
      stage_logs: [
        makeStageLog({ stage: "analyze_finances", status: "completed" }),
        makeStageLog({ stage: "generate_narratives", status: "degraded" }),
      ],
    });
    render(
      <ActiveRunCard
        run={run}
        wsStatus="connected"
        lastWsEventRef={{ current: Date.now() } as any}
        lastProgressEventRef={{ current: Date.now() } as any}
        lastActivityByStageRef={{ current: {} } as any}
        liveStageActivity={null}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/Ver detalhes técnicos \(2\/2 etapas\)/)).toBeInTheDocument();
  });
});
