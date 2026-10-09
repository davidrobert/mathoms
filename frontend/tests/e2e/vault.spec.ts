/**
 * F6.5C.5 — Vault + Unlock (Fluxo 4)
 *
 * Senha é cadastrada no vault → upload de PDF protegido → unlock automático.
 * Em CI real requer PDF protegido sintético + senha correspondente.
 * Aqui cobrimos o CRUD do vault + chamada de retry-unlock.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Vault + Unlock", () => {
  test("CRUD vault: adicionar, listar, remover senha", async ({ page, request }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/vault");
    await expect(page.getByText("Vault de Senhas")).toBeVisible();

    const label = `E2E Senha ${Date.now()}`;
    await page.getByPlaceholder(/Rótulo/).fill(label);
    await page.getByPlaceholder(/^Senha$/).fill("minha-senha-pdf");
    await page.getByRole("button", { name: /Adicionar/ }).click();

    await expect(page.getByText("Senha adicionada!")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText(label)).toBeVisible();

    // Remove
    const deleteBtn = page.getByRole("button", {
      name: new RegExp(`Remover senha ${label}`, "i"),
    });
    await deleteBtn.click();
    await page.getByRole("button", { name: /^Remover$/ }).click();
    await expect(page.getByText(label)).not.toBeVisible({ timeout: 5_000 });
  });

  test("retry-unlock mostra mensagem quando nenhum documento é desbloqueado", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/vault");
    await expect(page.getByText("Vault de Senhas")).toBeVisible();

    // Adiciona senha bogus para ter algo no vault
    const label = `Bogus ${Date.now()}`;
    await page.getByPlaceholder(/Rótulo/).fill(label);
    await page.getByPlaceholder(/^Senha$/).fill("bogus-password");
    await page.getByRole("button", { name: /Adicionar/ }).click();
    await expect(page.getByText(label)).toBeVisible();

    // Sem doc `needs_password` no workspace (nenhum spec sobe PDF cifrado), o
    // backend responde 404 (status fixado em backend/tests/test_documents.py::
    // test_retry_unlock_no_pending_docs; o texto do detail vem de
    // document_retry_service.py e só este spec o fixa) e a página mostra o
    // detail no banner de erro. "Nenhum documento conseguiu ser desbloqueado…"
    // só sai com 200 + doc travado (exige PDF protegido).
    const retryResponse = page.waitForResponse((r) =>
      r.url().endsWith("/documents/retry-unlock"),
    );
    // Botão atual: "Tentar desbloquear documentos pendentes"
    await page.getByRole("button", { name: /Tentar desbloquear documentos/ }).click();
    expect((await retryResponse).status()).toBe(404);
    await expect(page.getByText("Nenhum documento pendente de senha")).toBeVisible();
  });
});
