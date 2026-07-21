/**
 * A37.l10 (PD-04) — PremissasEconomicasCard: empty-state único quando todas
 * as classes estão `indisponivel` (caso real do dogfood emitia 10 linhas
 * idênticas) + rodapé sem jargão interno (COPY_GUIDELINES §6.3).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PremissasEconomicasCard } from "@/components/report/cards/PremissasEconomicasCard";
import type {
  PremissasEconomicasClassRow,
  PremissasEconomicasData,
} from "@/lib/api";

function row(
  overrides: Partial<PremissasEconomicasClassRow> & { classe_auvp: string },
): PremissasEconomicasClassRow {
  return {
    status: "emitted",
    retorno_real_esperado_pct_anual: "6.00",
    sigma_anual_pct: "12.00",
    fonte: "baseline global",
    fonte_origem: "global",
    effective_from: "2026-01-01",
    justificativa: null,
    razao_indisponivel: null,
    ...overrides,
  };
}

function indisponivel(classe: string): PremissasEconomicasClassRow {
  return row({
    classe_auvp: classe,
    status: "indisponivel",
    retorno_real_esperado_pct_anual: null,
    sigma_anual_pct: null,
    fonte: null,
    fonte_origem: null,
    effective_from: null,
    razao_indisponivel: "sem premissa vigente",
  });
}

const TODAS_AS_CLASSES = [
  "caixa",
  "rf_pos",
  "rf_pre",
  "rf_inflacao",
  "acoes_br",
  "acoes_intl",
  "fii",
  "imoveis_diretos",
  "cambio_usd",
  "cambio_eur",
];

function payload(
  classes: PremissasEconomicasClassRow[],
  status: "completo" | "parcial" = "parcial",
): PremissasEconomicasData {
  return { status, snapshot_at: "2026-07-01T12:00:00+00:00", classes };
}

describe("PremissasEconomicasCard — todas indisponíveis (A37.l10 PD-04)", () => {
  it("emite 1 empty-state e zero linhas repetidas (regressão: 10 linhas idênticas)", () => {
    render(
      <PremissasEconomicasCard
        premissas={payload(TODAS_AS_CLASSES.map(indisponivel))}
      />,
    );
    expect(
      screen.getAllByText(/Nenhuma premissa econômica vigente neste ciclo/),
    ).toHaveLength(1);
    expect(screen.queryAllByText(/Premissa indisponível/)).toHaveLength(0);
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("mantém badge de status e data do snapshot no empty-state", () => {
    render(
      <PremissasEconomicasCard
        premissas={payload(TODAS_AS_CLASSES.map(indisponivel))}
      />,
    );
    expect(screen.getByText(/Status: Parcial/)).toBeInTheDocument();
    expect(screen.getByText(/Snapshot em/)).toBeInTheDocument();
  });
});

describe("PremissasEconomicasCard — tabela parcial/completa", () => {
  it("mistura emitted + indisponivel renderiza tabela com 1 linha degradada", () => {
    render(
      <PremissasEconomicasCard
        premissas={payload([row({ classe_auvp: "caixa" }), indisponivel("fii")])}
      />,
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Caixa / Liquidez")).toBeInTheDocument();
    expect(screen.getByText("6.00% a.a.")).toBeInTheDocument();
    expect(screen.getAllByText(/Premissa indisponível/)).toHaveLength(1);
  });

  it("rodapé sem jargão interno (sem 'Override por workspace' / 'fiduciária')", () => {
    render(
      <PremissasEconomicasCard
        premissas={payload([row({ classe_auvp: "caixa" })], "completo")}
      />,
    );
    expect(screen.getByText(/Premissas revisadas trimestralmente/)).toBeInTheDocument();
    expect(screen.queryByText(/Override por workspace/)).toBeNull();
    expect(screen.queryByText(/fiduciária/)).toBeNull();
  });

  it("linha com override de workspace mostra selo 'Ajuste'", () => {
    render(
      <PremissasEconomicasCard
        premissas={payload(
          [
            row({
              classe_auvp: "acoes_br",
              fonte_origem: "workspace_override",
              justificativa: "carteira concentrada em small caps",
            }),
          ],
          "completo",
        )}
      />,
    );
    expect(screen.getByText("Ajuste")).toBeInTheDocument();
    expect(screen.queryByText("Override")).toBeNull();
  });
});
