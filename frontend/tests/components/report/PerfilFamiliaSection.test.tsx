/**
 * `PerfilFamiliaSection` — bloco de identidade fundido (ex-PerfilFamiliaCard +
 * ex-TitularesCard, ADR-259 §4): seção do shell `id="perfil"`, roster documental
 * (nome civil → CPF, ordenado por `order`, rótulo pelo `role` do cadastro) sobre
 * a narrativa `left` do E5.N. Matriz de vazio: só roster, só narrativa, ou
 * null quando ambos faltam.
 *
 * `right` morreu na emenda ADR-356 (A40.l43): publicava os KPIs do hero e a
 * regra que a exigia não-vazia produzia veredito incondicional.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";

import { PerfilFamiliaSection } from "@/components/report/PerfilFamiliaSection";
import { server } from "../../mocks/server";

const API = "/api/v1";
const WS = "ws-1";

const LEFT = "<p>Titular, 40 anos, é engenheiro.</p>\n<p>Cônjuge, CLT.</p>";
const NARRATIVAS = { perfil_familia: { left: LEFT } };

interface MemberStub {
  id: string;
  key: string;
  full_name: string;
  short_name: string;
  cpf_masked: string | null;
  role: string;
  order: number;
  accounts: unknown[];
}

function member(
  partial: Partial<MemberStub> & Pick<MemberStub, "id" | "full_name">,
): MemberStub {
  return {
    key: partial.id,
    short_name: partial.full_name,
    cpf_masked: "***.***.789-09",
    role: "titular",
    order: 0,
    accounts: [],
    ...partial,
  };
}

const WORKSPACE_BASE = {
  id: WS,
  name: "WS",
  family_surname: null,
  joined_at: "2026-01-01T00:00:00Z",
};

function mockMembersAndRole(
  members: MemberStub[],
  role: "owner" | "member" | "viewer",
) {
  server.use(
    http.get(`${API}/workspaces/${WS}/config/members`, () =>
      HttpResponse.json({ members, total: members.length }),
    ),
    http.get(`${API}/me/workspaces`, () =>
      HttpResponse.json({ workspaces: [{ ...WORKSPACE_BASE, role }], total: 1 }),
    ),
  );
}

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

afterEach(() => server.resetHandlers());

describe("PerfilFamiliaSection", () => {
  it("renderiza h2 da seção + card personalizado com o sobrenome", async () => {
    mockMembersAndRole(
      [member({ id: "m1", full_name: "David Robert" })],
      "owner",
    );
    render(
      <PerfilFamiliaSection
        narrativas={NARRATIVAS}
        workspaceId={WS}
        familySurname="Ferreira"
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Perfil da Família" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "A Família Ferreira" }),
    ).toBeInTheDocument();
    expect(document.getElementById("perfil")).toHaveAttribute(
      "data-report-section",
    );
  });

  it("sem sobrenome (null/vazio) o título é 'A Família', sem espaço pendurado", () => {
    mockMembersAndRole([], "owner");
    render(
      <PerfilFamiliaSection
        narrativas={NARRATIVAS}
        workspaceId={WS}
        familySurname="  "
      />,
    );

    expect(
      screen.getByRole("heading", { level: 3, name: "A Família" }),
    ).toBeInTheDocument();
  });

  it("roster ordena por `order` e rotula pelo `role` — dependente nunca vira 'Titular'", async () => {
    mockMembersAndRole(
      [
        member({
          id: "m3",
          full_name: "Theo Ferreira",
          role: "filho",
          order: 2,
        }),
        member({
          id: "m1",
          full_name: "David Robert",
          role: "titular",
          order: 0,
        }),
        member({
          id: "m2",
          full_name: "Mariana Ferreira",
          role: "conjuge",
          order: 1,
        }),
      ],
      "owner",
    );
    render(<PerfilFamiliaSection narrativas={NARRATIVAS} workspaceId={WS} />);

    const terms = await screen.findAllByRole("term");
    expect(terms.map((t) => t.textContent)).toEqual([
      "David RobertTitular",
      "Mariana FerreiraCônjuge",
      "Theo FerreiraFilho(a)",
    ]);
    expect(within(terms[2]).queryByText("Titular")).toBeNull();
    expect(screen.queryByText("Titulares")).toBeNull();
  });

  it("membro sem CPF não entra no roster (o nome dele vive na narrativa)", async () => {
    mockMembersAndRole(
      [
        member({ id: "m1", full_name: "David Robert" }),
        member({
          id: "m2",
          full_name: "Mariana Ferreira",
          cpf_masked: null,
          role: "conjuge",
        }),
      ],
      "owner",
    );
    render(<PerfilFamiliaSection narrativas={NARRATIVAS} workspaceId={WS} />);

    await screen.findByText("David Robert");
    expect(screen.queryByText("Mariana Ferreira")).toBeNull();
  });

  it("sem narrativa, roster sozinho renderiza a seção", async () => {
    mockMembersAndRole(
      [member({ id: "m1", full_name: "David Robert" })],
      "owner",
    );
    render(<PerfilFamiliaSection narrativas={{}} workspaceId={WS} />);

    expect(await screen.findByText("David Robert")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Perfil da Família" }),
    ).toBeInTheDocument();
  });

  it("com narrativa e sem membro com CPF, renderiza só a prosa (sem <dl>)", async () => {
    mockMembersAndRole([], "owner");
    const { container } = render(
      <PerfilFamiliaSection narrativas={NARRATIVAS} workspaceId={WS} />,
    );

    expect(
      screen.getByText("Titular, 40 anos, é engenheiro."),
    ).toBeInTheDocument();
    await waitFor(() => expect(container.querySelector("dl")).toBeNull());
  });

  it("sem narrativa e com fetch falhando, a seção não renderiza nada", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/config/members`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
      http.get(`${API}/me/workspaces`, () =>
        HttpResponse.json({ workspaces: [], total: 0 }),
      ),
    );
    const { container } = render(
      <PerfilFamiliaSection narrativas={{}} workspaceId={WS} />,
    );

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("member/viewer não tem o botão 'Ver completo'", async () => {
    mockMembersAndRole(
      [member({ id: "m1", full_name: "David Robert" })],
      "viewer",
    );
    render(<PerfilFamiliaSection narrativas={{}} workspaceId={WS} />);

    await screen.findByText("David Robert");
    expect(
      screen.queryByRole("button", { name: /ver cpf completo/i }),
    ).toBeNull();
  });

  it("não emite tags <p> literais (parse, não dangerouslySetInnerHTML)", () => {
    mockMembersAndRole([], "owner");
    const { container } = render(
      <PerfilFamiliaSection narrativas={NARRATIVAS} workspaceId={WS} />,
    );
    expect(container.textContent).not.toContain("<p>");
  });

  it("ignora `right` de artefato antigo — a chave não é mais lida", () => {
    mockMembersAndRole([], "owner");
    render(
      <PerfilFamiliaSection
        narrativas={{
          perfil_familia: { left: LEFT, right: "<p>Meta de IF de R$ 5M.</p>" },
        }}
        workspaceId={WS}
      />,
    );
    expect(screen.getByText("Titular, 40 anos, é engenheiro.")).toBeInTheDocument();
    expect(screen.queryByText("Meta de IF de R$ 5M.")).not.toBeInTheDocument();
  });

  it("só `right` (artefato antigo, sem pessoas) não renderiza narrativa", async () => {
    mockMembersAndRole([], "owner");
    const { container } = render(
      <PerfilFamiliaSection
        narrativas={{ perfil_familia: { right: "<p>Meta de IF.</p>" } }}
        workspaceId={WS}
      />,
    );
    await waitFor(() => expect(container.firstChild).toBeNull());
  });

  // Nunca `grid` com um filho: coluna vazia em relatório financeiro lê como
  // "algo não carregou". ≤2 parágrafos não se partem ao meio.
  it("2 parágrafos ficam em 1 coluna; 3+ fluem em duas", () => {
    mockMembersAndRole([], "owner");
    const { container: curto } = render(
      <PerfilFamiliaSection narrativas={NARRATIVAS} workspaceId={WS} />,
    );
    expect(curto.querySelector("[data-perfil-prosa]")?.className).not.toContain(
      "columns-2",
    );

    const tres = "<p>Um.</p><p>Dois.</p><p>Três.</p>";
    const { container: longo } = render(
      <PerfilFamiliaSection
        narrativas={{ perfil_familia: { left: tres } }}
        workspaceId={WS}
      />,
    );
    expect(longo.querySelector("[data-perfil-prosa]")?.className).toContain(
      "sm:columns-2",
    );
  });
});
