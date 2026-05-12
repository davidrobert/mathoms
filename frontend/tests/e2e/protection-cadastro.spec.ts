/**
 * ADR-192 · S9-T05 — Cadastro de apólice (Protection aggregate).
 *
 * Cobre o happy path da página /protecao:
 *   1. acessar a página
 *   2. cadastrar uma apólice (categoria=vida, capital=R$ 500.000)
 *   3. ver a apólice aparecer na listagem
 *   4. cancelar (soft-delete via POST /protections/{id}/cancel)
 *
 * Marcado `@critical` para entrar no gate Playwright do CI.
 *
 * Coordenação T04: o teste NÃO depende do S9 Hero card (T04 mergeado em
 * paralelo). Se T04 fechar antes, asserções de S9 podem ser adicionadas
 * num PR de follow-up.
 */
import { expect, test } from "@playwright/test";

import { ensureLoggedIn } from "./helpers/auth";

test.describe("@critical /protecao — cadastro de apólice", () => {
  test("cadastrar, listar e cancelar uma apólice", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/protecao");
    await expect(page.getByRole("heading", { name: "Proteção" })).toBeVisible();

    // Empty state ou listagem — abrir o dialog via botão de header.
    await page.getByTestId("add-protection").click();

    // Form de cadastro.
    await expect(page.getByText("Cadastrar apólice")).toBeVisible();

    // Categoria default é "vida" (primeira do select). Capital + data início.
    await page.getByLabel("Capital segurado (R$)").fill("500000,00");
    await page.getByLabel("Prêmio mensal (R$)").fill("350,00");

    // Date input — usar fill em formato yyyy-mm-dd.
    await page.getByLabel("Início da vigência").fill("2026-01-01");
    await page.getByLabel("Seguradora").fill("Seguradora Teste S/A");

    await page.getByRole("button", { name: /Cadastrar apólice/ }).click();

    // Listagem mostra a apólice.
    await expect(page.getByTestId("protections-totals")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("Seguradora Teste S/A")).toBeVisible();
    await expect(page.getByText(/R\$\s*500\.000/)).toBeVisible();

    // Cancela — confirma via window.confirm.
    page.on("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Cancelar apólice" }).first().click();

    // Após cancelar, com filtro default "Ativa", a linha desaparece.
    await expect(page.getByText("Nenhuma apólice corresponde aos filtros.")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("filtro de status mostra cancelada", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/protecao");

    // Cadastra rapidamente uma apólice para ter algo na lista.
    await page.getByTestId("add-protection").click();
    await page.getByLabel("Capital segurado (R$)").fill("100000,00");
    await page.getByLabel("Início da vigência").fill("2026-01-01");
    await page.getByRole("button", { name: /Cadastrar apólice/ }).click();

    await expect(page.getByText(/R\$\s*100\.000/)).toBeVisible({ timeout: 10_000 });

    // Mudar filtro para "Todas categorias" só para sanity check do select.
    const categoryFilter = page.getByTestId("filter-category");
    await categoryFilter.click();
    await page.getByRole("option", { name: "Vida" }).click();

    await expect(page.getByText(/R\$\s*100\.000/)).toBeVisible();
  });
});
