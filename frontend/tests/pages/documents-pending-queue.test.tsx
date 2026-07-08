/**
 * A29.l3 (ADR-308) — inbox de pendências em /documents.
 *
 * Cobre: fila agrupada a partir de reviews pendentes (issues estruturadas da
 * A29.l2), link "Corrigir" → EditDocumentDialog, estado resolvido → retomada
 * explícita, e helper buildQueueGroups (sentinela "N+", fallback legacy).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import DocumentsPage from "@/app/(app)/documents/page";
import { buildQueueGroups } from "@/app/(app)/documents/_components/PendingReviewQueue";
import type { StageReviewResponse } from "@/lib/api";
import { server } from "../mocks/server";
import { makeDocument } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/documents",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

const WS_DOCUMENTS = "/api/v1/workspaces/:workspaceId/documents";
const WS_RUNS = "/api/v1/workspaces/:workspaceId/pipeline/runs";
const WS_REVIEWS = "/api/v1/workspaces/:workspaceId/pipeline/runs/:id/reviews";

const PAUSED_RUN = {
  id: "run-paused",
  workspace_id: "ws-1",
  status: "needs_review",
  current_stage: null,
  failed_at_stage: null,
  paused_at_stage: "reconcile_transactions",
  tier_at_run: "free",
  total_documents: 2,
  incremental: false,
  celery_task_id: null,
  started_at: "2026-07-06T12:00:00Z",
  completed_at: null,
  stage_logs: [],
  report_id: null,
};

function issue(over: Record<string, unknown>) {
  return {
    code: "extract.missing_required_field",
    severity: "error",
    path: null,
    context: {},
    legacy_message: "extrato sem banco determinavel",
    ...over,
  };
}

function pendingReview(issues: unknown[]): unknown {
  return {
    id: "rev-1",
    pipeline_run_id: "run-paused",
    stage: "reconcile_transactions",
    status: "pending",
    original_output_json: {},
    edited_output_json: null,
    validation_errors: "extrato sem banco determinavel",
    validation_issues: issues,
    created_at: "2026-07-06T12:00:00Z",
    reviewed_at: null,
  };
}

describe("PendingReviewQueue em /documents", () => {
  it("run pausado → fila agrupada com copy amigável e link Corrigir", async () => {
    const doc = makeDocument({
      id: "doc-1",
      original_name: "extrato_sem_banco.pdf",
      status: "ready",
    });
    server.use(
      http.get(WS_DOCUMENTS, () =>
        HttpResponse.json({ documents: [doc], total: 1 }),
      ),
      http.get(WS_RUNS, () => HttpResponse.json({ runs: [PAUSED_RUN], total: 1 })),
      http.get(WS_REVIEWS, () =>
        HttpResponse.json([
          pendingReview([
            issue({ context: { document_id: "doc-1", artifact_key: "abc_itau" } }),
            issue({
              code: "domain.balance_gap",
              severity: "warning",
              context: { artifact_key: "outro" },
              legacy_message: "saldo nao continua",
            }),
          ]),
        ]),
      ),
    );
    const user = userEvent.setup();
    render(<DocumentsPage />);

    expect(
      await screen.findByText(/Sua análise está pausada esperando você/i),
    ).toBeInTheDocument();
    // Copy amigável do code (A29.l2), não a string técnica.
    expect(
      screen.getByText("Não lemos a instituição dentro do documento"),
    ).toBeInTheDocument();
    expect(screen.getByText("Saldo não continua entre extratos")).toBeInTheDocument();
    // Amostra com nome do documento resolvido por document_id.
    expect(screen.getByText("extrato_sem_banco.pdf")).toBeInTheDocument();
    // CTA para o gate de retomada (tela de conferência).
    expect(
      screen.getByText(/Concluir conferência/i).closest("a"),
    ).toHaveAttribute("href", "/pipeline/runs/run-paused/reviews");

    // "Corrigir" abre o EditDocumentDialog do documento.
    await user.click(screen.getByRole("button", { name: /^Corrigir$/ }));
    expect(await screen.findByText("Editar classificação")).toBeInTheDocument();
  });

  it("pendências resolvidas → retomada explícita chama /resume", async () => {
    let resumed = false;
    server.use(
      http.get(WS_DOCUMENTS, () => HttpResponse.json({ documents: [], total: 0 })),
      http.get(WS_RUNS, () => HttpResponse.json({ runs: [PAUSED_RUN], total: 1 })),
      http.get(WS_REVIEWS, () =>
        HttpResponse.json([{ ...(pendingReview([]) as object), status: "approved" }]),
      ),
      http.post(
        "/api/v1/workspaces/:workspaceId/pipeline/runs/:id/resume",
        () => {
          resumed = true;
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    const user = userEvent.setup();
    render(<DocumentsPage />);

    expect(
      await screen.findByText(/Tudo resolvido — retomar agora/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Retomar análise/i }));
    await waitFor(() => expect(resumed).toBe(true));
    // Banner some após retomar.
    await waitFor(() =>
      expect(
        screen.queryByText(/Tudo resolvido — retomar agora/i),
      ).not.toBeInTheDocument(),
    );
  });

  it("sem run pausado → fila não renderiza", async () => {
    server.use(
      http.get(WS_DOCUMENTS, () => HttpResponse.json({ documents: [], total: 0 })),
    );
    render(<DocumentsPage />);
    await screen.findByText("Documentos");
    expect(
      screen.queryByText(/análise está pausada/i),
    ).not.toBeInTheDocument();
  });
});

describe("buildQueueGroups", () => {
  const docs = [
    makeDocument({ id: "doc-1", original_name: "a.pdf", status: "ready" }),
  ];

  it("sentinela truncated → contagem exata somada e badge N+", () => {
    const review = pendingReview([
      issue({ context: { document_id: "doc-1" } }),
      issue({ context: { truncated: true, remaining: 30 } }),
    ]) as StageReviewResponse;
    const groups = buildQueueGroups([review], docs);
    expect(groups).toHaveLength(1);
    expect(groups[0]!.count).toBe(31);
    expect(groups[0]!.countIsExact).toBe(false);
    // Sentinela não vira amostra.
    expect(groups[0]!.samples).toHaveLength(1);
    expect(groups[0]!.samples[0]!.label).toBe("a.pdf");
  });

  it("fallback legacy (sem issues estruturadas) agrupa por mensagem", () => {
    const review = pendingReview([]) as StageReviewResponse;
    review.validation_issues = null;
    review.validation_errors = "erro A\nerro A\nerro B";
    const groups = buildQueueGroups([review], docs);
    expect(groups.map((g) => [g.title, g.count])).toEqual([
      ["erro A", 2],
      ["erro B", 1],
    ]);
    expect(groups[0]!.documentIds).toHaveLength(0);
  });
});
