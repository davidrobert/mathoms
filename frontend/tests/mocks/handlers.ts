/**
 * MSW handlers — F6.5 (sub-fase 6.5A.2)
 *
 * Defaults "happy path" para todos os endpoints declarados em `lib/api.ts`.
 * Tests específicos sobrescrevem via `server.use(...)`.
 *
 * Convenções:
 * - URLs absolutas com /api/v1/* (A6e.5 · ADR-108 — mesmo prefixo canônico
 *   que `API_BASE` em `src/lib/api/core.ts` e o rewrite em `next.config.ts`).
 * - Respostas usam fixtures (`./fixtures/`) ou factories (`../factories/`)
 *   para garantir shape alinhado com types do backend.
 * - Códigos não-2xx são opt-in via `server.use()` no teste — defaults nunca
 *   retornam erro pra evitar falsos vermelhos.
 *
 * Sync com backend: 6.5F.5 (MSW sync strategy) decide entre manual+lint vs
 * `openapi-typescript` codegen. Por enquanto, manual.
 */
import { http, HttpResponse } from "msw";

import { fixtures } from "./fixtures";

const API = "/api/v1";

export const handlers = [
  // ─── Auth ───
  http.post(`${API}/auth/register`, async () =>
    HttpResponse.json({ access_token: "test-token", token_type: "bearer" }),
  ),
  http.post(`${API}/auth/login`, async () =>
    HttpResponse.json({ access_token: "test-token", token_type: "bearer" }),
  ),
  http.get(`${API}/auth/me`, () => HttpResponse.json(fixtures.user)),
  http.get(`${API}/me/workspaces`, () =>
    HttpResponse.json({
      workspaces: [
        {
          id: "ws-1",
          name: "Workspace Teste",
          family_surname: "Teste",
          role: "owner",
          joined_at: "2026-04-15T12:00:00Z",
        },
      ],
      total: 1,
    }),
  ),
  http.get(`${API}/workspaces/:workspaceId/dashboard`, () =>
    HttpResponse.json(fixtures.dashboard),
  ),
  http.get(`${API}/workspaces/:workspaceId/notifications`, () =>
    HttpResponse.json({
      notifications: fixtures.notifications,
      total: fixtures.notifications.length,
      unread_count: fixtures.notifications.filter((n) => !n.is_read).length,
    }),
  ),

  // ─── Reports ───
  http.get(`${API}/reports`, () =>
    HttpResponse.json({ reports: fixtures.reports, total: fixtures.reports.length }),
  ),
  http.get(`${API}/reports/:id`, ({ params }) => {
    const report = fixtures.reports.find((r) => r.id === params.id);
    if (!report) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(report);
  }),
  http.get(`${API}/workspaces/:workspaceId/reports`, () =>
    HttpResponse.json({ reports: fixtures.reports, total: fixtures.reports.length }),
  ),
  http.get(`${API}/workspaces/:workspaceId/reports/:id`, ({ params }) => {
    const report = fixtures.reports.find((r) => r.id === params.id);
    if (!report) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(report);
  }),
  // F9 · ADR-076
  http.get(`${API}/workspaces/:workspaceId/reports/:id/data`, ({ params }) => {
    const report = fixtures.reports.find((r) => r.id === params.id);
    if (!report) return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    if (!report.has_analysis_data) {
      return HttpResponse.json(
        { detail: "Relatório pré-F9, sem JSON de análise." },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      periodo_dados: "202601-202604",
      patrimonio: { bruto: 1_000_000, liquido: 950_000 },
      score: { valor: 82, max: 100, classificacao: "Muito Bom" },
      _report_lineage: {
        pipeline_run_id: report.pipeline_run_id ?? null,
        source_document_count: 1,
        source_document_ids: ["doc-1"],
      },
    });
  }),

  // ─── Documents (legado `/api/v1/documents` + rotas por workspace usadas pelo cliente) ───
  http.get(`${API}/documents`, () =>
    HttpResponse.json({ documents: fixtures.documents, total: fixtures.documents.length }),
  ),
  http.get(`${API}/workspaces/:workspaceId/documents`, () =>
    HttpResponse.json({ documents: fixtures.documents, total: fixtures.documents.length }),
  ),
  http.post(`${API}/documents/upload`, () =>
    HttpResponse.json({
      documents: fixtures.documents,
      skipped_duplicates: [],
      total_uploaded: fixtures.documents.length,
      total_skipped: 0,
    }),
  ),
  http.post(`${API}/workspaces/:workspaceId/documents/upload`, () =>
    HttpResponse.json({
      documents: fixtures.documents,
      skipped_duplicates: [],
      total_uploaded: fixtures.documents.length,
      total_skipped: 0,
    }),
  ),
  http.delete(`${API}/documents/:id`, () => new HttpResponse(null, { status: 204 })),
  http.delete(`${API}/workspaces/:workspaceId/documents/:id`, () =>
    new HttpResponse(null, { status: 204 }),
  ),
  http.post(`${API}/documents/retry-unlock`, () => HttpResponse.json([])),
  http.post(`${API}/workspaces/:workspaceId/documents/retry-unlock`, () =>
    HttpResponse.json([]),
  ),
  http.post(`${API}/workspaces/:workspaceId/documents/reclassify`, () =>
    HttpResponse.json({ total: 1, updated: 0, skipped: 1, errors: 0 }),
  ),

  // ─── Vault ───
  http.get(`${API}/vault/passwords`, () =>
    HttpResponse.json({ passwords: fixtures.vaultPasswords, total: fixtures.vaultPasswords.length }),
  ),
  http.post(`${API}/vault/passwords`, () => HttpResponse.json(fixtures.vaultPasswords[0])),
  http.delete(`${API}/vault/passwords/:id`, () => new HttpResponse(null, { status: 204 })),

  // ─── Pipeline ───
  // Workspace-scoped (A29.l3 — PendingReviewQueue consulta runs+reviews a
  // partir de /documents; default sem run pausado → fila oculta).
  http.get(`${API}/workspaces/:workspaceId/pipeline/runs`, () =>
    HttpResponse.json({ runs: [fixtures.pipelineRun], total: 1 }),
  ),
  http.get(`${API}/workspaces/:workspaceId/pipeline/runs/:id/reviews`, () =>
    HttpResponse.json([]),
  ),
  http.post(
    `${API}/workspaces/:workspaceId/pipeline/runs/:id/resume`,
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.post(`${API}/pipeline/run`, () => HttpResponse.json(fixtures.pipelineRun)),
  http.get(`${API}/pipeline/runs`, () =>
    HttpResponse.json({ runs: [fixtures.pipelineRun], total: 1 }),
  ),
  http.get(`${API}/pipeline/runs/:id`, () => HttpResponse.json(fixtures.pipelineRun)),
  http.post(`${API}/pipeline/runs/:id/cancel`, () => new HttpResponse(null, { status: 204 })),
  http.post(`${API}/pipeline/runs/:id/resume`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${API}/pipeline/runs/:id/reviews`, () => HttpResponse.json([])),
  http.post(`${API}/pipeline/runs/:id/reviews/:reviewId`, () =>
    HttpResponse.json({ ok: true }),
  ),

  // ─── Config (workspace, members, categories, pipeline, institutions, layout, llm) ───
  http.get(`${API}/config/workspace`, () =>
    HttpResponse.json({ name: "Família Teste", family_surname: "Teste" }),
  ),
  http.patch(`${API}/config/workspace`, () =>
    HttpResponse.json({ name: "Família Teste", family_surname: "Teste" }),
  ),

  http.get(`${API}/config/members`, () =>
    HttpResponse.json({ members: fixtures.members, total: fixtures.members.length }),
  ),

  // ADR-215 P4/P5 — properties endpoints (default mock vazio).
  http.get(`${API}/workspaces/:workspaceId/properties`, ({ params }) =>
    HttpResponse.json({
      workspace_id: String(params.workspaceId),
      residencia_status: "undeclared",
      properties: [],
    }),
  ),
  http.put(
    `${API}/workspaces/:workspaceId/properties/:propertyId/classification`,
    ({ params }) =>
      HttpResponse.json({
        property_id: String(params.propertyId),
        titular_key: "titular",
        codigo_rfb: "12",
        descricao_sample: null,
        endereco_canonical: null,
        first_seen_year: 2024,
        low_confidence: false,
        classification: "residencia_principal",
        override_source: "user_manual",
        classification_set_at: new Date().toISOString(),
        suggested_score: null,
        suggested_residencia_principal: false,
      }),
  ),
  http.put(`${API}/workspaces/:workspaceId/residencia-status`, ({ params }) =>
    HttpResponse.json({
      workspace_id: String(params.workspaceId),
      status: "owned",
    }),
  ),

  http.post(`${API}/config/members`, () => HttpResponse.json(fixtures.members[0])),
  http.put(`${API}/config/members/:id`, () => HttpResponse.json(fixtures.members[0])),
  http.delete(`${API}/config/members/:id`, () => new HttpResponse(null, { status: 204 })),

  http.post(`${API}/config/members/:id/accounts`, () =>
    HttpResponse.json(fixtures.members[0].accounts[0]),
  ),
  http.delete(`${API}/config/members/:id/accounts/:accountId`, () =>
    new HttpResponse(null, { status: 204 }),
  ),

  http.get(`${API}/config/pipeline`, () => HttpResponse.json({})),
  http.put(`${API}/config/pipeline`, () => HttpResponse.json({})),

  http.get(`${API}/config/institutions`, () => HttpResponse.json({ config_json: {} })),
  http.put(`${API}/config/institutions`, () => HttpResponse.json({ config_json: {} })),

  http.get(`${API}/config/report-layout`, () => HttpResponse.json({ config_json: {} })),
  http.put(`${API}/config/report-layout`, () => HttpResponse.json({ config_json: {} })),

  // Transfer config (ADR-133) — também atendido em rota workspace-scoped
  http.get(`${API}/config/transfer`, () =>
    HttpResponse.json({
      patterns_pix: [],
      patterns_global: [],
      patterns_bank_specific: {},
      recipients: [],
    }),
  ),
  http.put(`${API}/config/transfer`, async ({ request }) => HttpResponse.json(await request.json())),
  http.get(`${API}/workspaces/:workspaceId/config/transfer`, () =>
    HttpResponse.json({
      patterns_pix: [],
      patterns_global: [],
      patterns_bank_specific: {},
      recipients: [],
    }),
  ),
  http.put(`${API}/workspaces/:workspaceId/config/transfer`, async ({ request }) =>
    HttpResponse.json(await request.json()),
  ),

  http.post(`${API}/config/import`, () => HttpResponse.json({ imported: [], total: 0 })),
  http.get(`${API}/config/export`, () =>
    HttpResponse.json({
      family_members: {},
      categorization: {},
      pipeline: {},
      institutions: {},
      report_layout: {},
    }),
  ),

  http.get(`${API}/config/llm`, () => HttpResponse.json(null)),
  http.put(`${API}/config/llm`, () => HttpResponse.json(fixtures.llmConfig)),
  http.delete(`${API}/config/llm`, () => new HttpResponse(null, { status: 204 })),
  http.post(`${API}/config/llm/test`, () =>
    HttpResponse.json({ success: true, message: "OK", model: "claude-opus-4-6" }),
  ),
  http.get(`${API}/config/llm/tier`, () =>
    HttpResponse.json({ tier: "free", has_llm_config: false }),
  ),

  // ─── Transactions ───
  http.get(`${API}/transactions`, () =>
    HttpResponse.json({
      transactions: fixtures.transactions,
      total: fixtures.transactions.length,
      page: 1,
      page_size: 50,
      summary: {
        total_receitas: 12500,
        total_despesas: -8400,
        saldo: 4100,
        count: fixtures.transactions.length,
        periodo_inicio: "2026-01-01",
        periodo_fim: "2026-04-30",
      },
    }),
  ),
  http.post(`${API}/transactions/:hash/override`, () =>
    HttpResponse.json({
      id: "ovr-1",
      transaction_hash: "h1",
      original_category: "alimentacao",
      new_category: "supermercado",
      notes: null,
      reviewed: false,
      created_at: new Date().toISOString(),
    }),
  ),
  http.delete(`${API}/transactions/:hash/override`, () =>
    new HttpResponse(null, { status: 204 }),
  ),

  // ─── Dashboard ───
  http.get(`${API}/dashboard`, () => HttpResponse.json(fixtures.dashboard)),

  // ─── Notifications ───
  http.get(`${API}/notifications`, () =>
    HttpResponse.json({
      notifications: fixtures.notifications,
      total: fixtures.notifications.length,
      unread_count: fixtures.notifications.filter((n) => !n.is_read).length,
    }),
  ),
  http.patch(`${API}/notifications/read`, () => new HttpResponse(null, { status: 204 })),
  http.delete(`${API}/notifications/:id`, () => new HttpResponse(null, { status: 204 })),

  // ─── Workspace-scoped defaults (A6e.5) ───
  // Paginas usam `/api/v1/workspaces/:id/...`; defaults aqui para cobrir o
  // happy-path das renderizações em teste. Tests específicos sobrescrevem
  // via `server.use()`.
  // Default "happy": meta IF configurada. Tests que cobrem onboarding sem
  // meta IF sobrescrevem com status 404 via `server.use()`.
  http.get(`${API}/workspaces/:workspaceId/goals/if`, () =>
    HttpResponse.json({
      id: "goal-test",
      type: "INDEPENDENCIA_FINANCEIRA",
      params_json: { inputs: {}, meta_version: 1 },
      derived_json: {},
      effective_from: "2026-01-01",
      effective_to: null,
      created_at: "2026-01-01T00:00:00.000Z",
      updated_at: "2026-01-01T00:00:00.000Z",
    }),
  ),
  http.get(`${API}/workspaces/:workspaceId/tasks/upcoming`, () =>
    HttpResponse.json({ tasks: [], total: 0 }),
  ),
  http.get(`${API}/workspaces/:workspaceId/transactions`, () =>
    HttpResponse.json({
      transactions: fixtures.transactions,
      total: fixtures.transactions.length,
      page: 1,
      page_size: 500,
      summary: {
        total_receitas: 12500,
        total_despesas: -8400,
        saldo: 4100,
        count: fixtures.transactions.length,
        periodo_inicio: "2026-01-01",
        periodo_fim: "2026-04-30",
      },
    }),
  ),

  // ─── Feature flags (default: all off — tests opt-in via server.use) ───
  http.get(`${API}/workspaces/:workspaceId/feature-flags`, () =>
    HttpResponse.json({
      flags: {
        learning_loop_enabled: false,
        tasks_v2_enabled: false,
      },
    }),
  ),

  // ─── Categorization Rules — learning loop (A12 P3/P4) ───
  http.post(
    `${API}/workspaces/:workspaceId/categorization/rules/preview`,
    () =>
      HttpResponse.json({
        matches_total: 12,
        matches_in_closed_months: 3,
        matches_with_manual_override: 1,
        matches_blocked_internal_transfers: 0,
        matches_amount_total_brl_cents: 284_000,
        matches_by_month: { "202604": 8, "202603": 4 },
        conflicts: [],
        low_risk: true,
        requires_user_confirmation: false,
        warnings: [],
      }),
  ),
  http.post(`${API}/workspaces/:workspaceId/categorization/rules`, () =>
    HttpResponse.json(
      {
        id: "rule-1",
        workspace_id: "ws-1",
        keyword: "MERCADO PAGO IFOOD",
        target_category: "Alimentação",
        priority: 100,
        enabled: true,
        origin_override_id: null,
        created_by_user_id: "user-1",
        applied_count: 8,
        revert_count_manual_edit: 0,
        revert_count_rule_disabled: 0,
        created_at: "2026-05-11T00:00:00Z",
        updated_at: "2026-05-11T00:00:00Z",
      },
      { status: 201 },
    ),
  ),
  http.get(
    `${API}/workspaces/:workspaceId/categorization/rules/:ruleId/apply-status`,
    () =>
      HttpResponse.json({
        rule_id: "rule-1",
        workspace_id: "ws-1",
        status: "completed",
        job_id: "job-1",
        started_at: null,
        completed_at: "2026-05-11T00:01:00Z",
        applied_count: 32,
        failed_count: 0,
        error: null,
      }),
  ),
];
