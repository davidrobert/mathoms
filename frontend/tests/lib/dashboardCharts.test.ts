/**
 * Contrato dos gráficos do dashboard (`/plano` › Mês corrente) — lado TS do par.
 *
 * Lê a MESMA fixture que `backend/tests/test_dashboard_charts_contract.py`, gerada
 * pelo produtor (`build_charts`) sobre um E5 dos produtores reais: fixture escrita
 * à mão descreveria um mundo que o produtor não emite (lição da A40.l3). "Investimentos por Classe" saía como
 * `{classes, total}` e `normalizeBarData` devolvia zero linhas — card com título
 * e sem barras.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  isMonthlyBarChart,
  normalizeBarData,
} from "@/app/(app)/plano/_components/_dashboard/dashboardHelpers";
import { normalizePieData } from "@/app/(app)/plano/_components/_dashboard/dashboardPie";
import type { DashboardChart } from "@/lib/api";

const FIXTURE: { charts: DashboardChart[]; conferencia: Record<string, number> } = JSON.parse(
  readFileSync(path.resolve(__dirname, "../fixtures/dashboard_charts.json"), "utf8"),
);

const BAR_CHARTS = FIXTURE.charts.filter((chart) => chart.chart_type === "bar");

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

describe("dashboard — clique na barra só onde há destino", () => {
  it("barra de classes não tem deep-link por período", () => {
    expect(isMonthlyBarChart(BAR_CHARTS[0])).toBe(false);
  });

  it("barra com eixo de meses tem", () => {
    const mensal: DashboardChart = {
      chart_type: "bar",
      title: "Receita vs Despesa Mensal",
      data: {
        labels: ["jan/2026", "fev/2026"],
        datasets: [{ label: "Receita", data: [10, 20] }],
      },
    };
    expect(isMonthlyBarChart(mensal)).toBe(true);
  });
});

function chart(title: string): DashboardChart {
  const found = FIXTURE.charts.find((c) => c.title === title);
  if (!found) {
    const titles = FIXTURE.charts.map((c) => c.title).join(", ");
    throw new Error(`fixture sem o gráfico "${title}"; tem: ${titles}`);
  }
  return found;
}

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
