import { describe, expect, it } from "vitest";

import {
  readMonteCarloData,
  readExcludedProperties,
  readPassiveIncome,
  readPremissasEconomicas,
  readProtecaoPatrimonial,
  readProventosRows,
  readRealEstateData,
  readScoreData,
} from "@/components/report/utils/reportContractGuards";

describe("reportContractGuards", () => {
  it("aceita score completo e recusa breakdown parcial", () => {
    const score = {
      valor: 7.5,
      max: 10,
      classificacao: "Bom",
      breakdown: [{ dimensao: "reserva", valor: 8, max: 10 }],
    };

    expect(readScoreData(score)).toBe(score);
    expect(
      readScoreData({ ...score, breakdown: [{ valor: 8 }] }),
    ).toBeUndefined();
  });

  it("aceita premissas completas e recusa classe parcial", () => {
    const premissas = {
      status: "completo",
      snapshot_at: "2026-08-14T00:00:00Z",
      classes: [
        {
          classe_auvp: "renda_fixa",
          status: "emitted",
          retorno_real_esperado_pct_anual: "4.00",
          sigma_anual_pct: "2.00",
          fonte: "curva",
          fonte_origem: "global",
          effective_from: "2026-08-01",
          justificativa: null,
          razao_indisponivel: null,
        },
      ],
    };

    expect(readPremissasEconomicas(premissas)).toBe(premissas);
    expect(
      readPremissasEconomicas({
        ...premissas,
        classes: [{ status: "emitted" }],
      }),
    ).toBeUndefined();
  });

  it("aceita proventos completos e recusa numerador ausente", () => {
    const rows = [
      {
        ticker: "TEST3",
        ano_base: 2025,
        total_proventos_brl: 100,
        ir_retido_brl: 10,
        renda_liquida_brl: 90,
        custo_total_brl: 1000,
        valor_mercado_brl: 1200,
        yield_on_cost_pct: 9,
        yield_on_market_pct: 7.5,
      },
    ];

    expect(readProventosRows(rows)).toBe(rows);
    expect(
      readProventosRows([{ ...rows[0], renda_liquida_brl: undefined }]),
    ).toBeUndefined();
  });

  it("aceita real estate completo e recusa rollup ausente", () => {
    const realEstate = {
      cap_rate_liquido_pct: null,
      cap_rate_bruto_pct: null,
      concentracao_pct: 0,
      valor_total_imoveis: 0,
      componentes_calculo: {},
      benchmarks: {
        cdi_liquido_pct: 9,
        ntnb_liquido_pct: 6,
        ifix_yield_pct: 8,
        as_of_date: "2026-08-14",
      },
      spreads_pp: { vs_cdi: 0, vs_ntnb: 0, vs_ifix: 0 },
      spread_brl_anual: { vs_cdi: 0, vs_ntnb: 0, vs_ifix: 0 },
      imoveis: [],
      excluded_properties: [],
      alertas: [],
    };

    expect(readRealEstateData(realEstate)).toBe(realEstate);
    expect(
      readRealEstateData({ ...realEstate, spreads_pp: undefined }),
    ).toBeUndefined();
  });

  it("preserva imóveis excluídos de um bloco histórico parcial", () => {
    const excluded = [
      {
        property_id: "property-1",
        descricao: "Imóvel sem classe",
        classification: "desconhecido",
        motivo: "classificacao_pendente",
      },
    ];

    expect(readExcludedProperties({ excluded_properties: excluded })).toBe(
      excluded,
    );
    expect(readExcludedProperties({ excluded_properties: [{}] })).toEqual([]);
  });

  it("aceita cone completo e recusa tupla de tamanho variável", () => {
    const monteCarlo = {
      sigma_usado: 0.15,
      exibir_cone: true,
      motivo_sem_cone: null,
      caminho_p10: [[2026, 100]],
      caminho_p50: [[2026, 120]],
      caminho_p90: [[2026, 140]],
    };

    expect(readMonteCarloData(monteCarlo)).toBe(monteCarlo);
    expect(
      readMonteCarloData({ ...monteCarlo, caminho_p10: [[2026, 100, 1]] }),
    ).toBeUndefined();
  });

  it("preserva empty state de renda passiva e recusa status ok parcial", () => {
    const semIrpf = { status: "sem_irpf" };

    expect(readPassiveIncome(semIrpf)).toBe(semIrpf);
    expect(
      readPassiveIncome({ status: "ok", patrimonio_gerador_brl: 100 }),
    ).toBeUndefined();
  });

  it("aceita proteção completa e recusa coleção parcial", () => {
    const protecao = {
      premio_total_anual_brl: "0.00",
      premio_decomposicao: {},
      pct_renda_anual: "0.000000",
      bens_com_gap_cobertura: [],
      gap_qualitativo: [],
      apolices_vigentes: [],
      apolices_vencendo: [],
      apolices_vencidas: [],
      corretoras_count: 0,
      seguradoras_count: 0,
    };

    expect(readProtecaoPatrimonial(protecao)).toBe(protecao);
    expect(
      readProtecaoPatrimonial({ ...protecao, apolices_vigentes: [{}] }),
    ).toBeUndefined();
  });
});
