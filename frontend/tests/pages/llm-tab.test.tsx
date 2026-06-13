/**
 * Integration tests — LLMTab (config /llm)
 *
 * Regressão: com config existente, trocar só o modelo deve habilitar SALVAR
 * e o PUT deve omitir api_key (backend reusa a chave criptografada).
 */
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "../mocks/server";

import LLMTab from "@/app/(app)/config/LLMTab";

const existingConfig = {
  id: "cfg-1",
  provider: "anthropic",
  api_key_masked: "sk-a****7890",
  api_key_status: "valid",
  model_name: "claude-sonnet-4-20250514",
  model_status: "ok",
  max_tokens: 4096,
  temperature: 0.1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const modelsResponse = {
  provider: "anthropic",
  models: [
    { value: "claude-sonnet-4-20250514", label: "Claude Sonnet 4", source: "curated", pricing_known: true },
    { value: "claude-opus-4-8", label: "Claude Opus 4.8", source: "curated", pricing_known: true },
  ],
  default_model: "claude-opus-4-8",
  fetched_dynamic: false,
};

function mockLLMEndpoints(config: typeof existingConfig | null) {
  server.use(
    http.get("/api/v1/workspaces/:workspaceId/config/llm", () => HttpResponse.json(config)),
    http.get("/api/v1/workspaces/:workspaceId/config/llm/tier", () =>
      HttpResponse.json({
        tier: config ? "premium" : "free",
        has_llm_config: Boolean(config),
      }),
    ),
    http.get("/api/v1/workspaces/:workspaceId/config/llm/models", () =>
      HttpResponse.json(modelsResponse),
    ),
  );
}

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

describe("LLMTab — habilitação do Salvar", () => {
  it("config existente: trocar só o modelo habilita Salvar e PUT omite api_key", async () => {
    mockLLMEndpoints(existingConfig);
    let putBody: Record<string, unknown> | null = null;
    server.use(
      http.put("/api/v1/workspaces/:workspaceId/config/llm", async ({ request }) => {
        putBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          ...existingConfig,
          model_name: putBody.model_name,
        });
      }),
    );

    const user = userEvent.setup();
    render(<LLMTab />);

    const saveButton = await screen.findByRole("button", { name: /Salvar/ });
    expect(saveButton).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Digitar manualmente" }));
    const modelInput = screen.getByLabelText("Modelo");
    await user.clear(modelInput);
    await user.type(modelInput, "claude-opus-4-8");

    expect(saveButton).toBeEnabled();
    await user.click(saveButton);

    await waitFor(() => expect(putBody).not.toBeNull());
    expect(putBody).toMatchObject({
      provider: "anthropic",
      model_name: "claude-opus-4-8",
    });
    expect(putBody).not.toHaveProperty("api_key");
  });

  it("config existente: voltar ao modelo salvo desabilita Salvar de novo", async () => {
    mockLLMEndpoints(existingConfig);
    const user = userEvent.setup();
    render(<LLMTab />);

    const saveButton = await screen.findByRole("button", { name: /Salvar/ });
    await user.click(screen.getByRole("button", { name: "Digitar manualmente" }));
    const modelInput = screen.getByLabelText("Modelo");
    await user.clear(modelInput);
    await user.type(modelInput, "claude-opus-4-8");
    expect(saveButton).toBeEnabled();

    await user.clear(modelInput);
    await user.type(modelInput, existingConfig.model_name);
    expect(saveButton).toBeDisabled();
  });

  it("sem config: Salvar exige chave de API", async () => {
    mockLLMEndpoints(null);
    const user = userEvent.setup();
    render(<LLMTab />);

    const saveButton = await screen.findByRole("button", { name: /Salvar/ });
    expect(saveButton).toBeDisabled();

    await user.type(screen.getByLabelText("Chave de API"), "sk-ant-nova-chave");
    expect(saveButton).toBeEnabled();
  });
});
