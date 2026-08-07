/**
 * Wrapper `@/components/ui/select` — o trigger mostra o **rótulo** do item
 * selecionado, não o `value` cru.
 *
 * `Select.Value` do `@base-ui/react` só resolve rótulo quando o Root recebe
 * `items`; sem isso renderiza o value cru (divergência vs. Radix, de onde este
 * wrapper shadcn veio). Os call-sites usam `value` = id/slug e children = nome
 * legível, então a ausência de `items` vazava id para a tela.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const OPCOES = [
  { value: "p-single", label: "Apto Vila Mariana" },
  { value: "p-multi", label: "Casa praia" },
];

function Fixture({
  value,
  placeholder,
  items,
  valueChildren,
}: {
  value?: string;
  placeholder?: string;
  items?: ReadonlyArray<{ label: React.ReactNode; value: unknown }>;
  valueChildren?: React.ReactNode;
}) {
  return (
    <Select value={value} items={items}>
      <SelectTrigger aria-label="Imóvel">
        <SelectValue placeholder={placeholder}>{valueChildren}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {OPCOES.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

describe("ui/select — rótulo no trigger", () => {
  it("mostra o rótulo do item selecionado, não o value", () => {
    render(<Fixture value="p-single" />);
    const trigger = screen.getByLabelText("Imóvel");
    expect(trigger).toHaveTextContent("Apto Vila Mariana");
    expect(trigger).not.toHaveTextContent("p-single");
  });

  it("preserva o placeholder quando nada está selecionado", () => {
    render(<Fixture value="" placeholder="Sem vínculo" />);
    expect(screen.getByLabelText("Imóvel")).toHaveTextContent("Sem vínculo");
  });

  it("respeita `items` explícito no Root em vez da derivação", () => {
    render(
      <Fixture
        value="p-single"
        items={[{ value: "p-single", label: "Rótulo externo" }]}
      />,
    );
    expect(screen.getByLabelText("Imóvel")).toHaveTextContent("Rótulo externo");
  });

  it("respeita children explícito no SelectValue", () => {
    render(<Fixture value="p-single" valueChildren={<span>Fixo</span>} />);
    const trigger = screen.getByLabelText("Imóvel");
    expect(trigger).toHaveTextContent("Fixo");
    expect(trigger).not.toHaveTextContent("Apto Vila Mariana");
  });

  it("cai no value cru quando nenhum item corresponde", () => {
    render(<Fixture value="p-desconhecido" />);
    expect(screen.getByLabelText("Imóvel")).toHaveTextContent("p-desconhecido");
  });

  /** Congela o limite documentado em `useItemLabels`: a travessia não monta
   * componente intermediário, então o item entregue por ele é invisível e o
   * trigger volta ao value cru — silenciosamente. Quem cair nesse caso passa
   * `items` explícito. Se algum dia a derivação passar a cobrir indireção,
   * este teste falha e é o lembrete de atualizar o comentário. */
  it("não enxerga item entregue por componente intermediário", () => {
    function ItensIndiretos() {
      return (
        <>
          {OPCOES.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </>
      );
    }
    render(
      <Select value="p-single">
        <SelectTrigger aria-label="Imóvel">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <ItensIndiretos />
        </SelectContent>
      </Select>,
    );
    expect(screen.getByLabelText("Imóvel")).toHaveTextContent("p-single");
  });
});
