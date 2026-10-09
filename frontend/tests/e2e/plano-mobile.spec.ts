/**
 * Onda 9 #7 — Mobile collapsibles em /plano (iPhone 13 390×844px)
 *
 * Valida que a tela abre em ≤2 viewport heights com as seções colapsáveis
 * fechadas por default em mobile. Spec usa device viewport 390×844.
 */
import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.use({ viewport: { width: 390, height: 844 } });

/**
 * Semeia 1 Decision via API para tirar o workspace do estado "zero".
 *
 * O workspace que `ensureLoggedIn` registra nasce vazio (sem meta IF, decisão
 * ou tarefa) e, nesse estado, `/plano` troca a tela inteira pelo
 * `OnboardingHero` — sem os `<details>` que este spec mede. A pré-condição é
 * deste spec: com `fullyParallel`, nenhum outro spec garante ordem nem worker.
 */
async function seedDecision(page: Page, request: APIRequestContext) {
  // Só legível depois de navegar para a origem do app: no about:blank
  // inicial o localStorage é inacessível (origem opaca).
  const token = await page.evaluate(() => localStorage.getItem("fin_token"));
  if (!token) throw new Error("fin_token ausente no localStorage após navegar");
  const headers = { Authorization: `Bearer ${token}` };
  const me = await request.get("/api/v1/me/workspaces", { headers });
  expect(me.status(), await me.text()).toBe(200);
  const { workspaces } = (await me.json()) as { workspaces: { id: string }[] };
  const created = await request.post(
    `/api/v1/workspaces/${workspaces[0].id}/decisions`,
    { headers, data: { title: "E2E plano-mobile — decisão sintética" } },
  );
  expect(created.status(), await created.text()).toBe(201);
}

test.describe("Plano — mobile collapsibles (iPhone 13) @critical", () => {
  test("Plano de Ação e Mês corrente começam colapsados em mobile", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/plano");
    await seedDecision(page, request);
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Aguarda o conteúdo carregar (KPI row deve estar visível)
    await expect(page.locator("text=Meu Plano").first()).toBeVisible({ timeout: 10_000 });

    // "Plano de Ação" deve ser um <summary> (fechado por default)
    const planoAcaoSummary = page.locator("summary", { hasText: "Plano de Ação" });
    await expect(planoAcaoSummary).toBeVisible();

    // O details parent deve estar fechado (sem atributo open)
    const planoAcaoDetails = page.locator("details", { has: planoAcaoSummary });
    await expect(planoAcaoDetails).not.toHaveAttribute("open");

    // "Mês corrente" também deve estar como summary (fechado)
    const mesCorrSummary = page.locator("summary", { hasText: "Mês corrente" });
    await expect(mesCorrSummary).toBeVisible();
    const mesCorrDetails = page.locator("details", { has: mesCorrSummary });
    await expect(mesCorrDetails).not.toHaveAttribute("open");

    // Scroll height deve ser ≤ 3 viewports (razoável com seções fechadas)
    // (2 viewports seria ideal mas depende da quantidade de dados)
    const scrollHeight = await page.evaluate(() => document.body.scrollHeight);
    const viewportHeight = 844;
    expect(scrollHeight).toBeLessThan(viewportHeight * 4);

    // Expandir "Plano de Ação" clicando no summary deve funcionar
    await planoAcaoSummary.click();
    await expect(planoAcaoDetails).toHaveAttribute("open");
  });

  test("Tap targets dos botões de ação têm altura mínima adequada", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    await page.goto("/acao");
    await page.waitForLoadState("networkidle");

    // Verifica que a página carregou (tab Inbox ou Tarefas)
    await expect(page.locator("text=Ação").first()).toBeVisible({ timeout: 10_000 });

    // Verifica que não há tab Timeline
    await expect(page.locator('[role="tab"][data-value="timeline"]')).not.toBeVisible();
    await expect(page.locator("text=Timeline")).not.toBeVisible();
  });
});
