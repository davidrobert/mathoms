"""Prazo do run — o soft time limit do executor visto por código que não pode importá-lo."""

# `pipeline/**` não importa `celery` (`dev/check_pipeline_boundaries.py`), mas o soft
# time limit do worker estoura DENTRO do código daqui: o billiard levanta
# `SoftTimeLimitExceeded`, uma `Exception` pura, na linha que estiver rodando.
#
# O sinal não serve de portador. Medido em 2026-10-08: dentro de uma chamada LLM o
# litellm o embrulha em `InternalServerError` e o instructor em
# `InstructorRetryException`. O `LLMService.call` classifica o resultado como
# `provider_error` e refaz a chamada. No `extract_with_llm` ele estoura no
# `as_completed`, e as threads do pool nunca o recebem. Por isso o prazo é um objeto
# do run, compartilhado entre threads: quem observa o sinal o DISPARA, e o relógio
# é a rede de segurança de quem não o observa (ADR-446).
#
# O tipo do sinal vem de `sys.modules`, nunca de import: se o billiard não foi
# carregado, o processo não é worker e o sinal não existe.

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable


class RunTimeLimitExceededError(Exception):
    """O prazo do run esgotou e o trabalho pedido não começa."""


def time_limit_exceptions() -> tuple[type[BaseException], ...]:
    """Exceções que encerram o run por tempo: o erro do prazo e, sob o billiard, o sinal."""
    module = sys.modules.get("billiard.exceptions")
    signal = getattr(module, "SoftTimeLimitExceeded", None)
    if isinstance(signal, type) and issubclass(signal, BaseException):
        return (RunTimeLimitExceededError, signal)
    return (RunTimeLimitExceededError,)


def is_time_limit(exc: BaseException) -> bool:
    """``exc`` ou uma causa dele encerra o run por tempo — o sinal chega embrulhado."""
    kinds = time_limit_exceptions()
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, kinds):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


# O relógio vence DEPOIS do sinal, nunca antes. O billiard conta a partir do ACK do
# job e confere a cada 1s, então o sinal chega em `ack + limite + [0, 1s]`. Um relógio
# que vencesse primeiro pararia o run e abriria o post-processing com o sinal ainda
# pendente, e o sinal cairia dentro da criação do relatório.
SIGNAL_GRACE_S = 5.0


@dataclass(frozen=True)
class RunDeadline:
    """Prazo do run: vence quando alguém o dispara ou o relógio passa de ``expires_at``."""

    expires_at: float | None = None
    budget_s: float | None = None
    started_at: float | None = None
    clock: Callable[[], float] = field(default=time.monotonic, repr=False, compare=False)
    _tripped: threading.Event = field(default_factory=threading.Event, repr=False, compare=False)

    @classmethod
    def starting_now(
        cls,
        budget_s: float | None,
        *,
        grace_s: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> RunDeadline:
        """Prazo de ``budget_s`` contado agora; o relógio só vence ``grace_s`` depois."""
        if budget_s is None:
            return cls(clock=clock)
        now = clock()
        return cls(
            expires_at=now + budget_s + grace_s, budget_s=budget_s, started_at=now, clock=clock
        )

    def trip(self) -> None:
        """O sinal foi observado: o prazo vence agora para todas as threads do run."""
        self._tripped.set()

    def expired(self) -> bool:
        if self._tripped.is_set():
            return True
        return self.expires_at is not None and self.clock() >= self.expires_at

    def remaining_s(self) -> float | None:
        """Segundos até o relógio vencer; ``None`` sem prazo, ``0.0`` se já venceu."""
        if self.expired():
            return 0.0
        return None if self.expires_at is None else self.expires_at - self.clock()

    def elapsed_s(self) -> float | None:
        return None if self.started_at is None else self.clock() - self.started_at

    def check(self, work: str) -> None:
        """Levanta ``RunTimeLimitExceededError`` se o prazo venceu antes de ``work`` começar."""
        if self.expired():
            raise RunTimeLimitExceededError(f"prazo do run esgotado: {work} não começa")
