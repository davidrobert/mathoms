/**
 * Dispensa client-side de cards da tela de review (A32.l6 PR3, decisão Q3).
 *
 * MVP: "Dispensar" esconde o card localmente (localStorage por review),
 * seguindo o padrão de `dismissedFreeTierBanner`. Não altera StageReview
 * nem o contrato do backend — a decisão formal continua sendo
 * aprovar/editar a review. Fallback silencioso sem storage (SSR/teste).
 */

const keyFor = (reviewId: string) => `reviews:dismissed:${reviewId}`;

export function getDismissedGroups(reviewId: string | undefined): string[] {
  if (!reviewId || typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(keyFor(reviewId));
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

export function dismissGroup(reviewId: string | undefined, groupKey: string): string[] {
  const next = [...new Set([...getDismissedGroups(reviewId), groupKey])];
  persist(reviewId, next);
  return next;
}

export function restoreDismissedGroups(reviewId: string | undefined): string[] {
  persist(reviewId, []);
  return [];
}

function persist(reviewId: string | undefined, keys: string[]) {
  if (!reviewId || typeof window === "undefined") return;
  try {
    if (keys.length === 0) window.localStorage.removeItem(keyFor(reviewId));
    else window.localStorage.setItem(keyFor(reviewId), JSON.stringify(keys));
  } catch {
    /* ignore */
  }
}
