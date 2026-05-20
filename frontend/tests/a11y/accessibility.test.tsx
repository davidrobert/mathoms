/**
 * Accessibility audit — F6.5D.1 (vitest-axe)
 *
 * Gate: 0 violations critical/serious em pages + compostos principais.
 * Moderate/minor são logados para triagem mas não bloqueiam CI aqui
 * (gate duro em 6.5D.8 Lighthouse).
 *
 * Convenção:
 * - Render componente/page
 * - Aguardar carga (waitFor se fetches)
 * - axe(container) → assert sem violations
 *
 * Páginas que dependem de auth → usam localStorage com token mock + MSW.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { axe } from "vitest-axe";
import { toHaveNoViolations } from "vitest-axe/matchers";
import { http, HttpResponse } from "msw";

import { KPICard } from "@/components/KPICard";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { Delta } from "@/components/Delta";
import { Spinner } from "@/components/Spinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";

import { server } from "../mocks/server";
import { makeDashboard, makeKPI, makeDocument, makeVaultPassword } from "../factories";

// next/navigation mock (algumas pages usam — incluindo redirect Server Component
// usado pelo /dashboard pós-ADR-155)
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
  redirect: vi.fn(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));
vi.mock("@/lib/usePipelineWS", () => ({
  usePipelineWS: () => ({ status: "disconnected", lastEvent: null }),
}));

// Estende expect com matcher do axe.
// vitest-axe@0.1.0 packaging bug: matchers.d.ts re-exporta com `export type *`,
// mas matchers.js exporta o runtime. Workaround até upstream corrigir.
// @ts-expect-error type-only export at .d.ts level (runtime value existe)
expect.extend({ toHaveNoViolations });

beforeEach(() => {
  localStorage.setItem("fin_token", "t");
});

// Filtro para asserts: apenas critical/serious bloqueiam (gate F6.5)
function assertNoSeriousViolations(results: any) {
  const blocking = (results.violations ?? []).filter(
    (v: any) => v.impact === "critical" || v.impact === "serious",
  );
  if (blocking.length > 0) {
    const msg = blocking
      .map((v: any) => `  - [${v.impact}] ${v.id}: ${v.description} (${v.nodes.length} nodes)`)
      .join("\n");
    throw new Error(`a11y violations (critical/serious):\n${msg}`);
  }
}

// ─── Compostos ───────────────────────────────────────────────────────

describe("a11y — compostos", () => {
  it("KPICard é acessível", async () => {
    const { container } = render(
      <KPICard label="Saldo" value="R$ 4.100,00" delta={{ value: 100, percent: 0.1 }} />,
    );
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("KPICard loading state é acessível", async () => {
    const { container } = render(<KPICard label="x" value="y" loading />);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("StatusBadge (todos variants) é acessível", async () => {
    const { container } = render(
      <div>
        <StatusBadge variant="success">Concluído</StatusBadge>
        <StatusBadge variant="warning">Pendente</StatusBadge>
        <StatusBadge variant="error">Falhou</StatusBadge>
        <StatusBadge variant="info">Executando</StatusBadge>
      </div>,
    );
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("EmptyState com CTA é acessível", async () => {
    const { container } = render(
      <EmptyState
        title="Sem documentos"
        description="Envie seu primeiro extrato."
        action={{ label: "Enviar", href: "/documents" }}
      />,
    );
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("Delta tem aria-label semântico", async () => {
    const { container } = render(<Delta value={-150.5} />);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("Spinner não gera violation (decorativo)", async () => {
    const { container } = render(<Spinner />);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("ConfirmDialog (open) é acessível — dialog role + heading + buttons", async () => {
    const { container } = render(
      <ConfirmDialog
        open={true}
        onOpenChange={() => {}}
        title="Remover?"
        description="Esta ação não pode ser desfeita."
        confirmLabel="Remover"
        variant="destructive"
        onConfirm={() => {}}
      />,
    );
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });
});

// ─── Pages ───────────────────────────────────────────────────────────

describe("a11y — pages", () => {
  it("LoginPage é acessível", async () => {
    const { default: LoginPage } = await import("@/app/login/page");
    const { container } = render(<LoginPage />);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("RegisterPage é acessível", async () => {
    const { default: RegisterPage } = await import("@/app/register/page");
    const { container } = render(<RegisterPage />);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("VaultPage (empty state) é acessível", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/vault/passwords", () =>
        HttpResponse.json({ passwords: [], total: 0 }),
      ),
    );
    const { default: VaultPage } = await import("@/app/(app)/vault/page");
    const { container, findByText } = render(<VaultPage />);
    await findByText(/Nenhuma senha cadastrada/);
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("VaultPage (com senhas) é acessível", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/vault/passwords", () =>
        HttpResponse.json({
          passwords: [
            makeVaultPassword({ label: "Itaú" }),
            makeVaultPassword({ label: "Bradesco" }),
          ],
          total: 2,
        }),
      ),
    );
    const { default: VaultPage } = await import("@/app/(app)/vault/page");
    const { container, findByText } = render(<VaultPage />);
    await findByText("Itaú");
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  it("DocumentsPage (com docs) é acessível", async () => {
    server.use(
      http.get("/api/v1/workspaces/:workspaceId/documents", () =>
        HttpResponse.json({
          documents: [
            makeDocument({
              original_name: "extrato.pdf",
              status: "ready",
              bank_code: null,
              doc_type: null,
              period: null,
            }),
          ],
          total: 1,
        }),
      ),
    );
    const { default: DocumentsPage } = await import("@/app/(app)/documents/page");
    const { container, findByText } = render(<DocumentsPage />);
    await findByText("extrato.pdf");
    const results = await axe(container);
    assertNoSeriousViolations(results);
  });

  // ADR-155: DashboardPage virou redirect; teste a11y dos charts/KPIs
  // operacionais (que agora vivem na seção "Mês corrente" do /plano)
  // fica como lane futura `plano-a11y` quando produto pedir.
});
