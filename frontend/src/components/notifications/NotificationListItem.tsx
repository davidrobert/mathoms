"use client";

import { AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import type { NotificationItem } from "@/lib/api";
import { cn } from "@/lib/cn";

const SEVERITY_CONFIG: Record<
  string,
  { icon: typeof AlertCircle; color: string; bg: string }
> = {
  critical: {
    icon: AlertCircle,
    color: "text-destructive",
    bg: "bg-destructive/10",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10",
  },
  info: {
    icon: Info,
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-500/10",
  },
};

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "agora";
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function NotificationListItem({
  item,
  onRemove,
}: {
  item: NotificationItem;
  onRemove: (id: string) => void;
}) {
  const cfg = SEVERITY_CONFIG[item.severity] ?? SEVERITY_CONFIG.info;
  const SeverityIcon = cfg.icon;

  return (
    <li
      className={cn(
        "group/item flex gap-3 rounded-lg p-3 transition-colors",
        !item.is_read && "bg-accent/50",
      )}
    >
      <div
        className={cn(
          "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          cfg.bg,
        )}
      >
        <SeverityIcon className={cn("h-3.5 w-3.5", cfg.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className={cn("text-sm leading-tight", !item.is_read && "font-medium")}>
            {item.title}
          </p>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(item.created_at)}
            </span>
            <button
              onClick={() => onRemove(item.id)}
              className="rounded p-0.5 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover/item:opacity-100"
              aria-label="Remover notificação"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
          {item.message}
        </p>
      </div>
    </li>
  );
}
