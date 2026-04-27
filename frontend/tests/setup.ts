/**
 * Vitest global setup — F6.5 (sub-fase 6.5A.1)
 *
 * Carrega antes de cada arquivo de teste:
 * 1. jest-dom matchers (toBeInTheDocument, toHaveClass, etc.)
 * 2. MSW server lifecycle (start/reset/close)
 * 3. Polyfills mínimos para jsdom (matchMedia, IntersectionObserver, ResizeObserver)
 * 4. Reset de localStorage entre testes
 *
 * NÃO incluir lógica de produto aqui. Apenas plumbing de teste.
 */
import "@testing-library/jest-dom/vitest";
import { createElement, Fragment, type ReactNode } from "react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./mocks/server";

/** F12.1 · ADR-130 — `useTranslations()` devolve identidade (chave → chave)
 * por default em testes que não montam `NextIntlClientProvider`. Suítes
 * que precisam de strings reais (tests/i18n/**) importam o provider
 * explicitamente e re-mockam `next-intl` localmente se necessário. */
vi.mock("next-intl", async () => {
  const actual = await vi.importActual<typeof import("next-intl")>("next-intl");
  return {
    ...actual,
    useTranslations: () => (key: string) => key,
    useLocale: () => "pt-BR",
  };
});

/** Mock global de `react-chartjs-2` (2026-04-27).
 *
 * Pós-v2.E.6 (refactor 502-line em ReceitaDespesaMensalChart), múltiplos
 * componentes do report renderizam Chart.js wrappers no caminho default.
 * jsdom não tem o pkg `canvas`; cada `acquireContext` falha, React entra
 * em loop de re-render via useEffect, Vitest hangea (run 24999684508 do
 * PR #10 ficou 22m54s antes do timeout).
 *
 * Stub global retorna componentes inertes; testes que precisam exercitar
 * o flow imperativo (ref → chart.update / getDatasetMeta) sobrescrevem
 * com `vi.mock` local — Vitest hoist do per-file ganha do setup global.
 * Padrão já usado em `ReceitaDespesaMensalChart.test.tsx`.
 */
vi.mock("react-chartjs-2", () => {
  const stub = () => null;
  const stubWithRef = (props: { ref?: (instance: unknown) => void }) => {
    if (typeof props.ref === "function") {
      props.ref({
        update: () => undefined,
        getDatasetMeta: () => ({ hidden: false }),
        toBase64Image: () => "data:image/png;base64,",
      });
    }
    return null;
  };
  return {
    Chart: stubWithRef,
    Line: stub,
    Bar: stub,
    Doughnut: stub,
    Pie: stub,
    PolarArea: stub,
    Radar: stub,
    Scatter: stub,
    Bubble: stub,
    getElementAtEvent: () => null,
    getDatasetAtEvent: () => null,
    getElementsAtEvent: () => null,
  };
});

/** Default workspace para páginas `(app)/` que usam `useWorkspace()` sem provider real. */
vi.mock("@/lib/WorkspaceProvider", () => ({
  WorkspaceProvider: ({ children }: { children: ReactNode }) =>
    createElement(Fragment, null, children),
  useWorkspace: () => ({
    workspace: {
      id: "ws-1",
      name: "Test WS",
      family_surname: "Test",
      role: "owner" as const,
      joined_at: "2026-01-01T00:00:00.000Z",
    },
    workspaces: [],
    isLoading: false,
    error: null,
    refresh: vi.fn(),
  }),
}));

// ─── MSW lifecycle ───
// Padrão "error" garante que toda chamada não-mockada quebre o teste em vez de
// silenciosamente passar — evita falsos positivos em integration tests.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup(); // unmount React trees
  server.resetHandlers(); // restaura handlers default entre testes
  localStorage.clear();
  sessionStorage.clear();
});
afterAll(() => server.close());

// ─── Polyfills jsdom ───

// localStorage / sessionStorage (jsdom 25 + vitest 2.1.x não instanciam a
// Storage Web API corretamente — `localStorage` retorna `{}` sem métodos).
// Polyfill mínimo (Map-backed) é suficiente para tests; troque por uma impl
// mais fiel se algum test depender de eventos `storage` cross-frame.
function makeStorageShim(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? (store.get(key) as string) : null;
    },
    key(i: number) {
      return Array.from(store.keys())[i] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  };
}

if (typeof window !== "undefined") {
  // Sempre substitui — jsdom devolve um stub vazio que confunde código que
  // faz `localStorage.clear()` ou `localStorage.getItem(...)`.
  Object.defineProperty(window, "localStorage", {
    writable: true,
    configurable: true,
    value: makeStorageShim(),
  });
  Object.defineProperty(window, "sessionStorage", {
    writable: true,
    configurable: true,
    value: makeStorageShim(),
  });
}

// matchMedia (next-themes, dark mode detection, Tailwind responsive hooks)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// IntersectionObserver (Recharts ResponsiveContainer, lazy components)
class IntersectionObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  takeRecords = vi.fn().mockReturnValue([]);
  root = null;
  rootMargin = "";
  thresholds = [];
}
Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: IntersectionObserverMock,
});

// ResizeObserver (Recharts, base-ui Popover/Dialog measurements)
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  configurable: true,
  value: ResizeObserverMock,
});

// scrollIntoView (Radix/base-ui usam ao abrir Combobox/Select)
Element.prototype.scrollIntoView = vi.fn();

// URL.createObjectURL (export.ts blob → download flow)
if (typeof URL.createObjectURL === "undefined") {
  Object.defineProperty(URL, "createObjectURL", {
    writable: true,
    value: vi.fn().mockReturnValue("blob:mock-url"),
  });
}
if (typeof URL.revokeObjectURL === "undefined") {
  Object.defineProperty(URL, "revokeObjectURL", {
    writable: true,
    value: vi.fn(),
  });
}

// crypto.randomUUID (alguns geradores de ID em Next 16 + React 19 dependem)
if (typeof crypto.randomUUID === "undefined") {
  Object.defineProperty(crypto, "randomUUID", {
    writable: true,
    value: () =>
      "00000000-0000-4000-8000-000000000000" as `${string}-${string}-${string}-${string}-${string}`,
  });
}
