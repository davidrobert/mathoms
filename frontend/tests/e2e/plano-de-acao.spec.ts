/**
 * A7.2a · ADR-136 — Plano de Ação (Decision aggregate)
 *
 * Cenário @critical: cria Decision via API → abre relatório → seção
 * "plano_de_acao" lista a Decision → CTA "Marcar como executada" muda
 * status para Executado (refetch) → reload mantém.
 *
 * Não usa o pipeline real; só valida o fluxo HTTP do aggregate isolado
 * (cria via POST, marca via POST /execute, lê via GET).
 */
import { test, expect } from "@playwright/test";
import { ensureLoggedIn, userForWorker } from "./helpers/auth";

test.describe("Plano de Ação — Decision aggregate @critical", () => {
  test("cria via API → marca executada via API → estado persistido", async ({
    page,
    request,
  }, info) => {
    await ensureLoggedIn(page, request, info);

    const token = await page.evaluate(() =>
      localStorage.getItem("fin_token"),
    );
    expect(token).toBeTruthy();

    // Descobre o workspace do usuário corrente
    const meResp = await request.get("/api/v1/me/workspaces", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(meResp.ok()).toBeTruthy();
    const me = await meResp.json();
    const wsId =
      me?.workspaces?.[0]?.id ?? me?.[0]?.id ?? me?.workspace_id ?? null;
    if (!wsId) {
      test.skip(true, "workspace fixture indisponível");
      return;
    }

    const u = userForWorker(info);
    const code = `D${(info.parallelIndex + 90).toString().padStart(2, "0")}`;

    // POST cria Decision
    const createResp = await request.post(
      `/api/v1/workspaces/${wsId}/decisions`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          code,
          title: `E2E ${u.full_name} fictício`,
          status: "Decidido",
          amount_brl: "1000.00",
        },
      },
    );
    expect(createResp.status(), await createResp.text()).toBe(201);
    const created = await createResp.json();
    expect(created.code).toBe(code);
    expect(created.status).toBe("Decidido");

    // POST execute → status vira Executado
    const execResp = await request.post(
      `/api/v1/workspaces/${wsId}/decisions/${created.id}/execute`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: { note: "e2e-marca-executada" },
      },
    );
    expect(execResp.ok(), await execResp.text()).toBeTruthy();
    const executed = await execResp.json();
    expect(executed.status).toBe("Executado");
    expect(executed.executed_at).not.toBeNull();

    // GET valida persistência
    const getResp = await request.get(
      `/api/v1/workspaces/${wsId}/decisions/${created.id}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(getResp.ok()).toBeTruthy();
    const fetched = await getResp.json();
    expect(fetched.status).toBe("Executado");
  });
});
