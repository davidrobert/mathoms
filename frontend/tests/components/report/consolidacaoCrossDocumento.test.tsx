/** A40.l2 PR3c2a — a nota que declara à família os lançamentos contados uma vez só.
 *
 * Nível de RENDER, não de payload: o aceite do track é explícito porque asserção
 * sobre payload não prova o que foi renderizado. Duas frases, uma base por frase
 * (ADR-306 D1) — a matriz cobre as três variantes de contagem do corpus × os
 * quatro estados da janela.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ConsolidacaoCrossDocumentoNota } from "@/components/report/ConsolidacaoCrossDocumentoNota";

/** Termos que a família nunca pode ler — jargão de máquina (COPY §6.3) e as
 * palavras que dizem o oposto do que houve. "consolidado" está aqui porque
 * PRODUCT.md §1 já o usa como "juntar/somar": o leitor entenderia o contrário. */
const PROIBIDOS = [
  "stage", "pipeline", "artefato", "hash", "digest", "run", "flag", "enforce",
  "override", "colapso", "colapsar", "cross-documento", "deduplic", "natural key",
  "consolidad", "removemos", "excluímos", "apagamos", "arquivo",
];

function comBases(
  corpusCount: number,
  meses: Array<{ mes: string; count: number }>,
  janelaCount: number | null,
  { comBloco12m = true, janelaMeses = 12 }: { comBloco12m?: boolean; janelaMeses?: number } = {},
) {
  const janela12m: Record<string, unknown> = { janela: "12m", janela_meses: janelaMeses };
  if (janelaCount !== null) {
    janela12m.consolidacao_cross_documento = {
      count: janelaCount,
      meses: [{ mes: "2026-02", count: janelaCount }],
    };
  }
  return {
    janela: "full",
    janela_meses: 36,
    consolidacao_cross_documento: { count: corpusCount, meses },
    ...(comBloco12m ? { janela_12m: janela12m } : {}),
  };
}

const corpusText = () => screen.getByTestId("s2-consolidacao-corpus").textContent ?? "";
const janelaText = () => screen.queryByTestId("s2-consolidacao-janela")?.textContent ?? "";

describe("ConsolidacaoCrossDocumentoNota — frase A (o fato, base corpus)", () => {
  it("N === 1: singular, e o fecho não diz 'cada um'", () => {
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(1, [{ mes: "2026-02", count: 1 }], 1)} />);

    expect(corpusText()).toBe(
      "1 lançamento aparecia em mais de um documento do mesmo banco. Contamos uma vez só.",
    );
  });

  it("N > 1 em UM mês: 'todos no mesmo mês', nunca 'em 1 mês'", () => {
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(4, [{ mes: "2026-02", count: 4 }], 4)} />);

    expect(corpusText()).toContain("4 lançamentos apareciam em mais de um documento do mesmo banco");
    expect(corpusText()).toContain("todos no mesmo mês");
    expect(corpusText()).not.toContain("em 1 mês");
  });

  it("N > 1 em M meses: declara M — é o 'em M meses' da salvaguarda", () => {
    const meses = [
      { mes: "2024-12", count: 4 },
      { mes: "2025-06", count: 3 },
      { mes: "2026-02", count: 4 },
    ];
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(11, meses, 7)} />);

    expect(corpusText()).toContain("11 lançamentos");
    expect(corpusText()).toContain("em 3 meses do período analisado");
  });
});

describe("ConsolidacaoCrossDocumentoNota — frase B (a janela das médias)", () => {
  it("n === 0: diz que as médias mensais NÃO mudaram por isso", () => {
    // O caso mais valioso: sem esta frase a família atribui à consolidação uma
    // queda nos headlines que ela não causou.
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(11, [{ mes: "2024-12", count: 11 }], 0)} />);

    expect(janelaText()).toContain("Nenhum deles está nos últimos 12 meses documentados");
    expect(janelaText()).toContain("não mudaram por causa disso");
  });

  it("0 < n < N: 'Destes, n estão …' — subconjunto explícito", () => {
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(11, [{ mes: "2026-02", count: 11 }], 7)} />);

    expect(janelaText()).toContain("Destes, 7 estão nos últimos 12 meses documentados");
    expect(janelaText()).toContain("base das médias mensais desta seção");
  });

  it("n === N > 1: 'Todos estão …'", () => {
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(4, [{ mes: "2026-02", count: 4 }], 4)} />);

    expect(janelaText()).toContain("Todos estão nos últimos 12 meses documentados");
  });

  it("n === N === 1: 'Ele está …'", () => {
    render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(1, [{ mes: "2026-02", count: 1 }], 1)} />);

    expect(janelaText()).toContain("Ele está nos últimos 12 meses documentados");
  });

  it("sem bloco de janela: a frase B some inteira, sem rótulo inventado", () => {
    render(
      <ConsolidacaoCrossDocumentoNota
        fluxo={comBases(4, [{ mes: "2026-02", count: 4 }], null, { comBloco12m: false })}
      />,
    );

    expect(screen.queryByTestId("s2-consolidacao-janela")).toBeNull();
    expect(corpusText()).toContain("4 lançamentos");
  });

  it("o rótulo sai do bloco da JANELA, nunca do corpus", () => {
    // Prova de mutação: trocar `describeJanelaEm(janela.rotulo)` pelo rótulo do
    // corpus imprime "em todo o período analisado (36 meses)" e derruba isto —
    // é a classe que a A40.l3 fechou, reaberta na frase.
    render(
      <ConsolidacaoCrossDocumentoNota
        fluxo={comBases(11, [{ mes: "2026-02", count: 11 }], 7, { janelaMeses: 1 })}
      />,
    );

    expect(janelaText()).toContain("no último mês documentado");
    expect(janelaText()).not.toContain("todo o período analisado");
  });
});

describe("ConsolidacaoCrossDocumentoNota — ausência e vocabulário", () => {
  it("sem o campo: NENHUM nó, não um alerta vazio nem '0 lançamentos'", () => {
    const { container } = render(
      <ConsolidacaoCrossDocumentoNota fluxo={{ janela: "full", janela_meses: 36 }} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("count 0 do produtor também não renderiza nada", () => {
    const { container } = render(
      <ConsolidacaoCrossDocumentoNota
        fluxo={{ janela: "full", consolidacao_cross_documento: { count: 0, meses: [] } }}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("fluxo undefined não estoura", () => {
    const { container } = render(<ConsolidacaoCrossDocumentoNota fluxo={undefined} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("nenhum identificador de máquina, e nenhuma palavra que diz o oposto do fato", () => {
    const meses = [
      { mes: "2024-12", count: 4 },
      { mes: "2026-02", count: 7 },
    ];
    const { container } = render(<ConsolidacaoCrossDocumentoNota fluxo={comBases(11, meses, 7)} />);
    const texto = (container.textContent ?? "").toLowerCase();

    for (const termo of PROIBIDOS) {
      expect(texto, `termo proibido na tela: ${termo}`).not.toContain(termo);
    }
  });

  it("sem R$ — a magnitude está deferida, e número que não reconcilia é pior que nenhum", () => {
    const { container } = render(
      <ConsolidacaoCrossDocumentoNota fluxo={comBases(11, [{ mes: "2026-02", count: 11 }], 7)} />,
    );

    expect(container.textContent).not.toContain("R$");
  });
});
