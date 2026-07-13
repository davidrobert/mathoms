/**
 * ADR-117/122 · Fase 6 — testes dos adapters de dados.
 *
 * Cobre conclusionUtils e priorityMap — derivadores determinísticos
 * frontend-side que alimentam os primitives das Fases 3/4 até o E5
 * entregar os campos nativamente.
 */
import { describe, expect, it } from "vitest";

import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "@/components/report/utils/conclusionUtils";
import { priorityFromEffort } from "@/components/report/utils/priorityMap";
import type { ReportAnalysisData } from "@/lib/api";

// ─── conclusionUtils ────────────────────────────────────────────────

describe("deriveChartConclusion()", () => {
  it("patrimonio_doughnut interpola top categoria + pct absoluto + valor", () => {
    // ADR-209: composicao[].pct é absoluto (50.0 = 50%, não 0.5).
    // Fixture pré-ADR-209 usava 0.5 e a heurística value <= 1 ? * 100 escondia
    // o bug. Removida a heurística, o fixture é alinhado ao contrato real do
    // backend (patrimonio_calculator._apply_percentuals_largest_remainder).
    const data = {
      patrimonio: {
        composicao: [
          { categoria: "Imóveis", valor: 500_000, pct: 50.0 },
          { categoria: "Renda Fixa", valor: 300_000, pct: 30.0 },
        ],
      },
    } as unknown as ReportAnalysisData;
    // ICU usa NBSP em BRL — match com \s (cobre espaço normal e non-breaking).
    expect(deriveChartConclusion("patrimonio_doughnut", data)).toMatch(
      /^Imóveis representa 50% do patrimônio bruto \(R\$\s*500\.000\)\.$/,
    );
  });

  it("patrimonio_doughnut cai em fallback quando composicao vazia", () => {
    const data = { patrimonio: {} } as ReportAnalysisData;
    expect(deriveChartConclusion("patrimonio_doughnut", data)).toBe(
      "Distribuição patrimonial por categoria.",
    );
  });

  it("score_gauge monta texto com valor + classe", () => {
    const data = {
      score: { valor: 7.8, max: 10, classificacao: "Bom" },
    } as ReportAnalysisData;
    expect(deriveChartConclusion("score_gauge", data)).toBe("Score atual: 7,8 / 10 (Bom).");
  });

  it("fluxo_mensal calcula fluxo líquido (receita - despesa)", () => {
    const data = {
      fluxo_caixa: {
        receita_recorrente_mensal: 25_000,
        despesa_mensal_media: 18_000,
      },
    } as unknown as ReportAnalysisData;
    const text = deriveChartConclusion("fluxo_mensal", data);
    expect(text).toMatch(/R\$\s*25\.000/);
    expect(text).toMatch(/R\$\s*18\.000/);
    expect(text).toMatch(/R\$\s*7\.000/); // líquido
  });

  it("receita_bar identifica top fonte e formata pt-BR", () => {
    const data = {
      fluxo_caixa: { por_fonte: { receita_clt: 10_000, receita_pj: 25_000, outras_receitas: 1_000 } },
    } as unknown as ReportAnalysisData;
    expect(deriveChartConclusion("receita_bar", data)).toBe(
      "PJ lidera as receitas (69%).",
    );
  });

  it("chart desconhecido retorna null", () => {
    expect(deriveChartConclusion("chart_que_nao_existe", {} as ReportAnalysisData)).toBeNull();
  });
});

describe("deriveSectionSummary()", () => {
  it("S1 usa patrimonio.liquido quando presente", () => {
    const data = { patrimonio: { liquido: 1_200_000 } } as unknown as ReportAnalysisData;
    expect(deriveSectionSummary("S1", data)).toMatch(/R\$\s*1\.200\.000/);
  });

  it("S10 inclui score + classificacao", () => {
    const data = { score: { valor: 8.2, max: 10, classificacao: "Excelente" } } as ReportAnalysisData;
    expect(deriveSectionSummary("S10", data)).toContain("8,2");
    expect(deriveSectionSummary("S10", data)).toContain("Excelente");
  });

  it("APP_C é template simples sem interpolação", () => {
    expect(deriveSectionSummary("APP_C", {} as ReportAnalysisData)).toContain("estresse");
  });

  it("Seção desconhecida retorna null", () => {
    expect(deriveSectionSummary("SXX", {} as ReportAnalysisData)).toBeNull();
  });

  // v2.9 · ADR-144 — prefer-snapshot LLM section summaries
  it("usa snapshot.section_summaries[id] quando presente (LLM)", () => {
    const data = {
      patrimonio: { liquido: 1_200_000 },
      section_summaries: {
        S1: "Resumo gerado por LLM com contexto narrativo.",
      },
    } as unknown as ReportAnalysisData;
    expect(deriveSectionSummary("S1", data)).toBe(
      "Resumo gerado por LLM com contexto narrativo.",
    );
  });

  it("cai no template determinístico se snapshot.section_summaries[id] está ausente", () => {
    const data = {
      patrimonio: { liquido: 1_200_000 },
      section_summaries: { S2: "outro id" },
    } as unknown as ReportAnalysisData;
    expect(deriveSectionSummary("S1", data)).toMatch(/R\$\s*1\.200\.000/);
  });

  it("strings vazias/whitespace no LLM caem para template", () => {
    const data = {
      patrimonio: { liquido: 1_200_000 },
      section_summaries: { S1: "   " },
    } as unknown as ReportAnalysisData;
    expect(deriveSectionSummary("S1", data)).toMatch(/R\$\s*1\.200\.000/);
  });
});

// ─── priorityMap ────────────────────────────────────────────────────

describe("priorityFromEffort()", () => {
  it("S → alta, R → media, O → baixa", () => {
    expect(priorityFromEffort("S")).toBe("alta");
    expect(priorityFromEffort("R")).toBe("media");
    expect(priorityFromEffort("O")).toBe("baixa");
  });
  it("case-insensitive", () => {
    expect(priorityFromEffort("s")).toBe("alta");
  });
  it("inválido/undefined → undefined", () => {
    expect(priorityFromEffort("X")).toBeUndefined();
    expect(priorityFromEffort(undefined)).toBeUndefined();
  });
});

// ─── aportesAdapter ─────────────────────────────────────────────────
// ADR-151 (Direção E): aportesAdapter removido junto com Tático T2.
// Lógica de aportes agora vive em /plano (SupportGoalsRow) e /dashboard.
//
// PR2 (pós ADR-151/154): kanbanAdapter e timelineAdapter removidos junto
// com primitivos órfãos Kanban/Timeline/Notas* (consumidor único era
// `_dev/ui/UiDevPlayground.tsx`).
