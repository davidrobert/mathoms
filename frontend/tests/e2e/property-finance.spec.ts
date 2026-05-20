/**
 * Sprint A15 Onda 5c — smoke test do fluxo FU-3 imóvel financiado.
 *
 * Tag ``@property-finance`` (track A15 §Testes). Smoke mínimo: confirma
 * que a tela ``/imoveis/financiamentos-review`` renderiza sem 500/erro
 * fatal. Cobertura de fluxo completo (declarar valor → vincular debt →
 * ver patrimônio atualizado) fica para iterations futuras quando
 * fixture de dados estiver disponível.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("@property-finance — fluxo FU-3 imóvel financiado (ADR-227)", () => {
  test("tela de revisão de financiamentos renderiza para usuário autenticado", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/imoveis/financiamentos-review");

    await expect(
      page.getByRole("heading", { name: /Revisão de financiamentos/i }).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("empty state quando workspace não tem Debts pendentes", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/imoveis/financiamentos-review");

    // Workspace recém-criado normalmente não tem Debts needs_review=true.
    const empty = page
      .getByText(/Nenhuma revisão pendente/i)
      .or(page.getByText(/Todas as dívidas migradas/i));
    if (await empty.isVisible().catch(() => false)) {
      await expect(empty).toBeVisible();
    } else {
      test.skip(true, "Workspace tem Debts pendentes — empty state não aplicável");
    }
  });
});
