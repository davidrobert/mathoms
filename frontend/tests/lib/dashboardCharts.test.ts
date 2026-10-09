/**
 * Contrato do bar chart do dashboard (`/plano` › Mês corrente) — lado TS do par.
 *
 * Lê a MESMA fixture que `backend/tests/test_dashboard_charts_contract.py`, gerada
 * pelo produtor (`build_charts`): fixture escrita à mão descreveria um mundo que o
 * produtor não emite (lição da A40.l3). "Investimentos por Classe" saía como
 * `{classes, total}` e `normalizeBarData` devolvia zero linhas — card com título
 * e sem barras.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  categoryBarChartHeight,
  isMonthlyBarChart,
  normalizeBarData,
} from "@/app/(app)/plano/_components/_dashboard/dashboardHelpers";
import type { DashboardChart } from "@/lib/api";

const FIXTURE: { charts: DashboardChart[] } = JSON.parse(
  readFileSync(path.resolve(__dirname, "../fixtures/dashboard_charts.json"), "utf8"),
);

const BAR_CHARTS = FIXTURE.charts.filter((chart) => chart.chart_type === "bar");

const MENSAL: DashboardChart = {
  chart_type: "bar",
  title: "Receita vs Despesa Mensal",
  data: {
    labels: ["jan/2026", "fev/2026"],
    datasets: [{ label: "Receita", data: [10, 20] }],
  },
};

describe("dashboard — bar chart como o backend emite", () => {
  it("a fixture traz o gráfico de classes (sem ele, os casos abaixo são vácuos)", () => {
    expect(BAR_CHARTS.map((chart) => chart.title)).toEqual(["Investimentos por Classe"]);
  });

  it("Investimentos por Classe: uma barra por classe, com o valor da classe", () => {
    const { rows, keys } = normalizeBarData(BAR_CHARTS[0]);

    expect(rows).toEqual([
      { month: "Renda Fixa", Valor: 300000 },
      { month: "Imóveis Investimento", Valor: 200000 },
      { month: "Ações BR", Valor: 100000 },
      { month: "Imóveis com uso não apurado", Valor: 150000 },
    ]);
    expect(keys.map((key) => key.name)).toEqual(["Valor"]);
  });
});

describe("dashboard — meses em colunas com clique; categorias deitadas, sem clique", () => {
  it("barra de classes: eixo de categorias, sem deep-link por período", () => {
    expect(isMonthlyBarChart(BAR_CHARTS[0])).toBe(false);
  });

  it("barra com eixo de meses: colunas com deep-link", () => {
    expect(isMonthlyBarChart(MENSAL)).toBe(true);
  });

  it("o mês precisa vir `mmm/aaaa`: `abr/26` cai no eixo de categorias e perde o clique", () => {
    const curto: DashboardChart = { ...MENSAL, data: { ...MENSAL.data, labels: ["abr/26", "mai/26"] } };
    expect(isMonthlyBarChart(curto)).toBe(false);
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
