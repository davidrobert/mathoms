/**
 * ADR-155 (Direção E consolidação) — `/dashboard` absorvido por `/plano`.
 *
 * Componentes (KpiRow, ChartsGrid, AlertCard, HeaderActions etc) foram
 * movidos para `frontend/src/app/(app)/plano/_components/_dashboard/` e
 * são renderizados como seção "Mês corrente" dentro de `/plano`.
 *
 * Este arquivo permanece apenas como redirect 308 para preservar
 * deep-links existentes (e-mails, marcadores, links em commits passados).
 */
import { redirect } from "next/navigation";

export default function DashboardRedirect() {
  redirect("/plano");
}
