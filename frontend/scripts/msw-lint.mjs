#!/usr/bin/env node
/**
 * MSW sync lint — F6.5F.5 (ADR-069)
 *
 * Compara endpoints declarados em `frontend/tests/mocks/handlers.ts` com
 * `openapi.json` do backend. Falha CI se:
 *   - Backend tem endpoint que NÃO está em handlers.ts (drift "added")
 *   - handlers.ts tem endpoint que NÃO existe no OpenAPI (drift "removed")
 *
 * Uso:
 *   node scripts/msw-lint.mjs                # requer backend UP em :8000
 *   node scripts/msw-lint.mjs --spec path    # usa openapi.json em disco
 *   node scripts/msw-lint.mjs --allow-extra  # permite handlers extras (reduz gate)
 *
 * Integração CI: ver `.github/workflows/ci.yml` job `frontend-tests`.
 * Ver ADR-069 para rationale.
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const BACKEND_URL = process.env.FIN_BACKEND_URL ?? "http://127.0.0.1:8000";
const HANDLERS_PATH = resolve("tests/mocks/handlers.ts");

const args = process.argv.slice(2);
const specFlag = args.indexOf("--spec");
const specPath = specFlag >= 0 ? args[specFlag + 1] : null;
const allowExtra = args.includes("--allow-extra");

// ─── Parse handlers.ts ───────────────────────────────────────────────
// Regex-based AST: procura `http.<method>("/api/...", ...)`
// (MSW http helpers).

function extractHandlerEndpoints(source) {
  const re = /http\.(get|post|put|patch|delete|head|options)\(\s*(?:`([^`]*)`|"([^"]*)"|'([^']*)')/g;
  const endpoints = new Set();
  let m;
  while ((m = re.exec(source)) !== null) {
    const method = m[1].toUpperCase();
    const url = m[2] ?? m[3] ?? m[4];
    // Normaliza: remove ${API} prefix se string contém template
    // Handlers usam `${API}${path}`. O regex cobre string plain com /api/...
    // Em nossos handlers todas as URLs são strings plain.
    const normalized = normalizeUrl(url);
    endpoints.add(`${method} ${normalized}`);
  }
  return endpoints;
}

function normalizeUrl(url) {
  // Troca `:param` → `{param}` para casar com OpenAPI spec
  return url.replace(/:(\w+)/g, "{$1}");
}

// ─── Carregar OpenAPI spec ───────────────────────────────────────────

async function loadOpenApiSpec() {
  if (specPath) {
    if (!existsSync(specPath)) {
      console.error(`✗ OpenAPI spec não encontrado: ${specPath}`);
      process.exit(2);
    }
    return JSON.parse(readFileSync(specPath, "utf-8"));
  }
  const url = `${BACKEND_URL}/openapi.json`;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`✗ Não foi possível baixar ${url}: ${err.message}`);
    console.error("Backend rodando? Ou passe --spec <arquivo>.");
    process.exit(2);
  }
}

function extractBackendEndpoints(spec) {
  const endpoints = new Set();
  const paths = spec.paths ?? {};
  for (const [path, methods] of Object.entries(paths)) {
    for (const method of Object.keys(methods)) {
      const m = method.toUpperCase();
      if (!["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"].includes(m)) continue;
      endpoints.add(`${m} ${path}`);
    }
  }
  return endpoints;
}

// ─── Main ────────────────────────────────────────────────────────────

async function main() {
  if (!existsSync(HANDLERS_PATH)) {
    console.error(`✗ handlers.ts não encontrado em ${HANDLERS_PATH}`);
    process.exit(2);
  }
  const handlersSource = readFileSync(HANDLERS_PATH, "utf-8");
  const frontendEndpoints = extractHandlerEndpoints(handlersSource);

  const spec = await loadOpenApiSpec();
  const backendEndpoints = extractBackendEndpoints(spec);

  // WebSocket endpoints não aparecem em OpenAPI — filtrar ruído
  const backendFiltered = new Set(
    [...backendEndpoints].filter((e) => !e.includes("/ws")),
  );

  const missingInFrontend = [...backendFiltered].filter(
    (e) => !frontendEndpoints.has(e),
  );
  const extraInFrontend = [...frontendEndpoints].filter(
    (e) => !backendFiltered.has(e),
  );

  console.log(`Backend endpoints: ${backendFiltered.size}`);
  console.log(`handlers.ts endpoints: ${frontendEndpoints.size}`);

  let hasError = false;

  if (missingInFrontend.length > 0) {
    console.error(
      `\n✗ ${missingInFrontend.length} endpoint(s) backend SEM handler MSW:`,
    );
    for (const e of missingInFrontend.slice(0, 20)) console.error(`   - ${e}`);
    if (missingInFrontend.length > 20) {
      console.error(`   ... (+${missingInFrontend.length - 20} outros)`);
    }
    console.error(
      "\nAdicione handlers em `frontend/tests/mocks/handlers.ts` (ver ADR-069).",
    );
    hasError = true;
  }

  if (extraInFrontend.length > 0 && !allowExtra) {
    console.error(
      `\n✗ ${extraInFrontend.length} handler(s) MSW sem endpoint backend:`,
    );
    for (const e of extraInFrontend.slice(0, 20)) console.error(`   - ${e}`);
    console.error(
      "\nRemova handlers obsoletos OU rode com --allow-extra (justifique).",
    );
    hasError = true;
  }

  if (!hasError) {
    console.log("\n✓ MSW handlers em sync com backend OpenAPI.");
  }

  process.exit(hasError ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
