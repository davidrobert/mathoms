/**
 * A40.l100 — o cartão de aportes não pode publicar a renda-alvo.
 *
 * `goals.if_trs_monthly_value` é a renda-alvo mensal DECLARADA
 * (`if_meta_bruta × TRS ÷ 12`, [[ADR-418]] §D3). O card a exibia sob o rótulo
 * "Aporte mensal necessário (meta IF)" — o fluxo que se quer RECEBER na IF
 * publicado como o que se precisa APORTAR.
 *
 * **Fixture discriminante.** O critério "os números batem" NÃO discrimina: no
 * workspace de origem a meta declarada e o PMT coincidiam, então ler qualquer
 * um dos dois passava. Aqui os três são distintos de propósito —
 * renda-alvo 333.333 · aporte declarado 20.000 · PMT necessário 42.111 — e o
 * teste falha para cada uma das três implementações erradas.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { EstrategiaAporteCard } from "@/components/report/cards/EstrategiaAporteCard";
import { S3InvestimentosSection } from "@/components/report/sections/S3InvestimentosSection";
import type { ReportAnalysisData } from "@/lib/api";

/** Renda-alvo mensal declarada — o número que o rótulo errado publicava. */
const RENDA_ALVO_MENSAL = 333_333;
/** Aporte que a família DECLAROU — o que o cético refutou como leitura correta. */
const APORTE_DECLARADO = 20_000;
/** PMT que atingiria a meta — só existe em `goal_service`, nunca no payload. */
const PMT_NECESSARIO = 42_111;

function makeData(
  overrides: Partial<Record<string, unknown>> = {},
): ReportAnalysisData {
  return {
    goals: {
      if_meta: 100_000_000,
      if_trs: 4,
      if_trs_monthly_value: RENDA_ALVO_MENSAL,
    },
    cenarios_conjuge: {
      labels: ["Sem renda do cônjuge"],
      aportes: [APORTE_DECLARADO],
    },
    ...overrides,
  } as unknown as ReportAnalysisData;
}

describe("EstrategiaAporteCard — renda-alvo não é aporte (A40.l100)", () => {
  it("não publica a renda-alvo nem rotula nada de 'necessário' em S3", () => {
    const { container } = render(<S3InvestimentosSection data={makeData()} />);
    const texto = container.textContent ?? "";

    // Lê a renda-alvo → o rótulo mente (defeito original).
    expect(texto).not.toContain("333.333");
    // Lê o aporte declarado sob rótulo de "necessário" → mente igual.
    expect(texto).not.toMatch(/necess[áa]rio/i);
    // O PMT real nunca esteve no payload: não pode aparecer por acidente.
    expect(texto).not.toContain("42.111");
  });

  it("publica o aporte DECLARADO na tabela de cenários, sob rótulo de cenário", () => {
    render(<EstrategiaAporteCard cenarios={{ labels: ["Sem renda do cônjuge"], aportes: [APORTE_DECLARADO] }} />);

    expect(screen.getByText("Sem renda do cônjuge")).toBeInTheDocument();
    expect(screen.getByText(/Aporte\/mês/)).toBeInTheDocument();
    expect(screen.queryByText(/necess[áa]rio/i)).not.toBeInTheDocument();
  });

  it("sem cenário declarado, alcança o estado honesto de 'não configurada'", () => {
    // Antes da A40.l100 este estado era INALCANÇÁVEL: `if_trs_monthly_value`
    // deriva da meta e está sempre presente, então o `!ifTrs` nunca era true.
    render(<EstrategiaAporteCard />);

    expect(screen.getByText("Meta de aporte não configurada.")).toBeInTheDocument();
  });

  it("o ramo rico (destinos) segue publicando os destinos declarados", () => {
    render(
      <EstrategiaAporteCard
        estrategia={{
          total_aporte: APORTE_DECLARADO,
          dia_aporte: 5,
          destinos: [{ destino: "Tesouro IPCA+", valor: APORTE_DECLARADO, pct: 100 }],
        }}
      />,
    );

    expect(screen.getByText("Tesouro IPCA+")).toBeInTheDocument();
    expect(screen.queryByText(/necess[áa]rio/i)).not.toBeInTheDocument();
  });
});
