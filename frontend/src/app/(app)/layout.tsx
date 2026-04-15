import AppShell from "@/components/AppShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";

/**
 * F6.5D.11 — toda page sob (app)/ envolvida em ErrorBoundary.
 * Crash em uma page (ex: chart quebrado no Dashboard) mostra fallback clean
 * em vez de derrubar o AppShell ou a tab inteira.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <ErrorBoundary>{children}</ErrorBoundary>
    </AppShell>
  );
}
