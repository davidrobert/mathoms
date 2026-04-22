/**
 * Bootstrap smoke test — F6.5 (final do bloco Bootstrap)
 *
 * Valida que toda a fundação está no ar:
 * 1. Vitest + jsdom (renderiza React 19 sem crash)
 * 2. @testing-library/react (queries por role/text)
 * 3. @testing-library/jest-dom (matchers)
 * 4. MSW interceptando /api/v1/* (handlers default)
 * 5. Factories type-safe (compilação + valores sane)
 * 6. Path alias `@/lib/...` resolvendo
 *
 * NÃO é "test do produto" — é "test da infra de teste". Se quebrar, o
 * problema é setup/config, não código de aplicação.
 *
 * Próximas suítes (6.5A.3-A.7) usam este arquivo como referência de padrão.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { getMe, isAuthenticated, setToken } from "@/lib/api";
import { makeMember, makeUser, resetCounters } from "./factories";

describe("Bootstrap smoke", () => {
  describe("Vitest + jest-dom + jsdom", () => {
    it("renderiza React 19 e queries do RTL funcionam", () => {
      render(<h1>Olá Fin</h1>);
      expect(screen.getByRole("heading", { name: "Olá Fin" })).toBeInTheDocument();
    });

    it("polyfills jsdom estão presentes", () => {
      expect(typeof window.matchMedia).toBe("function");
      expect(typeof window.IntersectionObserver).toBe("function");
      expect(typeof window.ResizeObserver).toBe("function");
      expect(typeof URL.createObjectURL).toBe("function");
    });
  });

  describe("MSW intercepta /api/v1/*", () => {
    it("GET /api/v1/auth/me retorna user do handler default", async () => {
      setToken("test-token");
      const me = await getMe();
      expect(me.email).toBe("founder@test.com");
      expect(me.is_active).toBe(true);
      expect(isAuthenticated()).toBe(true);
    });

    it("localStorage limpa entre tests (afterEach)", () => {
      // se o reset não funcionasse, este teste veria o token do anterior
      expect(localStorage.getItem("fin_token")).toBeNull();
    });
  });

  describe("Factories type-safe", () => {
    it("makeUser gera defaults sane com counter incremental", () => {
      resetCounters();
      const u1 = makeUser();
      const u2 = makeUser({ email: "custom@test.com" });
      expect(u1.email).toBe("user1@test.com");
      expect(u1.is_active).toBe(true);
      expect(u2.email).toBe("custom@test.com");
      expect(u2.id).toBe("user-2"); // counter independente do override
    });

    it("makeMember inclui account default e CPF placeholder LGPD-safe", () => {
      resetCounters();
      const m = makeMember();
      expect(m.cpf).toBe("000.000.000-00"); // placeholder, não CPF real
      expect(m.accounts).toHaveLength(1);
      expect(m.accounts[0].institution_code).toBe("c6bank");
    });

    it("aceita overrides parciais sem repetir o objeto", () => {
      const m = makeMember({ role: "conjuge", short_name: "Spouse" });
      expect(m.role).toBe("conjuge");
      expect(m.short_name).toBe("Spouse");
      expect(m.full_name).toMatch(/^Member \d+$/); // resto continua default
    });
  });
});
