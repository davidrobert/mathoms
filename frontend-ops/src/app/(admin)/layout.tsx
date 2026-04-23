"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthGuard } from "@/lib/auth-guard";

const NAV: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/users", label: "Usuários" },
  { href: "/documents", label: "Documentos" },
  { href: "/metrics", label: "Métricas" },
  { href: "/reports", label: "Relatórios" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { principal, loading } = useAuthGuard();
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout(): Promise<void> {
    try {
      await api.logout();
    } finally {
      router.replace("/login");
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-surface-bg text-surface-muted-fg">
        Carregando…
      </main>
    );
  }
  if (!principal) return null;

  return (
    <div className="min-h-screen flex flex-col bg-surface-bg text-surface-fg">
      <header className="border-b border-surface-border bg-surface-card">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-display text-lg font-semibold text-brand-primary">
              Mathoms · ops
            </span>
            <nav className="flex gap-1">
              {NAV.map((item) => {
                const active =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                      active
                        ? "bg-brand-primary text-brand-primary-fg"
                        : "text-surface-fg hover:bg-surface-muted"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-surface-muted-fg">
              {principal.username} · <em className="not-italic">{principal.role}</em>
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-md border border-surface-border hover:bg-surface-muted"
            >
              Sair
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
