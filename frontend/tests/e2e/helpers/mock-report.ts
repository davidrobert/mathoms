import type { Page, Route } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { ReportResponse } from "@/lib/api";

/**
 * Mock helper para rota /reports/[id] sem backend real.
 *
 * Lane `report-a11y-finalize` (resíduo F12, ADR-129): a11y/tab-order
 * gates não devem depender do pipeline E2E completo. `page.route()`
 * intercepta `/api/v1/**` antes de bater no backend; combinado com
 * token injetado em localStorage, o shell renderiza com fixture
 * sintética.
 *
 * Fixtures cobrem variância de dado real para evitar regressões pontuais
 * (overflow, anchoring, long strings) que escapam ao baseline `medium`:
 *
 * - `medium`         — densidade média, zero PII (fixture canônica)
 * - `long-strings`   — nomes/descrições longas (Top 15 ativos, dívidas)
 * - `large-values`   — totais grandes (R$ XX.XXX.XXX) → overflow em cards
 * - `sparse-data`    — datasets curtos / cauda longa (period anchoring)
 * - `degraded`       — A28.l9: todos os degrades de qualidade ativos
 *                      (nao_identificado 23%, premissas 10/10 fallback,
 *                      Monte Carlo sobre fallback, 7 imóveis pendentes)
 * - `janela-divergente` — A40.l3 (ADR-306 D1): 36 meses onde o bloco `full`
 *                      diverge de `fluxo_caixa.janela_12m` por valor
 *                      detectável (sobra mensal R$ 4.000 vs R$ 11.000;
 *                      gastos pontuais R$ 250.000 vs R$ 96.000). Só traz
 *                      `narrativas.perfil_familia` **de propósito**: uma
 *                      `narrativas.fluxo_mensal`/`S2` sombrearia
 *                      `deriveChartConclusion` (precedência absoluta em
 *                      `S2FluxoCaixaSection`) e o assert de janela viraria
 *                      tautologia.
 */
export type FixtureName =
  | "medium"
  | "long-strings"
  | "large-values"
  | "sparse-data"
  | "degraded"
  | "janela-divergente";

const FIXTURES_DIR = join(__dirname, "..", "fixtures", "reports");

export const MOCK_WORKSPACE_ID = "ws-fixture";
export const MOCK_REPORT_ID = "report-fixture-medium";

/** Resposta do `GET .../planner-review`. Ver `PLANNER_REVIEW_NOT_GENERATED`. */
export interface PlannerReviewStub {
  status: number;
  body: unknown;
}

/** Default do roteador: parecer ausente → `<ParecerEmptyState/>` (ADR-199). */
export const PLANNER_REVIEW_NOT_GENERATED: PlannerReviewStub = {
  status: 404,
  body: { detail: "not_generated_yet" },
};

/** A40.l22 — os 2 desfechos de degradação, como stub pronto.
 *
 * O contrato do `plannerReview` é o `PlannerReviewStub` cru (#1281), para o
 * smoke poder injetar qualquer payload. Estes dois são atalhos nomeados: o
 * DOM dos estados de degradação é longo, e replicá-lo em 4 specs garantiria
 * deriva entre eles.
 */
export type PlannerReviewFixture = "retido" | "parcial";

interface MockOptions {
  reportId?: string;
  workspaceId?: string;
  fixture?: FixtureName;
  /**
   * Sobrescreve a resposta do parecer. Spec que asserta a S_parecer renderizada
   * passa o payload aqui em vez de depender de um relatório real na listagem —
   * sem isso o assert só alcança o estado vazio.
   */
  plannerReview?: PlannerReviewStub;
}

/** Contagem única em toda a superfície de teste: seção, banner, `/pipeline` e
 *  PDF têm de dizer o MESMO número, então ele não pode ser literal solto. */
export const PARECER_ITENS_RETIDOS = 2;

function parecerContent() {
  const meta = {
    tier_at_generation: "premium",
    persona_hash: "a".repeat(64),
    manifest_version: "1.0",
    schema_version: "1.0",
    model_id: "anthropic/claude-sonnet-4",
    generated_at: "2026-08-07T12:00:00Z",
    gated_counts: {
      pontos_fortes: 0,
      riscos: 0,
      sugestoes_execucao: 0,
      sugestoes_taticas: 0,
      sugestoes_estrategicas: 0,
      metricas: 0,
      notas_metodologicas: 0,
    },
  };
  const risco = (titulo: string) => ({
    severidade: "Média",
    titulo,
    descricao: "Descrição sintética, sem valor monetário nem identificador.",
    tema_canonico: "Alocação",
    evidencia: null,
    evidencia_path: null,
    ancoras: [],
    section_id: "S4",
    confianca: "media",
  });
  // Uma sugestão por prioridade: `PRIORIDADE_TONE` tem 3 membros e o rótulo P1
  // era o que falhava contraste. Fixture com um só valor deixaria o gate de
  // a11y verde por AUSÊNCIA do caso, não por correção (A40.l22).
  const sugestao = (prioridade: string, acao: string) => ({
    prioridade,
    acao,
    impacto_qualitativo: "Reduz exposição concentrada sem alterar a liquidez.",
    tema_canonico: "Alocação",
    confianca: "media",
    section_id: "S4",
    suggestion_dedup_key: prioridade.toLowerCase().repeat(32).slice(0, 64),
    impacto_estimado: null,
    evidencia_path: null,
    ancoras: [],
  });
  return {
    version: "1.0",
    diagnostico_geral:
      "Família com reserva adequada e concentração de ativos acima do recomendado.",
    pontos_fortes: [
      {
        titulo: "Reserva de emergência coberta",
        descricao: "Liquidez suficiente para o horizonte declarado.",
        tema_canonico: "Saúde de balanço",
        section_id: "S1",
      },
    ],
    // Uma de cada severidade que renderiza no top-5: Crítica e Média cobrem os
    // dois `textToken` distintos de `SEVERIDADE_TONE`.
    riscos: [
      { ...risco("Concentração de ativos acima do teto"), severidade: "Crítica" },
      risco("Cobertura de seguro insuficiente"),
    ],
    sugestoes_execucao: [sugestao("P0", "Redistribuir 15% da posição concentrada")],
    sugestoes_taticas: [sugestao("P1", "Revisar o capital segurado do titular")],
    sugestoes_estrategicas: [sugestao("P2", "Avaliar previdência complementar")],
    metricas: [],
    notas_metodologicas: [],
    meta,
  };
}

function parecerResponse(kind: PlannerReviewFixture) {
  const parcial = kind === "parcial";
  return {
    id: "planner-review-fixture",
    workspace_id: MOCK_WORKSPACE_ID,
    pipeline_run_id: "run-fixture",
    status: "Gerado",
    persona_hash: "a".repeat(64),
    manifest_version: "1.0",
    schema_version: "1.0",
    model_id: "anthropic/claude-sonnet-4",
    tier_at_generation: "premium",
    items_shown_count: parcial ? 3 : 0,
    items_gated_count: 0,
    cost_usd_cents: 42,
    created_at: "2026-08-07T12:00:00Z",
    published_at: null,
    superseded_at: null,
    supersedes_id: null,
    superseded_by_id: null,
    immutable_hash: null,
    outcome: parcial ? "entregue_com_retencao" : "retido",
    retention: {
      reason: "parecer.citacao_nao_confirmada",
      items_dropped_count: parcial ? PARECER_ITENS_RETIDOS : 0,
    },
    content: parcial ? parecerContent() : null,
  };
}

function loadFixture(name: FixtureName): unknown {
  const raw = readFileSync(join(FIXTURES_DIR, `${name}.json`), "utf-8");
  return JSON.parse(raw);
}

function buildReportResponse(
  reportId: string,
  workspaceId: string,
): ReportResponse {
  return {
    id: reportId,
    workspace_id: workspaceId,
    title: "Relatório Sintético — Abril 2026",
    period: "2026-04",
    score: 82,
    patrimonio_liquido: 1200000,
    created_at: "2026-04-25T12:00:00Z",
    pipeline_run_id: "run-fixture",
    source_document_count: 3,
    source_document_ids: ["doc-1", "doc-2", "doc-3"],
    consumed_document_count: 3,
    consumed_document_ids: ["doc-1", "doc-2", "doc-3"],
    has_analysis_data: true,
    run_outcome: "complete",
    premissas_snapshot: null,
  };
}

function buildWorkspace(workspaceId: string) {
  return {
    id: workspaceId,
    name: "Workspace Fixture",
    family_surname: "Sintético",
    role: "owner" as const,
    joined_at: "2026-01-01T00:00:00Z",
  };
}

function buildUser() {
  return {
    id: "user-fixture",
    email: "fixture@test.com",
    full_name: "Fixture User",
    is_active: true,
    is_superuser: false,
    created_at: "2026-01-01T00:00:00Z",
  };
}

/**
 * Configura `page.route()` para responder a todas as chamadas necessárias
 * para renderizar /reports/[id] com fixture sintética. Roteador é tolerante
 * — endpoints não previstos retornam 200 com `[]` ou `{}` para não quebrar
 * o shell.
 */
export async function mockReportPage(
  page: Page,
  opts: MockOptions = {},
): Promise<{ workspaceId: string; reportId: string }> {
  const workspaceId = opts.workspaceId ?? MOCK_WORKSPACE_ID;
  const reportId = opts.reportId ?? MOCK_REPORT_ID;
  const data = loadFixture(opts.fixture ?? "medium");
  const plannerReview = opts.plannerReview ?? PLANNER_REVIEW_NOT_GENERATED;

  // Token para passar pelo auth gate da página
  await page.addInitScript(() => {
    localStorage.setItem("fin_token", "fixture-token");
  });

  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api\/v1/, "");

    if (path === "/auth/me") return json(route, buildUser());
    if (path === "/me/workspaces") {
      return json(route, {
        workspaces: [buildWorkspace(workspaceId)],
        total: 1,
      });
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}`) {
      return json(route, buildReportResponse(reportId, workspaceId));
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/data`) {
      return json(route, data);
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/notes`) {
      return json(route, {
        id: "notes-1",
        report_id: reportId,
        content: "",
        author_user_id: null,
        updated_at: "2026-04-25T00:00:00Z",
      });
    }
    if (path === `/workspaces/${workspaceId}/reports/${reportId}/kanban`) {
      return json(route, { items: [] });
    }
    if (path.includes("/notifications")) {
      return json(route, { notifications: [], total: 0, unread_count: 0 });
    }
    if (path.includes("/transactions")) {
      return json(route, {
        transactions: [],
        total: 0,
        page: 1,
        page_size: 500,
        summary: {
          total_in: 0,
          total_out: 0,
          net: 0,
          by_category: {},
          by_member: {},
        },
      });
    }
    // ADR-153 — `useSuggestions` (consumido por `<SuggestionCalloutInline/>`
    // dentro do AppLayout) faz `setSuggestions(resp.suggestions)` sem
    // guard. Sem esta rota, o catch-all `{}` produz `suggestions = undefined`
    // e o `.filter()` na seção dispara ErrorBoundary, derrubando o
    // `<article data-report-ready>` em **todas** as fixture variants
    // (regressão entrou junto com o spec smoke fixture-variants em #157).
    if (path.match(/\/workspaces\/[^/]+\/suggestions$/)) {
      return json(route, { suggestions: [], total: 0 });
    }

    // ADR-136 — `useDecisions` em `PlanoDeAcaoSection` faz
    // `setDecisions(resp.decisions)` sem guard. Mesmo padrão de
    // failure mode: catch-all `{}` produz `decisions = undefined` e
    // `.length`/`.filter()` em `DecisionTable` dispara ErrorBoundary.
    if (path.match(/\/workspaces\/[^/]+\/decisions$/)) {
      return json(route, { decisions: [], total: 0 });
    }

    // ADR-148 — `useConsumoPontuais` consome este endpoint em S2 (card
    // ConsumoConscienteCard). Sem esta rota, o catch-all `{}` quebrava
    // o shape e disparava ErrorBoundary, derrubando o `<article>` inteiro
    // — bug que fazia 28 baselines visuais skipar com `count===0` para
    // `section#S1[data-report-section]` (regressão pós-commit ba29df1).
    if (path.includes("/reports/consumo-pontuais")) {
      return json(route, {
        period: "3m",
        date_from: "2026-01-01",
        date_to: "2026-04-25",
        items: [],
        total: 0,
        total_valor: 0,
      });
    }
    if (path.includes("/dashboard")) {
      return json(route, {});
    }
    // ADR-153/161 — `useSuggestions` (SuggestionCalloutInline em S2/S7/...)
    // e `getSuggestionsSummary`/`countSuggestions` (banners em /plano).
    // Catch-all `{}` quebrava `resp.suggestions.filter()` em
    // SuggestionCalloutInline → ErrorBoundary global → snapshot tests
    // skipam silenciosamente, smoke spec falha em `data-report-ready`.
    if (path.endsWith("/suggestions") || path.includes("/suggestions?")) {
      return json(route, { suggestions: [], total: 0 });
    }
    if (path.endsWith("/suggestions/count")) {
      return json(route, { count: 0 });
    }
    if (path.endsWith("/suggestions/summary")) {
      return json(route, { count: 0, max_severity: null, by_category: {} });
    }
    // ADR-136 — `useDecisions` em PlanoDeAcaoSection. Mesmo motivo dos
    // `/suggestions`: catch-all sem `decisions` quebrava `.filter()`.
    if (path.endsWith("/decisions") || path.includes("/decisions?")) {
      return json(route, { decisions: [], total: 0 });
    }

    // ADR-187 (#185) — `MonthClosedBanner` chama
    // `/reports/{period}/publication`; backend retorna `null` quando mês
    // está aberto (default). Sem esta rota, o catch-all `{}` produz
    // `publication = {}` (truthy), banner renderiza com "Invalid Date" e
    // 1-2px de reflow afetam canvas dos charts → baselines visuais
    // quebram (ratio 0.03-0.04 px diff em S2/APP-A/APP-B etc).
    if (path.match(/\/reports\/\d+\/publication$/)) {
      return json(route, null);
    }

    // ADR-199 — `usePlannerReview` em SParecerSection. Em snapshots visuais
    // default não há parecer gerado; retornar 404 faz o componente
    // renderizar `<ParecerEmptyState />` (estado canônico do
    // not_generated). Catch-all `{}` quebrava com "content.meta undefined".
    // A40.l22 — `plannerReview` troca o desfecho servido. O `ReportShell`
    // consome o MESMO endpoint pelo banner, então a opção governa as duas
    // superfícies com uma rota só.
    if (path.match(/\/reports\/[^/]+\/planner-review$/)) {
      return json(route, plannerReview.body, plannerReview.status);
    }

    return json(route, {});
  });

  return { workspaceId, reportId };
}

/** Espera o shell estar pronto (data-report-ready="true" no <article>). */
export async function waitForReportReady(page: Page): Promise<void> {
  await page.waitForSelector('[data-report-ready="true"]', { timeout: 15_000 });
}

/** Stub do desfecho de degradação, para `mockReportPage({ plannerReview })`. */
export function plannerReviewStub(kind: PlannerReviewFixture): PlannerReviewStub {
  return { status: 200, body: parecerResponse(kind) };
}
