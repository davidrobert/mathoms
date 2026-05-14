/**
 * E2E smoke — Parecer do Planejador @critical (ADR-199 Ato 5).
 *
 * Cobre o caminho premium: relatório aberto → S_parecer renderizada →
 * hero presente → risco crítico visível → movimento P0 com CTA "Promover".
 *
 * Estratégia: intercepta o endpoint `GET .../planner-review` via
 * `page.route` para evitar dependência de pipeline completo. Conecta com
 * relatório real (fixture do `upload-pipeline-report.spec`) ou pula
 * graciosamente quando backend não está acessível.
 *
 * Tagged @critical → gate de deploy.
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn } from "./helpers/auth";

const PARECER_PAYLOAD = {
  id: "pr-smoke",
  workspace_id: "ws-smoke",
  pipeline_run_id: "run-smoke",
  status: "Gerado",
  persona_hash: "a".repeat(64),
  manifest_version: "1.0",
  schema_version: "1.0",
  model_id: "anthropic/claude-sonnet-4",
  tier_at_generation: "premium",
  items_shown_count: 5,
  items_gated_count: 0,
  cost_usd_cents: 42,
  created_at: "2026-05-13T16:00:00Z",
  published_at: null,
  superseded_at: null,
  supersedes_id: null,
  superseded_by_id: null,
  immutable_hash: null,
  content: {
    version: "1.0",
    diagnostico_geral:
      "Família com reserva sólida, exposição imobiliária acima do recomendado para o perfil de risco.",
    pontos_fortes: [
      {
        titulo: "Reserva 12 meses",
        descricao: "Liquidez adequada para emergências.",
        tema_canonico: "Saúde de balanço",
        section_id: "S1",
      },
    ],
    riscos: [
      {
        severidade: "Crítica",
        titulo: "Concentração imobiliária 70%",
        descricao:
          "Patrimônio acima do teto recomendado em ativos imobiliários.",
        tema_canonico: "Alocação",
        evidencia: null,
        evidencia_path: null,
        section_id: "S4",
        confianca: "alta",
      },
    ],
    sugestoes_execucao: [
      {
        prioridade: "P0",
        acao: "Diversificar 15% do patrimônio imobiliário",
        impacto_qualitativo:
          "Reduz risco sistêmico imobiliário sem perder renda passiva.",
        tema_canonico: "Alocação",
        confianca: "alta",
        section_id: "S4",
        suggestion_dedup_key: "d".repeat(64),
        impacto_estimado: null,
        evidencia_path: null,
      },
    ],
    sugestoes_taticas: [],
    sugestoes_estrategicas: [],
    metricas: [],
    notas_metodologicas: [],
    meta: {
      tier_at_generation: "premium",
      persona_hash: "a".repeat(64),
      manifest_version: "1.0",
      schema_version: "1.0",
      model_id: "anthropic/claude-sonnet-4",
      generated_at: "2026-05-13T16:00:00Z",
      gated_counts: {
        pontos_fortes: 0,
        riscos: 0,
        sugestoes_execucao: 0,
        sugestoes_taticas: 0,
        sugestoes_estrategicas: 0,
        metricas: 0,
        notas_metodologicas: 0,
      },
    },
  },
};

test.describe("Parecer do Planejador @critical", () => {
  test("relatório premium renderiza S_parecer com hero + risco + movimento P0", async ({
    page,
    request,
  }, info) => {
    // Mock do endpoint do parecer antes de logar — captura primeira chamada.
    await page.route(
      /\/api\/v\d+\/workspaces\/[^/]+\/reports\/[^/]+\/planner-review$/,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(PARECER_PAYLOAD),
        });
      },
    );

    // Login fixture (cria workspace mínimo); navegação para `/reports` lista
    // relatórios — se nenhum disponível, pula (smoke validate só renderer).
    await ensureLoggedIn(page, request, info);
    await page.goto("/reports");

    // Procura primeiro relatório clicável (ou pula).
    const firstReportLink = page.locator('a[href^="/reports/"]').first();
    if (!(await firstReportLink.isVisible().catch(() => false))) {
      test.skip(
        true,
        "Nenhum relatório listado — smoke do parecer exige relatório aberto",
      );
      return;
    }
    await firstReportLink.click();
    await page.waitForLoadState("networkidle");

    // Hero do parecer presente
    const hero = page.getByTestId("parecer-hero");
    await expect(hero).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("parecer-tier-badge")).toHaveText(/Premium/);

    // Risco crítico
    await expect(
      page.getByText("Concentração imobiliária 70%"),
    ).toBeVisible();

    // Movimento P0 + CTA Promover
    const movimento = page.getByTestId("parecer-movimento-card").first();
    await expect(movimento).toBeVisible();
    await expect(movimento).toHaveAttribute("data-priority", "P0");
    await expect(
      page.getByTestId("movimento-promover").first(),
    ).toBeVisible();

    // Disclaimer fiduciário
    await expect(page.getByTestId("parecer-disclaimer")).toBeVisible();

    // Sigilo §13 — nenhuma menção a Perini/Cerbasi/AUVP no HTML renderizado
    const html = (await page.content()).toLowerCase();
    expect(html).not.toContain("perini");
    expect(html).not.toContain("cerbasi");
    expect(html).not.toContain("auvp");
  });
});
