/**
 * Wrapper `@/components/ui/tabs` — `orientation` chega ao primitivo, não só ao
 * CSS.
 *
 * O wrapper desestruturava `orientation` e o gastava apenas num
 * `data-orientation` escrito à mão no Root: as classes `group-data-vertical/tabs:*`
 * passavam a valer, mas o `Tabs` do `@base-ui/react` nunca era informado — o
 * `aria-orientation` do tablist continuava `horizontal` e a navegação por seta
 * seguia o eixo horizontal. Tipo idêntico (`orientation` existe em
 * `Tabs.Root.Props`), comportamento divergente — a mesma classe do bug do
 * `Select` (ver [[SelectValueLabel.test.tsx]]).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

function Fixture({ orientation }: { orientation?: "horizontal" | "vertical" }) {
  return (
    <Tabs defaultValue="a" orientation={orientation}>
      <TabsList>
        <TabsTrigger value="a">Aba A</TabsTrigger>
        <TabsTrigger value="b">Aba B</TabsTrigger>
      </TabsList>
      <TabsContent value="a">painel A</TabsContent>
      <TabsContent value="b">painel B</TabsContent>
    </Tabs>
  );
}

describe("ui/tabs — orientation", () => {
  it("propaga vertical para o tablist (aria-orientation)", () => {
    render(<Fixture orientation="vertical" />);
    expect(screen.getByRole("tablist")).toHaveAttribute(
      "aria-orientation",
      "vertical",
    );
  });

  it("mantém o eixo de seta coerente com vertical", async () => {
    const user = userEvent.setup();
    render(<Fixture orientation="vertical" />);

    const [abaA, abaB] = screen.getAllByRole("tab");
    abaA.focus();
    await user.keyboard("{ArrowDown}");
    expect(abaB).toHaveFocus();
  });

  it("horizontal continua no eixo horizontal", async () => {
    const user = userEvent.setup();
    render(<Fixture />);

    // `horizontal` é o default de ARIA para tablist: o atributo é omitido.
    expect(screen.getByRole("tablist")).not.toHaveAttribute(
      "aria-orientation",
    );
    const [abaA, abaB] = screen.getAllByRole("tab");
    abaA.focus();
    await user.keyboard("{ArrowRight}");
    expect(abaB).toHaveFocus();
  });

  it("expõe data-orientation no Root e no tablist — as classes group-data-* dependem dele", () => {
    const { container } = render(<Fixture orientation="vertical" />);
    expect(container.querySelector("[data-slot='tabs']")).toHaveAttribute(
      "data-orientation",
      "vertical",
    );
    expect(screen.getByRole("tablist")).toHaveAttribute(
      "data-orientation",
      "vertical",
    );
  });
});
