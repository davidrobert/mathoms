/**
 * "Análise Financeira" do `/plano`: o sinal dos pontos urgentes com a seção fechada.
 *
 * A seção nasce colapsada no rodapé da página (Onda 7 #1); sem o sinal, um ponto urgente
 * de prioridade alta ficava invisível até alguém abri-la. Os alertas vêm de
 * `tests/fixtures/dashboard_alerts.json`, gerada pelos produtores reais do E5 em
 * `backend/tests/test_dashboard_alerts_contract.py` — nunca escrita à mão.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { FinancialAnalysisDetails } from "@/app/(app)/plano/_components/_dashboard/FinancialAnalysisDetails";
import {
  alertTone,
  urgentPointsLabel,
} from "@/app/(app)/plano/_components/_dashboard/alertTone";
import type { DashboardAlert, DashboardResponse } from "@/lib/api";

type Cenario = "sem_alerta" | "so_aviso" | "so_media" | "com_alta" | "misto";

const FIXTURE: Record<Cenario, DashboardAlert[]> = JSON.parse(
  readFileSync(path.resolve(__dirname, "../fixtures/dashboard_alerts.json"), "utf8"),
);

function dashboard(cenario: Cenario): DashboardResponse {
  return {
    kpis: [],
    charts: [],
    alerts: FIXTURE[cenario],
    data_freshness: null,
    periodo: null,
  };
}

function secao(data: DashboardResponse | null, loading = false) {
  return (
    <FinancialAnalysisDetails
      loading={loading}
      data={data}
      onBarClick={() => {}}
      onSliceClick={() => {}}
    />
  );
}

function chip() {
  return screen.queryByTestId("urgent-points-chip");
}

describe("summary fechado — sinal dos pontos urgentes", () => {
  it("antes dos dados não mostra nada: nem zero, nem skeleton", () => {
    const { container } = render(secao(null, true));
    expect(container.querySelector("summary")).toHaveTextContent("Análise Financeira");
    expect(chip()).toBeNull();
  });

  it.each(["sem_alerta", "so_aviso"] as const)(
    "%s: aviso de qualidade de dado não acende o sinal",
    (cenario) => {
      render(secao(dashboard(cenario)));
      expect(chip()).toBeNull();
    },
  );

  it("só prioridade média conta, mas sem o tom crítico", () => {
    render(secao(dashboard("so_media")));
    expect(chip()).toHaveTextContent(/^1 ponto urgente$/);
    expect(chip()).toHaveAttribute("data-tone", "neutral");
  });

  it("prioridade alta acende o tom crítico e diz a prioridade no texto", () => {
    render(secao(dashboard("com_alta")));
    expect(chip()).toHaveTextContent(/^1 ponto urgente de prioridade alta$/);
    expect(chip()).toHaveAttribute("data-tone", "critical");
  });

  it("conta todos os pontos urgentes e diz quantos são de prioridade alta", () => {
    render(secao(dashboard("misto")));
    expect(chip()).toHaveTextContent(/^4 pontos urgentes, 3 de prioridade alta$/);
    expect(chip()).toHaveAttribute("data-tone", "critical");
  });

  it("a seção segue fechada mesmo com ponto urgente de prioridade alta", () => {
    const { container } = render(secao(dashboard("misto")));
    expect(container.querySelector("details")).not.toHaveAttribute("open");
  });

  it("o chip vem depois do subtítulo e antes da régua, dentro do summary", () => {
    const { container } = render(secao(dashboard("com_alta")));
    const sinal = chip();
    expect(sinal?.parentElement).toBe(container.querySelector("summary"));
    expect(sinal?.previousElementSibling).toHaveTextContent(/última análise/);
    expect(sinal?.nextElementSibling).toHaveClass("flex-1", "border-t");
  });

  it("recarregar com os dados anteriores mantém o sinal", () => {
    const { rerender } = render(secao(dashboard("com_alta")));
    rerender(secao(dashboard("com_alta"), true));
    expect(chip()).toHaveTextContent(/de prioridade alta$/);
  });
});

describe("seção aberta — cards dos alertas", () => {
  it("pontos urgentes antes dos avisos; só a prioridade alta leva o tom crítico", () => {
    render(secao(dashboard("misto")));
    const titulos = screen.getAllByText(/^(Ponto Urgente|Aviso)$/);
    expect(titulos.map((t) => t.textContent)).toEqual([
      ...Array(4).fill("Ponto Urgente"),
      "Aviso",
    ]);
    const tons = titulos.map((t) =>
      t.closest('[data-slot="card"]')?.getAttribute("data-tone"),
    );
    expect(tons).toEqual(["critical", "critical", "critical", "neutral", "neutral"]);
  });
});

describe("tom e rótulo do sinal", () => {
  it("severidade fora do contrato cai no neutro, nunca no vermelho", () => {
    expect(alertTone("info").name).toBe("neutral");
  });

  it.each([
    [2, 0, "2 pontos urgentes"],
    [2, 2, "2 pontos urgentes de prioridade alta"],
  ])("%i pontos, %i de prioridade alta → %s", (total, highPriority, label) => {
    expect(urgentPointsLabel({ total, highPriority })).toBe(label);
  });
});
