/**
 * Tests — ErrorBoundary (F6.5D.11)
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErrorBoundary } from "@/components/ErrorBoundary";

// Componente que crasha deliberadamente
function Crasher({ shouldCrash = true }: { shouldCrash?: boolean }): JSX.Element {
  if (shouldCrash) {
    throw new Error("Chart quebrou");
  }
  return <div>OK</div>;
}

// Silencia console.error (React loga boundaries caught errors)
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("<ErrorBoundary />", () => {
  it("passa children quando não há erro", () => {
    render(
      <ErrorBoundary>
        <div>conteudo normal</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("conteudo normal")).toBeInTheDocument();
  });

  it("captura erro e mostra fallback default", () => {
    render(
      <ErrorBoundary>
        <Crasher />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Algo deu errado/)).toBeInTheDocument();
    expect(screen.getByText(/Chart quebrou/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Recarregar/ })).toBeInTheDocument();
  });

  it("botão 'Recarregar' reseta state e re-renderiza children", async () => {
    const user = userEvent.setup();
    let crashNow = true;
    function Toggle() {
      if (crashNow) throw new Error("boom");
      return <div>recuperado</div>;
    }
    render(
      <ErrorBoundary>
        <Toggle />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/Algo deu errado/)).toBeInTheDocument();

    crashNow = false;
    await user.click(screen.getByRole("button", { name: /Recarregar/ }));
    expect(screen.getByText("recuperado")).toBeInTheDocument();
  });

  it("onError callback é chamado com erro e componentStack", () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <Crasher />
      </ErrorBoundary>,
    );
    expect(onError).toHaveBeenCalled();
    const [err, info] = onError.mock.calls[0];
    expect(err.message).toBe("Chart quebrou");
    expect(info.componentStack).toBeTypeOf("string");
  });

  it("fallback customizado sobrescreve default", () => {
    render(
      <ErrorBoundary
        fallback={(error, reset) => (
          <div>
            custom: {error.message}
            <button onClick={reset}>tentar</button>
          </div>
        )}
      >
        <Crasher />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/custom: Chart quebrou/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "tentar" })).toBeInTheDocument();
  });

  it("F6.5D.11: crash em 1 subárvore não derruba siblings", () => {
    render(
      <div>
        <ErrorBoundary>
          <Crasher />
        </ErrorBoundary>
        <div>sibling intacto</div>
      </div>,
    );
    expect(screen.getByText("sibling intacto")).toBeInTheDocument();
    expect(screen.getByText(/Algo deu errado/)).toBeInTheDocument();
  });
});
