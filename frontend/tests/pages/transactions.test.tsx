/**
 * Integration tests — Transactions page (F6.5B.5)
 *
 * Inclui smoke XSS (F6.5D.6 antecipada): `<script>` em descrição/notas
 * deve ser renderizado escapado, não executado.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { makeTransaction } from "../factories";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/transactions",
}));

import TransactionsPage from "@/app/(app)/transactions/page";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
  replaceMock.mockClear();
});

describe("TransactionsPage", () => {
  it("loading: spinner inicial", () => {
    server.use(http.get("/api/transactions", () => new Promise(() => {})));
    const { container } = render(<TransactionsPage />);
    expect(container.querySelector("svg.animate-spin")).toBeInTheDocument();
  });

  it("renderiza transações + summary", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [
            makeTransaction({ descricao: "Mercado XYZ", valor: -250.5 }),
            makeTransaction({ descricao: "Pagto Folha", valor: 12500 }),
          ],
          total: 2,
          page: 1,
          page_size: 50,
          summary: {
            total_receitas: 12500,
            total_despesas: -250.5,
            saldo: 12249.5,
            count: 2,
            periodo_inicio: "2026-04-01",
            periodo_fim: "2026-04-30",
          },
        }),
      ),
    );
    render(<TransactionsPage />);
    expect(await screen.findByText("Mercado XYZ")).toBeInTheDocument();
    expect(screen.getByText("Pagto Folha")).toBeInTheDocument();
  });

  it("erro 500 mostra mensagem", async () => {
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    render(<TransactionsPage />);
    expect(await screen.findByText(/boom/)).toBeInTheDocument();
  });

  // ─── F6.5D.6 — XSS smoke (antecipada) ────────────────────────────
  it("XSS smoke: <script> em descrição é renderizado escapado, não executado", async () => {
    const xssPayload = "<script>window.__pwned=true</script>Mercado";
    const xssImg = '<img src=x onerror="window.__pwned2=true">';
    server.use(
      http.get("/api/transactions", () =>
        HttpResponse.json({
          transactions: [
            makeTransaction({ descricao: xssPayload }),
            makeTransaction({ descricao: xssImg }),
          ],
          total: 2,
          page: 1,
          page_size: 50,
          summary: {
            total_receitas: 0,
            total_despesas: -200,
            saldo: -200,
            count: 2,
            periodo_inicio: null,
            periodo_fim: null,
          },
        }),
      ),
    );
    render(<TransactionsPage />);
    // Aguarda render
    await waitFor(() => {
      expect(screen.getByText(/Mercado/)).toBeInTheDocument();
    });
    // CRÍTICO: scripts NÃO podem ter executado
    expect((window as any).__pwned).toBeUndefined();
    expect((window as any).__pwned2).toBeUndefined();
    // Texto contém o payload literal (escapado), nem tag <script> nem <img onerror> ativos
    const allText = document.body.textContent ?? "";
    expect(allText).toContain("<script>");
    // Não deve haver tag <script> real renderizada com o conteúdo malicioso
    const realScripts = Array.from(document.querySelectorAll("script")).filter((s) =>
      s.textContent?.includes("__pwned"),
    );
    expect(realScripts).toHaveLength(0);
    // Não deve haver <img> com onerror real
    const imgs = Array.from(document.querySelectorAll("img"));
    for (const img of imgs) {
      expect(img.getAttribute("onerror")).toBeNull();
    }
  });
});
