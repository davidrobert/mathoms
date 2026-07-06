/**
 * Integration tests — `/pipeline/runs/[runId]/reviews` (ADR-158).
 *
 * Cobre:
 * - Lista renderiza pending vs já aprovados.
 * - Detalhe carrega `original_output_json` no viewer.
 * - Submit aprovar chama POST com action:"approve".
 * - Submit editar serializa edição válida; bloqueia submit se JSON inválido.
 * - 409 em concorrência → estado atualizado, toast informativo (não erro).
 * - Resume explícito: aparece quando nenhuma review fica pending, chama POST
 *   /resume só após clique do usuário, mostra erro inline em falha.
 *
 * Mocks: WorkspaceProvider + useRouter (Next 13 app router) — convenção
 * existente em `pipeline.test.tsx`.
 */
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";

const pushMock = vi.fn();
const paramsMock = vi.fn<() => { runId: string; reviewId?: string }>(() => ({
  runId: "run-1",
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => paramsMock(),
  usePathname: () => "/pipeline",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useWorkspace: () => ({
    workspace: {
      id: "ws-1",
      name: "Workspace",
      family_surname: "Teste",
      role: "owner" as const,
      joined_at: "2026-01-01T00:00:00.000Z",
    },
    workspaces: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

import ReviewListPage from "@/app/(app)/pipeline/runs/[runId]/reviews/page";
import ReviewDetailPage from "@/app/(app)/pipeline/runs/[runId]/reviews/[reviewId]/page";

const REVIEW_PENDING = {
  id: "rev-1",
  pipeline_run_id: "run-1",
  stage: "extract_irpf_full",
  status: "pending" as const,
  original_output_json: { campo_a: "valor", campo_b: 42 },
  edited_output_json: null,
  validation_errors: "campo_a: obrigatório\ncampo_b: deve ser positivo",
  created_at: "2026-04-15T12:00:00Z",
  reviewed_at: null,
};
const REVIEW_APPROVED = {
  ...REVIEW_PENDING,
  id: "rev-2",
  status: "approved" as const,
  reviewed_at: "2026-04-15T13:00:00Z",
};
const RUN_NEEDS_REVIEW = {
  id: "run-1",
  workspace_id: "ws-1",
  status: "needs_review",
  current_stage: null,
  failed_at_stage: null,
  paused_at_stage: "extract_irpf_full",
  tier_at_run: "free",
  total_documents: 1,
  incremental: false,
  celery_task_id: null,
  started_at: "2026-04-15T11:00:00Z",
  completed_at: null,
  stage_logs: [],
  report_id: null,
};

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  pushMock.mockReset();
  paramsMock.mockReset();
  paramsMock.mockReturnValue({ runId: "run-1", reviewId: "rev-1" });
});

describe("ReviewListPage", () => {
  it("renderiza items pending e approved com badges distintos", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_PENDING, REVIEW_APPROVED]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    render(<ReviewListPage />);
    await waitFor(() =>
      expect(screen.getAllByLabelText(/Status:/)).toHaveLength(2),
    );
    expect(screen.getByLabelText("Status: Pendente")).toBeInTheDocument();
    expect(screen.getByLabelText("Status: Aprovado")).toBeInTheDocument();
  });

  it("todas reviews não-pending → card 'Tudo pronto' aparece com CTA retomar", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_APPROVED]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    render(<ReviewListPage />);
    expect(
      await screen.findByText(/Tudo pronto para continuar/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Retomar pipeline/i }),
    ).toBeInTheDocument();
  });

  it("ainda há review pending → card 'Tudo pronto' não aparece", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_PENDING, REVIEW_APPROVED]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    render(<ReviewListPage />);
    await waitFor(() =>
      expect(screen.getByLabelText("Status: Pendente")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(/Tudo pronto para continuar/i),
    ).not.toBeInTheDocument();
  });

  it("clique em Retomar chama POST /resume e redireciona", async () => {
    let resumeCalled = false;
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_APPROVED]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
      http.post(
        "/api/v1/workspaces/:wsId/pipeline/runs/:runId/resume",
        () => {
          resumeCalled = true;
          return HttpResponse.json({ ...RUN_NEEDS_REVIEW, status: "running" });
        },
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    const user = userEvent.setup();
    render(<ReviewListPage />);
    const btn = await screen.findByRole("button", { name: /Retomar pipeline/i });
    await user.click(btn);
    await waitFor(() => expect(resumeCalled).toBe(true));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/pipeline"));
  });

  it("resume falha → mensagem de erro inline + botão 'Tentar novamente'", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_APPROVED]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
      http.post(
        "/api/v1/workspaces/:wsId/pipeline/runs/:runId/resume",
        () => HttpResponse.json({ detail: "worker offline" }, { status: 503 }),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    const user = userEvent.setup();
    render(<ReviewListPage />);
    const btn = await screen.findByRole("button", { name: /Retomar pipeline/i });
    await user.click(btn);
    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(/worker offline/i);
    expect(
      screen.getByRole("button", { name: /Tentar novamente/i }),
    ).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("estado vazio → renderiza CTA voltar ao pipeline", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([]),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json({ ...RUN_NEEDS_REVIEW, status: "completed" }),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    render(<ReviewListPage />);
    expect(
      await screen.findByText(/Nenhuma revisão pendente/i),
    ).toBeInTheDocument();
  });

  it("erro de carregamento → CTA Tentar de novo", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId", () =>
        HttpResponse.json(RUN_NEEDS_REVIEW),
      ),
    );
    paramsMock.mockReturnValue({ runId: "run-1" });
    render(<ReviewListPage />);
    expect(
      await screen.findByRole("button", { name: /Tentar de novo/i }),
    ).toBeInTheDocument();
  });
});

describe("ReviewDetailPage", () => {
  it("h1 orientado a tarefa + JSON atrás de details (A29.l1)", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_PENDING]),
      ),
    );
    render(<ReviewDetailPage />);
    expect(
      await screen.findByRole("heading", {
        name: /Conferir 2 itens antes de continuar/i,
      }),
    ).toBeInTheDocument();
    // JSON continua acessível, mas atrás do details "avançado".
    expect(
      screen.getByText(/Ver dados extraídos \(avançado\)/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Output original do stage/i)).toHaveTextContent(
      /campo_a/,
    );
  });

  it("aprovar com erros: confirma consequência e chama POST action:'approve'", async () => {
    let body: unknown = null;
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_PENDING]),
      ),
      http.post(
        "/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews/:reviewId",
        async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({ ...REVIEW_PENDING, status: "approved" });
        },
      ),
    );
    const user = userEvent.setup();
    render(<ReviewDetailPage />);
    // Ação primária é editar; seguir sem corrigir é secundária com consequência.
    const btn = await screen.findByRole("button", {
      name: /Continuar sem corrigir \(2 pendências\)/i,
    });
    expect(btn).toHaveAttribute("aria-describedby", "review-approve-consequence");
    await user.click(btn);
    // ConfirmDialog: erro pendente nunca é 1-clique.
    await user.click(await screen.findByRole("button", { name: /Continuar assim/i }));
    await waitFor(() => expect(body).not.toBeNull());
    expect((body as { action: string }).action).toBe("approve");
  });

  it("18 linhas legacy duplicadas → 2 grupos com contador, sem texto repetido", async () => {
    const lines = [
      ...Array(7).fill(
        "periodo implausivel na normalizacao E3; documento requer revisao",
      ),
      ...Array(11).fill(
        "extrato sem banco determinavel; documento requer revisao",
      ),
    ].join("\n");
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([
          { ...REVIEW_PENDING, stage: "reconcile_transactions", validation_errors: lines },
        ]),
      ),
    );
    render(<ReviewDetailPage />);
    expect(
      await screen.findByRole("heading", {
        name: /Conferir 18 itens antes de continuar/i,
      }),
    ).toBeInTheDocument();
    // 2 grupos, cada mensagem aparece 1× (no summary), não 18 cards.
    expect(
      screen.getAllByText(/periodo implausivel na normalizacao E3/i),
    ).toHaveLength(1);
    expect(
      screen.getAllByText(/extrato sem banco determinavel/i),
    ).toHaveLength(1);
    // Contadores acessíveis no summary do grupo.
    expect(
      screen.getByLabelText(/periodo implausivel.*7 ocorrências.*aviso/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/extrato sem banco.*11 ocorrências.*aviso/i),
    ).toBeInTheDocument();
    // Stage de ingestão: botão fala em documentos + consequência visível.
    expect(
      screen.getByRole("button", { name: /Continuar sem estes 18 documentos/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/ficam de fora do relatório/i),
    ).toBeInTheDocument();
  });

  it("editor: JSON inválido bloqueia submit", async () => {
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () =>
        HttpResponse.json([REVIEW_PENDING]),
      ),
    );
    const user = userEvent.setup();
    render(<ReviewDetailPage />);
    const editBtn = await screen.findByRole("button", { name: /Editar e continuar/i });
    await user.click(editBtn);
    const textarea = await screen.findByLabelText(/Editar output do stage/i);
    await user.clear(textarea);
    // user.type interpreta `{` como modifier — escapar com `{{`.
    await user.type(textarea, "{{ campo_a");
    const saveBtn = await screen.findByRole("button", {
      name: /Salvar e continuar/i,
    });
    expect(saveBtn).toBeDisabled();
    expect(textarea).toHaveAttribute("aria-invalid", "true");
  });

  it("409 em submit → estado atualizado (conferência vira approved), sem erro", async () => {
    let firstCall = true;
    server.use(
      http.get("/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews", () => {
        const review = firstCall
          ? REVIEW_PENDING
          : { ...REVIEW_PENDING, status: "approved" };
        firstCall = false;
        return HttpResponse.json([review]);
      }),
      http.post(
        "/api/v1/workspaces/:wsId/pipeline/runs/:runId/reviews/:reviewId",
        () =>
          HttpResponse.json({ detail: "Review já processado" }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    render(<ReviewDetailPage />);
    const btn = await screen.findByRole("button", {
      name: /Continuar sem corrigir/i,
    });
    await user.click(btn);
    await user.click(await screen.findByRole("button", { name: /Continuar assim/i }));
    // Após 409 + refetch, review aparece como approved — ações somem,
    // mensagem de "já concluída" toma o lugar.
    expect(
      await screen.findByText(/já foi concluída/i),
    ).toBeInTheDocument();
  });
});
