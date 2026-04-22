// ESLint flat config (v9) — A6g.6 slice 2 + A6g.6b, ADR-114.
//
// Propósito: gate bloqueante de TypeScript para impedir regressão do sweep
// A6g.4 (T1 `any` + T2 files >500 linhas). `max-lines` foi promovido a
// error em A6g.6b após zero offenders no baseline. `max-lines-per-function`
// continua em warn — 59 arquivos (64 offenders) em React components de
// tasks/report/config precisam sweep dedicado (lane futura) antes de
// promover.
//
// Excluídos: src/generated/ (codegen), .next/, coverage/, dist/.
//
// Rodar local: `cd frontend && npx eslint src/`

import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    ignores: [
      "src/generated/**",
      ".next/**",
      "coverage/**",
      "dist/**",
      "node_modules/**",
      "tests/**",
      "scripts/**",
      "playwright-report/**",
      "test-results/**",
      "next-env.d.ts",
    ],
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        React: "readonly",
        JSX: "readonly",
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // Gate imediato: bloqueia regressão de A6g.4 (T1). Sweep varreu repo
      // inteiro; qualquer `any` novo = erro.
      "@typescript-eslint/no-explicit-any": "error",

      // Desligamos no-unused-vars do core; regra equivalente do TS plugin
      // entende melhor overloads e type-only imports.
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],

      // Falsos positivos comuns em Next.js 16 + React 19 com auto-imports.
      "no-undef": "off",

      // Prefere `const` quando reatribuição não acontece.
      "prefer-const": "error",

      // React rules — bloqueantes.
      "react/jsx-key": "error",
      "react/jsx-no-target-blank": "error",
      "react/no-direct-mutation-state": "error",
      "react-hooks/rules-of-hooks": "error",

      // Progressivos → decididos em A6g.6b.
      "react-hooks/exhaustive-deps": "warn",
      // Promovido a error em A6g.6b (zero offenders após A6g.4).
      "max-lines": [
        "error",
        { max: 500, skipBlankLines: true, skipComments: true },
      ],
      // Mantido em warn — 59 arquivos (64 offenders) em components React
      // de tasks/report/config; promoção depende de sweep refactor dedicado.
      "max-lines-per-function": [
        "warn",
        { max: 60, skipBlankLines: true, skipComments: true, IIFEs: true },
      ],
    },
  },
];
