/**
 * ADR-439 D2/D5 — a nota da residência não apurada tem um produtor só.
 *
 * O relatório e o dashboard do `/plano` tinham redações próprias, e elas divergiram: o
 * relatório dizia `sem_valor` sem a direção do erro e tratava o leitor por "vocês"
 * (COPY_GUIDELINES §1.2); o dashboard dizia "fica fora do patrimônio" sem condição, falso
 * para quem vendeu a casa no ano (ADR-444 D2). A identidade entre as duas superfícies é o
 * que barra a próxima cópia local da frase.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PieNotes } from "@/app/(app)/plano/_components/_dashboard/PieNotes";
import { PatrimonioCategoriasCard } from "@/components/report/cards/PatrimonioCategoriasCard";
import {
  NOTA_RESIDENCIA_NAO_APURADA,
  NotaResidenciaNaoApurada,
} from "@/lib/residenciaNaoApurada";
import type { MotivoBaldeImovel, PatrimonioData } from "@/types/report-analysis";

const MOTIVOS = Object.keys(NOTA_RESIDENCIA_NAO_APURADA) as MotivoBaldeImovel[];

function frasesDa(motivo: MotivoBaldeImovel): string[] {
  return NOTA_RESIDENCIA_NAO_APURADA[motivo].texto.split(/(?<=\.) /);
}

function patrimonioComResidencia(motivo: MotivoBaldeImovel): PatrimonioData {
  const residencia = { categoria: "Residência", valor: 0, pct: 0, estado: "nao_apurado", motivo };
  const veiculos = { categoria: "Veículos", valor: 50_000, pct: 100 };
  return { bruto: 50_000, composicao: [residencia, veiculos] } as PatrimonioData;
}

describe("NOTA_RESIDENCIA_NAO_APURADA — voz", () => {
  it.each(MOTIVOS)("%s abre pelo estado e não usa vocativo", (motivo) => {
    const { texto } = NOTA_RESIDENCIA_NAO_APURADA[motivo];
    expect(texto).toMatch(/^Residência não apurada: /);
    expect(texto).not.toMatch(/\bvocês?\b|a família/i);
  });

  it("não declarada não presume imóvel próprio — quem aluga também cai nela", () => {
    const { texto } = NOTA_RESIDENCIA_NAO_APURADA.nao_declarada;
    expect(texto).toMatch(/própria ou alugada/);
    expect(texto).not.toMatch(/qual imóvel/);
  });
});

// Oráculo do `financial-planner`: onde está o valor da casa em cada forma do motivo. O front
// não distingue as formas, então a frase diz cada direção — condicionada quando é uma só.
describe("NOTA_RESIDENCIA_NAO_APURADA — direção do erro por forma", () => {
  it.each([
    ["nao_localizada", "identidade perdida na leitura", /o valor dele pode estar em Outros imóveis\./],
    ["nao_localizada", "vendido ou transferido", /Se ele foi vendido ou transferido, a marcação ficou desatualizada$/],
    ["sem_valor", "valor não apurado", /Se ainda é próprio, ficou fora da soma, e o patrimônio real é maior\./],
    ["sem_valor", "zero em 31/12", /Se foi vendido ou transferido, a residência atual pode estar em Outros imóveis$/],
    ["nao_classificada", "própria sem marcação", /todos os imóveis contam em Outros imóveis$/],
    ["nao_declarada", "própria ou alugada", /todos os imóveis contam em Outros imóveis$/],
  ] as const)("%s (%s)", (motivo, _forma, direcao) => {
    expect(NOTA_RESIDENCIA_NAO_APURADA[motivo].texto).toMatch(direcao);
  });

  it("nenhuma frase tira a casa da soma sem condição", () => {
    const exclusoes = MOTIVOS.flatMap(frasesDa).filter((f) => /fora d[ao] (soma|total|patrimônio)/.test(f));
    expect(exclusoes.length).toBeGreaterThan(0);
    for (const frase of exclusoes) expect(frase).toMatch(/^Se /);
  });

  it("sem valor não se diz 'apurado': o zero declarado em 31/12 foi apurado", () => {
    expect(NOTA_RESIDENCIA_NAO_APURADA.sem_valor.texto).not.toMatch(/sem valor apurado/);
  });
});

describe("NOTA_RESIDENCIA_NAO_APURADA — ação", () => {
  it("'Indicar' sem marcação nenhuma; 'Atualizar' quando a marcação envelheceu", () => {
    const rotulos = Object.fromEntries(
      MOTIVOS.map((motivo) => [motivo, NOTA_RESIDENCIA_NAO_APURADA[motivo].cta.label]),
    );
    expect(rotulos).toEqual({
      nao_localizada: "Atualizar residência",
      sem_valor: "Atualizar residência",
      vinculo_perdido: "Atualizar residência",
      nao_classificada: "Indicar residência",
      nao_declarada: "Indicar residência",
      nao_classificados: "Indicar residência",
    });
  });

  it.each(["nao_localizada", "sem_valor", "vinculo_perdido"] as const)(
    "%s: 'Atualizar' só vem depois da condição de venda (ADR-444 D5)",
    (motivo) => {
      const frases = frasesDa(motivo);
      expect(frases[frases.length - 1]).toMatch(/^Se (ele )?foi vendido ou transferido, /);
    },
  );

  it.each(MOTIVOS)("%s: o CTA continua a frase e leva à configuração da residência", (motivo) => {
    const { texto, cta } = NOTA_RESIDENCIA_NAO_APURADA[motivo];
    render(
      <p data-testid="nota">
        <NotaResidenciaNaoApurada motivo={motivo} />
      </p>,
    );
    const nota = screen.getByTestId("nota");
    const link = screen.getByRole("link", { name: cta.label });

    expect(nota.textContent).toBe(`${texto} · ${cta.label}`);
    expect(link.parentElement).toBe(nota);
    expect(link).toHaveAttribute("href", "/config?tab=members");
  });
});

describe("relatório e dashboard dizem a mesma frase", () => {
  it.each(MOTIVOS)("%s", (motivo) => {
    const relatorio = render(<PatrimonioCategoriasCard patrimonio={patrimonioComResidencia(motivo)} />);
    const notaDoRelatorio = relatorio.getByTestId("nota-residencia-nao-apurada").textContent;
    const dashboard = render(<PieNotes notes={[{ kind: "residencia_nao_apurada", motivo }]} />);
    const notaDoDashboard = dashboard.getByTestId("pie-notes").textContent;

    expect(notaDoRelatorio).toBe(`— ${notaDoDashboard}`);
  });
});
