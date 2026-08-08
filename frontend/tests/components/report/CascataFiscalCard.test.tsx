/**
 * Sprint A16 L2 P5 (ADR-236 §D5) — Unit tests do `<CascataFiscalCard/>`.
 *
 * Pattern espelha `PrevidenciaPgblCard.test.tsx` — asserções pontuais
 * sobre estado renderizado, copy literal e a11y do callout.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CascataFiscalCard } from "@/components/report/cards/CascataFiscalCard";
import type {
  CascataPayload,
  CascataTrigger,
  TributarioBundle,
} from "@/lib/api";

function buildCascata(overrides: Partial<CascataPayload> = {}): CascataPayload {
  return {
    regime: "simples",
    regime_label: "Simples Nacional — Anexo III",
    regime_nao_suportado: false,
    motivo_nao_suportado: null,
    receita_bruta: 600000,
    tributos_federais: 60000,
    iss_total: 0,
    lucro_contabil_pj: 480000,
    pro_labore_bruto: 36000,
    inss_patronal: 0,
    inss_empregado: 3960,
    irrf_pro_labore: 2500,
    lucros_distribuidos: 420000,
    renda_pf_tributavel_total: 36000,
    carga_total_pct: 0.137,
    pgbl_base_anual: 36000,
    pgbl_limite_anual: 4320,
    pgbl_aplicavel: true,
    pgbl_motivo_inaplicavel: null,
    fator_r_pct: 0.32,
    fator_r_faixa: "anexo_iii",
    fator_r_break_even_mensal: null,
    triggers: [],
    ...overrides,
  };
}

function buildBundle(overrides: Partial<TributarioBundle> = {}): TributarioBundle {
  return {
    regime: "simples",
    regime_label: "Simples Nacional — Anexo III",
    cascata: buildCascata(),
    contador_nome: null,
    holding_prazo_meses: null,
    _source: "test",
    ...overrides,
  };
}

describe("<CascataFiscalCard /> · Simples Anexo III", () => {
  it("renderiza header + regime_label + badge fator-R", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(
      screen.getAllByText(/Tributário PJ · Cascata Fiscal/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText(/Simples Nacional — Anexo III/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Fator-R 32,0% · Anexo III/i)).toBeInTheDocument();
  });

  // Controle dos dois variantes do badge: o texto tem de sair no par
  // `-on-tint`, não na cor base. `cascataFiscalContrast.test.ts` prova que a
  // base reprova AA (4,09:1 no gain, 1,86:1 no alert); aqui provamos que o
  // componente consome o token corrigido — inclusive no branch `anexo_v`, que
  // nenhuma fixture E2E alcança (`medium.json` fixa `anexo_iii`).
  it.each([
    { faixa: "anexo_iii" as const, texto: "Fator-R 32,0% · Anexo III", token: "--semantic-gain-on-tint" },
    { faixa: "anexo_v" as const, texto: "Fator-R 32,0% · Anexo V", token: "--semantic-alert-on-tint" },
  ])("badge $faixa usa o token de texto legível sobre tint", ({ faixa, texto, token }) => {
    render(
      <CascataFiscalCard
        tributario={buildBundle({ cascata: buildCascata({ fator_r_faixa: faixa }) })}
      />,
    );
    expect(screen.getByText(texto).className).toContain(`text-[var(${token})]`);
  });

  it("renderiza camadas da cascata com label DAS Simples Nacional", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.getByText(/Receita bruta PJ \(12m\)/i)).toBeInTheDocument();
    expect(screen.getByText(/− DAS Simples Nacional/i)).toBeInTheDocument();
    expect(screen.getByText(/= Lucro contábil PJ/i)).toBeInTheDocument();
    expect(screen.getByText(/= Lucros distribuídos \(isentos\)/i)).toBeInTheDocument();
  });

  it("renderiza linha de carga tributária total em destaque", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.getByText(/Carga tributária total/i)).toBeInTheDocument();
    expect(screen.getByText(/13,7%/)).toBeInTheDocument();
  });

  it("omite linha ISS quando Simples (iss_total=0)", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.queryByText(/− ISS destacado/i)).not.toBeInTheDocument();
  });

  it("omite INSS patronal quando regime=simples (embutido no DAS)", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.queryByText(/− INSS patronal/i)).not.toBeInTheDocument();
  });

  it("renderiza bloco PGBL com valores e disclaimer sobre lucros isentos", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.getByText(/Base para dedução PGBL/i)).toBeInTheDocument();
    expect(screen.getByText(/Renda tributável PF\/ano/i)).toBeInTheDocument();
    expect(screen.getByText(/Limite PGBL \(12%\)/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Lucros distribuídos\s+não entram na base PGBL/i),
    ).toBeInTheDocument();
  });

  it("renderiza disclaimer fiduciário e protection sentence", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(
      screen.getByText(/não recomenda mudança/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Confirme com seu contador antes de qualquer decisão tributária/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Base: receita bruta 12 meses móveis/i),
    ).toBeInTheDocument();
  });

  // A40.l4 (ADR-319): o disclaimer sinaliza QUE existe contador, nunca QUEM —
  // nome de terceiro é PII e o relatório circula fora da família.
  it("sinaliza contador cadastrado sem publicar o nome", () => {
    render(
      <CascataFiscalCard
        tributario={buildBundle({ contador_nome: "Contábil ABC" })}
      />,
    );
    expect(
      screen.getByText(/Há contador cadastrado no perfil da PJ\./i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Contábil ABC/)).not.toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · Lucro Presumido", () => {
  it("renderiza tributos PIS+COFINS+IRPJ+CSLL + ISS + INSS patronal", () => {
    const cascata = buildCascata({
      regime: "lucro_presumido",
      regime_label: "Lucro Presumido",
      tributos_federais: 90000,
      iss_total: 30000,
      inss_patronal: 14400,
      fator_r_pct: null,
      fator_r_faixa: null,
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({
          regime: "lucro_presumido",
          regime_label: "Lucro Presumido",
          cascata,
        })}
      />,
    );
    expect(screen.getByText(/PIS \+ COFINS \+ IRPJ \+ CSLL/i)).toBeInTheDocument();
    expect(screen.getByText(/− ISS destacado/i)).toBeInTheDocument();
    expect(screen.getByText(/− INSS patronal \(20%\)/i)).toBeInTheDocument();
  });

  it("não renderiza badge fator-R em Presumido", () => {
    const cascata = buildCascata({
      regime: "lucro_presumido",
      regime_label: "Lucro Presumido",
      fator_r_pct: null,
      fator_r_faixa: null,
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({
          regime: "lucro_presumido",
          regime_label: "Lucro Presumido",
          cascata,
        })}
      />,
    );
    // Badge tem padrão "Fator-R NN,N% · Anexo X" — match no "% · Anexo".
    expect(screen.queryByText(/Fator-R [\d,]+% · Anexo/i)).not.toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · MEI", () => {
  it("renderiza DAS-MEI com valor fixo no label", () => {
    const cascata = buildCascata({
      regime: "mei",
      regime_label: "MEI",
      receita_bruta: 81000,
      tributos_federais: 959,
      fator_r_pct: null,
      fator_r_faixa: null,
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({ regime: "mei", regime_label: "MEI", cascata })}
      />,
    );
    expect(screen.getByText(/DAS-MEI \(R\$ 79,90\/mês\)/i)).toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · PGBL inaplicável", () => {
  it("renderiza flag amarela quando declaracao_simplificada", () => {
    const cascata = buildCascata({
      pgbl_aplicavel: false,
      pgbl_motivo_inaplicavel: "declaracao_simplificada",
    });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/PGBL não dedutível.*desconto simplificado/i),
    ).toBeInTheDocument();
  });

  it("renderiza estado neutro quando renda_tributavel_pf_zerada", () => {
    const cascata = buildCascata({
      pgbl_aplicavel: false,
      pgbl_motivo_inaplicavel: "renda_tributavel_pf_zerada",
      pgbl_base_anual: 0,
      pgbl_limite_anual: 0,
    });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/processar o IRPF mais recente libera o cálculo/i),
    ).toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · Decision triggers", () => {
  function buildTrigger(overrides: Partial<CascataTrigger>): CascataTrigger {
    return {
      code: "T1",
      severity: "considere",
      title: "default",
      params: {},
      ...overrides,
    };
  }

  it("renderiza T1 com copy CRC 'Trade-off observado' (não 'Considere avaliar')", () => {
    const trigger = buildTrigger({
      code: "T1",
      severity: "considere",
      title: "old title",
      params: {
        delta_pro_labore_mensal_brl: "5000",
        aporte_pgbl_extra_anual_brl: "7200",
        economia_ir_anual_brl: "1980",
        custo_inss_patronal_anual_brl: "0",
        ir_marginal_potencial_pct: "27.50",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/Trade-off observado: pró-labore × lucros distribuídos/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Trade-off favorável enquanto a alíquota marginal IR > 15%/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no Simples a contribuição patronal está embutida no DAS/i),
    ).toBeInTheDocument();
  });

  it("renderiza T2 com copy descritiva sem '9,5pp' hardcoded", () => {
    const trigger = buildTrigger({
      code: "T2",
      severity: "atencao",
      title: "old",
      params: {
        fator_r_pct: "27.50",
        fator_r_limiar_pct: "28.00",
        delta_folha_mensal_brl: "1200",
        delta_folha_anual_brl: "14400",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/Sinal de atenção: fator-R próximo do corte Anexo III × V/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Anexo V tem alíquotas mais altas em todas as faixas/i),
    ).toBeInTheDocument();
  });

  it("renderiza T3 com '10 anos de cada aporte' (não 'no fundo')", () => {
    const trigger = buildTrigger({
      code: "T3",
      severity: "oportunidade",
      title: "old",
      params: {
        ir_marginal_estimado_pct: "27.50",
        pgbl_limite_anual_brl: "4320",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/Oportunidade: PGBL dedutível dentro do seu perfil/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/tabela regressiva \(10% após 10 anos de cada aporte\)/i),
    ).toBeInTheDocument();
  });

  it("renderiza T4 com 'Cenário observado' (não 'Considere holding')", () => {
    const trigger = buildTrigger({
      code: "T4",
      severity: "considere",
      title: "old",
      params: {
        imoveis_alugados_count: "4",
        receita_aluguel_anual_brl: "180000",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/Cenário observado: imóveis locados em pessoa física/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/avalie com tributarista antes de qualquer movimento/i),
    ).toBeInTheDocument();
  });

  it("renderiza T5 com copy descritiva e callout amarelo", () => {
    const trigger = buildTrigger({
      code: "T5",
      severity: "atencao",
      title: "old",
      params: {
        receita_anual_brl: "3000000",
        distancia_brl: "600000",
        sublimite_brl: "3600000",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    render(<CascataFiscalCard tributario={buildBundle({ cascata })} />);
    expect(
      screen.getByText(/Sinal de atenção: receita próxima do sublimite Simples/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Avalie com seu contador o impacto de desenquadramento/i),
    ).toBeInTheDocument();
  });

  it("aria-label do callout inclui severity verbal (não só cor)", () => {
    const trigger = buildTrigger({
      code: "T3",
      severity: "oportunidade",
      title: "old",
      params: {
        ir_marginal_estimado_pct: "27.50",
        pgbl_limite_anual_brl: "4320",
      },
    });
    const cascata = buildCascata({ triggers: [trigger] });
    const { container } = render(
      <CascataFiscalCard tributario={buildBundle({ cascata })} />,
    );
    const callout = container.querySelector('[aria-label*="oportunidade"]');
    expect(callout).toBeTruthy();
  });

  it("oculta seção 'Pontos de atenção' quando triggers=[]", () => {
    render(<CascataFiscalCard tributario={buildBundle()} />);
    expect(screen.queryByText(/Pontos de atenção/i)).not.toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · Empty states", () => {
  it("estado 'perfil pendente' quando tributario undefined", () => {
    render(<CascataFiscalCard tributario={undefined} />);
    expect(screen.getByText(/Perfil tributário PJ incompleto/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Solicite ao seu consultor a complementação do perfil/i),
    ).toBeInTheDocument();
  });

  it("estado 'perfil pendente' quando motivo_nao_suportado=perfil_incompleto", () => {
    const cascata = buildCascata({
      regime: null,
      regime_label: "Perfil tributário incompleto",
      regime_nao_suportado: true,
      motivo_nao_suportado: "perfil_incompleto",
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({ regime: null, regime_label: "Perfil tributário incompleto", cascata })}
      />,
    );
    expect(screen.getByText(/Perfil tributário PJ incompleto/i)).toBeInTheDocument();
  });

  it("estado 'Lucro Real' quando motivo_nao_suportado=lucro_real", () => {
    const cascata = buildCascata({
      regime: "lucro_real",
      regime_label: "Lucro Real",
      regime_nao_suportado: true,
      motivo_nao_suportado: "lucro_real",
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({
          regime: "lucro_real",
          regime_label: "Lucro Real",
          cascata,
        })}
      />,
    );
    expect(
      screen.getByText(/Regime Lucro Real — cascata em desenvolvimento \(V2\)/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/escrituração contábil completa/i),
    ).toBeInTheDocument();
  });

  it("estado 'anexo pendente' quando motivo_nao_suportado=anexo_simples_pendente", () => {
    const cascata = buildCascata({
      regime: "simples",
      regime_label: "Simples Nacional",
      regime_nao_suportado: true,
      motivo_nao_suportado: "anexo_simples_pendente",
    });
    render(
      <CascataFiscalCard
        tributario={buildBundle({
          regime: "simples",
          regime_label: "Simples Nacional",
          cascata,
        })}
      />,
    );
    expect(screen.getByText(/Anexo Simples pendente/i)).toBeInTheDocument();
  });
});

describe("<CascataFiscalCard /> · gate anti-folclore", () => {
  it("NÃO contém 'Lucro presumido (32%)' em workspace Simples (ADR-236 N3)", () => {
    const { container } = render(
      <CascataFiscalCard tributario={buildBundle()} />,
    );
    expect(container.textContent).not.toMatch(/Lucro presumido \(32%\)/);
  });

  it("NÃO contém 'receita PJ × 32%' (confusão base PGBL)", () => {
    const { container } = render(
      <CascataFiscalCard tributario={buildBundle()} />,
    );
    expect(container.textContent).not.toMatch(/receita PJ × 32%/);
    expect(container.textContent).not.toMatch(/receita_pj.*x.*32/i);
  });

  it("NÃO contém prescrição 'Recomendamos' ou 'Você deve'", () => {
    const cascata = buildCascata({
      triggers: [
        {
          code: "T1",
          severity: "considere",
          title: "old",
          params: {
            delta_pro_labore_mensal_brl: "5000",
            aporte_pgbl_extra_anual_brl: "7200",
            economia_ir_anual_brl: "1980",
            custo_inss_patronal_anual_brl: "0",
            ir_marginal_potencial_pct: "27.50",
          },
        },
        {
          code: "T4",
          severity: "considere",
          title: "old",
          params: {
            imoveis_alugados_count: "4",
            receita_aluguel_anual_brl: "180000",
          },
        },
      ],
    });
    const { container } = render(
      <CascataFiscalCard tributario={buildBundle({ cascata })} />,
    );
    expect(container.textContent).not.toMatch(/Recomendamos/i);
    expect(container.textContent).not.toMatch(/Você deve/i);
    expect(container.textContent).not.toMatch(/O melhor regime/i);
  });
});
