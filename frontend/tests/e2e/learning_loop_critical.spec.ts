/**
 * Learning loop (A12 P4) — toast pós-override + modal preview + criar regra.
 *
 * Mocka backend via ``page.route()`` para não depender de seed completo:
 * - Workspace + user fixos
 * - Feature flag ``learning_loop_enabled: true``
 * - 1 transação editável; após PATCH → tx vira ``source: rule``
 * - Preview retorna contadores deterministas
 * - POST /rules retorna 201 sync
 *
 * Tagged @critical.
 */
import { expect, test, type Route } from "@playwright/test";

const WS_ID = "ws-fixture-a12p4";

test.describe("Learning loop · toast → modal → criar regra @critical", () => {
  test("editar categoria → toast → criar regra → toast sucesso", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("fin_token", "fixture-token");
      localStorage.setItem("fin.currentWorkspaceId", "ws-fixture-a12p4");
    });

    const json = (route: Route, body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    let categoryAfter = "alimentacao";
    let ruleCreated = false;

    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^\/api\/v1/, "");
      const method = route.request().method();

      if (path === "/auth/me") {
        return json(route, {
          id: "user-fix",
          email: "5@5.com",
          full_name: "Founder",
          is_active: true,
          is_developer: false,
        });
      }
      if (path === "/me/workspaces") {
        return json(route, {
          workspaces: [
            {
              id: WS_ID,
              name: "Fixture",
              family_surname: "Test",
              role: "owner",
              joined_at: "2026-01-01T00:00:00Z",
            },
          ],
          total: 1,
        });
      }
      if (path === `/workspaces/${WS_ID}/feature-flags`) {
        return json(route, {
          flags: { learning_loop_enabled: true, tasks_v2_enabled: false },
        });
      }
      if (path === `/workspaces/${WS_ID}/transactions`) {
        return json(route, {
          transactions: [
            {
              data: "2026-04-15",
              descricao: "MERCADO PAGO IFOOD",
              valor: -42.5,
              banco: "C6 Bank",
              categoria: categoryAfter,
              origem: "extrato",
              tipo_conta: "corrente",
              titular: "Founder",
              moeda: "BRL",
              transaction_hash: "h-1",
              row_id: "h-1:0",
              is_overridden: categoryAfter !== "alimentacao",
              override_source:
                categoryAfter !== "alimentacao" ? "manual" : null,
            },
          ],
          total: 1,
          page: 1,
          page_size: 50,
          summary: {
            total_receitas: 0,
            total_despesas: -42.5,
            saldo: -42.5,
            count: 1,
            periodo_inicio: "2026-04-15",
            periodo_fim: "2026-04-15",
          },
        });
      }
      if (path === `/workspaces/${WS_ID}/config/categories`) {
        return json(route, {
          categories: [
            { code: "alimentacao", group: "despesas", essencial: true },
            { code: "Alimentação", group: "despesas", essencial: true },
            { code: "Outros", group: "despesas", essencial: false },
          ],
        });
      }
      if (path === `/workspaces/${WS_ID}/config/family-members`) {
        return json(route, { members: [{ id: "m1", name: "Founder" }] });
      }
      if (
        path.startsWith(`/workspaces/${WS_ID}/transactions/`) &&
        path.endsWith("/override") &&
        method === "POST"
      ) {
        const body = (await route.request().postDataJSON()) as {
          new_category: string;
        };
        categoryAfter = body.new_category;
        return json(
          route,
          {
            id: "ovr-1",
            transaction_hash: "h-1",
            original_category: "alimentacao",
            new_category: body.new_category,
            notes: null,
            reviewed: true,
            created_at: new Date().toISOString(),
          },
          201,
        );
      }
      if (
        path === `/workspaces/${WS_ID}/categorization/rules/preview` &&
        method === "POST"
      ) {
        return json(route, {
          matches_total: 12,
          matches_in_closed_months: 2,
          matches_with_manual_override: 1,
          matches_blocked_internal_transfers: 0,
          matches_amount_total_brl_cents: 50_000,
          matches_by_month: { "202604": 12 },
          conflicts: [],
          low_risk: true,
          requires_user_confirmation: false,
          warnings: [],
        });
      }
      if (
        path === `/workspaces/${WS_ID}/categorization/rules` &&
        method === "POST"
      ) {
        ruleCreated = true;
        return json(
          route,
          {
            id: "rule-fix",
            workspace_id: WS_ID,
            keyword: "MERCADO PAGO IFOOD",
            target_category: "Alimentação",
            priority: 100,
            enabled: true,
            origin_override_id: null,
            created_by_user_id: "user-fix",
            applied_count: 9,
            revert_count_manual_edit: 0,
            revert_count_rule_disabled: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          201,
        );
      }
      // Default empty success para chamadas não mapeadas (dashboard, notifications).
      return json(route, {});
    });

    await page.goto("/transactions");

    // 1. Aguarda tabela carregar.
    await expect(page.getByText("MERCADO PAGO IFOOD")).toBeVisible({
      timeout: 10_000,
    });

    // 2. Clica na categoria para editar.
    await page.getByText("alimentacao").first().click();
    // Select editável aparece — escolhe "Alimentação".
    const selectLocator = page.locator("select").first();
    await selectLocator.selectOption("Alimentação");
    // Salva (botão check verde).
    await page
      .getByRole("button")
      .filter({ has: page.locator("svg.lucide-check") })
      .first()
      .click();

    // 3. Toast aparece com CTA "Criar regra".
    const criarRegra = page.getByRole("button", { name: /criar regra/i });
    await expect(criarRegra).toBeVisible({ timeout: 8000 });

    // 4. Clica no CTA do toast → abre modal.
    await criarRegra.click();
    await expect(
      page.getByText(/criar regra de categorização/i),
    ).toBeVisible();

    // 5. "Ver impacto" → preview renderiza.
    await page.getByTestId("rule-preview-button").click();
    await expect(page.getByText(/12/).first()).toBeVisible();
    await expect(
      page.getByText(/em meses já publicados/i),
    ).toBeVisible();

    // 6. "Criar" → POST sync → toast sucesso.
    await page.getByTestId("rule-create-button").click();
    await expect(
      page.getByText(/9 transações re-categorizadas/i),
    ).toBeVisible({ timeout: 5000 });

    expect(ruleCreated).toBe(true);
  });
});
