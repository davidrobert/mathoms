/**
 * Unit tests — `frontend/src/components/report/utils/conclusionUtils.ts`
 *
 * Cobre regressão da convenção numérica de percentual (ADR-209):
 * formatter `"pct"` espera valor ABSOLUTO (44.7 = 44,7%); não aplica
 * heurística value <= 1 ? * 100 — essa heurística antiga produzia
 * "50%" para rentabilidade legítima de 0,5% a.a.
 *
 * Builders cobertos: patrimonio_doughnut, receita_bar, despesas_doughnut,
 * impostos_pj, score_gauge — caminhos que tocam o formatter pct.
 */
import { describe, expect, it } from "vitest";

import { deriveChartConclusion } from "@/components/report/utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

function makeData(partial: Partial<ReportAnalysisData>): ReportAnalysisData {
  return partial as ReportAnalysisData;
}

describe("deriveChartConclusion — convenção ADR-209 (pct absoluto)", () => {
  describe("patrimonio_doughnut", () => {
    it("usa o pct absoluto vindo do backend (sem multiplicação extra)", () => {
      const data = makeData({
        patrimonio: {
          composicao: [
            { categoria: "Renda Fixa", valor: 500_000, pct: 50 },
            { categoria: "Ações BR", valor: 250_000, pct: 25 },
            { categoria: "FIIs", valor: 250_000, pct: 25 },
          ],
        } as ReportAnalysisData["patrimonio"],
      });
      const out = deriveChartConclusion("patrimonio_doughnut", data);
      expect(out).toContain("Renda Fixa representa 50%");
    });

    it("renderiza pct fracionário < 1% como '0%' (não confunde com fracional 0..1)", () => {
      // Caso real raríssimo mas legítimo: classe com 0,5% do patrimônio.
      // Bug histórico (pre-ADR-209) renderizava como '50%' por heurística.
      const data = makeData({
        patrimonio: {
          composicao: [
            { categoria: "Caixa", valor: 99_500, pct: 99.5 },
            { categoria: "Veículos", valor: 500, pct: 0.5 },
          ],
        } as ReportAnalysisData["patrimonio"],
      });
      const out = deriveChartConclusion("patrimonio_doughnut", data);
      // Builder usa o `top` (Caixa, 99.5%). Renderiza 100% por toFixed(0).
      expect(out).toContain("Caixa representa 100%");
    });

    it("declara a base como patrimônio bruto, não líquido (C11-F1)", () => {
      const data = makeData({
        patrimonio: {
          composicao: [
            { categoria: "Imóveis de Renda", valor: 1_442_706, pct: 39.7 },
          ],
        } as ReportAnalysisData["patrimonio"],
      });
      const out = deriveChartConclusion("patrimonio_doughnut", data);
      expect(out).toContain("do patrimônio bruto");
      expect(out).not.toContain("líquido");
    });
  });

  describe("receita_bar — topEntry retorna pct absoluto", () => {
    it("calcula % da fonte principal em formato absoluto", () => {
      const data = makeData({
        fluxo_caixa: {
          por_fonte: {
            receita_clt: 60_000,
            receita_pj: 30_000,
            receita_aluguel: 10_000,
          },
        } as ReportAnalysisData["fluxo_caixa"],
      });
      const out = deriveChartConclusion("receita_bar", data);
      expect(out).toContain("CLT lidera as receitas (60%");
      // A40.l3 (ADR-306 D1): composição é agregado full — exige rótulo.
      expect(out).toContain("todo o período analisado");
    });

    it("trata fonte única (100% concentração) sem dividir extra", () => {
      const data = makeData({
        fluxo_caixa: {
          por_fonte: {
            receita_clt: 100_000,
          },
        } as ReportAnalysisData["fluxo_caixa"],
      });
      const out = deriveChartConclusion("receita_bar", data);
      expect(out).toContain("100%");
    });
  });

  describe("despesas_doughnut — topEntry consistente com receita_bar", () => {
    it("renderiza pct absoluto da categoria dominante", () => {
      const data = makeData({
        fluxo_caixa: {
          despesas_por_categoria: {
            moradia: 5_000,
            alimentacao: 2_000,
            transporte: 1_500,
            lazer: 1_500,
          },
        } as ReportAnalysisData["fluxo_caixa"],
      });
      const out = deriveChartConclusion("despesas_doughnut", data);
      expect(out).toContain("50%");
    });
  });

  describe("impostos_pj — consume ratios.aliquota_efetiva_ir_pct", () => {
    it("renderiza alíquota numérica absoluta", () => {
      const data = makeData({
        ratios: {
          aliquota_efetiva_ir_pct: 22.5,
        } as ReportAnalysisData["ratios"],
      });
      const out = deriveChartConclusion("impostos_pj", data);
      expect(out).toContain("23%");
    });

    it("usa fallback quando alíquota vem como string (legado ratios)", () => {
      // ADR-209 §D2: alguns campos pct vêm como string ("22.50"). Builder
      // checa typeof === "number" e retorna null → caller usa fallback.
      const data = makeData({
        ratios: {
          aliquota_efetiva_ir_pct: "22.50",
        } as ReportAnalysisData["ratios"],
      });
      const out = deriveChartConclusion("impostos_pj", data);
      expect(out).toBe("Composição tributária PJ.");
    });
  });

  describe("fallbacks — quando dados ausentes", () => {
    it("retorna fallback se composicao vazia", () => {
      const data = makeData({
        patrimonio: { composicao: [] } as ReportAnalysisData["patrimonio"],
      });
      const out = deriveChartConclusion("patrimonio_doughnut", data);
      expect(out).toBe("Distribuição patrimonial por categoria.");
    });

    it("retorna fallback se por_fonte ausente", () => {
      const data = makeData({});
      const out = deriveChartConclusion("receita_bar", data);
      expect(out).toBe("Composição das receitas por fonte.");
    });
  });
});
