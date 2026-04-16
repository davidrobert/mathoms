"use client";

/**
 * Banner discreto que aparece quando o user está no workspace como `viewer`
 * (F9 · débito #2). Clara expectativa: dá pra navegar, não dá pra editar.
 */

import { Eye } from "lucide-react";

import { usePermissions } from "@/lib/usePermissions";

export function ViewerBanner() {
  const { isViewer } = usePermissions();
  if (!isViewer) return null;
  return (
    <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-6 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
      <Eye className="h-3.5 w-3.5 shrink-0" />
      <span>
        Você está <strong>acompanhando</strong> este workspace. Ações de
        edição (metas, transações, importação) ficam indisponíveis.
      </span>
    </div>
  );
}
