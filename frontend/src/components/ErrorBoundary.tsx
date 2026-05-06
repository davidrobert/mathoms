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
        Não conseguimos carregar esta página
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Tivemos um problema inesperado. Tente novamente — se continuar, recarregue
        o app ou avise nossa equipe que registramos o erro.
      </p>
      <div className="mt-6 flex gap-3">
        <Button onClick={reset}>Tentar novamente</Button>
        <Button
          variant="outline"
          onClick={() => {
            if (typeof window !== "undefined") {
              window.location.href = "/plano";
            }
          }}
        >
          Voltar para Meu Plano
        </Button>
      </div>
      <details className="mt-6 w-full text-left text-xs text-muted-foreground/80">
        <summary className="cursor-pointer select-none hover:text-muted-foreground">
          Detalhes técnicos
        </summary>
        <pre className="mt-2 overflow-x-auto rounded-md bg-muted/40 p-3 font-mono text-[11px] leading-relaxed">
          {error.name}: {error.message || "erro desconhecido"}
        </pre>
      </details>
    </div>
  );
}
