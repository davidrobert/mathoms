/**
 * A28.l9 — specs da derivação pura de sinais de qualidade de dados.
 *
 * Cobre: normalização da chave nao_identificado (raw vs title-cased do
 * wire), share por agregado vs datasets, degrade de premissas (parcial/
 * indisponível/ausente), imóveis pendentes e o agregador com threshold.
 */
import { describe, expect, it } from "vitest";

import {
  computeDataQualitySignals,
  computeNaoIdentificadoShare,
  computePremissasDegrade,
  isNaoIdentificadoKey,
  pendingClassificationProperties,
} from "@/components/report/utils/dataQualitySignals";
import type { PremissasEconomicasData, ReportAnalysisData } from "@/lib/api";
import type { RealEstateData } from "@/types/report-analysis";

describe("isNaoIdentificadoKey", () => {
  it("aceita grafias do wire: raw, title-cased e acentuada", () => {
    expect(isNaoIdentificadoKey("nao_identificado")).toBe(true);
    expect(isNaoIdentificadoKey("Nao Identificado")).toBe(true);
    expect(isNaoIdentificadoKey("Não identificado")).toBe(true);
  });

  it("rejeita categorias reais", () => {
    expect(isNaoIdentificadoKey("moradia")).toBe(false);
    expect(isNaoIdentificadoKey("Identificado")).toBe(false);
  });
});

describe("computeNaoIdentificadoShare", () => {
  it("prefere o agregado despesas_por_categoria", () => {
    const share = computeNaoIdentificadoShare({
      despesas_por_categoria: { moradia: 700, nao_identificado: 300 },
    });
    expect(share).toEqual({ valor: 300, pct: 30 });
  });

  it("cai nos datasets (labels title-cased) quando agregado ausente", () => {
    const share = computeNaoIdentificadoShare({
      receita_despesa_mensal_detalhado: {
        despesa_datasets: [
          { label: "Moradia", data: [400, 400] },
          { label: "Nao Identificado", data: [100, 100] },
        ],
      },
    });
    expect(share).toEqual({ valor: 200, pct: 20 });
  });

  it("retorna null sem dado de despesa por categoria", () => {
    expect(computeNaoIdentificadoShare(undefined)).toBeNull();
    expect(computeNaoIdentificadoShare({})).toBeNull();
  });
});

function makePremissas(
  overrides: Partial<PremissasEconomicasData> = {},
): PremissasEconomicasData {
  const classe = (status: "emitted" | "indisponivel") => ({
    classe_auvp: "renda_fixa",
    status,
    retorno_real_esperado_pct_anual: status === "emitted" ? "4.5" : null,
    sigma_anual_pct: null,
    fonte: null,
    fonte_origem: null,
    effective_from: null,
    justificativa: null,
    razao_indisponivel: status === "indisponivel" ? "sem premissa vigente" : null,
  });
  return {
    status: "parcial",
    snapshot_at: "2026-07-01T00:00:00Z",
    classes: [classe("indisponivel"), classe("emitted")],
    ...overrides,
  };
}

describe("computePremissasDegrade", () => {
  it("bloco ausente (run pré-ADR-219) não dispara sinal", () => {
    expect(computePremissasDegrade(undefined)).toBeNull();
  });

  it("status completo sem classes indisponíveis não dispara", () => {
    const p = makePremissas({ status: "completo" });
    p.classes[0].status = "emitted";
    expect(computePremissasDegrade(p)).toBeNull();
  });

  it("parcial: parte das classes indisponíveis", () => {
    expect(computePremissasDegrade(makePremissas())).toEqual({
      status: "parcial",
      classesIndisponiveis: 1,
      classesTotal: 2,
    });
  });

  it("indisponível: todas as classes em fallback (dogfood 10/10)", () => {
    const p = makePremissas();
    p.classes[1].status = "indisponivel";
    expect(computePremissasDegrade(p)?.status).toBe("indisponivel");
  });
});

function makeRealEstate(
  excluded: ReadonlyArray<{ classification: string }>,
): RealEstateData {
  return {
    excluded_properties: excluded.map((e, i) => ({
      property_id: `p${i}`,
      descricao: `Imóvel ${i}`,
      classification: e.classification,
      motivo: "…",
    })),
  } as unknown as RealEstateData;
}

describe("pendingClassificationProperties", () => {
  it("filtra apenas classification desconhecido", () => {
    const re = makeRealEstate([
      { classification: "desconhecido" },
      { classification: "residencia_principal" },
      { classification: "desconhecido" },
    ]);
    expect(pendingClassificationProperties(re)).toHaveLength(2);
  });

  it("tolera real_estate ausente", () => {
    expect(pendingClassificationProperties(undefined)).toHaveLength(0);
    expect(pendingClassificationProperties(null)).toHaveLength(0);
  });
});

describe("computeDataQualitySignals", () => {
  it("count 0 em relatório limpo (banner colapsa)", () => {
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    expect(computeDataQualitySignals(data, 0).count).toBe(0);
  });

  it("nao_identificado só entra acima do threshold de 10%", () => {
    const at9: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 910, nao_identificado: 90 } },
    };
    expect(computeDataQualitySignals(at9, 0).naoIdentificado).toBeNull();

    const at23: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 770, nao_identificado: 230 } },
    };
    const signals = computeDataQualitySignals(at23, 0);
    expect(signals.naoIdentificado?.pct).toBeCloseTo(23);
    expect(signals.count).toBe(1);
  });

  it("dogfood degradado: 4 sinais ativos", () => {
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 770, nao_identificado: 230 } },
      premissas_economicas: makePremissas(),
      real_estate: makeRealEstate([{ classification: "desconhecido" }]),
    };
    const signals = computeDataQualitySignals(data, 13);
    expect(signals.count).toBe(4);
    expect(signals.needsReviewDocs).toBe(13);
    expect(signals.imoveisPendentes).toBe(1);
    expect(signals.premissas?.status).toBe("parcial");
  });
});
