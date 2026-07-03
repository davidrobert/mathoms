import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import {
  dedupeBySemanticKey,
  isCircularScoreItem,
  semanticKey,
} from "@/components/report/utils/curadoriaDestaques";
import { PontosFortesCard } from "@/components/report/cards/PontosFortesCard";
import { PontosUrgentesCard } from "@/components/report/cards/PontosUrgentesCard";

/** Curadoria defensiva de destaques (A28.l10) — fixtures espelham o dogfood:
 * ponto forte circular de score, par redundante reserva/colchão e alerta
 * circular "Score financeiro: 7.2/10 (Bom)". PII-zero. */

const scoreForte = {
  titulo: "Score Financeiro Positivo",
  descricao: "Classificação «Bom» (7.2/10) indica solidez financeira geral.",
};
const reservaForte = {
  titulo: "Reserva de Emergência Excelente",
  descricao: "Cobertura de 32 meses de despesas — acima dos 12 meses recomendados.",
};
const colchaoForte = {
  titulo: "Colchão Patrimonial Robusto",
  descricao: "Patrimônio investível cobre 27 meses de despesas — margem de segurança ampla.",
};
const poupancaForte = {
  titulo: "Taxa de Poupança Elevada",
  descricao: "Poupança recorrente de 28.0% da renda — acima da referência de 30%.",
};
const scoreUrgente = {
  acao: "Score financeiro: 7.2/10 (Bom)",
  prioridade: "Alta",
};

describe("isCircularScoreItem", () => {
  it("detecta ponto forte circular de score", () => {
    expect(isCircularScoreItem(scoreForte)).toBe(true);
  });

  it("detecta alerta circular de score", () => {
    expect(isCircularScoreItem(scoreUrgente)).toBe(true);
  });

  it("não suprime item substantivo", () => {
    expect(isCircularScoreItem(reservaForte)).toBe(false);
    expect(isCircularScoreItem(poupancaForte)).toBe(false);
  });
});

describe("semanticKey", () => {
  it("colapsa reserva e colchão na mesma família de cobertura", () => {
    expect(semanticKey(reservaForte)).toBe("cobertura-meses");
    expect(semanticKey(colchaoForte)).toBe("cobertura-meses");
  });

  it("mantém chaves distintas para teses distintas", () => {
    expect(semanticKey(poupancaForte)).not.toBe(semanticKey(reservaForte));
  });
});

describe("dedupeBySemanticKey", () => {
  it("emite 1 item para o par redundante reserva/colchão e derruba o circular", () => {
    const out = dedupeBySemanticKey([
      scoreForte,
      reservaForte,
      colchaoForte,
      poupancaForte,
    ]);
    expect(out).toEqual([reservaForte, poupancaForte]);
  });

  it("lista vazia permanece vazia", () => {
    expect(dedupeBySemanticKey([])).toEqual([]);
  });
});

describe("<PontosFortesCard /> curadoria defensiva", () => {
  it("não duplica cobertura nem exibe ponto circular de score", () => {
    render(
      <PontosFortesCard
        pontos={[scoreForte, reservaForte, colchaoForte, poupancaForte]}
      />,
    );
    expect(screen.getByText("Reserva de Emergência Excelente")).toBeInTheDocument();
    expect(screen.getByText("Taxa de Poupança Elevada")).toBeInTheDocument();
    expect(screen.queryByText("Colchão Patrimonial Robusto")).not.toBeInTheDocument();
    expect(screen.queryByText("Score Financeiro Positivo")).not.toBeInTheDocument();
  });
});

describe("<PontosUrgentesCard /> curadoria defensiva", () => {
  it("empty state honesto quando só resta o alerta circular de score", () => {
    render(<PontosUrgentesCard pontos={[scoreUrgente]} />);
    expect(screen.getByText("Nenhum ponto urgente neste período.")).toBeInTheDocument();
    expect(screen.queryByText(/Score financeiro/)).not.toBeInTheDocument();
  });
});
