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
    { moeda: "USD", valor_brl: 900, share_pct: 90, pct_total_cambial: 90 },
    { moeda: "EUR", valor_brl: 100, share_pct: 10, pct_total_cambial: 10 },
  ],
  detalhes: [],
} as ExposicaoCambialData;

/** Resposta que o endpoint V2 devolve hoje para esse workspace. */
const V2_VAZIO = {
  workspace_id: "ws-1",
  total_brl: "0.00",
  pct_investivel_financeiro: 0,
  por_moeda: [],
  tier: "empty",
  ativos_contribuintes: [],
  source_run_id: "run-1",
  computed_at: "2026-08-11T18:34:09Z",
};

describe("ExposicaoCambialCard — precedência V1 x V2", () => {
  it("mostra as duas moedas quando o V2 não responde (fallback V1)", () => {
    V2_STATE.data = null;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("EUR")).toBeInTheDocument();
    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
  });

  it("não pode apagar a exposição real quando o V2 responde vazio", () => {
    V2_STATE.data = V2_VAZIO;
    render(<ExposicaoCambialCard data={V1} workspaceId="ws-1" />);

    // Hoje FALHA: o V2 vazio vence e o card afirma ausência de exposição.
    expect(screen.queryByText(/100% denominado em real/)).not.toBeInTheDocument();
    expect(screen.getByText("USD")).toBeInTheDocument();
    expect(screen.getByText("EUR")).toBeInTheDocument();
  });
});
