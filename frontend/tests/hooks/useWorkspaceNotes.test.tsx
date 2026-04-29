/** Tests — useWorkspaceNotes hook (ADR-153). */
import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { useWorkspaceNotes } from "@/hooks/useWorkspaceNotes";
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
      const n = note({
        id: crypto.randomUUID(),
        title: body.title ?? null,
        content: body.content ?? "",
        pinned: body.pinned ?? false,
      });
      store.push(n);
      return HttpResponse.json(n, { status: 201 });
    }),
    http.patch(`${API}/workspaces/${WS_ID}/notes/:id`, async ({ params, request }) => {
      const body = (await request.json()) as Partial<ServerNote>;
      const target = store.find((n) => n.id === params.id);
      if (!target) return new HttpResponse(null, { status: 404 });
      Object.assign(target, body);
      target.updated_at = new Date().toISOString();
      return HttpResponse.json(target);
    }),
    http.delete(`${API}/workspaces/${WS_ID}/notes/:id`, ({ params }) => {
      store = store.filter((n) => n.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
});

describe("useWorkspaceNotes", () => {
  it("retorna lista vazia quando workspaceId é undefined", async () => {
    const { result } = renderHook(() => useWorkspaceNotes(undefined));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notes).toEqual([]);
  });

  it("carrega notas ao montar", async () => {
    store.push(note({ title: "agenda", pinned: true }));
    store.push(note({ title: "lembrete", pinned: false }));
    const { result } = renderHook(() => useWorkspaceNotes(WS_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notes).toHaveLength(2);
  });

  it("create + reload reflete a nova nota", async () => {
    const { result } = renderHook(() => useWorkspaceNotes(WS_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.create({ title: "x" });
    });
    expect(result.current.notes).toHaveLength(1);
    expect(result.current.notes[0]?.title).toBe("x");
  });

  it("update muda content + pinned", async () => {
    store.push(note({ id: "n1", title: "antigo", pinned: false }));
    const { result } = renderHook(() => useWorkspaceNotes(WS_ID));
    await waitFor(() => expect(result.current.notes).toHaveLength(1));
    await act(async () => {
      await result.current.update("n1", { content: "novo", pinned: true });
    });
    expect(result.current.notes[0]?.content).toBe("novo");
    expect(result.current.notes[0]?.pinned).toBe(true);
  });

  it("remove deleta a nota e atualiza lista", async () => {
    store.push(note({ id: "n1" }));
    const { result } = renderHook(() => useWorkspaceNotes(WS_ID));
    await waitFor(() => expect(result.current.notes).toHaveLength(1));
    await act(async () => {
      await result.current.remove("n1");
    });
    expect(result.current.notes).toHaveLength(0);
  });

  it("popula error quando GET falha", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/notes`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    const { result } = renderHook(() => useWorkspaceNotes(WS_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
  });
});
