"use client";

import Link from "next/link";
import { Activity } from "lucide-react";
import { getStatusPageUrl } from "@/lib/statusPageUrl";
import { cn } from "@/lib/cn";

type Props = {
  /** `app` = borda superior (área logada); `auth` = login/cadastro */
  variant?: "app" | "auth";
};

/**
 * Rodapé com link para a status page pública (7E.6). Não renderiza nada se a env não estiver definida.
 */
export function StatusPageFooter({ variant = "auth" }: Props) {
  const href = getStatusPageUrl();
  if (!href) {
    return null;
  }
  return (
    <footer
      className={cn(
        "flex shrink-0 justify-center py-6",
        variant === "app" && "border-t border-border py-3"
      )}
    >
      <Link
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition hover:text-foreground"
      >
        <Activity className="h-3.5 w-3.5 shrink-0" aria-hidden />
        Status e incidentes
      </Link>
    </footer>
  );
}
