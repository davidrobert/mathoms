import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const FORBIDDEN_SOURCE = `
  import { listTransactions } from "@/lib/api";
  import { usePeriodTransactions } from "@/hooks/usePeriodTransactions";

  export const forbidden = [listTransactions, usePeriodTransactions, 1 + 2, 4 / 2]
    .filter(Boolean)
    .sort();
`;

const WINDOW_CARDS = [
  "src/components/report/cards/ReceitasFonteCard.tsx",
  "src/components/report/cards/ReceitasNaturezaStrip.tsx",
] as const;

describe("gates dos cards de janela", () => {
  it.each(WINDOW_CARDS)(
    "rejeita fetch, aritmética, filtro e ordenação em %s",
    async (filePath) => {
      const eslint = new ESLint({ cwd: process.cwd() });
      const [result] = await eslint.lintText(FORBIDDEN_SOURCE, { filePath });
      const restrictedImports = result.messages.filter(
        (message) => message.ruleId === "no-restricted-imports",
      );
      const moneyOperations = result.messages.filter(
        (message) =>
          message.ruleId === "no-restricted-syntax" &&
          message.message.includes("cards de janela"),
      );

      expect(restrictedImports).toHaveLength(2);
      expect(moneyOperations).toHaveLength(4);
    },
  );
});

// Gate de número com casas (COPY_GUIDELINES §4.6, `NUMERO_COM_CASAS_RESTRITO`).
// Com zero ofensores no src/, só esta prova mostra que o seletor ainda casa; mora
// aqui porque o ESLint já é carregado neste arquivo e o Vitest custa por arquivo.
const NUMERO_COM_CASAS_SOURCE = `
  export const casas = (x: number, y: number | undefined, n: number) => [
    x.toFixed(1),
    y?.toFixed(2),
    x.toFixed(n),
    x.toPrecision(3),
  ];
`;

const INTEIRO_SOURCE = `
  export const inteiros = (x: number, y: number | undefined) => [x.toFixed(0), y?.toFixed(0)];
`;

// Os 4 blocos que definem `no-restricted-syntax`: flat config substitui a regra
// em vez de concatenar, e cada bloco precisa repetir o gate.
const BLOCOS_DO_GATE = [
  "src/lib/numeroComCasas.ts",
  "src/components/report/numeroComCasas.ts",
  "src/components/report/cards/ReceitasFonteCard.tsx",
  "src/components/report/utils/fluxoJanela.ts",
] as const;

describe("gate de número com casas em copy pt-BR", () => {
  const eslint = new ESLint({ cwd: process.cwd() });

  async function reportsDoGate(source: string, filePath: string) {
    const [result] = await eslint.lintText(source, { filePath });
    return result.messages.filter(
      (message) =>
        message.ruleId === "no-restricted-syntax" &&
        message.message.includes("Número com casas em copy pt-BR"),
    );
  }

  // 4 chamadas, 4 reports: `y?.toFixed(2)` não pode contar duas vezes.
  it.each(BLOCOS_DO_GATE)("reprova toFixed com casas e toPrecision em %s", async (filePath) => {
    expect(await reportsDoGate(NUMERO_COM_CASAS_SOURCE, filePath)).toHaveLength(4);
  });

  it.each(BLOCOS_DO_GATE)("aceita toFixed(0) em %s", async (filePath) => {
    expect(await reportsDoGate(INTEIRO_SOURCE, filePath)).toHaveLength(0);
  });
});
