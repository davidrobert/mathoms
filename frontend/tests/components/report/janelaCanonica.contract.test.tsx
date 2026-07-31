/**
 * A40.l3 — contrato de janela canônica (ADR-306 D1).
 *
 * D1: família mensalização (ratios/KPIs/médias) lê a **janela 12m**; agregado
 * histórico full-period é permitido **apenas rotulado**. O defeito que este
 * spec trava: o texto declara "últimos 12 meses" e cita o número do bloco
 * `full` — o valor canônico existe em `fluxo_caixa.janela_12m` e nunca era
 * lido (`rg janela_12m frontend/src` → 0 antes desta lane).
 *
 * Quatro propriedades tornam o spec não-tautológico:
 *  1. self-check de divergência da fixture (se alguém "consertar" a fixture,
 *     o spec falha em vez de virar tautologia silenciosa);
 *  2. assert de dois lados por site (contém o valor 12m E **não** contém o
 *     valor full);
 *  3. simetria `full` — sem `janela_12m` o texto tem de declarar todo o
 *     período (D1 permite full **com** rótulo; o proibido é número full sob
 *     rótulo 12m);
 *  4. discriminador de campo errado — `janela_12m.fluxo_liquido` (R$ 228.000)
 *     é um TOTAL de 12 meses, não a sobra mensal (R$ 11.000): 20× de
 *     inflação silenciosa se lido no lugar errado.
 *
 * A fixture é a **mesma** consumida pelo E2E (`janela-divergente.json`), para
 * que guarda e verificação renderizada não possam divergir.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const mockUseConsumoPontuais = vi.fn();
vi.mock("@/hooks/useConsumoPontuais", () => ({
  useConsumoPontuais: (...args: unknown[]) => mockUseConsumoPontuais(...args),
}));

const mockUseIsPrint = vi.fn(() => false);
vi.mock("@/components/report/hooks/useIsPrint", () => ({
  useIsPrint: () => mockUseIsPrint(),
}));

vi.mock("react-chartjs-2", () => ({
  Chart: ({ "aria-label": ariaLabel }: { "aria-label"?: string }) => (
    <div data-testid="chart-mock" aria-label={ariaLabel} />
  ),
}));

import { FluxoMensalChart } from "@/components/report/charts/FluxoMensalChart";
import { ConsumoConscienteCard } from "@/components/report/cards/ConsumoConscienteCard";
import { HeroKpiGrid } from "@/components/report/kpi/HeroKpiGrid";
import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "@/components/report/utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  ConsumoConscienteData,
  FluxoCaixaSummary,
  RatiosData,
} from "@/types/report-analysis";

const FIXTURE_PATH = join(
  __dirname,
  "../../e2e/fixtures/reports/janela-divergente.json",
);

interface JanelaFixture extends ReportAnalysisData {
  fluxo_caixa: Record<string, unknown>;
  consumo_consciente: Record<string, unknown>;
  ratios: Record<string, unknown>;
}

function loadFixture(): JanelaFixture {
  return JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as JanelaFixture;
}

const fx = loadFixture();
const fluxo = fx.fluxo_caixa as FluxoCaixaSummary;
const janela12m = (fx.fluxo_caixa as { janela_12m: Record<string, number> })
  .janela_12m;
const consumo = fx.consumo_consciente as unknown as ConsumoConscienteData;

const brl0 = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v);
const brl2 = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);

/** Valores canônicos (12m) e proibidos (full) sob rótulo 12m. */
const V = {
  receita12m: brl0(92_000),
  despesa12m: brl0(81_000),
  sobra12m: brl0(11_000),
  receitaFull: brl0(40_000),
  despesaFull: brl0(36_000),
  sobraFull: brl0(4_000),
  /** `janela_12m.fluxo_liquido` — TOTAL de 12 meses, nunca a sobra mensal. */
  totalIntervalo12m: brl0(228_000),
  pontuais12m: brl2(96_000),
  pontuaisFull: brl2(250_000),
} as const;

/** Bloco `full` sem `janela_12m` — reproduz `degraded.json` / pré-A28. */
function fluxoSemJanela12m(): FluxoCaixaSummary {
  const clone = JSON.parse(JSON.stringify(fluxo)) as Record<string, unknown>;
  delete clone.janela_12m;
  return clone as FluxoCaixaSummary;
}

function dataSemJanela12m(): ReportAnalysisData {
  return { ...fx, fluxo_caixa: fluxoSemJanela12m() } as ReportAnalysisData;
}

function contextText(): string {
  return document.querySelector("[data-chart-context]")?.textContent ?? "";
}

function conclusionText(): string {
  return document.querySelector("[data-chart-conclusion]")?.textContent ?? "";
}

beforeEach(() => {
  mockUseIsPrint.mockReturnValue(false);
  mockUseConsumoPontuais.mockReturnValue({
    items: [],
    total: 0,
    totalValor: 0,
    isLoading: false,
    error: null,
  });
});

// ─────────────────────────────────────────────────────────────────────
// 1. Self-check — a fixture precisa divergir, senão o resto é tautologia
// ─────────────────────────────────────────────────────────────────────

describe("fixture janela-divergente — self-check de divergência", () => {
  it("bloco full e janela_12m divergem por valor detectável", () => {
    expect(janela12m.receita_recorrente_mensal).not.toBe(
      fluxo.receita_recorrente_mensal,
    );
    expect(janela12m.despesa_mensal_media).not.toBe(fluxo.despesa_mensal_media);
    expect(consumo.total_pontuais_janela).not.toBe(consumo.total_pontuais);
    expect(fx.ratios.janela_referencia).toBe("12m");
  });

  it("rótulos de janela estão declarados nos dois blocos", () => {
    expect((fluxo as { janela?: string }).janela).toBe("full");
    expect(janela12m.janela).toBe("12m");
    expect((fluxo as { janela_meses?: number }).janela_meses).toBe(36);
    expect(janela12m.janela_meses).toBe(12);
  });

  it("aritmética da fixture fecha (sobra mensal ≠ fluxo_liquido do intervalo)", () => {
    const sobra12m =
      janela12m.receita_recorrente_mensal - janela12m.despesa_mensal_media;
    expect(sobra12m).toBe(11_000);
    expect(janela12m.fluxo_liquido).toBe(228_000);
    expect(janela12m.receita_total - janela12m.despesa_total).toBe(
      janela12m.fluxo_liquido,
    );
    expect(janela12m.despesa_consumo).toBe(
      janela12m.despesa_total - janela12m.transferencia_patrimonial,
    );
  });

  it("narrativas não sombreiam o builder determinístico", () => {
    const narrativas = fx.narrativas as Record<string, unknown> | undefined;
    expect(Object.keys(narrativas ?? {})).toEqual(["perfil_familia"]);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 2. Site: buildContext (FluxoMensalChart · [data-chart-context])
// ─────────────────────────────────────────────────────────────────────

describe("buildContext — rótulo 12m cita agregado de 12m", () => {
  it("janela 12m: exibe o agregado de janela_12m e não o do bloco full", () => {
    render(<FluxoMensalChart fluxo={fluxo} />);
    const text = contextText();
    expect(text).toContain("últimos 12 meses");
    expect(text).toContain(V.receita12m);
    expect(text).toContain(V.despesa12m);
    expect(text).not.toContain(V.receitaFull);
    expect(text).not.toContain(V.despesaFull);
  });

  it("simetria full: sem janela_12m o texto declara todo o período", () => {
    render(<FluxoMensalChart fluxo={fluxoSemJanela12m()} />);
    const text = contextText();
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain("36 meses");
    expect(text).toContain(V.receitaFull);
    expect(text).not.toContain(V.receita12m);
  });

  it("isPrint (superfície do PDF) usa o mesmo agregado de 12m", () => {
    mockUseIsPrint.mockReturnValue(true);
    render(<FluxoMensalChart fluxo={fluxo} />);
    const text = contextText();
    expect(text).toContain("últimos 12 meses");
    expect(text).toContain(V.receita12m);
    expect(text).not.toContain(V.receitaFull);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 3. Site: buildFallbackConclusion (render sem prop `conclusion`)
// ─────────────────────────────────────────────────────────────────────

describe("buildFallbackConclusion — sobra mensal e taxa canônica", () => {
  it("cita a sobra de 12m, não a do bloco full nem o total do intervalo", () => {
    render(<FluxoMensalChart fluxo={fluxo} />);
    const text = conclusionText();
    expect(text).toContain(V.sobra12m);
    expect(text).not.toContain(V.sobraFull);
    // Discriminador da armadilha de 20×: fluxo_liquido é TOTAL, não sobra.
    expect(text).not.toContain(V.totalIntervalo12m);
  });

  it("taxa de poupança vem de janela_12m.taxa_poupanca_recorrente (ex-aporte)", () => {
    render(<FluxoMensalChart fluxo={fluxo} />);
    const text = conclusionText();
    expect(text).toContain("25,0%");
    // Recomputada de despesa_mensal_media reintroduziria o aporte:
    // (92000-81000)/92000 = 12,0% — proibido por ADR-333.
    expect(text).not.toContain("12,0%");
  });

  it("uma taxa por relatório: chart == ratios.taxa_poupanca_recorrente_pct", () => {
    render(<FluxoMensalChart fluxo={fluxo} />);
    const esperada = `${Number(fx.ratios.taxa_poupanca_recorrente_pct)
      .toFixed(1)
      .replace(".", ",")}%`;
    expect(conclusionText()).toContain(esperada);
  });

  it("simetria full: rotula o período completo e omite a taxa (não recomputa)", () => {
    render(<FluxoMensalChart fluxo={fluxoSemJanela12m()} />);
    const text = conclusionText();
    expect(text).toContain(V.sobraFull);
    expect(text).toMatch(/todo o período/i);
    expect(text).not.toContain("Taxa de poupança");
  });
});

// ─────────────────────────────────────────────────────────────────────
// 4. Site: builder `fluxo_mensal` (texto que S2 realmente renderiza)
// ─────────────────────────────────────────────────────────────────────

describe("deriveChartConclusion('fluxo_mensal') — builder de S2", () => {
  it("cita agregado de 12m sob rótulo de 12m", () => {
    const text = deriveChartConclusion("fluxo_mensal", fx) ?? "";
    expect(text).toMatch(/12 meses/);
    expect(text).toContain(V.receita12m);
    expect(text).toContain(V.despesa12m);
    expect(text).toContain(V.sobra12m);
    expect(text).not.toContain(V.receitaFull);
    expect(text).not.toContain(V.despesaFull);
    expect(text).not.toContain(V.sobraFull);
    expect(text).not.toContain(V.totalIntervalo12m);
  });

  it("simetria full: rotula todo o período", () => {
    const text = deriveChartConclusion("fluxo_mensal", dataSemJanela12m()) ?? "";
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain(V.receitaFull);
    expect(text).not.toContain(V.receita12m);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 5. Site: SECTION_SUMMARIES.S2 (deriveSectionSummary)
// ─────────────────────────────────────────────────────────────────────

describe("deriveSectionSummary('S2') — mesma fonte, com rótulo", () => {
  it("cita a receita recorrente de 12m com rótulo", () => {
    const text = deriveSectionSummary("S2", fx) ?? "";
    expect(text).toMatch(/12 meses/);
    expect(text).toContain(V.receita12m);
    expect(text).not.toContain(V.receitaFull);
  });

  it("simetria full: rotula todo o período", () => {
    const text = deriveSectionSummary("S2", dataSemJanela12m()) ?? "";
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain(V.receitaFull);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 6. Site: ConsumoConscienteCard (KPI + rótulo)
// ─────────────────────────────────────────────────────────────────────

describe("<ConsumoConscienteCard /> — gastos pontuais da janela", () => {
  it("KPI usa total_pontuais_janela quando janela != full", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    const dl = document.querySelector("dl")?.textContent ?? "";
    expect(dl).toContain(V.pontuais12m);
    expect(dl).not.toContain(V.pontuaisFull);
  });

  it("rótulo de janela acompanha o KPI (nunca número sem rótulo)", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    expect(
      screen.getByLabelText("Sobre a janela dos gastos pontuais"),
    ).toBeInTheDocument();
  });

  it("equivalente em meses de aporte é rotulado como período completo", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    expect(
      screen.getByLabelText("Sobre a janela do equivalente em meses de aporte"),
    ).toBeInTheDocument();
  });

  it("simetria full: sem janela o KPI usa o total full com rótulo", () => {
    const semJanela = { ...consumo, janela: undefined, janela_meses: undefined };
    render(<ConsumoConscienteCard consumo={semJanela} />);
    const dl = document.querySelector("dl")?.textContent ?? "";
    expect(dl).toContain(V.pontuaisFull);
    expect(dl).not.toContain(V.pontuais12m);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 7. Site: hero KPI Taxa de Poupança (bloco `ratios`, ADR-306 §Consequências)
// ─────────────────────────────────────────────────────────────────────

describe("<HeroKpiGrid /> — taxa de poupança rotulada", () => {
  const ratios = fx.ratios as unknown as RatiosData;

  it("anexa o rótulo da janela de referência do bloco ratios", () => {
    const { container } = render(
      <HeroKpiGrid
        patrimonio={undefined}
        reserva={undefined}
        ratios={ratios}
        goals={undefined}
        score={undefined}
      />,
    );
    expect(container.textContent).toContain("25,0%");
    const rotulado = container.querySelector('span[title*="12 meses documentados"]');
    expect(rotulado).not.toBeNull();
  });

  it("payload pré-A28 sem janela_referencia: nenhum rótulo inventado", () => {
    const { container } = render(
      <HeroKpiGrid
        patrimonio={undefined}
        reserva={undefined}
        ratios={{ taxa_poupanca_recorrente_pct: 25 }}
        goals={undefined}
        score={undefined}
      />,
    );
    // `PatrimonioInvestivelKpi` tem tooltip próprio — o negativo é escopado ao
    // texto de `formatJanelaTooltip`.
    expect(container.querySelector('span[title*="Média mensal calculada"]')).toBeNull();
  });
});
