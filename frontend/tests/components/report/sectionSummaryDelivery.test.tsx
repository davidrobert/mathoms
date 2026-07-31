/**
 * ENTREGA das narrativas de seção — lado TS do par (A40.l4 · ADR-356).
 *
 * Lê os MESMOS dois arquivos que `tests/test_e5n_delivery_contract.py`:
 * `e5n_delivery.json` (fixture gerada pelo produtor — o sentinela é a própria
 * copy dele; fixture inventada à mão descreveria um mundo que o produtor não
 * emite, lição da A40.l3) e `e5n_destinations.json` (mapa seção → chave
 * ESPERADO, declarado fora do layout).
 *
 * Render via `<MigratedSection>` — não a seção direto — porque o dispatcher é
 * onde a alcançabilidade se prova. As asserções usam o mapa DECLARADO, nunca o
 * do layout: o layout é o que está sendo verificado.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/lib/WorkspaceProvider", () => ({
  useWorkspace: () => ({
    workspace: { id: "ws-1" },
    workspaces: [],
    loading: false,
  }),
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
    path.resolve(
      __dirname,
      "../../../../tests/fixtures/narrativas/e5n_delivery.json",
    ),
    "utf8",
  ),
);

interface DestinationsDeclaration {
  readonly destinations: Record<string, { key: string; razao: string }>;
  readonly orphans: Record<string, string>;
}

/**
 * Mapa ESPERADO seção → chave, declarado FORA do layout. As asserções abaixo
 * usam este mapa, nunca `summary_source` do layout: ler o destino do layout e
 * asserí-lo contra o layout deixava mapeamento semanticamente errado invisível
 * (`summary_source: "s2"` na S2 — s2 é o parágrafo de SCORE — passava 30/30).
 * Mesmo arquivo lido por `tests/test_e5n_delivery_contract.py`.
 */
const DECLARATION: DestinationsDeclaration = JSON.parse(
  readFileSync(
    path.resolve(
      __dirname,
      "../../../../tests/fixtures/narrativas/e5n_destinations.json",
    ),
    "utf8",
  ),
);

const EXPECTED_DESTINATIONS: ReadonlyArray<readonly [string, string]> =
  Object.entries(DECLARATION.destinations).map(
    ([sectionId, spec]) => [sectionId, spec.key] as const,
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

function buildData(
  overrides: Partial<Record<string, unknown>> = {},
): ReportAnalysisData {
  return {
    narrativas: FIXTURE,
    patrimonio: { liquido: 1_200_000, composicao: [] },
    fluxo_caixa: {
      receita_recorrente_mensal: 30_000,
      despesa_mensal_media: 20_000,
    },
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

/** Entradas do layout que montam `<SectionSummary>` e estão habilitadas. */
const RENDER_SITES = [
  ...LAYOUT.estrategico.sections,
  ...(LAYOUT.estrategico.appendices ?? []),
].filter((e) => e.enabled && e.summary);

/** Texto renderizado da seção, com unmount — render por seção é isolado. */
function textOf(sectionId: string): string {
  const { container, unmount } = renderSection(sectionId, buildData());
  const text = container.textContent ?? "";
  unmount();
  return text;
}

const SUMMARY_TEXTS = Object.entries(FIXTURE.summaries).filter(([, t]) =>
  t.trim(),
);

describe("entrega de narrativa de seção (ADR-356)", () => {
  it("o layout entrega exatamente os destinos declarados (P7)", () => {
    const doLayout = RENDER_SITES.filter((e) => e.summary_source).map(
      (e) => [e.id, e.summary_source] as const,
    );
    expect(
      [...doLayout].sort(),
      "summary_source do layout divergiu de e5n_destinations.json — mudar o " +
        "mapeamento é decisão de produto, com a razão semântica por escrito",
    ).toEqual([...EXPECTED_DESTINATIONS].sort());
    // O resolver consome o mesmo mapa que o layout declara.
    expect(Object.entries(LAYOUT_SUMMARY_SOURCE).sort()).toEqual(
      [...doLayout].sort(),
    );
  });

  it.each(EXPECTED_DESTINATIONS)(
    "%s renderiza a string exata de narrativas.summaries.%s",
    (sectionId, summaryKey) => {
      const expected = FIXTURE.summaries[summaryKey];
      expect(expected, `fixture sem summaries.${summaryKey}`).toBeTruthy();
      renderSection(sectionId, buildData());
      expect(screen.getByText(expected)).toBeInTheDocument();
    },
  );

  // "e não de outra": destino semanticamente errado publica o parágrafo de OUTRA
  // dimensão. Comparação por string exata da fixture — sem regex de tópico.
  it.each(EXPECTED_DESTINATIONS)(
    "%s não renderiza o texto de nenhum summary além de %s",
    (sectionId, summaryKey) => {
      const text = textOf(sectionId);
      const intrusos = SUMMARY_TEXTS.filter(
        ([key, value]) => key !== summaryKey && text.includes(value),
      ).map(([key]) => key);
      expect(
        intrusos,
        `${sectionId} publicou summary de outra dimensão`,
      ).toEqual([]);
    },
  );

  it("seção sem destino declarado não publica summary nenhum", () => {
    const semDestino = RENDER_SITES.map((e) => e.id).filter(
      (id) => !DECLARATION.destinations[id],
    );
    expect(semDestino.length).toBeGreaterThan(0);
    for (const sectionId of semDestino) {
      const text = textOf(sectionId);
      const vazados = SUMMARY_TEXTS.filter(([, value]) =>
        text.includes(value),
      ).map(([key]) => key);
      expect(
        vazados,
        `${sectionId} não tem destino e publicou summary`,
      ).toEqual([]);
    }
  });

  it("nº de seções que entregam == nº de destinos declarados (KR-C)", () => {
    const entregues = EXPECTED_DESTINATIONS.filter(
      ([sectionId, summaryKey]) => {
        const sentinela = FIXTURE.summaries[summaryKey];
        // `includes("")` é sempre true — sentinela vazio inflaria a contagem.
        if (!sentinela?.trim()) return false;
        return textOf(sectionId).includes(sentinela);
      },
    );
    expect(entregues.length).toBe(EXPECTED_DESTINATIONS.length);
  });
});

describe("prova do gate — shapes que nenhum produtor emite (ADR-356)", () => {
  it("chave legada `narrativas[<ID maiúsculo>]` é ignorada", () => {
    const data = buildData({
      narrativas: {
        S1: { context: "CONTEXTO_LEGADO", conclusion: "CONCLUSAO_LEGADA" },
      },
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

describe("composição e supressão por seção (ADR-356)", () => {
  // ADR-148: o sufixo de changelog era anexado DENTRO de `deriveSectionSummary`
  // (camada 3). Com a camada 2 acesa em 7 seções, a 3 deixaria de rodar nelas e
  // o sufixo pararia de renderizar sem ninguém decidir isso. Decisão da l4: o
  // sufixo é anotação de delta, ortogonal a quem escreveu o parágrafo-base ⇒
  // COMPÕE com a camada 2.
  it("sufixo de changelog compõe com o texto do E5.N", () => {
    const data = buildData({
      changelog: [
        { section_id: "S1", summary: "Patrimônio subiu 4% no ciclo" },
      ],
    });
    renderSection("S1", data);
    expect(
      screen.getByText(`${FIXTURE.summaries.s1} Patrimônio subiu 4% no ciclo.`),
    ).toBeInTheDocument();
  });

  it("sufixo de changelog NÃO compõe com o texto do LLM", () => {
    const data = buildData({
      section_summaries: { S1: "TEXTO_DO_LLM" },
      changelog: [{ section_id: "S1", summary: "delta qualquer" }],
    });
    renderSection("S1", data);
    expect(screen.getByText("TEXTO_DO_LLM")).toBeInTheDocument();
    expect(screen.queryByText(/delta qualquer/)).not.toBeInTheDocument();
  });

  // A S9 em empty state tem <EmptyState/> que JÁ afirma "sem riscos cadastrados
  // não há análise de cobertura" — o `s9` diria o mesmo com outro wording.
  it("S9 em empty state não publica o s9 (o EmptyState é a mensagem)", () => {
    const data = buildData({
      narrativas: {
        ...FIXTURE,
        charts: {
          ...FIXTURE.charts,
          bubble_riscos: {
            ...FIXTURE.charts.bubble_riscos,
            data_state: "empty",
          },
        },
      },
    });
    const { container } = renderSection("S9", data);
    expect(container.textContent).not.toContain(FIXTURE.summaries.s9);
    expect(
      screen.getByText(/Mapeie seus riscos críticos/i),
    ).toBeInTheDocument();
  });
});
