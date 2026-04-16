"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PipelineEvent } from "./api";

interface UsePipelineWSOptions {
  runId: string | null;
  token: string | null;
  onEvent?: (event: PipelineEvent) => void;
  /** Chamado a cada ~15s enquanto o servidor mantém o WS vivo (não é persistido como evento de etapa). */
  onHeartbeat?: () => void;
  onRunFinished?: (event: PipelineEvent) => void;
  maxReconnects?: number;
}

type WSStatus = "disconnected" | "connecting" | "connected" | "failed";

const WS_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api`
    : "";

const TERMINAL_EVENTS = new Set(["run_completed", "run_failed", "run_cancelled"]);

export function usePipelineWS({
  runId,
  token,
  onEvent,
  onHeartbeat,
  onRunFinished,
  maxReconnects = 3,
}: UsePipelineWSOptions) {
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<PipelineEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      if (
        wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  const connect = useCallback(() => {
    if (!runId || !token || !WS_BASE) return;

    cleanup();
    setStatus("connecting");

    const url = `${WS_BASE}/pipeline/runs/${runId}/ws?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectCountRef.current = 0;
    };

    ws.onmessage = (evt) => {
      try {
        const data: PipelineEvent = JSON.parse(evt.data);
        if (data.event === "heartbeat") {
          onHeartbeat?.();
          return;
        }

        setLastEvent(data);
        onEvent?.(data);

        if (TERMINAL_EVENTS.has(data.event)) {
          onRunFinished?.(data);
          cleanup();
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = (evt) => {
      if (evt.code === 1000) {
        setStatus("disconnected");
        return;
      }

      if (reconnectCountRef.current < maxReconnects) {
        reconnectCountRef.current += 1;
        const delay = Math.min(1000 * 2 ** reconnectCountRef.current, 16000);
        setStatus("connecting");
        reconnectTimerRef.current = setTimeout(connect, delay);
      } else {
        setStatus("failed");
      }
    };

    ws.onerror = () => {
      // onclose will handle reconnection
    };
  }, [runId, token, maxReconnects, onEvent, onHeartbeat, onRunFinished, cleanup]);

  useEffect(() => {
    if (runId && token) {
      connect();
    } else {
      cleanup();
    }
    return cleanup;
  }, [runId, token, connect, cleanup]);

  return { status, lastEvent };
}
