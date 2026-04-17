/** Helper para normalizar `?next=` em fluxos de login/register (F9 · débito #5).
 *
 * Regras de segurança:
 *   - Aceita apenas caminhos relativos começando com `/`, **sem** protocolo
 *     explícito nem `//` (open-redirect defense).
 *   - Fallback é `/plano` (entrada pós-login).
 */

const DEFAULT_NEXT = "/plano";

export function resolveNext(raw: string | null | undefined): string {
  if (!raw) return DEFAULT_NEXT;
  // Previne `//attacker.com` e URLs absolutas
  if (!raw.startsWith("/") || raw.startsWith("//")) return DEFAULT_NEXT;
  return raw;
}
