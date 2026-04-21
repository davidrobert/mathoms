/**
 * PDF fixtures helper — E2E (A6g.1 · fix golden-path)
 *
 * Gera PDFs determinísticos via `tests/fixtures/pdf_generator.py` (reportlab)
 * para specs que dependem de upload + pipeline real processando o arquivo.
 *
 * Substitui bytes inline mínimos (header PDF sem body real) que o backend
 * detecta como "password-protected" via pikepdf/parser, derrubando o pipeline.
 *
 * CI: `reportlab` é instalado em `.github/workflows/ci.yml` job frontend-e2e.
 * Local: `pip install reportlab` ou usar venv de pipeline-tests.
 *
 * Bytes determinísticos permitem cache cross-run; geramos uma vez por spec
 * via `test.beforeAll`.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

export interface PdfFixtureSpec {
  bank: string;                  // código canônico de institutions.json
  kind: "extrato" | "fatura";
  period?: string;               // "YYYY-MM" (default 2026-04)
  transactions?: Array<{
    date: string;                // YYYY-MM-DD
    description: string;
    amount: number;              // negativo = débito
  }>;
  outfile: string;               // nome relativo em /tmp/e2e-fixtures/
}

// Raiz do repo resolvida a partir deste arquivo: frontend/tests/e2e/helpers → ../../../..
const REPO_ROOT = resolve(__dirname, "..", "..", "..", "..");
const FIXTURE_DIR = "/tmp/e2e-fixtures";

/**
 * Gera os PDFs dados via pdf_generator.py e retorna um map {outfile → bytes}.
 * Chame em `test.beforeAll` para materializar uma vez por worker.
 */
export function generateFixturePdfs(specs: PdfFixtureSpec[]): Record<string, Buffer> {
  mkdirSync(FIXTURE_DIR, { recursive: true });

  const payload = JSON.stringify(specs);
  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(REPO_ROOT)})
from tests.fixtures.pdf_generator import write_statement_pdf

for spec in json.loads(${JSON.stringify(payload)}):
    write_statement_pdf(
        path=${JSON.stringify(FIXTURE_DIR)} + "/" + spec["outfile"],
        bank=spec["bank"],
        kind=spec["kind"],
        period=spec.get("period", "2026-04"),
        transactions=spec.get("transactions", []),
    )
`;

  execFileSync("python3", ["-c", pyScript], {
    cwd: REPO_ROOT,
    stdio: ["ignore", "inherit", "inherit"],
  });

  const bytes: Record<string, Buffer> = {};
  for (const spec of specs) {
    bytes[spec.outfile] = readFileSync(join(FIXTURE_DIR, spec.outfile));
  }
  return bytes;
}
