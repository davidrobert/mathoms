"use client";

/**
 * /acao — superfície dinâmica de ação (Direção E · Onda 6 · ADR-152).
 *
 * Renomeada de `/plano-de-acao` em ADR-152. Tabs: Inbox · Tarefas ·
 * Timeline · Notas. Topo fixo de status agrega contadores.
 *
 * Default: tab Tarefas (estado atual da pré-Onda 6). Quando Onda 5
 * ligar Suggestions, fazer Inbox como default se houver pendentes
 * (designer recommendation: "força o ritual").
 */

import { useState } from "react";
import { CalendarClock, Inbox, ListTodo, StickyNote } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { ActionStatusBar } from "./_components/ActionStatusBar";
import { InboxTab } from "./_components/InboxTab";
import { NotasTab } from "./_components/NotasTab";
import { TasksTab } from "./_components/TasksTab";
import { TimelineTab } from "./_components/TimelineTab";

type TabId = "inbox" | "tarefas" | "timeline" | "notas";

const DEFAULT_TAB: TabId = "tarefas";

export default function AcaoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const [tab, setTab] = useState<TabId>(DEFAULT_TAB);

  if (wsLoading) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8">
        <PageHeader title="Ação" description="Carregando..." />
      </div>
    );
  }
  if (!workspace) {
    return <NoWorkspaceState />;
  }
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader
        title="Ação"
        description="O que fazer agora — sugestões, tarefas, próximos passos, notas"
      />
      <ActionStatusBar workspaceId={workspace.id} />
      <AcaoTabs
        tab={tab}
        onTabChange={setTab}
        workspaceId={workspace.id}
      />
    </div>
  );
}

function NoWorkspaceState() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <PageHeader title="Ação" />
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Nenhum workspace encontrado.
        </CardContent>
      </Card>
    </div>
  );
}

interface AcaoTabsProps {
  tab: TabId;
  onTabChange: (t: TabId) => void;
  workspaceId: string;
}

function AcaoTabs({ tab, onTabChange, workspaceId }: AcaoTabsProps) {
  return (
    <Tabs value={tab} onValueChange={(v) => onTabChange(v as TabId)}>
      <TabsList className="mb-4">
        <TabsTrigger value="inbox">
          <Inbox className="h-3.5 w-3.5" />
          Inbox
        </TabsTrigger>
        <TabsTrigger value="tarefas">
          <ListTodo className="h-3.5 w-3.5" />
          Tarefas
        </TabsTrigger>
        <TabsTrigger value="timeline">
          <CalendarClock className="h-3.5 w-3.5" />
          Timeline
        </TabsTrigger>
        <TabsTrigger value="notas">
          <StickyNote className="h-3.5 w-3.5" />
          Notas
        </TabsTrigger>
      </TabsList>
      <TabsContent value="inbox">
        <InboxTab workspaceId={workspaceId} />
      </TabsContent>
      <TabsContent value="tarefas">
        <TasksTab workspaceId={workspaceId} />
      </TabsContent>
      <TabsContent value="timeline">
        <TimelineTab workspaceId={workspaceId} />
      </TabsContent>
      <TabsContent value="notas">
        <NotasTab workspaceId={workspaceId} />
      </TabsContent>
    </Tabs>
  );
}
