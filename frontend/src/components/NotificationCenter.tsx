"use client";

import { useState } from "react";
import { Sheet } from "@/components/ui/sheet";
import { useNotifications } from "./notifications/useNotifications";
import { NotificationTrigger } from "./notifications/NotificationTrigger";
import { NotificationSheetContent } from "./notifications/NotificationSheetContent";

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const state = useNotifications({ open });

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <NotificationTrigger unread={state.unread} />
      <NotificationSheetContent {...state} />
    </Sheet>
  );
}
