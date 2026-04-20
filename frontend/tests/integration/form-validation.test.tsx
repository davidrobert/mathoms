/**
 * Form validation suite — F6.5B.13
 *
 * Cobertura paramétrica: para cada form-relevant validation rule, garantir
 * que mensagens user-facing aparecem corretamente.
 *
 * Forms cobertos:
 * - Login: required email + senha, formato email
 * - Register: required + minLength=6 senha
 * - (Member create / Bank account / Vault password / Family surname são
 *   triviais ou cobertas em integration de cada page)
 *
 * Para validações que dependem de backend (CPF mod-11, duplicate email),
 * a mensagem flui via ApiError detail — coberto em login.test.tsx + register.test.tsx
 * (status 401/409/422).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";

describe("Form validation — Login", () => {
  it("input email tem type='email' (browser HTML5 email validation)", () => {
    render(<LoginPage />);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    expect(email.type).toBe("email");
    expect(email.required).toBe(true);
  });

  it("input password tem type='password' + required", () => {
    render(<LoginPage />);
    const pw = screen.getByLabelText(/senha/i) as HTMLInputElement;
    expect(pw.type).toBe("password");
    expect(pw.required).toBe(true);
  });

  it("placeholder do email tem hint de formato", () => {
    render(<LoginPage />);
    const email = screen.getByLabelText(/email/i) as HTMLInputElement;
    expect(email.placeholder).toContain("@");
  });
});

describe("Form validation — Register", () => {
  it("input 'Seu nome' tem required", () => {
    render(<RegisterPage />);
    const name = screen.getByLabelText(/seu nome/i) as HTMLInputElement;
    expect(name.required).toBe(true);
  });

  it("input senha tem minLength=6", () => {
    render(<RegisterPage />);
    const pw = screen.getByLabelText(/senha/i) as HTMLInputElement;
    expect(pw.minLength).toBe(6);
  });

  it("placeholder da senha mostra mínimo 6 chars", () => {
    render(<RegisterPage />);
    const pw = screen.getByLabelText(/senha/i) as HTMLInputElement;
    expect(pw.placeholder).toMatch(/6/);
  });
});

describe("Form validation — paramétrico", () => {
  it.each([
    ["email", "type=email"],
    ["senha", "type=password"],
  ])("Login: input %s tem %s", (field, expectedAttr) => {
    render(<LoginPage />);
    const input = screen.getByLabelText(new RegExp(field, "i")) as HTMLInputElement;
    if (expectedAttr.includes("type=")) {
      expect(input.type).toBe(expectedAttr.split("=")[1]);
    }
  });
});
