/**
 * ADR-123 · Fase 8 — testes de wire-up T3 (Kanban) + T5 (Timeline) + T6 (Notas).
 *
 * Cobre: GET inicial, renderização do primitivo, optimistic move em T3,
 * autosave em T6 (debounce interno do NotasCard), e derivação em T5.
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import {
  T3TarefasSection,
  T5ProximosPassosSection,
  T6NotasSection,
} from "@/components/report/sections/TaticoSections";
import type { ReportAnalysisData } from "@/lib/api";
import { server } from "../../mocks/server";

const API = "/api/v1";
const WS = "ws-1";
const RID = "rpt-1";

function emptyData(): ReportAnalysisData {
  return {} as ReportAnalysisData;
}

describe("T3TarefasSection", () => {
  it("renderiza items do Kanban retornados pelo GET", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/${RID}/kanban`, () =>
        HttpResponse.json({
          items: [
            {
              id: "k1",
              report_id: RID,
              titulo: "Configurar previdência",
              coluna: "a_fazer",
              prioridade: "alta",
              prazo: null,
              categoria: null,
              essencial: "S",
              ordem: 0,
              updated_at: "2026-04-01T00:00:00Z",
            },
          ],
        }),
      ),
    );
    render(
      <T3TarefasSection data={emptyData()} workspaceId={WS} reportId={RID} />,
    );
    expect(await screen.findByText("Configurar previdência")).toBeInTheDocument();
  });

  it("mostra mensagem de vazio quando kanban está vazio", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/${RID}/kanban`, () =>
        HttpResponse.json({ items: [] }),
      ),
    );
    render(
      <T3TarefasSection data={emptyData()} workspaceId={WS} reportId={RID} />,
    );
    expect(
      await screen.findByText(/Nenhuma tarefa registrada no Kanban/),
    ).toBeInTheDocument();
  });

  it("move optimista via PATCH e reflete nova coluna", async () => {
    let patchedTo: string | null = null;
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/${RID}/kanban`, () =>
        HttpResponse.json({
          items: [
            {
              id: "k1",
              report_id: RID,
              titulo: "Tarefa X",
              coluna: "a_fazer",
              prioridade: null,
              prazo: null,
              categoria: null,
              essencial: null,
              ordem: 0,
              updated_at: "2026-04-01T00:00:00Z",
            },
          ],
        }),
      ),
      http.patch(
        `${API}/workspaces/${WS}/reports/${RID}/kanban/k1`,
        async ({ request }) => {
          const body = (await request.json()) as { coluna?: string };
          patchedTo = body.coluna ?? null;
          return HttpResponse.json({
            id: "k1",
            report_id: RID,
            titulo: "Tarefa X",
            coluna: body.coluna ?? "a_fazer",
            prioridade: null,
            prazo: null,
            categoria: null,
            essencial: null,
            ordem: 0,
            updated_at: "2026-04-02T00:00:00Z",
          });
        },
      ),
    );
    render(
      <T3TarefasSection data={emptyData()} workspaceId={WS} reportId={RID} />,
    );
    await screen.findByText("Tarefa X");
    const btn = screen.getByRole("button", { name: /Mover para Em andamento/ });
    await userEvent.click(btn);
    await waitFor(() => expect(patchedTo).toBe("em_andamento"));
  });
});

describe("T5ProximosPassosSection", () => {
  it("renderiza timeline derivada de dashboard.proximos_15d", () => {
    const data = {
      dashboard: {
        proximos_15d: [
          { data: "2026-05-01", acao: "Revisar orçamento", status: "pendente" },
          { data: "2026-05-03", acao: "Ligar banco", status: "feito" },
        ],
      },
    } as unknown as ReportAnalysisData;
    render(<T5ProximosPassosSection data={data} />);
    expect(screen.getByText("Revisar orçamento")).toBeInTheDocument();
    expect(screen.getByText("Ligar banco")).toBeInTheDocument();
  });

  it("mostra estado vazio quando não há ações", () => {
    render(<T5ProximosPassosSection data={emptyData()} />);
    expect(
      screen.getByText(/Nenhuma ação agendada/),
    ).toBeInTheDocument();
  });
});

describe("T6NotasSection", () => {
  it("carrega conteúdo inicial do GET /notes", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/${RID}/notes`, () =>
        HttpResponse.json({
          id: "n1",
          report_id: RID,
          content: "Conteúdo persistido",
          author_user_id: null,
          updated_at: "2026-04-01T00:00:00Z",
        }),
      ),
    );
    render(<T6NotasSection workspaceId={WS} reportId={RID} />);
    const textarea = (await screen.findByLabelText(
      "Notas do relatório",
    )) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Conteúdo persistido");
  });

  it("autosave via PUT /notes após debounce", async () => {
    let savedContent: string | null = null;
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/${RID}/notes`, () =>
        HttpResponse.json(null),
      ),
      http.put(
        `${API}/workspaces/${WS}/reports/${RID}/notes`,
        async ({ request }) => {
          const body = (await request.json()) as { content: string };
          savedContent = body.content;
          return HttpResponse.json({
            id: "n1",
            report_id: RID,
            content: body.content,
            author_user_id: null,
            updated_at: "2026-04-02T00:00:00Z",
          });
        },
      ),
    );
    render(<T6NotasSection workspaceId={WS} reportId={RID} />);
    const textarea = (await screen.findByLabelText(
      "Notas do relatório",
    )) as HTMLTextAreaElement;
    await userEvent.type(textarea, "Rascunho");
    await waitFor(() => expect(savedContent).toBe("Rascunho"), { timeout: 2000 });
    const status = await screen.findByRole("status");
    expect(within(status).getByText(/salvo|salvando/)).toBeInTheDocument();
  });
});
