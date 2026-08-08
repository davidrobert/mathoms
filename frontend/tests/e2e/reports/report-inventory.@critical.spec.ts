/**
 * Gate de inventário estrutural do relatório.
 *
 * ## Por que existe
 *
 * O gate visual (`sections.snapshots.visual.spec.ts`) compara **pixels**. Quando
 * um card some, a baseline só encolhe — e o diff de um PNG não é revisável em
 * PR, então a saída natural é rebaselinar. Foi o que aconteceu com o card
 * "Alocação · Atual vs Alvo": a A12 PR7 (#906) o fez depender de
 * `goals.alocacao_alvo.derived`, a fixture `medium` não tinha a chave, o card
 * sumiu e o #1290 congelou a perda. Ficou ~3 meses invisível. O mesmo mecanismo
 * manteve `report.print.pdf.png` congelado num error boundary por 3,5 meses.
 *
 * Este gate fecha a **classe**: falha nomeando o card que sumiu, em texto,
 * num diff que o revisor consegue ler.
 *
 * ## Assimetria de regeneração (o ponto todo)
 *
 * `MATHOMS_UPDATE_INVENTORY=1` só **acrescenta** entradas; nunca remove. Card
 * novo é regenerável (aditivo, baixo risco). **Card que sai exige apagar a
 * linha à mão**, e a linha apagada aparece no diff do PR. Sem essa assimetria
 * o arquivo vira a baseline PNG em texto: um comando de regeneração que lava
 * a perda de cobertura.
 *
 * ## Contrato da fixture
 *
 * `medium` é a fixture de **superfície completa**. "A fixture não tem o dado"
 * NÃO é justificativa aceitável para um card ausente — é exatamente o defeito
 * do #906. Ausência legítima é card que o produto removeu, e aí a linha sai
 * com justificativa no corpo do PR.
 *
 * Escopo v1: superfície de tela, tema claro, fixture `medium`. Print fica fora
 * (a caixa de página é 703px e o conjunto de cards pode divergir por design).
 *
 * Canônica: [[ADR-370]].
 */
import { test, expect } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { mockReportPage, waitForReportReady } from "../helpers/mock-report";

const EXPECTED_PATH = join(__dirname, "report-inventory.expected.json");
const UPDATE = process.env.MATHOMS_UPDATE_INVENTORY === "1";

type Inventory = Record<string, string[]>;

/** Títulos de `<ReportCard/>` por seção, varridos do DOM.
 *
 * Derivado da estrutura (`section.card-variant-*` + `h3` filho direto), não de
 * uma lista de títulos: card novo cai no inventário sozinho. `:scope > div > h3`
 * impede que um card aninhado tenha o título atribuído ao card externo.
 */
async function collectInventory(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const out: Record<string, string[]> = {};
    const sections = document.querySelectorAll("section[data-report-section]");
    for (const section of Array.from(sections)) {
      const titles: string[] = [];
      const cards = section.querySelectorAll('section[class*="card-variant-"]');
      for (const card of Array.from(cards)) {
        const heading = card.querySelector(":scope > div > h3");
        const text = heading?.textContent?.trim();
        if (text) titles.push(text);
      }
      out[(section as HTMLElement).id] = titles.sort();
    }
    return out;
  });
}

/** Espera o inventário parar de crescer antes de medir.
 *
 * Vários cards dependem de hook assíncrono (`useConsumoPontuais`,
 * `usePlannerReview`…). Medir cedo produziria ausência falsa — e gate que grita
 * lobo é gate que alguém desliga. Duas amostras iguais em sequência bastam;
 * `data-report-ready` já garante que o shell montou.
 */
async function collectStableInventory(
  page: import("@playwright/test").Page,
): Promise<Inventory> {
  let previous = JSON.stringify(await collectInventory(page));
  for (let attempt = 0; attempt < 10; attempt++) {
    await page.waitForTimeout(250);
    const current = await collectInventory(page);
    const serialized = JSON.stringify(current);
    if (serialized === previous) return current;
    previous = serialized;
  }
  return collectInventory(page);
}

function readExpected(): Inventory {
  return JSON.parse(readFileSync(EXPECTED_PATH, "utf-8")) as Inventory;
}

/** União com o observado — nunca remove. É aqui que a assimetria vive. */
function mergeAdditive(expected: Inventory, observed: Inventory): Inventory {
  const merged: Inventory = {};
  for (const key of new Set([...Object.keys(expected), ...Object.keys(observed)])) {
    const union = new Set([...(expected[key] ?? []), ...(observed[key] ?? [])]);
    merged[key] = [...union].sort();
  }
  return merged;
}

function diff(from: string[], to: string[]): string[] {
  const other = new Set(to);
  return from.filter((item) => !other.has(item));
}

test("inventário de cards do relatório bate com o esperado", async ({ page }) => {
  const { workspaceId, reportId } = await mockReportPage(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`/reports/${reportId}?workspace=${workspaceId}`);
  await waitForReportReady(page);

  const observed = await collectStableInventory(page);

  // Âncora anti-fail-open: rota que crasha ou seletor que apodrece produzem
  // inventário vazio, e todo assert de ausência passaria à toa.
  const total = Object.values(observed).reduce((n, list) => n + list.length, 0);
  expect(
    Object.keys(observed).length,
    "nenhuma seção encontrada — o relatório não renderizou (vacuidade, não sucesso)",
  ).toBeGreaterThan(0);
  expect(
    total,
    "nenhum card encontrado — seletor de card apodreceu ou o relatório crashou",
  ).toBeGreaterThan(0);

  // Em UPDATE as asserções continuam valendo sobre o arquivo já mesclado: as
  // adições são absorvidas (não falham), as REMOÇÕES seguem falhando. Sair
  // cedo aqui daria verde a quem regenerou com um card faltando, e a falha só
  // apareceria no CI.
  let expected = readExpected();
  if (UPDATE) {
    expected = mergeAdditive(expected, observed);
    writeFileSync(EXPECTED_PATH, `${JSON.stringify(expected, null, 2)}\n`, "utf-8");
  }

  const missingSections = diff(Object.keys(expected), Object.keys(observed));
  expect(
    missingSections,
    `seção(ões) sumiram do relatório: ${missingSections.join(", ")}. ` +
      "Regenerar NÃO conserta — apague a linha à mão e justifique no PR.",
  ).toEqual([]);

  for (const sectionId of Object.keys(expected)) {
    const gone = diff(expected[sectionId], observed[sectionId] ?? []);
    expect(
      gone,
      `${sectionId}: card(s) sumiram — ${gone.map((t) => `"${t}"`).join(", ")}. ` +
        "Se foi remoção deliberada, apague a linha do report-inventory.expected.json " +
        "à mão e justifique no PR. MATHOMS_UPDATE_INVENTORY=1 só acrescenta.",
    ).toEqual([]);
  }

  const added = Object.keys(observed).flatMap((sectionId) =>
    diff(observed[sectionId], expected[sectionId] ?? []).map((t) => `${sectionId}: "${t}"`),
  );
  expect(
    added,
    `card(s) novos não declarados — ${added.join(", ")}. ` +
      "Rode `MATHOMS_UPDATE_INVENTORY=1 npx playwright test tests/e2e/reports/report-inventory.@critical.spec.ts --project=chromium` e comite o diff.",
  ).toEqual([]);
});
