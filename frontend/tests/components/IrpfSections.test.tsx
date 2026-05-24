/**
 * Unit tests — ADR-157 · IRPF Full Schema · UI lane.
 * ADR-189 — IrpfPgblCapacidadeCard: switch sobre `pgbl_status` em 4 estados.
 *
 * Cobre:
 * - Contrato de degradação graciosa: workspaces sem `irpf_kpis` no snapshot
 *   E5 não devem renderizar as seções S_IRPF_RENDA / S_IRPF_OTIMIZACAO.
 * - Workspaces com KPIs válidos exibem valores monetários canônicos.
 * - 4 estados do diagnóstico PGBL (copy literal de ADR-189 §4 / §6.1).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { IrpfRendaSection } from "@/components/report/sections/IrpfRendaSection";
import { IrpfOtimizacaoSection } from "@/components/report/sections/IrpfOtimizacaoSection";
import { IrpfPgblCapacidadeCard } from "@/components/report/cards/IrpfPgblCapacidadeCard";
import { IrpfDependentesCard } from "@/components/report/cards/IrpfDependentesCard";
import { IrpfDedutiveisAplicadosCard } from "@/components/report/cards/IrpfDedutiveisAplicadosCard";
import type { IrpfKpis, PgblStatus, DependentesKpi } from "@/types/irpf";
import type { ReportAnalysisData } from "@/lib/api";

const KPIS_BASE: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2023, 2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "5400.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2023": "160000.00", "2024": "180000.00" },
};

function withStatus(status: PgblStatus, overrides: Partial<IrpfKpis> = {}): IrpfKpis {
  return { ...KPIS_BASE, pgbl_status: status, ...overrides };
}

describe("<IrpfRendaSection />", () => {
  it("retorna null quando irpf_kpis ausente (degrada gracioso)", () => {
    const data = { periodo_dados: "2024-01" } as ReportAnalysisData;
    const { container } = render(<IrpfRendaSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("retorna null quando irpf_kpis tem shape inválido", () => {
    const data = { irpf_kpis: { foo: "bar" } } as unknown as ReportAnalysisData;
    const { container } = render(<IrpfRendaSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza a seção e o título quando irpf_kpis válido", () => {
    const data = { irpf_kpis: KPIS_BASE } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 2, name: /Renda Anual e Impostos/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /Renda Anual Familiar/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /^IR Pago$/i })).toBeInTheDocument();
  });
});

describe("<IrpfOtimizacaoSection />", () => {
  it("retorna null quando irpf_kpis ausente", () => {
    const data = {} as ReportAnalysisData;
    const { container } = render(<IrpfOtimizacaoSection data={data} />);
    expect(container.firstChild).toBeNull();
  });

  it("renderiza apenas PGBL quando dependentes e dedutiveis ausentes (ADR-194 degradação)", () => {
    const data = { irpf_kpis: KPIS_BASE } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 2, name: /Otimização Tributária/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: /Capacidade PGBL/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dependentes Declarados/i }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dedutíveis Aplicados/i }),
    ).toBeNull();
  });

  it("renderiza 3 cards quando dependentes + dedutiveis presentes (ADR-194)", () => {
    const data = {
      irpf_kpis: {
        ...KPIS_BASE,
        dependentes: {
          count: 2,
          por_relacao: { conjuge_companheiro: 1, filho_filha: 1 },
        },
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "12345.67", teto_brl: null, teto_aplicado: false },
        },
      },
    } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(screen.getByRole("heading", { level: 3, name: /Capacidade PGBL/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /Dependentes Declarados/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /Dedutíveis Aplicados/i }),
    ).toBeInTheDocument();
  });

  it("esconde Dependentes quando count == 0 (ADR-194 §D9)", () => {
    const data = {
      irpf_kpis: {
        ...KPIS_BASE,
        dependentes: { count: 0, por_relacao: {} },
      },
    } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dependentes Declarados/i }),
    ).toBeNull();
  });

  it("esconde Dedutíveis quando payload vazio (ADR-194 §D9)", () => {
    const data = {
      irpf_kpis: { ...KPIS_BASE, dedutiveis_aplicados: {} },
    } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(
      screen.queryByRole("heading", { level: 3, name: /Dedutíveis Aplicados/i }),
    ).toBeNull();
  });

  it("propaga pgbl_status=modelo_simplificado para subtítulo do card Dedutíveis (ADR-194 §6.4)", () => {
    const data = {
      irpf_kpis: {
        ...KPIS_BASE,
        pgbl_status: "modelo_simplificado",
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "10000.00", teto_brl: null, teto_aplicado: false },
        },
      },
    } as unknown as ReportAnalysisData;
    render(<IrpfOtimizacaoSection data={data} />);
    expect(screen.getByText("Pagamentos elegíveis a dedução · 2024")).toBeInTheDocument();
    expect(screen.queryByText(/Valores deduzidos do imposto/)).toBeNull();
  });
});

describe("<IrpfDependentesCard /> · ADR-194 §6.1", () => {
  const DEPS_BASE: DependentesKpi = {
    count: 3,
    por_relacao: { conjuge_companheiro: 1, filho_filha: 2 },
  };

  it("renderiza count + lista de relações com singular/plural", () => {
    render(<IrpfDependentesCard dependentes={DEPS_BASE} anoBase={2024} />);
    expect(screen.getByRole("heading", { level: 3, name: /Dependentes Declarados/i })).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(
      screen.getByText(/Três dependentes declarados em 2024.*cônjuge · 1.*filho\/filha · 2/),
    ).toBeInTheDocument();
  });

  it("aplica singular quando count == 1", () => {
    const deps: DependentesKpi = { count: 1, por_relacao: { filho_filha: 1 } };
    render(<IrpfDependentesCard dependentes={deps} anoBase={2024} />);
    expect(screen.getByText(/Um dependente declarado em 2024.*filho\/filha · 1/)).toBeInTheDocument();
  });

  it("renderiza com variante neutral por default", () => {
    const { container } = render(
      <IrpfDependentesCard dependentes={DEPS_BASE} anoBase={2024} />,
    );
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
  });

  it("não exibe disclaimer (factual puro sem prescrição)", () => {
    render(<IrpfDependentesCard dependentes={DEPS_BASE} anoBase={2024} />);
    expect(screen.queryByText(/Não é recomendação/)).toBeNull();
  });
});

describe("<IrpfDedutiveisAplicadosCard /> · ADR-194 §6.2", () => {
  it("renderiza linhas sparse com chips por status + disclaimer rodapé", () => {
    const { container } = render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          saude: { utilizado_brl: "18420.00", teto_brl: null, teto_aplicado: false },
          educacao: { utilizado_brl: "2100.00", teto_brl: "3561.50", teto_aplicado: false },
          previdencia_oficial: {
            utilizado_brl: "8176.00",
            teto_brl: null,
            teto_aplicado: false,
          },
        }}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(
      screen.getByRole("heading", { level: 3, name: /Dedutíveis Aplicados por Categoria/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Saúde")).toBeInTheDocument();
    expect(screen.getByText("Educação")).toBeInTheDocument();
    expect(screen.getByText("Previdência oficial (INSS)")).toBeInTheDocument();
    // Disclaimer-rodapé presente
    expect(screen.getByText(/não é recomendação/)).toBeInTheDocument();
    // Variante info (há subutilização em educação)
    expect(container.querySelector(".card-variant-info")).not.toBeNull();
    // Chip "Sem teto legal" para saúde + INSS (2 linhas)
    expect(screen.getAllByText(/Sem teto legal/).length).toBe(2);
    // Chip "Espaço de ..." para educação
    expect(screen.getByText(/Espaço de/)).toBeInTheDocument();
  });

  it("usa variante neutral quando todas linhas estão no teto/sem teto", () => {
    const { container } = render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          saude: { utilizado_brl: "5000.00", teto_brl: null, teto_aplicado: false },
        }}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(container.querySelector(".card-variant-info")).toBeNull();
  });

  it("omite linhas com utilizado == 0 (sparse)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          saude: { utilizado_brl: "10000.00", teto_brl: null, teto_aplicado: false },
        }}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(screen.queryByText("Educação")).toBeNull();
    expect(screen.queryByText("Pensão alimentícia")).toBeNull();
    expect(screen.queryByText("Previdência oficial (INSS)")).toBeNull();
  });

  it('exibe chip "No teto" quando teto_aplicado=true', () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          educacao: { utilizado_brl: "3561.50", teto_brl: "3561.50", teto_aplicado: true },
        }}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(screen.getByText(/No teto/)).toBeInTheDocument();
  });
});

describe("<IrpfDedutiveisAplicadosCard /> · ADR-194 §6.4 — subtítulo condicional ao regime", () => {
  const DEDUTIVEIS_FIXTURE = {
    saude: { utilizado_brl: "10000.00", teto_brl: null, teto_aplicado: false },
  };

  it("capacidade_disponivel: subtítulo 'Valores deduzidos do imposto'", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_FIXTURE}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(screen.getByText("Valores deduzidos do imposto · 2024")).toBeInTheDocument();
    expect(screen.queryByText(/Pagamentos elegíveis a dedução/)).toBeNull();
  });

  it("no_teto: subtítulo 'Valores deduzidos do imposto' (modelo completa)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_FIXTURE}
        anoBase={2024}
        pgblStatus="no_teto"
      />,
    );
    expect(screen.getByText("Valores deduzidos do imposto · 2024")).toBeInTheDocument();
    expect(screen.queryByText(/Pagamentos elegíveis a dedução/)).toBeNull();
  });

  it("modelo_simplificado: subtítulo 'Pagamentos elegíveis a dedução' (não-deduzido)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_FIXTURE}
        anoBase={2024}
        pgblStatus="modelo_simplificado"
      />,
    );
    expect(screen.getByText("Pagamentos elegíveis a dedução · 2024")).toBeInTheDocument();
    expect(screen.queryByText(/Valores deduzidos do imposto/)).toBeNull();
  });

  it("sem_renda_tributavel: subtítulo 'Pagamentos elegíveis a dedução' (sem base)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_FIXTURE}
        anoBase={2024}
        pgblStatus="sem_renda_tributavel"
      />,
    );
    expect(screen.getByText("Pagamentos elegíveis a dedução · 2024")).toBeInTheDocument();
    expect(screen.queryByText(/Valores deduzidos do imposto/)).toBeNull();
  });

  it("título e disclaimer-rodapé inalterados em simplificado (chip 'Espaço de' vira 'Sem efeito neste regime' — ADR-198)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          saude: { utilizado_brl: "10000.00", teto_brl: null, teto_aplicado: false },
          educacao: { utilizado_brl: "2100.00", teto_brl: "3561.50", teto_aplicado: false },
        }}
        anoBase={2024}
        pgblStatus="modelo_simplificado"
      />,
    );
    expect(
      screen.getByRole("heading", { level: 3, name: /Dedutíveis Aplicados por Categoria/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Sem teto legal/)).toBeInTheDocument();
    expect(screen.queryByText(/Espaço de/)).toBeNull();
    expect(screen.getByText("Sem efeito neste regime")).toBeInTheDocument();
    expect(screen.getByText(/não é recomendação/)).toBeInTheDocument();
  });
});

describe("<IrpfDedutiveisAplicadosCard /> · ADR-198 — chip 'Espaço' condicional ao regime", () => {
  const DEDUTIVEIS_COM_SUBUTILIZACAO = {
    saude: { utilizado_brl: "10000.00", teto_brl: null, teto_aplicado: false },
    educacao: { utilizado_brl: "2100.00", teto_brl: "3561.50", teto_aplicado: false },
  };

  it("modelo_simplificado: ramo subutilizado vira chip 'Sem efeito neste regime' (neutral)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="modelo_simplificado"
      />,
    );
    expect(screen.getByText("Sem efeito neste regime")).toBeInTheDocument();
    expect(screen.queryByText(/Espaço de/)).toBeNull();
    // Outros chips factuais permanecem
    expect(screen.getByText(/Sem teto legal/)).toBeInTheDocument();
  });

  it("sem_renda_tributavel: ramo subutilizado vira chip 'Sem efeito neste regime' (neutral)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="sem_renda_tributavel"
      />,
    );
    expect(screen.getByText("Sem efeito neste regime")).toBeInTheDocument();
    expect(screen.queryByText(/Espaço de/)).toBeNull();
    expect(screen.getByText(/Sem teto legal/)).toBeInTheDocument();
  });

  it("capacidade_disponivel: chip 'Espaço de' preservado (regression guard)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(screen.getByText(/Espaço de/)).toBeInTheDocument();
    expect(screen.queryByText("Sem efeito neste regime")).toBeNull();
  });

  it("no_teto: chip 'Espaço de' preservado em dedutíveis (no_teto é regime completa — ADR-189 Estado 3)", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="no_teto"
      />,
    );
    expect(screen.getByText(/Espaço de/)).toBeInTheDocument();
    expect(screen.queryByText("Sem efeito neste regime")).toBeNull();
  });

  it("modelo_simplificado: variante do card permanece 'neutral' mesmo com subutilização (ADR-198 §3.2)", () => {
    const { container } = render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="modelo_simplificado"
      />,
    );
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(container.querySelector(".card-variant-info")).toBeNull();
  });

  it("sem_renda_tributavel: variante do card permanece 'neutral' mesmo com subutilização (ADR-198 §3.2)", () => {
    const { container } = render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="sem_renda_tributavel"
      />,
    );
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(container.querySelector(".card-variant-info")).toBeNull();
  });

  it("capacidade_disponivel: variante escala para 'info' com subutilização (regression guard)", () => {
    const { container } = render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={DEDUTIVEIS_COM_SUBUTILIZACAO}
        anoBase={2024}
        pgblStatus="capacidade_disponivel"
      />,
    );
    expect(container.querySelector(".card-variant-info")).not.toBeNull();
  });

  it("modelo_simplificado: chip 'No teto' preservado quando teto_aplicado=true (não vira 'Sem efeito neste regime')", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          educacao: { utilizado_brl: "3561.50", teto_brl: "3561.50", teto_aplicado: true },
        }}
        anoBase={2024}
        pgblStatus="modelo_simplificado"
      />,
    );
    expect(screen.getByText(/No teto/)).toBeInTheDocument();
    expect(screen.queryByText("Sem efeito neste regime")).toBeNull();
  });

  it("sem_renda_tributavel: chip 'Sem teto legal' preservado (não vira 'Sem efeito neste regime')", () => {
    render(
      <IrpfDedutiveisAplicadosCard
        dedutiveis={{
          saude: { utilizado_brl: "5000.00", teto_brl: null, teto_aplicado: false },
        }}
        anoBase={2024}
        pgblStatus="sem_renda_tributavel"
      />,
    );
    expect(screen.getByText(/Sem teto legal/)).toBeInTheDocument();
    expect(screen.queryByText("Sem efeito neste regime")).toBeNull();
  });
});

describe("<IrpfPgblCapacidadeCard /> · ADR-189 · 4 estados", () => {
  it("Estado 1 — capacidade_disponivel: variante info, disclaimer presente, valor monetário", () => {
    const kpis = withStatus("capacidade_disponivel", {
      pgbl_capacidade_dedutivel_brl: "11600.00",
      pgbl_aportado_brl: "10000.00",
      pgbl_teto_brl: "21600.00",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-info")).not.toBeNull();
    expect(screen.getByText(/Espaço dedutível remanescente · 2024/)).toBeInTheDocument();
    expect(screen.getByText(/Não é recomendação:/)).toBeInTheDocument();
    expect(screen.getByText(/tabela regressiva vs\. progressiva/)).toBeInTheDocument();
    expect(screen.getByText(/horizonte de resgate/)).toBeInTheDocument();
    expect(screen.getByText(/taxa de administração/)).toBeInTheDocument();
    expect(screen.getByText(/contribuição ao INSS/)).toBeInTheDocument();
    // Não usa "—" no estado positivo (zero monetário não aplicável aqui)
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).not.toBe("—");
  });

  describe("Estado 1 — ADR-195 · A12 · threshold AUVP modula variante + sufixo subtitle", () => {
    it("auvp_aderente (alíq >= 20%): variante info, sufixo 'alíquota efetiva alta', parágrafo + disclaimer intactos", () => {
      const kpis = withStatus("capacidade_disponivel", {
        aliquota_sobre_tributavel_pct: "22.50",
        pgbl_capacidade_dedutivel_brl: "11600.00",
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(container.querySelector(".card-variant-info")).not.toBeNull();
      expect(
        screen.getByText(/Espaço dedutível remanescente · 2024 · alíquota efetiva alta/),
      ).toBeInTheDocument();
      // ADR-189 §4 Estado 1 — copy literal preservada (não há regressão)
      expect(screen.getByText(/Não é recomendação:/)).toBeInTheDocument();
      expect(screen.getByText(/tabela regressiva vs\. progressiva/)).toBeInTheDocument();
    });

    it("neutro (12% <= alíq < 20%): variante info, sufixo 'alíquota efetiva intermediária'", () => {
      const kpis = withStatus("capacidade_disponivel", {
        aliquota_sobre_tributavel_pct: "16.50",
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(container.querySelector(".card-variant-info")).not.toBeNull();
      expect(
        screen.getByText(
          /Espaço dedutível remanescente · 2024 · alíquota efetiva intermediária/,
        ),
      ).toBeInTheDocument();
      expect(screen.getByText(/Não é recomendação:/)).toBeInTheDocument();
    });

    it("abaixo (alíq < 12%): variante neutral, sufixo 'alíquota efetiva baixa', hero monetário preservado", () => {
      const kpis = withStatus("capacidade_disponivel", {
        aliquota_sobre_tributavel_pct: "7.50",
        pgbl_capacidade_dedutivel_brl: "4500.00",
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
      expect(container.querySelector(".card-variant-info")).toBeNull();
      expect(
        screen.getByText(/Espaço dedutível remanescente · 2024 · alíquota efetiva baixa/),
      ).toBeInTheDocument();
      // Hero permanece colorido (não vira "—") — ADR-195 §3 D5
      const heroLine = container.querySelector(".font-mono.text-2xl");
      expect(heroLine?.textContent).not.toBe("—");
      // Disclaimer e parágrafo ADR-189 §4 intactos
      expect(screen.getByText(/Não é recomendação:/)).toBeInTheDocument();
    });

    it("indeterminado (alíquota inválida): fallback info, sem sufixo (ADR-195 §3 D5)", () => {
      const kpis = withStatus("capacidade_disponivel", {
        aliquota_sobre_tributavel_pct: "",
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(container.querySelector(".card-variant-info")).not.toBeNull();
      // Subtitle sem sufixo "alíquota efetiva ..."
      expect(
        screen.queryByText(/alíquota efetiva (alta|intermediária|baixa)/),
      ).toBeNull();
      // Subtitle base ainda presente
      expect(screen.getByText(/Espaço dedutível remanescente · 2024/)).toBeInTheDocument();
    });
  });

  it("Estado 2 — modelo_simplificado: variante neutral, '—', sem disclaimer", () => {
    const kpis = withStatus("modelo_simplificado", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "0",
      pgbl_teto_brl: "0",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(screen.getAllByText(/Não se aplica · 2024/).length).toBeGreaterThan(0);
    expect(screen.getByText(/modelo simplificado em 2024/)).toBeInTheDocument();
    expect(screen.getByText(/desconto fixo sobre os rendimentos tributáveis/)).toBeInTheDocument();
    expect(screen.getByText(/A capacidade de 12% só vale no modelo completo\./)).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).toBe("—");
  });

  describe("Estado 2 — ADR-197 · A12 · componentes elegíveis + ponteiro PGD/MIR", () => {
    it("renderiza lista sparse com 4 dedutíveis + dependentes + PGBL aportado quando todos presentes", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "5000.00",
        pgbl_teto_brl: "0",
        dependentes: {
          count: 2,
          por_relacao: { conjuge_companheiro: 1, filho_filha: 1 },
        },
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "8420.00", teto_brl: null, teto_aplicado: false },
          educacao: { utilizado_brl: "2100.00", teto_brl: "3561.50", teto_aplicado: false },
          previdencia_oficial: { utilizado_brl: "6500.00", teto_brl: null, teto_aplicado: false },
          pensao_alimenticia: { utilizado_brl: "1200.00", teto_brl: null, teto_aplicado: false },
        },
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(screen.getByText(/Componentes elegíveis no modelo completo/)).toBeInTheDocument();
      expect(screen.getByText("Saúde")).toBeInTheDocument();
      expect(screen.getByText("Educação")).toBeInTheDocument();
      expect(screen.getByText("Previdência oficial (INSS)")).toBeInTheDocument();
      expect(screen.getByText("Pensão alimentícia")).toBeInTheDocument();
      expect(screen.getByText("Dependentes")).toBeInTheDocument();
      expect(screen.getByText("PGBL aportado")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(
        screen.getByText(
          /O programa da Receita \(PGD\/MIR\) compara automaticamente os dois modelos/,
        ),
      ).toBeInTheDocument();
    });

    it("omite categorias com valor zero ou ausente (lista sparse)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "0",
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "8420.00", teto_brl: null, teto_aplicado: false },
          educacao: { utilizado_brl: "0", teto_brl: "3561.50", teto_aplicado: false },
        },
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(screen.getByText(/Componentes elegíveis no modelo completo/)).toBeInTheDocument();
      expect(screen.getByText("Saúde")).toBeInTheDocument();
      expect(screen.queryByText("Educação")).toBeNull();
      expect(screen.queryByText("Previdência oficial (INSS)")).toBeNull();
      expect(screen.queryByText("Pensão alimentícia")).toBeNull();
      expect(screen.queryByText("Dependentes")).toBeNull();
      expect(screen.queryByText("PGBL aportado")).toBeNull();
    });

    it("renderiza PGBL aportado quando simplificado tem aporte mas zero dedutíveis (caso real ADR-196)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "3000.00",
        pgbl_teto_brl: "0",
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(screen.getByText(/Componentes elegíveis no modelo completo/)).toBeInTheDocument();
      expect(screen.getByText("PGBL aportado")).toBeInTheDocument();
    });

    it("omite a lista inteira quando todos os componentes são zero/ausentes (sem ruído visual)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "0",
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(screen.queryByText(/Componentes elegíveis no modelo completo/)).toBeNull();
      expect(screen.queryByText("Saúde")).toBeNull();
      expect(screen.queryByText("Dependentes")).toBeNull();
    });

    it("ponteiro PGD/MIR sempre presente no Estado 2, mesmo sem componentes elegíveis", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "0",
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(
        screen.getByText(
          /O programa da Receita \(PGD\/MIR\) compara automaticamente os dois modelos/,
        ),
      ).toBeInTheDocument();
    });

    it("preserva variante neutral mesmo com lista completa (não escala para info)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "5000.00",
        dependentes: { count: 1, por_relacao: { filho_filha: 1 } },
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "12000.00", teto_brl: null, teto_aplicado: false },
        },
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
      expect(container.querySelector(".card-variant-info")).toBeNull();
      expect(container.querySelector(".card-variant-feature")).toBeNull();
    });

    it("disclaimer 'Não é recomendação' permanece ausente mesmo com lista de componentes (ADR-189 §D4 preservado)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "3000.00",
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "8000.00", teto_brl: null, teto_aplicado: false },
        },
      });
      render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    });

    it("hero permanece '—' mesmo com componentes presentes (zero monetário não aplicável)", () => {
      const kpis = withStatus("modelo_simplificado", {
        pgbl_aportado_brl: "5000.00",
        dedutiveis_aplicados: {
          saude: { utilizado_brl: "8000.00", teto_brl: null, teto_aplicado: false },
        },
      });
      const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
      const heroLine = container.querySelector(".font-mono.text-2xl");
      expect(heroLine?.textContent).toBe("—");
    });
  });

  it("Estado 3 — no_teto: variante feature, R$ 0,00, sem disclaimer", () => {
    const kpis = withStatus("no_teto", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "24000.00",
      pgbl_teto_brl: "24000.00",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-feature")).not.toBeNull();
    expect(screen.getByText(/Teto dedutível atingido · 2024/)).toBeInTheDocument();
    expect(screen.getByText(/esgotando os 12% dedutíveis/)).toBeInTheDocument();
    expect(
      screen.getByText(/Não há capacidade dedutível remanescente em 2024\./),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).not.toBe("—");
    expect(heroLine?.textContent ?? "").toMatch(/0,00/);
  });

  it("Estado 4 — sem_renda_tributavel: variante neutral, '—', sem disclaimer", () => {
    const kpis = withStatus("sem_renda_tributavel", {
      pgbl_capacidade_dedutivel_brl: "0",
      pgbl_aportado_brl: "0",
      pgbl_teto_brl: "0",
    });
    const { container } = render(<IrpfPgblCapacidadeCard kpis={kpis} />);
    expect(container.querySelector(".card-variant-neutral")).not.toBeNull();
    expect(screen.getByText(/Não se aplica · 2024/)).toBeInTheDocument();
    expect(
      screen.getByText(/apenas rendimentos isentos ou de tributação exclusiva/),
    ).toBeInTheDocument();
    expect(screen.getByText(/PGBL deduz da renda tributável/)).toBeInTheDocument();
    expect(screen.queryByText(/Não é recomendação:/)).toBeNull();
    const heroLine = container.querySelector(".font-mono.text-2xl");
    expect(heroLine?.textContent).toBe("—");
  });
});

// ----------------------------------------------------------------------------
// IrpfRendaAnualCard — ADR-266 tri-state (completo / provisorio / incompleto)
// ----------------------------------------------------------------------------

describe("<IrpfRendaAnualCard /> · ADR-266 completude tri-state", () => {
  it("renderiza Bruta + Líquida quando completo e valores divergentes (default)", () => {
    const kpis: IrpfKpis = {
      ...KPIS_BASE,
      ano_base_default: 2024,
      ano_base_completude: "completo",
      completude_motivo: null,
      anos_completude_por_ano: { "2023": "completo", "2024": "completo" },
    };
    const data = { irpf_kpis: kpis } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(screen.getByText(/Bruta · 2024/i)).toBeInTheDocument();
    expect(screen.getByText(/Líquida.*após IR/i)).toBeInTheDocument();
    // Badge não aparece quando completude=completo
    expect(screen.queryByRole("status", { name: /incompleto|provisório/i })).toBeNull();
  });

  it("collapse 1 linha quando completo + bruta == liquida (sem retenção)", () => {
    const kpis: IrpfKpis = {
      ...KPIS_BASE,
      renda_anual_familiar_brl: "100000.00",
      renda_liquida_familiar_brl: "100000.00",
      ano_base_default: 2024,
      ano_base_completude: "completo",
    };
    const data = { irpf_kpis: kpis } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(screen.getByText(/Renda Familiar · 2024/i)).toBeInTheDocument();
    expect(screen.getByText(/Sem retenção de IR ou INSS no ano/i)).toBeInTheDocument();
    // Bruta/Líquida NÃO aparecem como labels separados
    expect(screen.queryByText(/^Bruta · 2024$/)).toBeNull();
  });

  it("mostra badge + motivo quando incompleto, usando ano_base_default", () => {
    const kpis: IrpfKpis = {
      ...KPIS_BASE,
      ano_base: 2025,
      ano_base_default: 2024,
      ano_base_completude: "incompleto",
      completude_motivo: "Falta declaração de CPF ***.***.***-60 (presente em ano-base anterior).",
      evolucao_renda_anos: { "2024": "180000.00", "2025": "5469.95" },
      renda_anual_familiar_brl: "5469.95",
      renda_liquida_familiar_brl: "5469.95",
    };
    const data = { irpf_kpis: kpis } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(screen.getByRole("status", { name: /Ano-base incompleto/i })).toBeInTheDocument();
    expect(screen.getByText(/Falta declaração de CPF/i)).toBeInTheDocument();
    expect(screen.getByText(/Bruta · 2024/i)).toBeInTheDocument();
    // Não mostra o ano ruidoso (2025)
    expect(screen.queryByText(/Bruta · 2025/)).toBeNull();
  });

  it("mostra badge 'Provisório' quando dentro da janela RFB", () => {
    const kpis: IrpfKpis = {
      ...KPIS_BASE,
      ano_base: 2025,
      ano_base_default: 2024,
      ano_base_completude: "provisorio",
      completude_motivo: "Ano-base 2025 dentro da janela RFB.",
    };
    const data = { irpf_kpis: kpis } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(screen.getByRole("status", { name: /Provisório/i })).toBeInTheDocument();
  });

  it("workspace pre-ADR-266 (sem campos novos) assume completo no ano_base", () => {
    const data = { irpf_kpis: KPIS_BASE } as unknown as ReportAnalysisData;
    render(<IrpfRendaSection data={data} />);
    expect(screen.getByText(/Bruta · 2024/i)).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
