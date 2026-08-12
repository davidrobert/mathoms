/**
 * Inbox de /acao — corte de foco, data e chips navegáveis (F5).
 *
 * O que estes testes guardam, medido no dogfood 2026-08-11: a página
 * mostrava 11 acionáveis como lista plana — a ordenação metodológica
 * existia e era invisível. Aqui a hierarquia é afirmada no DOM: grupo de
 * foco com 3, resto sob header próprio, agendadas/informativas fechadas.
 *
 * Os dois falsos-verdes que os asserts evitam: (1) contar cards no
 * documento inteiro passaria mesmo com a lista plana de volta — por isso
 * a contagem é por `[data-group]`; (2) afirmar "tem cor de severidade"
 * passaria com Tailwind literal — por isso o assert nomeia a var.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, within } from "@testing-library/react";

import { ActionStatusBar } from "@/app/(app)/acao/_components/ActionStatusBar";
import { InboxTab } from "@/app/(app)/acao/_components/InboxTab";
import { clearToken, setToken } from "@/lib/api";
import type { Suggestion } from "@/lib/api";
import { server } from "../mocks/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/acao",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const API = "/api/v1";
const WS_ID = "ws-1";

function sug(over: Partial<Suggestion> & { id: string }): Suggestion {
  return {
    workspace_id: WS_ID,
    report_id: null,
    section_id: "S2",
    kind: "reserva_insuficiente",
    category: null,
    origin: "llm",
    horizon: null,
    severity: "warning",
    title: `Sugestão ${over.id}`,
    rationale: "Motivo da sugestão.",
    amount_brl: null,
    dedup_key: `dedup-${over.id}`,
    status: "Pendente",
    accepted_decision_id: null,
    accepted_decision_code: null,
    dismissed_reason: null,
    accepted_at: null,
    dismissed_at: null,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...over,
  };
}

function serveSuggestions(list: Suggestion[]) {
  server.use(
    http.get(`${API}/workspaces/${WS_ID}/suggestions`, () =>
      HttpResponse.json({ suggestions: list, total: list.length }),
    ),
  );
}

function renderInbox() {
  return render(<InboxTab workspaceId={WS_ID} />);
}

/** Cards dentro de um grupo nomeado — contar no documento inteiro daria
 *  verde para a lista plana que este PR remove. */
function cardsInGroup(title: string): number {
  const group = document.querySelector(`[data-group="${title}"]`);
  return group ? group.querySelectorAll("[data-suggestion-id]").length : 0;
}

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

describe("InboxTab — grupos nomeados", () => {
  it("11 acionáveis: 3 em 'Decidir agora', 8 em 'Nesta rodada'", async () => {
    serveSuggestions(
      Array.from({ length: 11 }, (_, i) => sug({ id: `w${i}` })),
    );
    renderInbox();

    await screen.findByText("Decidir agora (3)");
    expect(screen.getByText("Nesta rodada (8)")).toBeInTheDocument();
    expect(cardsInGroup("Decidir agora")).toBe(3);
    expect(cardsInGroup("Nesta rodada")).toBe(8);
  });

  it("danger abre o grupo de foco mesmo entrando por último", async () => {
    serveSuggestions([
      ...Array.from({ length: 5 }, (_, i) => sug({ id: `w${i}` })),
      sug({ id: "urgente", severity: "danger", title: "Risco imediato" }),
    ]);
    renderInbox();

    const focus = await screen.findByText("Decidir agora (3)");
    const group = focus.closest("[data-group]") as HTMLElement;
    expect(within(group).getByText("Risco imediato")).toBeInTheDocument();
  });

  it("táticas/estratégicas vão para 'Agendadas', colapsada por default", async () => {
    serveSuggestions([
      sug({ id: "agora" }),
      sug({ id: "t", horizon: "tatica" }),
      sug({ id: "e", horizon: "estrategica" }),
    ]);
    renderInbox();

    const toggle = await screen.findByRole("button", {
      name: /Agendadas — táticas e estratégicas \(2\)/,
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Decidir agora (1)")).toBeInTheDocument();
    expect(screen.queryByText(/Nesta rodada/)).not.toBeInTheDocument();
  });

  it("informativas ficam colapsadas e fora dos grupos abertos", async () => {
    serveSuggestions([
      sug({ id: "a" }),
      sug({ id: "i1", severity: "info" }),
      sug({ id: "i2", severity: "info" }),
    ]);
    renderInbox();

    const toggle = await screen.findByRole("button", {
      name: /2 informativas/,
    });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(cardsInGroup("Decidir agora")).toBe(1);
  });

  it("sem agendadas nem informativas, os disclosures não aparecem", async () => {
    serveSuggestions([sug({ id: "a" })]);
    renderInbox();

    await screen.findByText("Decidir agora (1)");
    expect(
      screen.queryByRole("button", { name: /Agendadas/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /informativa/ }),
    ).not.toBeInTheDocument();
  });
});

describe("SuggestionCard — data, valor e tokens", () => {
  it("mostra o mês de origem em pt-BR curto", async () => {
    serveSuggestions([sug({ id: "a", created_at: "2026-08-01T00:00:00Z" })]);
    renderInbox();

    const meta = await screen.findByTestId("suggestion-created-month");
    expect(meta).toHaveTextContent("ago/2026");
  });

  it("valor monetário sai por <MonetaryValue/> (mono + tabular-nums)", async () => {
    serveSuggestions([sug({ id: "a", amount_brl: "9000.00" })]);
    renderInbox();

    const amount = await screen.findByTestId("suggestion-amount");
    expect(amount).toHaveTextContent("9.000,00");
    expect(amount).toHaveClass("font-mono", "tabular-nums");
  });

  it("severidade vem de token semântico, não de classe Tailwind literal", async () => {
    serveSuggestions([sug({ id: "a", severity: "warning" })]);
    renderInbox();

    await screen.findByText("Decidir agora (1)");
    const card = document.querySelector("[data-suggestion-id]") as HTMLElement;
    expect(card.className).not.toMatch(/border-l-(red|amber|sky)-\d{3}/);
    expect(card.style.borderLeftColor).toBe("var(--semantic-alert)");
  });

  it("o rótulo em caixa alta some fora do foco; o ícone mantém o sinal", async () => {
    serveSuggestions(Array.from({ length: 5 }, (_, i) => sug({ id: `w${i}` })));
    renderInbox();

    await screen.findByText("Nesta rodada (2)");
    // 3 no foco mantêm o texto; os 2 de "Nesta rodada" trocam por ícone
    // rotulado — o par (texto some, aria-label entra) é o aceite.
    expect(screen.getAllByText("Atenção")).toHaveLength(3);
    expect(
      screen.getAllByRole("img", { name: "Severidade: Atenção" }),
    ).toHaveLength(2);
  });

  it("o texto da severidade usa o par -on-tint (AA sobre o card)", async () => {
    serveSuggestions([sug({ id: "a", severity: "warning" })]);
    renderInbox();

    const label = await screen.findByText("Atenção");
    // Guarda a correção, não só a cor: `var(--semantic-alert)` puro mede
    // 2,06:1 sobre `--surface-card` em light. O gate `check_tint_contrast`
    // não alcança `style` inline, então o nome da var é a asserção.
    expect((label.parentElement as HTMLElement).style.color).toBe(
      "var(--semantic-alert-on-tint)",
    );
  });
});

describe("ActionStatusBar — chips navegáveis", () => {
  function serveCounts(pending: number, decided: number, upcoming: number) {
    server.use(
      http.get(`${API}/workspaces/${WS_ID}/suggestions/count`, () =>
        HttpResponse.json({ count: pending, status: "Pendente" }),
      ),
      http.get(`${API}/workspaces/${WS_ID}/decisions`, () =>
        HttpResponse.json({
          decisions: Array.from({ length: decided }, (_, i) => ({
            id: `d${i}`,
            status: "Decidido",
          })),
          total: decided,
        }),
      ),
      http.get(`${API}/workspaces/${WS_ID}/tasks/upcoming`, () =>
        HttpResponse.json({
          tasks: Array.from({ length: upcoming }, (_, i) => ({ id: `t${i}` })),
          total: upcoming,
        }),
      ),
    );
  }

  it("os 3 chips com valor > 0 são links para o destino real", async () => {
    serveCounts(4, 2, 1);
    render(<ActionStatusBar workspaceId={WS_ID} />);

    // O chip de tarefas resolve por último (useCurrentWorkspace busca
    // /me/workspaces antes de listar) — esperar por ele cobre os três.
    expect(
      await screen.findByRole("link", { name: /Tarefas/ }),
    ).toHaveAttribute("href", "/acao?tab=tarefas");
    expect(
      screen.getByRole("link", { name: /Sugestões pendentes/ }),
    ).toHaveAttribute("href", "/acao?tab=inbox");
    // Decisões vivem em /plano — o rótulo antigo prometia uma tab de /acao
    // que nunca existiu.
    expect(
      screen.getByRole("link", { name: /Decisões a executar em \/plano/ }),
    ).toHaveAttribute("href", "/plano");
  });

  it("chip zerado não vira link (não promete lista vazia)", async () => {
    serveCounts(0, 0, 0);
    render(<ActionStatusBar workspaceId={WS_ID} />);

    await screen.findByText("Sugestões pendentes");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
