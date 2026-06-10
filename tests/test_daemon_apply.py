from kbd_auto_layout.daemon import apply_layout_verified, run_loop
from kbd_auto_layout.models import GeneralConfig
import threading
import time


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.set_calls = 0

    def layout_matches(self, layout, variant):
        return self.set_calls >= 1

    def set_layout(self, layout, variant):
        self.set_calls += 1


class NeverMatchesBackend:
    name = "fake"

    def __init__(self):
        self.set_calls = 0

    def layout_matches(self, layout, variant):
        return False

    def set_layout(self, layout, variant):
        self.set_calls += 1


def test_apply_layout_verified_retries_until_layout_matches(monkeypatch):
    backend = FakeBackend()
    monkeypatch.setattr("kbd_auto_layout.daemon.detect_backend", lambda configured: backend)

    general = GeneralConfig(apply_retries=3, apply_retry_delay=0)

    assert apply_layout_verified("us", "", "test", general)
    assert backend.set_calls == 1


def test_apply_layout_verified_returns_false_after_retries(monkeypatch):
    backend = NeverMatchesBackend()
    monkeypatch.setattr("kbd_auto_layout.daemon.detect_backend", lambda configured: backend)

    general = GeneralConfig(apply_retries=3, apply_retry_delay=0)

    assert not apply_layout_verified("us", "", "test", general)
    assert backend.set_calls == 3


def test_daemon_recovers_from_find_active_rule_error(monkeypatch):
    """Daemon should not crash when device enumeration fails."""
    call_count = [0]

    def failing_find():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise OSError("xinput failure simulation")
        # After 2 failures, return valid data so daemon exits cleanly
        raise SystemExit(0)

    monkeypatch.setattr("kbd_auto_layout.daemon.find_active_rule", failing_find)
    monkeypatch.setattr("kbd_auto_layout.daemon.signal.signal", lambda *a: None)

    try:
        run_loop()
    except SystemExit:
        pass

    # Should have retried at least twice without crashing
    assert call_count[0] >= 2
