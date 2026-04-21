"use client";

import { Button } from "@/components/ui/button";
import { SheetTrigger } from "@/components/ui/sheet";
import { Bell } from "lucide-react";

export function NotificationTrigger({ unread }: { unread: number }) {
  const displayCount = unread > 9 ? "9+" : String(unread);
  return (
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
  );
}
