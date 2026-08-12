/**
 * Regressão — o V2 vazio não pode apagar a exposição cambial real do V1.
 *
 * Cenário do workspace de dogfood 5@5.com (report 7a7d7115): o payload E5 traz
 * caixa em USD e EUR, mas `compute_exposicao_cambial_v2` devolve `tier: "empty"`
 * porque lê chaves (`patrimonio_full` / `investimentos_atuais`) que o artefato
 * não emite. O card prefere o V2 sempre que ele responde — inclusive vazio — e
 * o usuário passa a ler "100% denominado em real".
 *
 * Valores sintéticos: o shape é o que importa, não o patrimônio real.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExposicaoCambialCard } from "@/components/report/cards/ExposicaoCambialCard";
import type { ExposicaoCambialData } from "@/types/report-analysis";

const V2_STATE = {
  data: null as unknown,
  overrides: [],
  loading: false,
  error: "",
  reload: vi.fn(),
  declare: vi.fn(),
  remove: vi.fn(),
};

vi.mock("@/hooks/useExposicaoCambialV2", () => ({
  useExposicaoCambialV2: () => V2_STATE,
}));

/** Payload V1 (E5) com duas moedas — shape idêntico ao artefato real. */
const V1: ExposicaoCambialData = {
  total_brl: 1000,
  pct_investivel_financeiro: 6.45,
  tier: "amarelo",
  por_moeda: [
    { moeda: "USD", valor_brl: 900, pct_total_cambial: 90 },
    { moeda: "EUR", valor_brl: 100, pct_total_cambial: 10 },
  ],
  detalhes: [],
};

/** V2 sem base de cálculo: valores `null`, nunca zero. */
const V2_SEM_BASE = {
  workspace_id: "ws-1",
  base_disponivel: false,
  total_brl: null,
  pct_investivel_financeiro: null,
  por_moeda: [],
  tier: null,
  alvo_moeda_forte_brl: null,
  ativos_contribuintes: [],
  source_run_id: "run-1",
  computed_at: "2026-08-11T18:34:09Z",
};

/** V2 com base e zero medido — aí a afirmação de ausência é legítima. */
const V2_ZERO_MEDIDO = {
  ...V2_SEM_BASE,
  base_disponivel: true,
  total_brl: "0.00",
  pct_investivel_financeiro: 0,
  tier: "empty",
  alvo_moeda_forte_brl: "129987.47",
};

describe("ExposicaoCambialCard — precedência V1 x V2", () => {
  it("mostra as duas moedas quando o V2 não responde (fallback V1)", () => {
    V2_STATE.data = null;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("EUR")).toBeInTheDocument();
    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
  });

  it("não apaga a exposição real quando o V2 responde sem base", () => {
    V2_STATE.data = V2_SEM_BASE;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("EUR")).toBeInTheDocument();
  });

  it("avisa que o controle de declarar lastro sumiu, sem alarmar sobre o número", () => {
    V2_STATE.data = V2_SEM_BASE;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.getByText(/opção de declarar lastro/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tentar de novo/i })).toBeInTheDocument();
  });

  it("sem V1 e sem base no V2, declara indisponibilidade em vez de afirmar ausência", () => {
    V2_STATE.data = V2_SEM_BASE;
    render(<ExposicaoCambialCard data={undefined} workspaceId="ws-1" />);

    expect(screen.getByText(/indisponível neste relatório/i)).toBeInTheDocument();
    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
    expect(screen.queryByText(/0,0%/)).not.toBeInTheDocument();
  });

  it("com base e zero medido, aí sim afirma ausência de exposição", () => {
    V2_STATE.data = V2_ZERO_MEDIDO;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.getByText(/Nenhum ativo com lastro fora do real/)).toBeInTheDocument();
    // A frase antiga era errada mesmo com base: fala de patrimônio, não do investível
    // financeiro, e de denominação, não de lastro econômico.
    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
  });

  it("formata percentual com vírgula decimal (pt-BR)", () => {
    V2_STATE.data = null;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.getByText(/6,5% ·/)).toBeInTheDocument();
    expect(screen.queryByText(/6\.5%/)).not.toBeInTheDocument();
  });
});
