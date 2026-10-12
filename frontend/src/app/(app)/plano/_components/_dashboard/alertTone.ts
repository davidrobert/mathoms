import { AlertOctagon, AlertTriangle, type LucideIcon } from "lucide-react";

import type { DashboardAlert } from "@/lib/api";

/** Tom de um alerta do `/plano`: fonte única do chip do summary e do `AlertCard`. */
export interface AlertTone {
  name: "critical" | "neutral";
  icon: LucideIcon;
  chipClassName: string;
  cardClassName: string;
  cardIconClassName: string;
}

// Mesmas classes do `PontosUrgentesCard` do relatório: mesmo objeto, mesmo pixel. Tint e
// texto ficam na mesma linha porque o gate de contraste pareia por linha.
const CRITICAL_TONE: AlertTone = {
  name: "critical",
  icon: AlertOctagon,
  chipClassName:
    "bg-[color-mix(in_srgb,var(--semantic-loss)_15%,transparent)] text-[var(--semantic-loss-on-tint)]",
  cardClassName: "border-l-4 border-l-[var(--semantic-loss)]",
  cardIconClassName: "text-[var(--semantic-loss)]",
};

const NEUTRAL_TONE: AlertTone = {
  name: "neutral",
  icon: AlertTriangle,
  chipClassName:
    "bg-[color-mix(in_srgb,var(--surface-muted-foreground)_15%,transparent)] text-[var(--surface-muted-foreground-on-tint)]",
  cardClassName: "",
  cardIconClassName: "text-[var(--surface-muted-foreground)]",
};

/** Severidade fora do contrato cai no neutro, nunca no vermelho. */
export function alertTone(severity: string): AlertTone {
  return severity === "critical" ? CRITICAL_TONE : NEUTRAL_TONE;
}

export interface UrgentPointsSummary {
  total: number;
  highPriority: number;
}

/** Conta só os pontos urgentes: aviso de qualidade de dado não é risco da família. */
export function summarizeUrgentPoints(
  alerts: readonly DashboardAlert[],
): UrgentPointsSummary {
  const urgent = alerts.filter((alert) => alert.kind === "ponto_urgente");
  return {
    total: urgent.length,
    highPriority: urgent.filter((alert) => alert.severity === "critical").length,
  };
}

/** A prioridade vai no texto, não só no tom: leitor de tela não vê o tint. */
export function urgentPointsLabel({
  total,
  highPriority,
}: UrgentPointsSummary): string {
  const count = total === 1 ? "1 ponto urgente" : `${total} pontos urgentes`;
  if (highPriority === 0) return count;
  if (highPriority === total) return `${count} de prioridade alta`;
  return `${count}, ${highPriority} de prioridade alta`;
}
