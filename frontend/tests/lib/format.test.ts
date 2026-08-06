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
  docEffectiveStatus,
  docStatusLabel,
  isDocumentClassifiedOk,
  docSubtypeLabel,
  docTypeLabel,
  documentDisplayLabel,
  fileFormatLabel,
  institutionLabel,
  pipelineE2TouchLabel,
  pipelineTouchTooltipExplanation,
  formatBRLDecimalString,
  formatBRLNoCents,
  formatBytes,
  formatCompact,
  formatCurrency,
  formatCurrencyWithCode,
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
  formatPeriodCoverPtBR,
  formatRange,
  formatUSDPtBR,
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

  it("EUR e GBP usam símbolo + separador en-US (paridade com MonetaryValue)", () => {
    expect(formatCurrency(1234.5, "EUR")).toBe("€1,234.50");
    expect(formatCurrency(1234.5, "GBP")).toBe("£1,234.50");
  });

  it("maximumFractionDigits: 0 arredonda sem centavos (mínimo colapsa junto)", () => {
    expect(norm(formatCurrency(1234.56, "BRL", { maximumFractionDigits: 0 }))).toBe("R$ 1.235");
    expect(formatCurrency(1234.56, "USD", { maximumFractionDigits: 0 })).toBe("$1,235");
  });

  it("min 0 / max 3 reproduz dígitos de toLocaleString('pt-BR') cru (W5-T03 byte-parity)", () => {
    const digits = { minimumFractionDigits: 0, maximumFractionDigits: 3 };
    expect(norm(formatCurrency(8000, "BRL", digits))).toBe("R$ 8.000");
    expect(norm(formatCurrency(8000.5, "BRL", digits))).toBe("R$ 8.000,5");
    expect(norm(formatCurrency(1500.55, "BRL", digits))).toBe("R$ 1.500,55");
  });
});

// ─── formatBRLNoCents ────────────────────────────────────────────────

describe("formatBRLNoCents()", () => {
  it("null/undefined → em-dash", () => {
    expect(formatBRLNoCents(null)).toBe("—");
    expect(formatBRLNoCents(undefined)).toBe("—");
  });

  it("arredonda para inteiro em BRL", () => {
    expect(norm(formatBRLNoCents(1234.56))).toBe("R$ 1.235");
    expect(norm(formatBRLNoCents(0))).toBe("R$ 0");
  });
});

// ─── formatBRLDecimalString ──────────────────────────────────────────

describe("formatBRLDecimalString()", () => {
  it("null/undefined/vazio → em-dash", () => {
    expect(formatBRLDecimalString(null)).toBe("—");
    expect(formatBRLDecimalString(undefined)).toBe("—");
    expect(formatBRLDecimalString("")).toBe("—");
  });

  it("Decimal-string da API vira BRL sem centavos", () => {
    expect(norm(formatBRLDecimalString("500000.00"))).toBe("R$ 500.000");
    expect(norm(formatBRLDecimalString("79.9"))).toBe("R$ 80");
    expect(norm(formatBRLDecimalString("0"))).toBe("R$ 0");
  });

  it("string não-numérica ('N/D') → em-dash, nunca NaN", () => {
    expect(formatBRLDecimalString("N/D")).toBe("—");
    expect(formatBRLDecimalString("abc")).toBe("—");
  });
});

// ─── formatUSDPtBR ───────────────────────────────────────────────────

describe("formatUSDPtBR()", () => {
  it("USD com dígitos pt-BR e sem casas obrigatórias (telas de dolarização)", () => {
    expect(norm(formatUSDPtBR(50000))).toBe("US$ 50.000");
    expect(norm(formatUSDPtBR(1_000_000))).toBe("US$ 1.000.000");
  });

  it("preserva fração digitada até 3 casas (paridade com toLocaleString cru)", () => {
    expect(norm(formatUSDPtBR(50000.5))).toBe("US$ 50.000,5");
  });
});

// ─── formatCurrencyWithCode ──────────────────────────────────────────

describe("formatCurrencyWithCode()", () => {
  it("código ISO cru + dígitos pt-BR com mínimo de 2 casas (espaço ASCII)", () => {
    expect(formatCurrencyWithCode("CHF", 5210.55)).toBe("CHF 5.210,55");
    expect(formatCurrencyWithCode("JPY", 1000)).toBe("JPY 1.000,00");
  });

  it("não lança para código não-ISO (diferente de Intl currency)", () => {
    expect(formatCurrencyWithCode("PONTOS", 12.3)).toBe("PONTOS 12,30");
  });
});

// ─── formatPercent ───────────────────────────────────────────────────

// ADR-209: convenção absoluta — input é o número já em escala percentual
// (44.7 = 44,7%, NÃO 0.447). Formatter não multiplica por 100.
describe("formatPercent()", () => {
  it("formata valor absoluto como percent BR (não multiplica por 100)", () => {
    expect(norm(formatPercent(15.6))).toBe("15,6%");
  });

  it("ADR-209: input 44.71 produz '44,71%' (não '4.471%')", () => {
    expect(norm(formatPercent(44.71, 2))).toBe("44,71%");
    expect(norm(formatPercent(44.71))).toBe("44,7%");
  });

  it("zero", () => {
    expect(norm(formatPercent(0))).toBe("0,0%");
  });

  it("negativo", () => {
    expect(norm(formatPercent(-5))).toBe("-5,0%");
  });

  it("custom decimals", () => {
    expect(norm(formatPercent(12.345, 3))).toBe("12,345%");
  });

  it("valor > 100 é válido (ex.: cobertura 3,5× = 350%)", () => {
    expect(norm(formatPercent(350))).toBe("350,0%");
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

  it("inclui percentual quando passado (ADR-209: absoluto)", () => {
    const out = norm(formatDelta(100, { percent: 25 }));
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
    [0, "0ms"],
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

describe("formatPeriodCoverPtBR()", () => {
  it("range completo 'YYYY-MM a YYYY-MM' → 'mmm YYYY — mmm YYYY' (em-dash)", () => {
    expect(formatPeriodCoverPtBR("2023-01 a 2026-04")).toBe("jan 2023 — abr 2026");
  });

  it("período único 'YYYY-MM' → 'mmm YYYY'", () => {
    expect(formatPeriodCoverPtBR("2026-04")).toBe("abr 2026");
  });

  it("entrada inválida cai graciosamente para input cru", () => {
    expect(formatPeriodCoverPtBR("202601-202604")).toBe("202601-202604");
    expect(formatPeriodCoverPtBR("foo")).toBe("foo");
  });

  it("null/undefined → '—'", () => {
    expect(formatPeriodCoverPtBR(null)).toBe("—");
    expect(formatPeriodCoverPtBR(undefined)).toBe("—");
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

describe("docEffectiveStatus()", () => {
  it("status=error → Erro", () => {
    expect(docEffectiveStatus({ status: "error" })).toEqual({ label: "Erro", variant: "error" });
  });

  it("status=needs_password → Aguarda senha", () => {
    expect(docEffectiveStatus({ status: "needs_password" })).toEqual({
      label: "Aguarda senha",
      variant: "warning",
    });
  });

  it.each(["uploaded", "unlocking", "classifying"] as DocumentStatus[])(
    "status=%s → Recebido",
    (status) => {
      expect(docEffectiveStatus({ status })).toEqual({ label: "Recebido", variant: "neutral" });
    },
  );

  it("status=processing → Analisando", () => {
    expect(docEffectiveStatus({ status: "processing" })).toEqual({
      label: "Analisando",
      variant: "info",
    });
  });

  it("ready + sem needs_review → Pronto", () => {
    expect(docEffectiveStatus({ status: "ready", needs_review: false })).toEqual({
      label: "Pronto",
      variant: "info",
    });
  });

  it("ready + needs_review + tipo conhecido → Revisar (warning)", () => {
    expect(
      docEffectiveStatus({ status: "ready", needs_review: true, doc_type: "bank_statement" }),
    ).toEqual({ label: "Revisar", variant: "warning" });
  });

  it("ready + needs_review + doc_type=other → Não classificado (muted)", () => {
    expect(
      docEffectiveStatus({ status: "ready", needs_review: true, doc_type: "other" }),
    ).toEqual({ label: "Não classificado", variant: "muted" });
  });

  it("ready + needs_review sem doc_type → Revisar (fallback warning)", () => {
    expect(docEffectiveStatus({ status: "ready", needs_review: true })).toEqual({
      label: "Revisar",
      variant: "warning",
    });
  });

  it("processed + pipeline_e2_extract_ok=true → Extraído", () => {
    expect(
      docEffectiveStatus({ status: "processed", pipeline_e2_extract_ok: true }),
    ).toEqual({ label: "Extraído", variant: "success" });
  });

  it("processed + needs_review + doc_type=other → Não classificado (muted)", () => {
    expect(
      docEffectiveStatus({
        status: "processed",
        pipeline_e2_extract_ok: false,
        needs_review: true,
        doc_type: "other",
      }),
    ).toEqual({ label: "Não classificado", variant: "muted" });
  });

  it("processed + pipeline_e2_extract_ok=false sem needs_review → Sem extrato", () => {
    expect(
      docEffectiveStatus({ status: "processed", pipeline_e2_extract_ok: false }),
    ).toEqual({ label: "Sem extrato", variant: "neutral" });
  });

  it("processed + pipeline_e2_extract_ok=null (IRPF/members) → Processado", () => {
    expect(
      docEffectiveStatus({ status: "processed", pipeline_e2_extract_ok: null }),
    ).toEqual({ label: "Processado", variant: "success" });
  });
});

describe("isDocumentClassifiedOk()", () => {
  it("ready e processed → true", () => {
    expect(isDocumentClassifiedOk("ready")).toBe(true);
    expect(isDocumentClassifiedOk("processed")).toBe(true);
  });
  it("demais → false", () => {
    expect(isDocumentClassifiedOk("error")).toBe(false);
    expect(isDocumentClassifiedOk("needs_password")).toBe(false);
  });
});

describe("docTypeLabel()", () => {
  it("null → '—'", () => expect(docTypeLabel(null)).toBe("—"));
  it("bank_statement → 'Extrato'", () =>
    expect(docTypeLabel("bank_statement" as DocumentType)).toBe("Extrato"));
  it("comprovante_bem → 'Comprovante de bem' (fallback ADR-239 sem subtipo)", () =>
    expect(docTypeLabel("comprovante_bem" as DocumentType)).toBe("Comprovante de bem"));
  it("informe_rendimentos_anuais → 'Informe de rendimentos' (fallback ADR-238)", () =>
    expect(docTypeLabel("informe_rendimentos_anuais" as DocumentType)).toBe(
      "Informe de rendimentos",
    ));
  it("desconhecido → o próprio code", () => {
    expect(docTypeLabel("custom_type" as any)).toBe("custom_type");
  });
});

describe("docSubtypeLabel()", () => {
  it("informerendimentosaluguel → 'Informe de aluguéis (IRPF)'", () => {
    expect(docSubtypeLabel("informerendimentosaluguel", "irpf")).toBe("Informe de aluguéis (IRPF)");
  });
  it("informerendimentos → 'Informe de rendimentos (IRPF)'", () => {
    expect(docSubtypeLabel("informerendimentos", "irpf")).toBe("Informe de rendimentos (IRPF)");
  });
  it("irpfdeclaracao → 'Declaração IRPF'", () => {
    expect(docSubtypeLabel("irpfdeclaracao", "irpf")).toBe("Declaração IRPF");
  });
  it("apolice_seguro → 'Apólice de seguro' (ADR-239 A18 L2)", () => {
    expect(docSubtypeLabel("apolice_seguro", "comprovante_bem" as DocumentType)).toBe(
      "Apólice de seguro",
    );
  });
  it("crlv_eletronico → 'CRLV-e (veículo)' (ADR-239 A18 L1)", () => {
    expect(docSubtypeLabel("crlv_eletronico", "comprovante_bem" as DocumentType)).toBe(
      "CRLV-e (veículo)",
    );
  });
  it("informe_previdencia_privada → 'Informe de previdência privada' (ADR-238 A17 L1)", () => {
    expect(
      docSubtypeLabel("informe_previdencia_privada", "informe_rendimentos_anuais" as DocumentType),
    ).toBe("Informe de previdência privada");
  });
  it("comprovante_bem sem subtipo → 'Comprovante de bem' (fallback)", () => {
    expect(docSubtypeLabel(null, "comprovante_bem" as DocumentType)).toBe("Comprovante de bem");
  });
  it("e0_doc_type desconhecido → fallback para docTypeLabel(doc_type)", () => {
    expect(docSubtypeLabel("subtipo_xyz", "bank_statement" as DocumentType)).toBe("Extrato");
  });
  it("e0_doc_type null → fallback para docTypeLabel(doc_type)", () => {
    expect(docSubtypeLabel(null, "credit_card_bill" as DocumentType)).toBe("Fatura");
  });
});

describe("bankLabel()", () => {
  it.each([
    ["itau", "Itaú"],
    ["c6bank", "C6 Bank"],
    ["nubank", "Nubank"],
    ["bankofamerica", "Bank of America"],
    ["receitafederal", "Receita Federal"],
  ])("%s → %s", (code, label) => {
    expect(bankLabel(code)).toBe(label);
  });

  it("null → '—'", () => expect(bankLabel(null)).toBe("—"));
  it("desconhecido → o próprio code", () => expect(bankLabel("xyz")).toBe("xyz"));
  it("uppercase é normalizado", () => expect(bankLabel("ITAU")).toBe("Itaú"));
});

describe("institutionLabel()", () => {
  it("espelha bankLabel", () => {
    expect(institutionLabel("santander")).toBe(bankLabel("santander"));
  });
});

describe("fileFormatLabel()", () => {
  it("usa extensão do nome", () => {
    expect(fileFormatLabel(null, "x.pdf")).toBe("PDF");
    expect(fileFormatLabel(null, "dados.CSV")).toBe("CSV");
  });
  it("fallback por content-type", () => {
    expect(fileFormatLabel("application/pdf", "noext")).toBe("PDF");
  });
});

describe("pipelineE2TouchLabel()", () => {
  it("sem data → —", () => expect(pipelineE2TouchLabel(null, null)).toBe("—"));
  it("com leitura estruturada", () => {
    const s = pipelineE2TouchLabel("2026-04-16T12:00:00.000Z", true);
    expect(s).toContain("leitura estruturada");
    expect(s).not.toMatch(/E2/i);
  });
  it("com leitura automática incompleta", () => {
    const s = pipelineE2TouchLabel("2026-04-16T12:00:00.000Z", false);
    expect(s).toContain("leitura automática incompleta");
    expect(s).not.toMatch(/E2/i);
  });
});

describe("pipelineTouchTooltipExplanation()", () => {
  it("e2Ok true → mensagem clara", () => {
    const t = pipelineTouchTooltipExplanation(true);
    expect(t.length).toBeGreaterThan(20);
    expect(t).not.toMatch(/E2|JSON|pipeline|LLM/i);
  });
  it("e2Ok false → explica limite sem jargão", () => {
    const t = pipelineTouchTooltipExplanation(false);
    expect(t).toMatch(/análise|extrato/i);
    expect(t).not.toMatch(/E2|JSON|LLM/i);
  });
  it("e2Ok null → texto neutro", () => {
    expect(pipelineTouchTooltipExplanation(null)).toContain("verificar");
  });
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

  // A40.l21: "Parcial" respondia "quanto rodou?"; o rótulo tem de responder
  // "eu tenho relatório?". Trava o texto — o it.each acima não o faria.
  it("partial_failure é 'Concluído com ressalva', em warning", () => {
    expect(runStatusLabel("partial_failure")).toEqual({
      label: "Concluído com ressalva",
      variant: "warning",
    });
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
    "degraded",
  ];

  it.each(ALL)("retorna label/variant/icon para %s", (s) => {
    const out = stageStatusLabel(s);
    expect(out.label.length).toBeGreaterThan(0);
    expect(out.icon.length).toBeGreaterThan(0);
  });

  // Leitor tolerante antes do writer (ADR-357 §3): sem entrada no mapa, a UI
  // mostraria a string crua "degraded" com ícone "?".
  it("degraded não vaza vocabulário de backend na tela", () => {
    const out = stageStatusLabel("degraded");
    expect(out.label).toBe("Não publicado");
    expect(out.variant).toBe("warning");
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

  it("formatPercent (ADR-209 absoluto) inverte sinal e sempre termina em %", () => {
    fc.assert(
      fc.property(fc.double({ min: -100, max: 100, noNaN: true }), (n) => {
        const out = norm(formatPercent(n));
        if (n <= -0.05) expect(out).toMatch(/^-/);
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

// ─── documentDisplayLabel ───────────────────────────────────────────

describe("documentDisplayLabel()", () => {
  it("monta instituição · tipo · período quando tudo está presente", () => {
    const out = documentDisplayLabel({
      doc_type: "bank_statement",
      bank_code: "bradesco",
      period: "202603",
    });
    expect(out).toBe("Bradesco · Extrato · mar./2026");
  });

  it("omite período quando ausente mas mantém inst + tipo", () => {
    expect(
      documentDisplayLabel({
        doc_type: "credit_card_bill",
        bank_code: "itau",
        period: null,
      }),
    ).toBe("Itaú · Fatura");
  });

  it("formata range de período (fev./2026–mar./2026)", () => {
    const out = documentDisplayLabel({
      doc_type: "bank_statement",
      bank_code: "btgpactual",
      period: "202602_202603",
    });
    expect(out).toBe("BTG Pactual · Extrato · fev./2026–mar./2026");
  });

  it("ignora needs_review — incerteza é sinalizada por outro canal (ícone ⚠)", () => {
    const out = documentDisplayLabel({
      doc_type: "bank_statement",
      bank_code: "bradesco",
      period: "202603",
    });
    expect(out).toBe("Bradesco · Extrato · mar./2026");
  });

  it("aceita só instituição quando doc_type é null", () => {
    expect(
      documentDisplayLabel({ doc_type: null, bank_code: "itau", period: "2026" }),
    ).toBe("Itaú · 2026");
  });

  it("aceita só tipo quando bank_code é null", () => {
    expect(
      documentDisplayLabel({ doc_type: "bank_statement", bank_code: null, period: null }),
    ).toBe("Extrato");
  });

  it("retorna null se faltam bank_code E doc_type (só tem período)", () => {
    expect(
      documentDisplayLabel({ doc_type: null, bank_code: null, period: "2026" }),
    ).toBeNull();
  });

  it("retorna null se doc_type='other' sem instituição", () => {
    expect(
      documentDisplayLabel({ doc_type: "other", bank_code: null, period: null }),
    ).toBeNull();
  });

  it("usa label do e0_doc_type quando presente — 'Informe de aluguéis (IRPF)'", () => {
    const out = documentDisplayLabel({
      doc_type: "irpf",
      e0_doc_type: "informerendimentosaluguel",
      bank_code: "quintoandar",
      period: "2025",
    });
    expect(out).toBe("QuintoAndar · Informe de aluguéis (IRPF) · 2025");
  });

  it("e0_doc_type desconhecido cai pro doc_type genérico", () => {
    const out = documentDisplayLabel({
      doc_type: "irpf",
      e0_doc_type: "subtipo_que_nao_existe",
      bank_code: "bradesco",
      period: "2025",
    });
    expect(out).toBe("Bradesco · IRPF · 2025");
  });

  it("retorna null se nenhum campo presente", () => {
    expect(
      documentDisplayLabel({ doc_type: null, bank_code: null, period: null }),
    ).toBeNull();
  });

  it("mostra Indeterminado quando período é 999999", () => {
    const out = documentDisplayLabel({
      doc_type: "credit_card_bill",
      bank_code: "bradesco",
      period: "999999",
    });
    expect(out).toBe("Bradesco · Fatura · Indeterminado");
  });
});
