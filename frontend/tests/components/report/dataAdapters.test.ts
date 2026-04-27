/**
 * ADR-117/122/123 · Fase 6 — testes dos adapters de dados.
 *
 * Cobre conclusionUtils, kanbanAdapter, timelineAdapter e priorityMap —
 * derivadores determinísticos frontend-side que alimentam os primitives
 * das Fases 3/4 até o E5 entregar os campos nativamente.
 */
import { describe, expect, it } from "vitest";

import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "@/components/report/utils/conclusionUtils";
import { adaptTarefasToKanban } from "@/components/report/utils/kanbanAdapter";
import { adaptProximos15dToTimeline } from "@/components/report/utils/timelineAdapter";
import { priorityFromEffort } from "@/components/report/utils/priorityMap";
import {
  deriveAporteSummary,
  deriveInvestimentosDelta,
} from "@/components/report/utils/aportesAdapter";
import type { ReportAnalysisData } from "@/lib/api";

// ─── conclusionUtils ────────────────────────────────────────────────

describe("deriveChartConclusion()", () => {
  it("patrimonio_doughnut interpola top categoria + pct + valor", () => {
    const data = {
      patrimonio: {
        composicao: [
          { categoria: "Imóveis", valor: 500_000, pct: 0.5 },
          { categoria: "Renda Fixa", valor: 300_000, pct: 0.3 },
        ],
      },
    } as unknown as ReportAnalysisData;
    // ICU usa NBSP em BRL — match com \s (cobre espaço normal e non-breaking).
    expect(deriveChartConclusion("patrimonio_doughnut", data)).toMatch(
      /^Imóveis representa 50% do patrimônio líquido \(R\$\s*500\.000\)\.$/,
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

  it("U2 é template simples sem interpolação", () => {
    expect(deriveSectionSummary("U2", {} as ReportAnalysisData)).toContain("Green Card");
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

// ─── kanbanAdapter ──────────────────────────────────────────────────

describe("adaptTarefasToKanban()", () => {
  it("mapeia essencial→prioridade e status→coluna", () => {
    const data = {
      tarefas: [
        { id: 1, titulo: "Rebalancear", essencial: "S", status: "a_fazer", prazo: "2026-05-01" },
        { id: 2, titulo: "IRPF", essencial: "R", status: "em_andamento" },
        { id: 3, titulo: "Revisar orçamento", essencial: "O", status: "feito" },
      ],
    } as unknown as ReportAnalysisData;
    const items = adaptTarefasToKanban(data);
    expect(items).toHaveLength(3);
    expect(items[0]).toMatchObject({ coluna: "a_fazer", prioridade: "alta", prazoIso: "2026-05-01" });
    expect(items[1]).toMatchObject({ coluna: "em_andamento", prioridade: "media" });
    expect(items[2]).toMatchObject({ coluna: "concluido", prioridade: "baixa" });
  });

  it("ignora entries sem titulo", () => {
    const data = { tarefas: [{ id: 1 }, { titulo: "OK" }] } as unknown as ReportAnalysisData;
    expect(adaptTarefasToKanban(data)).toHaveLength(1);
  });

  it("retorna [] quando data.tarefas ausente", () => {
    expect(adaptTarefasToKanban({} as ReportAnalysisData)).toEqual([]);
  });
});

// ─── timelineAdapter ────────────────────────────────────────────────

describe("adaptProximos15dToTimeline()", () => {
  it("normaliza shapes diferentes (data|date|data_iso + acao|action|descricao)", () => {
    const data = {
      proximos_15d: [
        { data: "2026-04-28", acao: "Fechar aporte", status: "pendente" },
        { date: "2026-05-02", action: "Revisar IRPF", status: "aguardando" },
        { data_iso: "2026-05-10", descricao: "Reunião consultor", status: "feito" },
      ],
    } as unknown as ReportAnalysisData;
    const items = adaptProximos15dToTimeline(data);
    expect(items).toHaveLength(3);
    expect(items[0]).toMatchObject({ status: "pendente" });
    expect(items[1]).toMatchObject({ status: "aguardando" });
    expect(items[2]).toMatchObject({ status: "feito" });
  });

  it("formata data para pt-BR (DD/MM)", () => {
    const data = {
      proximos_15d: [{ data: "2026-04-28", acao: "X" }],
    } as unknown as ReportAnalysisData;
    expect(adaptProximos15dToTimeline(data)[0].date).toBe("28/04");
  });

  it("busca em dashboard.proximos_15d também", () => {
    const data = {
      dashboard: { proximos_15d: [{ data: "2026-05-01", acao: "Y" }] },
    } as unknown as ReportAnalysisData;
    expect(adaptProximos15dToTimeline(data)).toHaveLength(1);
  });

  it("sem fonte retorna []", () => {
    expect(adaptProximos15dToTimeline({} as ReportAnalysisData)).toEqual([]);
  });
});

// ─── aportesAdapter (v2.4) ──────────────────────────────────────────

describe("deriveAporteSummary()", () => {
  it("agrega cards, totais e cobertura quando há aportes no dashboard", () => {
    const data = {
      dashboard: {
        aportes: {
          a0: { label: "CDB", feito: true, valor_meta: 10_000, valor_feito: 10_000 },
          a1: { label: "Tesouro", feito: false, valor_meta: 5_000 },
          a2: { label: "ETF", feito: true, valor_meta: 3_000, valor_feito: 2_500 },
        },
      },
    } as unknown as ReportAnalysisData;
    const summary = deriveAporteSummary(data);
    expect(summary).not.toBeNull();
    expect(summary!.destinos_total).toBe(3);
    expect(summary!.destinos_concluidos).toBe(2);
    expect(summary!.total_meta).toBe(18_000);
    // feito.a2 usa valor_feito=2500; pendente.a1 não soma
    expect(summary!.total_realizado).toBe(12_500);
    expect(summary!.cards.map((c) => c.id)).toEqual(["a0", "a1", "a2"]);
  });

  it("retorna null quando dashboard.aportes está vazio ou ausente", () => {
    expect(deriveAporteSummary({} as ReportAnalysisData)).toBeNull();
    expect(
      deriveAporteSummary({ dashboard: { aportes: {} } } as unknown as ReportAnalysisData),
    ).toBeNull();
  });

  it("usa valor_meta como fallback quando feito=true sem valor_feito", () => {
    const data = {
      dashboard: {
        aportes: {
          k: { label: "X", feito: true, valor_meta: 4_000 },
        },
      },
    } as unknown as ReportAnalysisData;
    const summary = deriveAporteSummary(data);
    expect(summary!.total_realizado).toBe(4_000);
    expect(summary!.cards[0].valor_efetivo).toBe(4_000);
  });
});

describe("deriveInvestimentosDelta()", () => {
  it("calcula delta = atual - anterior por bloco", () => {
    const data = {
      dashboard: {
        investimentos_delta: {
          d: { label: "Investimentos David", anterior: 100_000, atual: 110_000 },
          m: { label: "Investimentos Mariana", anterior: 50_000, atual: 48_000 },
        },
      },
    } as unknown as ReportAnalysisData;
    const rows = deriveInvestimentosDelta(data);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ id: "d", delta: 10_000 });
    expect(rows[1]).toMatchObject({ id: "m", delta: -2_000 });
  });

  it("retorna [] quando dashboard ausente", () => {
    expect(deriveInvestimentosDelta({} as ReportAnalysisData)).toEqual([]);
  });
});
