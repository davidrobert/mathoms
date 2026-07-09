import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, it, expect } from "vitest";

import {
  ALOCACAO_CLASSES,
  ALOCACAO_CLASS_KEYS,
  ALOCACAO_FAMILIES,
} from "@/lib/alocacaoClasses";
import {
  completeWithCaixa,
  rebalGroupOf,
  REBAL_GROUPS,
  sumPcts,
  type Pcts,
} from "@/app/(app)/plano/alocacao/wizard/_components/constants";

const SCHEMA_PATH = path.resolve(
  __dirname,
  "../../../config/schemas/goal.alocacao_alvo.v2.schema.json",
);

function schemaInputKeys(): string[] {
  const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));
  return schema.properties.inputs.required as string[];
}

describe("alocacaoClasses — paridade com o schema v2", () => {
  it("os ids batem (ordem + conjunto) com inputs.required do schema", () => {
    const schemaKeys = schemaInputKeys();
    const classIds = ALOCACAO_CLASSES.map((c) => c.id);
    expect(classIds).toEqual(schemaKeys);
  });

  it("ALOCACAO_CLASS_KEYS reflete os ids na mesma ordem", () => {
    expect([...ALOCACAO_CLASS_KEYS]).toEqual(ALOCACAO_CLASSES.map((c) => c.id));
  });

  it("ids são únicos", () => {
    const ids = ALOCACAO_CLASSES.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("cores usam sempre var(--chart-N) (sem hex literal)", () => {
    for (const c of ALOCACAO_CLASSES) {
      expect(c.colorVar).toMatch(/^var\(--chart-\d+\)$/);
    }
  });

  it("labels e labelFull não são vazios", () => {
    for (const c of ALOCACAO_CLASSES) {
      expect(c.label.trim().length).toBeGreaterThan(0);
      expect(c.labelFull.trim().length).toBeGreaterThan(0);
    }
  });

  it("famílias cobrem todas as classes, sem sobra e na ordem", () => {
    const fromFamilies = ALOCACAO_FAMILIES.flatMap((f) => f.classes);
    expect(fromFamilies).toEqual([...ALOCACAO_CLASSES]);
  });
});

const ZERO: Pcts = {
  rf_pos_pct: 0,
  rf_pre_pct: 0,
  rf_ipca_pct: 0,
  acoes_br_pct: 0,
  acoes_int_pct: 0,
  fiis_pct: 0,
  caixa_pct: 0,
};

describe("sumPcts / completeWithCaixa", () => {
  it("sumPcts soma as 7 classes", () => {
    expect(sumPcts({ ...ZERO, rf_pos_pct: 40, acoes_br_pct: 35 })).toBe(75);
  });

  it("Completar com Caixa joga o resíduo em caixa_pct", () => {
    const before = { ...ZERO, rf_pos_pct: 50, acoes_br_pct: 30, caixa_pct: 0 };
    const after = completeWithCaixa(before);
    expect(after.caixa_pct).toBe(20);
    expect(sumPcts(after)).toBe(100);
  });

  it("ignora o caixa anterior ao calcular o resíduo", () => {
    const before = { ...ZERO, rf_pos_pct: 60, caixa_pct: 99 };
    expect(completeWithCaixa(before).caixa_pct).toBe(40);
  });

  it("nunca produz caixa negativa quando as outras já passam de 100", () => {
    const before = { ...ZERO, rf_pos_pct: 70, acoes_br_pct: 60, caixa_pct: 5 };
    expect(completeWithCaixa(before).caixa_pct).toBe(0);
  });
});

describe("rebalGroupOf — enum plano → grupo da UI", () => {
  it("mapeia cada modo para o grupo correto", () => {
    expect(rebalGroupOf("por_aporte")).toBe("por_aporte");
    expect(rebalGroupOf("trimestral")).toBe("periodico");
    expect(rebalGroupOf("semestral")).toBe("periodico");
    expect(rebalGroupOf("anual")).toBe("periodico");
    expect(rebalGroupOf("trigger_5pct")).toBe("gatilho");
    expect(rebalGroupOf("trigger_10pct")).toBe("gatilho");
  });

  it("cada grupo expõe um modo selecionável (value ou defaultValue)", () => {
    for (const group of REBAL_GROUPS) {
      const selectable = group.value ?? group.defaultValue;
      expect(selectable).toBeTruthy();
      if (group.options) {
        expect(group.options.map((o) => o.value)).toContain(group.defaultValue);
      }
    }
  });
});
