/**
 * ADR-167 — o cenário "Sem renda do cônjuge" na S3 segue a presença do bloco.
 *
 * O E5 publica `cenarios_conjuge: {}` para quem não é elegível (solteiro, sem
 * meta IF). O card da S3 não checava presença: o fallback estático de conclusão
 * sempre tinha texto, então o solteiro via "Cenários de Estresse — Sem renda do
 * cônjuge" com o bloco vazio. O card de aportes decidia "Meta de aporte não
 * configurada" pela ausência do cenário — falso para o solteiro que declarou
 * aporte.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { S3InvestimentosSection } from "@/components/report/sections/S3InvestimentosSection";
import type { ReportAnalysisData } from "@/lib/api";

const TITULO_CENARIO = "Cenários de Estresse — Sem renda do cônjuge";
const SEM_META = "Meta de aporte não configurada.";

const CENARIO_CASAL = {
  labels: ["Sem renda do cônjuge"],
  aportes: [13_200],
  prazos_if: [12],
  anos_if: [2038],
};

/** `aporte_mensal_usado` é o aporte declarado que a S7 também publica. */
function monteCarlo(aporteMensal: number) {
  return {
    sigma_usado: 0.15,
    exibir_cone: false,
    motivo_sem_cone: "sem prazo declarado",
    caminho_p10: [],
    caminho_p50: [],
    caminho_p90: [],
    aporte_mensal_usado: aporteMensal,
  };
}

function renderS3(overrides: Record<string, unknown>) {
  const data = { goals: { if_meta: 5_000_000 }, ...overrides };
  return render(
    <S3InvestimentosSection data={data as unknown as ReportAnalysisData} />,
  );
}

describe("S3 — cenário do cônjuge segue a presença do bloco (ADR-167)", () => {
  it("bloco vazio: o card do cenário não monta", () => {
    renderS3({ cenarios_conjuge: {} });

    expect(screen.queryByText(TITULO_CENARIO)).not.toBeInTheDocument();
  });

  it("bloco presente: o card do cenário monta", () => {
    renderS3({ cenarios_conjuge: CENARIO_CASAL });

    expect(screen.getByText(TITULO_CENARIO)).toBeInTheDocument();
  });
});

describe("S3 — card de aportes com predicado próprio de aporte declarado", () => {
  it("solteiro com aporte declarado: não afirma meta não configurada", () => {
    renderS3({ cenarios_conjuge: {}, if_monte_carlo: monteCarlo(20_000) });

    expect(screen.queryByText(SEM_META)).not.toBeInTheDocument();
    expect(screen.queryByText("Estratégia de Aportes")).not.toBeInTheDocument();
  });

  it("solteiro sem aporte declarado: o estado de meta não configurada segue alcançável", () => {
    renderS3({ cenarios_conjuge: {} });

    expect(screen.getByText(SEM_META)).toBeInTheDocument();
  });

  it("casal com aporte declarado: a tabela do cenário aparece", () => {
    renderS3({ cenarios_conjuge: CENARIO_CASAL, if_monte_carlo: monteCarlo(20_000) });

    expect(screen.getByRole("columnheader", { name: "Aporte/mês" })).toBeInTheDocument();
    expect(screen.queryByText(SEM_META)).not.toBeInTheDocument();
  });

  it("casal sem aporte declarado: 'não configurada' vence a tabela", () => {
    renderS3({ cenarios_conjuge: CENARIO_CASAL });

    expect(screen.getByText(SEM_META)).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "Aporte/mês" }),
    ).not.toBeInTheDocument();
  });
});
