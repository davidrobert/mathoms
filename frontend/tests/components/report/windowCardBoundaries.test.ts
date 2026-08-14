import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const FORBIDDEN_SOURCE = `
  import { listTransactions } from "@/lib/api";
  import { usePeriodTransactions } from "@/hooks/usePeriodTransactions";

  export const forbidden = [listTransactions, usePeriodTransactions, 1 + 2, 4 / 2]
    .filter(Boolean)
    .sort();
`;

describe("gates dos cards de janela", () => {
  it("rejeita fetch, aritmética, filtro e ordenação no boundary do relatório", async () => {
    const eslint = new ESLint({ cwd: process.cwd() });
    const [result] = await eslint.lintText(FORBIDDEN_SOURCE, {
      filePath: "src/components/report/cards/ReceitasFonteCard.tsx",
    });
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
  });
});
