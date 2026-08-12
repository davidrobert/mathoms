"use client";

import Link from "next/link";
import { CheckCircle2, Lightbulb, ListTodo } from "lucide-react";

import { useDecisions } from "@/hooks/useDecisions";
import { useUpcomingTasks } from "@/components/tasks/useUpcomingTasks";

import { useSuggestionsCount } from "../../plano/_components/useSuggestionsCount";

interface ActionStatusBarProps {
  workspaceId: string;
}

/** Direção E · Onda 6 — barra de status no topo de /acao.
 *
 * Mostra contadores agregados que dão escala do que está em jogo:
 * sugestões pendentes (do último relatório), tarefas com prazo nos
 * próximos 7 dias, decisões já decididas aguardando execução.
 *
 * F5 (PLAN-suggestion-lifecycle) — os chips passam a ser links de fato.
 * O docstring prometia isso desde a Onda 6, mas `StatusChip` renderizava
 * `<span>`: contador que promete navegação e não navega treina o usuário
 * a não clicar. O chip de decisões aponta para `/plano`, onde
 * `DecisionsSection` de fato mora — /acao não tem tab de decisões, e o
 * rótulo antigo sugeria que tinha.
 */
export function ActionStatusBar({ workspaceId }: ActionStatusBarProps) {
  const { count: suggestions } = useSuggestionsCount(workspaceId);
  const { tasks: upcoming } = useUpcomingTasks(20);
  const { decisions } = useDecisions(workspaceId);
  const decisionsToExecute = decisions.filter((d) => d.status === "Decidido")
    .length;

  return (
    <div
      role="status"
      aria-label="Resumo de itens em ação"
      className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-border bg-muted/30 px-4 py-2.5 text-sm"
    >
      <StatusChip
        icon={Lightbulb}
        label="Sugestões pendentes"
        value={suggestions}
        href="/acao?tab=inbox"
      />
      <ChipDivider />
      <StatusChip
        icon={ListTodo}
        label="Tarefas — próximos 7 dias"
        value={upcoming.length}
        href="/acao?tab=tarefas"
      />
      <ChipDivider />
      <StatusChip
        icon={CheckCircle2}
        label="Decisões a executar em /plano"
        value={decisionsToExecute}
        href="/plano"
      />
    </div>
  );
}

function ChipDivider() {
  return <span aria-hidden className="h-4 w-px bg-border" />;
}

interface StatusChipProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  /** Destino do chip quando `value > 0`. */
  href: string;
}

const CHIP_CLASS = "inline-flex items-center gap-1.5";

/** Zero fica não-clicável (muted, sem `<a>`): navegar para uma lista
 *  vazia é uma promessa quebrada, e um link inerte no tab order só
 *  adiciona parada sem destino para quem navega por teclado. */
function StatusChip({ icon: Icon, label, value, href }: StatusChipProps) {
  if (value === 0) {
    return (
      <span className={`${CHIP_CLASS} text-muted-foreground`}>
        <ChipBody Icon={Icon} label={label} value={value} />
      </span>
    );
  }
  return (
    <Link href={href} className={`${CHIP_CLASS} text-foreground hover:underline`}>
      <ChipBody Icon={Icon} label={label} value={value} />
    </Link>
  );
}

function ChipBody({
  Icon,
  label,
  value,
}: {
  Icon: StatusChipProps["icon"];
  label: string;
  value: number;
}) {
  return (
    <>
      <Icon className="h-3.5 w-3.5" />
      <span className="font-mono tabular-nums font-medium">{value}</span>
      <span className="text-xs">{label}</span>
    </>
  );
}
