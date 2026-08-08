/**
 * Contraste do badge Fator-R (`FatorRBadge`, S8), lido de `tokens.css` e
 * calculado por WCAG 2.1. Irmão de `parecerToneContrast.test.ts`, mesma
 * aritmética, outro par (componente, fundo).
 *
 * Por que existe além do axe: o `a11y.@critical.spec.ts` só alcança o variante
 * **Anexo III**. A fixture `medium` fixa `fator_r_faixa: "anexo_iii"`
 * (`tests/e2e/fixtures/reports/medium.json`), e o helper de mock stubba
 * endpoint, não campo — não há como pedir `anexo_v` sem autorar fixture nova.
 * Só que `anexo_v` é branch de produção real
 * (`pipeline/domain/services/tributario/cascata_calculator.py:319`, Fator-R
 * abaixo do limiar) e era o PIOR dos dois: 1,86:1 com `--semantic-alert`
 * como texto. Um gate que passasse verde ali estaria passando por **ausência
 * do caso**, não por correção. Este teste mede os dois variantes sem depender
 * de fixture, de render ou de tema injetado.
 *
 * O que ele mata: alguém "simplifica" `--semantic-gain-on-tint` de volta para
 * `--semantic-gain` (dedup tentador — no dark os dois são o mesmo hex), e o
 * badge volta a 4,09:1 em light.
 *
 * Limite honesto: a aritmética assume o fundo real do badge — tint de 15% da
 * cor base sobre `--surface-card`. Se o componente trocar de fundo, isto deixa
 * de valer e quem pega é o axe. Por isso o par está nomeado aqui, não inferido.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const TOKENS_CSS = readFileSync(
  join(__dirname, "..", "..", "..", "src", "styles", "tokens.css"),
  "utf-8",
);

/** Ver nota em `parecerToneContrast.test.ts`: classificar por seletor cobre as
 *  4 formas em que `tokens.css` declara tema (`:root`, `:root [data-report-scope]`,
 *  `.dark, [data-theme='dark']`, `.dark [data-report-scope]`). */
function tokenMap(theme: "light" | "dark"): Map<string, string> {
  const out = new Map<string, string>();
  for (const [, selector, body] of TOKENS_CSS.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (/\bdark\b/.test(selector) !== (theme === "dark")) continue;
    for (const [, name, hex] of body.matchAll(/--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b/g)) {
      out.set(name, hex);
    }
  }
  return out;
}

const TOKENS = { light: tokenMap("light"), dark: tokenMap("dark") } as const;

function tokenValue(name: string, theme: "light" | "dark"): string {
  const hex = TOKENS[theme].get(name);
  if (!hex) throw new Error(`token --${name} não encontrado no tema ${theme}`);
  return hex;
}

function channels(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

function relativeLuminance(hex: string): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const [r, g, b] = channels(hex);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrastRatio(fg: string, bg: string): number {
  const a = relativeLuminance(fg);
  const b = relativeLuminance(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function tint(token: string, bg: string, pct: number): string {
  const f = channels(token);
  const b = channels(bg);
  const a = pct / 100;
  const mixed = f.map((v, i) => Math.round(v * a + b[i] * (1 - a)));
  return `#${mixed.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

const AA_TEXTO_PEQUENO = 4.5;

/** O texto do badge é `text-[0.65rem]` = 10,4px normal — bem abaixo do limiar
 *  de "large text" (24px normal / 18,66px bold), então vale 4,5:1 e não 3:1. */
const TINT_PCT = 15;

/** Espelha `FatorRBadge` em `CascataFiscalCard.tsx`: fundo é tint da cor base,
 *  texto é o par `-on-tint`. */
const VARIANTES = [
  { faixa: "anexo_iii", bgToken: "semantic-gain", fgToken: "semantic-gain-on-tint" },
  { faixa: "anexo_v", bgToken: "semantic-alert", fgToken: "semantic-alert-on-tint" },
];

describe.each(["light", "dark"] as const)("badge Fator-R — %s", (theme) => {
  const card = () => tokenValue("surface-card", theme);

  it.each(VARIANTES)("$faixa ≥ 4,5:1", (v) => {
    const bg = tint(tokenValue(v.bgToken, theme), card(), TINT_PCT);
    const ratio = contrastRatio(tokenValue(v.fgToken, theme), bg);
    expect(
      ratio,
      `${v.faixa} em ${theme}: ${ratio.toFixed(2)}:1`,
    ).toBeGreaterThanOrEqual(AA_TEXTO_PEQUENO);
  });
});

/** `SEVERITY_TEXT_CLASS` de `alocacaoCardParts.tsx` — texto sobre o card, sem
 *  tint. Entrou aqui porque o #1294 devolveu o card de Alocação ao render
 *  depois de ~3 meses ausente, e com ele voltou `--semantic-alert` como texto
 *  sobre branco: **2,06:1** nos 14px da célula de desvio, o pior contraste do
 *  relatório. Os outros 3 membros passam com a cor base (17,85 / 6,47 / 4,76),
 *  então só `atencao` troca de token. */
const ALOCACAO_SEVERIDADES = [
  { severidade: "alinhado", fgToken: "surface-foreground" },
  { severidade: "atencao", fgToken: "semantic-alert-on-tint" },
  { severidade: "rebalancear", fgToken: "semantic-danger" },
  { severidade: "neutro", fgToken: "surface-muted-foreground" },
];

describe.each(["light", "dark"] as const)(
  "desvio da Alocação sobre o card — %s",
  (theme) => {
    it.each(ALOCACAO_SEVERIDADES)("$severidade ≥ 4,5:1", (s) => {
      const ratio = contrastRatio(
        tokenValue(s.fgToken, theme),
        tokenValue("surface-card", theme),
      );
      expect(
        ratio,
        `${s.severidade} em ${theme}: ${ratio.toFixed(2)}:1`,
      ).toBeGreaterThanOrEqual(AA_TEXTO_PEQUENO);
    });
  },
);

describe("o par -on-tint não pode colapsar de volta na cor base", () => {
  // No dark os dois tokens SÃO o mesmo hex, então o dedup parece seguro e o
  // teste acima sozinho não explica por que o par existe. Estes dois mostram.
  it.each([
    { faixa: "anexo_iii", token: "semantic-gain", esperado: 4.09 },
    { faixa: "anexo_v", token: "semantic-alert", esperado: 1.86 },
  ])("`--$token` como texto reprova em light ($faixa)", ({ token, esperado }) => {
    const base = tokenValue(token, "light");
    const ratio = contrastRatio(base, tint(base, tokenValue("surface-card", "light"), TINT_PCT));
    expect(ratio).toBeLessThan(AA_TEXTO_PEQUENO);
    expect(ratio).toBeCloseTo(esperado, 1);
  });

  it("`--semantic-alert` sobre o card **sem** tint é o pior caso: 2,06:1", () => {
    const ratio = contrastRatio(
      tokenValue("semantic-alert", "light"),
      tokenValue("surface-card", "light"),
    );
    expect(ratio).toBeLessThan(AA_TEXTO_PEQUENO);
    expect(ratio).toBeCloseTo(2.06, 1);
  });
});
