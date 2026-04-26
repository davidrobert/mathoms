"use client";

import { useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/cn";
import { Sheet, SheetTrigger } from "@/components/ui/sheet";
import { useNotifications } from "@/components/notifications/useNotifications";
import { NotificationSheetContent } from "@/components/notifications/NotificationSheetContent";

export function SidebarNotificationItem() {
  const [open, setOpen] = useState(false);
  const state = useNotifications({ open });
  const displayCount = state.unread > 9 ? "9+" : String(state.unread);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <button
            type="button"
            aria-label={`Notificações${state.unread > 0 ? ` (${state.unread} não lidas)` : ""}`}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
              "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          />
        }
      >
        <Bell className="h-4 w-4 text-muted-foreground" />
        <span className="flex-1 text-left">Notificações</span>
        {state.unread > 0 && (
          <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold leading-none text-white">
            {displayCount}
          </span>
        )}
      </SheetTrigger>
      <NotificationSheetContent {...state} />
    </Sheet>
  );
}
