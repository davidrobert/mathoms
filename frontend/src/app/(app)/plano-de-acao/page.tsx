/**
 * Direção E · Onda 6 · ADR-152 — redirect 301 para /acao.
 *
 * Antiga rota `/plano-de-acao` foi renomeada para `/acao`. Mantemos
 * este arquivo apenas para preservar deep-links existentes (e-mails,
 * marcadores, links em commits passados). Next.js `redirect()` em
 * Server Component emite 307 por default; `permanent: true` força
 * 308 (equivalente semântico ao 301 para SEO).
 */
import { redirect } from "next/navigation";

export default function PlanoDeAcaoRedirect() {
  redirect("/acao");
}
