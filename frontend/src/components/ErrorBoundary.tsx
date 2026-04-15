"use client";

import { Component, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

/**
 * ErrorBoundary — F6.5D.11
 *
 * Captura crashes de renderização em subárvores React e mostra fallback
 * clean ao invés de deixar o app inteiro quebrar. Envolve cada page sob
 * (app)/ via AppLayout.
 *
 * Política:
 * - Crash em 1 chart não derruba o dashboard inteiro.
 * - Fallback tem CTA "Recarregar" (reset state) + "Voltar" (router back).
 * - Em produção, relatar para Sentry (F7C). Aqui só console.error.
 *
 * NOTA: Error boundaries precisam ser class components (hook useError não
 * existe em React 19). Alternativa moderna é `react-error-boundary`, mas
 * manter aqui sem deps extras.
 */

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: { componentStack: string }) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack: string }) {
    // Log local; em prod vai para Sentry (F7C)
    if (typeof console !== "undefined") {
      console.error("[ErrorBoundary]", error, errorInfo.componentStack);
    }
    this.props.onError?.(error, errorInfo);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.reset);
      }
      return <DefaultFallback error={this.state.error} reset={this.reset} />;
    }
    return this.props.children;
  }
}

function DefaultFallback({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div
      role="alert"
      className="mx-auto mt-16 flex max-w-lg flex-col items-center rounded-xl border border-destructive/20 bg-destructive/5 p-8 text-center"
    >
      <AlertCircle className="mb-4 h-10 w-10 text-destructive" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">
        Algo deu errado ao renderizar esta página
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {error.message || "Erro desconhecido. Tente recarregar ou reportar o problema."}
      </p>
      <div className="mt-6 flex gap-3">
        <Button onClick={reset}>Recarregar</Button>
        <Button
          variant="outline"
          onClick={() => {
            if (typeof window !== "undefined") {
              window.location.href = "/dashboard";
            }
          }}
        >
          Ir para dashboard
        </Button>
      </div>
    </div>
  );
}
