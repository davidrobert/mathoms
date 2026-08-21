/**
 * PD-6 (RV6-22) — os contadores client-side sobre HTTP REAL (MSW + `apiFetch`).
 *
 * O par com `reportDataQualityMeasured.test.tsx` é deliberado: lá o fetch é
 * mockado no módulo (determinismo do render do banner), aqui a rejeição nasce
 * do produtor de verdade — status HTTP → `apiFetch` → `ApiError`. Sem esta
 * metade, o teste provaria só "promise rejeitada vira unknown" e não que o
 * caminho de rede que o PDF percorre chega lá.
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { server } from "../../mocks/server";
import { useNeedsReviewCount } from "@/components/report/hooks/useNeedsReviewCount";
import { useParecerRetidoCount } from "@/components/report/hooks/useParecerRetidoCount";
import type { MeasuredCount } from "@/components/report/utils/measuredCount";

const API = "/api/v1";

function label(value: MeasuredCount): string {
  return value.state === "ok" ? `ok:${value.count}` : value.state;
}

/** Lê o probe já no estado TERMINAL — `loading` não é resposta.
 *
 * `findByTestId` resolve na PRESENÇA do elemento, e o probe existe desde o
 * primeiro render (ainda em `loading`): ele não espera o fetch, espera o
 * `<span>`. A asserção de texto rodava então uma única vez, sobre o DOM
 * daquele instante, com a folga de um único `setTimeout(0)` que o
 * `asyncWrapper` do RTL concede — margem ZERO, um `delay(0)` no handler do
 * MSW já derruba. Sob contenção de CI o fetch não cabe na janela e a leitura
 * sai `loading`: foi o que quebrou o run 32500293097 (attempt 1) e passou no
 * attempt 2, mesmo SHA, sem mudança nenhuma.
 *
 * Esperar o estado terminal e só então comparar mantém a polaridade do
 * `MeasuredCount` (o valor exato é afirmado, não relaxado) e separa os dois
 * defeitos no relatório de falha: valor terminal errado falha na hora, com o
 * valor; hook que nunca assenta falha por timeout em `loading`.
 */
async function probeState(): Promise<string> {
  const probe = await screen.findByTestId("probe");
  await waitFor(() => expect(probe).not.toHaveTextContent(/^loading$/));
  return probe.textContent ?? "";
}

function NeedsReviewProbe({ workspaceId }: { workspaceId?: string }) {
  return (
    <span data-testid="probe">{label(useNeedsReviewCount(workspaceId))}</span>
  );
}

function ParecerProbe({ reportId }: { reportId?: string }) {
  return (
    <span data-testid="probe">
      {label(useParecerRetidoCount("ws-1", reportId))}
    </span>
  );
}

/** Um documento incerto (needs_review) + um resolvido — contagem esperada 1. */
const DOCS_FIXTURE = {
  documents: [
    {
      id: "doc-incerto",
      status: "ready",
      needs_review: true,
      classification_confidence: 0.42,
      pipeline_e2_extract_ok: false,
    },
    {
      id: "doc-ok",
      status: "ready",
      needs_review: false,
      classification_confidence: 0.98,
      pipeline_e2_extract_ok: true,
    },
  ],
};

const PARECER_COM_RETENCAO = {
  outcome: "entregue_com_retencao",
  retention: { items_dropped_count: 2 },
};

describe("useNeedsReviewCount", () => {
  it("500 no endpoint de documentos → unknown, nunca zero", async () => {
    server.use(
      http.get(`${API}/workspaces/:workspaceId/documents`, () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    render(<NeedsReviewProbe workspaceId="ws-1" />);
    expect(await probeState()).toBe("unknown");
  });

  it("200 → ok com a contagem medida", async () => {
    server.use(
      http.get(`${API}/workspaces/:workspaceId/documents`, () =>
        HttpResponse.json(DOCS_FIXTURE),
      ),
    );
    render(<NeedsReviewProbe workspaceId="ws-1" />);
    expect(await probeState()).toBe("ok:1");
  });

  it("sem workspace não há o que medir → unknown", async () => {
    render(<NeedsReviewProbe />);
    expect(await probeState()).toBe("unknown");
  });
});

describe("useParecerRetidoCount", () => {
  it("404 é ausência por construção (nunca gerado / free) → ok:0", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:workspaceId/reports/:reportId/planner-review`,
        () => HttpResponse.json({ detail: "not found" }, { status: 404 }),
      ),
    );
    render(<ParecerProbe reportId="report-1" />);
    expect(await probeState()).toBe("ok:0");
  });

  it("500 é falha de medição → unknown", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:workspaceId/reports/:reportId/planner-review`,
        () => HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    render(<ParecerProbe reportId="report-1" />);
    expect(await probeState()).toBe("unknown");
  });

  it("200 com retenção parcial → ok com a contagem", async () => {
    server.use(
      http.get(
        `${API}/workspaces/:workspaceId/reports/:reportId/planner-review`,
        () => HttpResponse.json(PARECER_COM_RETENCAO),
      ),
    );
    render(<ParecerProbe reportId="report-1" />);
    expect(await probeState()).toBe("ok:2");
  });

  it("sem `reportId` o sinal está desligado por construção → ok:0", async () => {
    render(<ParecerProbe />);
    expect(await probeState()).toBe("ok:0");
  });
});
