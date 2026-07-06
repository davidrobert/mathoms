/**
 * `CpfField` (ADR-259 §4) — mascarado por default, "ver completo" owner-only
 * auditado no backend, erro de rede não quebra a seção, print sempre mascara.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CpfField } from "@/components/report/ui/CpfField";
import { server } from "../../mocks/server";

const API = "/api/v1";
const CPF_URL = `${API}/workspaces/:wsId/config/members/:memberId/cpf/full`;

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

afterEach(() => server.resetHandlers());

const baseProps = {
  workspaceId: "ws-1",
  memberId: "member-1",
  memberName: "David Robert",
  cpfMasked: "***.***.789-09",
};

describe("CpfField", () => {
  it("mostra a máscara por default e não expõe o valor completo no DOM", () => {
    render(<CpfField {...baseProps} canReveal={false} />);
    expect(screen.getByText("***.***.789-09")).toBeInTheDocument();
    expect(screen.queryByText("123.456.789-09")).toBeNull();
  });

  it("sem CPF cadastrado renderiza travessão e nenhum affordance", () => {
    render(<CpfField {...baseProps} cpfMasked={null} canReveal={true} />);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("member/viewer (canReveal=false) não tem botão 'Ver completo'", () => {
    render(<CpfField {...baseProps} canReveal={false} />);
    expect(screen.queryByRole("button", { name: /ver cpf completo/i })).toBeNull();
  });

  it("owner clica 'Ver completo' → revela o CPF completo", async () => {
    server.use(
      http.get(CPF_URL, () => HttpResponse.json({ cpf_full: "123.456.789-09" })),
    );
    const user = userEvent.setup();
    render(<CpfField {...baseProps} canReveal={true} />);

    await user.click(screen.getByRole("button", { name: /ver cpf completo/i }));

    expect(await screen.findByText("123.456.789-09")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ocultar cpf/i })).toBeInTheDocument();
  });

  it("'Ocultar' volta ao estado mascarado sem nova chamada de rede", async () => {
    let calls = 0;
    server.use(
      http.get(CPF_URL, () => {
        calls += 1;
        return HttpResponse.json({ cpf_full: "123.456.789-09" });
      }),
    );
    const user = userEvent.setup();
    render(<CpfField {...baseProps} canReveal={true} />);

    await user.click(screen.getByRole("button", { name: /ver cpf completo/i }));
    await screen.findByText("123.456.789-09");
    await user.click(screen.getByRole("button", { name: /ocultar cpf/i }));

    expect(screen.getByText("***.***.789-09")).toBeInTheDocument();
    expect(screen.queryByText("123.456.789-09")).toBeNull();
    expect(calls).toBe(1);
  });

  it("erro de rede mantém a máscara visível e oferece 'Tentar de novo'", async () => {
    server.use(http.get(CPF_URL, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    const user = userEvent.setup();
    render(<CpfField {...baseProps} canReveal={true} />);

    await user.click(screen.getByRole("button", { name: /ver cpf completo/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("***.***.789-09")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tentar de novo/i })).toBeInTheDocument();
  });

  it("429 mostra copy específica de rate limit", async () => {
    server.use(http.get(CPF_URL, () => HttpResponse.json({ detail: "limite" }, { status: 429 })));
    const user = userEvent.setup();
    render(<CpfField {...baseProps} canReveal={true} />);

    await user.click(screen.getByRole("button", { name: /ver cpf completo/i }));

    expect(await screen.findByText(/muitas consultas seguidas/i)).toBeInTheDocument();
  });

  it("em print mode, sempre mostra a máscara e nunca o affordance de revelar", async () => {
    const original = window.matchMedia;
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === "print",
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
    try {
      // Playwright renderiza `/reports/[id]` do zero em contexto server-side
      // — o valor completo nunca chega a existir no DOM sem o clique
      // interativo do usuário, então o mount em print mode nunca tem o
      // botão que dispara a busca.
      render(<CpfField {...baseProps} canReveal={true} />);
      await waitFor(() => {
        expect(screen.getByText("***.***.789-09")).toBeInTheDocument();
      });
      expect(screen.queryByRole("button")).toBeNull();
    } finally {
      Object.defineProperty(window, "matchMedia", {
        writable: true,
        configurable: true,
        value: original,
      });
    }
  });
});
