/**
 * E2E — Transfer Config UI (ADR-133b)
 *
 * Fluxo: navegar para /config/transfer → adicionar recipient → salvar →
 * reload → verificar persistência (UI + GET /config/transfer).
 *
 * Tagged @critical.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Config /transfer round-trip @critical", () => {
  test("adicionar recipient → salvar → reload → persiste no backend", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    await page.goto("/config/transfer");

    await expect(
      page.getByRole("heading", { name: /Transferências internas/i }),
    ).toBeVisible();

    const sentinel = `PIX TESTE B-UI ${Date.now()}`;
    await page
      .getByTestId("recipients-new-input")
      .fill(sentinel);
    await page.getByTestId("recipients-add").click();

    await expect(page.getByDisplayValue(sentinel)).toBeVisible();

    const saveBtn = page.getByTestId("save-transfer-config");
    await expect(saveBtn).toBeEnabled();
    await saveBtn.click();

    await expect(
      page.getByText(/próximo relatório gerado já usará as novas regras/i),
    ).toBeVisible();

    await page.reload();
    await expect(page.getByDisplayValue(sentinel)).toBeVisible();

    // Confirma persistência via GET direto na API
    const token = await page.evaluate(() => localStorage.getItem("fin_token"));
    const wsListResp = await request.get("/api/v1/me/workspaces", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const wsList = await wsListResp.json();
    const workspaceId = wsList.workspaces?.[0]?.id;
    expect(workspaceId).toBeTruthy();

    const cfgResp = await request.get(
      `/api/v1/workspaces/${workspaceId}/config/transfer`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(cfgResp.ok()).toBeTruthy();
    const cfg = await cfgResp.json();
    expect(cfg.recipients).toContain(sentinel);
  });
});
