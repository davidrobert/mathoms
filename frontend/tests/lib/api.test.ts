/**
 * Unit tests — `lib/api.ts` (token mgmt, apiFetch, ApiError, FormData, XHR upload)
 *
 * F6.5A.5
 *
 * Estratégia:
 * - Token: localStorage do shim (tests/setup.ts)
 * - apiFetch: MSW intercepta /api/* (handlers.ts default OK) — overrides via server.use
 * - Erros 4xx/5xx: server.use com HttpResponse.json + status
 * - Upload XHR (uploadDocuments): mock XMLHttpRequest manualmente
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";

import {
  ApiError,
  clearToken,
  getToken,
  isAuthenticated,
  setToken,
  login,
  register,
  getMe,
  listReports,
  deleteDocument,
  uploadDocuments,
} from "@/lib/api";
import { server } from "../mocks/server";

beforeEach(() => {
  clearToken();
});

// ─── Token management ────────────────────────────────────────────────

describe("Token storage", () => {
  it("getToken retorna null quando vazio", () => {
    expect(getToken()).toBeNull();
  });

  it("setToken salva e getToken recupera", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("clearToken remove", () => {
    setToken("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("isAuthenticated é true quando token presente", () => {
    expect(isAuthenticated()).toBe(false);
    setToken("xyz");
    expect(isAuthenticated()).toBe(true);
  });
});

// ─── apiFetch via login/register/getMe (happy path) ──────────────────

describe("apiFetch happy path", () => {
  it("login retorna token via MSW handler default", async () => {
    const r = await login("user@test.com", "pass");
    expect(r.access_token).toBe("test-token");
    expect(r.token_type).toBe("bearer");
  });

  it("register retorna token", async () => {
    const r = await register("u@test.com", "pass", "Full Name");
    expect(r.access_token).toBe("test-token");
  });

  it("getMe retorna user do handler default", async () => {
    setToken("test-token");
    const me = await getMe();
    expect(me.email).toBe("founder@test.com");
    expect(me.is_active).toBe(true);
  });

  it("listReports retorna lista do handler default", async () => {
    setToken("test-token");
    const r = await listReports();
    expect(r.total).toBeGreaterThanOrEqual(1);
  });
});

// ─── Authorization header ────────────────────────────────────────────

describe("Authorization header", () => {
  it("inclui Bearer quando token salvo", async () => {
    setToken("my-token-xyz");
    let captured: string | null = null;
    server.use(
      http.get("/api/auth/me", ({ request }) => {
        captured = request.headers.get("authorization");
        return HttpResponse.json({
          id: "u1",
          email: "x@test.com",
          full_name: "X",
          is_active: true,
        });
      }),
    );
    await getMe();
    expect(captured).toBe("Bearer my-token-xyz");
  });

  it("omite header quando token ausente", async () => {
    let captured: string | null = "INITIAL";
    server.use(
      http.post("/api/auth/login", ({ request }) => {
        captured = request.headers.get("authorization");
        return HttpResponse.json({ access_token: "t", token_type: "bearer" });
      }),
    );
    await login("a@b.com", "p");
    expect(captured).toBeNull();
  });
});

// ─── Content-Type ────────────────────────────────────────────────────

describe("Content-Type handling", () => {
  it("seta application/json para body JSON", async () => {
    let captured: string | null = null;
    server.use(
      http.post("/api/auth/login", ({ request }) => {
        captured = request.headers.get("content-type");
        return HttpResponse.json({ access_token: "t", token_type: "bearer" });
      }),
    );
    await login("a@b.com", "p");
    expect(captured).toContain("application/json");
  });
});

// ─── Error handling ──────────────────────────────────────────────────

describe("ApiError", () => {
  it("instância de Error", () => {
    const err = new ApiError(401, "no auth");
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(401);
    expect(err.detail).toBe("no auth");
    expect(err.message).toBe("no auth");
  });

  it("apiFetch lança ApiError em 401 com detail do body", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json({ detail: "Token expirado" }, { status: 401 }),
      ),
    );
    await expect(getMe()).rejects.toMatchObject({
      status: 401,
      detail: "Token expirado",
    });
  });

  it("apiFetch lança ApiError em 500 com fallback de detail", async () => {
    server.use(
      http.get("/api/auth/me", () =>
        new HttpResponse("not json", { status: 500 }),
      ),
    );
    await expect(getMe()).rejects.toMatchObject({
      status: 500,
      // Quando body não é JSON, fallback "HTTP <status>"
      detail: expect.stringContaining("500"),
    });
  });

  it("apiFetch lança ApiError em 422 (validation)", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json({ detail: "Senha curta" }, { status: 422 }),
      ),
    );
    await expect(login("a@b.com", "x")).rejects.toMatchObject({
      status: 422,
      detail: "Senha curta",
    });
  });
});

// ─── 204 No Content ──────────────────────────────────────────────────

describe("204 handling", () => {
  it("deleteDocument retorna undefined em 204", async () => {
    setToken("t");
    // Handler default já é 204
    await expect(deleteDocument("doc-1")).resolves.toBeUndefined();
  });
});

// ─── XHR upload (uploadDocuments) ────────────────────────────────────

describe("uploadDocuments (XHR upload com progress)", () => {
  // XHR não passa por MSW — precisa mock manual
  it("envia FormData com files e dispara onProgress", async () => {
    const events: Array<{ loaded: number; total: number }> = [];
    let sentBody: any = null;
    let sentMethod: string | null = null;
    let sentURL: string | null = null;

    class MockXHR {
      upload = {
        listeners: [] as any[],
        addEventListener(type: string, fn: any) {
          this.listeners.push({ type, fn });
        },
      };
      private listeners: Record<string, any[]> = {};

      open(method: string, url: string) {
        sentMethod = method;
        sentURL = url;
      }
      setRequestHeader() {}
      addEventListener(type: string, fn: any) {
        this.listeners[type] = this.listeners[type] || [];
        this.listeners[type].push(fn);
      }
      send(body: any) {
        sentBody = body;
        // Simula progress event
        for (const l of this.upload.listeners) {
          if (l.type === "progress") {
            l.fn({ lengthComputable: true, loaded: 50, total: 100 });
            l.fn({ lengthComputable: true, loaded: 100, total: 100 });
          }
        }
        // Simula resposta sucesso
        (this as any).status = 201;
        (this as any).responseText = JSON.stringify({
          documents: [],
          skipped_duplicates: [],
          total_uploaded: 1,
          total_skipped: 0,
        });
        for (const fn of this.listeners["load"] || []) fn();
      }
    }

    const realXHR = globalThis.XMLHttpRequest;
    (globalThis as any).XMLHttpRequest = MockXHR;

    try {
      setToken("t");
      const file = new File(["hello"], "test.pdf", { type: "application/pdf" });
      const result = await uploadDocuments([file], (loaded, total) => {
        events.push({ loaded, total });
      });

      expect(sentMethod).toBe("POST");
      expect(sentURL).toContain("/api/documents/upload");
      expect(sentBody).toBeInstanceOf(FormData);
      expect(events).toEqual([
        { loaded: 50, total: 100 },
        { loaded: 100, total: 100 },
      ]);
      expect(result.total_uploaded).toBe(1);
    } finally {
      (globalThis as any).XMLHttpRequest = realXHR;
    }
  });

  it("propaga ApiError em status >= 400", async () => {
    class MockXHR {
      upload = { addEventListener() {} };
      private listeners: Record<string, any[]> = {};
      open() {}
      setRequestHeader() {}
      addEventListener(type: string, fn: any) {
        this.listeners[type] = this.listeners[type] || [];
        this.listeners[type].push(fn);
      }
      send() {
        (this as any).status = 400;
        (this as any).responseText = JSON.stringify({ detail: "arquivo grande" });
        for (const fn of this.listeners["load"] || []) fn();
      }
    }
    const realXHR = globalThis.XMLHttpRequest;
    (globalThis as any).XMLHttpRequest = MockXHR;
    try {
      const file = new File(["x"], "big.pdf");
      await expect(uploadDocuments([file])).rejects.toMatchObject({
        status: 400,
        detail: "arquivo grande",
      });
    } finally {
      (globalThis as any).XMLHttpRequest = realXHR;
    }
  });
});
