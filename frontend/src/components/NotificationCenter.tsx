"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Bell, CheckCheck } from "lucide-react";
import { useNotifications } from "./notifications/useNotifications";
import { NotificationListItem } from "./notifications/NotificationListItem";

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const { items, unread, loading, markAllRead, remove } = useNotifications({ open });
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
              onClick={markAllRead}
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
              {items.map((item) => (
                <NotificationListItem key={item.id} item={item} onRemove={remove} />
              ))}
            </ul>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
