/**
 * Tests — ADR-220 · ParecerMovimentoCard renderiza label semântico por `impacto_estimado.tipo`.
 *
 * Cobre:
 * - Label "Patrimônio-alvo" quando tipo='patrimonio_alvo' (sem `/ ano` apenso)
 * - Label "Fluxo anual estimado" quando tipo='fluxo_anual' (com unidade)
 * - Label "Economia anual em IR" quando tipo='economia_anual_irpf'
 * - Label "Impacto estimado" (legado) quando tipo ausente/null
 * - Label "Impacto estimado" quando tipo='outro'
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ParecerMovimentoCard } from "@/components/report/sections/SParecer/ParecerMovimentoCard";
import type { ImpactoTipo, Sugestao } from "@/lib/api";

function makeSugestao(overrides: { tipo?: ImpactoTipo | null } = {}): Sugestao {
  return {
    prioridade: "P1",
    acao: "Acumular o patrimônio necessário para destravar IF.",
    impacto_qualitativo: "Estoque-alvo dimensiona quanto falta até a meta.",
    tema_canonico: "Renda passiva",
    confianca: "alta",
    section_id: "S7",
    suggestion_dedup_key: "a".repeat(64),
    impacto_estimado: {
      valor_estimado_brl: "12426300.00",
      unidade: "ano",
      caveat: "Patrimônio-alvo calculado pela regra metodológica.",
      tipo: overrides.tipo === undefined ? null : overrides.tipo,
    },
    evidencia_path: null,
  };
}

describe("ParecerMovimentoCard — label semântico do impacto (ADR-220)", () => {
  it("mostra 'Patrimônio-alvo' (sem '/ ano') quando tipo=patrimonio_alvo", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: "patrimonio_alvo" })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Patrimônio-alvo:/)).toBeInTheDocument();
    // Sem unidade "/ ano" porque patrimônio é estoque, não fluxo
    expect(screen.queryByText(/\/ ano/)).not.toBeInTheDocument();
  });

  it("mostra 'Fluxo anual estimado' (com '/ ano') quando tipo=fluxo_anual", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: "fluxo_anual" })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Fluxo anual estimado:/)).toBeInTheDocument();
    expect(screen.getByText(/\/ ano/)).toBeInTheDocument();
  });

  it("mostra 'Economia anual em IR' quando tipo=economia_anual_irpf", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: "economia_anual_irpf" })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Economia anual em IR:/)).toBeInTheDocument();
  });

  it("mostra 'Capital de seguro faltante' quando tipo=gap_protecao", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: "gap_protecao" })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Capital de seguro faltante:/)).toBeInTheDocument();
  });

  it("mostra 'Impacto estimado' (legado) quando tipo ausente (runs pré-ADR-220)", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: null })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Impacto estimado:/)).toBeInTheDocument();
  });

  it("mostra 'Impacto estimado' quando tipo=outro", () => {
    render(
      <ParecerMovimentoCard
        sugestao={makeSugestao({ tipo: "outro" })}
        workspaceId="ws-1"
        readOnly
      />,
    );
    expect(screen.getByText(/Impacto estimado:/)).toBeInTheDocument();
  });
});
