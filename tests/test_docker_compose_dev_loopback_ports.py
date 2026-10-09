"""Todo `ports:` do compose de dev publica só no loopback do host (ADR-252)."""

# Dentro dos containers os servers escutam em 0.0.0.0 (o port-forward do Docker
# entrega na eth0); o prefixo `127.0.0.1:` é a única camada que impede o
# console interno e o api dev-only de aparecerem na LAN.

from __future__ import annotations

from pathlib import Path

import yaml

COMPOSE_DEV = Path(__file__).resolve().parents[1] / "docker-compose.dev.yml"


def _published_ports() -> list[tuple[str, object]]:
    services = yaml.safe_load(COMPOSE_DEV.read_text(encoding="utf-8"))["services"]
    return [(name, entry) for name, spec in services.items() for entry in spec.get("ports", [])]


def _binds_host_loopback(entry: object) -> bool:
    if isinstance(entry, dict):
        return entry.get("host_ip") == "127.0.0.1"
    return isinstance(entry, str) and entry.startswith("127.0.0.1:")


def test_compose_dev_publishes_every_port_on_host_loopback() -> None:
    ports = _published_ports()
    assert ports, f"nenhum `ports:` encontrado em {COMPOSE_DEV.name}"
    offenders = [(n, e) for n, e in ports if not _binds_host_loopback(e)]
    assert (
        not offenders
    ), f"expected `127.0.0.1:<host>:<container>` em todo ports:, got {offenders!r}"


def test_loopback_predicate_rejects_unprefixed_publish() -> None:
    assert not _binds_host_loopback("3110:3100")
    assert not _binds_host_loopback("0.0.0.0:3110:3100")
    assert not _binds_host_loopback({"target": 3100, "published": "3110"})
    assert _binds_host_loopback({"host_ip": "127.0.0.1", "target": 3100})
