/**
 * a11y gate por seção — Lane `report-a11y-finalize` item 2.
 *
 * Roda `@axe-core/playwright` em /reports/[id] (fixture medium) com gate
 * em `critical+serious` (decisão D1). Cada seção visível recebe scan
 * isolado para que falha aponte direto o componente.
 *
 * Roda no step `Report render gate` de `frontend-checks` (job que está em
 * `all-green.needs`), logo bloqueia merge. Antes de 2026-08-08 a tag
 * `@critical` era o único sinal de que isso deveria acontecer, e não
 * acontecia: nenhum job executava este arquivo, e ele acumulou 3 falhas —
 * 2 de fixture e 1 violação real de contraste em S8 — sem ninguém ver.
 * `@critical` no nome não é gate; gate é estar num job exigido.
 */
import { test, type Page } from "@playwright/test";
import { expectNoA11yViolations } from "../helpers/axe";
import {
  mockReportPage,
  plannerReviewStub,
  waitForReportReady,
  type PlannerReviewFixture,
} from "../helpers/mock-report";

// V0 (SNAPSHOT_CHANGELOG_V3 W4/D6) — renderiza quando a fixture tem
// `comparisons` (medium.json inclui o bloco desde a V0).
// A40.l22 — `S_parecer` entra aqui: o estado default é o empty (mock devolve
// 404), e os dois estados novos ganham bloco próprio abaixo, com tema.
const STRATEGIC_SECTIONS = [
  "V0", "S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10", "S_parecer",
];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];
// ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA removido.

/** Seções listadas acima que a fixture `medium` **não faz montar**.
 *
 * Mesma allowlist (e mesmos dois membros) de `sections.snapshots.visual.spec.ts`,
 * pelo mesmo motivo — as duas retornam `null` por hide-when-empty:
 * - `S4`    — `data.real_estate` ausente (ADR-216 Onda 6).
 * - `APP_C` — `cenarios_conjuge` é `{}` e não há `programa_milhas`, logo
 *   `hasCenarios`/`hasMilhas` são falsos (ADR-167). A chave `cenarios_conjuge`
 *   **existe** na fixture, só está vazia: ler o topo do JSON dá a impressão de
 *   que a seção monta.
 *
 * O #1295 fechou isso no spec visual e este ficou de fora — `S4` seguia em
 * `STRATEGIC_SECTIONS` esperando um `waitForSelector` que só podia estourar, e
 * o loop de apêndices pulava qualquer seção ausente com `test.skip` puro.
 *
 * É allowlist, não decoração: qualquer OUTRA seção que deixe de montar vira
 * falha. Sem isso, regressão de render (seção sumiu por bug) viraria job verde
 * — e um skip condicional passa verde num CI limpo, que é o modo de falha que
 * já custou 4 meses de baselines órfãs aqui. */
const SECTIONS_NOT_IN_MEDIUM_FIXTURE = new Set(["S4", "APP_C"]);

/** Espera a seção montar, ou decide entre skip declarado e falha.
 *
 * O `waitFor` (e não um `count()` seco) é deliberado: em runner lento a seção
 * pode montar depois do `data-report-ready`, e aí `count()===0` viraria um
 * "não montou" **falso** — vermelho confuso, do tipo que ensina a ignorar o
 * gate. O custo do wait só é pago pelas 2 seções declaradas ausentes. */
async function waitForSectionOrSkip(
  page: Page,
  sectionId: string,
): Promise<string | null> {
  const selector = `section#${sectionId}[data-report-section]`;
  const montou = await page
    .locator(selector)
    .waitFor({ state: "attached", timeout: 5_000 })
    .then(() => true, () => false);
  if (montou) return selector;
  if (!SECTIONS_NOT_IN_MEDIUM_FIXTURE.has(sectionId)) {
    throw new Error(
      `seção ${sectionId} não montou com a fixture atual. Se isso for ` +
        `deliberado, adicione-a a SECTIONS_NOT_IN_MEDIUM_FIXTURE; caso ` +
        `contrário é regressão de render.`,
    );
  }
  test.skip(true, `seção ${sectionId} não montada com a fixture medium`);
  return null;
}

test.describe("Report a11y @critical", () => {
  test("relatório completo (modo estratégico) sem violações critical+serious", async ({
    page,
  }) => {
    const { workspaceId, reportId } = await mockReportPage(page);
    await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
    await waitForReportReady(page);

    await expectNoA11yViolations(page, {
      selector: '[data-report-scope]',
    });
  });

  for (const sectionId of STRATEGIC_SECTIONS) {
    test(`seção ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const selector = await waitForSectionOrSkip(page, sectionId);
      if (!selector) return;
      await expectNoA11yViolations(page, { selector });
    });
  }

  for (const sectionId of APPENDICES) {
    test(`apêndice ${sectionId} sem violações critical+serious`, async ({ page }) => {
      const { workspaceId, reportId } = await mockReportPage(page);
      await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
      await waitForReportReady(page);

      const selector = await waitForSectionOrSkip(page, sectionId);
      if (!selector) return;
      await expectNoA11yViolations(page, { selector });
    });
  }
});

// ADR-168 (A8.4 PR4): Modo USA removido — bloco describe USA deletado.

/** A40.l22 — os 2 estados novos de `S_parecer`, em light E dark.
 *
 * O bloco acima cobre `S_parecer` no estado default (empty, 404). Estes dois
 * têm DOM diferente — o retido é um `Alert` com link, o parcial acrescenta uma
 * nota e um 3º contador na caption — e o critério da lane pede axe nos dois
 * temas, porque o contraste é o que muda entre eles.
 */
const PARECER_STATES: PlannerReviewFixture[] = ["retido", "parcial"];
const THEMES = ["light", "dark"] as const;

test.describe("S_parecer degradado — a11y @critical", () => {
  for (const plannerReview of PARECER_STATES) {
    for (const theme of THEMES) {
      test(`S_parecer ${plannerReview} — ${theme} sem violações critical+serious`, async ({
        page,
      }) => {
        // next-themes lê `localStorage` antes do mount; injetar depois do goto
        // produziria flash light→dark e mediria o tema errado.
        await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
        const { workspaceId, reportId } = await mockReportPage(page, {
          plannerReview: plannerReviewStub(plannerReview),
        });
        await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
        await waitForReportReady(page);

        const selector = "section#S_parecer[data-report-section]";
        await page.waitForSelector(selector, { timeout: 5_000 });
        // Controle positivo: sem isto, um estado que não montou passaria verde.
        await page.waitForSelector(
          plannerReview === "retido"
            ? '[data-testid="parecer-retained"]'
            : '[data-testid="parecer-retencao-parcial"]',
          { timeout: 5_000 },
        );
        await expectNoA11yViolations(page, { selector });
      });
    }
  }
});
