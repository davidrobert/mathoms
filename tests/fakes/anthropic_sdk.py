"""Fake do SDK ``anthropic`` no boundary do cliente (ADR-355)."""
# CLAUDE.md §Testes: fake nomeado, nunca MagicMock inline.
#
# Hookar o SDK — e não o choke-point ``LLMService`` — é o que torna a asserção
# "0 chamada LLM" confiável: as superfícies condicionais dentro de stage
# determinístico (classificação E0, parser Caixa) instanciam
# ``anthropic.Anthropic`` direto, passando por fora do choke-point.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, sdk: "RecordingAnthropicSDK") -> None:
        self._sdk = sdk

    def create(self, **kwargs: Any) -> _FakeMessage:
        self._sdk.calls.append(kwargs)
        return _FakeMessage(json.dumps(self._sdk.payload))


class _FakeClient:
    def __init__(self, sdk: "RecordingAnthropicSDK") -> None:
        self.messages = _FakeMessages(sdk)


@dataclass
class RecordingAnthropicSDK:
    """Substituto de ``anthropic.Anthropic`` que registra cada ``messages.create``."""

    payload: Dict[str, Any] = field(default_factory=dict)
    calls: List[Dict[str, Any]] = field(default_factory=list)

    def install(self, monkeypatch) -> "RecordingAnthropicSDK":
        """Troca ``anthropic.Anthropic`` pelo fake e devolve ``self`` para asserção."""
        import anthropic

        monkeypatch.setattr(anthropic, "Anthropic", lambda **_kwargs: _FakeClient(self))
        return self
