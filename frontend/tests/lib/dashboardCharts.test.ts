/**
 * Contrato dos gráficos do dashboard (`/plano` › Mês corrente) — lado TS do par.
 *
 * Lê a MESMA fixture que `backend/tests/test_dashboard_charts_contract.py`, gerada pelo
 * produtor (`build_charts`) sobre um E5 dos produtores reais: fixture escrita à mão
 * descreveria um mundo que o produtor não emite (lição da A40.l3). Três cards saíam
 * vazios, cada um por uma crença divergente de shape — classes (`{classes, total}`),
 * composição (`{items}`) e receita × despesa (`datasets` que o E5 não emite).
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  categoryBarChartHeight,
  formatIsoMonthShort,
  isMonthlyBarChart,
  isoMonthToDateRange,
  isWideChart,
  normalizeBarData,
} from "@/app/(app)/plano/_components/_dashboard/dashboardHelpers";
import { normalizePieData } from "@/app/(app)/plano/_components/_dashboard/dashboardPie";
import type { DashboardChart } from "@/lib/api";

interface Fixture {
  charts: DashboardChart[];
  conferencia: Record<string, number>;
}

const FIXTURE: Fixture = JSON.parse(
  readFileSync(path.resolve(__dirname, "../fixtures/dashboard_charts.json"), "utf8"),
);

function chart(title: string): DashboardChart {
  const found = FIXTURE.charts.find((c) => c.title === title);
  if (!found) {
    const titles = FIXTURE.charts.map((c) => c.title).join(", ");
    throw new Error(`fixture sem o gráfico "${title}"; tem: ${titles}`);
  }
  return found;
}

const MENSAL = "Receitas e Saídas por Mês";

it("a fixture traz os quatro gráficos (sem eles, os casos abaixo são vácuos)", () => {
  expect(FIXTURE.charts.map((c) => c.title)).toEqual([
    MENSAL,
    "Despesas por Categoria",
    "Composição Patrimonial",
    "Investimentos por Classe",
  ]);
});

describe("Investimentos por Classe", () => {
  it("uma barra por classe, com o valor da classe", () => {
    const { rows, keys } = normalizeBarData(chart("Investimentos por Classe"));
    expect(rows).toEqual([
      { month: "Renda Fixa", Valor: 300000 },
      { month: "Imóveis Investimento", Valor: 200000 },
      { month: "Ações BR", Valor: 100000 },
      { month: "Imóveis com uso não apurado", Valor: 150000 },
    ]);
    expect(keys.map((key) => key.name)).toEqual(["Valor"]);
  });

  it("não tem deep-link por período nem ocupa a largura inteira", () => {
    expect(isMonthlyBarChart(chart("Investimentos por Classe"))).toBe(false);
    expect(isWideChart(chart("Investimentos por Classe"))).toBe(false);
  });
});

describe(MENSAL, () => {
  it("12 meses, receitas e saídas por mês", () => {
    const { rows } = normalizeBarData(chart(MENSAL));
    expect(rows).toHaveLength(12);
    expect(rows[0]).toEqual({ month: "2025-03", Receitas: 20000, "Saídas (inclui aportes)": 13000 });
  });

  it("cor pelo papel da série — saídas incluem aporte e não pintam de perda", () => {
    const { keys } = normalizeBarData(chart(MENSAL));
    expect(keys.map((key) => [key.name, key.color])).toEqual([
      ["Receitas", "var(--semantic-gain)"],
      ["Saídas (inclui aportes)", "var(--semantic-neutral-financial)"],
    ]);
  });

  it("o clique leva ao mês da barra, e o eixo lê MMM/YY", () => {
    const { rows } = normalizeBarData(chart(MENSAL));
    const ultimo = rows[rows.length - 1].month;
    expect(isMonthlyBarChart(chart(MENSAL))).toBe(true);
    expect(isoMonthToDateRange(ultimo)).toEqual({ date_from: "2026-02-01", date_to: "2026-02-28" });
    expect(formatIsoMonthShort(ultimo)).toBe("fev/26");
  });

  it("com mais de 6 meses ocupa a largura inteira", () => {
    expect(isWideChart(chart(MENSAL))).toBe(true);
  });
});

describe("Composição Patrimonial", () => {
  it("só linha apurada vira fatia", () => {
    const { slices } = normalizePieData(chart("Composição Patrimonial"));
    expect(slices.map((s) => [s.name, s.value])).toEqual([
      ["Investimentos Titular", 300000],
      ["Outros imóveis", 200000],
      ["Investimentos Cônjuge", 100000],
      ["Caixa e Moeda Estrangeira", 50000],
    ]);
  });

  it("residência não apurada vira nota com o motivo — nunca fatia nem zero (ADR-439 D5)", () => {
    const { slices, notes, clickable } = normalizePieData(chart("Composição Patrimonial"));
    expect(slices.map((s) => s.name)).not.toContain("Residência");
    expect(notes).toEqual([{ kind: "residencia_nao_apurada", motivo: "nao_classificada" }]);
    expect(clickable).toBe(false);
  });
});

describe("Despesas por Categoria", () => {
  it("sem aporte, rótulo humano e chave crua para o deep-link", () => {
    const { slices, clickable } = normalizePieData(chart("Despesas por Categoria"));
    expect(slices).toEqual([{ id: "alimentacao", name: "Alimentação", value: 108000 }]);
    expect(clickable).toBe(true);
  });

  it("o aporte retirado é a transferência patrimonial do E5 (ADR-333)", () => {
    const { notes } = normalizePieData(chart("Despesas por Categoria"));
    const transferencia = FIXTURE.conferencia["fluxo_caixa.janela_12m.transferencia_patrimonial"];
    expect(transferencia).toBeGreaterThan(0);
    expect(notes).toEqual([{ kind: "base_despesas", janelaMeses: 12, aporteExcluido: transferencia }]);
  });
});

describe("roteamento — quem decide é o `x_axis`, não o formato do rótulo", () => {
  const barra = (data: Record<string, unknown>): DashboardChart => ({
    chart_type: "bar",
    title: "Qualquer",
    data: { datasets: [{ label: "Valor", data: [1, 2] }], ...data },
  });

  it("rótulo com cara de mês, sem `x_axis`, cai no eixo de categorias e perde o clique", () => {
    expect(isMonthlyBarChart(barra({ labels: ["abr/26", "mai/26"] }))).toBe(false);
  });

  it("`x_axis: \"month\"` vira coluna com deep-link, qualquer que seja o rótulo", () => {
    expect(isMonthlyBarChart(barra({ x_axis: "month", labels: ["abr/26", "mai/26"] }))).toBe(true);
  });
});

describe("dashboard — altura da barra deitada", () => {
  it("até 7 categorias fica na altura dos outros cards", () => {
    expect(categoryBarChartHeight(4)).toBe(300);
    expect(categoryBarChartHeight(7)).toBe(300);
  });

  it("da 8ª em diante cresce 36px por categoria — 11 (o vocabulário inteiro) dá 430", () => {
    expect(categoryBarChartHeight(8)).toBe(322);
    expect(categoryBarChartHeight(11)).toBe(430);
  });
});
