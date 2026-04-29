"use client";

/**
 * Direção E · Onda 7 #5 — primeiro contato em `/plano`.
 *
 * Renderizado quando o workspace está zero (sem IF, sem decisões, sem
 * tarefas). Oferece 3 next-steps verticais: configurar IF, importar
 * relatório, criar primeira decisão. Esconde o resto da tela para
 * evitar a "parede de blocos vazios" que mata a primeira impressão.
 */

import Link from "next/link";
import {
  ArrowRight,
  ClipboardList,
  FileText,
  Target,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface OnboardingHeroProps {
  hasIfGoal: boolean;
  hasDecisions: boolean;
}

export function OnboardingHero({ hasIfGoal, hasDecisions }: OnboardingHeroProps) {
  return (
    <Card className="mb-6 border-dashed">
      <CardContent className="py-10">
        <div className="mx-auto max-w-2xl">
          <header className="text-center">
            <Target className="mx-auto mb-4 h-10 w-10 text-muted-foreground" />
            <h2 className="font-heading text-xl font-semibold">
              Bem-vindo ao Mathoms
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              O Mathoms te ajuda a ler sua vida financeira e planejar os
              próximos passos. Comece configurando sua meta de Independência
              Financeira — em três passos curtos abaixo, seu plano sai do papel.
            </p>
          </header>
          <ol className="mt-8 space-y-3">
            <NextStep
              n={1}
              icon={Target}
              title="Configure sua meta de Independência Financeira"
              description="Defina renda passiva-alvo, retorno esperado e horizonte. O cálculo de patrimônio-alvo e aporte sai daí."
              ctaLabel={hasIfGoal ? "Configurada — revisar" : "Configurar IF"}
              ctaHref="/plano/meta-if/wizard"
              ctaVariant="default"
              done={hasIfGoal}
            />
            <NextStep
              n={2}
              icon={FileText}
              title="Importe seu primeiro relatório"
              description="Suba extratos e faturas para o Mathoms gerar um relatório completo da sua posição patrimonial e do mês corrente."
              ctaLabel="Ir para Documentos"
              ctaHref="/documents"
              ctaVariant="outline"
              done={false}
            />
            <NextStep
              n={3}
              icon={ClipboardList}
              title="Crie sua primeira decisão"
              description="Decisões são compromissos do casal — quitar dívida, aportar mensal, montar reserva. A primeira costuma vir do relatório, mas você pode criar manualmente."
              ctaLabel="Ver Plano de Ação"
              ctaHref="/acao"
              ctaVariant="ghost"
              disabled={!hasIfGoal}
              disabledHint="Configure a meta IF primeiro — assim suas decisões já entram conectadas ao plano."
              done={hasDecisions}
            />
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}

interface NextStepProps {
  n: number;
  icon: LucideIcon;
  title: string;
  description: string;
  ctaLabel: string;
  ctaHref: string;
  ctaVariant: "default" | "outline" | "ghost";
  disabled?: boolean;
  disabledHint?: string;
  done?: boolean;
}

function NextStep({
  n,
  icon: Icon,
  title,
  description,
  ctaLabel,
  ctaHref,
  ctaVariant,
  disabled,
  disabledHint,
  done,
}: NextStepProps) {
  return (
    <li className="flex items-start gap-4 rounded-lg border border-border bg-muted/20 p-4">
      <NextStepBadge n={n} done={!!done} disabled={!!disabled} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          <h3 className="text-sm font-semibold leading-snug">{title}</h3>
          {done && (
            <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
              Feito
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        {disabled && disabledHint && (
          <p className="mt-1 text-[11px] italic text-muted-foreground/80">
            {disabledHint}
          </p>
        )}
        <div className="mt-3">
          {disabled ? (
            <Button size="sm" variant={ctaVariant} disabled>
              {ctaLabel}
            </Button>
          ) : (
            <Button
              size="sm"
              variant={ctaVariant}
              nativeButton={false}
              render={<Link href={ctaHref} />}
            >
              {ctaLabel}
              <ArrowRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>
    </li>
  );
}

function NextStepBadge({
  n,
  done,
  disabled,
}: {
  n: number;
  done: boolean;
  disabled: boolean;
}) {
  if (done) {
    return (
      <span
        className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-emerald-500/40 bg-emerald-500/10 text-xs font-semibold text-emerald-700 dark:text-emerald-300"
        aria-label={`Passo ${n} concluído`}
      >
        ✓
      </span>
    );
  }
  return (
    <span
      className={[
        "grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-semibold tabular-nums",
        disabled
          ? "border-muted-foreground/30 text-muted-foreground/60"
          : "border-foreground/40 text-foreground",
      ].join(" ")}
      aria-label={`Passo ${n}`}
    >
      {n}
    </span>
  );
}
