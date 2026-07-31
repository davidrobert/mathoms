/**
 * A40.l3 — contrato de janela canônica (ADR-306 D1/D2/D6).
 *
 * D1: família mensalização (ratios/KPIs/médias) lê a **janela 12m**; agregado
 * histórico full-period é permitido **apenas rotulado**. O defeito que este
 * spec trava: o texto declara "últimos 12 meses" e cita o número do bloco
 * `full` — o valor canônico existe em `fluxo_caixa.janela_12m` e nunca era
 * lido (`rg janela_12m frontend/src` → 0 antes desta lane).
 *
 * Seis propriedades tornam o spec não-tautológico:
 *  1. self-check de divergência da fixture (se alguém "consertar" a fixture,
 *     o spec falha em vez de virar tautologia silenciosa);
 *  2. assert de dois lados por site (contém o valor 12m E **não** contém o
 *     valor full);
 *  3. simetria `full` — sem `janela_12m` o texto tem de declarar todo o
 *     período (D1 permite full **com** rótulo; o proibido é número full sob
 *     rótulo 12m);
 *  4. discriminador de campo errado — `janela_12m.fluxo_liquido` (R$ 228.000)
 *     é um TOTAL de 12 meses, não uma taxa mensal: proibido **como /mês**;
 *  5. **invariante de SEÇÃO** sobre `S2FluxoCaixaSection` composta. A versão
 *     anterior deste spec renderizava componentes isolados e 5 dos 21 asserts
 *     guardavam `buildFallbackConclusion`, inalcançável em produção
 *     (`FALLBACKS.fluxo_mensal` existe ⇒ `deriveChartConclusion` nunca devolve
 *     null ⇒ a prop `conclusion` é sempre string). Defeito de composição só cai
 *     em teste de composição;
 *  6. **invariante do seletor** — nenhum par (valor, rótulo) devolvido por
 *     `resolveConsumoBases`/`resolveFluxoJanelaMensal` mistura blocos. Um ramo
 *     de degradação anterior devolvia `total_pontuais` (acumulado de todo o
 *     período) carregando o rótulo `12m` do campo vizinho.
 *
 * **Escopo do invariante de seção:** o TEXTO derivado de dois cards
 * (`DespesasDoughnutChart` e `ReceitaDespesaMensalChart`) saiu desta lane para a
 * [[A40.l15]] — os dois citam bases legitimamente distintas (janela ex-aporte
 * por ADR-333 vs bruto de todo o período) e escolher qual base cada texto
 * declara é decisão de domínio. `CARDS_DA_L15` os exclui nominalmente da
 * varredura; o resto da seção continua coberto.
 *
 * A fixture é a **mesma** consumida pelo E2E (`janela-divergente.json`), para
 * que guarda e verificação renderizada não possam divergir.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

const mockUseConsumoPontuais = vi.fn();
vi.mock("@/hooks/useConsumoPontuais", () => ({
  useConsumoPontuais: (...args: unknown[]) => mockUseConsumoPontuais(...args),
}));

const mockUseIsPrint = vi.fn(() => false);
vi.mock("@/components/report/hooks/useIsPrint", () => ({
  useIsPrint: () => mockUseIsPrint(),
}));

vi.mock("react-chartjs-2", () => ({
  Chart: ({ "aria-label": ariaLabel }: { "aria-label"?: string }) => (
    <div data-testid="chart-mock" aria-label={ariaLabel} />
  ),
}));

import { FluxoMensalChart } from "@/components/report/charts/FluxoMensalChart";
import { DespesasDoughnutChart } from "@/components/report/charts/DespesasDoughnutChart";
import { ConsumoConscienteCard } from "@/components/report/cards/ConsumoConscienteCard";
import { HeroKpiGrid } from "@/components/report/kpi/HeroKpiGrid";
import { S2FluxoCaixaSection } from "@/components/report/sections/S2FluxoCaixaSection";
import {
  deriveChartConclusion,
  deriveSectionSummary,
} from "@/components/report/utils/conclusionUtils";
import {
  resolveConsumoBases,
  resolveFluxoJanelaMensal,
} from "@/components/report/utils/fluxoJanela";
import type { ReportAnalysisData } from "@/lib/api";
import type {
  ConsumoConscienteData,
  FluxoCaixaSummary,
  RatiosData,
} from "@/types/report-analysis";
import { CITA_AGREGADO, CLAUSULA_DE_BASE } from "../../shared/janelaBaseClause";

const FIXTURE_PATH = join(
  __dirname,
  "../../e2e/fixtures/reports/janela-divergente.json",
);

interface JanelaFixture extends ReportAnalysisData {
  fluxo_caixa: Record<string, unknown>;
  consumo_consciente: Record<string, unknown>;
  ratios: Record<string, unknown>;
}

function loadFixture(): JanelaFixture {
  return JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as JanelaFixture;
}

const fx = loadFixture();
const fluxo = fx.fluxo_caixa as FluxoCaixaSummary;
const janela12m = (fx.fluxo_caixa as { janela_12m: Record<string, number> })
  .janela_12m;
const consumo = fx.consumo_consciente as unknown as ConsumoConscienteData;

const brl0 = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v);
const brl2 = (v: number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);

/** Valores canônicos (12m) e proibidos (full) sob rótulo 12m. */
const V = {
  receita12m: brl0(92_000),
  despesa12m: brl0(81_000),
  receitaFull: brl0(40_000),
  despesaFull: brl0(36_000),
  /** `janela_12m.fluxo_liquido` — TOTAL de 12 meses, nunca uma taxa mensal. */
  totalIntervalo12m: brl0(228_000),
  pontuais12m: brl2(96_000),
  pontuaisFull: brl2(250_000),
} as const;

/** Bloco `full` sem `janela_12m` **e sem o campo `janela`** — o caminho real de
 * degradação (payload pré-A28).
 *
 * A versão anterior deletava só `janela_12m` e preservava `janela: "full"` no
 * top-level: `parseJanelaRotulo` casava o vocabulário e o argumento
 * `fallbackTipo` do seletor **nunca era exercitado**. O teste passava sem provar
 * nada sobre o ramo que existe para o payload que não declara base.
 * `janela_meses` fica (a contagem 36 vem do bloco lido, não de vizinho). */
function fluxoSemJanela12m(): FluxoCaixaSummary {
  const clone = JSON.parse(JSON.stringify(fluxo)) as Record<string, unknown>;
  delete clone.janela_12m;
  delete clone.janela;
  return clone as FluxoCaixaSummary;
}

/** Top-level com `janela` fora do vocabulário D2 — o shape que o produtor emite
 * no campo VIZINHO (`janela_referencia = "2025-01 a 2025-12"`,
 * `ratios_calculator.py:205`). Consumidor que aceitasse qualquer string
 * rotularia a base com um intervalo. */
function fluxoJanelaForaDoVocabulario(): FluxoCaixaSummary {
  const clone = JSON.parse(JSON.stringify(fluxo)) as Record<string, unknown>;
  delete clone.janela_12m;
  clone.janela = "2025-01 a 2025-12";
  return clone as FluxoCaixaSummary;
}

function dataSemJanela12m(): ReportAnalysisData {
  return { ...fx, fluxo_caixa: fluxoSemJanela12m() } as ReportAnalysisData;
}

/** Composição REAL de produção: a seção deriva a conclusão e a passa ao chart
 * (`S2FluxoCaixaSection.tsx:77`). Testar o chart sem a prop mediria um ramo que
 * produção não executa — a armadilha do I7. */
function renderFluxoCard(data: ReportAnalysisData, fluxoBloco: FluxoCaixaSummary) {
  return render(
    <FluxoMensalChart
      fluxo={fluxoBloco}
      conclusion={deriveChartConclusion("fluxo_mensal", data) ?? undefined}
    />,
  );
}

function contextText(): string {
  return document.querySelector("[data-chart-context]")?.textContent ?? "";
}

function conclusionText(): string {
  return document.querySelector("[data-chart-conclusion]")?.textContent ?? "";
}

function badges(root: ParentNode = document): string[] {
  return [...root.querySelectorAll("[data-janela-badge]")].map(
    (b) => b.textContent ?? "",
  );
}

beforeEach(() => {
  mockUseIsPrint.mockReturnValue(false);
  mockUseConsumoPontuais.mockReturnValue({
    items: [],
    total: 0,
    totalValor: 0,
    isLoading: false,
    error: null,
  });
});

// ─────────────────────────────────────────────────────────────────────
// 1. Self-check — a fixture precisa divergir, senão o resto é tautologia
// ─────────────────────────────────────────────────────────────────────

describe("fixture janela-divergente — self-check de divergência", () => {
  it("bloco full e janela_12m divergem por valor detectável", () => {
    expect(janela12m.receita_recorrente_mensal).not.toBe(
      fluxo.receita_recorrente_mensal,
    );
    expect(janela12m.despesa_mensal_media).not.toBe(fluxo.despesa_mensal_media);
    expect(consumo.total_pontuais_janela).not.toBe(consumo.total_pontuais);
    expect(Number(consumo.total_pontuais)).toBeGreaterThan(0);
  });

  it("rótulos de janela estão declarados nos dois blocos", () => {
    expect((fluxo as { janela?: string }).janela).toBe("full");
    expect(janela12m.janela).toBe("12m");
    expect((fluxo as { janela_meses?: number }).janela_meses).toBe(36);
    expect(janela12m.janela_meses).toBe(12);
  });

  it("ratios reproduz o shape do produtor: `janela` é vocabulário, `janela_referencia` é período", () => {
    // ratios_calculator.py:205 emite `janela_referencia = window.referencia`
    // ("2025-01 a 2025-12"). Fixture que trocasse os dois deixaria o consumidor
    // "funcionar" aqui e quebrar em produção (B3).
    expect(fx.ratios.janela).toBe("12m");
    expect(String(fx.ratios.janela_referencia)).toMatch(/^\d{4}-\d{2} a \d{4}-\d{2}$/);
  });

  it("aritmética da fixture fecha (total do intervalo ≠ mensalização)", () => {
    expect(janela12m.fluxo_liquido).toBe(228_000);
    expect(janela12m.receita_total - janela12m.despesa_total).toBe(
      janela12m.fluxo_liquido,
    );
    expect(janela12m.despesa_consumo).toBe(
      janela12m.despesa_total - janela12m.transferencia_patrimonial,
    );
    // `despesa_mensal_media` é BRUTA: inclui o aporte, logo `receita − despesa`
    // NÃO é "quanto sobra" e não fecha com a taxa ex-aporte de 25%.
    const sobraBruta =
      janela12m.receita_recorrente_mensal - janela12m.despesa_mensal_media;
    expect((sobraBruta / janela12m.receita_recorrente_mensal) * 100).not.toBe(
      janela12m.taxa_poupanca_recorrente,
    );
  });

  it("a prosa do E5 fala do período completo (D6), igual ao KPI de pontuais", () => {
    // Coerência interna do card: headline, equivalente e prosa na MESMA base.
    // (A prosa vem do calculator em produção; a fixture reproduz o texto real,
    // inclusive o formato en-US que o `f"{v:,.2f}"` emite — follow-up A40.l15.)
    expect(String(consumo.analise)).toContain("no período analisado");
    expect(String(consumo.analise)).toContain("20.8 meses de aporte");
  });

  it("narrativas não sombreiam o builder determinístico", () => {
    const narrativas = fx.narrativas as Record<string, unknown> | undefined;
    expect(Object.keys(narrativas ?? {})).toEqual(["perfil_familia"]);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 2. Invariante do SELETOR — o par (valor, rótulo) nunca mistura blocos
// ─────────────────────────────────────────────────────────────────────

describe("seletores — rótulo acompanha o bloco de onde o valor saiu", () => {
  it("consumo com janela 12m declarada: total full sob rótulo full", () => {
    const bases = resolveConsumoBases(consumo);
    // O bloco declara `janela: "12m"` — mas esse rótulo é da FOLGA (D1), e o
    // ramo antigo o colava no total acumulado (D6).
    expect(bases?.historico.valor).toBe(consumo.total_pontuais);
    expect(bases?.historico.rotulo.tipo).toBe("full");
    expect(bases?.equivalente.valor).toBe(consumo.equivalente_meses_aporte);
    expect(bases?.equivalente.rotulo.tipo).toBe("full");
    expect(bases?.rotuloFolga?.tipo).toBe("12m");
  });

  it("consumo SEM bloco/rótulo de janela: valor full E rótulo full, nunca full sob 12m", () => {
    const semJanela = {
      ...consumo,
      janela: undefined,
      janela_meses: undefined,
      total_pontuais_janela: undefined,
    };
    const bases = resolveConsumoBases(semJanela);
    expect(bases?.historico.valor).toBe(consumo.total_pontuais);
    expect(bases?.historico.rotulo.tipo).toBe("full");
    // Sem declaração não há rótulo inventado para folga/teto.
    expect(bases?.rotuloFolga).toBeNull();
  });

  it("o rótulo histórico nunca carrega contagem de meses de outro bloco", () => {
    // `consumo_consciente.janela_meses = 12` conta os meses da janela da folga.
    // Imprimi-lo ao lado do acumulado de todo o período seria o mesmo defeito.
    expect(consumo.janela_meses).toBe(12);
    expect(resolveConsumoBases(consumo)?.historico.rotulo.meses).toBeUndefined();
  });

  it("fluxo: o bloco lido e o rótulo devolvido são o mesmo bloco", () => {
    expect(resolveFluxoJanelaMensal(fluxo)?.rotulo.tipo).toBe("12m");
    expect(resolveFluxoJanelaMensal(fluxo)?.receitaRecorrenteMensal).toBe(
      janela12m.receita_recorrente_mensal,
    );
    const semJanela = resolveFluxoJanelaMensal(fluxoSemJanela12m());
    expect(semJanela?.rotulo.tipo).toBe("full");
    expect(semJanela?.receitaRecorrenteMensal).toBe(
      fluxo.receita_recorrente_mensal,
    );
    // Bloco full não emite a taxa ex-aporte: omitir > recomputar (ADR-333).
    expect(semJanela?.taxaPoupancaRecorrentePct).toBeUndefined();
  });

  it("degradação REAL (sem `janela_12m` e sem campo `janela`) usa o fallbackTipo do bloco", () => {
    // Exercita o argumento `fallbackTipo` de `readBloco`: sem declaração, a
    // posição do bloco é a única evidência da base. Preservar `janela: "full"`
    // (versão anterior desta fixture) fazia o vocabulário casar e o ramo nunca
    // rodar. Prova de mutação: trocar o `"full"` do segundo `readBloco` por
    // `"12m"` derruba este assert.
    const degradado = fluxoSemJanela12m();
    expect((degradado as { janela?: unknown }).janela).toBeUndefined();
    const lido = resolveFluxoJanelaMensal(degradado);
    expect(lido?.rotulo.tipo).toBe("full");
    // A contagem vem do bloco lido (`janela_meses` do top-level), não de vizinho.
    expect(lido?.rotulo.meses).toBe(36);
    expect(lido?.receitaRecorrenteMensal).toBe(fluxo.receita_recorrente_mensal);
  });

  it("`janela` fora do vocabulário D2 degrada para o fallbackTipo, sem rotular com o intervalo", () => {
    const lido = resolveFluxoJanelaMensal(fluxoJanelaForaDoVocabulario());
    expect(lido?.rotulo.tipo).toBe("full");
    expect(lido?.rotulo.anoIrpf).toBeUndefined();
    expect(JSON.stringify(lido?.rotulo)).not.toContain("2025-01");
    expect(lido?.receitaRecorrenteMensal).toBe(fluxo.receita_recorrente_mensal);
  });

  it("`janela_12m` sem o campo `janela` usa o fallbackTipo do PRÓPRIO bloco", () => {
    // Exercita `readBloco(bloco12m, "12m")` — o outro ramo de `fallbackTipo`,
    // que nenhum caso cobria: fixar `"full"` nos dois call sites deixava a suíte
    // verde. Aqui a posição do bloco é a única evidência da base, e rotulá-lo
    // "full" seria pôr rótulo de período completo num agregado de 12 meses.
    // Prova de mutação: trocar o `"12m"` do primeiro `readBloco` por `"full"`
    // derruba este assert.
    const semRotulo = JSON.parse(JSON.stringify(fluxo)) as Record<string, unknown>;
    const bloco = semRotulo.janela_12m as Record<string, unknown>;
    delete bloco.janela;
    delete bloco.janela_meses;
    const lido = resolveFluxoJanelaMensal(semRotulo as FluxoCaixaSummary);
    expect(lido?.rotulo.tipo).toBe("12m");
    expect(lido?.receitaRecorrenteMensal).toBe(janela12m.receita_recorrente_mensal);
    // `n_meses` do MESMO bloco serve de contagem; não há herança de vizinho.
    expect(lido?.rotulo.meses).toBe(janela12m.n_meses);
  });

  it("`janela: irpf_<ano>` no top-level vence a posição do bloco", () => {
    // O rótulo vem do CAMPO, não de onde o número estava — se viesse da
    // posição, o fallbackTipo "full" apagaria a declaração do payload.
    const irpf = fluxoSemJanela12m() as Record<string, unknown>;
    irpf.janela = "irpf_2024";
    const lido = resolveFluxoJanelaMensal(irpf as FluxoCaixaSummary);
    expect(lido?.rotulo.tipo).toBe("irpf");
    expect(lido?.rotulo.anoIrpf).toBe("2024");
  });
});

// ─────────────────────────────────────────────────────────────────────
// 3. Site: buildContext (FluxoMensalChart · [data-chart-context])
// ─────────────────────────────────────────────────────────────────────

describe("buildContext — barras do render, agregado do payload", () => {
  it("janela 12m: exibe o agregado de janela_12m e não o do bloco full", () => {
    renderFluxoCard(fx, fluxo);
    const text = contextText();
    expect(text).toContain("os últimos 12 meses documentados");
    expect(text).toContain(V.receita12m);
    expect(text).toContain(V.despesa12m);
    expect(text).not.toContain(V.receitaFull);
    expect(text).not.toContain(V.despesaFull);
  });

  it("contagem de meses vem do render, não do payload", () => {
    // ADR-306 D2 documenta `janela: "12m", janela_meses: 8` — payload com menos
    // meses documentados que a janela conceitual. A cláusula das barras não
    // pode herdar essa contagem: o range renderizado tem 12 rótulos.
    const oitoMeses = JSON.parse(JSON.stringify(fluxo)) as Record<string, unknown>;
    (oitoMeses.janela_12m as Record<string, unknown>).janela_meses = 8;
    (oitoMeses.janela_12m as Record<string, unknown>).n_meses = 8;
    renderFluxoCard(fx, oitoMeses as FluxoCaixaSummary);
    const text = contextText();
    expect(text).toContain("No gráfico: 12 meses");
    expect(text).toContain("os últimos 8 meses documentados");
  });

  it("simetria full: sem janela_12m o texto declara todo o período", () => {
    renderFluxoCard(dataSemJanela12m(), fluxoSemJanela12m());
    const text = contextText();
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain("36 meses");
    expect(text).toContain(V.receitaFull);
    expect(text).not.toContain(V.receita12m);
  });

  it("isPrint (superfície do PDF) usa o mesmo agregado de 12m", () => {
    mockUseIsPrint.mockReturnValue(true);
    renderFluxoCard(fx, fluxo);
    const text = contextText();
    expect(text).toContain("os últimos 12 meses documentados");
    expect(text).toContain(V.receita12m);
    expect(text).not.toContain(V.receitaFull);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 4. Site: builder `fluxo_mensal` — o texto que produção renderiza
// ─────────────────────────────────────────────────────────────────────

describe("deriveChartConclusion('fluxo_mensal') — único texto que mensaliza S2", () => {
  it("cita a mensalização da janela sob rótulo da janela", () => {
    const text = deriveChartConclusion("fluxo_mensal", fx) ?? "";
    expect(text).toContain("os últimos 12 meses documentados");
    expect(text).toContain(V.receita12m);
    expect(text).toContain(V.despesa12m);
    expect(text).not.toContain(V.receitaFull);
    expect(text).not.toContain(V.despesaFull);
    // Discriminador de 20×: `fluxo_liquido` é TOTAL do intervalo.
    expect(text).not.toContain(V.totalIntervalo12m);
  });

  it("não deriva 'quanto sobra' da despesa BRUTA nem cita taxa de poupança", () => {
    // `receita − despesa_mensal_media` = 11.000/mês, número que não fecha com a
    // taxa ex-aporte de 25% exibida no hero (ADR-333) e que o frontend não pode
    // fabricar (ADR-090). "Quanto sobra" vive só no KPI de folga.
    const text = deriveChartConclusion("fluxo_mensal", fx) ?? "";
    expect(text).not.toContain(brl0(11_000));
    expect(text).not.toMatch(/sobra|taxa de poupança|capacidade/i);
  });

  it("renderiza no card via prop conclusion (caminho de produção)", () => {
    renderFluxoCard(fx, fluxo);
    expect(conclusionText()).toContain(V.receita12m);
  });

  it("simetria full: rotula todo o período", () => {
    const text = deriveChartConclusion("fluxo_mensal", dataSemJanela12m()) ?? "";
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain(V.receitaFull);
    expect(text).not.toContain(V.receita12m);
  });

  it("bloco de 12m sem contagem: cláusula sem número de meses", () => {
    // Mesmo defeito do hero, no outro portador: a prosa não pode afirmar
    // "12 meses documentados" quando o payload declara só o NOME da janela.
    // Prova de mutação: restaurar `rotulo.meses ?? 12` derruba o segundo assert.
    const semContagem = JSON.parse(JSON.stringify(fx)) as JanelaFixture;
    const bloco = semContagem.fluxo_caixa.janela_12m as Record<string, unknown>;
    delete bloco.janela_meses;
    delete bloco.n_meses;
    const text = deriveChartConclusion("fluxo_mensal", semContagem as ReportAnalysisData) ?? "";
    expect(text).toContain("Sobre a janela documentada:");
    expect(text).not.toMatch(/\d+\s+(?:mês|meses)/);
    expect(text).toContain(V.receita12m);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 5. Site: SECTION_SUMMARIES.S2 (deriveSectionSummary)
// ─────────────────────────────────────────────────────────────────────

describe("deriveSectionSummary('S2') — mesma fonte, com rótulo", () => {
  it("cita a receita recorrente de 12m com rótulo", () => {
    const text = deriveSectionSummary("S2", fx) ?? "";
    expect(text).toMatch(/12 meses/);
    expect(text).toContain(V.receita12m);
    expect(text).not.toContain(V.receitaFull);
  });

  it("simetria full: rotula todo o período", () => {
    const text = deriveSectionSummary("S2", dataSemJanela12m()) ?? "";
    expect(text).toMatch(/todo o período/i);
    expect(text).toContain(V.receitaFull);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 6. Fatias do donut — soma correta; o TEXTO do card é da [[A40.l15]]
// ─────────────────────────────────────────────────────────────────────

describe("<DespesasDoughnutChart /> — fatias somam a janela renderizada, ex-aporte", () => {
  it("aporte não entra no total das fatias (delta com e sem o dataset)", () => {
    // Único assert desta lane sobre o donut. O par (valor, rótulo) do TEXTO do
    // card saiu para a [[A40.l15]]: o desenho é ex-aporte da janela e a conclusão
    // cita a base full, e decidir qual base cada texto declara é domínio.
    // O delta é o que prova que o filtro rodou — a fixture usava o label
    // "Aporte em investimentos", que `isAporteInvestimentoKey` não casa e o
    // produtor nunca emite (`fluxo_caixa_enricher.py:404` ⇒ "Aporte
    // Investimento"): com ele, o aporte entrava no donut e nada falhava.
    render(<DespesasDoughnutChart fluxo={fluxo} />);
    const comAporte = document.querySelector(".chart-context")?.textContent ?? "";
    expect(comAporte).toContain(brl0(828_000));
    expect(comAporte).not.toContain(brl0(972_000));
    expect(comAporte).toContain("3 categorias");
  });
});

// ─────────────────────────────────────────────────────────────────────
// 7. Invariante de SEÇÃO — o assert que pega B1 (composição, não unidade)
// ─────────────────────────────────────────────────────────────────────

/** Cards cujo TEXTO derivado saiu do escopo desta lane para a [[A40.l15]]: os
 * dois citam bases legitimamente distintas (janela ex-aporte por ADR-333 vs
 * bruto de todo o período) e escolher qual base cada texto declara é decisão de
 * domínio, não de render.
 *
 * Exclusão **nominal**: card novo não entra aqui sem alguém escrever o nome
 * dele, e renomear um card devolve o texto ao invariante (falha alta, não
 * silenciosa). O `it` abaixo garante que os dois títulos existem na seção —
 * senão a exclusão viraria vácuo sem ninguém notar. */
const CARDS_DA_L15 = [
  "Despesas por Categoria",
  "Receita vs Despesa — Mês a Mês",
] as const;

function tituloDoCard(card: Element): string {
  return card.querySelector("h3")?.textContent?.trim() ?? "";
}

/** Cópia da seção sem os cards herdados pela [[A40.l15]]. */
function noEscopoDaLane(root: HTMLElement): HTMLElement {
  const copia = root.cloneNode(true) as HTMLElement;
  for (const card of [...copia.querySelectorAll("section")]) {
    if ((CARDS_DA_L15 as readonly string[]).includes(tituloDoCard(card))) card.remove();
  }
  return copia;
}

/** Toda taxa de poupança exibida na seção. A canônica vive no hero (S1); S2 não
 * emite taxa própria — emitir é reintroduzir a segunda taxa divergente. */
function taxasDePoupanca(root: HTMLElement): string[] {
  const texto = root.textContent ?? "";
  const encontradas = new Set<string>();
  for (const re of [
    /\((\d{1,3}[.,]\d)% da receita\)/g,
    /taxa de poupança[^.]{0,40}?(\d{1,3}[.,]\d)\s*%/gi,
  ]) {
    for (const m of texto.matchAll(re)) encontradas.add(m[1]);
  }
  return [...encontradas];
}

/** Valores citados como mensalização (`X/mês`) na seção. */
function valoresPorMes(root: HTMLElement): string[] {
  const texto = root.textContent ?? "";
  return [...texto.matchAll(/R\$\s*([\d.]+(?:,\d+)?)\s*\/mês/g)].map((m) => m[1]);
}

/** Todo texto derivado (context/conclusion) renderizado na seção — varredura,
 * não enumeração de site: componente novo entra aqui sem ninguém lembrar. */
function textosDerivados(root: HTMLElement): string[] {
  return [
    ...root.querySelectorAll(
      "[data-chart-conclusion], [data-chart-context], .chart-context",
    ),
  ].map((n) => n.textContent ?? "");
}

describe("<S2FluxoCaixaSection /> — invariante de seção (ADR-306 D1)", () => {
  it("os dois cards herdados pela l15 estão na seção (exclusão não é vácuo)", () => {
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    const titulos = [...container.querySelectorAll("section")].map(tituloDoCard);
    for (const nome of CARDS_DA_L15) expect(titulos).toContain(nome);
    // E a cópia sem eles perdeu exatamente 2 cards.
    const restantes = [...noEscopoDaLane(container).querySelectorAll("section")];
    expect(restantes.length).toBe(
      [...container.querySelectorAll("section")].length - CARDS_DA_L15.length,
    );
  });

  it("no escopo da lane, S2 não emite taxa de poupança própria (a canônica é a do hero)", () => {
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    // `ReceitaDespesaMensalChart` continua emitindo "Taxa de poupança de 15,6%"
    // (média da série inteira, sem rótulo) — herdado pela [[A40.l15]] junto com
    // o resto do texto daquele card.
    expect(taxasDePoupanca(noEscopoDaLane(container))).toEqual([]);
  });

  it("no escopo da lane, toda mensalização vem da janela canônica", () => {
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    const porMes = valoresPorMes(noEscopoDaLane(container));
    expect(porMes.length).toBeGreaterThan(0);
    // Só `janela_12m.receita_recorrente_mensal` e `.despesa_mensal_media`.
    const permitidos = new Set(["92.000", "81.000"]);
    expect(porMes.filter((v) => !permitidos.has(v))).toEqual([]);
    // Bloco full mensalizado (42.667 / 36.000 / 40.000) nunca aparece como /mês.
    expect(porMes).not.toContain("42.667");
    expect(porMes).not.toContain("36.000");
    expect(porMes).not.toContain("40.000");
  });

  it("o total do intervalo de 12m nunca é citado como valor mensal", () => {
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    expect(valoresPorMes(noEscopoDaLane(container))).not.toContain("228.000");
  });

  it("um único número de 'quanto sobra' na seção, e é rotulado", () => {
    // F6: três leituras de sobra na mesma seção (capacidade, sem-destino, folga)
    // foram medidas como irreconciliáveis pelo leitor. Sobra = KPI de folga.
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    const texto = container.textContent ?? "";
    expect(texto).toContain("Folga mensal");
    expect(texto).not.toMatch(/sem destino definido|capacidade de poupança/);
    expect(badges(container)).toContain("últimos 12 meses documentados");
  });

  it("todo texto que cita agregado declara a base", () => {
    const { container } = render(<S2FluxoCaixaSection data={fx} />);
    const textos = textosDerivados(noEscopoDaLane(container)).filter((t) =>
      CITA_AGREGADO.test(t),
    );
    expect(textos.length).toBeGreaterThan(0);
    // Varredura, não enumeração: componente novo cai aqui sem ninguém lembrar.
    // `CLAUSULA_DE_BASE` é a MESMA const do spec de render (Playwright).
    for (const t of textos) expect(t).toMatch(CLAUSULA_DE_BASE);
  });

  it("`No gráfico: N meses` não satisfaz o invariante (é o desenho, não a base)", () => {
    // Prova de mutação da cláusula: enquanto `No gráfico:` esteve em
    // `CLAUSULA_DE_BASE`, este texto passava — declarando quantas barras foram
    // desenhadas e nada sobre a base do R$ citado. Reintroduzir a alternativa no
    // regex derruba este assert.
    const soODesenho = "No gráfico: 12 meses (25/01 a 25/12). Receita média de R$ 42.667/mês.";
    expect(CITA_AGREGADO.test(soODesenho)).toBe(true);
    expect(soODesenho).not.toMatch(CLAUSULA_DE_BASE);
    // E o texto que só descreve o desenho, sem citar agregado, não é sujeito do
    // invariante — não há número a rotular.
    expect(CITA_AGREGADO.test("No gráfico: 3 meses (25/10 a 25/12).")).toBe(false);
  });

  it("janela de UM mês documentado: a forma singular também satisfaz o invariante", () => {
    // `janela_meses = 1` é o valor do substrato versionado
    // (`dogfood_view_model.json`) — a forma singular é a que produção emite, e
    // era exatamente a que faltava no regex deste teste (a do E2E a tinha).
    // Sem "mês documentado" na cláusula, a conclusão do `fluxo_mensal`
    // ("Sobre o último mês documentado: …") derruba este assert.
    const umMes = JSON.parse(JSON.stringify(fx)) as JanelaFixture;
    const bloco = umMes.fluxo_caixa.janela_12m as Record<string, unknown>;
    bloco.janela_meses = 1;
    bloco.n_meses = 1;
    const { container } = render(
      <S2FluxoCaixaSection data={umMes as ReportAnalysisData} />,
    );
    const textos = textosDerivados(noEscopoDaLane(container));
    expect(textos.some((t) => /o último mês documentado/.test(t))).toBe(true);
    expect(textos.some((t) => /meses documentados/.test(t))).toBe(false);
    for (const t of textos.filter((t) => CITA_AGREGADO.test(t))) {
      expect(t).toMatch(CLAUSULA_DE_BASE);
    }
  });
});

// ─────────────────────────────────────────────────────────────────────
// 8. Site: ConsumoConscienteCard (duas bases, dois rótulos IMPRESSOS)
// ─────────────────────────────────────────────────────────────────────

describe("<ConsumoConscienteCard /> — bases declaradas em texto impresso", () => {
  it("KPI de pontuais usa o acumulado full (D6), coerente com a prosa do E5", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    const dl = document.querySelector("dl")?.textContent ?? "";
    expect(dl).toContain(V.pontuaisFull);
    expect(dl).not.toContain(V.pontuais12m);
    expect(dl).toContain("20,8");
  });

  it("rótulo de janela é texto IMPRESSO, não tooltip", () => {
    // I5: tooltip é `title=`/portal com hover — nenhum dos dois sai no PDF,
    // medido no PDF real. O rótulo tem de estar no DOM impresso.
    render(<ConsumoConscienteCard consumo={consumo} />);
    expect(badges()).toEqual([
      "todo o período documentado",
      "todo o período documentado",
      "últimos 12 meses documentados",
      "últimos 12 meses documentados",
    ]);
  });

  it("cada KPI carrega o rótulo da SUA base (histórico vs janela da folga)", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    const termos = [...document.querySelectorAll("dt")].map((t) => t.textContent ?? "");
    expect(termos[0]).toContain("Gastos pontuais");
    expect(termos[0]).toContain("todo o período documentado");
    expect(termos[2]).toContain("Folga mensal");
    expect(termos[2]).toContain("últimos 12 meses documentados");
  });

  it("escopo da LISTA é declarado (toggle próprio, default 3M)", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    const escopo =
      document.querySelector("[data-consumo-tabela-escopo]")?.textContent ?? "";
    expect(escopo).toContain("Lista: últimos 3M");
  });

  it("sem janela declarada: folga/teto ficam sem rótulo inventado", () => {
    const semJanela = { ...consumo, janela: undefined, janela_meses: undefined };
    render(<ConsumoConscienteCard consumo={semJanela} />);
    expect(badges()).toEqual([
      "todo o período documentado",
      "todo o período documentado",
    ]);
  });

  it("janela irpf_<ano> rotula folga/teto como ano-base, não como período completo", () => {
    // I1: o rótulo vem do CAMPO `janela` (D2 criou o campo justamente para a UI
    // não inferir a base pela posição do bloco).
    render(
      <ConsumoConscienteCard
        consumo={{ ...consumo, janela: "irpf_2024", janela_meses: 12 }}
      />,
    );
    expect(badges().slice(2)).toEqual([
      "ano-base IRPF 2024",
      "ano-base IRPF 2024",
    ]);
  });
});

// ─────────────────────────────────────────────────────────────────────
// 9. Site: hero KPI Taxa de Poupança (bloco `ratios`, ADR-306 D2)
// ─────────────────────────────────────────────────────────────────────

describe("<HeroKpiGrid /> — taxa de poupança com rótulo impresso", () => {
  const ratios = fx.ratios as unknown as RatiosData;

  function renderHero(r: RatiosData) {
    return render(
      <HeroKpiGrid
        patrimonio={undefined}
        reserva={undefined}
        ratios={r}
        goals={undefined}
        score={undefined}
      />,
    );
  }

  it("imprime o rótulo ao lado do número (tooltip é só complemento)", () => {
    const { container } = renderHero(ratios);
    expect(container.textContent).toContain("25,0%");
    expect(badges(container)).toEqual(["últimos 12 meses documentados"]);
    // O tooltip continua existindo, mas não é o portador da base.
    expect(container.querySelector('[title*="12 meses documentados"]')).not.toBeNull();
  });

  it("lê o campo `janela` (vocabulário D2), não `janela_referencia`", () => {
    const { container } = renderHero(ratios);
    expect(container.querySelector('[title*="2025-01 a 2025-12"]')).toBeNull();
    expect(badges(container)[0]).not.toContain("2025-01");
  });

  it("payload com só `janela_referencia` (período) não inventa rótulo", () => {
    const { container } = renderHero({
      taxa_poupanca_recorrente_pct: 25,
      janela_referencia: "2026-01 a 2026-01",
      janela_n_meses: 1,
    });
    expect(badges(container)).toEqual([]);
    expect(container.querySelector('[title*="Média mensal calculada"]')).toBeNull();
  });

  it("`janela: 12m` sem `janela_meses`: nenhum dígito de contagem no texto", () => {
    // Defeito medido no render: `rotulo.meses ?? 12` imprimia "últimos 12 meses
    // documentados" a partir de um payload que não afirma contagem nenhuma —
    // precisão fabricada, a mesma classe que esta sprint persegue. O vocabulário
    // D2 nomeia a janela; a contagem vive na chave irmã `janela_meses`.
    // Prova de mutação: restaurar o `?? 12` derruba os dois asserts abaixo.
    const { container } = renderHero({
      taxa_poupanca_recorrente_pct: 25,
      janela: "12m",
    });
    expect(badges(container)).toEqual(["janela documentada"]);
    expect(badges(container)[0]).not.toMatch(/\d/);
    const tooltip = container.querySelector('[title*="Média mensal"]');
    expect(tooltip?.getAttribute("title")).toBe(
      "Média mensal calculada sobre a janela documentada.",
    );
  });

  it("percentual serializado como string não derruba o KPI", () => {
    // Substrato real: `ratios.taxa_poupanca_recorrente_pct = "50.000000"`.
    const { container } = renderHero({
      taxa_poupanca_recorrente_pct: "50.000000" as unknown as number,
      janela: "12m",
      janela_meses: 1,
    });
    expect(container.textContent).toContain("50,0%");
  });

  it("rótulo de 1 mês documentado concorda artigo, numeral e particípio", () => {
    // `janela_meses: 1` é o valor do substrato versionado — "os últimos 1 mês
    // documentados" era bug alimentado por dado (I10). Assert de igualdade
    // exata: `toContain("1 mês documentado")` passava com a string quebrada.
    const { container } = renderHero({
      taxa_poupanca_recorrente_pct: 50,
      janela: "12m",
      janela_meses: 1,
    });
    expect(badges(container)).toEqual(["último mês documentado"]);
    // Escopado ao tooltip de janela: o card de Investível tem `title` próprio.
    const tooltip = container.querySelector('[title*="Média mensal"]');
    expect(tooltip?.getAttribute("title")).toBe(
      "Média mensal calculada sobre o último mês documentado.",
    );
  });

  it("o KPI é filho direto do grid (sem wrapper que quebre o stretch)", () => {
    // I6: `<span title style={{display:block}}>` virava o grid item e o card
    // parava de esticar (134px em item de 171px), além de produzir span > div.
    const { container } = renderHero(ratios);
    const grid = container.firstElementChild as HTMLElement;
    expect(grid.className).toContain("grid");
    [...grid.children].forEach((child) => expect(child.tagName).toBe("DIV"));
    expect(container.querySelector("span > div")).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────────
// 10. Superfície de print — o rótulo tem de IMPRIMIR
// ─────────────────────────────────────────────────────────────────────

describe("superfície de print (PDF)", () => {
  beforeEach(() => mockUseIsPrint.mockReturnValue(true));

  it("KPIs de consumo mantêm base e rótulo impresso", () => {
    render(<ConsumoConscienteCard consumo={consumo} />);
    expect(document.querySelector("dl")?.textContent).toContain(V.pontuaisFull);
    expect(badges()).toContain("todo o período documentado");
    expect(badges()).toContain("últimos 12 meses documentados");
  });

  it("hero imprime o rótulo da taxa (o PDF não tem hover)", () => {
    const { container } = render(
      <HeroKpiGrid
        patrimonio={undefined}
        reserva={undefined}
        ratios={fx.ratios as unknown as RatiosData}
        goals={undefined}
        score={undefined}
      />,
    );
    expect(badges(container)).toEqual(["últimos 12 meses documentados"]);
  });
});
