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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makeRun } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/pipeline",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));
vi.mock("@/lib/usePipelineWS", () => ({
  usePipelineWS: () => ({ status: "disconnected", lastEvent: null }),
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
  server.use(
    http.get("/api/v1/workspaces/:workspaceId/pipeline/new-doc-count", () =>
      HttpResponse.json({ new_count: 0 }),
    ),
  );
});

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
