from kbd_auto_layout.daemon import _wait_for_next_check
from kbd_auto_layout.models import GeneralConfig


class FakeMonitor:
    available = True

    def __init__(self):
        self.wait_calls = 0

    def wait(self, timeout):
        self.wait_calls += 1
        return None


class UnavailableMonitor:
    available = False

    def __init__(self):
        self.wait_calls = 0

    def wait(self, timeout):
        self.wait_calls += 1
        return None


def test_wait_for_next_check_uses_event_monitor(monkeypatch):
    monitor = FakeMonitor()
    slept = []

    monkeypatch.setattr("kbd_auto_layout.daemon.time.sleep", lambda seconds: slept.append(seconds))
    monkeypatch.setattr("kbd_auto_layout.daemon.clear_device_cache", lambda: None)

    general = GeneralConfig(event_mode="auto", event_timeout=7)

    _wait_for_next_check(general, monitor)

    assert monitor.wait_calls == 1
    assert slept == []


def test_wait_for_next_check_falls_back_to_polling(monkeypatch):
    monitor = UnavailableMonitor()
    slept = []

    monkeypatch.setattr("kbd_auto_layout.daemon.time.sleep", lambda seconds: slept.append(seconds))
    monkeypatch.setattr("kbd_auto_layout.daemon.clear_device_cache", lambda: None)

    general = GeneralConfig(event_mode="auto", poll_interval=2)

    _wait_for_next_check(general, monitor)

    assert monitor.wait_calls == 0
    assert slept == [2]
