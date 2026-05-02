/**
 * Pipeline review screen — UI dedicada para aprovar/editar StageReview.
 * ADR-158, entregável F (Playwright @critical).
 *
 * Status: stub. O cenário completo (run em needs_review com 2 reviews
 * pending → aprova um → edita outro → run volta a running → não há
 * mais card needs_review) depende de seed real no backend (criar
 * pipeline_run + stage_reviews via API ou helper). Hoje não há helper
 * `seedNeedsReviewRun` no e2e suite — implementação fica como follow-up.
 *
 * Smoke test: navega direto para a rota com runId fictício e valida que
 * a tela responde (mostra erro ou empty, sem crash). Cobre regressão
 * básica (rota existe, components renderizam).
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

test.describe("Pipeline review screen @critical", () => {
  test.setTimeout(60_000);

  test("rota /pipeline/runs/[id]/reviews carrega sem crash", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);
    // Run fictício — backend retornará 404 ou lista vazia. UI deve
    // renderizar empty state ou erro com retry, sem white screen.
    await page.goto("/pipeline/runs/00000000-0000-0000-0000-000000000000/reviews");
    // PageHeader sempre presente.
    await expect(
      page.getByRole("heading", { name: /Revisões pendentes/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
