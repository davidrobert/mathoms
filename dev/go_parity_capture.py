#!/usr/bin/env python3
"""Captura de eventos WS de um run do pipeline via Redis pub/sub (F2 GO_SHELL, [[ADR-150]] §7): assina `pipeline:{run_id}` e despeja os envelopes num JSON que o `dev/go_parity_gate.py` consome no Tier-2. Integração (exige Redis + run ativo); o operador roda contra a stack do `make go-on`."""

# Espelha o subscribe de backend/app/application/realtime/pipeline_progress.py
# (canal pipeline:{run_id}, get_message ignore_subscribe_messages, eventos
# terminais run_completed/failed/cancelled). Cliente Redis sync + URL do env
# (MATHOMS_REDIS_URL/REDIS_URL) — sem importar backend, para rodar standalone.
#
# --pattern existe por uma corrida REAL: o run_id só nasce no dispatch, e pub/sub
# não faz replay. Assinar pipeline:{run_id} DEPOIS de disparar perde os primeiros
# envelopes (run_started, primeiro stage_started) por uma janela que varia a cada
# run — divergência de sequência que parece bug do Go e é artefato do harness.
# Com psubscribe pipeline:* o coletor sobe ANTES do dispatch e não perde nada;
# quem filtra por run é filter_by_run, depois, com o run_id em mão.

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


_PATTERN = "pipeline:*"
_MESSAGE_TYPES = frozenset({"message", "pmessage"})


def filter_by_run(events: list[dict], run_id: str) -> list[dict]:
    """Recorta os envelopes de um run só, preservando a ordem de chegada (a sequência é o que o Tier-2 compara)."""
    return [e for e in events if e.get("run_id") == run_id]


def capture_events(run_id: str, *, idle_timeout: float = 20.0) -> list[dict]:
    """Coleta os envelopes de ``pipeline:{run_id}`` até um evento terminal ou ``idle_timeout``s sem mensagem."""
    return _capture(f"pipeline:{run_id}", pattern=False, idle_timeout=idle_timeout)


def capture_any_run(*, idle_timeout: float = 20.0) -> list[dict]:
    """Coleta de ``pipeline:*`` até o primeiro terminal — para subir ANTES do dispatch (ver corrida no topo)."""
    return _capture(_PATTERN, pattern=True, idle_timeout=idle_timeout)


def _capture(channel: str, *, pattern: bool, idle_timeout: float) -> list[dict]:
    import redis  # lazy: só o operador com a stack ativa precisa do pacote

    client = redis.from_url(_redis_url(), decode_responses=True)
    sub = client.pubsub()
    (sub.psubscribe if pattern else sub.subscribe)(channel)
    try:
        return _drain(sub, idle_timeout)
    finally:
        (sub.punsubscribe if pattern else sub.unsubscribe)(channel)
        sub.close()
        client.close()


def _drain(sub, idle_timeout: float) -> list[dict]:
    events: list[dict] = []
    while True:
        message = sub.get_message(ignore_subscribe_messages=True, timeout=idle_timeout)
        if message is None:
            return events  # idle: run terminou sem evento terminal ou pausou
        if message.get("type") not in _MESSAGE_TYPES:
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


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura eventos WS de um run (F2 GO_SHELL).")
    parser.add_argument("--run-id", help="pipeline_run_id a assinar (omita com --pattern)")
    parser.add_argument("--out", required=True, help="arquivo JSON de saída (lista de envelopes)")
    parser.add_argument(
        "--pattern",
        action="store_true",
        help="assina pipeline:* (suba ANTES do dispatch; filtre depois com filter_by_run)",
    )
    parser.add_argument("--idle-timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    if not args.pattern and not args.run_id:
        parser.error("--run-id é obrigatório sem --pattern")
    return args


def _gather(args: argparse.Namespace) -> list[dict]:
    """Com --pattern o recorte por run é opcional: o orquestrador prefere filtrar ele mesmo."""
    if not args.pattern:
        return capture_events(args.run_id, idle_timeout=args.idle_timeout)
    events = capture_any_run(idle_timeout=args.idle_timeout)
    return filter_by_run(events, args.run_id) if args.run_id else events


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    events = _gather(args)
    Path(args.out).write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"capturados {len(events)} eventos → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
