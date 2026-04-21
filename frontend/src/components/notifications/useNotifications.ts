"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  listNotifications,
  markNotificationsRead,
  deleteNotification,
  type NotificationItem,
} from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";

const POLL_INTERVAL_MS = 30_000;

/** Estado + side-effects do painel de notificações — polling a cada
 * 30s, marcação em lote e remoção individual. Extraído do
 * NotificationCenter para manter o componente abaixo do cap de 40 linhas. */
export function useNotifications(opts: { open: boolean }) {
  const { workspace } = useWorkspace();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(async () => {
    if (!workspace) return;
    try {
      const data = await listNotifications(workspace.id, { limit: 50 });
      setItems(data.notifications);
      setUnread(data.unread_count);
    } catch {
      // Only toast when user explicitly opened the panel (not background polling)
      if (opts.open) {
        toast.error("Erro ao carregar notificações");
      }
    }
  }, [opts.open, workspace]);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  useEffect(() => {
    if (opts.open) fetchNotifications();
  }, [opts.open, fetchNotifications]);

  const markAllRead = useCallback(async () => {
    if (!workspace) return;
    const unreadIds = items.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length === 0) return;
    setLoading(true);
    try {
      await markNotificationsRead(workspace.id, unreadIds);
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } catch {
      toast.error("Erro ao marcar notificações como lidas");
    } finally {
      setLoading(false);
    }
  }, [items, workspace]);

  const remove = useCallback(
    async (id: string) => {
      if (!workspace) return;
      try {
        await deleteNotification(workspace.id, id);
        setItems((prev) => prev.filter((n) => n.id !== id));
        setUnread((prev) => {
          const wasUnread = items.find((n) => n.id === id && !n.is_read);
          return wasUnread ? Math.max(0, prev - 1) : prev;
        });
      } catch {
        toast.error("Erro ao remover notificação");
      }
    },
    [items, workspace],
  );

  return { items, unread, loading, markAllRead, remove };
}
