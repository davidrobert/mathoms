/**
 * Unit tests — `lib/cn.ts` (`cn()` helper)
 * F6.5A.6 — combina clsx + tailwind-merge para resolver conflitos de classes
 * Tailwind (`px-2 px-4` → mantém só `px-4`).
 */
import { describe, expect, it } from "vitest";
import { cn } from "@/lib/cn";

describe("cn()", () => {
  it("concatena classes simples", () => {
    expect(cn("a", "b", "c")).toBe("a b c");
  });

  it("ignora valores falsy (false, undefined, null, '')", () => {
    expect(cn("a", false, undefined, null, "", "b")).toBe("a b");
  });

  it("aceita objeto com toggle (clsx behavior)", () => {
    expect(cn("base", { active: true, disabled: false })).toBe("base active");
  });

  it("aceita arrays nested", () => {
    expect(cn(["a", ["b", "c"]], "d")).toBe("a b c d");
  });

  it("resolve conflito Tailwind: última classe ganha (px-2 vs px-4)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("resolve conflito complexo: text-red-500 + text-blue-500 → blue", () => {
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("preserva classes não-conflitantes ao resolver merge", () => {
    expect(cn("px-2 py-2", "px-4")).toBe("py-2 px-4");
  });

  it("retorna string vazia sem args", () => {
    expect(cn()).toBe("");
  });

  it("aceita variant condicional (padrão shadcn)", () => {
    const isPrimary = true;
    const result = cn("btn", isPrimary && "btn-primary", "rounded");
    expect(result).toBe("btn btn-primary rounded");
  });
});
