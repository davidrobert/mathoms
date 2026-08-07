/**
 * A28.l9 — specs do `<ReportDataQualityBanner/>`.
 *
 * Teste de honestidade (critério da lane): com o payload degradado, o
 * leitor responde "quão confiável é este relatório?" pelo banner, sem
 * abrir `<details>`. Relatório limpo colapsa para barra fina.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReportDataQualityBanner } from "@/components/report/ReportDataQualityBanner";
import type { ReportAnalysisData } from "@/lib/api";

const mockNeedsReview = vi.hoisted(() => ({ count: 0 }));
vi.mock("@/components/report/hooks/useNeedsReviewCount", () => ({
  useNeedsReviewCount: () => mockNeedsReview.count,
}));

function degradedData(): ReportAnalysisData {
  return {
    fluxo_caixa: {
      despesas_por_categoria: { moradia: 1_340_000, nao_identificado: 401_000 },
    },
    premissas_economicas: {
      status: "parcial",
      snapshot_at: "2026-07-01T00:00:00Z",
      classes: Array.from({ length: 10 }, (_, i) => ({
        classe_auvp: `classe_${i}`,
        status: "indisponivel" as const,
        retorno_real_esperado_pct_anual: null,
        sigma_anual_pct: null,
        fonte: null,
        fonte_origem: null,
        effective_from: null,
        justificativa: null,
        razao_indisponivel: "sem premissa vigente",
      })),
    },
    real_estate: {
      excluded_properties: Array.from({ length: 7 }, (_, i) => ({
        property_id: `p${i}`,
        descricao: `Imóvel sintético ${i}`,
        classification: "desconhecido",
        motivo: "Classificação pendente",
      })),
    } as unknown as ReportAnalysisData["real_estate"],
  };
}

describe("<ReportDataQualityBanner />", () => {
  it("degradado: consolida os 4 sinais com CTAs de resolução", () => {
    mockNeedsReview.count = 13;
    render(
      <ReportDataQualityBanner
        data={degradedData()}
        workspaceId="ws-1"
        runOutcome="complete"
      />,
    );

    const banner = screen.getByTestId("data-quality-banner");
    expect(banner.textContent).toMatch(/4 pendências afetam/);
    // 401k / 1.741k = 23,0%
    expect(banner.textContent).toMatch(/23,0% do total/);
    expect(banner.textContent).toMatch(/13 documentos aguardam revisão/);
    expect(banner.textContent).toMatch(/10\/10 classes sem premissa vigente/);
    expect(banner.textContent).toMatch(/7 imóveis sem classificação/);

    expect(
      screen.getByRole("link", { name: "Reclassificar transações" }),
    ).toHaveAttribute(
      "href",
      "/transactions?category=nao_identificado&sort=valor_desc",
    );
    expect(
      screen.getByRole("link", { name: "Revisar documentos" }),
    ).toHaveAttribute("href", "/documents?filter=needs_review");
    expect(
      screen.getByRole("link", { name: "Ver premissas adotadas" }),
    ).toHaveAttribute("href", "#APP_B");
    expect(
      screen.getByRole("link", { name: "Classificar em Configurações" }),
    ).toHaveAttribute("href", "/config?tab=members");
  });

  it("limpo: colapsa para barra fina com role=status", () => {
    mockNeedsReview.count = 0;
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    render(
      <ReportDataQualityBanner
        data={data}
        workspaceId="ws-1"
        runOutcome="complete"
      />,
    );

    expect(screen.queryByTestId("data-quality-banner")).not.toBeInTheDocument();
    const bar = screen.getByTestId("data-quality-clean");
    expect(bar).toHaveAttribute("role", "status");
    expect(bar.textContent).toMatch(/sem pendências/);
  });

  it("singular: 1 documento → copy no singular", () => {
    mockNeedsReview.count = 1;
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    render(
      <ReportDataQualityBanner
        data={data}
        workspaceId="ws-1"
        runOutcome="complete"
      />,
    );
    const banner = screen.getByTestId("data-quality-banner");
    expect(banner.textContent).toMatch(/1 pendência afeta/);
    expect(banner.textContent).toMatch(/1 documento aguarda revisão/);
  });
  // ─── A40.l18 · ADR-357 — supressão da afirmação positiva ───

  it("run degradado: NÃO afirma que está limpo", () => {
    // O par com o teste "limpo" acima é o controle positivo. Sem ele,
    // `toHaveCount(0)` passaria também se o banner não montasse por outro motivo.
    mockNeedsReview.count = 0;
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    render(
      <ReportDataQualityBanner
        data={data}
        workspaceId="ws-1"
        runOutcome="with_gap"
      />,
    );

    expect(screen.queryByTestId("data-quality-clean")).not.toBeInTheDocument();
    // A ressalva positiva é da A40.l22; aqui o slot fica vazio, não mentindo.
    expect(screen.queryByTestId("data-quality-banner")).not.toBeInTheDocument();
  });

  it("run indeterminável: fail-closed, também não afirma", () => {
    // `reports.pipeline_run_id` é `ondelete="SET NULL"`. Sem evidência do
    // desfecho, a afirmação positiva não se sustenta.
    mockNeedsReview.count = 0;
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    render(
      <ReportDataQualityBanner
        data={data}
        workspaceId="ws-1"
        runOutcome="unknown"
      />,
    );
    expect(screen.queryByTestId("data-quality-clean")).not.toBeInTheDocument();
  });

  it("run degradado COM sinais: o alerta continua, com as N linhas", () => {
    // A supressão gateia só a barra limpa. Incompleto não é falso — e pôr
    // `runOutcome` no `count` renderizaria "1 pendência" com <ul> vazia.
    mockNeedsReview.count = 2;
    const data: ReportAnalysisData = {
      fluxo_caixa: { despesas_por_categoria: { moradia: 1000 } },
    };
    render(
      <ReportDataQualityBanner
        data={data}
        workspaceId="ws-1"
        runOutcome="with_gap"
      />,
    );

    const banner = screen.getByTestId("data-quality-banner");
    expect(banner.textContent).toMatch(/2 documentos aguardam revisão/);
    expect(
      screen.getByLabelText("Pendências de qualidade de dados").children,
    ).toHaveLength(1);
  });
});
