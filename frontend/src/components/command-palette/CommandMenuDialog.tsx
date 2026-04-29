"use client";

import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/cn";

const NAV: { label: string; href: string; icon: typeof Target }[] = [
  { label: "Meu Plano", href: "/plano", icon: Target },
  { label: "Ação", href: "/acao", icon: ListTodo },
  { label: "Documentos", href: "/documents", icon: FileText },
  { label: "Pipeline", href: "/pipeline", icon: Zap },
  { label: "Transações", href: "/transactions", icon: ArrowLeftRight },
  { label: "Relatórios", href: "/reports", icon: BarChart3 },
  { label: "Cofre", href: "/vault", icon: KeyRound },
  { label: "Configurações", href: "/config", icon: Settings },
];

export function CommandMenuDialog({
  open,
  onOpenChange,
  onOpenHelp,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenHelp: () => void;
}) {
  const router = useRouter();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
                    onOpenChange(false);
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
                onOpenChange(false);
                onOpenHelp();
              }}
            >
              <Keyboard className="h-3.5 w-3.5" />
              Atalhos (?)
            </button>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
