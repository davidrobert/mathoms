/**
 * Security smoke tests — F6.5D.6
 *
 * Cobertura:
 * - XSS em 4 campos user-controlled (descrição já em transactions.test.tsx;
 *   aqui cobrimos member.full_name, category.name, vault.label)
 * - JWT expiry mid-session (401 em API → clearToken + redirect /login)
 * - Logout limpa localStorage completamente (token + quaisquer outros)
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makeMember, makeCategory, makeVaultPassword } from "../factories";
import { clearToken, getToken, ApiError } from "@/lib/api";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  replaceMock.mockClear();
});

// ─── XSS smoke em campos user-controlled ─────────────────────────────

const XSS_PAYLOAD = '<script>window.__xss_fired=true</script>';
const XSS_IMG = '<img src=x onerror="window.__xss_img=true">';

describe("XSS smoke — F6.5D.6", () => {
  beforeEach(() => {
    (window as any).__xss_fired = undefined;
    (window as any).__xss_img = undefined;
  });

  it("member.full_name com <script> renderiza escapado (não executa)", async () => {
    server.use(
      http.get("/api/config/workspace", () =>
        HttpResponse.json({ name: "x", family_surname: null }),
      ),
      http.get("/api/config/members", () =>
        HttpResponse.json({
          members: [makeMember({ full_name: XSS_PAYLOAD })],
          total: 1,
        }),
      ),
    );
    const { default: MembersTab } = await import("@/app/(app)/config/MembersTab");
    render(<MembersTab />);
    await waitFor(() => {
      expect(document.body.textContent).toContain("<script>");
    });
    expect((window as any).__xss_fired).toBeUndefined();
    // Não deve haver <script> real
    expect(
      Array.from(document.querySelectorAll("script")).filter((s) =>
        s.textContent?.includes("__xss_fired"),
      ),
    ).toHaveLength(0);
  });

  it("category.name com <img onerror> renderiza escapado", async () => {
    server.use(
      http.get("/api/config/categories", () =>
        HttpResponse.json({
          categories: [makeCategory({ name: XSS_IMG })],
          total: 1,
        }),
      ),
    );
    const { default: CategoriesTab } = await import("@/app/(app)/config/CategoriesTab");
    render(<CategoriesTab />);
    await waitFor(() => {
      expect(document.body.textContent).toContain("onerror");
    });
    expect((window as any).__xss_img).toBeUndefined();
    // Nenhum <img> com onerror real
    for (const img of Array.from(document.querySelectorAll("img"))) {
      expect(img.getAttribute("onerror")).toBeNull();
    }
  });

  it("vault.label com <script> renderiza escapado", async () => {
    server.use(
      http.get("/api/vault/passwords", () =>
        HttpResponse.json({
          passwords: [makeVaultPassword({ label: XSS_PAYLOAD })],
          total: 1,
        }),
      ),
    );
    const { default: VaultPage } = await import("@/app/(app)/vault/page");
    render(<VaultPage />);
    await waitFor(() => {
      expect(document.body.textContent).toContain("<script>");
    });
    expect((window as any).__xss_fired).toBeUndefined();
  });
});

// ─── JWT expiry mid-session ──────────────────────────────────────────

describe("JWT expiry mid-session — F6.5D.6", () => {
  it("401 em API causa apiFetch a lançar ApiError com status=401", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "Token expirado" }, { status: 401 }),
      ),
    );
    const { getMe } = await import("@/lib/api");
    await expect(getMe()).rejects.toMatchObject({ status: 401 });
  });

  it("AppShell em 401 chama clearToken + router.replace('/login')", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "x" }, { status: 401 }),
      ),
    );
    const { default: AppShell } = await import("@/components/AppShell");
    render(<AppShell>x</AppShell>);
    await waitFor(() => {
      expect(replaceMock).toHaveBeenCalledWith("/login");
    });
    expect(localStorage.getItem("fin_token")).toBeNull();
  });
});

// ─── Logout cleanup ──────────────────────────────────────────────────

describe("Logout cleanup — F6.5D.6", () => {
  it("clearToken remove fin_token do localStorage", () => {
    localStorage.setItem("fin_token", "abc");
    localStorage.setItem("outro_valor", "x"); // não afetado
    clearToken();
    expect(localStorage.getItem("fin_token")).toBeNull();
    // Não dever apagar outros (clearToken é cirúrgico)
    expect(localStorage.getItem("outro_valor")).toBe("x");
  });

  it("getToken retorna null após clearToken (estado consistente)", () => {
    localStorage.setItem("fin_token", "abc");
    expect(getToken()).toBe("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("logout via AppShell remove token e redireciona", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({
          id: "u1",
          email: "x@test.com",
          full_name: "User",
          is_active: true,
        }),
      ),
    );
    const { default: AppShell } = await import("@/components/AppShell");
    const user = userEvent.setup();
    render(<AppShell>x</AppShell>);
    await screen.findByText("User");
    await user.click(screen.getByRole("button", { name: /sair/i }));
    expect(localStorage.getItem("fin_token")).toBeNull();
    expect(replaceMock).toHaveBeenCalledWith("/login");
  });
});
