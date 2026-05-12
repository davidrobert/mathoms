/** S9-T04 (ADR-192 §D4) — Unit tests for the 4 new protection cards. */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  AcoesMitigacaoCard,
  CoberturaSegurosCard,
  HeroGapProtecaoCard,
  SucessaoCard,
  type ProtectionBundle,
} from "@/components/report/cards";

function makeBundle(overrides: Partial<ProtectionBundle> = {}): ProtectionBundle {
  return {
    policies: [],
    gap_analysis: {},
    recommendations: [],
    auto_inferred_risks: [],
    methodology_thresholds: {},
    has_us_exposure: false,
    adapter_version: 1,
    ...overrides,
  };
}

describe("<HeroGapProtecaoCard /> — KPI protagonista (ADR-192 §D4)", () => {
  it("estado empty quando sem apólices", () => {
    render(<HeroGapProtecaoCard bundle={makeBundle()} />);
    expect(
      screen.getByText(/Nenhuma apólice cadastrada ainda/),
    ).toBeInTheDocument();
  });

  it("renderiza disclaimer fiduciário canônico (COPY_GUIDELINES §13.2 — sem atribuição)", () => {
    render(
      <HeroGapProtecaoCard
        bundle={makeBundle()}
        effectiveDate="2026-05-12"
      />,
    );
    expect(
      screen.getByText(/metodologia consagrada de planejamento patrimonial brasileiro/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Susep e planejador CFP/),
    ).toBeInTheDocument();
    expect(screen.getByText(/2026-05-12/)).toBeInTheDocument();
  });

  it("mostra KPIs quando bundle tem policies + gap_analysis", () => {
    const bundle = makeBundle({
      policies: [
        {
          id: "p1",
          category: "vida",
          coverage_brl: 500_000,
          starts_at: "2024-01-01",
          status: "Ativa",
        },
      ],
      gap_analysis: {
        vida: {
          actual_brl: 500_000,
          ideal_brl: 2_000_000,
          gap_brl: 1_500_000,
          methodology: "cerbasi",
        },
      },
    });
    render(<HeroGapProtecaoCard bundle={bundle} />);
    expect(screen.getByTestId("hero-gap-actual")).toBeInTheDocument();
    expect(screen.getByTestId("hero-gap-ideal")).toBeInTheDocument();
    expect(screen.getByTestId("hero-gap-delta")).toBeInTheDocument();
  });
});

describe("<CoberturaSegurosCard /> — tabela de cobertura (ADR-192 §D4)", () => {
  it("renderiza 6 categorias canônicas mesmo sem apólices", () => {
    render(<CoberturaSegurosCard bundle={makeBundle()} />);
    expect(screen.getAllByText(/Vida/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Invalidez/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Saúde/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Patrimonial/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/RC Profissional/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Sucessório/).length).toBeGreaterThan(0);
  });

  it("status 'Contratado' quando há apólice ativa sem gap", () => {
    const bundle = makeBundle({
      policies: [
        {
          id: "p1",
          category: "saude",
          coverage_brl: 500_000,
          premium_monthly_brl: 1_200,
          starts_at: "2024-01-01",
          ends_at: "2027-01-01",
          status: "Ativa",
        },
      ],
    });
    render(<CoberturaSegurosCard bundle={bundle} />);
    const contratadoBadges = screen.getAllByLabelText("Contratado");
    expect(contratadoBadges.length).toBeGreaterThan(0);
  });

  it("disclaimer fiduciário sempre presente", () => {
    render(
      <CoberturaSegurosCard bundle={makeBundle()} effectiveDate="2026-05-12" />,
    );
    expect(
      screen.getByText(/não constitui recomendação fiduciária/),
    ).toBeInTheDocument();
  });

  it("tabela tem aria-label e caption acessível", () => {
    render(<CoberturaSegurosCard bundle={makeBundle()} />);
    expect(
      screen.getByRole("table", { name: /Cobertura de seguros por categoria/ }),
    ).toBeInTheDocument();
  });
});

describe("<SucessaoCard /> — checklist sucessório (ADR-192 §D4)", () => {
  it("variant warn quando há gap (sem apólice sucessória ativa)", () => {
    const { container } = render(<SucessaoCard bundle={makeBundle()} />);
    // ReportCard injeta classe `card-variant-warn`
    expect(container.querySelector(".card-variant-warn")).toBeTruthy();
  });

  it("renderiza 4 items do checklist", () => {
    render(<SucessaoCard bundle={makeBundle()} />);
    expect(screen.getByText(/Testamento registrado/)).toBeInTheDocument();
    expect(
      screen.getByText(/Beneficiários de previdência declarados/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Holding patrimonial avaliada/)).toBeInTheDocument();
    expect(screen.getByText(/ITCMD estimado por estado/)).toBeInTheDocument();
  });

  it("mostra ITCMD estimado quando bundle tem gap_analysis.sucessorio.ideal_brl", () => {
    const bundle = makeBundle({
      gap_analysis: {
        sucessorio: {
          actual_brl: 0,
          ideal_brl: 250_000,
          gap_brl: 250_000,
          methodology: "itcmd_sp_4pct",
        },
      },
    });
    render(<SucessaoCard bundle={bundle} />);
    expect(screen.getByTestId("sucessao-itcmd")).toBeInTheDocument();
  });

  it("disclaimer fiduciário sucessório", () => {
    render(<SucessaoCard bundle={makeBundle()} effectiveDate="2026-05-12" />);
    expect(
      screen.getByText(/metodologia sucessória BR/),
    ).toBeInTheDocument();
  });
});

describe("<AcoesMitigacaoCard /> — lista priorizada (ADR-192 §D4)", () => {
  it("estado vazio quando sem recomendações nem auto-inferred", () => {
    render(<AcoesMitigacaoCard bundle={makeBundle()} />);
    expect(
      screen.getByText(/Nenhuma ação prioritária identificada/),
    ).toBeInTheDocument();
  });

  it("renderiza recomendações ordenadas por prioridade (alta primeiro)", () => {
    const bundle = makeBundle({
      recommendations: [
        { category: "vida", rationale: "Baixa prioridade", priority: "baixa" },
        { category: "vida", rationale: "Alta prioridade", priority: "alta" },
        { category: "invalidez", rationale: "Media prioridade", priority: "média" },
      ],
    });
    render(<AcoesMitigacaoCard bundle={bundle} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Alta prioridade");
    expect(items[1]).toHaveTextContent("Media prioridade");
    expect(items[2]).toHaveTextContent("Baixa prioridade");
  });

  it("renderiza auto_inferred_risks com botão 'Aceitar como Risco' (TODO T05)", () => {
    const onAccept = vi.fn();
    const bundle = makeBundle({
      auto_inferred_risks: [
        {
          category: "vida",
          name: "Falta de seguro de vida",
          rationale: "Dependentes em minoridade sem cobertura",
          estimated_impact_brl: 1_500_000,
          source_calculator: "life_insurance_coverage_ideal",
        },
      ],
    });
    render(<AcoesMitigacaoCard bundle={bundle} onAcceptRisk={onAccept} />);
    expect(screen.getByText(/Falta de seguro de vida/)).toBeInTheDocument();
    const btn = screen.getByRole("button", {
      name: /Aceitar Falta de seguro de vida como Risco/,
    });
    expect(btn).toBeInTheDocument();
    btn.click();
    expect(onAccept).toHaveBeenCalledTimes(1);
  });

  it("disclaimer fiduciário canônico", () => {
    render(
      <AcoesMitigacaoCard bundle={makeBundle()} effectiveDate="2026-05-12" />,
    );
    expect(
      screen.getByText(/não constitui recomendação fiduciária/),
    ).toBeInTheDocument();
  });
});
