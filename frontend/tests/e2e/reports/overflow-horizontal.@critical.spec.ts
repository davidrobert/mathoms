/**
 * Nada do relatório vaza para fora da caixa em superfície estreita.
 *
 * Por que existe: em 390px a página NÃO rola horizontalmente
 * (`document.scrollWidth == innerWidth`), então o que passa da borda direita do
 * `<article>` não é "cortado feio" — é inalcançável. Em 2026-08-11 a coluna Δ da
 * tabela Antes/Depois (V0) ficava 301px fora, e nenhum gate via: o inventário de
 * seções (`report-inventory`) conta seções, o visual compara pixel em desktop, e
 * `print-text` inventaria títulos, não colunas.
 *
 * INSTRUMENTO — as escolhas abaixo não são cosméticas:
 *
 * 1. As duas superfícies são as CAIXAS ESTREITAS reais, não breakpoints
 *    bonitos: 390px é telefone, e 703px é a caixa de página A4 do
 *    `pdf_renderer.py` — o Chromium relayouta contra a página, não contra a
 *    janela, então `md:` (768px) NUNCA casa no PDF ([[ADR-381]]).
 *
 * 2. A varredura é DERIVADA do DOM (todo nó dentro do `<article>`), não uma
 *    lista de seletores. Card novo cai no gate sozinho — foi exatamente o modo
 *    de falha original, em que cada sintoma parecia um caso isolado.
 *
 * 3. Na TELA, conteúdo dentro de contêiner rolável não conta: o usuário alcança
 *    com gesto. No PAPEL conta, porque não existe gesto — por isso a superfície
 *    de print mede tudo.
 *
 * Anti-fail-open: se a rota crashar, o inventário fica vazio e a asserção passa
 * à toa. Por isso o teste primeiro exige que o relatório tenha renderizado
 * (mesma lição da baseline de print que era um error boundary).
 */
import { expect, test, type Page } from "@playwright/test";

import { mockReportPage, waitForReportReady, type FixtureName } from "../helpers/mock-report";
import { PRINT_AREA_PX } from "../helpers/report-pdf";

interface Vazamento {
  readonly node: string;
  readonly texto: string;
  readonly px: number;
}

const SUPERFICIES = [
  { nome: "telefone 390px", width: 390, height: 844, media: "screen" as const },
  { nome: "caixa A4 703px", width: PRINT_AREA_PX.width, height: PRINT_AREA_PX.height, media: "print" as const },
];

/** `medium` é o caso corrente; `large-values` estressa a largura dos valores. */
const FIXTURES: FixtureName[] = ["medium", "large-values"];

async function abrirRelatorio(
  page: Page,
  superficie: (typeof SUPERFICIES)[number],
  fixture: FixtureName,
): Promise<void> {
  await page.emulateMedia({ media: superficie.media });
  await page.addInitScript(() => localStorage.setItem("theme", "light"));
  const { workspaceId, reportId } = await mockReportPage(page, { fixture });
  await page.setViewportSize({ width: superficie.width, height: superficie.height });
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}&print=1`);
  await waitForReportReady(page);
  // Recharts/canvas terminam de dimensionar; sem isto o rect é o de antes do layout final.
  await page.waitForTimeout(1_200);
}

async function vazamentos(page: Page, ignorarRolavel: boolean): Promise<Vazamento[]> {
  return page.evaluate((ignorarRolavelArg) => {
    const article = document.querySelector("article[data-report-mode]");
    if (!article) return [];
    const limite = article.getBoundingClientRect().right;

    const dentroDeRolavel = (el: Element): boolean => {
      for (let p = el.parentElement; p && p !== article; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
      }
      return false;
    };

    const nome = (el: Element): string => {
      const secao = el.closest("[data-report-section]")?.id ?? "?";
      const testid = el.getAttribute("data-testid");
      const classes = (el.getAttribute("class") ?? "").split(/\s+/).slice(0, 3).join(".");
      return `[${secao}] ${el.tagName.toLowerCase()}${testid ? `@${testid}` : ""}${classes ? "." + classes : ""}`;
    };

    const achados: Vazamento[] = [];
    for (const el of article.querySelectorAll("*")) {
      // `sr-only` tem 1px de largura por construção; `truncate` corta com
      // reticências, que é affordance visível e escolha de design.
      if (el.classList.contains("sr-only") || el.classList.contains("truncate")) continue;
      if (ignorarRolavelArg && dentroDeRolavel(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || cs.position === "fixed") continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.right > limite + 1) {
        achados.push({
          node: nome(el),
          texto: (el.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 50),
          px: Math.round(r.right - limite),
        });
      }
    }
    // Só o nó mais externo de cada seção interessa: pai que vaza arrasta os filhos.
    const porSecao = new Map<string, Vazamento>();
    for (const a of achados) {
      const chave = a.node.split(" ")[0];
      const atual = porSecao.get(chave);
      if (!atual || a.px > atual.px) porSecao.set(chave, a);
    }
    return [...porSecao.values()];
  }, ignorarRolavel);
}

for (const superficie of SUPERFICIES) {
  for (const fixture of FIXTURES) {
    test(`nada vaza da caixa · ${superficie.nome} · ${fixture} @critical`, async ({ page }) => {
      await abrirRelatorio(page, superficie, fixture);

      // Âncora: sem relatório renderizado, zero vazamentos é vacuidade.
      await expect(page.locator("[data-report-section]").first()).toBeAttached();

      const achados = await vazamentos(page, superficie.media === "screen");
      const relato = achados
        .sort((a, b) => b.px - a.px)
        .map((v) => `  ${v.px}px além da caixa · ${v.node} :: ${v.texto}`)
        .join("\n");

      expect(achados, `conteúdo fora da caixa em ${superficie.nome}:\n${relato}`).toEqual([]);
    });
  }
}

test("a tabela Antes/Depois cabe na caixa A4 com folga @critical", async ({ page }) => {
  // A folga é o que o gate protege: antes deste teste a tabela exigia 691px numa
  // caixa de 703px, e um rótulo mais longo tirava a coluna do julgamento do PDF.
  await abrirRelatorio(page, SUPERFICIES[1], "medium");

  const medida = await page.evaluate(() => {
    const card = document.querySelector<HTMLElement>('[data-testid="variacao-section-card"]');
    const tabela = document.querySelector<HTMLTableElement>('[data-testid="v0-indicators-table"]');
    if (!card || !tabela) return null;
    const cs = getComputedStyle(card);
    const util =
      card.getBoundingClientRect().width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const clone = tabela.cloneNode(true) as HTMLTableElement;
    clone.style.cssText = "position:absolute;visibility:hidden;width:min-content;left:-9999px;top:0";
    document.body.appendChild(clone);
    const minContent = Math.ceil(clone.getBoundingClientRect().width);
    clone.remove();
    return { util: Math.round(util), minContent };
  });

  expect(medida, "a seção V0 não montou na fixture — o teste viraria vacuidade").not.toBeNull();
  expect(
    medida!.minContent,
    `a tabela exige ${medida!.minContent}px numa caixa de ${medida!.util}px`,
  ).toBeLessThan(medida!.util * 0.75);
});

test("a lista de indicadores substitui a tabela no telefone, sem perder o Δ @critical", async ({ page }) => {
  // A variante estreita tem de carregar cor, glifo e nome acessível JUNTOS:
  // perder um dos três é regressão de acessibilidade disfarçada de responsividade.
  await abrirRelatorio(page, SUPERFICIES[0], "medium");

  await expect(page.getByTestId("v0-indicators-table")).toBeHidden();
  const lista = page.getByTestId("v0-indicators-list");
  await expect(lista).toBeVisible();

  const itens = lista.locator("li");
  await expect(itens.first()).toBeVisible();

  const primeiro = itens.first();
  await expect(primeiro).toHaveAttribute("data-delta-signal", /up|down|stable/);
  const delta = primeiro.locator("[aria-label]").first();
  await expect(delta).toHaveAttribute("aria-label", /avaliação (boa|ruim)|base de comparação alterada/);
  await expect(delta).toContainText(/[▲▼•]/);
});
