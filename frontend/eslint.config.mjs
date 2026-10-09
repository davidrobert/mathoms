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

// A40.l3 · ADR-306 D1 — gate de CONSUMO dos campos com base temporal.
//
// Por que aqui e não num script em dev/: roda no step ESLint de `frontend-checks`
// (job já em `all-green.needs`), custo ~0.
//
// **O que esta regra pega:** leitura direta de um campo cuja base temporal está
// declarada em outro campo (`janela`/`janela_meses`) — o caminho pelo qual um
// número perde o rótulo. `resolveFluxoJanelaMensal`/`resolveConsumoBases`/
// `resolveTaxaPoupanca` devolvem o par (valor, rótulo) e são os únicos leitores
// legítimos.
//
// **O que esta regra NÃO pega, e é honesto dizer:** componente que deriva a
// própria média a partir de uma série já renderizada (foi exatamente o caso do
// `ReceitaDespesaMensalChart`, que somava `receita_datasets`/`despesa_datasets` e
// dividia por `data.length` — nenhum campo restrito envolvido). Essa classe cai
// no **invariante de seção** de `janelaCanonica.contract.test.tsx`, que varre
// todo `X/mês` renderizado por `S2FluxoCaixaSection` composta. As duas camadas
// são complementares: lint detém o acesso, o invariante detém a aritmética
// local. Comentário que prometesse garantia única aqui seria a própria classe de
// defeito que esta sprint fecha.
const CAMPOS_MENSALIZADOS = [
  "receita_recorrente_mensal",
  "despesa_mensal_media",
  // Custo essencial mensalizado (ADR-191) — mesma família, mesmo risco.
  "despesa_mensal_essencial",
  "taxa_poupanca_recorrente",
  // Headline do hero: `ratios.taxa_poupanca_*_pct` são os campos que renderizam
  // o KPI de Taxa de Poupança e carregam base declarada em `ratios.janela`.
  "taxa_poupanca_recorrente_pct",
  "taxa_poupanca_total_pct",
  "total_pontuais",
  "total_pontuais_janela",
];

const MENSAGEM_MENSALIZACAO =
  "ADR-306 D1: campo com base temporal declarada não pode ser lido direto — use " +
  "resolveFluxoJanelaMensal()/resolveConsumoBases()/resolveTaxaPoupanca() " +
  "(report/utils/fluxoJanela.ts), que devolvem o par (valor, rótulo de janela). " +
  "Número sem base declarada é o defeito que A40.l3 fechou.";

const MENSALIZACAO_RESTRITA = CAMPOS_MENSALIZADOS.flatMap((campo) => [
  {
    // `fluxo.despesa_mensal_media`
    selector: `MemberExpression[computed=false] > Identifier.property[name="${campo}"]`,
    message: MENSAGEM_MENSALIZACAO,
  },
  {
    // `fluxo["despesa_mensal_media"]` e `getPath(data, "…despesa_mensal_media")`
    selector: `Literal[value=/${campo}/]`,
    message: MENSAGEM_MENSALIZACAO,
  },
  {
    // `const { despesa_mensal_media } = fluxo`
    selector: `Property > Identifier.key[name="${campo}"]`,
    message: MENSAGEM_MENSALIZACAO,
  },
]);

// Número com casas em copy pt-BR leva vírgula decimal (COPY_GUIDELINES §4.6) e
// passa por `formatNumber`/`formatPercent` (`@/lib/format`). Mesmo racional de
// custo do gate acima: step ESLint de `frontend-checks` + hook `eslint-frontend`,
// nenhum processo novo.
//
// **O que esta regra pega:** toda chamada de `toFixed(n)` com n ≠ 0 e de
// `toPrecision` — com ou sem `%`, com ou sem unidade, guardada em variável ou
// não. Elas não conhecem locale ("42.8%", "1.5 MB", "71.2 meses"), e a vírgula
// escrita à mão (`.replace(".", ",")`) arredonda o binário (0.35 → "0,3", onde o
// Intl dá "0,4") e não agrupa milhar. Substitui os gates de `toFixed` colado ao
// `%` (#2091, #2123) e de vírgula à mão (#2126), que recortavam pela grafia dos
// ofensores já vistos: eram 56 chamadas em 2026-10-08 e nenhuma depois deles e do
// PR desta regra. `toFixed(0)` fica de fora: inteiro não tem separador decimal.
//
// **O que NÃO pega:** número cru interpolado (`${pct}%`, `${meses} meses` de um
// campo fracionário). Esse fica com os testes de render, que assertam a vírgula e
// recusam o ponto (`tests/shared/percentualPtBr.ts`, `tests/shared/decimalPtBr.ts`).
//
// **Uso fora de copy** (CSS inline, path SVG, payload decimal): helper nomeado em
// `src/lib/` com isenção por arquivo, no padrão do `fluxoJanela.ts` abaixo. Nunca
// `eslint-disable` na linha: ele desliga a regra inteira, e a mensalização e o
// money dos cards de janela caem junto. Prova do seletor, com inventário zero:
// `tests/components/report/windowCardBoundaries.test.ts`.
const MENSAGEM_NUMERO_COM_CASAS =
  "Número com casas em copy pt-BR passa por formatNumber(valor, casas) ou " +
  "formatPercent(valor, casas) de @/lib/format. `toFixed`/`toPrecision` não conhecem " +
  "locale (\"1.5 MB\", \"42.8%\") e a vírgula à mão arredonda o binário " +
  "(0.35 → \"0,3\") (COPY_GUIDELINES §4.6).";

const NUMERO_COM_CASAS_RESTRITO = [
  {
    selector:
      'CallExpression[callee.property.name=/^to(Fixed|Precision)$/]:not([arguments.0.value=0])',
    message: MENSAGEM_NUMERO_COM_CASAS,
  },
];

const CARD_MONEY_MESSAGE =
  "A40.l44: cards de janela renderizam o payload table-ready; aritmética, filtro " +
  "ou ordenação monetária pertencem ao produtor E5.";

const CARD_MONEY_RESTRICTIONS = [
  {
    selector: 'BinaryExpression[operator="+"]',
    message: CARD_MONEY_MESSAGE,
  },
  {
    selector: 'BinaryExpression[operator="/"]',
    message: CARD_MONEY_MESSAGE,
  },
  ...["filter", "sort", "reduce"].map((method) => ({
    selector: `CallExpression[callee.property.name="${method}"]`,
    message: CARD_MONEY_MESSAGE,
  })),
];

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

      // A40.l3 (ADR-306 D1) — gate de CONSUMO da mensalização de fluxo.
      // Ver bloco dedicado abaixo para o racional e a allowlist. Número com
      // casas (COPY_GUIDELINES §4.6) vale para todo o src/, não só o relatório.
      "no-restricted-syntax": [
        "error",
        ...MENSALIZACAO_RESTRITA,
        ...NUMERO_COM_CASAS_RESTRITO,
      ],
    },
  },
  {
    // Os blocos abaixo que redefinem `no-restricted-syntax` SUBSTITUEM este (flat
    // config não concatena opções de regra) — por isso cada um repete o array.
    files: ["src/components/report/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...MENSALIZACAO_RESTRITA,
        ...NUMERO_COM_CASAS_RESTRITO,
      ],
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@/hooks/usePeriodTransactions",
              message:
                "A40.l44: relatório seleciona fluxo_caixa.janelas; não busca transações para reagregar.",
            },
            {
              name: "@/lib/api",
              importNames: ["listTransactions"],
              message:
                "A40.l44: listTransactions não cruza a fronteira do relatório.",
            },
            {
              name: "@/lib/api/transactions",
              importNames: ["listTransactions"],
              message:
                "A40.l44: listTransactions não cruza a fronteira do relatório.",
            },
          ],
        },
      ],
    },
  },
  {
    files: [
      "src/components/report/cards/ReceitasFonteCard.tsx",
      "src/components/report/cards/ReceitasNaturezaStrip.tsx",
      "src/components/report/cards/OrcamentoProspectivoCard.tsx",
    ],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...MENSALIZACAO_RESTRITA,
        ...NUMERO_COM_CASAS_RESTRITO,
        ...CARD_MONEY_RESTRICTIONS,
      ],
    },
  },
  {
    // Único leitor legítimo dos campos com base temporal: o seletor canônico.
    // Allowlist por arquivo (não por linha) porque a regra é "quem lê", não
    // "onde lê" — e é o seletor que garante o par (valor, rótulo). `janelaLabel.ts`
    // NÃO entra: ele só interpreta o vocabulário `janela`/`janela_meses`, nunca
    // toca campo de valor. A isenção é da mensalização, não do número com casas.
    files: ["src/components/report/utils/fluxoJanela.ts"],
    rules: {
      "no-restricted-syntax": ["error", ...NUMERO_COM_CASAS_RESTRITO],
    },
  },
];
