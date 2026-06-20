/**
 * Unit tests — SParecerSection (ADR-199 / ADR-208 · Ato 5).
 *
 * Cobre:
 * - empty state (404) → "Parecer ainda não gerado";
 * - render premium (full content) com hero + risk + movimento + métrica;
 * - render free (teaser): chip "Amostra", teaser "+N no Premium";
 * - sigilo §13: jamais cita Perini/Cerbasi/AUVP no DOM.
 *
 * MSW intercepta GET /workspaces/:wsId/reports/:reportId/planner-review.
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";

import { SParecerSection } from "@/components/report/sections/SParecer";
import type { PlannerReviewResponse } from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api/v1";
const WS_ID = "ws-test-uuid-1";
const REPORT_ID = "report-test-uuid-1";

function premiumResponse(): PlannerReviewResponse {
  return {
    id: "pr-1",
    workspace_id: WS_ID,
    pipeline_run_id: "run-1",
    status: "Gerado",
    persona_hash: "a".repeat(64),
    manifest_version: "1.0",
    schema_version: "1.0",
    model_id: "anthropic/claude-sonnet-4",
    tier_at_generation: "premium",
    items_shown_count: 5,
    items_gated_count: 0,
    cost_usd_cents: 42,
    created_at: "2026-05-13T16:00:00Z",
    published_at: null,
    superseded_at: null,
    supersedes_id: null,
    superseded_by_id: null,
    immutable_hash: null,
    content: {
      version: "1.0",
      diagnostico_geral:
        "Família com reserva sólida, exposição imobiliária acima do recomendado.",
      pontos_fortes: [
        {
          titulo: "Reserva 12 meses",
          descricao: "Liquidez adequada.",
          tema_canonico: "Saúde de balanço",
          section_id: "S1",
        },
      ],
      riscos: [
        {
          severidade: "Crítica",
          titulo: "Concentração imobiliária 70%",
          descricao: "Acima do teto recomendado.",
          tema_canonico: "Alocação",
          evidencia: null,
          evidencia_path: null,
          ancoras: [],
          section_id: "S4",
          confianca: "alta",
        },
      ],
      sugestoes_execucao: [
        {
          prioridade: "P0",
          acao: "Diversificar 15% do imobiliário",
          impacto_qualitativo: "Reduz risco sistêmico imobiliário.",
          tema_canonico: "Alocação",
          confianca: "alta",
          section_id: "S4",
          suggestion_dedup_key: "d".repeat(64),
          impacto_estimado: null,
          evidencia_path: null,
          ancoras: [],
        },
      ],
      sugestoes_taticas: [],
      sugestoes_estrategicas: [],
      metricas: [
        {
          nome: "Concentração imobiliária",
          valor_atual: "70%",
          target: "45%",
          frequencia_revisao: "trimestral",
          section_id: "S4",
          tema_canonico: "Alocação",
        },
      ],
      notas_metodologicas: [],
      meta: {
        tier_at_generation: "premium",
        persona_hash: "a".repeat(64),
        manifest_version: "1.0",
        schema_version: "1.0",
        model_id: "anthropic/claude-sonnet-4",
        generated_at: "2026-05-13T16:00:00Z",
        gated_counts: {
          pontos_fortes: 0,
          riscos: 0,
          sugestoes_execucao: 0,
          sugestoes_taticas: 0,
          sugestoes_estrategicas: 0,
          metricas: 0,
          notas_metodologicas: 0,
        },
      },
    },
  };
}

function freeResponse(): PlannerReviewResponse {
  const p = premiumResponse();
  return {
    ...p,
    tier_at_generation: "free",
    items_gated_count: 14,
    content: {
      ...p.content,
      pontos_fortes: p.content.pontos_fortes.slice(0, 1),
      sugestoes_execucao: [],
      sugestoes_taticas: [],
      sugestoes_estrategicas: [],
      metricas: [],
      meta: {
        ...p.content.meta,
        tier_at_generation: "free",
        gated_counts: {
          pontos_fortes: 2,
          riscos: 3,
          sugestoes_execucao: 2,
          sugestoes_taticas: 1,
          sugestoes_estrategicas: 1,
          metricas: 4,
          notas_metodologicas: 2,
        },
      },
    },
  };
}

describe("<SParecerSection /> @ADR-199", () => {
  it("renderiza empty state quando endpoint retorna 404 not_generated_yet", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:wsId/reports/:reportId/planner-review`,
        () =>
          HttpResponse.json(
            { detail: { code: "not_generated_yet", message: "ainda não gerado" } },
            { status: 404 },
          ),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-empty")).toBeInTheDocument();
    });
    expect(screen.getByText("Parecer ainda não gerado")).toBeInTheDocument();
  });

  it("renderiza parecer premium completo (hero + risco crítico + movimento P0)", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:wsId/reports/:reportId/planner-review`,
        () => HttpResponse.json(premiumResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });
    expect(screen.getByTestId("parecer-tier-badge")).toHaveTextContent("Premium");
    expect(screen.getByTestId("parecer-risks-table")).toBeInTheDocument();
    expect(screen.getByText("Concentração imobiliária 70%")).toBeInTheDocument();
    expect(screen.getByTestId("parecer-movimento-card")).toBeInTheDocument();
    expect(screen.getByText("Diversificar 15% do imobiliário")).toBeInTheDocument();
    expect(screen.getByTestId("parecer-metricas-table")).toBeInTheDocument();
    expect(screen.getByTestId("parecer-disclaimer")).toBeInTheDocument();
  });

  it("renderiza tier free com badge Amostra + teaser '+N no Premium'", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:wsId/reports/:reportId/planner-review`,
        () => HttpResponse.json(freeResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);

    await waitFor(() => {
      expect(screen.getByTestId("parecer-tier-badge")).toHaveTextContent("Amostra");
    });
    // Teaser de horizonte execução
    expect(
      screen.getByTestId("parecer-horizonte-teaser-execucao"),
    ).toBeInTheDocument();
    expect(screen.getByText(/2 movimento/i)).toBeInTheDocument();
  });

  it("não cita Perini/Cerbasi/AUVP no DOM renderizado (sigilo §13)", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:wsId/reports/:reportId/planner-review`,
        () => HttpResponse.json(premiumResponse()),
      ),
    );

    const { container } = render(
      <SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("parecer-hero")).toBeInTheDocument();
    });

    const html = container.innerHTML.toLowerCase();
    expect(html).not.toContain("perini");
    expect(html).not.toContain("cerbasi");
    expect(html).not.toContain("auvp");
    expect(html).not.toContain("viver de renda");
  });

  it("renderiza disclaimer fiduciário visível", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:wsId/reports/:reportId/planner-review`,
        () => HttpResponse.json(premiumResponse()),
      ),
    );

    render(<SParecerSection workspaceId={WS_ID} reportId={REPORT_ID} />);
    await waitFor(() => {
      expect(screen.getByTestId("parecer-disclaimer")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/não constitui recomendação personalizada/i),
    ).toBeInTheDocument();
  });
});
