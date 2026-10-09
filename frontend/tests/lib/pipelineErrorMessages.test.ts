import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  buildUserFacingError,
  DATABASE_VALUES_OMITTED,
} from "@/lib/pipelineErrorMessages";

describe("buildUserFacingError — PDF protegido por senha", () => {
  it("casa mensagem com 'password protected'", () => {
    const err = buildUserFacingError("PDF password protected", "E0-route");
    expect(err.headline).toContain("protegido por senha");
  });

  it("casa mensagem com 'senha'", () => {
    const err = buildUserFacingError("Não foi possível abrir: senha necessária", null);
    expect(err.headline).toContain("protegido por senha");
  });

  it("casa mensagem com 'encrypted'", () => {
    const err = buildUserFacingError("File is encrypted", null);
    expect(err.headline).toContain("protegido por senha");
  });

  it("casa mensagem 'PDF está protegido por senha'", () => {
    const err = buildUserFacingError("PDF está protegido por senha", null);
    expect(err.headline).toContain("protegido por senha");
  });
});

describe("buildUserFacingError — NÃO confundir SQLite lock com PDF lock", () => {
  // Regressão prod 2026-05-22: 'database is locked' (SQLite) era mostrado
  // como "PDF protegido por senha", confundindo o usuário.
  it("não casa 'database is locked' como PDF protegido", () => {
    const err = buildUserFacingError(
      "(sqlite3.OperationalError) database is locked\n[SQL: INSERT INTO vehicles ...]",
      "extract_comprovantes_bens",
    );
    expect(err.headline).not.toContain("protegido por senha");
  });

  it("não casa 'account locked' como PDF protegido", () => {
    const err = buildUserFacingError("user account locked", null);
    expect(err.headline).not.toContain("protegido por senha");
  });

  it("não casa 'mutex locked' como PDF protegido", () => {
    const err = buildUserFacingError("mutex locked: timeout", null);
    expect(err.headline).not.toContain("protegido por senha");
  });

  it("ainda casa 'PDF is locked' (contexto PDF próximo)", () => {
    const err = buildUserFacingError("PDF is locked and cannot be opened", null);
    expect(err.headline).toContain("protegido por senha");
  });
});

describe("buildUserFacingError — outros patterns mantêm comportamento", () => {
  it("casa timeout", () => {
    const err = buildUserFacingError("Request timed out after 30s", "E5");
    expect(err.headline).toContain("demorou mais que o esperado");
  });

  it("fallback genérico quando nenhum pattern casa", () => {
    const err = buildUserFacingError("erro genérico inesperado", "E3");
    expect(err.hint).toContain("Tente reprocessar");
  });
});

// ADR-441 D2: o texto redigido traz nome de tabela/coluna — casaria senha, formato
// ou timeout por acidente. O marcador decide antes de qualquer padrão.
const REDIGIDO = (detalhe: string) =>
  `IntegrityError: UniqueViolation [sqlstate 23505; ${detalhe}] — ${DATABASE_VALUES_OMITTED}`;

describe("buildUserFacingError — erro de banco redigido (ADR-441)", () => {
  it.each([
    ["column api_key_encrypted", "protegido por senha"],
    ["column hashed_password", "protegido por senha"],
    ["column schema_version", "formato inesperado"],
    ["column deadline_at", "demorou mais que o esperado"],
  ])("'%s' cai no genérico da fase, não em '%s'", (detalhe, acidental) => {
    const err = buildUserFacingError(REDIGIDO(detalhe), "E3");
    expect(err.headline).not.toContain(acidental);
    expect(err.headline).toContain("Não conseguimos completar a etapa");
  });

  it("statement timeout redigido vira a mensagem de timeout", () => {
    const texto = `OperationalError: QueryCanceled [statement timeout; sqlstate 57014] — ${DATABASE_VALUES_OMITTED}`;
    const err = buildUserFacingError(texto, "E5");
    expect(err.headline).toContain("demorou mais que o esperado");
  });

  it("o backend declara o mesmo marcador (contrato Python ↔ TypeScript)", () => {
    const python = readFileSync(
      path.resolve(
        __dirname,
        "../../../pipeline/observability/failure_text.py",
      ),
      "utf8",
    );
    expect(python).toContain(
      `DATABASE_VALUES_OMITTED = "${DATABASE_VALUES_OMITTED}"`,
    );
  });
});
