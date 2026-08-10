/**
 * Nota one-shot de recalibração da S7 (A40.l25 · ADR-360 §Nota one-shot).
 *
 * Cada teste corresponde a uma forma da nota MENTIR ou assustar: afirmar
 * monotonia, imprimir a probabilidade antiga (incomparável sob ADR-369 D2),
 * negar mudança de carteira num relatório mensal, ou ler como alarme.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RecalibracaoMcNote } from "@/components/report/sections/RecalibracaoMcNote";
import type { RecalibracaoMcData } from "@/lib/api";

const ANO: RecalibracaoMcData = {
  facetas: [{ faceta: "ano_cone", ano_anterior: 2046, ano_novo: 2049 }],
  periodo_anterior: "202512",
  competencia_mudou: true,
};

const PROB: RecalibracaoMcData = {
  facetas: [
    { faceta: "probabilidade_alvo", prazo_declarado_anos: 20, ano_alvo_declarado: 2046 },
  ],
  periodo_anterior: "202512",
  competencia_mudou: false,
};

describe("RecalibracaoMcNote", () => {
  it("nota ausente não renderiza nada", () => {
    const { container } = render(<RecalibracaoMcNote nota={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lista de facetas vazia não renderiza nada", () => {
    const vazia = { ...ANO, facetas: [] };
    const { container } = render(<RecalibracaoMcNote nota={vazia} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("faceta comparável imprime o par de anos em prosa, sem seta", () => {
    const { container } = render(<RecalibracaoMcNote nota={ANO} />);
    expect(container.textContent).toContain("de 2046 para 2049");
    // Seta lê mal em leitor de tela e depende de fonte no PDF.
    expect(container.textContent).not.toContain("→");
    // Ano nunca passa por formatador monetário nem ganha separador de milhar.
    expect(container.textContent).not.toContain("2.049");
  });

  it("competência diferente traz a cláusula de atribuição; igual, não", () => {
    const { container: comMudanca } = render(<RecalibracaoMcNote nota={ANO} />);
    expect(comMudanca.textContent).toContain("mistura essa revisão e a evolução");

    const mesmoPeriodo = { ...ANO, competencia_mudou: false };
    const { container: semMudanca } = render(<RecalibracaoMcNote nota={mesmoPeriodo} />);
    expect(semMudanca.textContent).not.toContain("mistura essa revisão");
  });

  it("faceta incomparável recusa a comparação e declara os DOIS sentidos", () => {
    const { container } = render(<RecalibracaoMcNote nota={PROB} />);
    expect(container.textContent).toContain("não se compara com o anterior");
    expect(container.textContent).toContain("maior ou menor");
    // "sempre mais conservador" deixou de valer sob ADR-369 D2.
    expect(container.textContent).not.toMatch(/sempre mais conservador|monoton/i);
  });

  it("nunca imprime probabilidade — não há par para a faceta incomparável", () => {
    const { container } = render(<RecalibracaoMcNote nota={PROB} />);
    expect(container.textContent).not.toMatch(/\d+\s?%/);
  });

  it("nunca afirma nada sobre a carteira do cliente — nem a negação", () => {
    for (const nota of [ANO, PROB]) {
      const { container } = render(<RecalibracaoMcNote nota={nota} />);
      expect(container.textContent).not.toMatch(/sua carteira/i);
      expect(container.textContent).not.toMatch(/erro|falha|estava errad|corrigimos/i);
    }
  });

  it("não usa jargão de estatística", () => {
    const { container } = render(<RecalibracaoMcNote nota={PROB} />);
    expect(container.textContent).not.toMatch(
      /Monte Carlo|percentil|erro-padrão|intervalo de confian|mc_version|P10|P50|P90/i,
    );
  });

  it("é informativa, não alarme, e declara que não pede ação", () => {
    render(<RecalibracaoMcNote nota={ANO} />);
    const alerta = screen.getByRole("status");
    // Âmbar é o tratamento de DEGRADAÇÃO de dado (PremissasFallbackAlert).
    expect(alerta.getAttribute("data-alert-severity")).toBe("info");
    expect(alerta.textContent).toContain("não pede nenhuma ação sua");
    expect(alerta.textContent).toContain("aparece só neste relatório");
  });

  it("nomeia a competência anterior por extenso, e degrada sem ela", () => {
    const { container } = render(<RecalibracaoMcNote nota={ANO} />);
    expect(container.textContent).toContain("dezembro de 2025");

    const semPeriodo = { ...ANO, periodo_anterior: null };
    const { container: degradado } = render(<RecalibracaoMcNote nota={semPeriodo} />);
    expect(degradado.textContent).toContain("Revisamos como calculamos");
    expect(degradado.textContent).not.toContain("Desde o seu relatório de");
  });

  it("as duas facetas juntas saem na ordem em que os números aparecem na seção", () => {
    const ambas = { ...ANO, facetas: [...ANO.facetas, ...PROB.facetas] };
    const { container } = render(<RecalibracaoMcNote nota={ambas} />);
    const texto = container.textContent ?? "";
    expect(texto.indexOf("Ano da meta")).toBeLessThan(texto.indexOf("A probabilidade agora"));
  });

  it("não racha entre páginas no PDF", () => {
    const { container } = render(<RecalibracaoMcNote nota={ANO} />);
    expect(container.firstElementChild?.className).toContain("break-inside-avoid");
  });
});
