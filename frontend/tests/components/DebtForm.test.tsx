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

type TestUser = ReturnType<typeof userEvent.setup>;

/** Abre o Select de imóvel e escolhe a opção — esperando o popup abrir.
 *
 * O popup do Select (`@base-ui/react`) abre de forma assíncrona: em jsdom leva
 * ~7 macrotasks (~20ms) depois que `await user.click(trigger)` já retornou.
 * Enquanto fechado, o positioner tem `hidden` + `pointer-events: none`, e
 * clicar direto na opção joga "Unable to perform pointer interaction as the
 * element has `pointer-events: none`". Quem ganha essa corrida depende só da
 * velocidade do runner — o ubuntu-latest do CI (~400ms/teste) ganhava por
 * acidente, máquina de dev (~15ms/teste) perdia — o que dava falha só local.
 *
 * `findByRole("option")` é o ponto de espera determinístico: `*ByRole` exclui
 * nó fora da a11y tree, então só resolve **depois** que o popup abriu.
 */
async function escolheImovel(user: TestUser, nome: RegExp) {
  await user.click(screen.getByLabelText(/Imóvel vinculado/i));
  await user.click(await screen.findByRole("option", { name: nome }));
}

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
    await escolheImovel(userEvent.setup(), /Apto Vila Mariana/i);
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
    await escolheImovel(userEvent.setup(), /Casa praia/i);
    await waitFor(() =>
      expect(screen.getByLabelText(/Percentual de atribuição/i)).toBeInTheDocument(),
    );
  });

  it("mostra o rótulo — não o id/slug — nos triggers de imóvel e tipo", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <DebtForm
        properties={PROPS_SINGLE}
        members={MEMBERS}
        onSubmit={onSubmit}
      />,
    );
    const user = userEvent.setup();
    await escolheImovel(user, /Apto Vila Mariana/i);
    const imovel = screen.getByLabelText(/Imóvel vinculado/i);
    expect(imovel).toHaveTextContent(/Apto Vila Mariana/i);
    expect(imovel).not.toHaveTextContent("p-single");

    await user.click(screen.getByLabelText(/^Tipo$/i));
    await user.click(
      await screen.findByRole("option", { name: /Financiamento imobiliário/i }),
    );
    const tipo = screen.getByLabelText(/^Tipo$/i);
    expect(tipo).toHaveTextContent(/Financiamento imobiliário/i);
    expect(tipo).not.toHaveTextContent("financiamento_imobiliario");
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
    await escolheImovel(user, /Apto Vila Mariana/i);
    await user.click(screen.getByRole("button", { name: /Salvar/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].percentual_atribuicao_imovel).toBeNull();
    expect(onSubmit.mock.calls[0][0].property_id).toBe("p-single");
    expect(onSubmit.mock.calls[0][0].saldo_devedor_brl).toBe("300000");
  });
});
