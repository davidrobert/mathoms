/**
 * Copy do `/plano` sob a COPY_GUIDELINES.
 *
 * O botão do HeaderActions só refaz o fetch do painel: "Atualizar análise"
 * é o nome reservado ao botão que roda o pipeline (§3, §6.3), e "dashboard"
 * é inglês cru vetado (§9). O OnboardingHero fala com qualquer composição
 * familiar — 1 pessoa, casal, filhos, dependentes (§8).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { HeaderActions } from "@/app/(app)/plano/_components/_dashboard/HeaderActions";
import { OnboardingHero } from "@/app/(app)/plano/_components/OnboardingHero";

describe("HeaderActions — botão que recarrega os dados", () => {
  it("chama-se 'Recarregar análise' e dispara o recarregamento", async () => {
    const onRefresh = vi.fn();
    render(
      <HeaderActions
        dataFreshness={null}
        loading={false}
        onRefresh={onRefresh}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Recarregar análise" }),
    );

    expect(onRefresh).toHaveBeenCalledOnce();
  });
});

describe("OnboardingHero — composição familiar", () => {
  it("não presume casal em nenhum passo", () => {
    const { container } = render(
      <OnboardingHero hasIfGoal={false} hasDecisions={false} />,
    );

    expect(container.textContent).not.toMatch(/casal/i);
  });
});
