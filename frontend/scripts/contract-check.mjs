#!/usr/bin/env node
/**
 * Contract test FE↔BE — F6.5D.10
 *
 * Fluxo:
 *  1. Faz GET http://127.0.0.1:8000/openapi.json (backend FastAPI auto-gen)
 *  2. Passa por openapi-typescript → gera types inferidos
 *  3. Compara com types.generated.d.ts gerado anteriormente (snapshot)
 *  4. Se diff → falha CI (sinal de drift entre schemas BE e types FE em lib/api.ts)
 *
 * NOTA: gate hard vira em F7C (CI/CD). Aqui é scaffold — rodar manualmente:
 *
 *   cd frontend && node scripts/contract-check.mjs
 *
 * Requer backend rodando em 127.0.0.1:8000. Para CI usar
 * `scripts/test_backend_up.sh` (6.5F.3) antes.
 */
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const BACKEND_URL = process.env.FIN_BACKEND_URL ?? "http://127.0.0.1:8000";
const OPENAPI_URL = `${BACKEND_URL}/openapi.json`;
const SNAPSHOT_PATH = resolve("tests/contracts/openapi.types.d.ts");

async function main() {
  try {
    execSync(`curl -sf ${OPENAPI_URL} > /tmp/openapi.json`);
  } catch {
    console.error(`✗ Não foi possível baixar ${OPENAPI_URL}. Backend rodando?`);
    process.exit(2);
  }

  const generated = execSync(
    "npx openapi-typescript /tmp/openapi.json",
    { encoding: "utf-8" },
  );

  if (!existsSync(SNAPSHOT_PATH)) {
    writeFileSync(SNAPSHOT_PATH, generated);
    console.log(`✓ Baseline snapshot criado em ${SNAPSHOT_PATH}`);
    console.log("Commita esse arquivo e rode novamente para validar.");
    process.exit(0);
  }

  const snapshot = readFileSync(SNAPSHOT_PATH, "utf-8");
  if (snapshot === generated) {
    console.log("✓ OpenAPI types não mudaram — contract OK.");
    process.exit(0);
  }

  console.error("✗ Drift detectado entre OpenAPI do backend e snapshot.");
  console.error("Atualize snapshot se a mudança for intencional:");
  console.error(`  npx openapi-typescript ${OPENAPI_URL} > ${SNAPSHOT_PATH}`);
  console.error("E sincronize lib/api.ts com os novos types.");
  process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
