/**
 * Unit tests — TransferConfigEditor (ADR-133b)
 *
 * Cobre: load → render → add → remove → save (PUT chamado com body atualizado).
 * MSW intercepta /workspaces/:id/config/transfer.
 */
import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import TransferConfigEditor from "@/app/(app)/config/transfer/TransferConfigEditor";
import { server } from "../mocks/server";

const API = "/api/v1";

const baseConfig = {
  patterns_pix: ["PIX TRANSF DAVID"],
  patterns_global: [],
  patterns_bank_specific: { c6bank: ["Pagamento"] },
  recipients: ["DAVID ROBERT"],
};

describe("<TransferConfigEditor /> @ADR-133b", () => {
  it("carrega config existente e renderiza recipients + patterns", async () => {
    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json(baseConfig),
      ),
    );

    render(<TransferConfigEditor />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("DAVID ROBERT")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("PIX TRANSF DAVID")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Pagamento")).toBeInTheDocument();
    expect(screen.getByText("c6bank")).toBeInTheDocument();
  });

  it("adicionar recipient marca botão Salvar como habilitado", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({
          patterns_pix: [],
          patterns_global: [],
          patterns_bank_specific: {},
          recipients: [],
        }),
      ),
    );

    render(<TransferConfigEditor />);

    const saveBtn = await screen.findByTestId("save-transfer-config");
    expect(saveBtn).toBeDisabled();

    const input = screen.getByTestId("recipients-new-input");
    await user.type(input, "MARIANA TEIXEIRA");
    await user.click(screen.getByTestId("recipients-add"));

    expect(screen.getByDisplayValue("MARIANA TEIXEIRA")).toBeInTheDocument();
    expect(saveBtn).toBeEnabled();
  });

  it("save chama PUT com body atualizado e mostra mensagem de sucesso", async () => {
    const user = userEvent.setup();
    let receivedBody: unknown = null;

    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({
          patterns_pix: [],
          patterns_global: [],
          patterns_bank_specific: {},
          recipients: [],
        }),
      ),
      http.put(`${API}/workspaces/:wsId/config/transfer`, async ({ request }) => {
        receivedBody = await request.json();
        return HttpResponse.json(receivedBody as Record<string, unknown>);
      }),
    );

    render(<TransferConfigEditor />);

    await screen.findByTestId("recipients-new-input");
    await user.type(screen.getByTestId("recipients-new-input"), "PIX TESTE B-UI");
    await user.click(screen.getByTestId("recipients-add"));

    await user.click(screen.getByTestId("save-transfer-config"));

    await waitFor(() => {
      expect(receivedBody).toEqual({
        patterns_pix: [],
        patterns_global: [],
        patterns_bank_specific: {},
        recipients: ["PIX TESTE B-UI"],
      });
    });

    expect(
      screen.getByText(/próximo relatório gerado já usará as novas regras/i),
    ).toBeInTheDocument();
  });

  it("remover recipient atualiza a lista", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({
          ...baseConfig,
          recipients: ["DAVID ROBERT", "MARIANA TEIXEIRA"],
        }),
      ),
    );

    render(<TransferConfigEditor />);

    await screen.findByDisplayValue("DAVID ROBERT");
    expect(screen.getByDisplayValue("MARIANA TEIXEIRA")).toBeInTheDocument();

    await user.click(screen.getByTestId("recipients-remove-1"));

    expect(screen.queryByDisplayValue("MARIANA TEIXEIRA")).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("DAVID ROBERT")).toBeInTheDocument();
  });

  it("adicionar banco novo cria bloco com 0 patterns", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({
          patterns_pix: [],
          patterns_global: [],
          patterns_bank_specific: {},
          recipients: [],
        }),
      ),
    );

    render(<TransferConfigEditor />);

    const newBankInput = await screen.findByTestId("bank-new-input");
    await user.type(newBankInput, "itau");
    await user.click(screen.getByTestId("bank-add"));

    expect(screen.getByTestId("bank-itau")).toBeInTheDocument();
    expect(screen.getByText("itau")).toBeInTheDocument();
  });

  it("erro do backend exibe mensagem inline", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({
          patterns_pix: [],
          patterns_global: [],
          patterns_bank_specific: {},
          recipients: [],
        }),
      ),
      http.put(`${API}/workspaces/:wsId/config/transfer`, () =>
        HttpResponse.json({ detail: "permissão negada" }, { status: 403 }),
      ),
    );

    render(<TransferConfigEditor />);

    await screen.findByTestId("recipients-new-input");
    await user.type(screen.getByTestId("recipients-new-input"), "X");
    await user.click(screen.getByTestId("recipients-add"));
    await user.click(screen.getByTestId("save-transfer-config"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/permissão negada/i);
    });
  });
});
