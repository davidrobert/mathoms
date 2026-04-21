"use client";

import { useEffect, useState } from "react";
import { CommandMenuDialog } from "./command-palette/CommandMenuDialog";
import { ShortcutsHelpDialog } from "./command-palette/ShortcutsHelpDialog";

function isTypingTarget(t: EventTarget | null): boolean {
  if (!(t instanceof HTMLElement)) return false;
  const tag = t.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  return t.isContentEditable;
}

/** F11.8 — paleta de comandos (Cmd/Ctrl+K) + ajuda de atalhos (?). */
export function CommandPalette() {
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
      <CommandMenuDialog
        open={open}
        onOpenChange={setOpen}
        onOpenHelp={() => setHelpOpen(true)}
      />
      <ShortcutsHelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
    </>
  );
}
