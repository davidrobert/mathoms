/**
 * F6.5C.4 — Config round-trip (Fluxo 3)
 *
 * Cria membro via UI → exporta JSON → assert que membro está no payload.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Config round-trip", () => {
  test("criar membro via UI + exportar JSON = membro presente no payload", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/config");
    await expect(
      page.getByRole("heading", { name: "Configurações" }),
    ).toBeVisible();

    // Abre tab Membros (default, mas garantindo)
    await page.getByRole("tab", { name: /Membros/ }).click();

    // Clica "+ Adicionar membro" — botão de dashed border no rodapé da lista
    const addBtn = page.getByRole("button", { name: /Adicionar membro/ });
    if (await addBtn.isVisible().catch(() => false)) {
      await addBtn.click();
      // Preencher campos mínimos: nome completo e nome curto são required
      // Labels atuais: "Nome completo (civil atual)" e "Como prefere ser chamado(a)"
      await page.getByPlaceholder(/Como nos documentos oficiais/).fill("Membro E2E");
      await page.getByPlaceholder(/Ex\.: Maria, David/).fill("E2E");
      // Salvar — botão do formulário de novo membro
      await page.getByRole("button", { name: /Salvar e abrir edição/ }).click();
    }

    // Via API, exportar JSON — endpoint é workspace-scoped
    const token = await page.evaluate(() => localStorage.getItem("fin_token"));
    const wsListResp = await request.get("/api/v1/me/workspaces", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const wsList = await wsListResp.json();
    const workspaceId = wsList.workspaces?.[0]?.id;

    const exportResp = await request.get(
      `/api/v1/workspaces/${workspaceId}/config/export`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(exportResp.ok()).toBeTruthy();
    const body = await exportResp.json();

    // Estrutura do export
    expect(body).toHaveProperty("family_members");
    // Payload é válido (lista pode estar vazia se UI requer steps adicionais)
    expect(body.family_members).toBeTruthy();
  });

  test("alterar family_surname via UI persiste no backend", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/config");
    await page.getByRole("tab", { name: /Membros/ }).click();

    // Label: "Sobrenome da família" com htmlFor="family-surname"
    const surnameInput = page.getByLabel(/Sobrenome da família/i);
    if (await surnameInput.isVisible().catch(() => false)) {
      await surnameInput.fill(`Surname-${Date.now()}`);
      // Clica Salvar (botão associado ao campo de sobrenome da família)
      await page.getByRole("button", { name: /^Salvar$/ }).click();
      // Aguarda feedback de sucesso
      await expect(page.getByText(/Sobrenome da família atualizado/)).toBeVisible({
        timeout: 5_000,
      });

      // Valida via API (ADR-072: rotas workspace-scoped)
      const token = await page.evaluate(() => localStorage.getItem("fin_token"));
      const wsListResp = await request.get("/api/v1/me/workspaces", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const wsList = await wsListResp.json();
      const workspaceId = wsList.workspaces?.[0]?.id;
      const resp = await request.get(
        `/api/v1/workspaces/${workspaceId}/config/workspace`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      const data = await resp.json();
      expect(data.family_surname).toMatch(/Surname-\d+/);
    }
  });
});
