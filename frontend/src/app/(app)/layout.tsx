import AppShell from "@/components/AppShell";
import { AuthBootstrap } from "@/components/AuthBootstrap";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { WorkspaceProvider } from "@/lib/WorkspaceProvider";
import { DebugDuplicateKey } from "@/components/DebugDuplicateKey";

/**
 * F6.5D.11 — toda page sob (app)/ envolvida em ErrorBoundary.
 * Crash em uma page (ex: chart quebrado no Dashboard) mostra fallback clean
 * em vez de derrubar o AppShell ou a tab inteira.
 *
 * F9 · AuthBootstrap instala handler global de `token_revoked` — quando
 * backend invalida o JWT (user removido de workspace), redireciona pro login.
 *
 * P2 · WorkspaceProvider resolve o workspace uma vez e compartilha via context.
 * Pages usam `useWorkspace()` em vez de `useCurrentWorkspace()` (fetch por page).
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <AppShell>
        <DebugDuplicateKey />
        <AuthBootstrap />
        <ErrorBoundary>{children}</ErrorBoundary>
      </AppShell>
    </WorkspaceProvider>
  );
}
