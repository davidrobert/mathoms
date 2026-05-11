/**
 * Tests — Track T06 / ADR-191 — RentabilidadeCard cobre 4 status + defasagem >18m.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RentabilidadeCard } from "@/components/report/cards/RentabilidadeCard";
import type { RatiosData, RentabilidadeRatio } from "@/types/report-analysis";

function makeRatio(overrides: Partial<RentabilidadeRatio> = {}): RentabilidadeRatio {
  return {
    valor_pct: 3.25,
    ano_base: 2024,
    defasagem_meses: 4,
    meta_pct: 5,
    cobertura_despesa_essencial_pct: 20.83,
    status: "ok",
    ...overrides,
  };
}

function makeRatios(rentabilidade: RentabilidadeRatio | null): RatiosData {
  return {
    taxa_poupanca_recorrente_pct: 30,
    taxa_poupanca_total_pct: 25,
    taxa_endividamento_pct: 12,
    cobertura_despesas_meses: 8,
    rentabilidade_pct: rentabilidade?.valor_pct ?? "N/D",
    aliquota_efetiva_ir_pct: 15,
    janela_referencia: "2025-04 a 2026-03",
    janela_n_meses: 12,
    rentabilidade,
  };
}

describe("<RentabilidadeCard /> · status ok", () => {
  it("mostra TRS efetiva, meta, cobertura essencial, ano-base e defasagem", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio())} />);
    expect(screen.getByText("3,25%")).toBeInTheDocument();
    expect(screen.getByText("a.a.")).toBeInTheDocument();
    expect(screen.getByText(/Meta de referência: 5,0% a.a/i)).toBeInTheDocument();
    expect(screen.getByText("20,8%")).toBeInTheDocument();
    expect(
      screen.getByText(/da despesa essencial mensal coberta pela renda passiva/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Ano-base IRPF 2024")).toBeInTheDocument();
    expect(screen.getByText("4 meses de defasagem")).toBeInTheDocument();
  });

  it("computa diff vs meta com sinal correto", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio({ valor_pct: 6.5 }))} />);
    expect(screen.getByText(/\+1,50 pp vs\. meta/)).toBeInTheDocument();
  });

  it("usa singular 'mês' quando defasagem=1", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio({ defasagem_meses: 1 }))} />);
    expect(screen.getByText("1 mês de defasagem")).toBeInTheDocument();
  });

  it("não mostra badge 'Dado defasado' quando defasagem <= 18 meses", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio({ defasagem_meses: 18 }))} />);
    expect(screen.queryByText("Dado defasado")).not.toBeInTheDocument();
  });
});

describe("<RentabilidadeCard /> · branch defasagem > 18 meses", () => {
  it("mostra badge 'Dado defasado' quando defasagem > 18 meses", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio({ defasagem_meses: 19 }))} />);
    expect(screen.getByText("Dado defasado")).toBeInTheDocument();
  });

  it("mostra badge quando defasagem é muito alta (24m)", () => {
    render(<RentabilidadeCard ratios={makeRatios(makeRatio({ defasagem_meses: 24 }))} />);
    expect(screen.getByText("Dado defasado")).toBeInTheDocument();
  });
});

describe("<RentabilidadeCard /> · status sem_dados_essencial", () => {
  it("mostra TRS mas omite cobertura, com mensagem explicativa", () => {
    const ratio = makeRatio({
      status: "sem_dados_essencial",
      cobertura_despesa_essencial_pct: null,
    });
    render(<RentabilidadeCard ratios={makeRatios(ratio)} />);
    expect(screen.getByText("3,25%")).toBeInTheDocument();
    expect(
      screen.getByText(/Categorização incompleta — cobertura essencial não disponível/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/da despesa essencial mensal/i)).not.toBeInTheDocument();
  });
});

describe("<RentabilidadeCard /> · empty state sem_irpf", () => {
  it("mostra CTA para upload do IRPF", () => {
    const ratio: RentabilidadeRatio = {
      valor_pct: null,
      ano_base: null,
      defasagem_meses: null,
      meta_pct: 5,
      cobertura_despesa_essencial_pct: null,
      status: "sem_irpf",
    };
    render(<RentabilidadeCard ratios={makeRatios(ratio)} />);
    expect(
      screen.getByText(/Indicador indisponível — precisamos do seu IRPF/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Carregue a declaração mais recente em Documentos/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/% a.a/i)).not.toBeInTheDocument();
  });
});

describe("<RentabilidadeCard /> · empty state gerador_zero", () => {
  it("explica ausência de carteira de renda e preserva ano-base", () => {
    const ratio: RentabilidadeRatio = {
      valor_pct: null,
      ano_base: 2024,
      defasagem_meses: 5,
      meta_pct: 5,
      cobertura_despesa_essencial_pct: null,
      status: "gerador_zero",
    };
    render(<RentabilidadeCard ratios={makeRatios(ratio)} />);
    expect(
      screen.getByText(/Sem patrimônio gerador identificado/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/ações, fundos imobiliários/i)).toBeInTheDocument();
    expect(screen.getByText("Ano-base IRPF 2024")).toBeInTheDocument();
  });
});

describe("<RentabilidadeCard /> · back-compat (sem campo aninhado)", () => {
  it("renderiza fallback com valor flat quando workspace pré-PR-A", () => {
    const ratios: RatiosData = {
      rentabilidade_pct: 3.25,
      // rentabilidade aninhado AUSENTE (workspace antigo)
    };
    render(<RentabilidadeCard ratios={ratios} />);
    expect(screen.getByText("3.25%")).toBeInTheDocument();
    expect(screen.getByText(/Yield observado sobre patrimônio gerador/i)).toBeInTheDocument();
  });

  it("renderiza fallback com N/D quando rentabilidade_pct=string", () => {
    const ratios: RatiosData = {
      rentabilidade_pct: "N/D",
    };
    render(<RentabilidadeCard ratios={ratios} />);
    expect(screen.getByText("N/D")).toBeInTheDocument();
  });

  it("não renderiza nada quando ratios é undefined", () => {
    const { container } = render(<RentabilidadeCard ratios={undefined} />);
    expect(container.firstChild).toBeNull();
  });
});
