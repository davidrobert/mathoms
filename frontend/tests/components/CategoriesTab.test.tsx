/**
 * Integration tests — CategoriesTab (A11.cat-overrides-ux W4).
 *
 * Cobre:
 * - workspace novo → 24 categorias renderizadas (smoke do read-path).
 * - badge "Personalizada" condicional ao override existir.
 * - AlertCircle quando v desatualizada.
 * - tabs renderizam (V1 1 entrada → conteúdo direto, sem TabsList).
 *
 * MSW intercepta `/workspaces/:wsId/config/category-overrides/resolved`.
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";

import CategoriesTab from "@/app/(app)/config/CategoriesTab";
import { server } from "../mocks/server";

const API = "/api/v1";

// Helper — gera N categorias seguindo o template default.
function seedCategories(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: null,
    code: `cat_${i.toString().padStart(2, "0")}`,
    name: `Categoria ${i}`,
    category_type: i % 4 === 0 ? "income" : "expense",
    monthly_cap: null,
    order: i,
    keywords: [`KW_${i}_A`, `KW_${i}_B`],
  }));
}

describe("<CategoriesTab />", () => {
  it("workspace novo → 24 categorias default (sem override)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/config/category-overrides/resolved`, () =>
        HttpResponse.json({
          categories: seedCategories(24),
          total: 24,
          template_version_used: 1,
          latest_template_version: 1,
        }),
      ),
    );

    render(<CategoriesTab />);

    await waitFor(() => {
      // Categoria 0 (sem override) não deve ter badge Personalizada.
      expect(screen.getByText("Categoria 0")).toBeInTheDocument();
    });
    // Existe linha pra cada categoria seedada.
    for (let i = 0; i < 24; i++) {
      expect(screen.getByTestId(`category-row-cat_${i.toString().padStart(2, "0")}`))
        .toBeInTheDocument();
    }
    expect(screen.queryByTestId("badge-personalizada")).not.toBeInTheDocument();
    expect(screen.queryByTestId("alert-outdated-template")).not.toBeInTheDocument();
  });

  it("badge 'Personalizada' aparece quando id != null (override existe)", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/config/category-overrides/resolved`, () =>
        HttpResponse.json({
          categories: [
            {
              id: "override-uuid",
              code: "moradia",
              name: "Casa Renomeada",
              category_type: "expense",
              monthly_cap: null,
              order: 1,
              keywords: ["ALUGUEL"],
            },
            {
              id: null,
              code: "alimentacao",
              name: "Alimentação",
              category_type: "expense",
              monthly_cap: null,
              order: 2,
              keywords: ["MERCADO"],
            },
          ],
          total: 2,
          template_version_used: 1,
          latest_template_version: 1,
        }),
      ),
    );

    render(<CategoriesTab />);

    await waitFor(() => {
      expect(screen.getByText("Casa Renomeada")).toBeInTheDocument();
    });
    const badges = screen.getAllByTestId("badge-personalizada");
    expect(badges).toHaveLength(1);
    // Personalizada está na linha "moradia", não na "alimentacao".
    const moradiaRow = screen.getByTestId("category-row-moradia");
    expect(moradiaRow.textContent).toContain("Personalizada");
    const alimRow = screen.getByTestId("category-row-alimentacao");
    expect(alimRow.textContent).not.toContain("Personalizada");
  });

  it("AlertCircle aparece quando template_version_used < latest_template_version", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/config/category-overrides/resolved`, () =>
        HttpResponse.json({
          categories: seedCategories(2),
          total: 2,
          template_version_used: 1,
          latest_template_version: 2,
        }),
      ),
    );

    render(<CategoriesTab />);

    await waitFor(() => {
      const alerts = screen.getAllByTestId("alert-outdated-template");
      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  it("erro ao carregar mostra mensagem", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/config/category-overrides/resolved`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );

    render(<CategoriesTab />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar categorias/)).toBeInTheDocument();
    });
  });
});
