/**
 * Integration tests — Pipeline page (F6.5B.4)
 *
 * Cobre os ramos críticos: empty (sem docs ready), trigger pipeline,
 * erro 400 com banner, lista de runs anteriores, cancel.
 *
 * WebSocket é mockado via `vi.mock` do hook `usePipelineWS` para evitar
 * complexidade de mock de WS aqui (hook tem suite própria em 6.5A.7).
 */
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makePartialRun, makeRun } from "../factories";

// Captor: o mock anterior descartava os callbacks, o que tornava impossível
// exercitar toast/redirect de desfecho terminal (A40.l21).
const h = vi.hoisted(() => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
  push: vi.fn(),
  ws: { opts: null as any },
}));

vi.mock("sonner", () => ({ toast: h.toast }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: h.push }),
  usePathname: () => "/pipeline",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));
vi.mock("@/lib/usePipelineWS", () => ({
  usePipelineWS: (opts: any) => {
    h.ws.opts = opts;
    return { status: "disconnected", lastEvent: null };
  },
}));
vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) => (
    <>{children}</>
  ),
  useWorkspace: () => ({
    workspace: {
      id: "ws-test",
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

import PipelinePage from "@/app/(app)/pipeline/page";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  vi.clearAllMocks();
  h.ws.opts = null;
  server.use(
    http.get("/api/v1/workspaces/:workspaceId/pipeline/new-doc-count", () =>
      HttpResponse.json({ new_count: 0 }),
    ),
  );
});

/** Stubs mínimos para a página montar (5 chamadas em Promise.all no mount). */
function stubPipelinePage(runs: any[], docCount = 2) {
  server.use(
    http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
      HttpResponse.json({ runs, total: runs.length }),
    ),
    http.get("/api/v1/workspaces/:workspaceId/documents", () =>
      HttpResponse.json({
        documents: Array(docCount).fill({ status: "ready" }),
        total: docCount,
      }),
    ),
    http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
      HttpResponse.json({ tier: "premium", has_llm_config: true }),
    ),
  );
}

describe("PipelinePage", () => {
  it("loading: spinner inicial", () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () => new Promise(() => {})),
      http.get("/api/v1/workspaces/:workspaceId/documents", () => HttpResponse.json({ documents: [], total: 0 })),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
    );
    const { container } = render(<PipelinePage />);
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("sem docs ready → mensagem 'Nenhum documento pronto' + link Enviar documentos", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ runs: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({ documents: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
    );
    render(<PipelinePage />);
    expect(await screen.findByText(/Nenhum documento pronto/)).toBeInTheDocument();
    expect(screen.getByText(/Enviar documentos/).closest("a")).toHaveAttribute(
      "href",
      "/documents",
    );
  });

  it("com docs ready → mostra contador + botão 'Processar'", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ runs: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({
          documents: Array(3).fill({ status: "ready" }),
          total: 3,
        }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
    );
    render(<PipelinePage />);
    expect(await screen.findByText(/3/, { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/documento\(s\) pronto/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Processar documentos/ })).toBeInTheDocument();
  });

  it("trigger feliz → adiciona run à lista (skip_llm: !premium)", async () => {
    let triggered = false;
    let triggerBody: any = null;
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ runs: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({
          documents: Array(2).fill({ status: "ready" }),
          total: 2,
        }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
      http.post("/api/v1/workspaces/:workspaceId/pipeline/run", async ({ request }) => {
        triggered = true;
        triggerBody = await request.json();
        return HttpResponse.json(makeRun({ status: "running" }));
      }),
    );
    const user = userEvent.setup();
    render(<PipelinePage />);
    const btn = await screen.findByRole("button", { name: /Processar documentos/ });
    await user.click(btn);

    await waitFor(() => expect(triggered).toBe(true));
    // Free tier → skip_llm true (BUG-007 anti-regression)
    expect(triggerBody.skip_llm).toBe(true);
  });

  it("trigger 400 mostra mensagem de erro", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ runs: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({
          documents: Array(1).fill({ status: "ready" }),
          total: 1,
        }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
      http.post("/api/v1/workspaces/:workspaceId/pipeline/run", () =>
        HttpResponse.json({ detail: "Workspace inválido" }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    render(<PipelinePage />);
    const btn = await screen.findByRole("button", { name: /Processar documentos/ });
    await user.click(btn);
    await waitFor(() =>
      expect(screen.getByText(/Workspace inválido/)).toBeInTheDocument(),
    );
  });

  it("premium tier → trigger envia skip_llm: false (BUG-007)", async () => {
    let triggerBody: any = null;
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ runs: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({
          documents: Array(1).fill({ status: "ready" }),
          total: 1,
        }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "premium", has_llm_config: true }),
      ),
      http.post("/api/v1/workspaces/:workspaceId/pipeline/run", async ({ request }) => {
        triggerBody = await request.json();
        return HttpResponse.json(makeRun({ status: "running" }));
      }),
    );
    const user = userEvent.setup();
    render(<PipelinePage />);
    const btn = await screen.findByRole("button", { name: /Processar documentos/ });
    await user.click(btn);
    await waitFor(() => expect(triggerBody).not.toBeNull());
    expect(triggerBody.skip_llm).toBe(false);
  });

  // ─── A40.l21 · run que entregou relatório para de ser pintado como falha ───

  describe("run partial_failure (ADR-357)", () => {
    it("não levanta card de falha", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial" })]);
      render(<PipelinePage />);
      expect(await screen.findByText(/Concluído com ressalva/)).toBeInTheDocument();
      expect(screen.queryByText(/Não conseguimos completar a etapa/)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Tentar novamente/ })).not.toBeInTheDocument();
    });

    it("mantém o CTA de processar — não há nada a corrigir antes de rodar de novo", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial" })]);
      render(<PipelinePage />);
      expect(
        await screen.findByRole("button", { name: /Processar documentos/ }),
      ).toBeInTheDocument();
    });

    it("aparece no histórico com o link do relatório", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial", report_id: "report-77" })]);
      render(<PipelinePage />);
      await screen.findByText(/Concluído com ressalva/);
      const links = screen.getAllByRole("link", { name: /ver relatório/i });
      expect(links.some((l) => l.getAttribute("href") === "/reports/report-77")).toBe(true);
    });

    it("declara a lacuna em banner próprio", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial" })]);
      render(<PipelinePage />);
      expect(await screen.findByRole("status")).toHaveTextContent(
        /sem o parecer do planejador/,
      );
    });

    it("banner some ao dispensar", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial" })]);
      const user = userEvent.setup();
      render(<PipelinePage />);
      const dismiss = await screen.findByRole("button", {
        name: /Fechar aviso de relatório com ressalva/,
      });
      await user.click(dismiss);
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
      expect(localStorage.getItem("pipeline:dismissedPartialRunId")).toBe("run-partial");
    });

    it("dispensar o parcial não dispensa o falhado (chaves separadas)", async () => {
      stubPipelinePage([makePartialRun({ id: "run-partial" })]);
      const user = userEvent.setup();
      render(<PipelinePage />);
      await user.click(
        await screen.findByRole("button", { name: /Fechar aviso de relatório com ressalva/ }),
      );
      expect(localStorage.getItem("pipeline:dismissedFailedRunId")).toBeNull();
    });
  });

  describe("desfecho terminal → toast + redirect (A40.l21)", () => {
    async function mountAndFinish(event: Record<string, unknown>) {
      stubPipelinePage([]);
      render(<PipelinePage />);
      await screen.findByRole("button", { name: /Processar documentos/ });
      await act(async () => {
        h.ws.opts.onRunFinished(event);
      });
    }

    it("run_completed com status partial_failure → toast de ressalva + redirect", async () => {
      await mountAndFinish({
        event: "run_completed",
        run_id: "run-p",
        status: "partial_failure",
      });
      expect(h.toast.warning).toHaveBeenCalledWith(
        "Relatório gerado com ressalva",
        expect.objectContaining({ action: expect.anything() }),
      );
      expect(h.toast.success).not.toHaveBeenCalled();
    });

    // O nome do evento é a escolha indefinida da A40.l18: o leitor tem que dar
    // a mesma resposta pelos dois caminhos.
    it("run_failed com status partial_failure → o MESMO toast de ressalva", async () => {
      await mountAndFinish({
        event: "run_failed",
        run_id: "run-p",
        status: "partial_failure",
      });
      expect(h.toast.warning).toHaveBeenCalledWith(
        "Relatório gerado com ressalva",
        expect.anything(),
      );
      expect(h.toast.error).not.toHaveBeenCalled();
    });

    it("run_completed normal continua sucesso", async () => {
      await mountAndFinish({ event: "run_completed", run_id: "run-c", status: "completed" });
      expect(h.toast.success).toHaveBeenCalled();
      expect(h.toast.warning).not.toHaveBeenCalled();
    });

    it("run_failed continua erro", async () => {
      await mountAndFinish({ event: "run_failed", run_id: "run-f", status: "failed" });
      expect(h.toast.error).toHaveBeenCalled();
      expect(h.toast.warning).not.toHaveBeenCalled();
    });

    it("mesmo run terminando duas vezes anuncia uma só (WS + polling)", async () => {
      await mountAndFinish({
        event: "run_completed",
        run_id: "run-dup",
        status: "partial_failure",
      });
      await act(async () => {
        h.ws.opts.onRunFinished({
          event: "run_completed",
          run_id: "run-dup",
          status: "partial_failure",
        });
      });
      expect(h.toast.warning).toHaveBeenCalledTimes(1);
    });
  });

  it("erro ao carregar runs mostra 'Erro ao carregar dados'", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/pipeline/runs", () =>
        HttpResponse.json({ detail: "x" }, { status: 500 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({ documents: [], total: 0 }),
      ),
      http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
    );
    render(<PipelinePage />);
    expect(await screen.findByText(/Erro ao carregar dados/)).toBeInTheDocument();
  });
});
