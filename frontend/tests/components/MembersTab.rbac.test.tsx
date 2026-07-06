/**
 * `MembersTab` — RBAC de escrita + CPF mascarado (ADR-259 §4 follow-up).
 *
 * Backend já bloqueia `viewer` com 403 (`require_write_role`); aqui cobrimos
 * a UX: viewer não vê affordances de escrita nem o botão "Ver completo"
 * (owner-only); member escreve mas não revela CPF completo; owner tem tudo.
 *
 * `tests/setup.ts` mocka `useWorkspace()` globalmente fixo em `role: "owner"`
 * — este arquivo sobrescreve o mock localmente (per-file ganha do global,
 * mesmo padrão de `react-chartjs-2` documentado em `tests/setup.ts`) com um
 * role mutável via `vi.hoisted`, para exercitar member/viewer também.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";

import MembersTab from "@/app/(app)/config/MembersTab";
import { makeMember } from "../factories";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS = "ws-1";

const { getRole, setRole } = vi.hoisted(() => {
  let role: "owner" | "member" | "viewer" = "owner";
  return {
    getRole: () => role,
    setRole: (r: "owner" | "member" | "viewer") => {
      role = r;
    },
  };
});

vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) => children,
  useWorkspace: () => ({
    workspace: { id: WS, name: "WS", family_surname: "Robert", role: getRole(), joined_at: "2026-01-01T00:00:00Z" },
    workspaces: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/config",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const TEST_MEMBER = makeMember({
  id: "member-david",
  key: "david",
  full_name: "David Robert",
  short_name: "David",
  cpf_masked: "***.***.789-09",
  accounts: [],
});

function mockMembers(members: unknown[] = [TEST_MEMBER]) {
  server.use(
    http.get(`${API}/workspaces/:wsId/config/workspace`, () =>
      HttpResponse.json({ name: "WS", family_surname: "Robert" }),
    ),
    http.get(`${API}/workspaces/:wsId/config/members`, () =>
      HttpResponse.json({ members, total: members.length }),
    ),
    http.get(`${API}/workspaces/:wsId/feature-flags`, () => HttpResponse.json({ flags: {} })),
  );
}

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  setRole("owner");
});

afterEach(() => server.resetHandlers());

describe("MembersTab — RBAC", () => {
  it("owner vê 'Adicionar membro', 'Editar', excluir e 'Ver completo'", async () => {
    mockMembers();
    render(<MembersTab />);

    await screen.findByText("David Robert");
    expect(screen.getByRole("button", { name: /adicionar membro/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ver cpf completo/i })).toBeInTheDocument();
  });

  it("member escreve (edita/adiciona) mas não revela CPF completo", async () => {
    setRole("member");
    mockMembers();
    render(<MembersTab />);

    await screen.findByText("David Robert");
    expect(screen.getByRole("button", { name: /adicionar membro/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ver cpf completo/i })).toBeNull();
  });

  it("viewer não vê nenhum affordance de escrita nem excluir", async () => {
    setRole("viewer");
    mockMembers();
    render(<MembersTab />);

    await screen.findByText("David Robert");
    expect(screen.queryByRole("button", { name: /adicionar membro/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /ver cpf completo/i })).toBeNull();
    // "Editar" continua visível (só expande detalhes read-only).
    expect(screen.getByRole("button", { name: /editar/i })).toBeInTheDocument();
  });

  it("viewer expandido vê campos como texto, sem controles de edição", async () => {
    setRole("viewer");
    mockMembers();
    const user = userEvent.setup();
    render(<MembersTab />);

    await screen.findByText("David Robert");
    await user.click(screen.getByRole("button", { name: /editar/i }));

    await waitFor(() => {
      expect(screen.getByText("David Robert", { selector: "div" })).toBeInTheDocument();
    });
    // Sem InlineField clicável para full_name — é uma <div>, não <button>.
    expect(screen.queryByRole("button", { name: "David Robert" })).toBeNull();
  });

  it("membro sem CPF mostra travessão, sem affordance", async () => {
    mockMembers([makeMember({ id: "m2", full_name: "Sem CPF", cpf_masked: null, accounts: [] })]);
    render(<MembersTab />);

    await screen.findByText("Sem CPF");
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
