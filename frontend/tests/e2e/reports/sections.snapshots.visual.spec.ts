/**
 * Snapshots por seção (light + dark) — Lane `report-a11y-finalize` item 3.
 *
 * Não-`@critical` (lento, 28 snapshots). Roda apenas no projeto `visual`
 * do `playwright.config.ts` (PW_VISUAL=1 no CI dedicado), porque
 * snapshots são OS/font-rendering específicos e baselines devem vir do
 * runner Linux.
 *
 * Decisão D3 do track: spec mobile fica **fora** desta lane (lane futura
 * `report-mobile-spec` quando produto decidir o que sai em <767px).
 * Aqui rodamos só desktop @ 1280×800.
 *
 * Cobertura (28 baselines = 14 alvos × {light, dark}):
 * - shell global (cover) × {light, dark}
 * - Estratégico: S1, S2, S3, S7, S8, S9, S10 + APP_A, APP_B, APP_D, APP_E
 * - `S_parecer` nos 2 estados de degradação (retido, parcial)
 *
 * `S4` e `APP_C` estão nas listas abaixo mas NÃO geram baseline com a fixture
 * `medium` — ver `SECTIONS_NOT_IN_MEDIUM_FIXTURE`.
 *
 * ADR-151 (Direção E): Modo Tático removido. ADR-168 (A8.4 PR4): Modo USA
 * removido — Estratégico é o modo único. As 20 baselines órfãs desses dois
 * modos foram deletadas em 2026-08-08; sobreviveram ~4 meses à remoção do
 * código porque nada cruza PNG em disco com teste existente.
 *
 * Baselines vivem em `sections.snapshots.visual.spec.ts-snapshots/` (default
 * do Playwright, irmão deste arquivo).
 * Atualização: `npm run test:e2e -- --project=visual --grep sections.snapshots --update-snapshots`
 * (em CI Linux, nunca local em macOS — pixel rendering diverge).
 */
import { test, expect, type Page } from "@playwright/test";
import {
  mockReportPage,
  plannerReviewStub,
  waitForReportReady,
} from "../helpers/mock-report";

const VIEWPORT = { width: 1280, height: 800 };

const STRATEGIC_SECTIONS = ["S1", "S2", "S3", "S4", "S7", "S8", "S9", "S10"];
const APPENDICES = ["APP_A", "APP_B", "APP_C", "APP_D", "APP_E"];

const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];

/** A40.l22 — os 2 estados de degradação de `S_parecer`.
 *
 * `S_parecer` fica FORA de `STRATEGIC_SECTIONS` acima de propósito: no estado
 * default (404) a seção é um empty state de 3 linhas, e uma baseline dele não
 * detectaria nada. O que muda de fato é o DOM dos estados novos.
 */
const PARECER_STATES = ["retido", "parcial"] as const;

/** Seções listadas acima que a fixture `medium` **não faz montar**.
 *
 * Ambas retornam `null` por hide-when-empty, e o dado que as ligaria não
 * existe na fixture:
 * - `S4`    — `data.real_estate` ausente (ADR-216 Onda 6).
 * - `APP_C` — `cenarios_conjuge` é `{}` e não há `programa_milhas`, então
 *   `hasCenarios`/`hasMilhas` são falsos (ADR-167). Atenção: a chave
 *   `cenarios_conjuge` **existe** na fixture — só está vazia. Ler o topo do
 *   JSON dá a impressão de que a seção monta.
 *
 * As baselines das duas foram deletadas em 2026-08-08: eram do #174 (abril),
 * de quando a fixture ainda ligava as seções, e nunca mais foram exercitadas.
 * Mantê-las era o pior dos mundos — no dia em que alguém popular a fixture, o
 * Playwright compararia contra um PNG de 4 meses que ninguém revisou.
 *
 * O que cada uma perde ao sair daqui é DIFERENTE — medido em 2026-08-08 sobre
 * as 6 fixtures de `tests/e2e/fixtures/reports/`:
 * - `S4` perde só o baseline de pixel. Continua com cobertura estrutural em
 *   `sections.fixtures.smoke.visual.spec.ts`, que a trata como **required** em
 *   4 fixtures (`degraded`, `large-values`, `long-strings`, `sparse-data` — as
 *   que têm `real_estate`). `medium` é uma das 2 sem.
 * - `APP_C` não tem cobertura **nenhuma**: `cenarios_conjuge.labels` está vazia
 *   nas 6 fixtures e nenhuma tem `programa_milhas`, e o smoke a lista em
 *   `APPENDICES_OPTIONAL`. `StressScenarioCard` não é renderizado por teste
 *   algum. Esse é o buraco real — S4 é o menor dos dois problemas.
 *
 * Ligar as duas aqui é trabalho separado: rebaseline no runner Linux **com
 * revisão visual humana** das PNGs novas. Para `S4` o dado sai de copiar o
 * bloco `real_estate` de outra fixture; para `APP_C` é preciso autorar
 * `cenarios_conjuge` do zero, porque não existe em lugar nenhum.
 *
 * Esta lista é allowlist, não decoração: qualquer OUTRA seção que deixe de
 * montar vira falha. Sem isso, o `test.skip` abaixo transformava regressão de
 * render (seção sumiu por bug) em job verde. */
const SECTIONS_NOT_IN_MEDIUM_FIXTURE = new Set(["S4", "APP_C"]);

async function setupReport(page: Page, theme: Theme): Promise<void> {
  // next-themes lê localStorage key="theme" antes do mount — injetar
  // ANTES de qualquer goto evita flash light → dark no snapshot.
  await page.addInitScript((t) => {
    localStorage.setItem("theme", t);
  }, theme);

  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize(VIEWPORT);
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);

  // A40.l53 — sem esta afirmação, o projeto perder `contextOptions.reducedMotion`
  // volta a ser invisível: os snapshots simplesmente ficariam flaky de novo, e o
  // vermelho pareceria drift de baseline. `reducedMotion` NÃO é chave de topo de
  // `use` nesta versão — escrita ali, vira no-op silencioso.
  const semMovimento = await page.evaluate(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  if (!semMovimento) {
    throw new Error(
      "projeto `visual` sem `contextOptions.reducedMotion: 'reduce'` — o Chart.js " +
        "volta a animar e o gate de estabilidade do Playwright passa a perseguir " +
        "o redesenho que a própria captura provoca (A40.l53)",
    );
  }
}

async function snapshotSection(
  page: Page,
  sectionId: string,
  theme: Theme,
  /** A40.l22 — nome da baseline quando a MESMA seção tem >1 estado. */
  baselineId: string = sectionId,
): Promise<void> {
  const selector = `section#${sectionId}[data-report-section]`;
  const exists = await page.locator(selector).count();
  if (exists === 0) {
    if (!SECTIONS_NOT_IN_MEDIUM_FIXTURE.has(sectionId)) {
      throw new Error(
        `seção ${sectionId} não montou com a fixture atual. Se isso for ` +
          `deliberado, adicione-a a SECTIONS_NOT_IN_MEDIUM_FIXTURE e delete a ` +
          `baseline órfã; caso contrário é regressão de render.`,
      );
    }
    test.skip(true, `seção ${sectionId} não montada com a fixture medium`);
    return;
  }
  await page.locator(selector).scrollIntoViewIfNeeded();
  await expect(page.locator(selector)).toHaveScreenshot(
    `${baselineId}.${theme}.png`,
    {
      // Tolerância proporcional. Threshold anterior `maxDiffPixels: 200`
      // (~0.007% em S2) gerava flake crônico: PRs #147-#165 mergeavam com
      // gate red mesmo sem regressão real. NÃO combinar com `maxDiffPixels`
      // absoluto — Playwright usa `Math.min(absoluto, ratio×area)`, então o
      // piso absoluto anula o ratio em imagens grandes.
      //
      // A justificativa original deste 2.5% era "chart.js canvas tem
      // não-determinismo inerente entre runs (~1-2% da imagem)". MEDIDO em
      // 2026-08-30 (A40.l103): dois `workflow_dispatch` do MESMO SHA
      // (`ec50cbd7`; runs 33323919131 / 33323920209) devolveram as 28
      // baselines BYTE-IDÊNTICAS. Entre runs não há ruído — n=2. O que este
      // número absorve de fato é reflow dirigido por COMMIT: 1px de
      // deslocamento marca 9,58% numa imagem curta e o realinhamento `dy=±1`
      // zera. Ou seja, 2.5% aqui é folga herdada, não medida — é por isso que
      // `cover` e `sumario-executivo` abaixo mediram a sua (0.0003) em vez de
      // herdar esta. Re-calibrar este valor é lane própria; não o copie para
      // baseline nova sem medir o par (piso de ruído, menor mudança que
      // precisa reprovar).
      maxDiffPixelRatio: 0.025,
      // Mascarar elementos cuja renderização exata não importa para
      // detecção de regressão estrutural (ex.: timestamps).
      mask: [page.locator("[data-mask-snapshot]")],
    },
  );
}

// ─── Estratégico (default mode) ────────────────────────────────────────

test.describe("Snapshots — modo estratégico", () => {
  for (const theme of THEMES) {
    for (const sectionId of [...STRATEGIC_SECTIONS, ...APPENDICES]) {
      test(`${sectionId} — ${theme}`, async ({ page }) => {
        await setupReport(page, theme);
        await snapshotSection(page, sectionId, theme);
      });
    }
  }
});

/** FABs do `FloatingNav` — `position: fixed`, logo entram no recorte de
 * QUALQUER locator que caia no canto inferior direito da viewport. Pior que
 * estático: `data-visible` deles é função da posição de scroll, que é função da
 * altura da página — então mudança em seção não relacionada mudaria a baseline.
 * É o mesmo acoplamento estranho que o recorte page-level da capa tinha. */
function floatingNavMask(page: Page) {
  return page.locator(
    'button[aria-label="Voltar ao topo"], ' +
      'button[aria-label="Ir para o final"], ' +
      'button[aria-label="Abrir índice do relatório"]',
  );
}

// ─── Cover (estratégico, fullPage do hero) ─────────────────────────────

test.describe("Snapshots — cover (hero)", () => {
  for (const theme of THEMES) {
    test(`cover — ${theme}`, async ({ page }) => {
      await setupReport(page, theme);
      // Controle positivo: o `<header data-report-cover>` do ReportCover.
      // NÃO volte a procurar o texto do badge — de 2026-04-26 (v2.F.3b,
      // `db6cf6f7`) a 2026-08-11 este teste procurou `text="Relatório Premium"`,
      // string que o componente não pode produzir (o shell não passa `badge`,
      // então `resolveBadge` devolve "Relatório · Família X" ou "Relatório
      // Patrimonial"), e o `test.skip` engoliu 107 dias de cobertura da capa:
      // as duas baselines seguiram commitadas sem nunca serem comparadas.
      await page.waitForSelector("[data-report-cover]", { timeout: 10_000 });
      // Os meta-cards são o conteúdo que a baseline precisa provar: sem eles
      // montados, o screenshot congela um hero pela metade.
      await page.waitForSelector("[data-report-cover] >> text=Gerado em", {
        timeout: 10_000,
      });
      // Recorte no locator, NÃO page-level. O `clip: {0,0,1280,720}` anterior
      // era medido a partir do topo da página, e a nav é `position: sticky;
      // top: 0` — então os ~52px de cima desta "baseline da capa" eram nav, e
      // mais abaixo entravam o `aside.sidebar-toc` (240px) e o conteúdo pós-
      // header. O `<header data-report-cover>` era ~1/3 da própria imagem.
      //
      // O acoplamento não era teórico: em 2026-08-27 a A40.l88 (#1755) inseriu
      // o chip `2.5` na nav e esta baseline reprovou com bbox (715,16,1071,36)
      // — inteiramente dentro da nav, sem tocar o header. Quem viu "cover"
      // vermelho foi procurar a causa no ReportCover e não achou nada.
      //
      // Tolerância MEDIDA nos dois extremos, não escolhida:
      //
      //   piso de ruído  = 0px — dois `workflow_dispatch` do MESMO SHA (runs
      //                    33323919131 / 33323920209, `ec50cbd7`) devolveram as
      //                    28 baselines byte-idênticas. n=2.
      //   menor mudança  = 304px light / 310px dark (~0,076%) — acrescentar
      //   que importa      "XX" ao `subtitle` do header, medido em run com a
      //                    baseline apagada (run 33325757975), bbox 32×19.
      //
      // 0.0003 (≈120px nesta imagem) fica ACIMA do ruído e ABAIXO da menor
      // mudança que precisa reprovar. O primeiro valor tentado, 0.005, deixava
      // a mudança de texto passar por folga de 6,6× — a classe conhecida do
      // repo em que o `<h2>` da S9 mudou e o gate ficou verde.
      //
      // NÃO herda o `maxDiffPixelRatio: 0.025` do helper de seção: aquele número
      // existe para absorver não-determinismo de canvas do chart.js, e nem o
      // header nem a grade de KPI têm canvas.
      //
      // Armadilha de método, para quem for re-medir: `--update-snapshots` só
      // reescreve a baseline quando a comparação FALHA. Mutação sob a tolerância
      // devolve o arquivo antigo intacto, e a comparação parece dar 0px — que é
      // o arquivo comparado consigo mesmo, não medição. Apague a baseline na
      // branch de sonda para forçar a escrita.
      await expect(page.locator("[data-report-cover]")).toHaveScreenshot(
        `cover.${theme}.png`,
        {
          maxDiffPixelRatio: 0.0003,
          mask: [page.locator("[data-mask-snapshot]"), floatingNavMask(page)],
        },
      );
    });
  }
});

// ─── Sumário Executivo (Hero KPI) ──────────────────────────────────────
//
// Esta baseline nasce junto com o estreitamento acima, e não é escopo novo:
// é a cobertura que o `clip` de 720px vinha dando POR ACIDENTE ao
// `<section id="sumario-executivo">` (Patrimônio Líquido, Patrimônio
// Investível, Reserva de Emergência, Taxa de Poupança, IF, Score). Estreitar
// sem isto derrubaria em silêncio o único gate sobre o bloco de números-
// manchete do relatório — medido: o bloco NÃO está em `STRATEGIC_SECTIONS`,
// não tem `data-report-section`, e não aparece em
// `report-inventory.expected.json` (17 seções, nenhuma delas o sumário).
//
// Seletor próprio, sem `data-report-section`, de propósito: aquele atributo
// faria o bloco entrar no inventário da [[ADR-370]], que roda em TODO PR sem
// label — mudança de contrato que não pertence a um PR de recorte de teste.
// O buraco de inventário fica registrado na lane, com dono.
test.describe("Snapshots — sumário executivo (hero KPI)", () => {
  for (const theme of THEMES) {
    test(`sumario-executivo — ${theme}`, async ({ page }) => {
      await setupReport(page, theme);
      const sel = "section#sumario-executivo";
      await page.waitForSelector(sel, { timeout: 10_000 });
      // Controle positivo: sem um card montado, o screenshot congelaria uma
      // grade vazia e a baseline ficaria verde sobre o DOM errado.
      await page.waitForSelector(`${sel} >> text=Patrimônio Líquido`, {
        timeout: 10_000,
      });
      await page.locator(sel).scrollIntoViewIfNeeded();
      await expect(page.locator(sel)).toHaveScreenshot(
        `sumario-executivo.${theme}.png`,
        {
          maxDiffPixelRatio: 0.0003,
          mask: [page.locator("[data-mask-snapshot]"), floatingNavMask(page)],
        },
      );
    });
  }
});

// Cobertura que o recorte largo dava e que NÃO é reposta aqui, declarada de
// propósito (o padrão do arquivo é declarar o gap, cf. SECTIONS_NOT_IN_MEDIUM_FIXTURE):
//
// - `ReportTopNav` — sem baseline. Criar uma agora fossilizaria a truncagem da
//   trilha ("SÍNTESE" → "SÍNTI"), que é exatamente o defeito que a A40.l102
//   está consertando; baseline de nav vale mais DEPOIS daquele fix, e o gate
//   daquela lane é de alcançabilidade, não de pixel.
// - `ReportPremissasBlock` — sem baseline. É `<section>` sem
//   `data-report-section` e um `<details>` fechado por default, então o que o
//   recorte largo provava era uma linha de `<summary>`.
// - `aside.sidebar-toc` — sem baseline. É `no-print` e derivado de
//   `LAYOUT.navigation` via codegen; baseline ali reafirmaria o codegen.

// ADR-168 (A8.4 PR4): Modo USA removido — bloco USA `test.describe` deletado.
// Modo Estratégico cobre 100% do relatório.

// ─── A40.l22 · S_parecer degradado ─────────────────────────────────────

test.describe("Snapshots — S_parecer degradado", () => {
  for (const theme of THEMES) {
    for (const estado of PARECER_STATES) {
      test(`S_parecer ${estado} — ${theme}`, async ({ page }) => {
        await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
        const { workspaceId, reportId } = await mockReportPage(page, {
          plannerReview: plannerReviewStub(estado),
        });
        await page.setViewportSize(VIEWPORT);
        await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
        await waitForReportReady(page);
        // Controle positivo: sem isto, um estado que não montou geraria
        // baseline do empty state e o gate ficaria verde sobre o DOM errado.
        await page.waitForSelector(
          estado === "retido"
            ? '[data-testid="parecer-retained"]'
            : '[data-testid="parecer-retencao-parcial"]',
          { timeout: 5_000 },
        );
        await snapshotSection(page, "S_parecer", theme, `S_parecer-${estado}`);
      });
    }
  }
});
