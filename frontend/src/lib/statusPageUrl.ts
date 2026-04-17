/**
 * URL pública da status page (7E.6). Definir em `.env.local`:
 * NEXT_PUBLIC_FIN_STATUS_PAGE_URL=https://status.exemplo.com
 */
export function getStatusPageUrl(): string | undefined {
  const raw = process.env.NEXT_PUBLIC_FIN_STATUS_PAGE_URL;
  if (raw == null || String(raw).trim() === "") {
    return undefined;
  }
  const u = String(raw).trim();
  try {
    const parsed = new URL(u);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return undefined;
    }
    return u;
  } catch {
    return undefined;
  }
}
