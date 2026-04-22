"use client";

import Link from "next/link";
import { ArrowRight, ListTodo, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TaskDeadlineBadge } from "@/components/tasks/TaskDeadlineBadge";
import { TaskPriorityChip } from "@/components/tasks/TaskPriorityChip";
import { TaskStatusPill } from "@/components/tasks/TaskStatusPill";
import type { TaskResponse } from "@/lib/api";

interface LinkedTasksSectionProps {
  tasks: TaskResponse[];
}

export function LinkedTasksSection({ tasks }: LinkedTasksSectionProps) {
  return (
    <Card className="mt-6">
      <CardContent className="py-6">
        <LinkedTasksHeader count={tasks.length} />
        {tasks.length === 0 ? (
          <EmptyLinkedTasks />
        ) : (
          <ul className="space-y-2">
            {tasks.map((task) => (
              <LinkedTaskRow key={task.id} task={task} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function LinkedTasksHeader({ count }: { count: number }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        <ListTodo className="h-4 w-4" />
        Tarefas que destravam esta meta
        {count > 0 && (
          <span className="ml-1 font-mono text-xs tabular-nums normal-case">
            ({count})
          </span>
        )}
      </h2>
      <Button
        variant="ghost"
        size="xs"
        nativeButton={false}
        render={<Link href="/plano-de-acao" />}
      >
        Ver todas <ArrowRight className="ml-1 h-3 w-3" />
      </Button>
    </div>
  );
}

function EmptyLinkedTasks() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-6 text-center">
      <ListTodo className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
      <p className="text-sm text-muted-foreground">
        Nenhuma tarefa ligada a esta meta.
      </p>
      <div className="mt-3 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
        <Button
          variant="outline"
          size="sm"
          nativeButton={false}
          render={<Link href="/plano-de-acao" />}
        >
          <ListTodo className="mr-1.5 h-3.5 w-3.5" />
          Criar tarefa manual
        </Button>
        <Button
          variant="ghost"
          size="sm"
          nativeButton={false}
          render={<Link href="/plano-de-acao/sugestoes" />}
        >
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          Ver sugestoes automaticas
        </Button>
      </div>
    </div>
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
