#!/usr/bin/env python3
"""Captura de eventos WS de um run do pipeline via Redis pub/sub (F2 GO_SHELL, [[ADR-150]] §7): assina `pipeline:{run_id}` e despeja os envelopes num JSON que o `dev/go_parity_gate.py` consome no Tier-2. Integração (exige Redis + run ativo); o operador roda contra a stack do `make go-on`."""

# Espelha o subscribe de backend/app/application/realtime/pipeline_progress.py
# (canal pipeline:{run_id}, get_message ignore_subscribe_messages, eventos
# terminais run_completed/failed/cancelled). Cliente Redis sync + URL do env
# (MATHOMS_REDIS_URL/REDIS_URL) — sem importar backend, para rodar standalone.

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_TERMINAL_EVENTS = frozenset({"run_completed", "run_failed", "run_cancelled"})


def _is_terminal(event: dict) -> bool:
    return event.get("event") in _TERMINAL_EVENTS


def _redis_url() -> str:
    url = os.environ.get("MATHOMS_REDIS_URL") or os.environ.get("REDIS_URL")
    if not url:
        raise SystemExit(
            "MATHOMS_REDIS_URL/REDIS_URL ausente — aponte para o Redis da stack ativa."
        )
    return url


def capture_events(run_id: str, *, idle_timeout: float = 20.0) -> list[dict]:
    """Coleta os envelopes de ``pipeline:{run_id}`` até um evento terminal ou ``idle_timeout``s sem mensagem."""
    import redis  # lazy: só o operador com a stack ativa precisa do pacote

    client = redis.from_url(_redis_url(), decode_responses=True)
    sub = client.pubsub()
    sub.subscribe(f"pipeline:{run_id}")
    try:
        return _drain(sub, idle_timeout)
    finally:
        sub.unsubscribe(f"pipeline:{run_id}")
        sub.close()
        client.close()


def _drain(sub, idle_timeout: float) -> list[dict]:
    events: list[dict] = []
    while True:
        message = sub.get_message(ignore_subscribe_messages=True, timeout=idle_timeout)
        if message is None:
            return events  # idle: run terminou sem evento terminal ou pausou
        if message.get("type") != "message":
            continue
        event = _decode(message.get("data"))
        if event is None:
            continue
        events.append(event)
        if _is_terminal(event):
            return events


def _decode(data) -> dict | None:
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captura eventos WS de um run (F2 GO_SHELL).")
    parser.add_argument("--run-id", required=True, help="pipeline_run_id a assinar")
    parser.add_argument("--out", required=True, help="arquivo JSON de saída (lista de envelopes)")
    parser.add_argument("--idle-timeout", type=float, default=20.0)
    args = parser.parse_args(argv)

    events = capture_events(args.run_id, idle_timeout=args.idle_timeout)
    Path(args.out).write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"capturados {len(events)} eventos → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
