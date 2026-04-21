"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  LayoutDashboard,
  FileText,
  Zap,
  BarChart3,
  Settings,
  Target,
  ArrowLeftRight,
  KeyRound,
  ListTodo,
  Keyboard,
} from "lucide-react";
import { cn } from "@/lib/cn";

function isTypingTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false;
  const tag = t.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return t.isContentEditable;
}

const NAV: { label: string; href: string; icon: typeof LayoutDashboard }[] = [
  { label: "Meu Plano", href: "/plano", icon: Target },
  { label: "Plano de Ação", href: "/plano-de-acao", icon: ListTodo },
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Documentos", href: "/documents", icon: FileText },
  { label: "Pipeline", href: "/pipeline", icon: Zap },
  { label: "Transações", href: "/transactions", icon: ArrowLeftRight },
  { label: "Relatórios", href: "/reports", icon: BarChart3 },
  { label: "Cofre", href: "/vault", icon: KeyRound },
  { label: "Configurações", href: "/config", icon: Settings },
];

/** F11.8 — paleta de comandos (Cmd/Ctrl+K) + ajuda de atalhos (?). */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        return;
      }
      if (e.key === "?" && !isTypingTarget(e.target)) {
        e.preventDefault();
        setHelpOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="max-w-lg gap-0 overflow-hidden p-0 sm:max-w-lg"
          showCloseButton
          aria-describedby={undefined}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>Buscar no app</DialogTitle>
            <DialogDescription>
              Navegue para uma página ou abra a ajuda de atalhos.
            </DialogDescription>
          </DialogHeader>
          <Command className="rounded-lg bg-popover text-popover-foreground" label="Comandos">
            <div className="flex items-center border-b px-3" cmdk-input-wrapper="">
              <Command.Input
                placeholder="Ir para…"
                className={cn(
                  "flex h-11 w-full bg-transparent py-3 text-sm outline-none",
                  "placeholder:text-muted-foreground",
                )}
              />
            </div>
            <Command.List className="max-h-[min(60vh,320px)] overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                Nenhum resultado.
              </Command.Empty>
              <Command.Group heading="Navegação" className="text-xs text-muted-foreground">
                {NAV.map((item) => (
                  <Command.Item
                    key={item.href}
                    value={`${item.label} ${item.href}`}
                    onSelect={() => {
                      router.push(item.href);
                      setOpen(false);
                    }}
                    className={cn(
                      "flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm",
                      "aria-selected:bg-accent aria-selected:text-accent-foreground",
                    )}
                  >
                    <item.icon className="h-4 w-4 shrink-0 opacity-70" />
                    {item.label}
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
            <div className="border-t bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground">
              <button
                type="button"
                className="inline-flex items-center gap-1 font-medium text-foreground underline-offset-2 hover:underline"
                onClick={() => {
                  setOpen(false);
                  setHelpOpen(true);
                }}
              >
                <Keyboard className="h-3.5 w-3.5" />
                Atalhos (?)
              </button>
            </div>
          </Command>
        </DialogContent>
      </Dialog>

      <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
        <DialogContent className="max-w-md" showCloseButton aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle>Atalhos de teclado</DialogTitle>
            <DialogDescription>
              Atalhos globais; em campos de texto, <kbd className="rounded border px-1">?</kbd> não
              abre esta janela.
            </DialogDescription>
          </DialogHeader>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between gap-4">
              <span>Abrir paleta</span>
              <kbd className="rounded border bg-muted px-1.5 font-mono text-xs">⌘ K</kbd>{" "}
              <span className="text-muted-foreground">/ Ctrl+K</span>
            </li>
            <li className="flex justify-between gap-4">
              <span>Esta ajuda</span>
              <kbd className="rounded border bg-muted px-1.5 font-mono text-xs">?</kbd>
            </li>
          </ul>
        </DialogContent>
      </Dialog>
    </>
  );
}
