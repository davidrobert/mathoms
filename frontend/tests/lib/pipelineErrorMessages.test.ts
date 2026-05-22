import { describe, expect, it } from "vitest";
import { buildUserFacingError } from "@/lib/pipelineErrorMessages";

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
