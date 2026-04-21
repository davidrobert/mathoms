/** LocalStorage helpers para lembrar qual run falhado o usuário já dispensou
 *  (evita reabrir o banner em F5). Fallback silencioso se storage não disponível. */

const KEY = "pipeline:dismissedFailedRunId";

export function getDismissedFailedRunId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setDismissedFailedRunId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(KEY, id);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
