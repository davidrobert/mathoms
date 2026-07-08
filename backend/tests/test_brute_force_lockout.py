"""Unit tests do BruteForceLockoutService (7B.13)."""

from __future__ import annotations

import pytest

from backend.app.services.security.brute_force_lockout import (
    BruteForceLockoutService,
    InMemoryBruteForceLockoutBackend,
    LockoutState,
    NoOpBruteForceLockoutService,
)


@pytest.fixture
def backend() -> InMemoryBruteForceLockoutBackend:
    return InMemoryBruteForceLockoutBackend()


@pytest.fixture
def service(backend: InMemoryBruteForceLockoutBackend) -> BruteForceLockoutService:
    return BruteForceLockoutService(
        backend,
        threshold=5,
        durations_s=(60, 300, 900, 3600),
    )


class TestThresholdAndLockout:
    def test_below_threshold_does_not_lock(self, service: BruteForceLockoutService) -> None:
        for _ in range(4):
            state = service.record_failure("user@x.com")
            assert state.locked is False
        # 4 failures → still unlocked
        assert service.check_locked("user@x.com").locked is False

    def test_threshold_triggers_first_lockout_at_60s(
        self, service: BruteForceLockoutService
    ) -> None:
        for _ in range(4):
            service.record_failure("user@x.com")
        state = service.record_failure("user@x.com")
        assert state.locked is True
        assert state.retry_after_s == 60
        assert state.level == 1

    def test_check_locked_during_lockout_returns_remaining(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        for _ in range(5):
            service.record_failure("user@x.com")
        backend.advance_clock(20.0)
        state = service.check_locked("user@x.com")
        assert state.locked is True
        assert state.retry_after_s == 40

    def test_lockout_expires_after_duration(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        for _ in range(5):
            service.record_failure("user@x.com")
        backend.advance_clock(60.5)
        assert service.check_locked("user@x.com").locked is False


class TestEscalation:
    def test_second_lockout_uses_5min_duration(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        # Primeira rodada — 5 falhas → 60s
        for _ in range(5):
            service.record_failure("user@x.com")
        assert service.check_locked("user@x.com").retry_after_s == 60

        # Espera lock acabar e gera 5 novas falhas → 300s (level=1 já está)
        backend.advance_clock(61.0)
        for _ in range(4):
            service.record_failure("user@x.com")
        state = service.record_failure("user@x.com")
        assert state.locked is True
        assert state.retry_after_s == 300
        assert state.level == 2

    def test_fourth_and_beyond_lockouts_cap_at_1h(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        # Acelera 4 ciclos completos → durations devem ser 60, 300, 900, 3600
        durations_seen: list[int] = []
        for _ in range(5):  # 5 ciclos: 4º+ deve cair no cap (3600)
            for _ in range(5):
                state = service.record_failure("user@x.com")
            durations_seen.append(state.retry_after_s)
            backend.advance_clock(state.retry_after_s + 1)
        assert durations_seen == [60, 300, 900, 3600, 3600]


class TestRecordSuccess:
    def test_success_clears_fail_count(
        self,
        service: BruteForceLockoutService,
    ) -> None:
        for _ in range(3):
            service.record_failure("user@x.com")
        service.record_success("user@x.com")
        # Próximas 4 falhas não devem travar — contador foi a zero
        for _ in range(4):
            state = service.record_failure("user@x.com")
            assert state.locked is False

    def test_success_does_not_clear_level(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        # Trava uma vez (level=1)
        for _ in range(5):
            service.record_failure("user@x.com")
        backend.advance_clock(61.0)
        # Sucesso depois do unlock natural
        service.record_success("user@x.com")
        # Próximas 5 falhas → 300s (level preservado), não 60s
        for _ in range(5):
            state = service.record_failure("user@x.com")
        assert state.retry_after_s == 300

    def test_success_clears_lock_when_already_unlocked(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        for _ in range(5):
            service.record_failure("user@x.com")
        backend.advance_clock(61.0)
        service.record_success("user@x.com")
        assert service.check_locked("user@x.com").locked is False


class TestEmailNormalization:
    def test_email_case_insensitive(self, service: BruteForceLockoutService) -> None:
        for _ in range(5):
            service.record_failure("User@Example.COM")
        # Mesma conta com casing diferente → mesmo bucket
        assert service.check_locked("user@example.com").locked is True
        assert service.check_locked("USER@example.com").locked is True

    def test_email_strips_whitespace(self, service: BruteForceLockoutService) -> None:
        for _ in range(5):
            service.record_failure("  user@x.com  ")
        assert service.check_locked("user@x.com").locked is True


class TestPerEmailIsolation:
    def test_different_emails_independent(self, service: BruteForceLockoutService) -> None:
        for _ in range(5):
            service.record_failure("a@x.com")
        # b@x.com permanece intacto
        assert service.check_locked("b@x.com").locked is False
        for _ in range(4):
            state = service.record_failure("b@x.com")
            assert state.locked is False


class TestUnlock:
    def test_unlock_clears_everything(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        # Trava + escalação
        for _ in range(5):
            service.record_failure("user@x.com")
        assert service.check_locked("user@x.com").locked is True
        service.unlock("user@x.com")
        state = service.check_locked("user@x.com")
        assert state.locked is False
        assert state.fail_count == 0
        assert state.level == 0
        # E a primeira lockout volta a ser de 60s (não 300s)
        for _ in range(5):
            new_state = service.record_failure("user@x.com")
        assert new_state.retry_after_s == 60


class TestRecordFailureWhenLocked:
    def test_does_not_extend_existing_lock(
        self,
        service: BruteForceLockoutService,
        backend: InMemoryBruteForceLockoutBackend,
    ) -> None:
        # Trava
        for _ in range(5):
            service.record_failure("user@x.com")
        backend.advance_clock(30.0)
        before = service.check_locked("user@x.com").retry_after_s
        # Tentativa adicional não deve estender o lock nem subir level
        service.record_failure("user@x.com")
        after = service.check_locked("user@x.com").retry_after_s
        assert after == before


class TestNoOpService:
    def test_noop_never_locks(self) -> None:
        s = NoOpBruteForceLockoutService()
        for _ in range(100):
            assert s.record_failure("user@x.com").locked is False
        assert s.check_locked("user@x.com").locked is False


class TestServiceConfig:
    def test_threshold_must_be_positive(self, backend: InMemoryBruteForceLockoutBackend) -> None:
        with pytest.raises(ValueError):
            BruteForceLockoutService(backend, threshold=0)

    def test_durations_must_be_nonempty(self, backend: InMemoryBruteForceLockoutBackend) -> None:
        with pytest.raises(ValueError):
            BruteForceLockoutService(backend, threshold=5, durations_s=())


class TestLockoutStateDataclass:
    def test_default_unlocked(self) -> None:
        s = LockoutState(locked=False)
        assert s.retry_after_s == 0
        assert s.fail_count == 0
        assert s.level == 0
