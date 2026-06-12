/**
 * Learning loop (A12 P4) — toast + modal + badge.
 *
 * Cobre:
 *   - Badge "Regra" renderiza quando ``override_source === "rule"``
 *   - Badge NÃO renderiza com ``override_source === "manual"``
 *   - Modal CreateRuleDialog renderiza preview + criação
 *   - Modal mostra checkbox de confirmação quando ``requires_user_confirmation``
 *   - Heatmap de "meses já publicados" aparece quando ``matches_in_closed_months > 0``
 *
 * Não cobre: integração full E2E (vai pra Playwright).
 */
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";
import { CreateRuleDialog } from "@/app/(app)/transactions/_components/CreateRuleDialog";
import { TransactionRow } from "@/app/(app)/transactions/_components/TransactionRow";
import { Table, TableBody } from "@/components/ui/table";
import type { TransactionItem } from "@/lib/api";

const API = "/api/v1";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/transactions",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useWorkspace: () => ({
    workspace: {
      id: "ws-1",
      name: "Test",
      family_surname: "Test",
      role: "owner" as const,
      joined_at: "2026-01-01T00:00:00.000Z",
    },
    workspaces: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

function mkTx(overrides: Partial<TransactionItem> = {}): TransactionItem {
  return {
    data: "2026-04-15",
    descricao: "MERCADO PAGO IFOOD",
    valor: -42.5,
    banco: "C6",
    categoria: "Alimentação",
    tipo_conta: "corrente",
    titular: "F",
    moeda: "BRL",
    transaction_hash: "h1",
    row_id: "h1:0",
    is_overridden: false,
    ...overrides,
  };
}

function wrapRow(tx: TransactionItem) {
  return (
    <Table>
      <TableBody>
        <TransactionRow
          tx={tx}
          categoryOptions={["Alimentação", "Outros"]}
          editing={false}
          editCategory=""
          savingOverride={false}
          onStartEdit={vi.fn()}
          onCancelEdit={vi.fn()}
          onEditCategoryChange={vi.fn()}
          onSaveOverride={vi.fn()}
          onRemoveOverride={vi.fn()}
        />
      </TableBody>
    </Table>
  );
}

describe("TransactionRow · rule source badge (A12 P4)", () => {
  it("renders 'Regra' badge when override_source === 'rule'", () => {
    render(
      wrapRow(
        mkTx({ is_overridden: true, override_source: "rule" }),
      ),
    );
    expect(screen.getByTestId("rule-source-badge")).toBeInTheDocument();
    expect(screen.getByText("Regra")).toBeInTheDocument();
  });

  it("does NOT render 'Regra' badge for manual override", () => {
    render(
      wrapRow(
        mkTx({ is_overridden: true, override_source: "manual" }),
      ),
    );
    expect(screen.queryByTestId("rule-source-badge")).not.toBeInTheDocument();
    // Manual mostra "editado".
    expect(screen.getByText("editado")).toBeInTheDocument();
  });

  it("does NOT render any source badge when not overridden", () => {
    render(wrapRow(mkTx()));
    expect(screen.queryByTestId("rule-source-badge")).not.toBeInTheDocument();
    expect(screen.queryByText("editado")).not.toBeInTheDocument();
  });
});

describe("CreateRuleDialog · preview + create flow (A12 P4)", () => {
  it("pré-preenche keyword e categoria dos defaults", () => {
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="MERCADO PAGO IFOOD"
        defaultTargetCategory="Alimentação"
        categoryOptions={["Alimentação", "Outros"]}
      />,
    );
    expect(screen.getByTestId("rule-keyword-input")).toHaveValue(
      "MERCADO PAGO IFOOD",
    );
    expect(screen.getByTestId("rule-target-select")).toHaveValue("Alimentação");
  });

  it("mostra microcopy explicando matching por trecho sob o campo keyword", () => {
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="MERCADO PAGO IFOOD"
        defaultTargetCategory="Alimentação"
        categoryOptions={["Alimentação"]}
      />,
    );
    expect(
      screen.getByText(/encurte para o trecho que se repete/i),
    ).toBeInTheDocument();
  });

  it("hint de match único aparece com keyword longa (pré-fill não-editado)", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        `${API}/workspaces/:ws/categorization/rules/preview`,
        () =>
          HttpResponse.json({
            matches_total: 1,
            matches_in_closed_months: 0,
            matches_with_manual_override: 0,
            matches_blocked_internal_transfers: 0,
            matches_amount_total_brl_cents: 4_662_429,
            matches_by_month: {},
            conflicts: [],
            low_risk: true,
            requires_user_confirmation: false,
            warnings: [],
          }),
      ),
    );
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="Pix recebido de ARVO SAUDE LTDA"
        defaultTargetCategory="receita_pj"
        categoryOptions={["receita_pj"]}
      />,
    );
    await user.click(screen.getByTestId("rule-preview-button"));
    await waitFor(() => {
      expect(screen.getByTestId("rule-single-match-hint")).toBeInTheDocument();
    });
  });

  it("hint de match único NÃO aparece com keyword curta", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        `${API}/workspaces/:ws/categorization/rules/preview`,
        () =>
          HttpResponse.json({
            matches_total: 1,
            matches_in_closed_months: 0,
            matches_with_manual_override: 0,
            matches_blocked_internal_transfers: 0,
            matches_amount_total_brl_cents: 10_000,
            matches_by_month: {},
            conflicts: [],
            low_risk: true,
            requires_user_confirmation: false,
            warnings: [],
          }),
      ),
    );
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="IFOOD"
        defaultTargetCategory="Alimentação"
        categoryOptions={["Alimentação"]}
      />,
    );
    await user.click(screen.getByTestId("rule-preview-button"));
    await waitFor(() => {
      expect(screen.getByText(/transações no total/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("rule-single-match-hint"),
    ).not.toBeInTheDocument();
  });

  it("'Ver impacto' chama /preview e renderiza contadores", async () => {
    const user = userEvent.setup();
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="MERCADO PAGO IFOOD"
        defaultTargetCategory="Alimentação"
        categoryOptions={["Alimentação", "Outros"]}
      />,
    );
    await user.click(screen.getByTestId("rule-preview-button"));
    await waitFor(() => {
      // Padrão de fixture default: total=12, closed=3, manual=1.
      expect(screen.getByText(/12/)).toBeInTheDocument();
      expect(
        screen.getByText(/em meses já publicados/i),
      ).toBeInTheDocument();
    });
  });

  it("mostra checkbox de confirmação quando requires_user_confirmation=true", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        `${API}/workspaces/:ws/categorization/rules/preview`,
        () =>
          HttpResponse.json({
            matches_total: 50,
            matches_in_closed_months: 0,
            matches_with_manual_override: 0,
            matches_blocked_internal_transfers: 0,
            matches_amount_total_brl_cents: 100_000,
            matches_by_month: { "202604": 50 },
            conflicts: [],
            low_risk: false,
            requires_user_confirmation: true,
            warnings: [
              {
                code: "high_impact_open_months",
                message:
                  "Esta regra vai recategorizar transações em meses não-publicados.",
              },
            ],
          }),
      ),
    );
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="UBER"
        defaultTargetCategory="Transporte"
        categoryOptions={["Transporte"]}
      />,
    );
    await user.click(screen.getByTestId("rule-preview-button"));
    await waitFor(() => {
      expect(screen.getByTestId("rule-confirm-impact")).toBeInTheDocument();
    });
    const createBtn = screen.getByTestId("rule-create-button");
    expect(createBtn).toBeDisabled();
    await user.click(screen.getByTestId("rule-confirm-impact"));
    expect(createBtn).not.toBeDisabled();
  });

  it("destaca contagem de meses fechados visualmente", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        `${API}/workspaces/:ws/categorization/rules/preview`,
        () =>
          HttpResponse.json({
            matches_total: 10,
            matches_in_closed_months: 5,
            matches_with_manual_override: 0,
            matches_blocked_internal_transfers: 0,
            matches_amount_total_brl_cents: 50_000,
            matches_by_month: {},
            conflicts: [],
            low_risk: true,
            requires_user_confirmation: false,
            warnings: [],
          }),
      ),
    );
    render(
      <CreateRuleDialog
        open
        onOpenChange={vi.fn()}
        workspaceId="ws-1"
        defaultKeyword="IFOOD"
        defaultTargetCategory="Alimentação"
        categoryOptions={["Alimentação"]}
      />,
    );
    await user.click(screen.getByTestId("rule-preview-button"));
    await waitFor(() => {
      expect(
        screen.getByText(/em meses já publicados/i),
      ).toBeInTheDocument();
    });
  });
});
