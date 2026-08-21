/**
 * Handlers **opt-in** das seções do relatório — NÃO entram em `handlers.ts`.
 *
 * Renderizar `<ReportShell>` (ou `<MigratedSection>`) monta a árvore inteira de
 * seções, e cada uma dispara o próprio fetch: roster, sugestões, decisões,
 * parecer e exposição cambial. Um teste que só quer medir o shell (capa, ToC,
 * header) não declara nada sobre esses dados — e, sem override, as 5 requests
 * batiam no `onUnhandledRequest: "error"` do setup e rejeitavam **depois** da
 * asserção síncrona: 81 linhas de ruído por run, seções em estado de falha, e
 * nenhum sinal (medido em 2026-08-21 — as 18 asserções passam idênticas com e
 * sem estes handlers).
 *
 * As respostas são o **estado vazio declarado**, não payload rico: o workspace
 * do teste não tem membro, sugestão, decisão nem parecer. Assim a árvore
 * renderizada é a mesma de antes — só que por uma razão dita, não por uma
 * rejeição — e o teste de shell não fica acoplado ao conteúdo de seção.
 *
 * Opt-in de propósito: quem precisar de dado real chama `server.use(...)` com o
 * payload dele. Teste novo que esquecer o override continua falhando alto — é
 * o que um default permissivo em `handlers.ts` destruiria.
 */
import { http, HttpResponse } from "msw";

const API = "/api/v1";

/** Instale com `server.use(...reportSectionHandlers("ws-test"))`. */
export function reportSectionHandlers(workspaceId: string) {
  const ws = `${API}/workspaces/${workspaceId}`;
  return [
    http.get(`${ws}/config/members`, () =>
      HttpResponse.json({ members: [], total: 0 }),
    ),
    http.get(`${ws}/suggestions`, () =>
      HttpResponse.json({ suggestions: [], total: 0 }),
    ),
    http.get(`${ws}/decisions`, () =>
      HttpResponse.json({ decisions: [], total: 0 }),
    ),
    // 404 `not_generated_yet` é o estado de ausência que a seção sabe ler
    // (ADR-199); 200 com `content: null` não é forma que o endpoint emita.
    http.get(`${ws}/reports/:reportId/planner-review`, () =>
      HttpResponse.json(
        { detail: { code: "not_generated_yet", message: "sem parecer" } },
        { status: 404 },
      ),
    ),
    // `base_disponivel: false` + valores null — zero falso é infabricável
    // (contrato de `ExposicaoCambialV2Response`).
    http.get(`${ws}/cards/exposicao-cambial`, () =>
      HttpResponse.json({
        workspace_id: workspaceId,
        base_disponivel: false,
        total_brl: null,
        pct_investivel_financeiro: null,
        por_moeda: [],
        tier: null,
        alvo_moeda_forte_brl: null,
        ativos_contribuintes: [],
        catalog_version: 1,
        source_run_id: null,
        computed_at: "2026-04-17T12:00:00.000Z",
      }),
    ),
    http.get(`${ws}/cards/exposicao-cambial/overrides`, () =>
      HttpResponse.json({ workspace_id: workspaceId, overrides: [] }),
    ),
  ];
}
