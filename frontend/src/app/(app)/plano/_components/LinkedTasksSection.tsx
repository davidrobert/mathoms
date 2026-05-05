"use client";

import Link from "next/link";
import { ArrowRight, ListTodo } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { TaskDeadlineBadge } from "@/components/tasks/TaskDeadlineBadge";
import { TaskPriorityChip } from "@/components/tasks/TaskPriorityChip";
import { TaskStatusPill } from "@/components/tasks/TaskStatusPill";
import type { TaskResponse } from "@/lib/api";

interface LinkedTasksSectionProps {
  tasks: TaskResponse[];
}

export function LinkedTasksSection({ tasks }: LinkedTasksSectionProps) {
  return (
    <section className="mt-8">
      <SectionHeading
        icon={ListTodo}
        label="Tarefas que destravam esta meta"
        count={tasks.length > 0 ? tasks.length : undefined}
        action={
          <Button
            variant="ghost"
            size="xs"
            nativeButton={false}
            render={<Link href="/acao" />}
          >
            Ver todas <ArrowRight className="ml-1 h-3 w-3" />
          </Button>
        }
      />
      {tasks.length === 0 ? (
        <EmptyLinkedTasks />
      ) : (
        <ul className="space-y-2">
          {tasks.map((task) => (
            <LinkedTaskRow key={task.id} task={task} />
          ))}
        </ul>
      )}
    </section>
  );
}

function EmptyLinkedTasks() {
  return (
    <EmptyState
      icon={ListTodo}
      title="Nenhuma tarefa ligada a esta meta."
      description="Crie tarefas em /acao e ligue-as à meta de IF para acompanhar o progresso aqui."
      layout="inline"
      ctas={[
        { label: "Criar tarefa manual", href: "/acao", variant: "secondary" },
        { label: "Ver sugestões automáticas", href: "/acao/sugestoes", variant: "secondary" },
      ]}
    />
  );
}

function LinkedTaskRow({ task }: { task: TaskResponse }) {
  return (
    <li className="flex items-start gap-3 rounded-md border border-transparent bg-muted/30 px-3 py-2 text-sm hover:border-border">
      <span className="mt-0.5 font-mono text-xs tabular-nums text-muted-foreground">
        #{task.number}
      </span>
      <div className="flex-1">
        <p className="font-medium">{task.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <TaskPriorityChip priority={task.priority} />
          <Badge variant="outline">{task.category}</Badge>
          <TaskStatusPill status={task.status} />
          <TaskDeadlineBadge task={task} />
        </div>
      </div>
    </li>
  );
}
