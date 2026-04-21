"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function ShortcutsHelpDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" showCloseButton aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Atalhos de teclado</DialogTitle>
          <DialogDescription>
            Atalhos globais; em campos de texto,{" "}
            <kbd className="rounded border px-1">?</kbd> não abre esta janela.
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
  );
}
