/** LocalStorage helpers para lembrar qual run parcial o usuário já dispensou.
 *  Chave própria: run que entregou não é run que falhou, e compartilhar a chave
 *  de `dismissedFailedRun` faria dispensar um dispensar o outro.
 *  Fallback silencioso se storage não disponível. */

const KEY = "pipeline:dismissedPartialRunId";

export function getDismissedPartialRunId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setDismissedPartialRunId(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(KEY, id);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
