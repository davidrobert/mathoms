/**
 * v2.7 — gate funcional do DnD do Kanban (T3 · Tarefas).
 *
 * Tagged @critical: confirma que arrastar um card de uma coluna para
 * outra dispara PATCH /v1/.../kanban/:id com `coluna` atualizada.
 * Cobre o caminho desktop com mouse — fallback mobile (botões "→ Coluna")
 * é validado em vitest.
 */
import { test, expect } from "@playwright/test";

import {
  MOCK_REPORT_ID,
  MOCK_WORKSPACE_ID,
  mockReportPage,
  waitForReportReady,
} from "../helpers/mock-report";

const KANBAN_ITEMS = [
  {
    id: "task-1",
    titulo: "Revisar reserva de emergência",
    coluna: "a_fazer",
    prioridade: "alta",
    prazo: null,
    categoria: null,
    essencial: "S",
    ordem: 1,
  },
  {
    id: "task-2",
    titulo: "Estudo previdência PGBL",
    coluna: "em_andamento",
    prioridade: "media",
    prazo: null,
    categoria: null,
    essencial: "R",
    ordem: 2,
  },
  {
    id: "task-3",
    titulo: "Quitação cartão",
    coluna: "concluido",
    prioridade: "baixa",
    prazo: null,
    categoria: null,
    essencial: "S",
    ordem: 3,
  },
];

test.describe("Kanban DnD @critical", () => {
  test("drag card de 'A fazer' para 'Em andamento' chama PATCH com nova coluna", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    const kanbanPath = `**/api/v1/workspaces/${workspaceId}/reports/${reportId}/kanban`;
    const patches: Array<{ id: string; body: Record<string, unknown> }> = [];

    // Override LIST → seeded items.
    await page.route(kanbanPath, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: KANBAN_ITEMS }),
        });
        return;
      }
      await route.continue();
    });

    // Override PATCH /:id → record + 200.
    await page.route(`${kanbanPath}/*`, async (route) => {
      if (route.request().method() === "PATCH") {
        const url = route.request().url();
        const itemId = url.split("/").pop() ?? "";
        const bodyText = route.request().postData() ?? "{}";
        const body = JSON.parse(bodyText) as Record<string, unknown>;
        patches.push({ id: itemId, body });
        const orig = KANBAN_ITEMS.find((it) => it.id === itemId);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...orig, ...body }),
        });
        return;
      }
      await route.continue();
    });

    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    // Aguarda card task-1 renderizar dentro de coluna a_fazer.
    const sourceCol = page.locator('[data-kanban-column="a_fazer"]');
    const targetCol = page.locator('[data-kanban-column="em_andamento"]');
    await expect(sourceCol).toBeVisible();
    await expect(targetCol).toBeVisible();

    const sourceCard = sourceCol.locator(
      '[data-kanban-item][data-item-id="task-1"]',
    );
    await expect(sourceCard).toBeVisible();

    // dragTo simula pointerdown + move + up; @dnd-kit/core exige
    // distance:6 de ativação configurada em useSensor(PointerSensor).
    await sourceCard.dragTo(targetCol);

    // Aguarda PATCH ser registrado (debounce de @dnd-kit + fetch async).
    await expect.poll(() => patches.length, { timeout: 5_000 }).toBeGreaterThan(0);

    expect(patches[0]?.id).toBe("task-1");
    expect(patches[0]?.body).toEqual({ coluna: "em_andamento" });
  });

  test("drag dentro da mesma coluna NÃO chama PATCH (read-only ordering)", async ({
    page,
  }) => {
    const workspaceId = MOCK_WORKSPACE_ID;
    const reportId = MOCK_REPORT_ID;
    await mockReportPage(page, { workspaceId, reportId });
    const kanbanPath = `**/api/v1/workspaces/${workspaceId}/reports/${reportId}/kanban`;
    const patches: string[] = [];

    await page.route(kanbanPath, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: KANBAN_ITEMS }),
        });
        return;
      }
      await route.continue();
    });
    await page.route(`${kanbanPath}/*`, async (route) => {
      if (route.request().method() === "PATCH") {
        patches.push(route.request().url());
        await route.fulfill({ status: 200, body: "{}" });
        return;
      }
      await route.continue();
    });

    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    const sourceCol = page.locator('[data-kanban-column="a_fazer"]');
    const card = sourceCol.locator(
      '[data-kanban-item][data-item-id="task-1"]',
    );
    await expect(card).toBeVisible();
    // Drop sobre a mesma coluna: o handler em Kanban.tsx checa
    // `item.coluna === target` e retorna sem chamar onMove.
    await card.dragTo(sourceCol);
    await page.waitForTimeout(500);
    expect(patches).toHaveLength(0);
  });
});
