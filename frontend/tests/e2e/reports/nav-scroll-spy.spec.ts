/**
 * A faixa sticky diz onde você está, e todo alvo dela tem pixel (A40.l104).
 *
 * Cinco defeitos conviviam aqui, e cada um era INERTE sob o teste dos outros —
 * por isso cada asserção abaixo mapeia 1:1 para um, e nenhuma passa por tabela:
 *
 * 1. o scroll-spy dos dois componentes morria na montagem (o efeito registrava
 *    zero elementos e nunca re-registrava) → `chips ativos ao longo do scroll`
 * 2. a eleição do ativo usava só as entradas que MUDARAM no disparo, então a
 *    faixa dizia `S2` onde o índice dizia `S8` → `faixa e índice concordam`
 * 3. a faixa nunca rolava o chip ativo para dentro do campo, e no compacto só
 *    o ativo expande o rótulo → `o chip ativo fica visível`
 * 4. chip sem `num` renderizava 12px em branco → `todo chip tem tinta`
 * 5. abaixo de md os 20 chips ficavam focáveis dentro de uma caixa de 0px,
 *    foco sem pixel algum (2.4.7) → `abaixo de md a faixa não é focável`
 *
 * Sem `@critical` de propósito: Firefox e WebKit divergem no timing de
 * `IntersectionObserver` e de `scrollIntoView`, e o valor aqui é o invariante,
 * não a paridade cross-browser. Assim roda só no projeto `chromium`, que não
 * filtra por tag — continua gateando todo PR.
 */
import { expect, test, type Page } from "@playwright/test";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const LARGO = { width: 1600, height: 900 };

async function abrir(page: Page, tocAberto = false): Promise<void> {
  await page.addInitScript((abrir) => {
    localStorage.setItem("theme", "light");
    if (abrir) localStorage.setItem("mathoms:report:toc-open", "true");
  }, tocAberto);
  const { workspaceId, reportId } = await mockReportPage(page, { fixture: "medium" });
  await page.setViewportSize(LARGO);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);
  await page.waitForTimeout(700);
}

/** Seção corrente segundo cada superfície, no scroll atual. */
async function lerAtivos(page: Page) {
  return page.evaluate(() => {
    const chip = document.querySelector("[data-report-topnav] a[data-active='true']");
    const rail = document.querySelector("[data-report-nav-rail]");
    const toc = document.querySelector("aside.sidebar-toc [data-toc-id][class*='brand-primary']");
    let chipVisivel: boolean | null = null;
    if (chip && rail) {
      const c = chip.getBoundingClientRect();
      const r = rail.getBoundingClientRect();
      chipVisivel = c.left >= r.left - 1 && c.right <= r.right + 1;
    }
    return {
      faixa: chip?.getAttribute("data-nav-id") ?? null,
      toc: toc?.getAttribute("data-toc-id") ?? null,
      chipVisivel,
    };
  });
}

async function rolarPara(page: Page, top: number): Promise<void> {
  await page.evaluate((y) => window.scrollTo({ top: y, behavior: "instant" as ScrollBehavior }), top);
  await page.waitForTimeout(450);
}

const PONTOS = [1500, 3500, 6000, 9000, 13000];

test("a faixa marca chips ativos ao longo do scroll", async ({ page }) => {
  await abrir(page);
  const vistos = new Set<string>();
  for (const top of PONTOS) {
    await rolarPara(page, top);
    const { faixa } = await lerAtivos(page);
    if (faixa) vistos.add(faixa);
  }
  // Antes do fix este conjunto era VAZIO em todos os pontos do documento.
  expect(vistos.size, `ativos vistos: ${[...vistos].join(",")}`).toBeGreaterThanOrEqual(3);
});

test("o índice montado desde o load também marca — é o usuário que volta", async ({ page }) => {
  await abrir(page, true);
  const vistos = new Set<string>();
  for (const top of PONTOS) {
    await rolarPara(page, top);
    const { toc } = await lerAtivos(page);
    if (toc) vistos.add(toc);
  }
  expect(vistos.size, `ativos do índice: ${[...vistos].join(",")}`).toBeGreaterThanOrEqual(3);
});

test("faixa e índice concordam sobre a seção corrente", async ({ page }) => {
  await abrir(page, true);
  for (const top of PONTOS) {
    await rolarPara(page, top);
    const { faixa, toc } = await lerAtivos(page);
    if (faixa && toc) expect(faixa, `divergiram em scrollTop=${top}`).toBe(toc);
  }
});

test("o chip ativo fica dentro do campo da faixa", async ({ page }) => {
  await abrir(page);
  for (const top of PONTOS) {
    await rolarPara(page, top);
    const { faixa, chipVisivel } = await lerAtivos(page);
    if (faixa) expect(chipVisivel, `chip ${faixa} fora do campo`).toBe(true);
  }
});

test("todo chip declarado tem tinta", async ({ page }) => {
  await abrir(page);
  const semTinta = await page.evaluate(() => {
    const chips = [...document.querySelectorAll("[data-report-nav-rail] a[data-nav-id]")];
    return chips
      .filter((a) => {
        const badge = a.querySelector("span");
        return !badge || badge.getBoundingClientRect().width === 0;
      })
      .map((a) => a.getAttribute("data-nav-id"));
  });
  expect(semTinta, "chip sem pixel visível").toEqual([]);
});

test("abaixo de md a faixa não é focável", async ({ page }) => {
  await abrir(page);
  await page.setViewportSize({ width: 390, height: 812 });
  await page.waitForTimeout(300);
  const estado = await page.evaluate(() => {
    const rail = document.querySelector("[data-report-nav-rail]") as HTMLElement;
    return {
      display: getComputedStyle(rail).display,
      focaveis: rail.querySelectorAll("a[href]").length,
      // a rota de navegação nessa faixa é o FAB, e ele precisa estar lá
      fab: !!document.querySelector("[aria-label='Abrir índice do relatório']"),
    };
  });
  expect(estado.display).toBe("none");
  expect(estado.fab, "sem faixa E sem FAB o relatório fica sem navegação").toBe(true);
});
