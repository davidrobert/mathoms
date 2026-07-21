/**
 * Specs de `@/lib/categoryLabels` — mapa único + humanize fallback (A37.l6).
 *
 * KR-B: para toda key de categoria das superfícies do relatório, o label
 * nunca contém `_` nem inicia com minúscula-código. O fallback cobre keys
 * futuras do pipeline sem regressão visual.
 */
import { describe, expect, it } from "vitest";

import { CATEGORY_LABELS, humanizeCategoryLabel } from "@/lib/categoryLabels";

describe("CATEGORY_LABELS", () => {
  it("cobre as 4 keys que vazavam cru (PD-03)", () => {
    expect(CATEGORY_LABELS["lazer"]).toBe("Lazer");
    expect(CATEGORY_LABELS["das_simples"]).toBe("DAS (Simples Nacional)");
    expect(CATEGORY_LABELS["folha_pj"]).toBe("Folha PJ");
    expect(CATEGORY_LABELS["aporte_investimento"]).toBe("Aporte em investimentos");
  });

  it("KR-B: todo label do mapa é humano — sem `_`, sem inicial minúscula", () => {
    for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
      expect(label, `label de ${key}`).not.toMatch(/_/);
      expect(label.charAt(0), `label de ${key}`).not.toMatch(/[a-z]/);
    }
  });
});

describe("humanizeCategoryLabel", () => {
  it("resolve keys mapeadas para o label canônico", () => {
    expect(humanizeCategoryLabel("nao_identificado")).toBe("Não identificado");
    expect(humanizeCategoryLabel("lazer_viagens")).toBe("Lazer e viagens");
  });

  it("fallback de key desconhecida: troca `_` por espaço e capitaliza", () => {
    expect(humanizeCategoryLabel("categoria_futura_x")).toBe("Categoria futura x");
    expect(humanizeCategoryLabel("outro")).toBe("Outro");
  });

  it("preserva label já humanizado vindo do wire (paridade .title())", () => {
    // fluxo_caixa_enricher emite .title() → "Nao Identificado"; não deve quebrar.
    expect(humanizeCategoryLabel("Nao Identificado")).toBe("Nao Identificado");
  });

  it("string vazia não explode nem vira label fantasma", () => {
    expect(humanizeCategoryLabel("")).toBe("");
  });
});
