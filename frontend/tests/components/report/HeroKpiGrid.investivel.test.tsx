/**
 * Regressão do hero card "Patrimônio Investível" (ADR-142 + ADR-215 §6).
 *
 * Bug histórico: backend renomeou `investivel` → `investivel_financeiro` +
 * `investivel_efetivo`, mas frontend continuou lendo a chave morta. Card
 * mostrava "—" silenciosamente. Decisão semântica do financial-planner
 * (2026-05-20):
 *  - Valor primário = `investivel_financeiro` (estável, alinha Perini + AUVP).
 *  - Sub-linha condicional reflete o estado do toggle `imoveis_no_if`.
 *  - Critério de aceite testável: flippar o toggle NÃO muda o valor primário.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { HeroKpiGrid } from "@/components/report/kpi/HeroKpiGrid";
import type { PatrimonioData } from "@/types/report-analysis";

import { vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function makePatrimonio(overrides: Partial<PatrimonioData> = {}): PatrimonioData {
  return {
    bruto: 4_010_000,
    liquido: 3_800_000,
    investivel_financeiro: 850_000,
    investivel_efetivo: 850_000,
    imoveis_geradores: 0,
    imoveis_no_if: false,
    fonte_investimentos: "posicoes_atuais+irpf",
    ...overrides,
  };
}

function renderGrid(patrimonio: PatrimonioData | undefined) {
  return render(
    <HeroKpiGrid
      patrimonio={patrimonio}
      reserva={undefined}
      ratios={undefined}
      goals={undefined}
      score={undefined}
    />,
  );
}

describe("<HeroKpiGrid /> · Patrimônio Investível @ADR-142 @ADR-215", () => {
  it("renderiza R$ 850 mil quando só há investivel_financeiro (toggle off)", () => {
    renderGrid(makePatrimonio({ imoveis_no_if: false }));
    expect(screen.getByText("Patrimônio Investível")).toBeInTheDocument();
    // Intl.NumberFormat pt-BR compact: "R$ 850 mil" (NBSP entre R$ e número)
    expect(screen.getByText(/R\$\s*850(?:,\d+)?\s*mil/)).toBeInTheDocument();
    expect(screen.getByText("Imóveis fora do cálculo de IF")).toBeInTheDocument();
  });

  it("mostra sub-linha de imóveis geradores quando toggle on + geradores>0", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        investivel_financeiro: 850_000,
        investivel_efetivo: 1_450_000,
        imoveis_geradores: 600_000,
      }),
    );
    // Valor primário NÃO é o efetivo — continua o financeiro
    expect(screen.getByText(/R\$\s*850(?:,\d+)?\s*mil/)).toBeInTheDocument();
    expect(screen.getByText(/em imóveis de renda/)).toBeInTheDocument();
    expect(screen.getByText(/total efetivo/)).toBeInTheDocument();
  });

  it("mostra CTA 'classificar' quando toggle on mas sem imóveis geradores", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        investivel_financeiro: 850_000,
        investivel_efetivo: 850_000,
        imoveis_geradores: 0,
      }),
    );
    expect(screen.getByText(/Sem imóveis de renda classificados/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /classificar/i });
    expect(link).toHaveAttribute("href", "/config?tab=members");
  });

  // ADR-439 D3 — o veredito decide antes do número. Na fase expand o balde ainda sai 0
  // com veredito `nao_apurado`; no flip ele sai `null`. Os dois caíam no CTA de
  // classificar, que afirma ausência e manda reclassificar o que já foi classificado.
  const veredito = (motivo: string | null) =>
    ({
      imoveis_geradores: { status: "nao_apurado", motivo, piso: false },
    }) as unknown as PatrimonioData["cobertura_classificacao_imovel"];

  it("vínculo perdido: diz a direção do erro e não oferece 'classificar'", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        imoveis_geradores: 0,
        cobertura_classificacao_imovel: veredito("vinculo_perdido"),
      }),
    );
    expect(screen.getByText(/Imóveis de renda não identificados/)).toBeInTheDocument();
    expect(screen.getByText(/o progresso da IF pode ser maior/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /classificar/i })).toBeNull();
  });

  it("balde null sem bloco (flip, payload sem cobertura) segue o mesmo ramo", () => {
    renderGrid(makePatrimonio({ imoveis_no_if: true, imoveis_geradores: null }));
    expect(screen.getByText(/Imóveis de renda não identificados/)).toBeInTheDocument();
    expect(screen.queryByText(/Sem imóveis de renda classificados/)).toBeNull();
  });

  it("gerador sem valor apurado tem copy própria", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        imoveis_geradores: null,
        cobertura_classificacao_imovel: veredito("sem_valor"),
      }),
    );
    expect(screen.getByText(/Imóveis de renda sem valor apurado/)).toBeInTheDocument();
  });

  it("nunca classificou: o CTA de classificar continua certo", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        imoveis_geradores: null,
        cobertura_classificacao_imovel: veredito("nao_classificados"),
      }),
    );
    expect(screen.getByText(/Sem imóveis de renda classificados/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /classificar/i })).toBeInTheDocument();
  });

  it("toggle off ignora o veredito: os geradores não entram no IF", () => {
    renderGrid(
      makePatrimonio({
        imoveis_no_if: false,
        cobertura_classificacao_imovel: veredito("vinculo_perdido"),
      }),
    );
    expect(screen.getByText("Imóveis fora do cálculo de IF")).toBeInTheDocument();
  });

  it("renderiza '—' quando patrimonio é undefined", () => {
    renderGrid(undefined);
    expect(screen.getByText("Patrimônio Investível")).toBeInTheDocument();
    // formatCompactBRL retorna "—" quando valor é null/undefined
    const card = screen.getByText("Patrimônio Investível").parentElement;
    expect(card?.textContent).toContain("—");
  });

  it("renderiza '—' quando investivel_financeiro é undefined (payload parcial)", () => {
    renderGrid({
      bruto: 4_010_000,
      liquido: 3_800_000,
      fonte_investimentos: "posicoes_atuais+irpf",
    });
    const card = screen.getByText("Patrimônio Investível").parentElement;
    expect(card?.textContent).toContain("—");
    // Fonte aparece como fallback de sub-linha
    expect(screen.getByText(/Fonte: posicoes_atuais\+irpf/)).toBeInTheDocument();
  });

  it("invariante: flippar imoveis_no_if NÃO muda o valor primário do card", () => {
    // Critério de aceite financial-planner — estabilidade visual.
    const off = renderGrid(
      makePatrimonio({
        imoveis_no_if: false,
        investivel_financeiro: 850_000,
        investivel_efetivo: 850_000,
        imoveis_geradores: 0,
      }),
    );
    const valueOff = screen.getByText(/R\$\s*850(?:,\d+)?\s*mil/).textContent;
    off.unmount();

    renderGrid(
      makePatrimonio({
        imoveis_no_if: true,
        investivel_financeiro: 850_000,
        investivel_efetivo: 1_450_000,
        imoveis_geradores: 600_000,
      }),
    );
    const valueOn = screen.getByText(/R\$\s*850(?:,\d+)?\s*mil/).textContent;
    expect(valueOn).toBe(valueOff);
  });

  it("expõe tooltip nativo com a definição metodológica do card", () => {
    const { container } = renderGrid(makePatrimonio());
    const wrapper = container.querySelector('[title^="Patrimônio Investível:"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper?.getAttribute("title")).toMatch(/Não inclui residência/);
  });
});
