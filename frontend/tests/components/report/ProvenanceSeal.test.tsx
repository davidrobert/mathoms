/**
 * Tests — A25.l5 (ADR-279) — selo de proveniência N1 + popover N2.
 *
 * Critérios G-d/G-h da lane: flag off ⇒ DOM idêntico; flag on muda só a
 * máscara do selo; copy pt-BR exata (co-design 2026-06-10) sem jargão de
 * pipeline (COPY_GUIDELINES §6.3); a11y de teclado/foco.
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MonetaryValue } from "@/components/report/MonetaryValue";
import {
  ReportProvenanceProvider,
} from "@/components/report/provenance/ReportProvenanceProvider";
import type { ReportAnalysisData } from "@/lib/api";

const RESERVA_LABEL = "Reserva de emergência — total líquido";
const DESPESA_LABEL = "Despesa total do período";
const ENDIVIDAMENTO_LABEL = "Endividamento — total de dívidas";

function makeData(overrides: Partial<ReportAnalysisData> = {}): ReportAnalysisData {
  return {
    _report_lineage: {
      pipeline_run_id: null,
      source_document_count: 14,
      source_document_ids: [],
      consumed_document_count: 12,
      consumed_document_ids: [],
    },
    _lineage: {
      lineage_version: "1.0",
      fields: {
        "reserva_emergencia.total_liquida": {
          label: RESERVA_LABEL,
          edge_type: "aggregation",
        },
        "fluxo_caixa.despesa_total": {
          label: DESPESA_LABEL,
          edge_type: "aggregation",
          signals: { tx_total: "120", dedup_collapsed: "3", dedup_review: "0" },
        },
        "endividamento.total_dividas": {
          label: ENDIVIDAMENTO_LABEL,
          edge_type: "aggregation",
        },
      },
    },
    ...overrides,
  };
}

function renderSeal(
  ui: React.ReactElement,
  { data = makeData(), enabled = true }: { data?: ReportAnalysisData; enabled?: boolean } = {},
) {
  return render(
    <ReportProvenanceProvider data={data} enabled={enabled}>
      {ui}
    </ReportProvenanceProvider>,
  );
}

const RESERVA = { fieldId: "reserva_emergencia.total_liquida" };
const DESPESA = { fieldId: "fluxo_caixa.despesa_total" };

describe("selo N1 — flag off ⇒ relatório === atual", () => {
  it("sem provider, prop provenance não muda nada no DOM", () => {
    const plain = render(<MonetaryValue value={1234.56} />);
    const withProp = render(<MonetaryValue value={1234.56} provenance={RESERVA} />);
    expect(withProp.container.innerHTML).toBe(plain.container.innerHTML);
  });

  it("provider com flag off ⇒ DOM idêntico (zero selo/handler)", () => {
    const plain = render(<MonetaryValue value={1234.56} />);
    const flagged = renderSeal(<MonetaryValue value={1234.56} provenance={RESERVA} />, {
      enabled: false,
    });
    expect(flagged.container.innerHTML).toBe(plain.container.innerHTML);
  });

  it("flag on mas campo sem dados de lineage ⇒ DOM idêntico", () => {
    const plain = render(<MonetaryValue value={10} />);
    const unknown = renderSeal(
      <MonetaryValue value={10} provenance={{ fieldId: "campo.inexistente" }} />,
    );
    expect(unknown.container.innerHTML).toBe(plain.container.innerHTML);
  });
});

describe("selo N1 — flag on", () => {
  it("flag-ON === flag-off exceto máscara do selo (mesmo texto, mesmo valor)", () => {
    const plain = render(<MonetaryValue value={250000.45} />);
    const { container } = renderSeal(
      <MonetaryValue value={250000.45} provenance={RESERVA} />,
    );
    expect(container.textContent).toBe(plain.container.textContent);
    expect(container.querySelector("[data-provenance-seal]")).not.toBeNull();
  });

  it("affordance light+dark via tokens (markup tema-agnóstico) — snapshot isolado", () => {
    const { container } = renderSeal(
      <MonetaryValue value={1000} provenance={RESERVA} data-testid="mv" />,
    );
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    expect(seal.className).toContain("decoration-dotted");
    expect(seal.className).toContain("decoration-[var(--border)]");
    expect(seal.className).toContain("hover:decoration-[var(--brand-primary)]");
    expect(seal.className).toContain("underline-offset-[3px]");
    expect(seal.className).toContain("cursor-help");
    expect(seal.outerHTML).toMatchSnapshot();
  });

  it("hero usa espessura 1.5px", () => {
    const { container } = renderSeal(
      <MonetaryValue value={1000} size="hero" provenance={RESERVA} />,
    );
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    expect(seal.className).toContain("decoration-[1.5px]");
  });

  it("aria-label sem jargão: 'Como chegamos ao {label}'", () => {
    const { container } = renderSeal(<MonetaryValue value={1000} provenance={RESERVA} />);
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    expect(seal.getAttribute("aria-label")).toBe(`Como chegamos ao ${RESERVA_LABEL}`);
  });

  it("sinal +/− fica FORA do sublinhado (selo só nos dígitos)", () => {
    const { container } = renderSeal(
      <MonetaryValue value={-500} signed provenance={RESERVA} />,
    );
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    expect(seal.textContent).not.toContain("-");
    expect(container.textContent).toContain("-");
  });
});

describe("popover N2 — copy exata", () => {
  async function openPopover(provenance = DESPESA, data = makeData()) {
    const user = userEvent.setup();
    const { container } = renderSeal(<MonetaryValue value={100} provenance={provenance} />, {
      data,
    });
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    await user.click(seal);
    const popup = await screen.findByText("Como chegamos a esse número");
    return { user, seal, popup: popup.closest("[data-slot=popover-content]") as HTMLElement };
  }

  it("título, subtítulo, 4 verbos e rodapé (fluxo, k>0)", async () => {
    const { popup } = await openPopover();
    const text = popup.textContent ?? "";
    expect(text).toContain("Como chegamos a esse número");
    expect(text).toContain(DESPESA_LABEL);
    expect(text).toContain("Li 12 documentos que você enviou");
    expect(text).toContain("Conferi 120 lançamentos — 3 apareciam repetidos e contei só uma vez");
    expect(text).toContain("Classifiquei cada lançamento por categoria");
    expect(text).toContain("Calculei somando o que entra e subtraindo o que sai");
    expect(text).toContain("O número acima é o que vale. Aqui só mostro como conferi.");
  });

  it("snapshot textual pt-BR dos valores expostos (G-d)", async () => {
    const { popup } = await openPopover();
    expect(popup.textContent).toMatchSnapshot();
  });

  it("snapshot textual pt-BR — endividamento total_dividas (G-d, A25.l6)", async () => {
    const { popup } = await openPopover({ fieldId: "endividamento.total_dividas" });
    expect(popup.textContent).toMatchSnapshot();
  });

  it("k=0 ⇒ 'sem repetições' — NUNCA '0 repetidos'", async () => {
    const data = makeData();
    data._lineage!.fields["fluxo_caixa.despesa_total"].signals = {
      tx_total: "80",
      dedup_collapsed: "0",
      dedup_review: "0",
    };
    const { popup } = await openPopover(DESPESA, data);
    expect(popup.textContent).toContain("Conferi 80 lançamentos, sem repetições");
    expect(popup.textContent).not.toMatch(/0 (apareciam|repetidos)/);
  });

  it("counts de documentos null ⇒ verbo sem número (nunca '0')", async () => {
    const data = makeData({
      _report_lineage: {
        pipeline_run_id: null,
        source_document_count: 0,
        source_document_ids: [],
        consumed_document_count: 0,
        consumed_document_ids: [],
      },
    });
    const { popup } = await openPopover(DESPESA, data);
    expect(popup.textContent).toContain("Li os documentos que você enviou");
    expect(popup.textContent).not.toContain("Li 0");
  });

  it("agregado baseline-fed (sem lançamentos) omite Conferi/Classifiquei", async () => {
    const { popup } = await openPopover(RESERVA);
    expect(popup.textContent).toContain("Li 12 documentos que você enviou");
    expect(popup.textContent).not.toContain("Conferi");
    expect(popup.textContent).not.toContain("Classifiquei");
    expect(popup.textContent).toContain("Calculei somando o que entra e subtraindo o que sai");
  });

  it("edge_type passthrough ⇒ 'Confirmei o saldo direto dos seus extratos'", async () => {
    const data = makeData();
    data._lineage!.fields["reserva_emergencia.total_liquida"].edge_type = "passthrough";
    const { popup } = await openPopover(RESERVA, data);
    expect(popup.textContent).toContain("Confirmei o saldo direto dos seus extratos");
    expect(popup.textContent).not.toContain("Calculei somando");
  });

  it("copy gate §6.3: DOM do popover sem jargão de pipeline", async () => {
    const { popup } = await openPopover();
    expect(popup.textContent).not.toMatch(/stage|pipeline|artefato|dedup|hash|run/i);
  });
});

describe("popover N2 — needs_review", () => {
  it("faixa âmbar (forma+texto) + selo variante âmbar", async () => {
    const data = makeData();
    data._lineage!.fields["fluxo_caixa.despesa_total"].signals = {
      tx_total: "120",
      dedup_collapsed: "3",
      dedup_review: "2",
    };
    const user = userEvent.setup();
    const { container } = renderSeal(<MonetaryValue value={100} provenance={DESPESA} />, {
      data,
    });
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    expect(seal.className).toContain("decoration-[var(--semantic-warning)]");
    await user.click(seal);
    const band = await screen.findByText(
      "Ainda estou conferindo um detalhe deste número. Pode mudar levemente.",
    );
    const wrapper = band.closest("[data-provenance-needs-review]") as HTMLElement;
    expect(wrapper).not.toBeNull();
    // `--semantic-alert` é o mesmo hex de `--semantic-warning`; o call-site foi
    // normalizado para o trio canônico gain/loss/alert para o gate de contraste
    // conseguir parear fundo↔texto por nome (dev/check_tint_contrast.py).
    expect(wrapper.className).toContain("var(--semantic-alert)");
    expect(wrapper.querySelector("svg")).not.toBeNull();
  });
});

describe("popover N2 — a11y de teclado e motion", () => {
  it("Enter abre; Escape fecha e devolve o foco ao selo", async () => {
    const user = userEvent.setup();
    const { container } = renderSeal(<MonetaryValue value={100} provenance={DESPESA} />);
    const seal = container.querySelector("[data-provenance-seal]") as HTMLElement;
    seal.focus();
    await user.keyboard("{Enter}");
    await screen.findByText("Como chegamos a esse número");
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByText("Como chegamos a esse número")).toBeNull(),
    );
    expect(document.activeElement).toBe(seal);
  });

  it("prefers-reduced-motion desliga animação (motion-reduce:animate-none)", async () => {
    const user = userEvent.setup();
    const { container } = renderSeal(<MonetaryValue value={100} provenance={DESPESA} />);
    await user.click(container.querySelector("[data-provenance-seal]") as HTMLElement);
    const popup = (await screen.findByText("Como chegamos a esse número")).closest(
      "[data-slot=popover-content]",
    ) as HTMLElement;
    expect(popup.className).toContain("motion-reduce:animate-none");
  });
});
