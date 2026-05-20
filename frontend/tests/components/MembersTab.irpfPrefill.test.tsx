/**
 * Tests — MembersTab IRPF pre-fill (ADR-229 PR2).
 *
 * Cobre os 4 cenários do gate:
 *  1. flag desligada → seção não aparece (mesmo com sugestões)
 *  2. sugestão "new" → clique em Adicionar → POST /accounts com origem_irpf=true
 *  3. sugestão "partial_collision" → modal diff abre → "merge" descarta sugestão
 *  4. dismiss → POST /irpf-dismissals + toast
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import MembersTab from "@/app/(app)/config/MembersTab";
import { makeMember, makeBankAccount } from "../factories";
import { server } from "../mocks/server";

const API = "/api/v1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/config",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

const toastSpy = { success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => toastSpy.success(...args),
    error: (...args: unknown[]) => toastSpy.error(...args),
  },
}));

const TEST_MEMBER = makeMember({
  id: "member-david",
  key: "david",
  full_name: "David Robert",
  short_name: "David",
  accounts: [
    makeBankAccount({
      id: "acc-99",
      institution_code: "c6bank",
      account_number: "99999-9",
    }),
  ],
});

function _setupWorkspaceSettings() {
  server.use(
    http.get(`${API}/workspaces/:wsId/config/workspace`, () =>
      HttpResponse.json({ name: "WS", family_surname: "Robert" }),
    ),
    http.get(`${API}/workspaces/:wsId/config/members`, () =>
      HttpResponse.json({ members: [TEST_MEMBER], total: 1 }),
    ),
  );
}

function _enableFlag(enabled: boolean) {
  server.use(
    http.get(`${API}/workspaces/:wsId/feature-flags`, () =>
      HttpResponse.json({ flags: { irpf_prefill_enabled: enabled } }),
    ),
  );
}

function _suggestionResponse(items: Record<string, unknown>[]) {
  return HttpResponse.json({
    irpf_year: 2024,
    processed_at: "2025-04-15T12:00:00Z",
    suggestions: items,
    total_filtered_exact_match: 0,
    total_dismissed: 0,
  });
}

beforeEach(() => {
  toastSpy.success.mockReset();
  toastSpy.error.mockReset();
  localStorage.setItem("fin_token", "t");
  _setupWorkspaceSettings();
});

afterEach(() => server.resetHandlers());

describe("MembersTab IRPF pre-fill", () => {
  it("flag desligada → não renderiza seção de sugestões", async () => {
    _enableFlag(false);
    server.use(
      http.get(`${API}/workspaces/:wsId/config/members/suggestions-from-irpf`, () =>
        _suggestionResponse([
          {
            institution_code: "itau",
            institution_label: "Itaú",
            account_type: "corrente",
            agency: "1234",
            account_number_raw: "12345-6",
            account_number_norm: "123456",
            member_key: "david",
            member_full_name: "David Robert",
            cpf_titular_masked: "***.123.456-**",
            irpf_year: 2024,
            match_kind: "new",
            collision_with_account_id: null,
          },
        ]),
      ),
    );
    render(<MembersTab />);
    const editar = await screen.findByRole("button", { name: "Editar" });
    await userEvent.setup().click(editar);
    await waitFor(() =>
      expect(screen.queryByTestId("member-irpf-section")).not.toBeInTheDocument(),
    );
  });

  it("flag ligada + sugestão new → POST /accounts com origem_irpf=true", async () => {
    _enableFlag(true);
    server.use(
      http.get(`${API}/workspaces/:wsId/config/members/suggestions-from-irpf`, () =>
        _suggestionResponse([
          {
            institution_code: "itau",
            institution_label: "Itaú",
            account_type: "corrente",
            agency: "1234",
            account_number_raw: "12345-6",
            account_number_norm: "123456",
            member_key: "david",
            member_full_name: "David Robert",
            cpf_titular_masked: "***.123.456-**",
            irpf_year: 2024,
            match_kind: "new",
            collision_with_account_id: null,
          },
        ]),
      ),
    );
    let receivedBody: Record<string, unknown> = {};
    server.use(
      http.post(
        `${API}/workspaces/:wsId/config/members/:memberId/accounts`,
        async ({ request }) => {
          receivedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ id: "acc-new", ...receivedBody });
        },
      ),
    );
    const user = userEvent.setup();
    render(<MembersTab />);
    await user.click(await screen.findByRole("button", { name: "Editar" }));
    const card = await screen.findByTestId("irpf-suggestion-itau-123456");
    await user.click(card.querySelector("button[class*=secondary], button[variant=secondary]") as HTMLElement
      ?? screen.getByRole("button", { name: /Adicionar$/ }));
    await waitFor(() => expect(receivedBody.origem_irpf).toBe(true));
    expect(receivedBody.origem_irpf_year).toBe(2024);
    expect(toastSpy.success).toHaveBeenCalled();
  });

  it("partial_collision → clique abre modal diff", async () => {
    _enableFlag(true);
    server.use(
      http.get(`${API}/workspaces/:wsId/config/members/suggestions-from-irpf`, () =>
        _suggestionResponse([
          {
            institution_code: "c6bank",
            institution_label: "C6 Bank",
            account_type: "corrente",
            agency: "0001",
            account_number_raw: "11111-1",
            account_number_norm: "111111",
            member_key: "david",
            member_full_name: "David Robert",
            cpf_titular_masked: "***.123.456-**",
            irpf_year: 2024,
            match_kind: "partial_collision",
            collision_with_account_id: "acc-99",
          },
        ]),
      ),
    );
    const user = userEvent.setup();
    render(<MembersTab />);
    await user.click(await screen.findByRole("button", { name: "Editar" }));
    const card = await screen.findByTestId("irpf-suggestion-c6bank-111111");
    expect(card.textContent).toMatch(/Possível duplicata/i);
    await user.click(screen.getByRole("button", { name: /Comparar/i }));
    expect(await screen.findByTestId("irpf-diff-modal-grid")).toBeInTheDocument();
  });

  it("dismiss → POST /irpf-dismissals + toast sucesso", async () => {
    _enableFlag(true);
    server.use(
      http.get(`${API}/workspaces/:wsId/config/members/suggestions-from-irpf`, () =>
        _suggestionResponse([
          {
            institution_code: "nubank",
            institution_label: "Nubank",
            account_type: "corrente",
            agency: null,
            account_number_raw: "55555-5",
            account_number_norm: "555555",
            member_key: "david",
            member_full_name: "David Robert",
            cpf_titular_masked: null,
            irpf_year: 2024,
            match_kind: "new",
            collision_with_account_id: null,
          },
        ]),
      ),
    );
    let receivedDismiss: Record<string, unknown> = {};
    server.use(
      http.post(
        `${API}/workspaces/:wsId/config/members/irpf-dismissals`,
        async ({ request }) => {
          receivedDismiss = (await request.json()) as Record<string, unknown>;
          return new HttpResponse(null, { status: 204 });
        },
      ),
    );
    const user = userEvent.setup();
    render(<MembersTab />);
    await user.click(await screen.findByRole("button", { name: "Editar" }));
    await screen.findByTestId("irpf-suggestion-nubank-555555");
    await user.click(screen.getByRole("button", { name: /^Descartar sugestão/i }));
    await waitFor(() => expect(receivedDismiss.institution_code).toBe("nubank"));
    expect(receivedDismiss.irpf_year).toBe(2024);
    expect(toastSpy.success).toHaveBeenCalled();
  });
});
