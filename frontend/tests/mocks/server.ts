/**
 * MSW server (Node) — F6.5 (sub-fase 6.5A.2)
 *
 * Por que server (não worker)? Roda em Vitest+jsdom (Node), interceptando
 * `fetch`/XHR via `setupServer`. O equivalente browser (`setupWorker`) só
 * vale para dev real e não é usado aqui.
 *
 * Lifecycle: gerenciado em `tests/setup.ts` (listen/resetHandlers/close).
 *
 * Override por teste:
 *   import { server } from "../mocks/server";
 *   import { http, HttpResponse } from "msw";
 *   server.use(
 *     http.get("/api/v1/dashboard", () => HttpResponse.json({ ... }))
 *   );
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
