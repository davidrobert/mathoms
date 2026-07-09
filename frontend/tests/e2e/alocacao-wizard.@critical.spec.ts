/**
 * Wizard de alocação-alvo v2 (A12 PR8, ADR-141 §Emenda item 11).
 *
 * Cobre o fluxo completo sem backend real (mock via ``page.route()``):
 * distribuição agrupada → barra Σ→100 com estado warning/danger →
 * "Completar com Caixa" → rebalanceamento agrupado (grupo + sub-opção) →
 * confirma e persiste os inputs v2 corretos.
 *
 * Tagged @critical.
 */
import { expect, test, type Route } from "@playwright/test";

const WS_ID = "ws-fixture-alocacao";

interface SavedGoal {
  inputs: Record<string, unknown>;
  notes?: string | null;
}

test.describe("Wizard alocação-alvo v2 @critical", () => {
  test("distribuição → completar com caixa → rebalanceamento → confirma", async ({
    page,
  }) => {
    await page.addInitScript((ws) => {
      localStorage.setItem("fin_token", "fixture-token");
      localStorage.setItem("fin.currentWorkspaceId", ws);
    }, WS_ID);

    let saved: SavedGoal | null = null;

    const json = (route: Route, body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });

    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^\/api\/v1/, "");
      const method = route.request().method();

      if (path === "/auth/me") {
        return json(route, {
          id: "user-fix",
          email: "founder@test.com",
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
      if (path === `/workspaces/${WS_ID}/notifications`) {
        return json(route, { notifications: [], total: 0, unread: 0 });
      }
      if (path === `/workspaces/${WS_ID}/goals/alocacao` && method === "PUT") {
        saved = (await route.request().postDataJSON()) as SavedGoal;
        return json(route, {
          id: "goal-fix",
          workspace_id: WS_ID,
          type: "ALOCACAO_ALVO",
          meta_version: 2,
          inputs: saved.inputs,
          derived: { soma_percentuais: 100 },
          converted_from: null,
          effective_from: "2026-01-01",
          effective_to: null,
          is_template: false,
          notes: saved.notes ?? null,
          created_by: "user-fix",
          created_by_name: "Founder",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
      // Default empty success para o shell (dashboard, notificações, flags).
      return json(route, {});
    });

    // ── Passo 1: distribuição ────────────────────────────────────────────
    await page.goto("/plano/alocacao/wizard");
    await expect(
      page.getByRole("heading", { name: "Distribua seus investimentos" }),
    ).toBeVisible({ timeout: 15_000 });

    const progress = page.getByTestId("alocacao-progress");
    // Preset Moderado é o default → soma 100 → estado ok.
    await expect(progress).toHaveAttribute("data-state", "ok");

    // Quebra a soma → estado warning (durante edição, sem tentativa de avançar).
    await page.locator("#rf_pos_pct").fill("30");
    await expect(progress).toHaveAttribute("data-state", "warning");

    // Tenta avançar com Σ≠100 → estado danger e permanece no passo 1.
    await page.getByRole("button", { name: /Próximo/ }).click();
    await expect(progress).toHaveAttribute("data-state", "danger");
    await expect(
      page.getByRole("heading", { name: "Distribua seus investimentos" }),
    ).toBeVisible();

    // Ação determinística: joga o resíduo em Caixa → Σ=100 → estado ok.
    await page.getByRole("button", { name: /Completar com Caixa/ }).click();
    await expect(progress).toHaveAttribute("data-state", "ok");
    await expect(page.locator("#caixa_pct")).toHaveValue("5");

    // ── Passo 2: instrumentos (opcional) ─────────────────────────────────
    await page.getByRole("button", { name: /Próximo/ }).click();
    await expect(
      page.getByRole("heading", { name: "Instrumentos preferidos" }),
    ).toBeVisible();

    // ── Passo 3: rebalanceamento agrupado ────────────────────────────────
    await page.getByRole("button", { name: /Próximo/ }).click();
    await expect(
      page.getByRole("heading", { name: "Rebalanceamento" }),
    ).toBeVisible();

    // "No aporte (recomendado)" é o default.
    await expect(
      page.getByRole("radio", { name: /No aporte/ }),
    ).toHaveAttribute("aria-checked", "true");

    // Seleciona "Periódico" → sub-opções aparecem → escolhe "Trimestral".
    await page.getByRole("radio", { name: /Periódico/ }).click();
    await page.getByRole("button", { name: "Trimestral" }).click();

    // ── Confirma e valida persistência ───────────────────────────────────
    await page.getByRole("button", { name: /Confirmar/ }).click();

    await expect.poll(() => saved, { timeout: 10_000 }).not.toBeNull();
    const persisted = saved as unknown as SavedGoal;
    expect(persisted.inputs.rebalanceamento_modo).toBe("trimestral");
    expect(persisted.inputs.caixa_pct).toBe(5);
    const soma = [
      "rf_pos_pct",
      "rf_pre_pct",
      "rf_ipca_pct",
      "acoes_br_pct",
      "acoes_int_pct",
      "fiis_pct",
      "caixa_pct",
    ].reduce((acc, k) => acc + Number(persisted.inputs[k] ?? 0), 0);
    expect(soma).toBe(100);
  });
});
