"use client";

import { Info } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * `InfoTooltip` — `Info` icon WCAG-compliant para anexar contexto a um label.
 *
 * Padrão de uso (Lane A8.3 / S7): ao lado do *label* do KPI, **não no value**.
 * Cobre WCAG 2.1.1 (keyboard) + 1.4.13 (Content on Hover dismissable +
 * hoverable + persistent — fornecidos pelo `@base-ui/react` Tooltip
 * primitive).
 *
 * Conteúdo crítico de mitigação metodológica não pode depender exclusivamente
 * deste tooltip — o consumidor (ex.: S7) precisa exibir caption permanente
 * para usuários em fase de acumulação (a maioria do dogfood).
 */
export interface InfoTooltipProps {
  /** Texto do tooltip — curto, sem markdown. */
  content: React.ReactNode;
  /** `aria-label` do botão (descritivo, ex.: "Sobre TRS efetiva"). */
  ariaLabel: string;
  /** Override opcional da classe; defaults a tamanho ícone 14px. */
  className?: string;
}

export function InfoTooltip({ content, ariaLabel, className }: InfoTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button
            type="button"
            aria-label={ariaLabel}
            className={
              className ??
              "inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[var(--surface-muted-foreground)] transition-colors hover:text-[var(--surface-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)] focus-visible:ring-offset-1"
            }
          />
        }
      >
        <Info className="h-3.5 w-3.5" aria-hidden="true" />
      </TooltipTrigger>
      <TooltipContent>{content}</TooltipContent>
    </Tooltip>
  );
}
