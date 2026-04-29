/** Unit tests — NotasTab (ADR-153). */
import { beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { NotasTab } from "@/app/(app)/acao/_components/NotasTab";
import { clearToken, setToken } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-1";

interface ServerNote {
  id: string;
  workspace_id: string;
  title: string | null;
  content: string;
  pinned: boolean;
  author_user_id: string | null;
  created_at: string;
  updated_at: string;
}

let store: ServerNote[] = [];

function note(over: Partial<ServerNote> = {}): ServerNote {
  return {
    id: over.id ?? crypto.randomUUID(),
    workspace_id: WS_ID,
    title: null,
    content: "",
    pinned: false,
    author_user_id: null,
    created_at: "2026-04-29T00:00:00Z",
    updated_at: "2026-04-29T00:00:00Z",
    ...over,
  };
}

beforeEach(() => {
  clearToken();
  setToken("test-token");
  store = [];
  server.use(
    http.get(`${API}/workspaces/${WS_ID}/notes`, () =>
      HttpResponse.json({ notes: [...store], total: store.length }),
    ),
    http.post(`${API}/workspaces/${WS_ID}/notes`, async ({ request }) => {
      const body = (await request.json()) as Partial<ServerNote>;
      const n = note({ id: crypto.randomUUID(), ...body });
      store.push(n);
      return HttpResponse.json(n, { status: 201 });
    }),
    http.patch(`${API}/workspaces/${WS_ID}/notes/:id`, async ({ params, request }) => {
      const body = (await request.json()) as Partial<ServerNote>;
      const target = store.find((n) => n.id === params.id);
      if (!target) return new HttpResponse(null, { status: 404 });
      Object.assign(target, body);
      return HttpResponse.json(target);
    }),
    http.delete(`${API}/workspaces/${WS_ID}/notes/:id`, ({ params }) => {
      store = store.filter((n) => n.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

describe("NotasTab", () => {
  it("mostra empty state quando sem notas", async () => {
    render(<NotasTab workspaceId={WS_ID} />);
    await waitFor(() => expect(screen.getByText(/Nenhuma nota/i)).toBeInTheDocument());
  });

  it("renderiza lista de notas", async () => {
    store.push(note({ id: "n1", title: "agenda", content: "lembrar" }));
    render(<NotasTab workspaceId={WS_ID} />);
    await waitFor(() => expect(screen.getByDisplayValue("agenda")).toBeInTheDocument());
    expect(screen.getByDisplayValue("lembrar")).toBeInTheDocument();
  });

  it("clica Nova nota e cria via API", async () => {
    render(<NotasTab workspaceId={WS_ID} />);
    await waitFor(() => expect(screen.getByText(/Nenhuma nota/i)).toBeInTheDocument());
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Nova nota/i }));
    await waitFor(() => expect(store).toHaveLength(1));
  });
});
