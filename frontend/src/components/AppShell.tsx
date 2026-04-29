"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { getMe, clearToken, type UserResponse } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/Spinner";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SidebarWorkspaceCard } from "@/components/sidebar/SidebarWorkspaceCard";
import { SidebarNotificationItem } from "@/components/sidebar/SidebarNotificationItem";
import { ViewerBanner } from "@/components/ViewerBanner";
import { StatusPageFooter } from "@/components/StatusPageFooter";
import { CommandPalette } from "@/components/CommandPalette";
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

function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** F11.1 — eixo estratégico vs operacional do período. */
const NAV_GROUPS: {
  heading: string;
  items: { href: string; label: string; icon: typeof Target }[];
}[] = [
  {
    heading: "Plano de vida",
    items: [
      { href: "/plano", label: "Meu Plano", icon: Target },
      { href: "/acao", label: "Ação", icon: ListTodo },
    ],
  },
  {
    heading: "Fechamento do período",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/documents", label: "Documentos", icon: FileText },
      { href: "/pipeline", label: "Pipeline", icon: Zap },
      { href: "/transactions", label: "Transações", icon: ArrowLeftRight },
      { href: "/reports", label: "Relatórios", icon: BarChart3 },
    ],
  },
  {
    heading: "Conta",
    items: [
      { href: "/vault", label: "Cofre", icon: KeyRound },
      { href: "/config", label: "Configurações", icon: Settings },
    ],
  },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("header");
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
      <CommandPalette />
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r border-border bg-card transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center border-b border-border px-5">
          <Link href="/plano" className="font-display text-xl font-bold tracking-tight">
            {t("title")}
          </Link>
        </div>

        <div className="border-b border-border px-2 py-2">
          <SidebarWorkspaceCard />
        </div>

        <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-4">
          <div className="space-y-0.5">
            <SidebarNotificationItem />
          </div>
          {NAV_GROUPS.map((group) => (
            <div key={group.heading}>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {group.heading}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
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
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      )}
                    >
                      <item.icon
                        className={cn("h-4 w-4", active ? "text-primary" : "text-muted-foreground")}
                      />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <Separator />
        <div className="shrink-0 p-4">
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

      {/* Mobile FAB — substitui o header em telas <lg. */}
      <Button
        variant="outline"
        size="icon"
        className="fixed left-3 top-3 z-30 h-10 w-10 shadow-md lg:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Abrir menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        <ViewerBanner />
        <main className="flex-1 overflow-y-auto">{children}</main>
        <StatusPageFooter variant="app" />
      </div>
    </div>
  );
}
