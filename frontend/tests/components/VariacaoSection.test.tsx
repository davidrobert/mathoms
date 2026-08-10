/**
 * Tests — V0 sob mudança de base de consolidação ([[A40.l2]] §3c2b, eixo 10 do §Critério
 * de saída · [[ADR-190]] D6 §Emenda).
 *
 * O eixo existe porque o PR que liga o enforce é justamente quem tem incentivo a não olhar
 * para a V0. A medição que o fundamenta: a Taxa de Poupança **desce** 14,37 pp por mudança
 * de método e é a única linha renderizada — acusação vermelha isolada, sobre nada.
 *
 * Nível de RENDER, não de payload: `dedupeBySemanticKey` e o filtro de `stable` decidem o
 * que chega à tela, então asserção sobre o payload não prova o que o usuário lê.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { VariacaoSection } from "@/components/report/VariacaoSection";
import type { ComparisonItemRead, ReportAnalysisData } from "@/lib/api";

const TAXA: ComparisonItemRead = {
  section_id: "M_TAXA_POUPANCA",
  section_label: "Taxa de Poupança",
  before: 34.01,
  after: 19.64,
  delta_pct: -42.25,
  delta_signal: "down",
  direction_positive: "up",
  unit: "pp",
};

const DIVIDA: ComparisonItemRead = {
  section_id: "M_DIVIDA",
  section_label: "Dívidas",
  before: 1000,
  after: 800,
  delta_pct: -20,
  delta_signal: "down",
  direction_positive: "down",
  unit: "brl",
};

function renderV0(
  baseChanged: boolean,
  items: ComparisonItemRead[] = [TAXA, DIVIDA],
) {
  const data = {
    comparisons: items,
    comparison_periods: { current: "202604", previous: "202603" },
    comparison_base_changed: baseChanged,
  } as unknown as ReportAnalysisData;
  return render(<VariacaoSection data={data} />);
}

function celulasDelta(): HTMLElement[] {
  return Array.from(document.querySelectorAll("td[aria-label]"));
}

describe("V0 · base de comparação inalterada", () => {
  it("julga: cor semântica e nome acessível com avaliação", () => {
    renderV0(false);

    const nomes = celulasDelta().map((c) => c.getAttribute("aria-label") ?? "");
    expect(nomes.some((n) => n.includes("avaliação ruim"))).toBe(true);
    expect(nomes.some((n) => n.includes("avaliação boa"))).toBe(true);
    expect(celulasDelta().map((c) => c.style.color)).toContain(
      "var(--semantic-danger)",
    );
    expect(screen.queryByTestId("v0-base-changed-note")).toBeNull();
  });
});

describe("V0 · base de comparação alterada", () => {
  // Mutação: `deltaColor` voltar a julgar sob base alterada. Este assert fica vermelho.
  it("nenhuma célula usa cor semântica", () => {
    renderV0(true);

    for (const celula of celulasDelta()) {
      expect(celula.style.color).toBe("var(--surface-muted-foreground)");
    }
  });

  // WCAG 1.4.1: a cor carrega julgamento, então neutralizar só a cor deixaria o leitor de
  // tela ouvindo "avaliação ruim" sobre uma célula cinza. Cor e texto caem JUNTOS.
  it("nenhum nome acessível contém avaliação, e a paridade cor ≡ texto se mantém", () => {
    renderV0(true);

    const celulas = celulasDelta();
    expect(celulas.length).toBeGreaterThan(0);
    for (const celula of celulas) {
      expect(celula.getAttribute("aria-label")).not.toContain("avaliação");
      expect(celula.getAttribute("aria-label")).toContain(
        "base de comparação alterada",
      );
      expect(celula.style.color).toBe("var(--surface-muted-foreground)");
    }
  });

  it("o estado é NOMEADO e ancorado — silêncio leria como 'nada mudou'", () => {
    renderV0(true);

    const nota = screen.getByTestId("v0-base-changed-note");
    expect(nota.textContent).toContain("comparam bases diferentes");
    for (const celula of celulasDelta()) {
      expect(celula.getAttribute("aria-describedby")).toBe(nota.id);
    }
  });

  // Em `unit: "brl"` o sinal do movimento vive só no glifo e na cor. Neutralizar a cor sem
  // preservar o glifo apagaria a direção: o usuário leria "20,0%" sem saber se subiu ou caiu.
  it("o glifo de direção sobrevive à neutralização", () => {
    renderV0(true, [DIVIDA]);

    expect(celulasDelta()[0].textContent).toContain("▼");
  });
});

describe("V0 · rollback do enforce", () => {
  // O flip pode ser desfeito, e o par volta a ser não-comparável — pela razão inversa. Sem
  // este caso, um gatilho escrito como "enforce ligado" passaria verde e deixaria a V0
  // julgando na volta.
  it("trata a volta como base alterada, igual à ida", () => {
    renderV0(true);
    const naVolta = celulasDelta().map((c) => c.style.color);

    expect(
      naVolta.every((cor) => cor === "var(--surface-muted-foreground)"),
    ).toBe(true);
    expect(screen.getByTestId("v0-base-changed-note")).toBeTruthy();
  });

  // A mutação irmã — gatilho por PRESENÇA em vez de DIFERENÇA entre as pontas — mora no
  // backend, onde o booleano nasce: `test_comparison_base_changed.py`. Aqui ela passaria
  // por vacuidade, porque este componente recebe o booleano pronto.
});
