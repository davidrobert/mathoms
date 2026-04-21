import { apiFetch } from "./core";

// ─── Notification Types ───

export interface NotificationItem {
  id: string;
  severity: string;
  title: string;
  message: string;
  source: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
}

// ─── Notification API ───

export async function listNotifications(workspaceId: string, params?: {
  severity?: string;
  is_read?: boolean;
  limit?: number;
}): Promise<NotificationListResponse> {
  const qp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qp.set(k, String(v));
    });
  }
  const qs = qp.toString();
  return apiFetch(`/workspaces/${workspaceId}/notifications${qs ? `?${qs}` : ""}`);
}

export async function markNotificationsRead(workspaceId: string, ids: string[]): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/notifications/read`, {
    method: "PATCH",
    body: JSON.stringify({ notification_ids: ids }),
  });
}

export async function deleteNotification(workspaceId: string, id: string): Promise<void> {
  return apiFetch(`/workspaces/${workspaceId}/notifications/${id}`, { method: "DELETE" });
}
