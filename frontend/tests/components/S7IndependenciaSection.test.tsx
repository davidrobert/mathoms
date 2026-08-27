/**
 * Tests — Lane A8.3 (TRS real) · S7 com 4 KPIs + tooltip + 2 banners + empty states.
 *
 * Cobre matriz de cenários:
 * - 3 fases (acumulação · aproximação · independência) × 2 acumuladores
 *   (low/high) × 3 defasagens (none/info/warning) = 18 cenários.
 * - 2 empty states: ``sem_irpf`` e ``gerador_zero``.
 * - Caption permanente em acumulação aparece/some.
 * - Card "Em acumuladores" tom warning + sublabel quando >40%.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  S7IndependenciaSection,
  TRS_EFETIVA_TOOLTIP,
} from "@/components/report/sections/S7IndependenciaSection";
import type {
  IFMonteCarloData,
  PassiveIncomeData,
  PremissasEconomicasData,
  ReportAnalysisData,
} from "@/lib/api";
import type { IrpfKpis } from "@/types/irpf";

function makePassiveIncome(
  overrides: Partial<PassiveIncomeData> = {},
): PassiveIncomeData {
  return {
    status: "ok",
    renda_passiva_anual_brl: 24_000,
    renda_passiva_mensal_brl: 2_000,
    renda_passiva_por_fonte_brl: {
      dividendos: 12_000,
      jcp: 4_000,
      aplicacoes: 3_000,
      exterior: 3_000,
      alugueis: 2_000,
    },
    renda_ativa_pj_excluida_brl: 0,
    ganho_capital_excluido_brl: 2_000,
    patrimonio_gerador_brl: 1_000_000,
    trs_efetiva_pct: 2.4,
    ano_referencia_irpf: 2024,
    defasagem_meses: 5,
    acumuladores_pct_gerador: 12.0,
    ...overrides,
  };
}

function makeData(
  overrides: Partial<ReportAnalysisData> = {},
): ReportAnalysisData {
  return {
    goals: {
      if_meta: 5_000_000,
      if_pct: 30,
      if_trs: 5,
      ano_if: 2040,
      if_gap: 4_000_000,
    },
    passive_income: makePassiveIncome(),
    ...overrides,
  };
}

const IRPF_KPIS: IrpfKpis = {
  ano_base: 2024,
  anos_disponiveis: [2024],
  renda_anual_familiar_brl: "180000.00",
  renda_liquida_familiar_brl: "144000.00",
  ir_pago_total_brl: "24000.00",
  aliquota_sobre_tributavel_pct: "16.50",
  aliquota_sobre_total_pct: "13.30",
  pgbl_capacidade_dedutivel_brl: "11600.00",
  pgbl_status: "capacidade_disponivel",
  pgbl_aportado_brl: "10000.00",
  pgbl_teto_brl: "21600.00",
  split_trabalho_brl: "120000.00",
  split_capital_brl: "60000.00",
  evolucao_renda_anos: { "2024": "180000.00" },
};

describe("<S7IndependenciaSection /> · localização PGBL", () => {
  it("declara o IRPF ausente sem número nem âncora morta", () => {
    render(<S7IndependenciaSection data={makeData()} />);
    expect(screen.getByTestId("s7-pgbl-without-irpf")).toHaveTextContent(
      /não há declaração de IRPF processada/i,
    );
    expect(
      screen.queryByRole("link", { name: /Otimização Tributária/i }),
    ).toBeNull();
    expect(
      screen.getByRole("link", { name: /Importar declaração de IRPF/i }),
    ).toHaveAttribute("href", "/documents");
  });

  it("aponta para o Card B quando há IRPF processado", () => {
    const data = makeData({
      irpf_kpis: IRPF_KPIS as unknown as Record<string, unknown>,
      fluxo_caixa: {
        receita_despesa_mensal_detalhado: { labels: ["2024-12"] },
      },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByTestId("s7-pgbl-location")).toHaveTextContent(
      /IRPF de 2024/i,
    );
    expect(
      screen.getByRole("link", { name: /Otimização Tributária/i }),
    ).toHaveAttribute("href", "#S_IRPF_OTIMIZACAO");
    expect(screen.queryByText(/defasado em/i)).toBeNull();
  });

  it("preserva o aviso de defasagem maior ou igual a dois anos", () => {
    const data = makeData({
      irpf_kpis: { ...IRPF_KPIS, ano_base: 2022 } as unknown as Record<
        string,
        unknown
      >,
      fluxo_caixa: {
        receita_despesa_mensal_detalhado: { labels: ["2025-12"] },
      },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByTestId("s7-pgbl-location")).toHaveTextContent(
      /defasado em 3 anos/i,
    );
    expect(screen.getByTestId("s7-pgbl-location")).toHaveTextContent(
      /IRPF mais recente/i,
    );
  });
});

describe("<S7IndependenciaSection /> · empty states", () => {
  it("renderiza empty state sem_irpf com CTA Importar IRPF", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ status: "sem_irpf" }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("heading", { level: 3, name: /Importe seu IRPF/i }),
    ).toBeInTheDocument();
    // EmptyState renderiza link como <a role="button"> — busca por texto.
    const cta = screen.getByText("Importar IRPF");
    expect(cta.closest("a")).toHaveAttribute("href", "/documents");
  });

  it("renderiza empty state gerador_zero (sem CTA)", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ status: "gerador_zero" }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: /TRS efetiva começa quando há patrimônio/i,
      }),
    ).toBeInTheDocument();
  });

  it("não renderiza KPIs de TRS quando passive_income ausente", () => {
    const data = makeData({ passive_income: undefined });
    render(<S7IndependenciaSection data={data} />);
    // O label "TRS efetiva" só aparece dentro do bloco PassiveIncomeOk;
    // botão "Sobre TRS efetiva" tem aria-label específico que cobre ausência.
    expect(
      screen.queryByRole("button", { name: /Sobre TRS efetiva/i }),
    ).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · caption de acumulação", () => {
  it("aparece quando progresso < 50", () => {
    const data = makeData({
      goals: { if_meta: 5_000_000, if_pct: 30, if_trs: 5 },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/Carteira em acumulação/i)).toBeInTheDocument();
  });

  it("some quando progresso >= 50", () => {
    const data = makeData({
      goals: { if_meta: 5_000_000, if_pct: 60, if_trs: 5 },
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/Carteira em acumulação/i)).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · banners condicionais", () => {
  it("AcumuladoresBanner aparece quando pct > 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 60 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByText(
        /sua carteira de renda está em ativos sem distribuição/i,
      ),
    ).toBeInTheDocument();
  });

  it("AcumuladoresBanner some quando pct <= 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 35 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByText(
        /sua carteira de renda está em ativos sem distribuição/i,
      ),
    ).toBeNull();
  });

  it("DefasagemWarningBanner aparece quando defasagem >= 15m", () => {
    const data = makeData({
      passive_income: makePassiveIncome({
        defasagem_meses: 18,
        ano_referencia_irpf: 2023,
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/IRPF de 2023 desatualizado/i)).toBeInTheDocument();
  });

  it("DefasagemWarningBanner some quando defasagem < 15m", () => {
    const data = makeData({
      passive_income: makePassiveIncome({
        defasagem_meses: 12,
        ano_referencia_irpf: 2024,
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/desatualizado/i)).toBeNull();
  });
});

describe("<S7IndependenciaSection /> · loop visual KPI↔banner", () => {
  it("card Em acumuladores tem sublabel '>40% subestima TRS' quando pct > 40", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 60 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/>40% subestima TRS/)).toBeInTheDocument();
  });

  it("card Em acumuladores mostra 'Sem ETFs/fundos acumuladores' quando 0", () => {
    const data = makeData({
      passive_income: makePassiveIncome({ acumuladores_pct_gerador: 0 }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByText(/Sem ETFs\/fundos acumuladores/i),
    ).toBeInTheDocument();
  });
});

describe("<S7IndependenciaSection /> · matriz fase × acumuladores × defasagem (18 cenários)", () => {
  const PHASES = [
    { name: "acumulacao", if_pct: 30 },
    { name: "aproximacao", if_pct: 70 },
    { name: "independencia", if_pct: 96 },
  ];
  const ACUMULADORES = [
    { name: "low", pct: 12 },
    { name: "high", pct: 60 },
  ];
  const DEFASAGENS = [
    { name: "none", meses: 5 },
    { name: "info", meses: 8 },
    { name: "warning", meses: 18 },
  ];

  for (const phase of PHASES) {
    for (const acum of ACUMULADORES) {
      for (const def of DEFASAGENS) {
        it(`renderiza 4 KPIs em ${phase.name} × ${acum.name} acumuladores × ${def.name} defasagem`, () => {
          const data = makeData({
            goals: { if_meta: 5_000_000, if_pct: phase.if_pct, if_trs: 5 },
            passive_income: makePassiveIncome({
              acumuladores_pct_gerador: acum.pct,
              defasagem_meses: def.meses,
              ano_referencia_irpf: 2024,
            }),
          });
          render(<S7IndependenciaSection data={data} />);
          // 4 KPIs sempre presentes em status ok — usamos getAllByText pois
          // "Renda passiva" também aparece no NarrativeChartCard.
          expect(screen.getAllByText(/Renda passiva/i).length).toBeGreaterThan(
            0,
          );
          expect(screen.getByText(/Patrimônio investido/i)).toBeInTheDocument();
          expect(screen.getByText(/Em acumuladores/i)).toBeInTheDocument();
        });
      }
    }
  }
});

describe("<S7IndependenciaSection /> · acessibilidade (label + tooltip)", () => {
  it("InfoTooltip tem aria-label descritivo, não apenas ícone", () => {
    const data = makeData();
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.getByRole("button", { name: /Sobre TRS efetiva/i }),
    ).toBeInTheDocument();
  });
});

// ─── A28.l9 — ressalva de premissas fallback no Monte Carlo ───

function makeMonteCarlo(
  overrides: Partial<IFMonteCarloData> = {},
): IFMonteCarloData {
  return {
    // ADR-369 D1 — cenário nomeado: favorável é o ano mais CEDO (2036), adverso
    // é o mais tarde (2044). O fixture antigo lia `p10_ano_if: 2044`, que era
    // literalmente a inversão que o rename existe para desfazer.
    ano_if_cenario_favoravel: 2036,
    ano_if_cenario_central: 2040,
    ano_if_cenario_adverso: 2044,
    prob_if_ate_prazo_declarado: 0.31,
    prazo_declarado_anos: 15,
    ano_alvo_declarado: 2041,
    declarado_em: "2026-03-01",
    sigma_usado: 0.15,
    exibir_cone: true,
    motivo_sem_cone: null,
    caminho_p10: [[2026, 1_000_000]],
    caminho_p50: [[2026, 1_000_000]],
    caminho_p90: [[2026, 1_000_000]],
    ...overrides,
  };
}

function makePremissasEconomicas(
  status: "completo" | "parcial",
  classStatus: "emitted" | "indisponivel",
): PremissasEconomicasData {
  return {
    status,
    snapshot_at: "2026-07-01T00:00:00Z",
    classes: [
      {
        classe_auvp: "renda_fixa",
        status: classStatus,
        retorno_real_esperado_pct_anual:
          classStatus === "emitted" ? "4.5" : null,
        sigma_anual_pct: null,
        fonte: null,
        fonte_origem: null,
        effective_from: null,
        justificativa: null,
        razao_indisponivel:
          classStatus === "indisponivel" ? "sem premissa" : null,
      },
    ],
  };
}

describe("IFMonteCarloBlock · premissas fallback (A28.l9)", () => {
  it("premissas parcial: Alert de ressalva acima do cone", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo(),
      premissas_economicas: makePremissasEconomicas("parcial", "indisponivel"),
    });
    render(<S7IndependenciaSection data={data} />);
    const alert = screen.getByTestId("s7-premissas-fallback-alert");
    expect(alert.textContent).toMatch(/premissas de mercado padrão/);
    expect(alert.textContent).toMatch(/referência, não como previsão/);
  });

  it("premissas completo: sem ressalva (cone renderiza limpo)", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo(),
      premissas_economicas: makePremissasEconomicas("completo", "emitted"),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByTestId("s7-premissas-fallback-alert"),
    ).not.toBeInTheDocument();
  });

  it("bloco de premissas ausente (run pré-ADR-219): sem ressalva", () => {
    const data = makeData({ if_monte_carlo: makeMonteCarlo() });
    render(<S7IndependenciaSection data={data} />);
    expect(
      screen.queryByTestId("s7-premissas-fallback-alert"),
    ).not.toBeInTheDocument();
  });

  // ADR-369 D2 — sem prazo declarado (Goal semeado, prazo vencido, ou artefato
  // de contrato anterior) a cláusula some. Publicar "0%" seria aritmeticamente
  // correto e inútil: afirmaria "nenhuma simulação atinge".
  it("prazo declarado ausente: omite a cláusula de probabilidade, mantém o cone", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo({
        prazo_declarado_anos: null,
        prob_if_ate_prazo_declarado: null,
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText(/Probabilidade de atingir IF/)).toBeNull();
    expect(screen.getByTestId("s7-if-cone-chart")).toBeInTheDocument();
  });

  // A data é da família: sem "que você declarou" o usuário lê o ano como nosso.
  it("prazo declarado presente: nomeia o dono da data e o ano-alvo", () => {
    const data = makeData({ if_monte_carlo: makeMonteCarlo() });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/15 anos que você declarou/)).toBeInTheDocument();
    expect(screen.getByText(/2041/)).toBeInTheDocument();
  });

  // Prazo além da janela: o número é PISO, não teto — truncar a janela só
  // remove sucessos. Rotular como teto seria o defeito que a lane mata.
  it("prazo truncado: declara que a probabilidade é um piso", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo({
        prazo_declarado_anos: 48,
        prazo_declarado_truncado: true,
        horizonte_simulado_anos: 40,
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText(/piso/)).toBeInTheDocument();
    expect(screen.queryByText(/teto/)).toBeNull();
  });

  it("motivo_sem_cone: role note + ícone, não só itálico (a11y A28.l9)", () => {
    const data = makeData({
      if_monte_carlo: makeMonteCarlo({
        exibir_cone: false,
        motivo_sem_cone: "Meta IF não configurada para este workspace.",
      }),
    });
    render(<S7IndependenciaSection data={data} />);
    const note = screen.getByRole("note", {
      name: "Motivo da ausência do cone de probabilidade",
    });
    expect(note.textContent).toMatch(/Meta IF não configurada/);
  });
});

/**
 * O bloco de 4 stats de IF era gateado por `goals &&` — a truthiness do
 * objeto inteiro. Como o E5 emite `goals` SEMPRE (dict, eventualmente só com
 * `alocacao_alvo`), um workspace sem meta de IF caía no ramo verdadeiro e
 * imprimia quatro placeholders vazios. O gate passa a olhar os campos que o
 * bloco de fato lê.
 */
describe("<S7IndependenciaSection /> · gate do bloco de stats de IF", () => {
  it("goals sem nenhum KPI de IF: bloco some em vez de imprimir 4 vazios", () => {
    const data = makeData({
      goals: { alocacao_alvo: { derived: { has_alvo: true } } },
    } as Partial<ReportAnalysisData>);
    render(<S7IndependenciaSection data={data} />);
    expect(screen.queryByText("Meta IF")).toBeNull();
    expect(screen.queryByText("Ano projetado")).toBeNull();
    // O placeholder que o gate quebrado produzia — "Progresso" com 0,0%.
    expect(screen.queryByText("Progresso")).toBeNull();
  });

  it("basta UM KPI presente para o bloco aparecer", () => {
    const data = makeData({
      goals: { if_pct: 30 },
    } as Partial<ReportAnalysisData>);
    render(<S7IndependenciaSection data={data} />);
    expect(screen.getByText("Meta IF")).toBeInTheDocument();
    expect(screen.getByText("Progresso")).toBeInTheDocument();
  });

  it("goals completo continua renderizando o bloco (não-regressão)", () => {
    render(<S7IndependenciaSection data={makeData()} />);
    expect(screen.getByText("Meta IF")).toBeInTheDocument();
    expect(screen.getByText("Gap")).toBeInTheDocument();
  });
});

/**
 * A40.l47 (RV4-13 · [[ADR-191]] §emenda 2026-08-14) — não existe yield-alvo no
 * produto. O único percentual que a família configura é `goals.trs_pct`, e ele é
 * taxa de **saque** (`goal.if.v2` §inputs; `if_meta = renda × 12 ÷ trs_pct`; wizard
 * passo 2). Compará-lo com o yield observado promove saque a meta de retorno — o
 * defeito que a A40.l4 mascarava ao imprimir a constante `5.0` no lugar.
 *
 * O gate é de **ausência na superfície**, não de valor: qualquer reintrodução de
 * meta neste card volta a montar a comparação.
 */
describe("<S7IndependenciaSection /> · sem alvo de retorno", () => {
  it("não imprime meta de yield, venha o payload de onde vier", () => {
    const comMeta = makeData({
      ratios: { rentabilidade: { meta_pct: 4.0 } },
    } as Partial<ReportAnalysisData>);
    for (const data of [makeData(), comMeta]) {
      const { unmount } = render(<S7IndependenciaSection data={data} />);
      expect(screen.queryByText(/Yield-alvo/i)).toBeNull();
      expect(screen.queryByText(/\bmeta\b.*%/i)).toBeNull();
      unmount();
    }
  });

  it("o valor observado continua visível — sustenta-se sem meta", () => {
    render(<S7IndependenciaSection data={makeData()} />);
    expect(screen.getByText("2.4%")).toBeInTheDocument();
  });

  // A copy do tooltip é asserida na constante, não no DOM: `TooltipContent`
  // só monta no open, então um assert por DOM passaria vazio (vacuoso).
  it("copy do tooltip não colapsa yield com taxa de retirada nem cita alvo", () => {
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/Trinity/i);
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/retirada sustentável/i);
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/\b4%/);
    expect(TRS_EFETIVA_TOOLTIP).not.toMatch(/alvo/i);
  });
});

/**
 * A40.l91 ([[ADR-418]] §D3) — o card de "Meta IF" publicava um número sem dizer qual
 * renda mensal ele sustenta nem de que base o gap e o progresso saíram. Auditar a base
 * exigia ler código-fonte, que é como o PV9-16 nasceu.
 */
describe("S7 — a Meta IF nomeia a base e o que ela financia", () => {
  it("nomeia a renda-alvo mensal que a meta sustenta", () => {
    const data = makeData({
      goals: {
        if_meta: 5_000_000,
        if_pct: 30,
        if_trs: 5,
        ano_if: 2040,
        if_gap: 4_000_000,
        if_trs_monthly_value: 20_833,
      },
    } as Partial<ReportAnalysisData>);

    render(<S7IndependenciaSection data={data} />);

    expect(
      screen.getByText(/financia .*\/mês — a renda-alvo declarada/),
    ).toBeInTheDocument();
  });

  it("declara o desconto quando a meta é líquida de renda fora da carteira", () => {
    const data = makeData({
      goals: {
        if_meta: 4_000_000,
        if_pct: 30,
        if_trs: 5,
        ano_if: 2040,
        if_gap: 3_000_000,
        if_trs_monthly_value: 20_833,
        if_meta_base: "renda_alvo_liquida_de_renda_externa",
        renda_passiva_fora_do_investivel_mensal_brl: 4_166,
      },
    } as Partial<ReportAnalysisData>);

    render(<S7IndependenciaSection data={data} />);

    expect(
      screen.getByText(/já descontados .*\/mês de bens fora desta carteira/),
    ).toBeInTheDocument();
  });

  it("não inventa desconto quando o termo é zero ou não foi medido", () => {
    const data = makeData({
      goals: {
        if_meta: 5_000_000,
        if_pct: 30,
        if_trs: 5,
        ano_if: 2040,
        if_gap: 4_000_000,
        if_trs_monthly_value: 20_833,
        renda_passiva_fora_do_investivel_mensal_brl: 0,
      },
    } as Partial<ReportAnalysisData>);

    render(<S7IndependenciaSection data={data} />);

    expect(screen.queryByText(/já descontados/)).not.toBeInTheDocument();
  });
});

/**
 * A40.l91 ([[ADR-418]] §D5) — `if_pct` é `null` quando a meta clampa em zero. O `?? 0`
 * anterior renderizava "0,0%": a afirmação oposta ao fato, e o mesmo modo de falha que a
 * ADR-412 §D7 já nomeava para o piso.
 */
describe("S7 — progresso ausente não vira 0,0%", () => {
  const semProgresso = {
    if_meta: 0,
    if_meta_bruta: 5_000_000,
    if_meta_base: "renda_externa_cobre_alvo",
    if_pct: null,
    if_gap: 0,
    if_trs: 5,
    ano_if: 2040,
  };

  it("renderiza traço, não zero", () => {
    render(
      <S7IndependenciaSection
        data={makeData({ goals: semProgresso } as Partial<ReportAnalysisData>)}
      />,
    );

    expect(screen.queryByText("0.0%")).not.toBeInTheDocument();
    expect(screen.queryByText("0,0%")).not.toBeInTheDocument();
  });

  it("nomeia por que o progresso não saiu", () => {
    render(
      <S7IndependenciaSection
        data={makeData({ goals: semProgresso } as Partial<ReportAnalysisData>)}
      />,
    );

    expect(
      screen.getByText(
        /renda de bens fora desta carteira já cobre a renda-alvo/,
      ),
    ).toBeInTheDocument();
  });

  it("não afirma fase de acumulação sem progresso apurado", () => {
    render(
      <S7IndependenciaSection
        data={makeData({ goals: semProgresso } as Partial<ReportAnalysisData>)}
      />,
    );

    expect(
      screen.queryByText(/Carteira em acumulação/),
    ).not.toBeInTheDocument();
  });
});
