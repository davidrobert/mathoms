/**
 * DebtForm (ADR-227 §D1 · Sprint A15 Onda 5) — coverage do percentual condicional.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DebtForm } from "@/components/debts/DebtForm";
import type {
  MemberOption,
  PropertyOption,
} from "@/components/debts/DebtForm";

const PROPS_SINGLE: PropertyOption[] = [
  { id: "p-single", label: "Apto Vila Mariana", cotitulares_count: 1 },
];
const PROPS_COTITULAR: PropertyOption[] = [
  { id: "p-multi", label: "Casa praia (cotitularidade)", cotitulares_count: 2 },
];
const MEMBERS: MemberOption[] = [{ id: "m-1", label: "David" }];

describe("DebtForm", () => {
  it("oculta percentual_atribuicao_imovel quando property tem 1 cotitular", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <DebtForm
        properties={PROPS_SINGLE}
        members={MEMBERS}
        onSubmit={onSubmit}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/Imóvel vinculado/i));
    await user.click(screen.getByText(/Apto Vila Mariana/i));
    expect(screen.queryByLabelText(/Percentual de atribuição/i)).not.toBeInTheDocument();
  });

  it("mostra percentual_atribuicao_imovel quando property tem >1 cotitular", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <DebtForm
        properties={PROPS_COTITULAR}
        members={MEMBERS}
        onSubmit={onSubmit}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/Imóvel vinculado/i));
    await user.click(screen.getByText(/Casa praia/i));
    await waitFor(() =>
      expect(screen.getByLabelText(/Percentual de atribuição/i)).toBeInTheDocument(),
    );
  });

  it("submete payload sem percentual quando property tem 1 cotitular", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <DebtForm
        properties={PROPS_SINGLE}
        members={MEMBERS}
        onSubmit={onSubmit}
      />,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Saldo devedor/i), "300000");
    await user.click(screen.getByLabelText(/Imóvel vinculado/i));
    await user.click(screen.getByText(/Apto Vila Mariana/i));
    await user.click(screen.getByRole("button", { name: /Salvar/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].percentual_atribuicao_imovel).toBeNull();
    expect(onSubmit.mock.calls[0][0].property_id).toBe("p-single");
    expect(onSubmit.mock.calls[0][0].saldo_devedor_brl).toBe("300000");
  });
});
