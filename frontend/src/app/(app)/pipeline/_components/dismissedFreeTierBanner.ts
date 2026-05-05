/** LocalStorage helpers para lembrar qual run free-tier o usuário já dispensou.
 *  Fallback silencioso se storage não disponível. */

const KEY = "pipeline:dismissedFreeTierRunId";

export function getDismissedFreeTierRunId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setDismissedFreeTierRunId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(KEY, id);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
