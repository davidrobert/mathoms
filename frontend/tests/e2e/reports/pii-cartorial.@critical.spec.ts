/**
 * A40.l6 · ADR-337 critério 4 — gate RENDERIZADO de PII cartorial.
 *
 * O §Critério de aceite da lane pede as DUAS superfícies porque elas divergem:
 * a coluna de impressão tem 703px, um `<details>` colapsado pode não sair no
 * PDF **e ainda assim** estar no DOM servido, e o inverso também ocorre —
 * `print:hidden`/`print:block` mudam o que a folha recebe.
 *
 * Por que a fixture é mutada em memória e não vive em disco: uma fixture com
 * PII cartorial commitada seria varrida (e acusada) pelo `lint_no_real_pii`.
 * Mutar no `mockReportPage` mantém o repo limpo e o teste honesto — a fixture
 * CARREGA a PII, então "não aparece" é medição, não tautologia.
 *
 * ESCOPO — este spec mede o CLIENTE, porque ele mocka a API. A defesa tem duas
 * camadas e cada uma é provada no seu nível:
 *
 * 1. **Cliente (aqui)** — o card não pode ALCANÇAR campo cartorial. `descricao`,
 *    `endereco_canonical` e `imobiliaria_cnpj` são infectados de propósito: se o
 *    render tocar qualquer um, o gate acusa nas duas superfícies.
 * 2. **API** — `dividas[].descricao` o card renderiza VERBATIM por contrato (o
 *    rótulo nasce de vocabulário fechado, ADR-401 D4). Quem garante que ele chega
 *    limpo é `get_report_data`, que redige na leitura para alcançar artefato
 *    gravado antes do fix. Provado em
 *    `backend/tests/test_reports.py::test_report_data_redige_pii_de_artefato_armazenado`,
 *    com mutação. Injetar PII nesse campo aqui mediria o contrato da API pelo
 *    lado errado do mock.
 *
 * Prova de que o teste testa algo: o primeiro caso assere que o mutador achou
 * as 3 listas povoadas — medido em 2026-08-24, a fixture `medium` tem ZERO
 * imóveis e o mutador virava no-op.
 */
import { expect, test, type Page } from "@playwright/test";

import {
  generateReportPdf,
  normalizarTexto,
  pdfToText,
  pdftotextInstalado,
  setupPrintReport,
} from "../helpers/report-pdf";

/** `degraded` porque é a única fixture com as TRÊS superfícies povoadas
 *  (2 imóveis, 7 excluídos, 2 dívidas). A canônica `medium` tem zero de cada:
 *  o mutador viraria no-op e o gate mediria ausência sobre lista vazia. */
const FIXTURE = "degraded" as const;
const LINHAS_ESPERADAS = { imoveis: 2, excluidos: 7, dividas: 2 };

/** Placeholders canônicos da ADR-319 — casam o shape do gate, o lint não acusa. */
const MATRICULA = "999.999";
const LOGRADOURO = "Rua Exemplo, 100";
const CEP = "00000-000";
const CPF = "123.456.789-09";
const CARTORIAL = `Apartamento matrícula ${MATRICULA}, ${LOGRADOURO}, CEP ${CEP}, CPF ${CPF}`;

/** A forma NORMALIZADA que `canonicalize()` emite para a descrição acima.
 *  Assertar só a grafia crua ficava verde com esta na tela (§Ataque A4). */
const CANONICO = "exemplo 100";

const PROIBIDO = [MATRICULA, LOGRADOURO, CEP, CPF, CANONICO, "mat:999999", "iptu:"];

/** Injeta PII cartorial em TODO campo que o card poderia alcançar — inclusive
 *  `endereco_canonical`, que é o campo legado que o #1569 passou a exibir. */
function injetarPiiCartorial(data: Record<string, unknown>): typeof LINHAS_ESPERADAS {
  const re = data.real_estate as Record<string, unknown> | undefined;
  const imoveis = (re?.imoveis as Record<string, unknown>[]) ?? [];
  const excluidos = (re?.excluded_properties as Record<string, unknown>[]) ?? [];
  const dividas =
    ((data.endividamento as Record<string, unknown> | undefined)?.dividas as Record<
      string,
      unknown
    >[]) ?? [];
  for (const im of imoveis) {
    im.descricao = CARTORIAL;
    im.endereco_canonical = CANONICO;
    im.endereco_display = null;
    im.imobiliaria_cnpj = "11.222.333/0001-81";
  }
  for (const ex of excluidos) ex.descricao = CARTORIAL;
  // `dividas[].descricao` NÃO é infectado — ver §ESCOPO no topo: o card o
  // renderiza por contrato, e quem garante a limpeza é a API.

  return { imoveis: imoveis.length, excluidos: excluidos.length, dividas: dividas.length };
}

async function textoDoBody(page: Page): Promise<string> {
  return normalizarTexto(await page.locator("body").innerText());
}

test.describe("PII cartorial não alcança superfície renderizada (A40.l6)", () => {
  test("o mutador encontra linhas para infectar — o gate não é tautologia", async ({ page }) => {
    // Sem isto o gate é vácuo: medido em 2026-08-24, a fixture `medium` tem
    // ZERO imóveis/dívidas, o mutador virava no-op e "PII não aparece" ficava
    // verde sobre lista vazia. Este assert é o que impede o falso-verde.
    let vistas = { imoveis: 0, excluidos: 0, dividas: 0 };
    await setupPrintReport(
      page,
      undefined,
      (data) => {
        vistas = injetarPiiCartorial(data);
      },
      FIXTURE,
    );
    expect(vistas).toEqual(LINHAS_ESPERADAS);
  });

  test("nenhum identificador cartorial no DOM servido", async ({ page }) => {
    await setupPrintReport(page, undefined, injetarPiiCartorial, FIXTURE);
    const corpo = await textoDoBody(page);
    for (const proibido of PROIBIDO) {
      expect(corpo, `"${proibido}" apareceu no DOM do relatório`).not.toContain(proibido);
    }
  });

  test("nenhum identificador cartorial na camada de texto do PDF", async ({ page }) => {
    test.skip(!pdftotextInstalado(), "pdftotext (poppler) ausente no runner");
    await setupPrintReport(page, undefined, injetarPiiCartorial, FIXTURE);
    const texto = normalizarTexto(pdfToText(await generateReportPdf(page)));
    expect(texto.length, "PDF sem camada de texto — o gate não mediria nada").toBeGreaterThan(500);
    for (const proibido of PROIBIDO) {
      expect(texto, `"${proibido}" apareceu no PDF exportado`).not.toContain(proibido);
    }
  });
});
