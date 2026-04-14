"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listNotifications,
  markNotificationsRead,
  type NotificationItem,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const data = await listNotifications({ limit: 50 });
      setItems(data.notifications);
      setUnread(data.unread_count);
    } catch {
      // silently ignore — bell just shows stale count
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30_000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    if (open) fetchNotifications();
  }, [open, fetchNotifications]);

  const handleMarkAllRead = async () => {
    const unreadIds = items.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length === 0) return;
    setLoading(true);
    try {
      await markNotificationsRead(unreadIds);
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } finally {
      setLoading(false);
    }
  };

  const displayCount = unread > 9 ? "9+" : String(unread);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button
            variant="ghost"
            size="icon"
            className="relative h-8 w-8"
            aria-label={`Notificações${unread > 0 ? ` (${unread} não lidas)` : ""}`}
          />
        }
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-white">
            {displayCount}
          </span>
        )}
      </SheetTrigger>

      <SheetContent className="flex w-full flex-col sm:max-w-md">
        <SheetHeader className="flex-row items-center justify-between space-y-0 pr-6">
          <SheetTitle>Notificações</SheetTitle>
          {unread > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs"
              onClick={handleMarkAllRead}
              disabled={loading}
            >
              <CheckCheck className="mr-1.5 h-3.5 w-3.5" />
              Marcar todas como lidas
            </Button>
          )}
        </SheetHeader>

        <div className="flex-1 overflow-y-auto -mx-6 px-6">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Bell className="mb-3 h-10 w-10 opacity-30" />
              <p className="text-sm">Nenhuma notificação</p>
            </div>
          ) : (
            <ul className="space-y-1" role="list">
              {items.map((item) => {
                const cfg = SEVERITY_CONFIG[item.severity] ?? SEVERITY_CONFIG.info;
                const SeverityIcon = cfg.icon;
                return (
                  <li
                    key={item.id}
                    className={cn(
                      "flex gap-3 rounded-lg p-3 transition-colors",
                      !item.is_read && "bg-accent/50"
                    )}
                  >
                    <div
                      className={cn(
                        "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                        cfg.bg
                      )}
                    >
                      <SeverityIcon className={cn("h-3.5 w-3.5", cfg.color)} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p
                          className={cn(
                            "text-sm leading-tight",
                            !item.is_read && "font-medium"
                          )}
                        >
                          {item.title}
                        </p>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {formatRelativeTime(item.created_at)}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                        {item.message}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
