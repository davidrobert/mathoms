/** A6g.4 · T2 — barrel re-export do cliente HTTP. A fonte agora é
 * decomposta por domínio em `lib/api/<domain>.ts`. Consumidores devem
 * continuar a importar `@/lib/api`; over time podem migrar para o módulo
 * específico (`@/lib/api/tasks`, etc.) para reduzir superfície. */

export * from "./api/core";
export * from "./api/auth";
export * from "./api/authErrorMessages";
export * from "./api/reports";
export * from "./api/documents";
export * from "./api/vault";
export * from "./api/pipeline";
export * from "./api/config";
export * from "./api/transactions";
export * from "./api/dashboard";
export * from "./api/notifications";
export * from "./api/workspaces";
export * from "./api/goals";
export * from "./api/tasks";
export * from "./api/feature-flags";
export * from "./api/categorization-rules";
export * from "./api/decisions";
export * from "./api/risks";
export * from "./api/protections";
// Direção E · Onda 5 — re-export de suggestions usa nomes prefixados
// `SuggestionAggregate*` para não colidir com `SuggestionStatus` de
// `tasks.ts` (TaskSuggestion legado, lower-case `pending|approved|...`).
export * from "./api/suggestions";
export * from "./api/planner-review";
export * from "./api/workspace-notes";
