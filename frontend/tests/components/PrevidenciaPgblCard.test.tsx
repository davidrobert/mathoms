/**
 * Unit tests — ADR-196 · A12 · Card A Previdência PGBL (6 modos).
 *
 * Pattern espelha `IrpfSections.test.tsx`: asserções pontuais sobre
 * variante, presença/ausência de disclaimer/grid/cross-link e copy
 * literal por modo. Não usa snapshot DOM completo.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  PrevidenciaPgblCard,
  type PrevidenciaPgblData,
} from "@/components/report/cards/PrevidenciaPgblCard";

const PREVIDENCIA_BASE: PrevidenciaPgblData = {
  status: "Calculado",
  nota: "Base: receita PJ anualizada R$ 240.000, lucro presumido 32%.",
  renda_tributavel_anual: 76800,
  limite_pgbl_anual: 9216,
  aporte_mensal: 768,
  aliquota_marginal: 27.5,
  economia_ir_anual: 2534.4,
};

describe("<PrevidenciaPgblCard /> · modo default", () => {
  it("renderiza grid de 4 KPIs + disclaimer 'Não é recomendação'", () => {
    render(<PrevidenciaPgblCard previdencia={PREVIDENCIA_BASE} mode="default" />);
    expect(screen.getByText(/Renda tributável\/ano/i)).toBeInTheDocument();
    expect(screen.getByText(/Limite PGBL\/ano \(12%\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Aporte sugerido\/mês/i)).toBeInTheDocument();
    expect(screen.getByText(/Economia de IR\/ano/i)).toBeInTheDocument();
    expect(screen.getByText(/Não é recomendação:/i)).toBeInTheDocument();
    expect(screen.getByText(/regime tributário declarado.*contribuição ao INSS/i)).toBeInTheDocument();
  });

  it("renderiza nota explicativa do cálculo quando presente", () => {
    render(<PrevidenciaPgblCard previdencia={PREVIDENCIA_BASE} mode="default" />);
    expect(screen.getByText(/Base: receita PJ anualizada/i)).toBeInTheDocument();
  });

  it("usa default mode quando prop mode omitido (compat legacy)", () => {
    render(<PrevidenciaPgblCard previdencia={PREVIDENCIA_BASE} />);
    expect(screen.getByText(/Aporte sugerido\/mês/i)).toBeInTheDocument();
    expect(screen.getByText(/Não é recomendação:/i)).toBeInTheDocument();
  });

  it("retorna empty card quando status = 'Não aplicável'", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={{ status: "Não aplicável" }}
        mode="default"
      />,
    );
    expect(
      screen.getByText(/PGBL não aplicável para este perfil tributário/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Aporte sugerido/i)).not.toBeInTheDocument();
  });

  it("retorna empty card quando previdencia undefined", () => {
    render(<PrevidenciaPgblCard previdencia={undefined} />);
    expect(
      screen.getByText(/PGBL não aplicável para este perfil tributário/i),
    ).toBeInTheDocument();
  });
});

describe("<PrevidenciaPgblCard /> · modo default-defasado", () => {
  it("mantém grid + adiciona nota de defasagem com ano_base", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={PREVIDENCIA_BASE}
        mode="default-defasado"
        anoBase={2022}
      />,
    );
    expect(screen.getByText(/Última declaração: 2022 · defasada/i)).toBeInTheDocument();
    expect(screen.getByText(/Aporte sugerido\/mês/i)).toBeInTheDocument();
    expect(screen.getByText(/Não é recomendação:/i)).toBeInTheDocument();
  });
});

describe("<PrevidenciaPgblCard /> · modo informative-capacidade", () => {
  it("suprime grid, mostra cross-link e copy de capacidade", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={PREVIDENCIA_BASE}
        mode="informative-capacidade"
        anoBase={2024}
      />,
    );
    expect(screen.queryByText(/Aporte sugerido\/mês/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Economia de IR\/ano/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/i)).not.toBeInTheDocument();

    expect(
      screen.getByText(/Capacidade dedutível autoritativa está em/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/baseada no IRPF 2024 declarado/i)).toBeInTheDocument();

    const crossLinks = screen.getAllByRole("link", { name: /Otimização Tributária/i });
    expect(crossLinks.length).toBeGreaterThan(0);
    expect(crossLinks[0]).toHaveAttribute("href", "#S_IRPF_OTIMIZACAO");
  });
});

describe("<PrevidenciaPgblCard /> · modo informative-simplificado", () => {
  it("mostra '—' com aria-label + copy do modelo simplificado", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={PREVIDENCIA_BASE}
        mode="informative-simplificado"
        anoBase={2024}
      />,
    );
    expect(
      screen.getByLabelText(/Métrica não aplicável/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/declaração de 2024 é pelo modelo simplificado/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/caso houvesse migração para o modelo completo/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Aporte sugerido\/mês/i)).not.toBeInTheDocument();
  });
});

describe("<PrevidenciaPgblCard /> · modo informative-no-teto", () => {
  it("não usa '—' (mostra parágrafo factual sem hero monetário)", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={PREVIDENCIA_BASE}
        mode="informative-no-teto"
        anoBase={2024}
      />,
    );
    expect(
      screen.getByText(/Em 2024 você esgotou os dedutíveis/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Capacidade adicional só no próximo ano-base/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Aporte sugerido\/mês/i)).not.toBeInTheDocument();

    const crossLinks = screen.getAllByRole("link", { name: /Otimização Tributária/i });
    expect(crossLinks[0]).toHaveAttribute("href", "#S_IRPF_OTIMIZACAO");
  });
});

describe("<PrevidenciaPgblCard /> · modo informative-sem-renda", () => {
  it("mostra '—' + copy explicando isentos/exclusiva", () => {
    render(
      <PrevidenciaPgblCard
        previdencia={PREVIDENCIA_BASE}
        mode="informative-sem-renda"
        anoBase={2024}
      />,
    );
    expect(
      screen.getByLabelText(/Métrica não aplicável/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/apenas rendimentos isentos ou de tributação exclusiva/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/só geraria espaço dedutível se classificada como tributável/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Aporte sugerido\/mês/i)).not.toBeInTheDocument();
  });
});
