/**
 * Wrapper `@/components/ui/tooltip` — o conteúdo do tooltip é **associado
 * programaticamente** ao trigger.
 *
 * O `Tooltip` do `@base-ui/react` v1.4.0 não emite `role="tooltip"` no popup
 * nem `aria-describedby` no trigger; o Radix (de onde este wrapper shadcn veio)
 * emitia os dois. Sem a associação, o leitor de tela anuncia que existe um
 * botão mas nunca o texto explicativo — exatamente o conteúdo que o
 * `InfoTooltip` existe para entregar. A divergência é invisível ao `tsc`
 * porque nenhuma prop muda de assinatura entre as duas libs.
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { InfoTooltip } from "@/components/ui/InfoTooltip";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

describe("ui/tooltip — associação acessível do conteúdo", () => {
  it("liga o texto do tooltip ao trigger via aria-describedby", async () => {
    const user = userEvent.setup();
    render(<InfoTooltip content="Taxa real de sucesso" ariaLabel="Sobre TRS" />);

    const trigger = screen.getByLabelText("Sobre TRS");
    await user.hover(trigger);
    await waitFor(() =>
      expect(screen.getByText("Taxa real de sucesso")).toBeInTheDocument(),
    );

    const describedBy = trigger.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    expect(document.getElementById(describedBy!)).toHaveTextContent(
      "Taxa real de sucesso",
    );
  });

  it("marca o popup com role=tooltip", async () => {
    const user = userEvent.setup();
    render(
      <Tooltip>
        <TooltipTrigger render={<button type="button">alvo</button>} />
        <TooltipContent>dica</TooltipContent>
      </Tooltip>,
    );

    await user.hover(screen.getByText("alvo"));
    await waitFor(() => expect(screen.getByRole("tooltip")).toBeInTheDocument());
    expect(screen.getByRole("tooltip")).toHaveTextContent("dica");
  });

  it("preserva aria-describedby explícito do call-site", async () => {
    const user = userEvent.setup();
    render(
      <>
        <span id="externo">descrição externa</span>
        <Tooltip>
          <TooltipTrigger
            aria-describedby="externo"
            render={<button type="button">alvo</button>}
          />
          <TooltipContent>dica</TooltipContent>
        </Tooltip>
      </>,
    );

    const trigger = screen.getByText("alvo");
    await user.hover(trigger);
    await waitFor(() => expect(screen.getByText("dica")).toBeInTheDocument());
    expect(trigger).toHaveAttribute("aria-describedby", "externo");
  });

  it("preserva role explícito no conteúdo", async () => {
    const user = userEvent.setup();
    render(
      <Tooltip>
        <TooltipTrigger render={<button type="button">alvo</button>} />
        <TooltipContent role="status">dica</TooltipContent>
      </Tooltip>,
    );

    await user.hover(screen.getByText("alvo"));
    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
