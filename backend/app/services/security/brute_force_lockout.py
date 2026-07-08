"""Brute-force lockout escalonado por e-mail para `/auth/login` (7B.13 · ADR-111 stateless)."""

# Esquema de chaves Redis (todas com TTL para auto-cleanup):
#   mathoms:auth:lockout:fail_count:{email_lc}   — INCR; TTL FAIL_COUNT_TTL_S (1h)
#   mathoms:auth:lockout:level:{email_lc}        — escalação; TTL LEVEL_TTL_S (24h)
#   mathoms:auth:lockout:locked_until:{email_lc} — epoch_s; TTL=duração
#
# Falha aberta em prod: se Redis cai, `get_default_lockout_service()` retorna
# `NoOpBruteForceLockoutService` (warning + nunca trava) — disponibilidade do
# login vence ganho marginal de segurança aqui.
#
# Wire em `backend/app/application/auth/login_user.py`:
#   check_locked → record_failure (em senha errada) | record_success (em senha certa).

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

#: Default — 5 falhas consecutivas dispara o primeiro lockout (BACKLOG 7B.13).
DEFAULT_THRESHOLD = 5

#: Cooldown escalonado em segundos: 1min → 5min → 15min → 1h.
DEFAULT_LOCKOUT_DURATIONS_S: tuple[int, ...] = (60, 300, 900, 3600)

#: TTL do contador de falhas — após 1h sem nova falha, contador reseta.
FAIL_COUNT_TTL_S = 3600

#: TTL da escalação — após 24h sem novo lockout, level volta a 0.
LEVEL_TTL_S = 24 * 3600


@dataclass(frozen=True)
class LockoutState:
    """Estado consultável por chamadores. ``locked`` ⟹ ``retry_after_s > 0``."""

    locked: bool
    retry_after_s: int = 0
    fail_count: int = 0
    level: int = 0


class BruteForceLockoutBackend(Protocol):
    """Protocol mínimo de storage com TTL (Redis-shaped)."""

    def get_int(self, key: str) -> Optional[int]: ...

    def incr_with_ttl(self, key: str, ttl_s: int) -> int:
        """INCR + EXPIRE atômico (ou equivalente). Retorna novo valor."""
        ...

    def set_int(self, key: str, value: int, ttl_s: int) -> None: ...

    def delete(self, *keys: str) -> None: ...

    def now_epoch_s(self) -> int:
        """Tempo agora em epoch seconds — backend define para permitir clock injection em tests."""
        ...


class BruteForceLockoutService:
    """Lockout escalonado por e-mail. Sem estado em instância (apenas backend + config)."""

    def __init__(
        self,
        backend: BruteForceLockoutBackend,
        *,
        threshold: int = DEFAULT_THRESHOLD,
        durations_s: tuple[int, ...] = DEFAULT_LOCKOUT_DURATIONS_S,
        fail_count_ttl_s: int = FAIL_COUNT_TTL_S,
        level_ttl_s: int = LEVEL_TTL_S,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if not durations_s:
            raise ValueError("durations_s must have at least one entry")
        self._backend = backend
        self._threshold = threshold
        self._durations_s = durations_s
        self._fail_count_ttl_s = fail_count_ttl_s
        self._level_ttl_s = level_ttl_s

    @staticmethod
    def _normalize(email: str) -> str:
        return email.strip().lower()

    def _key_count(self, email_lc: str) -> str:
        return f"mathoms:auth:lockout:fail_count:{email_lc}"

    def _key_level(self, email_lc: str) -> str:
        return f"mathoms:auth:lockout:level:{email_lc}"

    def _key_lock(self, email_lc: str) -> str:
        return f"mathoms:auth:lockout:locked_until:{email_lc}"

    def check_locked(self, email: str) -> LockoutState:
        """Snapshot do estado atual. Não muta nada."""
        email_lc = self._normalize(email)
        locked_until = self._backend.get_int(self._key_lock(email_lc)) or 0
        now = self._backend.now_epoch_s()
        if locked_until > now:
            return LockoutState(
                locked=True,
                retry_after_s=locked_until - now,
                fail_count=self._backend.get_int(self._key_count(email_lc)) or 0,
                level=self._backend.get_int(self._key_level(email_lc)) or 0,
            )
        return LockoutState(
            locked=False,
            fail_count=self._backend.get_int(self._key_count(email_lc)) or 0,
            level=self._backend.get_int(self._key_level(email_lc)) or 0,
        )

    def record_failure(self, email: str) -> LockoutState:
        """Incrementa contador; trava com cooldown escalonado se atingir threshold."""
        email_lc = self._normalize(email)
        # defesa-em-profundidade: se já travado, login flow não deveria chegar aqui
        existing = self.check_locked(email)
        if existing.locked:
            return existing
        new_count = self._backend.incr_with_ttl(self._key_count(email_lc), self._fail_count_ttl_s)
        if new_count < self._threshold:
            return LockoutState(locked=False, fail_count=new_count, level=existing.level)
        return self._apply_lockout(email_lc, existing.level)

    def _apply_lockout(self, email_lc: str, prev_level: int) -> LockoutState:
        idx = min(prev_level, len(self._durations_s) - 1)
        duration = self._durations_s[idx]
        locked_until = self._backend.now_epoch_s() + duration
        new_level = prev_level + 1
        self._backend.set_int(self._key_lock(email_lc), locked_until, ttl_s=duration)
        # contador zerado para que próximas N falhas elevem o level
        self._backend.delete(self._key_count(email_lc))
        self._backend.set_int(self._key_level(email_lc), new_level, ttl_s=self._level_ttl_s)
        logger.warning(
            "brute_force_lockout_triggered",
            extra={
                "email_hash": _hash_email(email_lc),
                "duration_s": duration,
                "level": new_level,
            },
        )
        return LockoutState(locked=True, retry_after_s=duration, fail_count=0, level=new_level)

    def record_success(self, email: str) -> None:
        """Login OK — limpa contador e lock; preserva level (decai por TTL)."""
        email_lc = self._normalize(email)
        # Não deletamos `level` para que escalação persista contra
        # padrões attack-then-pause-then-attack (pelo TTL de 24h).
        self._backend.delete(
            self._key_count(email_lc),
            self._key_lock(email_lc),
        )

    def unlock(self, email: str) -> None:
        """Unlock manual (admin/internal_ops). Limpa tudo, inclusive level."""
        email_lc = self._normalize(email)
        self._backend.delete(
            self._key_count(email_lc),
            self._key_lock(email_lc),
            self._key_level(email_lc),
        )
        logger.info(
            "brute_force_lockout_manual_unlock",
            extra={"email_hash": _hash_email(email_lc)},
        )


def _hash_email(email_lc: str) -> str:
    """Hash curto para logs estruturados (ADR-110 D5 — e-mail = PII)."""
    import hashlib

    return hashlib.sha256(email_lc.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


class RedisBruteForceLockoutBackend:
    """Redis adapter. Falha aberta — exceções viram log + retorno seguro."""

    def __init__(self, client) -> None:  # noqa: ANN001 — redis client é dinâmico
        self._client = client

    def get_int(self, key: str) -> Optional[int]:
        try:
            value = self._client.get(key)
        except Exception as exc:  # noqa: BLE001 — falha aberta proposital
            logger.warning("RedisBruteForceLockoutBackend.get failed for %s: %s", key, exc)
            return None
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def incr_with_ttl(self, key: str, ttl_s: int) -> int:
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, int(ttl_s))
            results = pipe.execute()
            # results[0] = novo valor do INCR
            return int(results[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("RedisBruteForceLockoutBackend.incr failed for %s: %s", key, exc)
            # Falha aberta: retorna 0 para não travar conta por bug de infra.
            return 0

    def set_int(self, key: str, value: int, ttl_s: int) -> None:
        try:
            self._client.set(key, int(value), ex=int(ttl_s))
        except Exception as exc:  # noqa: BLE001
            logger.warning("RedisBruteForceLockoutBackend.set failed for %s: %s", key, exc)

    def delete(self, *keys: str) -> None:
        if not keys:
            return
        try:
            self._client.delete(*keys)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RedisBruteForceLockoutBackend.delete failed: %s", exc)

    def now_epoch_s(self) -> int:
        return int(time.time())


class InMemoryBruteForceLockoutBackend:
    """Backend in-memory para tests. NÃO usar em prod (viola ADR-111)."""

    def __init__(self) -> None:
        self._values: dict[str, int] = {}
        self._expires_at: dict[str, float] = {}
        self._clock: float = time.monotonic()

    # Permite testes determinísticos: avançar o relógio explicitamente.
    def advance_clock(self, seconds: float) -> None:
        self._clock += float(seconds)
        self._gc()

    def _gc(self) -> None:
        now = self._clock
        expired = [k for k, exp in self._expires_at.items() if exp <= now]
        for k in expired:
            self._values.pop(k, None)
            self._expires_at.pop(k, None)

    def get_int(self, key: str) -> Optional[int]:
        self._gc()
        return self._values.get(key)

    def incr_with_ttl(self, key: str, ttl_s: int) -> int:
        self._gc()
        new_value = self._values.get(key, 0) + 1
        self._values[key] = new_value
        self._expires_at[key] = self._clock + float(ttl_s)
        return new_value

    def set_int(self, key: str, value: int, ttl_s: int) -> None:
        self._gc()
        self._values[key] = int(value)
        self._expires_at[key] = self._clock + float(ttl_s)

    def delete(self, *keys: str) -> None:
        for key in keys:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)

    def now_epoch_s(self) -> int:
        # Em test, "agora" é um clock virtual baseado em advance_clock.
        # Convertemos para epoch-like int (offset arbitrário) — coerente
        # com locked_until calculado dentro do mesmo backend.
        return int(self._clock)


# ---------------------------------------------------------------------------
# No-op (Redis indisponível em prod = não trava)
# ---------------------------------------------------------------------------


class NoOpBruteForceLockoutService:
    """Service que nunca trava — ativado quando Redis indisponível (warning na 1ª chamada)."""

    def __init__(self) -> None:
        self._warned = False

    def _maybe_warn(self) -> None:
        if not self._warned:
            logger.warning("brute_force_lockout_disabled — Redis unavailable, all attempts allowed")
            self._warned = True

    def check_locked(self, email: str) -> LockoutState:  # noqa: ARG002
        self._maybe_warn()
        return LockoutState(locked=False)

    def record_failure(self, email: str) -> LockoutState:  # noqa: ARG002
        self._maybe_warn()
        return LockoutState(locked=False)

    def record_success(self, email: str) -> None:  # noqa: ARG002
        return None

    def unlock(self, email: str) -> None:  # noqa: ARG002
        return None


# ---------------------------------------------------------------------------
# Resolver — entrypoint usado pelo login_user
# ---------------------------------------------------------------------------


def get_default_lockout_service() -> "BruteForceLockoutService | NoOpBruteForceLockoutService":
    """Resolve backend default — Redis se disponível (ADR-111), senão no-op."""
    client = _resolve_redis_client()
    if client is None:
        return NoOpBruteForceLockoutService()
    from backend.app.core.config import settings

    return BruteForceLockoutService(
        RedisBruteForceLockoutBackend(client),
        threshold=settings.BRUTE_FORCE_THRESHOLD,
        durations_s=tuple(settings.BRUTE_FORCE_LOCKOUT_DURATIONS_S),
    )


def _resolve_redis_client():  # noqa: ANN202 — redis client é dinâmico
    try:
        from backend.app.services.pipeline.events import _get_redis

        return _get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load Redis for brute-force lockout: %s", exc)
        return None
