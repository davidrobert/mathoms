/**
 * `TitularesCard` (ADR-259 §4) — lista titulares com `CpfField`; erro de
 * rede no fetch de membros não quebra a seção (renderiza nada).
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";

import { TitularesCard } from "@/components/report/cards/TitularesCard";
import { server } from "../../mocks/server";

const API = "/api/v1";
const WS = "ws-1";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

afterEach(() => server.resetHandlers());

function mockMembersAndRole(members: unknown[], role: "owner" | "member" | "viewer") {
  server.use(
    http.get(`${API}/workspaces/${WS}/config/members`, () =>
      HttpResponse.json({ members, total: members.length }),
    ),
    http.get(`${API}/me/workspaces`, () =>
      HttpResponse.json({ workspaces: [{ id: WS, name: "WS", family_surname: null, role, joined_at: "2026-01-01T00:00:00Z" }], total: 1 }),
    ),
  );
}

describe("TitularesCard", () => {
  it("renderiza nome + CpfField para membro com CPF cadastrado", async () => {
    mockMembersAndRole(
      [{ id: "m1", key: "david", full_name: "David Robert", short_name: "David", cpf_masked: "***.***.789-09", role: "titular", order: 0, accounts: [] }],
      "owner",
    );
    render(<TitularesCard workspaceId={WS} />);

    expect(await screen.findByText("David Robert")).toBeInTheDocument();
    expect(await screen.findByText("***.***.789-09")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ver cpf completo/i })).toBeInTheDocument();
  });

  it("member/viewer não tem o botão 'Ver completo'", async () => {
    mockMembersAndRole(
      [{ id: "m1", key: "david", full_name: "David Robert", short_name: "David", cpf_masked: "***.***.789-09", role: "titular", order: 0, accounts: [] }],
      "viewer",
    );
    render(<TitularesCard workspaceId={WS} />);

    await screen.findByText("David Robert");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("membro sem CPF não aparece na lista", async () => {
    mockMembersAndRole(
      [{ id: "m1", key: "mariana", full_name: "Mariana Robert", short_name: "Mariana", cpf_masked: null, role: "conjuge", order: 1, accounts: [] }],
      "owner",
    );
    const { container } = render(<TitularesCard workspaceId={WS} />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("erro de rede no fetch de membros não quebra a seção — renderiza nada", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/config/members`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
      http.get(`${API}/me/workspaces`, () =>
        HttpResponse.json({ workspaces: [], total: 0 }),
      ),
    );
    const { container } = render(<TitularesCard workspaceId={WS} />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
