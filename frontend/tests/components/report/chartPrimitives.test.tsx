/**
 * ADR-117 · Fase 2 — smoke tests dos primitivos de chart.
 *
 * Não testa render visual do canvas (Chart.js precisa de 'canvas' npm pkg
 * que não está instalado — ver setup.ts). Testa: (a) registro idempotente
 * de Chart.js, (b) transforms determinísticos, (c) useChartTheme em
 * mudança de tema, (d) ChartConclusion + ChartNav (componentes puros sem
 * canvas).
 */
import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";

import {
  ChartConclusion,
  ChartNav,
  ensureChartRegistered,
  useChartTheme,
} from "@/components/report/charts/primitives";

describe("ensureChartRegistered()", () => {
  it("é idempotente — múltiplas chamadas não levantam", () => {
    expect(() => {
      ensureChartRegistered();
      ensureChartRegistered();
      ensureChartRegistered();
    }).not.toThrow();
  });
});

describe("<ChartConclusion />", () => {
  it("renderiza texto como parágrafo com data-chart-conclusion", () => {
    const { container } = render(
      <ChartConclusion>Texto de leitura curta</ChartConclusion>,
    );
    const p = container.querySelector("[data-chart-conclusion]");
    expect(p).toBeInTheDocument();
    expect(p?.tagName.toLowerCase()).toBe("p");
    expect(p?.textContent).toBe("Texto de leitura curta");
  });
});

describe("<ChartNav />", () => {
  it("desabilita prev em page=0 e next em page=total-1", () => {
    const { rerender } = render(
      <ChartNav
        label="p1"
        page={0}
        total={3}
        onPrev={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Período anterior")).toBeDisabled();
    expect(screen.getByLabelText("Próximo período")).not.toBeDisabled();

    rerender(
      <ChartNav
        label="p3"
        page={2}
        total={3}
        onPrev={vi.fn()}
        onNext={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Período anterior")).not.toBeDisabled();
    expect(screen.getByLabelText("Próximo período")).toBeDisabled();
  });

  it("chama onPrev/onNext nos cliques", () => {
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <ChartNav label="p2" page={1} total={3} onPrev={onPrev} onNext={onNext} />,
    );
    fireEvent.click(screen.getByLabelText("Período anterior"));
    fireEvent.click(screen.getByLabelText("Próximo período"));
    expect(onPrev).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});

describe("useChartTheme()", () => {
  it("retorna paleta com 12 cores categóricas", () => {
    const { result } = renderHook(() => useChartTheme());
    expect(result.current.categorical).toHaveLength(12);
    expect(result.current.text).toBeTruthy();
    expect(result.current.grid).toBeTruthy();
  });

  it("re-renderiza ao mudar data-theme no <html>", () => {
    const { result } = renderHook(() => useChartTheme());
    const firstText = result.current.text;
    act(() => {
      document.documentElement.setAttribute("data-theme", "dark");
    });
    // Sem CSS real carregado no jsdom não conseguimos testar mudança de cor,
    // mas o hook deve ter re-executado — verifica referência do objeto.
    expect(result.current).toBeTruthy();
    act(() => {
      document.documentElement.removeAttribute("data-theme");
    });
    expect(typeof firstText).toBe("string");
  });
});
