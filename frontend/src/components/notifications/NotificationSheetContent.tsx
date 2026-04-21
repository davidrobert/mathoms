"use client";

import { Button } from "@/components/ui/button";
import { SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Bell, CheckCheck } from "lucide-react";
import type { NotificationItem } from "@/lib/api";
import { NotificationListItem } from "./NotificationListItem";

function MarkAllReadButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 text-xs"
      onClick={onClick}
      disabled={disabled}
    >
      <CheckCheck className="mr-1.5 h-3.5 w-3.5" />
      Marcar todas como lidas
    </Button>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <Bell className="mb-3 h-10 w-10 opacity-30" />
      <p className="text-sm">Nenhuma notificação</p>
    </div>
  );
}

export function NotificationSheetContent({
  items,
  unread,
  loading,
  markAllRead,
  remove,
}: {
  items: NotificationItem[];
  unread: number;
  loading: boolean;
  markAllRead: () => void;
  remove: (id: string) => void;
}) {
  return (
    <SheetContent className="flex w-full flex-col sm:max-w-md">
      <SheetHeader className="flex-row items-center justify-between space-y-0 pr-6">
        <SheetTitle>Notificações</SheetTitle>
        {unread > 0 && <MarkAllReadButton onClick={markAllRead} disabled={loading} />}
      </SheetHeader>

      <div className="flex-1 overflow-y-auto -mx-6 px-6">
        {items.length === 0 ? (
          <EmptyState />
        ) : (
          <ul className="space-y-1" role="list">
            {items.map((item) => (
              <NotificationListItem key={item.id} item={item} onRemove={remove} />
            ))}
          </ul>
        )}
      </div>
    </SheetContent>
  );
}
