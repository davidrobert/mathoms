/**
 * Direção E · Onda 6 · ADR-152 — redirect 301 para /acao/sugestoes.
 */
import { redirect } from "next/navigation";

export default function PlanoDeAcaoSugestoesRedirect() {
  redirect("/acao/sugestoes");
}
