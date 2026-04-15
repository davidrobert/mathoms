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
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { server } from "./mocks/server";

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
