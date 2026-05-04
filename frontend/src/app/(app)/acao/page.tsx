"use client";

/**
 * /acao — superfície dinâmica de ação (Direção E · Onda 6 · ADR-152).
 *
 * Renomeada de `/plano-de-acao` em ADR-152. Tabs: Inbox · Tarefas ·
 * Timeline · Notas. Topo fixo de status agrega contadores.
 *
 * Default (Onda 7 #2): tab Inbox quando há sugestões pendentes; senão
 * Tarefas. URL `?tab=inbox|tarefas|timeline|notas` sempre vence (deep-
 * link do relatório → /acao?tab=inbox#SUG-XXX).
 */

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
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
import { useSuggestionsCount } from "../plano/_components/useSuggestionsCount";

type TabId = "inbox" | "tarefas" | "timeline" | "notas";

const FALLBACK_TAB: TabId = "tarefas";
const VALID_TAB_IDS: ReadonlySet<string> = new Set([
  "inbox",
  "tarefas",
  "timeline",
  "notas",
]);

function parseTabId(value: string | null | undefined): TabId | null {
  return value && VALID_TAB_IDS.has(value) ? (value as TabId) : null;
}

export default function AcaoPage() {
  return (
    <Suspense fallback={<AcaoLoadingState />}>
      <AcaoPageInner />
    </Suspense>
  );
}

function AcaoLoadingState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader title="Ação" description="Carregando..." />
    </div>
  );
}

function AcaoPageInner() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const searchParams = useSearchParams();
  const urlTab = parseTabId(searchParams?.get("tab"));
  const { count: pending, loading: pendingLoading } = useSuggestionsCount(workspace?.id);
  const { tab, onTabChange } = useTabSelection({ urlTab, pending, pendingLoading });
  useScrollToHashCard(tab);

  if (wsLoading) return <AcaoLoadingState />;
  if (!workspace) return <NoWorkspaceState />;
  return <AcaoLoaded workspaceId={workspace.id} tab={tab} onTabChange={onTabChange} />;
}

interface AcaoLoadedProps {
  workspaceId: string;
  tab: TabId;
  onTabChange: (t: TabId) => void;
}

function AcaoLoaded({ workspaceId, tab, onTabChange }: AcaoLoadedProps) {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader
        title="Ação"
        description="O que fazer agora — sugestões, tarefas, próximos passos, notas"
      />
      <ActionStatusBar workspaceId={workspaceId} />
      <AcaoTabs tab={tab} onTabChange={onTabChange} workspaceId={workspaceId} />
    </div>
  );
}

interface UseTabSelectionInput {
  urlTab: TabId | null;
  pending: number;
  pendingLoading: boolean;
}

/** Onda 7 #2 — defaulta para Inbox quando há sugestões pendentes; URL
 * `?tab=` sempre vence; se o usuário trocou manualmente, ignora pending. */
function useTabSelection({ urlTab, pending, pendingLoading }: UseTabSelectionInput) {
  const [tab, setTab] = useState<TabId>(urlTab ?? FALLBACK_TAB);
  const userPickedRef = useRef(false);

  useEffect(() => {
    if (urlTab) return;
    if (userPickedRef.current) return;
    if (pendingLoading) return;
    if (pending > 0) setTab("inbox");
  }, [pending, pendingLoading, urlTab]);

  const onTabChange = (t: TabId) => {
    userPickedRef.current = true;
    setTab(t);
  };
  return { tab, onTabChange };
}

/** Onda 7 #3 — quando navegamos para `/acao?tab=inbox#SUG-XXX`, o Inbox
 * carrega assíncrono; tentamos posicionar o card por ~2s até ele
 * existir no DOM. Anchor highlight via `:target` em SuggestionCard. */
function useScrollToHashCard(tab: TabId) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (tab !== "inbox") return;
    const hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    let attempts = 0;
    const handle = window.setInterval(() => {
      const el = document.getElementById(hash.slice(1));
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        window.clearInterval(handle);
        return;
      }
      if (++attempts >= 20) window.clearInterval(handle);
    }, 100);
    return () => window.clearInterval(handle);
  }, [tab]);
}

function NoWorkspaceState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
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
