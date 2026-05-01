from kbd_auto_layout.daemon import apply_layout_verified
from kbd_auto_layout.models import GeneralConfig


def test_apply_layout_verified_retries_until_layout_matches(monkeypatch):
    calls = {"matches": 0, "set": 0}

    def fake_layout_matches(layout, variant):
        calls["matches"] += 1
        return calls["set"] >= 1

    def fake_set_layout(layout, variant):
        calls["set"] += 1

    monkeypatch.setattr("kbd_auto_layout.daemon.layout_matches", fake_layout_matches)
    monkeypatch.setattr("kbd_auto_layout.daemon.set_layout", fake_set_layout)

    general = GeneralConfig(apply_retries=3, apply_retry_delay=0)

    assert apply_layout_verified("us", "", "test", general)
    assert calls["set"] == 1


def test_apply_layout_verified_returns_false_after_retries(monkeypatch):
    calls = {"set": 0}

    monkeypatch.setattr("kbd_auto_layout.daemon.layout_matches", lambda layout, variant: False)

    def fake_set_layout(layout, variant):
        calls["set"] += 1

    monkeypatch.setattr("kbd_auto_layout.daemon.set_layout", fake_set_layout)

    general = GeneralConfig(apply_retries=3, apply_retry_delay=0)

    assert not apply_layout_verified("us", "", "test", general)
    assert calls["set"] == 3
