/**
 * A40.l22 — contraste dos rótulos de severidade/prioridade do parecer, lido de
 * `tokens.css` e calculado por WCAG 2.1.
 *
 * Por que este teste existe além do axe: a varredura axe de `S_parecer` vive em
 * `a11y.@critical.spec.ts`, que é **label-gated** (`e2e`) e estava skipped em
 * 12/12 runs recentes. Um fix de contraste cuja única guarda é um job que não
 * roda é um fix sem gate. Este spec roda em `frontend-checks`, que está em
 * `all-green.needs`.
 *
 * O que ele mata: alguém "simplifica" `textToken` de volta para `token`
 * (dedup óbvio — 3 dos 4 membros são iguais), e o rótulo Média volta a 1,97:1.
 *
 * Limite honesto: o cálculo assume o fundo real de cada rótulo — tint de 6% do
 * token sobre `--surface-card` nos riscos, `--surface-card` puro no movimento.
 * Se o componente mudar de fundo, esta aritmética deixa de valer e o axe é quem
 * pega. Por isso o par (componente, fundo) está nomeado aqui, não inferido.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const TOKENS_CSS = readFileSync(
  join(__dirname, "..", "..", "..", "src", "styles", "tokens.css"),
  "utf-8",
);

/** Mapa token → hex por tema.
 *
 * `tokens.css` não tem UM bloco por tema: light vive em `:root` e em
 * `:root [data-report-scope]`, dark em `.dark, [data-theme='dark']` **e** em
 * `.dark [data-report-scope], …`. Splitar por `.dark {` (a forma óbvia) perdia
 * os tokens `--report-*` do dark e o teste morria com "token não encontrado" em
 * vez de medir — falso-vermelho que esconde o falso-verde. Classificar por
 * seletor cobre as 4 formas.
 */
function tokenMap(theme: "light" | "dark"): Map<string, string> {
  const out = new Map<string, string>();
  for (const [, selector, body] of TOKENS_CSS.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const isDark = /\bdark\b/.test(selector);
    if (isDark !== (theme === "dark")) continue;
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

/** `color-mix(in oklab, <token> 6%, transparent)` sobre `bg` — em oklab o
 *  resultado difere de sRGB por ~1 nível por canal, o que não move o ratio na
 *  2ª decimal; a margem exigida abaixo absorve isso. */
function tint(token: string, bg: string, pct: number): string {
  const f = channels(token);
  const b = channels(bg);
  const a = pct / 100;
  const mixed = f.map((v, i) => Math.round(v * a + b[i] * (1 - a)));
  return `#${mixed.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

const AA_TEXTO_PEQUENO = 4.5;

/** Espelha `SEVERIDADE_TONE` de `ParecerRisksTable` — rótulo sobre tint de 6%. */
const SEVERIDADES = [
  { label: "Crítica", token: "semantic-loss", textToken: "semantic-loss" },
  { label: "Alta", token: "semantic-loss", textToken: "semantic-loss" },
  { label: "Média", token: "semantic-alert", textToken: "report-alert-warning-text" },
  { label: "Baixa", token: "semantic-info-financial", textToken: "semantic-info-financial" },
];

/** Espelha `PRIORIDADE_TONE` de `ParecerMovimentoCard` — rótulo sobre o card. */
const PRIORIDADES = [
  { label: "P0", textToken: "semantic-loss" },
  { label: "P1", textToken: "report-alert-warning-text" },
  { label: "P2", textToken: "semantic-info-financial" },
];

/** Espelha o badge de tier de `ParecerHeroDiagnostico` — par sólido do ADR-117. */
const BADGES = [
  { label: "Premium", bg: "report-badge-green-bg", fg: "report-badge-green-text" },
  { label: "Amostra", bg: "report-badge-neutral-bg", fg: "report-badge-neutral-text" },
];

describe.each(["light", "dark"] as const)("contraste do parecer — %s", (theme) => {
  const card = () => tokenValue("surface-card", theme);

  it.each(SEVERIDADES)("rótulo de severidade $label ≥ 4,5:1", (sev) => {
    const bg = tint(tokenValue(sev.token, theme), card(), 6);
    const ratio = contrastRatio(tokenValue(sev.textToken, theme), bg);
    expect(ratio, `severidade ${sev.label} em ${theme}: ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
      AA_TEXTO_PEQUENO,
    );
  });

  it.each(PRIORIDADES)("rótulo de prioridade $label ≥ 4,5:1", (pri) => {
    const ratio = contrastRatio(tokenValue(pri.textToken, theme), card());
    expect(ratio, `prioridade ${pri.label} em ${theme}: ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
      AA_TEXTO_PEQUENO,
    );
  });

  it.each(BADGES)("badge de tier $label ≥ 4,5:1", (badge) => {
    const ratio = contrastRatio(tokenValue(badge.fg, theme), tokenValue(badge.bg, theme));
    expect(ratio, `badge ${badge.label} em ${theme}: ${ratio.toFixed(2)}:1`).toBeGreaterThanOrEqual(
      AA_TEXTO_PEQUENO,
    );
  });
});

describe("o rótulo não pode voltar a usar o token decorativo", () => {
  // O dedup tentador: 3 dos 4 membros têm `textToken === token`, então parece
  // campo redundante. Este teste mostra POR QUE o 4º existe.
  it("`--semantic-alert` como texto reprova em light — é o caso que criou o campo", () => {
    const bg = tint(tokenValue("semantic-alert", "light"), tokenValue("surface-card", "light"), 6);
    expect(contrastRatio(tokenValue("semantic-alert", "light"), bg)).toBeLessThan(
      AA_TEXTO_PEQUENO,
    );
  });
});
