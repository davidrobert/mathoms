"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { getMe, clearToken, type UserResponse } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/Spinner";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NotificationCenter } from "@/components/NotificationCenter";
import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher";
import { ViewerBanner } from "@/components/ViewerBanner";
import { StatusPageFooter } from "@/components/StatusPageFooter";
import {
  LayoutDashboard,
  FileText,
  Zap,
  ArrowLeftRight,
  BarChart3,
  Settings,
  KeyRound,
  Menu,
  LogOut,
  Target,
  ListTodo,
} from "lucide-react";

/** Match route without treating `/plano` as prefix of `/plano-de-acao` (startsWith bug). */
function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

const NAV_ITEMS = [
  { href: "/plano", label: "Meu Plano", icon: Target },
  { href: "/plano-de-acao", label: "Plano de Ação", icon: ListTodo },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/pipeline", label: "Pipeline", icon: Zap },
  { href: "/transactions", label: "Transações", icon: ArrowLeftRight },
  { href: "/reports", label: "Relatórios", icon: BarChart3 },
  { href: "/vault", label: "Cofre", icon: KeyRound },
  { href: "/config", label: "Configurações", icon: Settings },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {
        clearToken();
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r border-border bg-card transition-transform lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center border-b border-border px-5">
          <Link href="/plano" className="font-display text-xl font-bold tracking-tight">
            Fin
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const active = isNavActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className={cn("h-4 w-4", active ? "text-primary" : "text-muted-foreground")} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <Separator />
        <div className="p-4">
          <p className="truncate text-sm font-medium">{user?.full_name}</p>
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          <div className="mt-3 flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => {
                clearToken();
                router.replace("/login");
              }}
            >
              <LogOut className="mr-2 h-3.5 w-3.5" />
              Sair
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/20 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center border-b border-border bg-card">
          {/* Left: mobile menu + branding */}
          <div className="flex items-center gap-3 pl-4 pr-2 lg:pl-6">
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Abrir menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <span className="text-style-heading-sm lg:hidden">Fin</span>
          </div>

          {/* Center: workspace — grows to fill, stays centered on desktop */}
          <div className="flex min-w-0 flex-1 items-center lg:justify-start">
            <WorkspaceSwitcher />
          </div>

          {/* Right: actions */}
          <div className="flex items-center gap-1 pr-4 lg:pr-6">
            <NotificationCenter />
            <div className="lg:hidden">
              <ThemeToggle />
            </div>
          </div>
        </header>
        <ViewerBanner />
        <main className="flex-1 overflow-y-auto">{children}</main>
        <StatusPageFooter variant="app" />
      </div>
    </div>
  );
}
