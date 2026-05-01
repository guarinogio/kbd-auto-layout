from kbd_auto_layout.daemon import apply_layout_verified
from kbd_auto_layout.models import GeneralConfig


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.matches_calls = 0
        self.set_calls = 0

    def layout_matches(self, layout, variant):
        self.matches_calls += 1
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
