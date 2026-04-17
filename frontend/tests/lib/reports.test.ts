/**
 * Unit tests — F9 · ADR-076 · F0.5
 *
 * Cobre getReport, getReportData, hasAnalysisData flag, erros de rede.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";

import {
  ApiError,
  clearToken,
  getReport,
  getReportData,
  listReports,
  setToken,
} from "@/lib/api";
import { server } from "../mocks/server";

const API = "/api";

beforeEach(() => {
  clearToken();
  setToken("test-token");
});

const WS = "ws-1";

describe("listReports — ReportResponse inclui has_analysis_data", () => {
  it("retorna campo has_analysis_data no payload", async () => {
    const result = await listReports(WS);
    expect(result.reports[0]).toHaveProperty("has_analysis_data");
    expect(typeof result.reports[0].has_analysis_data).toBe("boolean");
  });

  it("retorna score e patrimonio_liquido (novos campos)", async () => {
    const result = await listReports(WS);
    const report = result.reports[0];
    expect(report).toHaveProperty("score");
    expect(report).toHaveProperty("patrimonio_liquido");
  });
});

describe("getReport", () => {
  it("retorna report por id", async () => {
    const result = await getReport(WS, "report-1");
    expect(result.id).toBe("report-1");
    expect(result.has_analysis_data).toBe(true);
  });

  it("lança ApiError 404 quando não encontrado", async () => {
    await expect(getReport(WS, "nonexistent")).rejects.toBeInstanceOf(ApiError);
    await expect(getReport(WS, "nonexistent")).rejects.toMatchObject({ status: 404 });
  });
});

describe("getReportData — E5 analysis JSON (F0.4+F0.5)", () => {
  it("retorna payload com chaves top-level do E5", async () => {
    const data = await getReportData(WS, "report-1");
    expect(data.periodo_dados).toBe("202601-202604");
    expect(data.patrimonio).toBeDefined();
    expect(data.score).toBeDefined();
    expect(data.score?.valor).toBe(82);
    expect(data._report_lineage?.source_document_count).toBe(1);
  });

  it("lança 404 para relatório inexistente", async () => {
    await expect(getReportData(WS, "nonexistent")).rejects.toMatchObject({ status: 404 });
  });

  it("lança 404 com mensagem específica para relatório pré-F9", async () => {
    // Override handler: report existe mas sem data
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/legacy-report/data`, () =>
        HttpResponse.json(
          { detail: "Relatório pré-F9, sem JSON de análise." },
          { status: 404 },
        ),
      ),
    );
    try {
      await getReportData(WS, "legacy-report");
      throw new Error("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(404);
      expect((err as ApiError).message).toContain("pré-F9");
    }
  });

  it("propaga 500 se JSON corrompido no backend", async () => {
    server.use(
      http.get(`${API}/workspaces/${WS}/reports/corrupted/data`, () =>
        HttpResponse.json(
          { detail: "JSON de análise corrompido" },
          { status: 500 },
        ),
      ),
    );
    await expect(getReportData(WS, "corrupted")).rejects.toMatchObject({ status: 500 });
  });
});
