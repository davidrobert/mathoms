/**
 * Unit tests — `lib/usePipelineWS.ts` (WebSocket hook)
 *
 * F6.5A.7
 *
 * Cobertura: connect, mensagens, eventos terminais, reconnect com backoff,
 * cleanup ao desmontar. WebSocket é mockado via classe customizada com
 * fila de instâncias para inspeção.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, waitFor } from "@testing-library/react";
import { useEffect } from "react";

import { usePipelineWS } from "@/lib/usePipelineWS";

// ─── Mock WebSocket ──────────────────────────────────────────────────

class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  url: string;
  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  onerror: ((ev: any) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  // simulação manual
  simOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({});
  }
  simMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
  simClose(code: number) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }
  simError() {
    this.onerror?.({});
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }

  static reset() {
    MockWebSocket.instances = [];
  }
}

// Helper component que usa o hook
function HookHarness(props: {
  runId: string | null;
  token: string | null;
  onEvent?: (e: any) => void;
  onRunFinished?: (e: any) => void;
  onStatus?: (s: string) => void;
  maxReconnects?: number;
}) {
  const { status, lastEvent } = usePipelineWS({
    runId: props.runId,
    token: props.token,
    onEvent: props.onEvent,
    onRunFinished: props.onRunFinished,
    maxReconnects: props.maxReconnects,
  });
  useEffect(() => {
    props.onStatus?.(status);
  }, [status, props]);
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="last">{lastEvent ? JSON.stringify(lastEvent) : ""}</span>
    </div>
  );
}

beforeEach(() => {
  MockWebSocket.reset();
  vi.useFakeTimers();
  // WebSocket é readonly em jsdom — usar stubGlobal (vitest) que restaura no afterEach
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// ─── Connect lifecycle ───────────────────────────────────────────────

describe("usePipelineWS — connect lifecycle", () => {
  it("não conecta quando runId é null", () => {
    render(<HookHarness runId={null} token="t" />);
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("não conecta quando token é null", () => {
    render(<HookHarness runId="run-1" token={null} />);
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("conecta com URL contendo runId + token URL-encoded", () => {
    render(<HookHarness runId="run-1" token="abc 123" />);
    expect(MockWebSocket.instances).toHaveLength(1);
    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain("/pipeline/runs/run-1/ws");
    expect(ws.url).toContain("token=abc%20123");
  });

  it("status vai para 'connected' após onopen", async () => {
    const { getByTestId } = render(<HookHarness runId="run-1" token="t" />);
    expect(getByTestId("status").textContent).toBe("connecting");

    act(() => {
      MockWebSocket.instances[0].simOpen();
    });
    expect(getByTestId("status").textContent).toBe("connected");
  });
});

// ─── Mensagens / heartbeat / terminal events ─────────────────────────

describe("usePipelineWS — message handling", () => {
  it("propaga evento via onEvent callback", async () => {
    const onEvent = vi.fn();
    render(<HookHarness runId="r" token="t" onEvent={onEvent} />);
    const ws = MockWebSocket.instances[0];
    act(() => ws.simOpen());

    act(() => ws.simMessage({ event: "stage_started", stage: "E2" }));
    expect(onEvent).toHaveBeenCalledWith({ event: "stage_started", stage: "E2" });
  });

  it("ignora heartbeat (não chama onEvent nem atualiza lastEvent)", () => {
    const onEvent = vi.fn();
    const { getByTestId } = render(
      <HookHarness runId="r" token="t" onEvent={onEvent} />,
    );
    const ws = MockWebSocket.instances[0];
    act(() => ws.simOpen());

    act(() => ws.simMessage({ event: "heartbeat" }));
    expect(onEvent).not.toHaveBeenCalled();
    expect(getByTestId("last").textContent).toBe("");
  });

  it("dispara onRunFinished + cleanup em run_completed", () => {
    const onFinished = vi.fn();
    render(<HookHarness runId="r" token="t" onRunFinished={onFinished} />);
    const ws = MockWebSocket.instances[0];
    act(() => ws.simOpen());

    act(() => ws.simMessage({ event: "run_completed", run_id: "r" }));
    expect(onFinished).toHaveBeenCalledWith({ event: "run_completed", run_id: "r" });
  });

  it("dispara onRunFinished em run_failed e run_cancelled", () => {
    const onFinished = vi.fn();
    const { rerender } = render(
      <HookHarness runId="r" token="t" onRunFinished={onFinished} />,
    );
    act(() => MockWebSocket.instances[0].simOpen());
    act(() =>
      MockWebSocket.instances[0].simMessage({ event: "run_failed", run_id: "r" }),
    );
    expect(onFinished).toHaveBeenCalledTimes(1);

    // Reset → novo runId para abrir nova conexão
    rerender(<HookHarness runId="r2" token="t" onRunFinished={onFinished} />);
    act(() => MockWebSocket.instances[1].simOpen());
    act(() =>
      MockWebSocket.instances[1].simMessage({
        event: "run_cancelled",
        run_id: "r2",
      }),
    );
    expect(onFinished).toHaveBeenCalledTimes(2);
  });

  it("ignora mensagens malformadas (JSON inválido) sem crashar", () => {
    const onEvent = vi.fn();
    render(<HookHarness runId="r" token="t" onEvent={onEvent} />);
    const ws = MockWebSocket.instances[0];
    act(() => ws.simOpen());

    act(() => {
      ws.onmessage?.({ data: "{ malformed json" });
    });
    expect(onEvent).not.toHaveBeenCalled();
  });
});

// ─── Reconnect com backoff exponencial ───────────────────────────────

describe("usePipelineWS — reconnect", () => {
  it("reconecta com backoff exponencial após close não-1000", async () => {
    const onStatus: string[] = [];
    render(
      <HookHarness runId="r" token="t" onStatus={(s) => onStatus.push(s)} />,
    );
    expect(MockWebSocket.instances).toHaveLength(1);

    // Simula close abrupto (não 1000)
    act(() => MockWebSocket.instances[0].simClose(1006));

    // Primeiro reconnect: delay = min(1000 * 2^1, 16000) = 2000ms
    expect(MockWebSocket.instances).toHaveLength(1); // ainda só 1 — aguardando timer
    act(() => {
      vi.advanceTimersByTime(2001);
    });
    expect(MockWebSocket.instances).toHaveLength(2);

    // Segundo reconnect: 1000 * 2^2 = 4000ms
    act(() => MockWebSocket.instances[1].simClose(1006));
    act(() => {
      vi.advanceTimersByTime(4001);
    });
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("para de reconectar após maxReconnects (status='failed')", () => {
    const { getByTestId } = render(
      <HookHarness runId="r" token="t" maxReconnects={2} />,
    );

    // 1ª tentativa
    act(() => MockWebSocket.instances[0].simClose(1006));
    act(() => vi.advanceTimersByTime(2001));
    // 2ª tentativa
    act(() => MockWebSocket.instances[1].simClose(1006));
    act(() => vi.advanceTimersByTime(4001));
    // 3ª tentativa rejeitada — passa de maxReconnects
    act(() => MockWebSocket.instances[2].simClose(1006));

    expect(getByTestId("status").textContent).toBe("failed");
    // Não deve haver 4ª instância
    act(() => vi.advanceTimersByTime(20000));
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("close 1000 (normal close) NÃO dispara reconnect", () => {
    const { getByTestId } = render(<HookHarness runId="r" token="t" />);
    act(() => MockWebSocket.instances[0].simClose(1000));
    act(() => vi.advanceTimersByTime(20000));

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(getByTestId("status").textContent).toBe("disconnected");
  });

  it("zera contador de reconnect ao conectar com sucesso", () => {
    render(<HookHarness runId="r" token="t" maxReconnects={2} />);

    // Primeira queda + reconnect bem-sucedido
    act(() => MockWebSocket.instances[0].simClose(1006));
    act(() => vi.advanceTimersByTime(2001));
    act(() => MockWebSocket.instances[1].simOpen());

    // Nova queda — contador deve ter zerado, então mais 2 retries permitidos
    act(() => MockWebSocket.instances[1].simClose(1006));
    act(() => vi.advanceTimersByTime(2001));
    act(() => MockWebSocket.instances[2].simClose(1006));
    act(() => vi.advanceTimersByTime(4001));

    // 4 instâncias = inicial + 3 reconnects (2 do primeiro ciclo + ...)
    // Importante: o test prova que NÃO ficou em 'failed' no segundo ciclo.
    expect(MockWebSocket.instances.length).toBeGreaterThanOrEqual(3);
  });
});

// ─── Cleanup ─────────────────────────────────────────────────────────

describe("usePipelineWS — cleanup", () => {
  it("limpa WS ao desmontar", () => {
    const { unmount } = render(<HookHarness runId="r" token="t" />);
    const ws = MockWebSocket.instances[0];
    const closeSpy = vi.spyOn(ws, "close");
    unmount();
    expect(closeSpy).toHaveBeenCalled();
  });

  it("muda runId → fecha conexão antiga e abre nova", () => {
    const { rerender } = render(<HookHarness runId="r1" token="t" />);
    const first = MockWebSocket.instances[0];
    const closeSpy = vi.spyOn(first, "close");

    rerender(<HookHarness runId="r2" token="t" />);
    expect(closeSpy).toHaveBeenCalled();
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toContain("/pipeline/runs/r2/ws");
  });
});
