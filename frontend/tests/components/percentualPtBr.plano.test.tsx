/**
 * Percentual em copy pt-BR usa vírgula decimal (COPY_GUIDELINES §4.6) — os
 * componentes fora do relatório trocados para `formatPercent` que não tinham
 * arquivo de teste. Um arquivo só porque o Vitest custa por arquivo, não por
 * teste; o par do relatório é `report/percentualPtBr.cards.test.tsx`.
 *
 * As premissas (`goalPremissas.ts`) e o IFHeroCard/PlanoKpiRow têm a asserção
 * no teste que já os exercitava.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { PERCENTUAL_COM_PONTO } from "../shared/percentualPtBr";

// Referência estável: a página de aportes tem `router` nas deps do effect de
// carga, e um objeto novo por render a recarrega em laço.
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/plano",
  useSearchParams: () => new URLSearchParams(),
}));

import { TaskProgressCard } from "@/components/tasks/TaskProgressCard";
import { DecisionCard } from "@/app/(app)/plano/_components/DecisionCard";
import AportesEditPage from "@/app/(app)/plano/aportes/page";
import MetaIFWizardPage from "@/app/(app)/plano/meta-if/wizard/page";
import type {
  AporteGoalResponse,
  Decision,
  IFGoalDerived,
  TaskProgress,
} from "@/lib/api";

const WS_API = "/api/v1/workspaces/:workspaceId";

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

function makeTaskProgress(overrides: Partial<TaskProgress>): TaskProgress {
  return {
    is_trackable: true,
    period_start: "2026-10-01",
    period_end: "2026-10-31",
    target_brl: 1000,
    executed_brl: 625,
    percent_executed: 62.5,
    matched_keywords: [],
    matched_transactions_count: 3,
    ...overrides,
  };
}

describe("<TaskProgressCard /> — percentual pt-BR", () => {
  function renderWithProgress(progress: TaskProgress) {
    server.use(
      http.get(`${WS_API}/tasks/:taskId/progress`, () => HttpResponse.json(progress)),
    );
    return render(<TaskProgressCard workspaceId="ws-1" taskId="task-1" />);
  }

  it("execução no mês usa vírgula", async () => {
    const { container } = renderWithProgress(makeTaskProgress({}));
    expect(await screen.findByText("62,5%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });

  // `formatPercent(null)` dá "0,0%" onde `null.toFixed` lançava: é a guarda
  // `pct != null` que mantém ausente ≠ zero (COPY_GUIDELINES §4.3).
  it("percentual ausente não vira 0,0%", async () => {
    const { container } = renderWithProgress(
      makeTaskProgress({ percent_executed: null }),
    );
    await screen.findByText("Execução no mês");
    expect(container.textContent).not.toContain("%");
  });
});

function makeDecision(overrides: Partial<Decision>): Decision {
  return {
    id: "dec-1",
    workspace_id: "ws-1",
    code: "D01",
    title: "Reduzir a taxa de retirada",
    rationale: null,
    amount_brl: null,
    status: "Pendente",
    supersedes_id: null,
    decided_at: null,
    executed_at: null,
    target_field: null,
    target_value: null,
    target_value_type: null,
    context_snapshot: null,
    impact_1y_brl: null,
    impact_10y_brl: null,
    horizon: "short_6_12m",
    priority: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("<DecisionCard /> — percentual pt-BR", () => {
  it("TRS do momento da decisão usa vírgula", () => {
    const { container } = render(
      <DecisionCard
        decision={makeDecision({ context_snapshot: { trs_pct_when_decided: 4.5 } })}
        allDecisions={[]}
        workspaceId="ws-1"
        onEdit={() => {}}
        onSupersede={() => {}}
        onMarkDecided={async () => {}}
        onExecute={async () => {}}
      />,
    );
    expect(screen.getByText("· TRS 4,5%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

const APORTE_GOAL: AporteGoalResponse = {
  id: "goal-aporte",
  workspace_id: "ws-1",
  type: "APORTE_MENSAL",
  meta_version: 1,
  inputs: {
    meta_aporte_mensal_brl: 3000,
    dia_aporte: 5,
    distribuicao: { "Renda fixa": 2000, "Renda variável": 1000 },
  },
  derived: {
    aporte_anual_brl: 36000,
    distribuicao_pct: { "Renda fixa": 66.7, "Renda variável": 33.3 },
  },
  effective_from: "2026-01-01",
  effective_to: null,
  is_template: false,
  notes: null,
  created_by: null,
  created_by_name: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("Página de aportes — percentual pt-BR", () => {
  it("distribuição derivada e linha de premissas usam vírgula", async () => {
    server.use(
      http.get(`${WS_API}/goals/aportes`, () => HttpResponse.json(APORTE_GOAL)),
      http.post(`${WS_API}/goals/aportes/compute`, () =>
        HttpResponse.json({ derived: APORTE_GOAL.derived }),
      ),
    );
    const { container } = render(<AportesEditPage />);

    expect(await screen.findByText("66,7%", {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText("33,3%")).toBeInTheDocument();
    expect(
      screen.getByText("Renda fixa: 66,7% · Renda variável: 33,3%"),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});

const IF_DERIVED: IFGoalDerived = {
  if_meta_brl: 4_800_000,
  aporte_necessario_mensal_brl: 12_000,
  if_meta_conservadora_brl: 6_000_000,
  aporte_mensal_com_patrimonio_atual_brl: null,
  patrimonio_atual_utilizado_brl: null,
};

describe("Wizard da meta IF — percentual pt-BR", () => {
  // Os inputs andam de 0,5 em 0,5 (`step={0.5}`); o default é inteiro e
  // esconderia o número cru do resumo do passo 4.
  it("TRS, retorno real e o resumo do passo 4 usam vírgula", async () => {
    server.use(
      http.post(`${WS_API}/goals/if/compute`, () =>
        HttpResponse.json({
          derived: IF_DERIVED,
          percentual_conquistado: null,
          faltante_brl: null,
        }),
      ),
    );
    const user = userEvent.setup();
    const { container } = render(<MetaIFWizardPage />);

    await user.click(await screen.findByRole("button", { name: /Próximo/ }));
    fireEvent.change(screen.getByLabelText("TRS (% ao ano)"), {
      target: { value: "4.5" },
    });
    expect(await screen.findByText("4,5%")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Próximo/ }));
    fireEvent.change(screen.getByLabelText("Retorno real a.a. (%)"), {
      target: { value: "5.5" },
    });
    expect(await screen.findByText("5,5% real a.a.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Próximo/ }));
    expect(
      await screen.findByText("Meta conservadora (TRS 4,0%)", {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByText("15a · 4,5% · 5,5%")).toBeInTheDocument();
    expect(container.textContent).not.toMatch(PERCENTUAL_COM_PONTO);
  });
});
