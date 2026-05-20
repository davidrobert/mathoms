/**
 * Unit tests — `lib/export.ts` (CSV BOM, XLSX auto-width, download flow)
 *
 * F6.5A.4
 *
 * Estratégia:
 * - exportToCSV: construir Blob → ler texto → asserir BOM + delimitador `;`
 * - exportToXLSX: construir Blob → confirmar tipo MIME + tamanho > 0
 * - downloadBlob: spy em createElement('a') + click() + revokeObjectURL
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as XLSX from "xlsx";

import { exportToCSV, exportToXLSX } from "@/lib/export";

const SAMPLE = [
  { Data: "2026-04-05", Descrição: "Mercado", Valor: -250.5 },
  { Data: "2026-04-01", Descrição: "Salário", Valor: 12_500 },
];

// Em vez de inspecionar o Blob (jsdom 25 tem Blob.text() quebrado em alguns
// caminhos), interceptamos o construtor Blob e capturamos as partes + opts
// diretamente. Funciona para verificar conteúdo CSV (string) e binário XLSX
// (ArrayBuffer/Uint8Array).
let lastBlobParts: BlobPart[] = [];
let lastBlobOptions: BlobPropertyBag | undefined;
let lastFilename: string | null = null;

const RealBlob = globalThis.Blob;

beforeEach(() => {
  lastBlobParts = [];
  lastBlobOptions = undefined;
  lastFilename = null;

  // Spy Blob constructor
  vi.stubGlobal(
    "Blob",
    class SpyBlob extends RealBlob {
      constructor(parts?: BlobPart[], opts?: BlobPropertyBag) {
        super(parts ?? [], opts);
        lastBlobParts = parts ?? [];
        lastBlobOptions = opts;
      }
    } as unknown as typeof Blob,
  );

  // createObjectURL e revokeObjectURL devem existir para o downloadBlob não crashar
  vi.spyOn(URL, "createObjectURL").mockImplementation(() => "blob:mock-url");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

  // Spy anchor.click() — não dispara navegação real
  const realCreateElement = document.createElement.bind(document);
  vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
    const el = realCreateElement(tag);
    if (tag === "a") {
      Object.defineProperty(el, "click", {
        value: vi.fn(() => {
          lastFilename = (el as HTMLAnchorElement).download;
        }),
        configurable: true,
      });
    }
    return el;
  });
});

// Helpers que reconstroem o conteúdo a partir das partes capturadas
function getCSVText(): string {
  return lastBlobParts
    .map((p) => (typeof p === "string" ? p : ""))
    .join("");
}
function getXLSXBuffer(): ArrayBuffer {
  // exportToXLSX passa Uint8Array via XLSX.write(..., {type:'array'})
  for (const p of lastBlobParts) {
    if (p instanceof ArrayBuffer) return p;
    if (ArrayBuffer.isView(p)) {
      const view = p as Uint8Array;
      // Cópia para ArrayBuffer "puro" (não SharedArrayBuffer) — TS 5.7+
      // distingue ArrayBufferLike, então fazemos new ArrayBuffer + copy.
      const out = new ArrayBuffer(view.byteLength);
      new Uint8Array(out).set(view);
      return out;
    }
  }
  throw new Error("Nenhum ArrayBuffer/Uint8Array encontrado nas partes do Blob");
}
function getMimeType(): string {
  return lastBlobOptions?.type ?? "";
}

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── exportToCSV ─────────────────────────────────────────────────────

describe("exportToCSV()", () => {
  it("noop quando dataset vazio", () => {
    exportToCSV([], "vazio");
    expect(lastBlobParts).toHaveLength(0);
  });

  it("inclui BOM UTF-8 no início do arquivo", () => {
    exportToCSV(SAMPLE, "tx");
    const text = getCSVText();
    expect(text.charCodeAt(0)).toBe(0xfeff);
  });

  it("usa `;` como delimitador (padrão Excel BR)", () => {
    exportToCSV(SAMPLE, "tx");
    const text = getCSVText().slice(1); // strip BOM
    const firstLine = text.split("\n")[0];
    expect(firstLine).toContain(";");
    expect(firstLine.split(";").length).toBeGreaterThan(1);
  });

  it("MIME type é text/csv com charset utf-8", () => {
    exportToCSV(SAMPLE, "tx");
    expect(getMimeType()).toContain("text/csv");
    expect(getMimeType().toLowerCase()).toContain("utf-8");
  });

  it("preserva acentos (UTF-8 + BOM)", () => {
    exportToCSV([{ Coluna: "ação café Ñ" }], "acentos");
    const text = getCSVText().slice(1);
    expect(text).toContain("ação");
    expect(text).toContain("café");
    expect(text).toContain("Ñ");
  });

  it("filename ganha extensão .csv automaticamente", () => {
    exportToCSV(SAMPLE, "transacoes");
    expect(lastFilename).toBe("transacoes.csv");
  });

  it("filename já com .csv não duplica extensão", () => {
    exportToCSV(SAMPLE, "transacoes.csv");
    expect(lastFilename).toBe("transacoes.csv");
  });

  it("revoga objectURL após download (memory leak guard)", () => {
    exportToCSV(SAMPLE, "tx");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });
});

// ─── exportToXLSX ────────────────────────────────────────────────────

describe("exportToXLSX()", () => {
  it("noop quando dataset vazio", () => {
    exportToXLSX([], "vazio");
    expect(lastBlobParts).toHaveLength(0);
  });

  it("MIME type é spreadsheetml.sheet (XLSX moderno)", () => {
    exportToXLSX(SAMPLE, "tx");
    expect(getMimeType()).toContain("spreadsheetml.sheet");
  });

  it("filename ganha .xlsx automaticamente", () => {
    exportToXLSX(SAMPLE, "transacoes");
    expect(lastFilename).toBe("transacoes.xlsx");
  });

  it("não duplica .xlsx se já presente", () => {
    exportToXLSX(SAMPLE, "transacoes.xlsx");
    expect(lastFilename).toBe("transacoes.xlsx");
  });

  it("auto-width: !cols configurado por chave (header + max conteúdo)", () => {
    // !cols não é persistido no formato XLSX — para verificar o auto-width,
    // espionamos book_append_sheet e capturamos a worksheet ANTES do write.
    let appendedWs: XLSX.WorkSheet | null = null;
    const spy = vi
      .spyOn(XLSX.utils, "book_append_sheet")
      .mockImplementation((wb, ws, name) => {
        appendedWs = ws;
        const sheetName = name ?? "Sheet1";
        Object.assign(wb.Sheets ?? (wb.Sheets = {}), { [sheetName]: ws });
        wb.SheetNames = [...(wb.SheetNames ?? []), sheetName];
        return sheetName;
      });

    exportToXLSX(SAMPLE, "tx");

    expect(appendedWs).not.toBeNull();
    const cols = (appendedWs as any)["!cols"] as XLSX.ColInfo[] | undefined;
    expect(cols).toBeDefined();
    expect(cols!.length).toBe(Object.keys(SAMPLE[0]).length);
    for (const col of cols!) {
      expect(col.wch).toBeLessThanOrEqual(50);
      expect(col.wch).toBeGreaterThan(0);
    }
    spy.mockRestore();
  });

  it("usa nome de sheet customizado quando passado", () => {
    exportToXLSX(SAMPLE, "tx", "MinhaPlan");
    const wb = XLSX.read(getXLSXBuffer(), { type: "array" });
    expect(wb.SheetNames).toContain("MinhaPlan");
  });

  it("default sheet name é 'Dados'", () => {
    exportToXLSX(SAMPLE, "tx");
    const wb = XLSX.read(getXLSXBuffer(), { type: "array" });
    expect(wb.SheetNames).toContain("Dados");
  });

  it("arquivo gerado é parseável de volta (round-trip)", () => {
    exportToXLSX(SAMPLE, "tx");
    const wb = XLSX.read(getXLSXBuffer(), { type: "array" });
    const back = XLSX.utils.sheet_to_json<typeof SAMPLE[0]>(
      wb.Sheets[wb.SheetNames[0]],
    );
    expect(back).toHaveLength(SAMPLE.length);
    expect(back[0]).toMatchObject({
      Data: SAMPLE[0].Data,
      Descrição: SAMPLE[0].Descrição,
    });
  });
});
