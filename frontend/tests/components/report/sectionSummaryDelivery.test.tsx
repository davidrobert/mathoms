/**
 * ENTREGA das narrativas de seção — lado TS do par (A40.l4 · ADR-355).
 *
 * Lê a MESMA fixture que `tests/test_e5n_delivery_contract.py`
 * (`tests/fixtures/narrativas/e5n_delivery.json`, gerada pelo produtor) e
 * assere no DOM a string EXATA de cada destino declarado no layout. O
 * sentinela é a própria copy do produtor: fixture inventada à mão poderia
 * descrever um mundo que o produtor não emite (lição da A40.l3).
 *
 * Render via `<MigratedSection>` — não a seção direto — porque o dispatcher é
 * onde a alcançabilidade se prova. Contagem computada do layout, nunca
 * hardcoded: o KR-C sai do dado declarativo.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/WorkspaceProvider", () => ({
  useWorkspace: () => ({ workspace: { id: "ws-1" }, workspaces: [], loading: false }),
}));

import { MigratedSection } from "@/components/report/MigratedSection";
import { LAYOUT } from "@/generated/report-layout";
import { LAYOUT_SUMMARY_SOURCE } from "@/components/report/utils/sectionSummarySource";
import type { ReportAnalysisData } from "@/lib/api";

interface NarrativasFixture {
  readonly summaries: Record<string, string>;
  readonly charts: Record<string, { context: string; conclusion: string }>;
  readonly perfil_familia: { left: string; right: string };
}

const FIXTURE: NarrativasFixture = JSON.parse(
  readFileSync(
    path.resolve(__dirname, "../../../../tests/fixtures/narrativas/e5n_delivery.json"),
    "utf8",
  ),
);

/** `real_estate` real (copiado de uma fixture E2E) — a S4 é hide-when-empty. */
const REAL_ESTATE = {
  cap_rate_liquido_pct: 0.9,
  cap_rate_bruto_pct: 1.1,
  componentes_calculo: {
    aluguel_anual_bruto: { valor: 8400, origem: "irpf", confidence: "low" },
  },
  benchmarks: {
    cdi_liquido_pct: 8.99,
    ntnb_liquido_pct: 5.52,
    ifix_yield_pct: 9.2,
    as_of_date: "2026-04-30",
  },
  spreads_pp: { vs_cdi: -8.09, vs_ntnb: -4.62, vs_ifix: -8.3 },
  spread_brl_anual: { vs_cdi: -64720, vs_ntnb: -36960, vs_ifix: -66400 },
  concentracao_pct: 100,
  valor_total_imoveis: 800000,
  imoveis: [
    {
      property_id: "sp-1",
      descricao: "Kitnet",
      classification: "locado",
      valor_imovel: 800000,
      valor_imovel_origem: "irpf",
      aluguel_mensal_bruto: 700,
      ir_retido_mensal: 0,
      status_contrato: "desconhecido",
      origem_aluguel: "irpf",
    },
  ],
  excluded_properties: [],
  alertas: [],
};

function buildData(overrides: Partial<Record<string, unknown>> = {}): ReportAnalysisData {
  return {
    narrativas: FIXTURE,
    patrimonio: { liquido: 1_200_000, composicao: [] },
    fluxo_caixa: { receita_recorrente_mensal: 30_000, despesa_mensal_media: 20_000 },
    score: { valor: 8.2, max: 10, classificacao: "Excelente" },
    real_estate: REAL_ESTATE,
    ...overrides,
  } as unknown as ReportAnalysisData;
}

function renderSection(sectionId: string, data: ReportAnalysisData) {
  return render(
    <MigratedSection
      sectionId={sectionId}
      data={data}
      workspaceId="ws-1"
      reportId="r-1"
    />,
  );
}

/** Destinos declarados no layout (seções + apêndices, só `enabled`). */
const DESTINOS = Object.entries(LAYOUT_SUMMARY_SOURCE);

describe("entrega de narrativa de seção (ADR-355)", () => {
  it("o layout declara os mesmos destinos que o resolver consome", () => {
    const doLayout = [
      ...LAYOUT.estrategico.sections,
      ...(LAYOUT.estrategico.appendices ?? []),
    ]
      .filter((e) => e.enabled && e.summary_source)
      .map((e) => e.id)
      .sort();
    expect(DESTINOS.map(([id]) => id).sort()).toEqual(doLayout);
    expect(DESTINOS.length).toBeGreaterThan(0);
  });

  it.each(DESTINOS)(
    "%s renderiza a string exata de narrativas.summaries.%s",
    (sectionId, summaryKey) => {
      const expected = FIXTURE.summaries[summaryKey];
      expect(expected, `fixture sem summaries.${summaryKey}`).toBeTruthy();
      renderSection(sectionId, buildData());
      expect(screen.getByText(expected)).toBeInTheDocument();
    },
  );

  it("nº de seções que entregam == nº de destinos declarados (KR-C)", () => {
    const entregues = DESTINOS.filter(([sectionId, summaryKey]) => {
      const sentinela = FIXTURE.summaries[summaryKey];
      // `includes("")` é sempre true — sentinela vazio inflaria a contagem.
      if (!sentinela?.trim()) return false;
      const { container, unmount } = renderSection(sectionId, buildData());
      const hit = (container.textContent ?? "").includes(sentinela);
      unmount();
      return hit;
    });
    expect(entregues.length).toBe(DESTINOS.length);
  });
});

describe("prova do gate — shapes que nenhum produtor emite (ADR-355)", () => {
  it("chave legada `narrativas[<ID maiúsculo>]` é ignorada", () => {
    const data = buildData({
      narrativas: { S1: { context: "CONTEXTO_LEGADO", conclusion: "CONCLUSAO_LEGADA" } },
    });
    renderSection("S1", data);
    expect(screen.queryByText("CONTEXTO_LEGADO")).not.toBeInTheDocument();
    expect(screen.queryByText("CONCLUSAO_LEGADA")).not.toBeInTheDocument();
  });

  it("objeto em `summaries.s1` não renderiza [object Object] e cai no derivado", () => {
    const data = buildData({
      narrativas: {
        ...FIXTURE,
        summaries: {
          ...FIXTURE.summaries,
          s1: { context: "OBJ_CTX", conclusion: "OBJ_CONCL" },
        },
      },
    });
    const { container } = renderSection("S1", data);
    expect(container.textContent).not.toContain("[object Object]");
    expect(screen.queryByText("OBJ_CTX")).not.toBeInTheDocument();
    expect(screen.queryByText(FIXTURE.summaries.s1)).not.toBeInTheDocument();
    // Camada 3 assume: template determinístico da S1 (patrimônio líquido).
    expect(screen.getByText(/Patrimônio líquido em/)).toBeInTheDocument();
  });

  it("string vazia no LLM não apaga o texto do E5.N", () => {
    const data = buildData({ section_summaries: { S1: "   " } });
    renderSection("S1", data);
    expect(screen.getByText(FIXTURE.summaries.s1)).toBeInTheDocument();
  });

  it("`section_summaries[<ID>]` (LLM) tem precedência sobre o E5.N", () => {
    const data = buildData({ section_summaries: { S1: "TEXTO_DO_LLM" } });
    renderSection("S1", data);
    expect(screen.getByText("TEXTO_DO_LLM")).toBeInTheDocument();
    expect(screen.queryByText(FIXTURE.summaries.s1)).not.toBeInTheDocument();
  });
});
