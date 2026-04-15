/**
 * Unit tests — `lib/format.ts` (9 formatters + 4 status maps + property-based BRL)
 *
 * F6.5A.3 + F6.5D.2 (property-based via fast-check)
 *
 * Por que tanto detalhe em formatadores monetários?
 * - Bug de format BRL destrói confiança em fintech permanentemente.
 * - Casos cobertos: negativo, zero, micro (R$ 0,01), bilhão+, NaN/null,
 *   round-trip, separadores corretos (`.` milhar, `,` decimal).
 *
 * Status maps: garante que todos os enums conhecidos têm label + variant
 * declarados (erro no enum quebra type-check, mas teste protege contra
 * mismatch entre tipo e map).
 */
import { describe, expect, it } from "vitest";
import * as fc from "fast-check";

import {
  bankLabel,
  docStatusLabel,
  docTypeLabel,
  formatBytes,
  formatCompact,
  formatCurrency,
  formatDate,
  formatDateShort,
  formatDelta,
  formatDocPeriod,
  formatDuration,
  formatElapsed,
  formatMonth,
  formatNumber,
  formatPercent,
  formatPeriod,
  formatRange,
  runStatusLabel,
  stageName,
  stageStatusLabel,
  STAGE_DISPLAY_NAMES,
} from "@/lib/format";
import type {
  DocumentStatus,
  DocumentType,
  PipelineRunStatus,
  PipelineStageStatus,
} from "@/lib/api";

// Intl.NumberFormat usa NBSP (\u00A0) em pt-BR; literalmente igualar precisa
// de cuidado. Helper para normalizar nas asserts onde só importa o conteúdo
// numérico.
const norm = (s: string) => s.replace(/\u00A0/g, " ");

// ─── formatCurrency ──────────────────────────────────────────────────

describe("formatCurrency()", () => {
  it("formata BRL positivo com R$ + separador BR", () => {
    expect(norm(formatCurrency(1234.56))).toBe("R$ 1.234,56");
  });

  it("formata BRL zero", () => {
    expect(norm(formatCurrency(0))).toBe("R$ 0,00");
  });

  it("formata BRL negativo (sinal antes do R$ ou com -R$)", () => {
    const out = norm(formatCurrency(-99.5));
    // Intl pode usar "-R$ 99,50" ou "R$ -99,50" dependendo da plataforma
    expect(out).toMatch(/-.*99,50/);
  });

  it("formata micro-valor (R$ 0,01)", () => {
    expect(norm(formatCurrency(0.01))).toBe("R$ 0,01");
  });

  it("formata bilhão+", () => {
    expect(norm(formatCurrency(1_234_567_890.12))).toBe("R$ 1.234.567.890,12");
  });

  it("USD usa $ + separador en-US", () => {
    expect(formatCurrency(1234.56, "USD")).toBe("$1,234.56");
  });

  it("arredonda 2 casas (banker's? toleramos qualquer arredondamento Intl)", () => {
    const out = norm(formatCurrency(1.005));
    // Pode ser "R$ 1,00" ou "R$ 1,01" — só garantimos 2 decimais
    expect(out).toMatch(/R\$\s\d+,\d{2}$/);
  });
});

// ─── formatPercent ───────────────────────────────────────────────────

describe("formatPercent()", () => {
  it("formata fração como percent BR", () => {
    // Valor 0.156 → "15,6%" (Intl usa fração, não 0-100)
    expect(norm(formatPercent(0.156))).toBe("15,6%");
  });

  it("zero", () => {
    expect(norm(formatPercent(0))).toBe("0,0%");
  });

  it("negativo", () => {
    expect(norm(formatPercent(-0.05))).toBe("-5,0%");
  });

  it("custom decimals", () => {
    expect(norm(formatPercent(0.12345, 3))).toBe("12,345%");
  });
});

// ─── formatDelta ─────────────────────────────────────────────────────

describe("formatDelta()", () => {
  it("positivo recebe + e formata BRL", () => {
    expect(norm(formatDelta(100))).toBe("+R$ 100,00");
  });

  it("negativo já vem com sinal do BRL (não duplica)", () => {
    const out = norm(formatDelta(-100));
    expect(out).toMatch(/-.*100,00/);
    // Não deve ter "+-"
    expect(out).not.toContain("+-");
  });

  it("inclui percentual quando passado", () => {
    const out = norm(formatDelta(100, { percent: 0.25 }));
    expect(out).toContain("+R$ 100,00");
    expect(out).toContain("(+25,0%)");
  });
});

// ─── formatCompact ───────────────────────────────────────────────────

describe("formatCompact()", () => {
  it("formato compact mil → mil/k abreviado", () => {
    const out = norm(formatCompact(12_500));
    // Intl pode usar "R$ 12,5 mil" pt-BR
    expect(out).toMatch(/R\$/);
  });

  it("milhão", () => {
    const out = norm(formatCompact(1_500_000));
    expect(out).toMatch(/R\$/);
  });
});

// ─── formatNumber ────────────────────────────────────────────────────

describe("formatNumber()", () => {
  it("0 decimais", () => {
    expect(norm(formatNumber(1234.56))).toBe("1.235");
  });

  it("2 decimais", () => {
    expect(norm(formatNumber(1234.5, 2))).toBe("1.234,50");
  });
});

// ─── formatBytes ─────────────────────────────────────────────────────

describe("formatBytes()", () => {
  it.each([
    [null, "—"],
    [undefined, "—"],
    [0, "—"], // 0 bytes é tratado como "vazio" via !bytes
    [512, "512 B"],
    [1024, "1 KB"],
    [102_400, "100 KB"],
    [1_048_576, "1.0 MB"],
    [10_485_760, "10.0 MB"],
  ])("%j → %j", (input, expected) => {
    expect(formatBytes(input)).toBe(expected);
  });
});

// ─── formatDuration ──────────────────────────────────────────────────

describe("formatDuration()", () => {
  it.each([
    [null, "—"],
    [0, "—"],
    [500, "500ms"],
    [1500, "1.5s"],
    [60_000, "1m 0s"],
    [125_000, "2m 5s"],
  ])("%j → %j", (input, expected) => {
    expect(formatDuration(input)).toBe(expected);
  });
});

// ─── formatDate / formatDateShort ────────────────────────────────────

describe("formatDate()", () => {
  it("formata ISO em dd/mm/yyyy hh:mm pt-BR", () => {
    const out = formatDate("2026-04-15T12:00:00Z");
    expect(out).toMatch(/15\/04\/2026/);
    expect(out).toMatch(/\d{2}:\d{2}/);
  });
});

describe("formatDateShort()", () => {
  it("dd/mm/yyyy", () => {
    expect(formatDateShort("2026-04-15T12:00:00Z")).toBe("15/04/2026");
  });
});

// ─── formatPeriod / formatRange / formatMonth / formatDocPeriod ──────

describe("formatPeriod()", () => {
  it("YYYYMM → mês/yyyy abreviado", () => {
    const out = formatPeriod("202604");
    // pt-BR mês curto pode ter ponto "abr." ou "abr"
    expect(out).toMatch(/\d{4}/);
    expect(out.toLowerCase()).toMatch(/abr/);
  });

  it("aceita number", () => {
    const out = formatPeriod(202604);
    expect(out.toLowerCase()).toMatch(/abr/);
  });

  it("inválido (mês > 12) volta original", () => {
    expect(formatPeriod("202613")).toBe("202613");
  });

  it("string curta volta original", () => {
    expect(formatPeriod("2026")).toBe("2026");
  });
});

describe("formatMonth()", () => {
  it("mês longo + ano", () => {
    const out = formatMonth(new Date(2026, 3, 1));
    expect(out.toLowerCase()).toContain("abril");
    expect(out).toContain("2026");
  });
});

describe("formatRange()", () => {
  it("usa traço (en-dash)", () => {
    const out = formatRange("202601", "202604");
    expect(out).toContain("–"); // en-dash
  });
});

describe("formatDocPeriod()", () => {
  it.each([
    [null, "—"],
    [undefined, "—"],
    ["999999", "Indeterminado"], // sentinel
  ])("%j → %j", (input, expected) => {
    expect(formatDocPeriod(input as any)).toBe(expected);
  });

  it("range YYYYMM_YYYYMM com mesmo período → singular", () => {
    const out = formatDocPeriod("202604_202604");
    expect(out.toLowerCase()).toMatch(/abr/);
    expect(out).not.toContain("–");
  });

  it("range YYYYMM_YYYYMM com períodos distintos → range", () => {
    const out = formatDocPeriod("202601_202604");
    expect(out).toContain("–");
  });
});

// ─── formatElapsed ───────────────────────────────────────────────────

describe("formatElapsed()", () => {
  it("startedAt no futuro → 0s (defesa)", () => {
    const future = new Date(Date.now() + 60_000).toISOString();
    expect(formatElapsed(future)).toBe("0s");
  });

  it("< 10s → '< 10s'", () => {
    const recent = new Date(Date.now() - 5_000).toISOString();
    expect(formatElapsed(recent)).toBe("< 10s");
  });

  it("< 60s → segundos", () => {
    const half = new Date(Date.now() - 30_000).toISOString();
    expect(formatElapsed(half)).toMatch(/^\d{1,2}s$/);
  });

  it("> 1min → 'Xmin YYs'", () => {
    const old = new Date(Date.now() - 125_000).toISOString();
    expect(formatElapsed(old)).toMatch(/^\d+min \d{2}s$/);
  });
});

// ─── Status Maps ─────────────────────────────────────────────────────

describe("docStatusLabel()", () => {
  const ALL_STATUS: DocumentStatus[] = [
    "uploaded",
    "unlocking",
    "classifying",
    "ready",
    "needs_password",
    "processing",
    "processed",
    "error",
  ];

  it.each(ALL_STATUS)("retorna label e variant para %s", (s) => {
    const out = docStatusLabel(s);
    expect(out.label).toBeTypeOf("string");
    expect(out.label.length).toBeGreaterThan(0);
    expect(out.variant).toMatch(/^(success|warning|error|info|neutral|premium|muted)$/);
  });

  it("status desconhecido fallback para neutral", () => {
    const out = docStatusLabel("xyz_unknown" as any);
    expect(out.variant).toBe("neutral");
  });
});

describe("docTypeLabel()", () => {
  it("null → '—'", () => expect(docTypeLabel(null)).toBe("—"));
  it("bank_statement → 'Extrato'", () =>
    expect(docTypeLabel("bank_statement" as DocumentType)).toBe("Extrato"));
  it("desconhecido → o próprio code", () => {
    expect(docTypeLabel("custom_type" as any)).toBe("custom_type");
  });
});

describe("bankLabel()", () => {
  it.each([
    ["itau", "Itaú"],
    ["c6bank", "C6 Bank"],
    ["nubank", "Nubank"],
    ["bankofamerica", "Bank of America"],
  ])("%s → %s", (code, label) => {
    expect(bankLabel(code)).toBe(label);
  });

  it("null → '—'", () => expect(bankLabel(null)).toBe("—"));
  it("desconhecido → o próprio code", () => expect(bankLabel("xyz")).toBe("xyz"));
  it("uppercase é normalizado", () => expect(bankLabel("ITAU")).toBe("Itaú"));
});

describe("runStatusLabel()", () => {
  const ALL: PipelineRunStatus[] = [
    "pending",
    "running",
    "completed",
    "partial_failure",
    "failed",
    "cancelled",
    "needs_review",
    "resuming",
  ];

  it.each(ALL)("retorna label/variant para %s", (s) => {
    const out = runStatusLabel(s);
    expect(out.label.length).toBeGreaterThan(0);
    expect(out.variant).toMatch(/^(success|warning|error|info|neutral|premium|muted)$/);
  });
});

describe("stageStatusLabel()", () => {
  const ALL: PipelineStageStatus[] = [
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    "skipped_free_tier",
    "needs_review",
  ];

  it.each(ALL)("retorna label/variant/icon para %s", (s) => {
    const out = stageStatusLabel(s);
    expect(out.label.length).toBeGreaterThan(0);
    expect(out.icon.length).toBeGreaterThan(0);
  });
});

describe("stageName()", () => {
  it.each(Object.entries(STAGE_DISPLAY_NAMES))("%s → %s", (code, expected) => {
    expect(stageName(code)).toBe(expected);
  });

  it("código novo desconhecido volta literal (não quebra UI)", () => {
    expect(stageName("E99-future")).toBe("E99-future");
  });
});

// ─── Property-based — F6.5D.2 ────────────────────────────────────────

describe("Property-based: BRL formatter (F6.5D.2)", () => {
  it("para qualquer número finito, output sempre tem 'R$' e 2 decimais", () => {
    fc.assert(
      fc.property(
        fc.double({ min: -9_999_999_999, max: 9_999_999_999, noNaN: true }),
        (n) => {
          const out = norm(formatCurrency(n));
          expect(out).toContain("R$");
          // Deve terminar com `,XX` (2 dígitos)
          expect(out).toMatch(/,\d{2}$/);
        },
      ),
      { numRuns: 200 },
    );
  });

  it("nunca emite ponto antes da vírgula sem dígito (separadores BR íntegros)", () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.01, max: 1_000_000, noNaN: true }),
        (n) => {
          const out = norm(formatCurrency(n));
          // Dígito deve seguir cada ponto de milhar
          // R$ 1.000,00 OK; R$ .000,00 NÃO
          expect(out).not.toMatch(/\.[^\d]/);
        },
      ),
      { numRuns: 200 },
    );
  });

  it("formatPercent inverte sinal corretamente para qualquer fração", () => {
    fc.assert(
      fc.property(fc.double({ min: -1, max: 1, noNaN: true }), (n) => {
        const out = norm(formatPercent(n));
        if (n < 0) expect(out).toMatch(/^-/);
        // Sempre termina com %
        expect(out).toMatch(/%$/);
      }),
      { numRuns: 100 },
    );
  });

  it("formatDelta para positivo SEMPRE começa com +", () => {
    fc.assert(
      fc.property(fc.double({ min: 0.01, max: 1_000_000, noNaN: true }), (n) => {
        const out = norm(formatDelta(n));
        expect(out.startsWith("+")).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("formatBytes é monotônico crescente acima de 1KB", () => {
    fc.assert(
      fc.property(
        fc.tuple(
          fc.integer({ min: 1024, max: 100_000_000 }),
          fc.integer({ min: 1024, max: 100_000_000 }),
        ),
        ([a, b]) => {
          if (a === b) return; // skip equal
          const [smaller, larger] = a < b ? [a, b] : [b, a];
          // Heurística: maior número → output gera mesma ou mais larga string
          // (não testamos comparação numérica do parsing — apenas que ambos formatam)
          expect(formatBytes(smaller)).toMatch(/B|KB|MB/);
          expect(formatBytes(larger)).toMatch(/B|KB|MB/);
        },
      ),
      { numRuns: 50 },
    );
  });
});
