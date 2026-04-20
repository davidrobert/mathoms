/**
 * Integration tests — Config page (F6.5B.7)
 *
 * Cobre que o shell ConfigPage renderiza todas as 7 tabs e a tab default
 * (Members) carrega. Tabs individuais (CategoriesTab, PipelineTab, LLMTab,
 * etc.) ficam para PRs sucessivos focados em cada uma — escopo aqui é a
 * estrutura de navegação por tabs e a tab inicial.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makeMember } from "../factories";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/config",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

import ConfigPage from "@/app/(app)/config/page";
import MembersTab from "@/app/(app)/config/MembersTab";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("ConfigPage", () => {
  beforeEach(() => {
    server.use(
      http.get("/api/workspaces/:workspaceId/config/workspace", () =>
        HttpResponse.json({ name: "Família", family_surname: "Teste" }),
      ),
      http.get("/api/workspaces/:workspaceId/config/members", () =>
        HttpResponse.json({
          members: [makeMember({ full_name: "Membro Inicial" })],
          total: 1,
        }),
      ),
    );
  });

  it("renderiza header + 8 tabs", async () => {
    render(<ConfigPage />);
    expect(screen.getByText("Configurações")).toBeInTheDocument();
    for (const label of [
      "Membros",
      "Acessos",
      "Categorias",
      "Pipeline",
      "LLM",
      "Instituições",
      "Layout",
      "Import/Export",
    ]) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }
  });

  it("tab default 'Membros' está selecionada", () => {
    render(<ConfigPage />);
    const membersTab = screen.getByRole("tab", { name: "Membros" });
    // base-ui usa aria-selected="true" (ARIA standard)
    expect(membersTab.getAttribute("aria-selected")).toBe("true");
  });

  it("trocar de tab → outra tab vira ativa", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/config/categories", () =>
        HttpResponse.json({ categories: [], total: 0 }),
      ),
    );
    const user = userEvent.setup();
    render(<ConfigPage />);
    const categoriesTab = screen.getByRole("tab", { name: "Categorias" });
    await user.click(categoriesTab);
    await waitFor(() => {
      expect(categoriesTab.getAttribute("aria-selected")).toBe("true");
    });
  });

  it("tab inicial Members carrega dados via API", async () => {
    render(<ConfigPage />);
    expect(await screen.findByText(/Membro Inicial/)).toBeInTheDocument();
  });

  it("membros template (sem id) mostram Editar e explicam ao expandir", async () => {
    server.use(
      http.get("/api/workspaces/:workspaceId/config/members", () =>
        HttpResponse.json({
          members: [
            {
              key: "titular",
              full_name: "Titular Exemplo",
              short_name: "Titular",
              role: "titular",
              order: 0,
              accounts: [],
            },
          ],
          total: 1,
        }),
      ),
    );
    const user = userEvent.setup();
    render(<MembersTab />);
    expect(
      await screen.findByText(/Conta de acesso e pessoas do relatório são coisas diferentes/),
    ).toBeInTheDocument();
    await screen.findByText("Titular Exemplo");
    await user.click(screen.getByRole("button", { name: "Editar" }));
    expect(await screen.findByTestId("members-fallback-notice")).toBeInTheDocument();
  });

  it("F6.5B.7: navegação para LLM tab carrega seu endpoint", async () => {
    let called = false;
    server.use(
      http.get("/api/workspaces/:workspaceId/config/llm", () => {
        called = true;
        return HttpResponse.json(null);
      }),
      http.get("/api/config/llm/tier", () =>
        HttpResponse.json({ tier: "free", has_llm_config: false }),
      ),
    );
    const user = userEvent.setup();
    render(<ConfigPage />);
    await user.click(screen.getByRole("tab", { name: "LLM" }));
    await waitFor(() => expect(called).toBe(true));
  });
});
